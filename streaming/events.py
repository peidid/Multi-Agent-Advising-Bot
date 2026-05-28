"""
Streaming event types for real-time updates.
"""
from enum import Enum
from typing import Optional, Any, Dict
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


class EventType(str, Enum):
    """Types of streaming events."""
    # Workflow level
    WORKFLOW_START = "workflow_start"
    WORKFLOW_COMPLETE = "workflow_complete"

    # Coordinator events
    COORDINATOR_THINKING = "coordinator_thinking"
    COORDINATOR_ROUTING = "coordinator_routing"
    COORDINATOR_CONFLICT = "coordinator_conflict"
    COORDINATOR_MEMORY_RESOLVED = "coordinator_memory_resolved"

    # Agent lifecycle
    AGENT_START = "agent_start"
    AGENT_RETRIEVING = "agent_retrieving"
    AGENT_THINKING = "agent_thinking"
    AGENT_OUTPUT = "agent_output"  # Full agent response available for streaming display
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"

    # Synthesis events
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_STREAMING = "synthesis_streaming"  # Token-by-token output
    SYNTHESIS_COMPLETE = "synthesis_complete"

    # General
    STATUS = "status"
    ERROR = "error"

    # Coordinator Evaluation events (for chat mode)
    COORDINATOR_EVALUATION = "coordinator_evaluation"
    AGENT_RERUN_START = "agent_rerun_start"
    AGENT_RERUN_COMPLETE = "agent_rerun_complete"

    # Planning Mode events
    PLANNING_SESSION_START = "planning_session_start"
    PLANNING_ROUND_START = "planning_round_start"
    PLANNING_PROPOSING = "planning_proposing"
    PLANNING_PROPOSAL = "planning_proposal"
    PLANNING_CRITIQUING = "planning_critiquing"
    PLANNING_CRITIQUE = "planning_critique"
    PLANNING_ROUND_COMPLETE = "planning_round_complete"
    PLANNING_COMPLETE = "planning_complete"


class AgentPhase(str, Enum):
    """Phases within agent execution."""
    STARTING = "starting"
    RETRIEVING = "retrieving"  # RAG retrieval
    ANALYZING = "analyzing"    # Processing context
    GENERATING = "generating"  # LLM generation
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamEvent:
    """
    A streaming event that can be sent to the frontend.

    Designed to be serializable to JSON for SSE transmission.
    """
    event_type: EventType
    agent_name: Optional[str] = None
    phase: Optional[AgentPhase] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.event_type.value,
            "timestamp": self.timestamp,
            "message": self.message,
        }
        if self.agent_name:
            result["agent"] = self.agent_name
        if self.phase:
            result["phase"] = self.phase.value
        if self.data:
            result["data"] = self.data
        return result

    def to_sse(self) -> str:
        """Format as Server-Sent Event."""
        return f"data: {json.dumps(self.to_dict())}\n\n"


# Pre-built event factories for common events
def workflow_start_event(query: str) -> StreamEvent:
    return StreamEvent(
        event_type=EventType.WORKFLOW_START,
        message="Starting to process your question...",
        data={"query": query[:100]}  # Truncate for display
    )


def coordinator_thinking_event(message: str = "Analyzing your question...") -> StreamEvent:
    return StreamEvent(
        event_type=EventType.COORDINATOR_THINKING,
        agent_name="coordinator",
        message=message
    )


