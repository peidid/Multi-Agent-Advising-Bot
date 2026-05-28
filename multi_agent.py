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
        workflow_complete_event,
        coordinator_evaluation_event,
        agent_rerun_start_event,
        agent_rerun_complete_event,
        agent_output_event,
    )
    STREAMING_AVAILABLE = True
except ImportError:
    STREAMING_AVAILABLE = False
    def emit_event(event): pass

# Memory resolution event is optional — handle older streaming/events versions.
try:
    from streaming.events import coordinator_memory_resolved_event
    MEMORY_EVENT_AVAILABLE = True
except ImportError:
    MEMORY_EVENT_AVAILABLE = False

# Greeting short-circuit event is optional too.
try:
    from streaming.events import coordinator_greeting_event
    GREETING_EVENT_AVAILABLE = True
except ImportError:
    GREETING_EVENT_AVAILABLE = False

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

# ============================================================================
# COORDINATOR-EVALUATED RE-RETRIEVAL SETTINGS (Chat Mode)
# ============================================================================
# The coordinator evaluates all agent outputs holistically and decides
# if more information is needed. This is better than agent self-reported
# confidence because the coordinator has full context.

MAX_EVALUATION_ROUNDS = 3    # Max rounds of coordinator evaluation
ENHANCED_K = 10              # k value for enhanced retrieval (vs default 5-8)


