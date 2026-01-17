"""
LLM-Driven Coordinator (Research Version for ACL 2026)

Key Difference from Rule-Based Coordinator:
- No predefined intent types
- No hard-coded routing rules
- LLM understands advisor role and agent capabilities
- LLM dynamically plans workflow based on reasoning
- LLM adapts based on intermediate results

Philosophy:
"Let the LLM be the coordinator, not just a classifier"
"""

from typing import Dict, List, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re
from dataclasses import dataclass, asdict


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    name: str
    role: str
    capabilities: List[str]
    knowledge_domains: List[str]
    tools: List[str]
    limitations: List[str]


@dataclass
class WorkflowPlan:
    """A dynamic workflow plan created by the coordinator."""
    goal: str  # What are we trying to achieve?
    reasoning: str  # Why this workflow?
    agents: List[str]  # Which agents to use
    execution_order: List[str]  # In what order
    parallel_stages: List[List[str]]  # Which can run in parallel
    decision_points: List[Dict]  # Where to check results and adapt
    expected_challenges: List[str]  # What might go wrong
    success_criteria: str  # How do we know we succeeded


class LLMDrivenCoordinator:
    """
    A coordinator that uses LLM reasoning to understand problems
    and dynamically plan workflows.
    
    No predefined intent types. No hard-coded rules.
    Pure LLM-driven coordination.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        
        # Define agent capabilities (this is the "knowledge" the coordinator has)
        self.agent_capabilities = {
            "programs_requirements": AgentCapability(
                name="Programs Requirements Agent",
                role="Academic program specialist",
                capabilities=[
                    "Validate if a course plan satisfies major/minor requirements",
                    "Check degree progress toward graduation",
                    "Explain what courses are needed for a specific program",
                    "Propose semester-by-semester plans",
                    "Identify missing requirements",
                ],
                knowledge_domains=[
                    "Major requirements (CS, IS, Business)",
                    "Minor requirements",
                    "Degree structures",
                    "Course substitutions and equivalencies",
                    "Program-specific policies",
                ],
                tools=[
                    "RAG over program requirement documents",
                    "Degree audit logic",
                ],
                limitations=[
                    "Does NOT know specific course details (prerequisites, content, schedule)",
                    "Does NOT know university-wide policies (only program-specific)",
                    "Cannot check time conflicts or course availability",
                ]
            ),
            
            "course_scheduling": AgentCapability(
                name="Course Scheduling Agent",
                role="Course information specialist",
                capabilities=[
                    "Provide detailed information about specific courses",
                    "Explain prerequisites, corequisites, anti-requisites",
                    "Describe course content, assessment structure, workload",
                    "Check when courses are offered (semester, time)",
                    "Identify time conflicts between courses",
                    "Suggest alternative courses if conflicts exist",
                ],
                knowledge_domains=[
                    "Course catalog (all courses at CMU-Q)",
                    "Course prerequisites and dependencies",
                    "Course schedules and offerings",
                    "Course content and learning objectives",
                    "Instructor information",
                ],
                tools=[
                    "RAG over course descriptions",
                    "Course schedule database",
                ],
                limitations=[
                    "Does NOT know if a course satisfies major requirements",
                    "Does NOT know university policies about units, overload, etc.",
                    "Cannot validate degree progress",
                ]
            ),
            
            "policy_compliance": AgentCapability(
                name="Policy Compliance Agent",
                role="University policy specialist",
                capabilities=[
                    "Check if a plan complies with university policies",
                    "Explain unit limits, overload policies, GPA requirements",
                    "Validate registration rules (drop/add deadlines, etc.)",
                    "Flag policy violations and suggest fixes",
                    "Explain academic integrity, grading policies",
                ],
                knowledge_domains=[
                    "University-wide academic policies",
                    "Registration policies",
                    "Grading policies",
                    "Academic integrity policies",
                    "Financial policies (tuition, fees)",
                ],
                tools=[
                    "RAG over policy documents",
                    "Policy rule checker",
                ],
                limitations=[
                    "Does NOT know course-specific details",
                    "Does NOT know program-specific requirements",
                    "Cannot propose course plans (only validate them)",
                ]
            ),

            "academic_planning": AgentCapability(
                name="Academic Planning Agent",
                role="Multi-semester course planning specialist",
                capabilities=[
                    "Generate semester-by-semester course plans from current status to graduation",
                    "Balance workload across semesters (typically 45-54 units)",
                    "Ensure prerequisite courses are taken in correct order",
                    "Consider course availability patterns (Fall-only, Spring-only, every semester)",
                    "Integrate minor requirements into graduation plans",
                    "Adapt plans for early graduation, study abroad, or other constraints",
                    "Create multiple plan options with different strategies",
                    "Flag risky semesters (overload, high-difficulty courses together)",
                ],
                knowledge_domains=[
                    "Program requirements and sample curricula",
                    "Course offering patterns and schedules",
                    "Typical course sequencing and prerequisites",
                    "Workload balancing strategies",
                    "Minor integration approaches",
                ],
                tools=[
                    "RAG over program requirements and sample curricula",
                    "Course schedule database loader",
                    "Prerequisite analysis",
                    "Workload calculation utilities",
                ],
                limitations=[
                    "Cannot validate policy compliance (needs Policy Agent)",
                    "May not know latest course schedule changes",
                    "Cannot guarantee course availability in future semesters",
                    "Needs Programs Agent to verify requirement satisfaction",
                ]
            ),
        }
    
    def understand_and_plan(self, 
                           user_query: str,
                           conversation_history: List[Dict] = None,
                           student_profile: Dict = None) -> WorkflowPlan:
        """
        The core method: Understand the problem and plan a workflow.
        
        This is where the LLM does the reasoning, not rule matching.
        """
        
        # Build a rich context for the LLM
        agent_descriptions = self._format_agent_capabilities()
        advisor_role = self._get_advisor_role_description()
        conversation_context = self._format_conversation_history(conversation_history or [])
        student_context = self._format_student_profile(student_profile or {})
        
        # The prompt: Let LLM understand and plan
        prompt = f"""{advisor_role}