def coordinator_memory_resolved_event(resolved_context: Dict[str, Any]) -> StreamEvent:
    """
    Emitted after the coordinator's short-term memory resolves the current turn.

    Surfaces pronoun expansion, focus entities, and topic continuity to the UI
    so users can see exactly how the system interpreted their follow-up question.
    """
    rc = resolved_context or {}
    resolved_query = (rc.get("resolved_query") or "").strip()
    fe = rc.get("focus_entities") or {}
    continuity = rc.get("topic_continuity", "new_topic")
    unresolved = rc.get("unresolved_references") or []
    needs_clar = bool(rc.get("needs_clarification", False))
    confidence = rc.get("confidence", 0.0)

    # Short, human-readable summary for the UI ticker.
    parts = []
    if continuity != "new_topic":
        parts.append(f"topic={continuity}")
    if fe.get("courses"):
        parts.append(f"courses={','.join(fe['courses'])}")
    if fe.get("programs"):
        parts.append(f"programs={','.join(fe['programs'])}")
    if fe.get("semesters"):
        parts.append(f"semesters={','.join(fe['semesters'])}")
    if unresolved:
        parts.append(f"unresolved={','.join(unresolved)}")
    summary = "; ".join(parts) if parts else "no references to resolve"

    return StreamEvent(
        event_type=EventType.COORDINATOR_MEMORY_RESOLVED,
        agent_name="coordinator",
        message=f"Short-term memory resolved ({summary})",
        data={
            "resolved_query": resolved_query,
            "focus_entities": fe,
            "topic_continuity": continuity,
            "prior_facts_summary": rc.get("prior_facts_summary", ""),
            "unresolved_references": unresolved,
            "needs_clarification": needs_clar,
            "confidence": confidence,
        }
    )


def coordinator_routing_event(agents: list, reasoning: str = "") -> StreamEvent:
    agent_names = {
        "programs_requirements": "Programs & Requirements",
        "course_scheduling": "Course & Scheduling",
        "policy_compliance": "Policy & Compliance",
        "academic_planning": "Academic Planning"
    }
    friendly_names = [agent_names.get(a, a) for a in agents]
    return StreamEvent(
        event_type=EventType.COORDINATOR_ROUTING,
        agent_name="coordinator",
        message=f"Routing to {len(agents)} agents: {', '.join(friendly_names)}",
        data={"agents": agents, "reasoning": reasoning}
    )


def agent_start_event(agent_name: str) -> StreamEvent:
    agent_descriptions = {
        "programs_requirements": "Checking degree requirements...",
        "course_scheduling": "Searching course information...",
        "policy_compliance": "Reviewing university policies...",
        "academic_planning": "Planning academic pathway..."
    }
    return StreamEvent(
        event_type=EventType.AGENT_START,
        agent_name=agent_name,
        phase=AgentPhase.STARTING,
        message=agent_descriptions.get(agent_name, f"Starting {agent_name}...")
    )


def agent_retrieving_event(agent_name: str, query: str = "", doc_count: int = 0) -> StreamEvent:
    return StreamEvent(
        event_type=EventType.AGENT_RETRIEVING,
        agent_name=agent_name,
        phase=AgentPhase.RETRIEVING,
        message=f"Retrieving relevant documents..." if not doc_count else f"Found {doc_count} relevant documents",
        data={"query": query[:50] if query else "", "doc_count": doc_count}
    )


def agent_thinking_event(agent_name: str, message: str = "Analyzing information...") -> StreamEvent:
    return StreamEvent(
        event_type=EventType.AGENT_THINKING,
        agent_name=agent_name,
        phase=AgentPhase.ANALYZING,
        message=message
    )


def agent_output_event(
    agent_name: str,
    answer: str,
    confidence: float = 0.0,
    risks: list = None,
    relevant_policies: list = None
) -> StreamEvent:
    """
    Emit full agent output for real-time display.
    This allows users to see agent responses as they complete,
    before the final synthesis is done.
    """
    return StreamEvent(
        event_type=EventType.AGENT_OUTPUT,
        agent_name=agent_name,
        phase=AgentPhase.COMPLETE,
        message=f"Response ready ({int(confidence * 100)}% confidence)",
        data={
            "answer": answer,
            "confidence": confidence,
            "risks": risks or [],
            "relevant_policies": relevant_policies or []
        }
    )


