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
