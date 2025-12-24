"""
Policy & Compliance Agent

Responsibilities:
- Check plan compliance with policies
- Identify violations
- CRITIQUE plans proposed by Programs agent

Knowledge Base: chroma_db_policies/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint
from langchain_core.messages import SystemMessage
import json
import re

class PolicyComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="policy_compliance",
            domain="policies"  # Uses chroma_db_policies/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Policy & Compliance agent.
        
        This agent CRITIQUES plans (part of Proposal + Critique protocol).
        """
        user_query = state.get("user_query", "")
        agent_outputs = state.get("agent_outputs", {})
        student_profile = state.get("student_profile", {})
        
        # Check if we need to critique a plan
        programs_output = agent_outputs.get("programs_requirements")
        has_plan = (
            programs_output and 
            programs_output.plan_options and 
            len(programs_output.plan_options) > 0
        )
        
        if has_plan:
            return self._critique_plan(programs_output.plan_options[0], student_profile)
        else:
            return self._answer_policy_question(user_query)
    
    def _critique_plan(self, plan_option, student_profile: dict) -> AgentOutput:
        """Critique a proposed plan for policy compliance."""
        context = self.retrieve_context(
            "overload limits probation rules course repeat policies registration deadlines"
        )
        
        prompt = f"""You are the Policy & Compliance Agent for CMU-Q.

Your role: CRITIQUE proposed plans for policy compliance.

Student Profile: {json.dumps(student_profile, indent=2)}

Proposed Plan:
Semesters: {json.dumps(plan_option.semesters, indent=2)}
Courses: {plan_option.courses}
Justification: {plan_option.justification}

Retrieved Policies:
{context}

Check compliance with:
1. Overload limits (max units per semester)
2. Probation rules
3. Course repeat policies
4. Registration deadlines
5. Prerequisites

For each violation or risk, provide:
- Type of violation/risk
- Severity (high/medium/low)
- Policy citation
- Suggested modification

Format as JSON:
{{
    "answer": "Your critique",
    "confidence": 0.9,
    "relevant_policies": ["policy1"],
    "risks": [
        {{"type": "overload_risk", "severity": "high", "description": "...", "policy_citation": "..."}}
    ],
    "constraints": [
        {{"source": "policy", "description": "...", "hard": true, "policy_citation": "..."}}
    ]
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return self._parse_response(response.content)
    
    def _answer_policy_question(self, query: str) -> AgentOutput:
        """Answer general policy questions."""
        context = self.retrieve_context(query)
        prompt = f"""You are the Policy & Compliance Agent.

Query: {query}

Retrieved Policies:
{context}

Answer questions about university policies, compliance, and regulations.
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
    
    def _parse_response(self, response_text: str) -> AgentOutput:
        """Parse critique response."""
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"answer": response_text, "confidence": 0.8, "relevant_policies": [], "risks": [], "constraints": []}
            
            risks = [Risk(**r) for r in data.get("risks", [])]
            constraints = [Constraint(**c) for c in data.get("constraints", [])]
            
            return AgentOutput(
                agent_name=self.name,
                answer=data.get("answer", response_text),
                confidence=data.get("confidence", 0.8),
                relevant_policies=data.get("relevant_policies", []),
                risks=risks,
                constraints=constraints
            )
        except Exception as e:
            print(f"Error parsing Policy agent response: {e}")
            return AgentOutput(
                agent_name=self.name,
                answer=response_text,
                confidence=0.7,
                relevant_policies=[],
                risks=[],
                constraints=[]
            )