AVAILABLE AGENTS AND THEIR CAPABILITIES:

{agent_descriptions}

STUDENT CONTEXT:
{student_context}

CONVERSATION HISTORY:
{conversation_context}

CURRENT QUERY:
"{user_query}"

YOUR TASK AS COORDINATOR:

1. UNDERSTAND THE PROBLEM:
   - What is the student really asking for?
   - What is the underlying goal or concern?
   - What information do we need to provide a good answer?

2. ANALYZE WHICH AGENTS CAN HELP:
   - Which agents have the capabilities needed?
   - What are the limitations of each agent?
   - Do we need multiple agents? If so, why?

3. PLAN THE WORKFLOW:
   - In what order should agents be consulted?
   - Can any agents work in parallel?
   - Are there decision points where we need to check results before proceeding?
   - What might go wrong, and how do we handle it?

4. DEFINE SUCCESS:
   - How will we know if we've answered the student's question well?

RESPOND IN JSON FORMAT:
{{
    "understanding": {{
        "student_goal": "What the student is trying to achieve",
        "underlying_concern": "The deeper concern or question",
        "information_needed": ["What info we need to answer well"]
    }},
    "agent_analysis": {{
        "agent_name": {{
            "can_help_with": ["Specific things this agent can do for this query"],
            "cannot_help_with": ["Things this agent cannot do"],
            "priority": "high" | "medium" | "low",
            "reasoning": "Why we need (or don't need) this agent"
        }}
    }},
    "workflow_plan": {{
        "goal": "Clear statement of what we're trying to achieve",
        "reasoning": "Why this workflow makes sense",
        "execution_order": ["agent1", "agent2", ...],
        "parallel_stages": [["agent1", "agent2"], ["agent3"]],
        "decision_points": [
            {{
                "after_agent": "agent_name",
                "check": "What to check in the result",
                "if_problem": "What to do if there's an issue"
            }}
        ],
        "expected_challenges": ["What might go wrong"],
        "success_criteria": "How we know we succeeded"
    }},
    "confidence": 0.0-1.0,
    "needs_clarification": true | false,
    "clarification_questions": ["Question if needed"]
}}

