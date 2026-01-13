"""
Main Multi-Agent Workflow
Implements dynamic routing with Coordinator managing agent execution.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from blackboard.schema import BlackboardState, WorkflowStep
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from coordinator.coordinator import Coordinator
from config import print_model_config

# Print model configuration on startup
print_model_config()
print()

# Initialize components
# Coordinator now uses LLM-driven coordination by default
coordinator = Coordinator()

programs_agent = ProgramsRequirementsAgent()
courses_agent = CourseSchedulingAgent()
policy_agent = PolicyComplianceAgent()

# ============================================================================
# NODES
# ============================================================================

def coordinator_node(state: BlackboardState) -> Dict[str, Any]:
    """Coordinator node: Classifies intent, plans workflow."""
    user_query = state.get("user_query", "")
    workflow_step = state.get("workflow_step", WorkflowStep.INITIAL)
    
    if workflow_step == WorkflowStep.INITIAL:
        intent = coordinator.classify_intent(user_query)
        workflow = coordinator.plan_workflow(intent)
        
        return {
            "active_agents": workflow,
            "workflow_step": WorkflowStep.AGENT_EXECUTION,
            "next_agent": workflow[0] if workflow else None,
            "user_goal": intent.get("intent_type", "")
        }
    
    elif workflow_step == WorkflowStep.NEGOTIATION:
        negotiation_result = coordinator.manage_negotiation(state)
        return negotiation_result
    
    else:
        # After agents execute, check if more agents needed or synthesize
        active_agents = state.get("active_agents", [])
        agent_outputs = state.get("agent_outputs", {})
        executed_agents = list(agent_outputs.keys())
        
        remaining = [a for a in active_agents if a not in executed_agents]
        if remaining:
            # More agents to execute
            return {
                "next_agent": remaining[0],
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        else:
            # All agents done - check conflicts or synthesize
            conflicts = coordinator.detect_conflicts(state)
            if conflicts:
                return {
                    "conflicts": conflicts,
                    "workflow_step": WorkflowStep.CONFLICT_RESOLUTION
                }
            else:
                return {
                    "workflow_step": WorkflowStep.SYNTHESIS
                }

def programs_node(state: BlackboardState) -> Dict[str, Any]:
    """Programs agent execution."""
    output = programs_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["programs_requirements"] = output
    
    plan_options = []
    if output.plan_options:
        plan_options = output.plan_options
    
    return {
        "agent_outputs": agent_outputs,
        "plan_options": plan_options,
        "risks": state.get("risks", []) + output.risks,
        "constraints": state.get("constraints", []) + output.constraints
    }

def courses_node(state: BlackboardState) -> Dict[str, Any]:
    """Courses agent execution."""
    output = courses_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["course_scheduling"] = output
    
    return {
        "agent_outputs": agent_outputs,
        "risks": state.get("risks", []) + output.risks
    }

def policy_node(state: BlackboardState) -> Dict[str, Any]:
    """Policy agent execution."""
    output = policy_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["policy_compliance"] = output
    
    return {
        "agent_outputs": agent_outputs,
        "risks": state.get("risks", []) + output.risks,
        "constraints": state.get("constraints", []) + output.constraints
    }

def synthesize_node(state: BlackboardState) -> Dict[str, Any]:
    """Synthesize final answer."""
    answer = coordinator.synthesize_answer(state)
    
    return {
        "messages": [HumanMessage(content=answer)],
        "workflow_step": WorkflowStep.COMPLETE
    }

# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_after_coordinator(state: BlackboardState) -> str:
    """Route after coordinator decides next step."""
    workflow_step = state.get("workflow_step")
    next_agent = state.get("next_agent")
    
    if workflow_step == WorkflowStep.SYNTHESIS:
        return "synthesize"
    elif workflow_step == WorkflowStep.USER_INPUT:
        return END
    elif next_agent == "programs_requirements":
        return "programs"
    elif next_agent == "course_scheduling":
        return "courses"
    elif next_agent == "policy_compliance":
        return "policy"
    else:
        return "synthesize"

def route_after_agent(state: BlackboardState) -> str:
    """Route after agent execution."""
    active_agents = state.get("active_agents", [])
    agent_outputs = state.get("agent_outputs", {})
    executed_agents = list(agent_outputs.keys())
    
    # Check if all agents have executed
    if len(executed_agents) >= len(active_agents):
        # All agents done - check for conflicts or synthesize
        conflicts = state.get("conflicts", [])
        if conflicts:
            return "coordinator"
        else:
            return "synthesize"
    else:
        # More agents needed - go back to coordinator to route to next agent
        remaining = [a for a in active_agents if a not in executed_agents]
        if remaining:
            return "coordinator"
        else:
            return "synthesize"

# ============================================================================
# BUILD WORKFLOW
# ============================================================================

workflow = StateGraph(BlackboardState)

# Add nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("programs", programs_node)
workflow.add_node("courses", courses_node)
workflow.add_node("policy", policy_node)
workflow.add_node("synthesize", synthesize_node)

# Add edges
workflow.add_edge(START, "coordinator")
workflow.add_conditional_edges("coordinator", route_after_coordinator)
workflow.add_conditional_edges("programs", route_after_agent)
workflow.add_conditional_edges("courses", route_after_agent)
workflow.add_conditional_edges("policy", route_after_agent)
workflow.add_edge("synthesize", END)

# Compile
app = workflow.compile()

# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    initial_state = {
        "user_query": "Can I add a CS minor as an IS student?",
        "student_profile": {"major": ["IS"], "gpa": 3.5},
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "plan_options": [],
        "conflicts": [],
        "open_questions": [],
        "messages": [HumanMessage(content="Can I add a CS minor as an IS student?")],
        "active_agents": [],
        "workflow_step": WorkflowStep.INITIAL,
        "iteration_count": 0,
        "next_agent": None,
        "user_goal": None
    }
    
    result = app.invoke(initial_state)
    
    print("=" * 70)
    print("FINAL ANSWER:")
    print("=" * 70)
    print(result["messages"][-1].content)
    print("\n" + "=" * 70)
    print("AGENT OUTPUTS:")
    for agent_name, output in result.get("agent_outputs", {}).items():
        print(f"\n{agent_name}:")
        print(f"  Answer: {output.answer[:200]}...")
        print(f"  Confidence: {output.confidence}")

