"""
Programs & Requirements Agent

Responsibilities:
- Answer questions about major/minor requirements
- Check degree progress
- Validate plans
- PROPOSE semester-by-semester plans

Knowledge Base: chroma_db_programs/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint, PlanOption
from langchain_core.messages import SystemMessage
import json
import re

class ProgramsRequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="programs_requirements",
            domain="programs"  # Uses chroma_db_programs/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Programs & Requirements agent.

        This agent PROPOSES plans (part of Proposal + Critique protocol).
        Emits streaming events for real-time UI updates.
        """
        # Emit start event
        self.emit_start()

        # Set enhanced retrieval k if provided (for confidence-based re-retrieval)
        self.set_retrieval_k_from_state(state)

        try:
            # 1. Read from Blackboard
            user_query = state.get("user_query", "")
            user_goal = state.get("user_goal", "")
            student_profile = state.get("student_profile", {})
            constraints = state.get("constraints", [])

            # Get memory context (conversation history + student profile)
            memory_context = self.get_memory_context(state)

            # 2. Retrieve domain-specific context (emits its own events)
            query_for_rag = f"{user_query} {user_goal}"
            context = self.retrieve_context(query_for_rag)

            # 3. Build prompt
            self.emit_thinking("Analyzing program requirements...")
            prompt = self._build_prompt(user_query, user_goal, student_profile, context, constraints, memory_context)

            # 4. Call LLM
            self.emit_thinking("Generating response...")
            response = self.llm.invoke([SystemMessage(content=prompt)])

            # 5. Parse and return structured output
            result = self._parse_response(response.content)

            # Emit full output for streaming display
            self.emit_output(result)

            # Emit completion
            self.emit_complete(
                confidence=result.confidence,
                summary=f"Found {len(result.relevant_policies)} relevant policies"
            )

            return result

        except Exception as e:
            self.emit_error(str(e))
            raise
    
    def _build_prompt(self, query: str, goal: str, profile: dict, context: str, constraints: list, memory_context: str = "") -> str:
        """Build detailed prompt for Programs agent."""
        constraints_text = "\n".join([f"- {c.description}" for c in constraints]) if constraints else "None"
        profile_text = json.dumps(profile, indent=2) if profile else "Not provided"

        # Include conversation context if available
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what "it", "the course", "this program", "that requirement" etc. refer to. If the student mentions something from a previous message, look at the context to understand what they mean.
"""

        return f"""You are the Programs & Requirements Agent for CMU-Q.
{context_section}

Your Responsibilities:
1. Answer questions about major/minor requirements
2. Check degree progress
3. Validate whether plans satisfy requirements
4. PROPOSE semester-by-semester plans when asked

Student Profile: {profile_text}
User Goal: {goal}
User Query: {query}
Existing Constraints: {constraints_text}

Retrieved Context (from program requirements documents):
{context}

IMPORTANT - How to Use Retrieved Context:
- Each retrieved chunk includes [DOCUMENT CONTEXT] metadata showing:
  * File name and type (e.g., program_requirements, concentration_info)
  * Program it relates to (e.g., Information Systems)
  * Courses mentioned in that document
  * Summary of what the document contains
- Use this metadata to understand the SOURCE and SCOPE of information
- When citing requirements, mention which document/file they come from
- If multiple documents provide conflicting info, prefer the most specific one
- If a document summary shows it contains exactly what the user needs, pay special attention to it

Instructions:
- Be specific and cite relevant policies AND document sources
- If proposing a plan, provide semester-by-semester breakdown
- Identify any requirement violations or risks
- Provide confidence score (0.0-1.0)
- Reference the specific documents used (from [DOCUMENT CONTEXT] metadata)

Format your response as JSON:
{{
    "answer": "Your detailed answer",
    "confidence": 0.85,
    "relevant_policies": ["policy1", "policy2"],
    "risks": [
        {{"type": "overload_risk", "severity": "high", "description": "..."}}
    ],
    "constraints": [
        {{"source": "policy", "description": "...", "hard": true}}
    ],
    "plan_options": [
        {{
            "semesters": [
                {{"semester": "Fall 2026", "courses": ["15-112", "67-100"]}},
                {{"semester": "Spring 2027", "courses": ["15-121", "67-200"]}}
            ],
            "courses": ["15-112", "67-100", "15-121", "67-200"],
            "confidence": 0.8,
            "justification": "This plan satisfies all requirements..."
        }}
    ]
}}
"""
    
    def _parse_response(self, response_text: str) -> AgentOutput:
        """Parse LLM response into structured AgentOutput."""
        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback
                data = {
                    "answer": response_text,
                    "confidence": 0.7,
                    "relevant_policies": [],
                    "risks": [],
                    "constraints": [],
                    "plan_options": []
                }
            
            # Convert to AgentOutput
            risks = [Risk(**r) for r in data.get("risks", [])]
            constraints = [Constraint(**c) for c in data.get("constraints", [])]
            plan_options = None
            if data.get("plan_options"):
                plan_options = [PlanOption(**p) for p in data["plan_options"]]
            
            return AgentOutput(
                agent_name=self.name,
                answer=data.get("answer", response_text),
                confidence=data.get("confidence", 0.8),
                relevant_policies=data.get("relevant_policies", []),
                risks=risks,
                constraints=constraints,
                plan_options=plan_options
            )
        except Exception as e:
            print(f"Error parsing Programs agent response: {e}")
            return AgentOutput(
                agent_name=self.name,
                answer=response_text,
                confidence=0.7,
                relevant_policies=[],
                risks=[],
                constraints=[]
            )