IMPORTANT:
- Think like an advisor, not a router
- your main task is to ensure that the students could finish his/her degree on time and successfully, while remaining in good health/mental condition. Remember to consider program requirement, if academic decision-making is involved. 
- Reason about the problem and students' academic plans, don't just match keywords
- Consider the student's context and history
- Plan dynamically based on the specific situation
- Explain your reasoning clearly
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        try:
            # Parse LLM response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                # Convert to WorkflowPlan
                workflow_data = result.get('workflow_plan', {})
                plan = WorkflowPlan(
                    goal=workflow_data.get('goal', ''),
                    reasoning=workflow_data.get('reasoning', ''),
                    agents=self._extract_unique_agents(workflow_data),
                    execution_order=workflow_data.get('execution_order', []),
                    parallel_stages=workflow_data.get('parallel_stages', []),
                    decision_points=workflow_data.get('decision_points', []),
                    expected_challenges=workflow_data.get('expected_challenges', []),
                    success_criteria=workflow_data.get('success_criteria', '')
                )
                
                # Store full result for debugging
                plan.full_analysis = result
                
                return plan
        
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            # Fallback to simple plan
            return self._create_fallback_plan(user_query)
    
    def adapt_workflow(self, 
                      current_plan: WorkflowPlan,
                      agent_results: Dict[str, Any],
                      current_state: Dict) -> WorkflowPlan:
        """
        Adapt the workflow based on intermediate results.
        
        This is where dynamic coordination happens.
        """
        
        # Check decision points
        for decision_point in current_plan.decision_points:
            after_agent = decision_point.get('after_agent')
            
            if after_agent in agent_results:
                # Ask LLM to evaluate and adapt
                result = agent_results[after_agent]
                
                adaptation_prompt = f"""You are coordinating a multi-agent academic advising system.

ORIGINAL PLAN:
Goal: {current_plan.goal}
Reasoning: {current_plan.reasoning}
Remaining agents: {[a for a in current_plan.execution_order if a not in agent_results]}

DECISION POINT:
After agent: {after_agent}
Check: {decision_point.get('check')}
If problem: {decision_point.get('if_problem')}

AGENT RESULT:
{json.dumps(result, indent=2, default=str)}

QUESTION:
Based on this result, should we:
1. Continue with the original plan?
2. Modify the plan (add/remove agents, change order)?
3. Stop here (we have enough information)?

Respond in JSON:
{{
    "decision": "continue" | "modify" | "stop",
    "reasoning": "Why this decision",
    "modifications": {{
        "add_agents": ["agent_name"],
        "remove_agents": ["agent_name"],
        "new_order": ["agent1", "agent2", ...]
    }} if decision is "modify"
}}
"""
                
                adaptation_response = self.llm.invoke([SystemMessage(content=adaptation_prompt)])
                
                try:
                    json_match = re.search(r'\{.*\}', adaptation_response.content, re.DOTALL)
                    if json_match:
                        adaptation = json.loads(json_match.group())
                        
                        if adaptation['decision'] == 'modify':
                            # Update plan
                            mods = adaptation.get('modifications', {})
                            current_plan.execution_order = mods.get('new_order', current_plan.execution_order)
                            # Add reasoning for modification
                            current_plan.reasoning += f"\n\nADAPTATION: {adaptation['reasoning']}"
                
                except Exception as e:
                    print(f"Error adapting workflow: {e}")
        
        return current_plan
    
    def _format_agent_capabilities(self) -> str:
        """Format agent capabilities for LLM."""
        formatted = []
        
        for agent_name, capability in self.agent_capabilities.items():
            formatted.append(f"""
Agent: {capability.name} ({agent_name})
Role: {capability.role}

Capabilities:
{chr(10).join(f'  • {cap}' for cap in capability.capabilities)}

Knowledge Domains:
{chr(10).join(f'  • {domain}' for domain in capability.knowledge_domains)}

Tools:
{chr(10).join(f'  • {tool}' for tool in capability.tools)}

Limitations:
{chr(10).join(f'  • {limit}' for limit in capability.limitations)}
""")
        
        return "\n".join(formatted)
    
    def _get_advisor_role_description(self) -> str:
        """Describe the coordinator's role as an advisor."""
        return """You are the COORDINATOR of a multi-agent academic advising system at CMU-Q.

YOUR ROLE AS ADVISOR:
- Help students make informed decisions about their academic path
- Understand not just what students ask, but what they really need
- Coordinate specialized agents to provide comprehensive advice
- Ensure advice is accurate, compliant with policies, and personalized
- Think holistically about the student's goals and constraints

YOUR RESPONSIBILITIES AS COORDINATOR:
- Understand the student's query and underlying goals
- Determine which specialized agents can help
- Plan an efficient workflow that gets all necessary information
- Adapt the plan if intermediate results reveal new needs
- Synthesize agent outputs into coherent, actionable advice

COORDINATION PRINCIPLES:
1. Reason, don't match: Understand the problem deeply, don't just match keywords
2. Be efficient: Only activate agents that are truly needed
3. Be thorough: Don't miss important considerations
4. Be adaptive: Change the plan if new information emerges
5. Be explainable: Always explain your reasoning"""
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """Format conversation history."""
        if not history:
            return "No previous conversation."
        
        formatted = []
        for msg in history[-5:]:  # Last 5 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _format_student_profile(self, profile: Dict) -> str:
        """Format student profile."""
        if not profile:
            return "No student profile available."
        
        return json.dumps(profile, indent=2)
    
    def _extract_unique_agents(self, workflow_data: Dict) -> List[str]:
        """Extract unique agent names from workflow plan."""
        agents = set()
        
        # From execution order
        agents.update(workflow_data.get('execution_order', []))
        
        # From parallel stages
        for stage in workflow_data.get('parallel_stages', []):
            agents.update(stage)
        
        return list(agents)
    
    def _create_fallback_plan(self, query: str) -> WorkflowPlan:
        """Create a simple fallback plan if LLM parsing fails."""
        return WorkflowPlan(
            goal="Answer the student's query",
            reasoning="Fallback plan due to parsing error",
            agents=["programs_requirements"],
            execution_order=["programs_requirements"],
            parallel_stages=[],
            decision_points=[],
            expected_challenges=["Unknown due to fallback"],
            success_criteria="Provide some answer"
        )


# Example usage
if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    import httpx
    
    http_client = httpx.Client(verify=False, timeout=180.0)
    llm = ChatOpenAI(
        model="gpt-4-turbo", 
        temperature=0.3,
        http_client=http_client,
        request_timeout=180.0
    )
    coordinator = LLMDrivenCoordinator(llm)
    
    # Test query
    query = "I probably will get a D in 15-112 this semester. as a CS student, do I need to retake it next semester?"
    
    print("=" * 80)
    print("LLM-Driven Coordination")
    print("=" * 80)
    print(f"\nQuery: {query}\n")
    
    plan = coordinator.understand_and_plan(query)
    
    print("UNDERSTANDING:")
    print(json.dumps(plan.full_analysis.get('understanding', {}), indent=2))
    
    print("\nAGENT ANALYSIS:")
    print(json.dumps(plan.full_analysis.get('agent_analysis', {}), indent=2))
    
    print("\nWORKFLOW PLAN:")
    print(f"Goal: {plan.goal}")
    print(f"Reasoning: {plan.reasoning}")
    print(f"Execution Order: {' → '.join(plan.execution_order)}")
    print(f"Expected Challenges: {', '.join(plan.expected_challenges)}")
    print(f"Success Criteria: {plan.success_criteria}")