def agent_complete_event(agent_name: str, confidence: float = 0.0, summary: str = "") -> StreamEvent:
    return StreamEvent(
        event_type=EventType.AGENT_COMPLETE,
        agent_name=agent_name,
        phase=AgentPhase.COMPLETE,
        message=summary or f"Completed analysis",
        data={"confidence": confidence}
    )


def agent_error_event(agent_name: str, error: str) -> StreamEvent:
    return StreamEvent(
        event_type=EventType.AGENT_ERROR,
        agent_name=agent_name,
        phase=AgentPhase.ERROR,
        message=f"Error: {error[:100]}"
    )


def synthesis_start_event() -> StreamEvent:
    return StreamEvent(
        event_type=EventType.SYNTHESIS_START,
        agent_name="coordinator",
        message="Synthesizing final answer..."
    )


def synthesis_token_event(token: str) -> StreamEvent:
    """For token-by-token streaming of the final answer."""
    return StreamEvent(
        event_type=EventType.SYNTHESIS_STREAMING,
        agent_name="coordinator",
        data={"token": token}
    )


def synthesis_complete_event(answer: str = "") -> StreamEvent:
    return StreamEvent(
        event_type=EventType.SYNTHESIS_COMPLETE,
        agent_name="coordinator",
        message="Answer complete",
        data={"answer_preview": answer[:200] if answer else ""}
    )


def workflow_complete_event(agents_used: list, total_time: float) -> StreamEvent:
    return StreamEvent(
        event_type=EventType.WORKFLOW_COMPLETE,
        message="Response complete",
        data={
            "agents_used": agents_used,
            "total_time_seconds": round(total_time, 2)
        }
    )


# ============================================================================
# COORDINATOR EVALUATION EVENTS (Chat Mode)
# ============================================================================

def coordinator_evaluation_event(
    round_num: int,
    sufficient: bool,
    quality_score: int,
    agent_feedback: dict,
    reasoning: str,
    agents_to_rerun: list = None,
    eval_time: float = 0.0
) -> StreamEvent:
    """Emitted when the coordinator evaluates agent outputs."""
    if sufficient:
        message = f"Round {round_num}: Quality {quality_score}/100 - Sufficient"
    else:
        message = f"Round {round_num}: Quality {quality_score}/100 - Need more info"

    return StreamEvent(
        event_type=EventType.COORDINATOR_EVALUATION,
        agent_name="coordinator",
        message=message,
        data={
            "round": round_num,
            "sufficient": sufficient,
            "quality_score": quality_score,
            "agent_feedback": agent_feedback,
            "reasoning": reasoning,
            "agents_to_rerun": agents_to_rerun or [],
            "eval_time": eval_time
        }
    )


def agent_rerun_start_event(
    round_num: int,
    agents: list,
    enhanced_k: int = 10
) -> StreamEvent:
    """Emitted when agents are being re-run with enhanced retrieval."""
    agent_names = {
        "programs_requirements": "Programs",
        "course_scheduling": "Courses",
        "policy_compliance": "Policy",
        "academic_planning": "Planning"
    }
    friendly_names = [agent_names.get(a, a) for a in agents]

    return StreamEvent(
        event_type=EventType.AGENT_RERUN_START,
        agent_name="coordinator",
        message=f"Re-running {len(agents)} agent(s) with enhanced retrieval (k={enhanced_k})",
        data={
            "round": round_num,
            "agents": agents,
            "enhanced_k": enhanced_k,
            "agent_names": friendly_names
        }
    )


def agent_rerun_complete_event(
    agent_name: str,
    round_num: int,
    execution_time: float
) -> StreamEvent:
    """Emitted when a re-run agent completes."""
    return StreamEvent(
        event_type=EventType.AGENT_RERUN_COMPLETE,
        agent_name=agent_name,
        message=f"Re-run complete ({execution_time:.2f}s)",
        data={
            "round": round_num,
            "execution_time": execution_time
        }
    )


# ============================================================================
# PLANNING MODE EVENTS
# ============================================================================

