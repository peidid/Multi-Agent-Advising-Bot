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
        """
        # 1. Read from Blackboard
        user_query = state.get("user_query", "")
        user_goal = state.get("user_goal", "")
        student_profile = state.get("student_profile", {})
        constraints = state.get("constraints", [])
        
        # 2. Retrieve domain-specific context
        query_for_rag = f"{user_query} {user_goal}"
        context = self.retrieve_context(query_for_rag)
        
        # 3. Build prompt
        prompt = self._build_prompt(user_query, user_goal, student_profile, context, constraints)
        
        # 4. Call LLM
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        # 5. Parse and return structured output
        return self._parse_response(response.content)
    
    def _build_prompt(self, query: str, goal: str, profile: dict, context: str, constraints: list) -> str:
        """Build detailed prompt for Programs agent."""
        constraints_text = "\n".join([f"- {c.description}" for c in constraints]) if constraints else "None"
        profile_text = json.dumps(profile, indent=2) if profile else "Not provided"
        
        return f"""You are the Programs & Requirements Agent for CMU-Q.

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

Instructions:
- Be specific and cite relevant policies
- If proposing a plan, provide semester-by-semester breakdown
- Identify any requirement violations or risks
- Provide confidence score (0.0-1.0)

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

