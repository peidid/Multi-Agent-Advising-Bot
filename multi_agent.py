"""
Main Multi-Agent Workflow
Implements dynamic routing with Coordinator managing agent execution.
Supports PARALLEL agent execution for improved performance.
Includes real-time streaming events for UI visibility.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from blackboard.schema import BlackboardState, WorkflowStep
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from agents.planning_agent import AcademicPlanningAgent
from coordinator.coordinator import Coordinator
from config import print_model_config

# Import streaming module (optional - graceful fallback if not available)
try:
    from streaming.callback import emit_event
    from streaming.events import (
        coordinator_thinking_event,
        coordinator_routing_event,
        synthesis_start_event,
        synthesis_complete_event,
        workflow_complete_event
    )
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False
    def emit_event(event): pass

# Print model configuration on startup
print_model_config()
print()

# Initialize components
# Coordinator now uses LLM-driven coordination by default
coordinator = Coordinator()

programs_agent = ProgramsRequirementsAgent()
courses_agent = CourseSchedulingAgent()
policy_agent = PolicyComplianceAgent()
planning_agent = AcademicPlanningAgent()

# ============================================================================
# AGENT REGISTRY (for parallel execution)
# ============================================================================

AGENT_REGISTRY = {
    "programs_requirements": programs_agent,
    "course_scheduling": courses_agent,
    "policy_compliance": policy_agent,
    "academic_planning": planning_agent
}


def execute_single_agent(agent_name: str, state: BlackboardState) -> tuple:
    """
    Execute a single agent and return (agent_name, output, execution_time).
    Used by ThreadPoolExecutor for parallel execution.
    """
    start_time = time.time()
    agent = AGENT_REGISTRY.get(agent_name)
    if agent is None:
        return (agent_name, None, 0.0)

    output = agent.execute(state)
    execution_time = time.time() - start_time
    return (agent_name, output, execution_time)


# ============================================================================
# NODES
# ============================================================================

def coordinator_node(state: BlackboardState) -> Dict[str, Any]:
    """Coordinator node: Classifies intent, plans workflow. Emits streaming events."""
    user_query = state.get("user_query", "")
    workflow_step = state.get("workflow_step", WorkflowStep.INITIAL)
    conversation_history = state.get("conversation_history", [])
    student_profile = state.get("student_profile", {})

    if workflow_step == WorkflowStep.INITIAL:
        # Emit thinking event
        if STREAMING_AVAILABLE:
            emit_event(coordinator_thinking_event("Analyzing your question..."))

        # Track intent classification time
        intent_start = time.time()
        # Pass conversation history and profile for context-aware classification
        intent = coordinator.classify_intent(
            user_query,
            conversation_history=conversation_history,
            student_profile=student_profile
        )
        workflow = coordinator.plan_workflow(intent)
        intent_time = time.time() - intent_start

        # Emit routing event
        if STREAMING_AVAILABLE:
            reasoning = intent.get("reasoning", "")
            emit_event(coordinator_routing_event(workflow, reasoning))

        # Initialize phase timing
        phase_timing = state.get("phase_timing", {})
        phase_timing["intent_classification"] = round(intent_time, 2)

        return {
            "active_agents": workflow,
            "workflow_step": WorkflowStep.AGENT_EXECUTION,
            "next_agent": None,  # No longer used in parallel mode
            "user_goal": intent.get("intent_type", ""),
            "phase_timing": phase_timing,
            # Pass context_text to agents
            "context_text": intent.get("context_text", "")
        }

    elif workflow_step == WorkflowStep.NEGOTIATION:
        negotiation_result = coordinator.manage_negotiation(state)
        return negotiation_result

    else:
        # After parallel execution, check conflicts or synthesize
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


def parallel_agents_node(state: BlackboardState) -> Dict[str, Any]:
    """
    Execute ALL active agents in PARALLEL using ThreadPoolExecutor.
    This is the key optimization - agents run simultaneously instead of sequentially.
    """
    active_agents = state.get("active_agents", [])

    if not active_agents:
        return {
            "workflow_step": WorkflowStep.SYNTHESIS,
            "execution_metadata": {
                "execution_mode": "parallel",
                "agents_executed": [],
                "execution_times": {},
                "total_execution_time": 0.0,
                "parallel_speedup": None
            }
        }

    # Track execution times
    execution_times = {}
    agent_outputs = {}
    all_risks = list(state.get("risks", []))
    all_constraints = list(state.get("constraints", []))
    plan_options = []

    # Start timing
    parallel_start = time.time()

    # Execute agents in parallel
    with ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
        # Submit all agents simultaneously
        future_to_agent = {
            executor.submit(execute_single_agent, agent_name, state): agent_name
            for agent_name in active_agents
        }

        # Collect results as they complete
        for future in as_completed(future_to_agent):
            agent_name, output, exec_time = future.result()

            if output is not None:
                agent_outputs[agent_name] = output
                execution_times[agent_name] = round(exec_time, 2)

                # Aggregate risks and constraints
                all_risks.extend(output.risks)
                all_constraints.extend(output.constraints)

                # Collect plan options
                if output.plan_options:
                    plan_options.extend(output.plan_options)

    # Calculate total parallel time
    parallel_total = time.time() - parallel_start

    # Calculate theoretical sequential time (sum of all agent times)
    sequential_total = sum(execution_times.values())

    # Calculate speedup factor
    speedup = sequential_total / parallel_total if parallel_total > 0 else 1.0

    # Build execution metadata
    execution_metadata = {
        "execution_mode": "parallel",
        "agents_executed": list(agent_outputs.keys()),
        "execution_times": execution_times,
        "total_execution_time": round(parallel_total, 2),
        "sequential_equivalent": round(sequential_total, 2),
        "parallel_speedup": round(speedup, 2)
    }

    # Update phase timing
    phase_timing = state.get("phase_timing", {})
    phase_timing["parallel_agents"] = round(parallel_total, 2)
    phase_timing["parallel_agents_detail"] = execution_times

    return {
        "agent_outputs": agent_outputs,
        "risks": all_risks,
        "constraints": all_constraints,
        "plan_options": plan_options if plan_options else state.get("plan_options", []),
        "workflow_step": WorkflowStep.AGENT_EXECUTION,  # Keep for routing
        "execution_metadata": execution_metadata,
        "phase_timing": phase_timing
    }


def synthesize_node(state: BlackboardState) -> Dict[str, Any]:
    """Synthesize final answer. Emits streaming events."""
    # Emit synthesis start event
    if STREAMING_AVAILABLE:
        emit_event(synthesis_start_event())

    # Track synthesis time
    synthesis_start = time.time()
    answer = coordinator.synthesize_answer(state)
    synthesis_time = time.time() - synthesis_start

    # Update phase timing
    phase_timing = state.get("phase_timing", {})
    phase_timing["synthesis"] = round(synthesis_time, 2)

    # Calculate total time (filter to only numeric values, excluding nested dicts like parallel_agents_detail)
    total_time = sum(v for v in phase_timing.values() if isinstance(v, (int, float)))
    phase_timing["total"] = round(total_time, 2)

    # Emit synthesis complete and workflow complete events
    if STREAMING_AVAILABLE:
        emit_event(synthesis_complete_event(answer[:200] if answer else ""))
        agents_used = list(state.get("agent_outputs", {}).keys())
        emit_event(workflow_complete_event(agents_used, total_time))

    return {
        "messages": [HumanMessage(content=answer)],
        "workflow_step": WorkflowStep.COMPLETE,
        "phase_timing": phase_timing
    }

# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_after_coordinator(state: BlackboardState) -> str:
    """Route after coordinator decides next step."""
    workflow_step = state.get("workflow_step")
    active_agents = state.get("active_agents", [])

    if workflow_step == WorkflowStep.SYNTHESIS:
        return "synthesize"
    elif workflow_step == WorkflowStep.USER_INPUT:
        return END
    elif workflow_step == WorkflowStep.AGENT_EXECUTION and active_agents:
        # Route to parallel execution
        return "parallel_agents"
    else:
        return "synthesize"


def route_after_parallel(state: BlackboardState) -> str:
    """Route after parallel agent execution - check conflicts or synthesize."""
    # Check for conflicts
    conflicts = coordinator.detect_conflicts(state)
    if conflicts:
        # Store conflicts and go back to coordinator for resolution
        return "coordinator"
    else:
        return "synthesize"

# ============================================================================
# BUILD WORKFLOW (Parallel Execution)
# ============================================================================
#
# New Flow (Parallel):
#   START → Coordinator → Parallel Agents (all at once) → Synthesize → END
#                              ↓
#                    [Programs, Courses, Policy, Planning]
#                         (executed simultaneously)
#
# This replaces the old sequential flow:
#   START → Coordinator → Agent1 → Coordinator → Agent2 → ... → Synthesize → END
#

workflow = StateGraph(BlackboardState)

# Add nodes (simplified - only 3 main nodes now)
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("parallel_agents", parallel_agents_node)
workflow.add_node("synthesize", synthesize_node)

# Add edges
workflow.add_edge(START, "coordinator")
workflow.add_conditional_edges("coordinator", route_after_coordinator)
workflow.add_conditional_edges("parallel_agents", route_after_parallel)
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
        "user_goal": None,
        "execution_metadata": None,
        "phase_timing": {}
    }

    print("=" * 70)
    print("PARALLEL AGENT EXECUTION TEST")
    print("=" * 70)

    start_time = time.time()
    result = app.invoke(initial_state)
    total_time = time.time() - start_time

    print("\n" + "=" * 70)
    print("EXECUTION METADATA (Parallel):")
    print("=" * 70)
    exec_meta = result.get("execution_metadata", {})
    if exec_meta:
        print(f"  Mode: {exec_meta.get('execution_mode', 'unknown')}")
        print(f"  Agents Executed: {', '.join(exec_meta.get('agents_executed', []))}")
        print(f"  Individual Times:")
        for agent, t in exec_meta.get('execution_times', {}).items():
            print(f"    - {agent}: {t}s")
        print(f"  Parallel Total: {exec_meta.get('total_execution_time', 0)}s")
        print(f"  Sequential Equivalent: {exec_meta.get('sequential_equivalent', 0)}s")
        print(f"  Speedup: {exec_meta.get('parallel_speedup', 1.0)}x")
    print(f"  Overall Total (incl. coordinator): {total_time:.2f}s")

    print("\n" + "=" * 70)
    print("FINAL ANSWER:")
    print("=" * 70)
    print(result["messages"][-1].content)

    print("\n" + "=" * 70)
    print("AGENT OUTPUTS:")
    for agent_name, output in result.get("agent_outputs", {}).items():
        print(f"\n{agent_name}:")
        print(f"  Answer: {output.answer[:200]}...")
        print(f"  Confidence: {output.confidence}")

