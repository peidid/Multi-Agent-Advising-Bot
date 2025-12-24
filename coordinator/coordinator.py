"""
Coordinator / Orchestrator

Key Responsibilities:
- Intent classification & routing
- Workflow planning (dynamic)
- Conflict detection
- Negotiation management
- Answer synthesis
"""
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from blackboard.schema import (
    BlackboardState, Conflict, ConflictType, WorkflowStep, AgentOutput
)
import json
import re

class Coordinator:
    """Main orchestrator for multi-agent system."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.available_agents = [
            "programs_requirements",
            "course_scheduling",
            "policy_compliance"
        ]
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent to determine which agents are needed.
        """
        prompt = f"""Classify this academic advising query and determine which agents are needed.

Query: {query}

Available Agents:
- programs_requirements: For major/minor requirements, degree progress, plan validation
- course_scheduling: For course offerings, schedules, time conflicts
- policy_compliance: For university policies, compliance checking

Intent Types:
- check_requirements: Questions about requirements
- plan_semester: Planning courses for a semester
- add_minor: Adding a minor
- policy_question: Questions about policies
- validate_plan: Checking if a plan is valid
- general: General advising questions

Respond in JSON format:
{{
    "intent_type": "check_requirements" | "plan_semester" | "add_minor" | "policy_question" | "validate_plan" | "general",
    "required_agents": ["agent1", "agent2"],
    "priority": "high" | "medium" | "low",
    "reasoning": "Why these agents are needed"
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        try:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback
        return {
            "intent_type": "general",
            "required_agents": ["programs_requirements"],
            "priority": "medium",
            "reasoning": "Default fallback"
        }
    
    def plan_workflow(self, intent: Dict[str, Any]) -> List[str]:
        """
        Plan the workflow: which agents to call in what order.
        """
        required_agents = intent.get("required_agents", [])
        intent_type = intent.get("intent_type", "general")
        
        # Dynamic workflow planning
        if intent_type == "validate_plan" or intent_type == "plan_semester":
            # Full workflow: propose → check schedule → check compliance
            workflow = []
            if "programs_requirements" in required_agents:
                workflow.append("programs_requirements")
            if "course_scheduling" in required_agents:
                workflow.append("course_scheduling")
            if "policy_compliance" in required_agents:
                workflow.append("policy_compliance")
            return workflow
        elif intent_type == "add_minor":
            return [a for a in required_agents if a in ["programs_requirements", "policy_compliance"]]
        else:
            return required_agents
    
    def detect_conflicts(self, state: BlackboardState) -> List[Conflict]:
        """
        Detect conflicts between agent outputs.
        """
        agent_outputs = state.get("agent_outputs", {})
        conflicts = []
        
        # Check Policy agent for violations
        policy_output = agent_outputs.get("policy_compliance")
        if policy_output:
            hard_constraints = [c for c in policy_output.constraints if c.hard]
            high_risks = [r for r in policy_output.risks if r.severity == "high"]
            
            if hard_constraints:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HARD_VIOLATION,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"Plan violates policies: {[c.description for c in hard_constraints]}",
                    options=[]
                ))
            
            if high_risks:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HIGH_RISK,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"High-risk plan: {[r.description for r in high_risks]}",
                    options=[]
                ))
        
        # Check for trade-offs
        plan_options = state.get("plan_options", [])
        if len(plan_options) > 1:
            conflicts.append(Conflict(
                conflict_type=ConflictType.TRADE_OFF,
                affected_agents=["programs_requirements"],
                description="Multiple valid plan options available",
                options=[{"plan": p.dict() if hasattr(p, 'dict') else p} for p in plan_options]
            ))
        
        return conflicts
    
    def synthesize_answer(self, state: BlackboardState) -> str:
        """Synthesize final answer from all agent outputs."""
        agent_outputs = state.get("agent_outputs", {})
        user_query = state.get("user_query", "")
        conflicts = state.get("conflicts", [])
        
        # Combine agent outputs
        agent_summaries = []
        for agent_name, output in agent_outputs.items():
            agent_summaries.append(f"""
{agent_name.upper()}:
Answer: {output.answer}
Confidence: {output.confidence}
Policies: {', '.join(output.relevant_policies)}
Risks: {len(output.risks)}
""")
        
        conflicts_text = ""
        if conflicts:
            conflicts_text = "\nConflicts Detected:\n"
            for conflict in conflicts:
                conflicts_text += f"- {conflict.conflict_type.value}: {conflict.description}\n"
        
        prompt = f"""You are the Coordinator synthesizing answers from multiple specialized agents.

User Query: {user_query}

Agent Outputs:
{chr(10).join(agent_summaries)}
{conflicts_text}

Synthesize a coherent, helpful answer that:
1. Combines relevant information from all agents
2. Addresses conflicts if any
3. Provides clear, actionable advice
4. Cites policies when relevant
5. Is professional and friendly

Write a comprehensive answer (2-4 paragraphs).
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return response.content
    
    def manage_negotiation(self, state: BlackboardState) -> Dict[str, Any]:
        """
        Manage Proposal + Critique Protocol.
        
        Protocol:
        1. Programs Agent proposes plan
        2. Policy Agent critiques plan
        3. If conflicts, loop (max 3 iterations)
        """
        iteration = state.get("iteration_count", 0)
        max_iterations = 3
        
        agent_outputs = state.get("agent_outputs", {})
        
        # Step 1: Check if Programs agent has proposed
        if "programs_requirements" not in agent_outputs:
            return {
                "next_agent": "programs_requirements",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 2: Check if Policy agent has critiqued
        if "policy_compliance" not in agent_outputs:
            return {
                "next_agent": "policy_compliance",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 3: Detect conflicts
        conflicts = self.detect_conflicts(state)
        
        if conflicts:
            has_hard_violation = any(c.conflict_type == ConflictType.HARD_VIOLATION for c in conflicts)
            
            if iteration >= max_iterations:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["The proposed plan has conflicts. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT
                }
            
            if has_hard_violation:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["This plan violates university policies. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT,
                    "iteration_count": iteration + 1
                }
            else:
                # Soft conflicts - try to resolve
                return {
                    "conflicts": conflicts,
                    "workflow_step": WorkflowStep.NEGOTIATION,
                    "next_agent": "programs_requirements",
                    "iteration_count": iteration + 1
                }
        
        # No conflicts - ready to synthesize
        return {
            "workflow_step": WorkflowStep.SYNTHESIS
        }