def planning_session_start_event(session_id: str, request: str, max_rounds: int = 5) -> StreamEvent:
    """Emitted when a planning session begins."""
    return StreamEvent(
        event_type=EventType.PLANNING_SESSION_START,
        agent_name="planning_coordinator",
        message="Starting collaborative planning session...",
        data={
            "session_id": session_id,
            "request": request[:200],
            "max_rounds": max_rounds
        }
    )


def planning_round_start_event(round_num: int, session_id: str) -> StreamEvent:
    """Emitted at the start of each negotiation round."""
    return StreamEvent(
        event_type=EventType.PLANNING_ROUND_START,
        agent_name="planning_coordinator",
        message=f"Starting Round {round_num}...",
        data={
            "round": round_num,
            "session_id": session_id
        }
    )


def planning_proposing_event(round_num: int) -> StreamEvent:
    """Emitted when planning agent is generating/revising a plan."""
    action = "Generating initial" if round_num == 1 else "Revising"
    return StreamEvent(
        event_type=EventType.PLANNING_PROPOSING,
        agent_name="academic_planning",
        message=f"{action} course plan...",
        data={"round": round_num}
    )


def planning_proposal_event(round_num: int, plan: dict) -> StreamEvent:
    """Emitted when a plan proposal is ready."""
    semester_count = len(plan.get("semesters", []))
    return StreamEvent(
        event_type=EventType.PLANNING_PROPOSAL,
        agent_name="academic_planning",
        message=f"Proposed {semester_count}-semester plan",
        data={
            "round": round_num,
            "plan": plan
        }
    )


def planning_critiquing_event(round_num: int, agents: list) -> StreamEvent:
    """Emitted when critique agents start evaluating (in parallel)."""
    return StreamEvent(
        event_type=EventType.PLANNING_CRITIQUING,
        agent_name="planning_coordinator",
        message=f"Evaluating plan with {len(agents)} agents in parallel...",
        data={
            "round": round_num,
            "agents": agents
        }
    )


def planning_critique_event(
    round_num: int,
    agent_name: str,
    approved: bool,
    issues: list,
    suggestions: list
) -> StreamEvent:
    """Emitted when a single agent's critique is complete."""
    status = "Approved" if approved else f"Found {len(issues)} issue(s)"
    return StreamEvent(
        event_type=EventType.PLANNING_CRITIQUE,
        agent_name=agent_name,
        message=status,
        data={
            "round": round_num,
            "approved": approved,
            "issues": issues,
            "suggestions": suggestions
        }
    )


def planning_round_complete_event(
    round_num: int,
    all_approved: bool,
    critiques_summary: dict
) -> StreamEvent:
    """Emitted when a round completes."""
    if all_approved:
        message = f"Round {round_num}: All agents approved!"
    else:
        failed = [k for k, v in critiques_summary.items() if not v]
        message = f"Round {round_num}: Revisions needed from {', '.join(failed)}"

    return StreamEvent(
        event_type=EventType.PLANNING_ROUND_COMPLETE,
        agent_name="planning_coordinator",
        message=message,
        data={
            "round": round_num,
            "all_approved": all_approved,
            "critiques_summary": critiques_summary
        }
    )


def planning_complete_event(
    session_id: str,
    status: str,
    total_rounds: int,
    final_plan: dict = None,
    message: str = ""
) -> StreamEvent:
    """Emitted when the planning session is complete."""
    if status == "completed":
        msg = f"Plan approved after {total_rounds} round(s)!"
    elif status == "max_rounds_reached":
        msg = f"Maximum rounds ({total_rounds}) reached. Final plan may have unresolved issues."
    else:
        msg = message or f"Planning session ended: {status}"

    return StreamEvent(
        event_type=EventType.PLANNING_COMPLETE,
        agent_name="planning_coordinator",
        message=msg,
        data={
            "session_id": session_id,
            "status": status,
            "total_rounds": total_rounds,
            "final_plan": final_plan
        }
    )