def execute_single_agent(agent_name: str, state: BlackboardState, enhanced_k: int = None) -> tuple:
    """
    Execute a single agent and return (agent_name, output, execution_time).
    Used by ThreadPoolExecutor for parallel execution.

    Args:
        agent_name: Name of the agent to execute
        state: Current blackboard state
        enhanced_k: Optional enhanced k value for retrieval (for confidence re-retrieval)
    """
    start_time = time.time()
    agent = AGENT_REGISTRY.get(agent_name)
    if agent is None:
        return (agent_name, None, 0.0)

    # If enhanced_k is specified, add it to state for agent to use
    if enhanced_k is not None:
        state = dict(state)  # Make a copy
        state["retrieval_k"] = enhanced_k

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

        # =====================================================================
        # TOP-LAYER TRIAGE — fast binary greeting check.
        # Single small-model LLM call (~150-300ms). If the message is purely
        # social (hi/thanks/bye), respond immediately and skip the entire
        # pipeline (resolver, classifier, agents, evaluation, synthesis).
        # Failure mode is safe: on any error this returns is_greeting=false
        # and the full pipeline runs as usual.
        # =====================================================================
        triage_start = time.time()
        triage = coordinator.triage_greeting(user_query)
        triage_time = time.time() - triage_start

        if triage.get("is_greeting"):
            reply = triage.get("reply") or coordinator._DEFAULT_GREETING_REPLY
            phase_timing = state.get("phase_timing", {})
            phase_timing["triage"] = round(triage_time, 2)
            phase_timing["total"] = round(triage_time, 2)

            # Emit streaming events so the UI knows what happened.
            if STREAMING_AVAILABLE and GREETING_EVENT_AVAILABLE:
                try:
                    emit_event(coordinator_greeting_event(reply, triage_time))
                except Exception:
                    pass
            if STREAMING_AVAILABLE:
                emit_event(workflow_complete_event([], triage_time))

            return {
                "messages": [HumanMessage(content=reply)],
                "workflow_step": WorkflowStep.COMPLETE,
                "active_agents": [],
                "phase_timing": phase_timing,
            }

        # Track intent classification time (includes the short-term memory
        # resolver, which runs inside classify_intent before routing).
        intent_start = time.time()
        intent = coordinator.classify_intent(
            user_query,
            conversation_history=conversation_history,
            student_profile=student_profile
        )
        workflow = coordinator.plan_workflow(intent)
        intent_time = time.time() - intent_start

        # Record triage time on the phase timing too — it ran for every turn.
        phase_timing = state.get("phase_timing", {})
        phase_timing["triage"] = round(triage_time, 2)
        state["phase_timing"] = phase_timing

        # Extract resolved short-term memory produced by the coordinator.
        resolved_context = intent.get("resolved_context") or {}

        # Emit memory-resolution event so the UI can show what was resolved
        # (this is independent of the routing event below).
        if STREAMING_AVAILABLE and MEMORY_EVENT_AVAILABLE and resolved_context:
            try:
                emit_event(coordinator_memory_resolved_event(resolved_context))
            except Exception:
                pass

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
            "context_text": intent.get("context_text", ""),
            # Pass specific task instructions for each agent
            "agent_tasks": intent.get("agent_tasks", {}),
            # Pass short-term memory (resolved query + focus entities)
            "resolved_context": resolved_context,
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

    Uses COORDINATOR-EVALUATED sufficiency checking:
    1. Run all agents in parallel (round 1)
    2. Coordinator evaluates if outputs are sufficient
    3. If not, coordinator specifies which agents to re-run with enhanced k
    4. Maximum 3 rounds total

    This is better than agent self-reported confidence because the coordinator
    has full context of all outputs and can make holistic decisions.
    """
    active_agents = state.get("active_agents", [])
    user_query = state.get("user_query", "")

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

    # Track execution times and evaluation rounds
    execution_times = {}
    agent_outputs = {}
    evaluation_history = []  # Track coordinator evaluation decisions

    # Start timing
    parallel_start = time.time()

    # =========================================================================
    # ROUND 1: Initial parallel execution (default k)
    # =========================================================================
    print(f"[Chat Mode] Round 1: Executing {len(active_agents)} agents in parallel")

    with ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
        future_to_agent = {
            executor.submit(execute_single_agent, agent_name, state): agent_name
            for agent_name in active_agents
        }

        for future in as_completed(future_to_agent):
            agent_name, output, exec_time = future.result()

            if output is not None:
                agent_outputs[agent_name] = output
                execution_times[agent_name] = round(exec_time, 2)

    # =========================================================================
    # COORDINATOR EVALUATION LOOP (max 3 rounds)
    # Uses GPT-5.2 for holistic evaluation and semantic feedback
    # =========================================================================
    for round_num in range(1, MAX_EVALUATION_ROUNDS + 1):
        # Coordinator evaluates all outputs using GPT-5.2
        print(f"\n{'='*60}")
        print(f"[Coordinator Evaluation] Round {round_num}/{MAX_EVALUATION_ROUNDS}")
        print(f"{'='*60}")

        eval_start = time.time()
        # Get student profile for validation (completed courses, etc.)
        student_profile = state.get("student_profile", {})
        evaluation = coordinator.evaluate_outputs_for_sufficiency(
            user_query=user_query,
            agent_outputs=agent_outputs,
            current_round=round_num,
            student_profile=student_profile
        )
        eval_time = time.time() - eval_start

        # Extract evaluation details
        quality_score = evaluation.get("quality_score", 0)
        agent_feedback = evaluation.get("agent_feedback", {})
        missing_info = evaluation.get("missing_info", [])

        # Store comprehensive evaluation history
        evaluation_history.append({
            "round": round_num,
            "sufficient": evaluation["sufficient"],
            "quality_score": quality_score,
            "agents_to_rerun": evaluation.get("agents_to_rerun", []),
            "agent_feedback": agent_feedback,
            "reasoning": evaluation.get("reasoning", ""),
            "missing_info": missing_info,
            "eval_time": round(eval_time, 2)
        })

        # Display detailed evaluation results
        print(f"\n📊 Quality Score: {quality_score}/100")
        print(f"📝 Decision: {'✅ SUFFICIENT' if evaluation['sufficient'] else '🔄 NEED MORE INFO'}")
        print(f"💭 Reasoning: {evaluation.get('reasoning', 'N/A')}")

        # Display per-agent feedback
        if agent_feedback:
            print(f"\n📋 Agent Feedback:")
            for agent_name, feedback in agent_feedback.items():
                agent_score = feedback.get("score", "N/A")
                print(f"   • {agent_name}: {agent_score}/100")
                if feedback.get("strengths"):
                    print(f"     ✓ Strengths: {', '.join(feedback['strengths'][:2])}")
                if feedback.get("gaps"):
                    print(f"     ✗ Gaps: {', '.join(feedback['gaps'][:2])}")
                if feedback.get("guidance"):
                    print(f"     → Guidance: {feedback['guidance'][:100]}...")

        if missing_info:
            print(f"\n❓ Missing Info: {', '.join(missing_info[:3])}")

        # Emit comprehensive streaming event for real-time UI
        if STREAMING_AVAILABLE:
            emit_event(coordinator_evaluation_event(
                round_num=round_num,
                sufficient=evaluation["sufficient"],
                quality_score=quality_score,
                agent_feedback=agent_feedback,
                reasoning=evaluation.get("reasoning", ""),
                agents_to_rerun=evaluation.get("agents_to_rerun", []),
                eval_time=round(eval_time, 2)
            ))

        if evaluation["sufficient"]:
            # Ready for synthesis
            print(f"\n✅ Outputs sufficient after round {round_num} (score: {quality_score}/100)")
            break

        if round_num >= MAX_EVALUATION_ROUNDS:
            # Max rounds reached, proceed with what we have
            print(f"\n⏱️ Max rounds ({MAX_EVALUATION_ROUNDS}) reached, proceeding with synthesis")
            break

        # Re-run specified agents with enhanced k and coordinator feedback
        agents_to_rerun = evaluation.get("agents_to_rerun", [])
        if not agents_to_rerun:
            # Coordinator said insufficient but didn't specify agents - proceed anyway
            print("\n⚠️ No agents specified to re-run, proceeding with synthesis")
            break

        print(f"\n🔄 Round {round_num + 1}: Re-running {agents_to_rerun} with enhanced k={ENHANCED_K}")

        # Emit streaming event for re-retrieval
        if STREAMING_AVAILABLE:
            emit_event(agent_rerun_start_event(
                round_num=round_num + 1,
                agents=agents_to_rerun,
                enhanced_k=ENHANCED_K
            ))

        # Prepare state with coordinator feedback for agents
        rerun_state = dict(state)
        rerun_state["retrieval_k"] = ENHANCED_K
        rerun_state["coordinator_feedback"] = agent_feedback  # Pass feedback to agents

        with ThreadPoolExecutor(max_workers=len(agents_to_rerun)) as executor:
            future_to_agent = {
                executor.submit(execute_single_agent, agent_name, rerun_state, ENHANCED_K): agent_name
                for agent_name in agents_to_rerun
            }

            for future in as_completed(future_to_agent):
                agent_name, output, exec_time = future.result()

                if output is not None:
                    # Update with new output (enhanced retrieval)
                    agent_outputs[agent_name] = output
                    execution_times[agent_name] = round(
                        execution_times.get(agent_name, 0) + exec_time, 2
                    )
                    guidance = agent_feedback.get(agent_name, {}).get("guidance", "")
                    print(f"   ✓ {agent_name}: re-executed with k={ENHANCED_K}")
                    if guidance:
                        print(f"     Applied guidance: {guidance[:80]}...")

                    # Emit streaming events for agent completion
                    if STREAMING_AVAILABLE:
                        # Emit updated agent output so frontend can display new answer
                        risks = [{"type": r.type, "severity": r.severity, "description": r.description}
                                 for r in (output.risks or [])]
                        emit_event(agent_output_event(
                            agent_name,
                            answer=output.answer,
                            confidence=output.confidence,
                            risks=risks,
                            relevant_policies=output.relevant_policies or []
                        ))
                        # Emit rerun complete event
                        emit_event(agent_rerun_complete_event(
                            agent_name=agent_name,
                            round_num=round_num + 1,
                            execution_time=round(exec_time, 2)
                        ))

    # Aggregate final risks and constraints
    all_risks = list(state.get("risks", []))
    all_constraints = list(state.get("constraints", []))
    plan_options = []

    for output in agent_outputs.values():
        all_risks.extend(output.risks)
        all_constraints.extend(output.constraints)
        if output.plan_options:
            plan_options.extend(output.plan_options)

    # Calculate total parallel time
    parallel_total = time.time() - parallel_start

    # Calculate theoretical sequential time
    sequential_total = sum(execution_times.values())

    # Calculate speedup factor
    speedup = sequential_total / parallel_total if parallel_total > 0 else 1.0

    # Extract final quality score from last evaluation
    final_quality_score = evaluation_history[-1].get("quality_score", 0) if evaluation_history else 0
    final_agent_feedback = evaluation_history[-1].get("agent_feedback", {}) if evaluation_history else {}

    # Build execution metadata with comprehensive evaluation info
    execution_metadata = {
        "execution_mode": "parallel_with_coordinator_evaluation",
        "agents_executed": list(agent_outputs.keys()),
        "execution_times": execution_times,
        "total_execution_time": round(parallel_total, 2),
        "sequential_equivalent": round(sequential_total, 2),
        "parallel_speedup": round(speedup, 2),
        "evaluation_rounds": len(evaluation_history),
        "final_quality_score": final_quality_score,
        "final_agent_feedback": final_agent_feedback,
        "evaluation_history": evaluation_history,
        "final_confidences": {
            name: round(output.confidence, 2)
            for name, output in agent_outputs.items()
        }
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
        "workflow_step": WorkflowStep.AGENT_EXECUTION,
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

    # Greeting short-circuit: coordinator already produced the reply, end now.
    if workflow_step == WorkflowStep.COMPLETE:
        return END
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
# BUILD WORKFLOW (Parallel Execution with Coordinator Evaluation)
# ============================================================================
#
# Flow:
#   START → Coordinator (Intent) → Parallel Agents → [Coordinator Eval] → Synthesize → END
#                                        ↓                    ↓
#                           [All agents run in parallel]   [Evaluate sufficiency]
#                                                               ↓
#                                                    [If insufficient: re-run
#                                                     specified agents with k=10]
#                                                    [Max 3 rounds]
#
# The coordinator evaluates all agent outputs holistically before synthesis.
# This is better than agent self-reported confidence because the coordinator
# has full context of all outputs and can make better decisions.
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
    print("EXECUTION METADATA (Parallel with Coordinator Evaluation):")
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

        # Print final quality score
        final_score = exec_meta.get('final_quality_score', 0)
        print(f"\n  📊 Final Quality Score: {final_score}/100")

        # Print coordinator evaluation history
        eval_history = exec_meta.get('evaluation_history', [])
        if eval_history:
            print(f"\n  Coordinator Evaluation Rounds: {len(eval_history)}")
            for eval_round in eval_history:
                score = eval_round.get('quality_score', 'N/A')
                print(f"    Round {eval_round['round']}: {'✓ Sufficient' if eval_round['sufficient'] else '✗ Need more'} (Score: {score})")
                print(f"      Reasoning: {eval_round['reasoning'][:100]}...")
                if eval_round.get('agents_to_rerun'):
                    print(f"      Re-run: {eval_round['agents_to_rerun']}")
                # Print agent feedback summary
                agent_feedback = eval_round.get('agent_feedback', {})
                if agent_feedback:
                    print("      Agent Scores:")
                    for agent, fb in agent_feedback.items():
                        agent_score = fb.get('score', 'N/A')
                        gaps = fb.get('gaps', [])
                        print(f"        - {agent}: {agent_score}/100", end="")
                        if gaps:
                            print(f" (gaps: {', '.join(gaps[:2])})")
                        else:
                            print()

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

