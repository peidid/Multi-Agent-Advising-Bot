"""
Conversation and Message models for MongoDB storage.
Stores chat history and agent interactions.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"  # For individual agent responses


class WorkflowStep(str, Enum):
    """Current step in the multi-agent workflow."""
    INITIAL = "initial"
    INTENT_CLASSIFICATION = "intent_classification"
    CLARIFICATION = "clarification"
    AGENT_EXECUTION = "agent_execution"
    NEGOTIATION = "negotiation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    ERROR = "error"


class AgentStatus(str, Enum):
    """Status of an agent during execution."""
    IDLE = "idle"
    THINKING = "thinking"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"
    SKIPPED = "skipped"


class AgentOutput(BaseModel):
    """Output from a single agent."""
    agent_name: str
    agent_type: str  # programs, courses, policy, planning
    answer: str
    confidence: float = 0.0
    relevant_policies: List[str] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    plan_options: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    status: AgentStatus = AgentStatus.COMPLETE


class ConflictInfo(BaseModel):
    """Information about a detected conflict."""
    conflict_type: str  # hard_violation, high_risk, trade_off
    severity: str  # critical, high, medium, low
    affected_agents: List[str]
    description: str
    options: List[Dict[str, Any]] = Field(default_factory=list)
    resolution: Optional[str] = None
    user_choice: Optional[str] = None


class WorkflowState(BaseModel):
    """Current state of the multi-agent workflow."""
    step: WorkflowStep = WorkflowStep.INITIAL
    active_agents: List[str] = Field(default_factory=list)
    completed_agents: List[str] = Field(default_factory=list)
    agent_outputs: Dict[str, AgentOutput] = Field(default_factory=dict)
    conflicts: List[ConflictInfo] = Field(default_factory=list)
    iteration_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class Message(BaseModel):
    """A single message in a conversation."""
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # For agent messages
    agent_name: Optional[str] = None
    agent_output: Optional[AgentOutput] = None

    # For assistant messages with full workflow
    workflow_state: Optional[WorkflowState] = None

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationBase(BaseModel):
    """Base conversation model."""
    user_id: str
    title: Optional[str] = None  # Auto-generated from first message
    is_active: bool = True


class ConversationCreate(ConversationBase):
    """Model for creating a new conversation."""
    initial_message: Optional[str] = None


class Conversation(ConversationBase):
    """Full conversation as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")

    # Messages
    messages: List[Message] = Field(default_factory=list)

    # Current workflow state (for real-time updates)
    current_workflow: Optional[WorkflowState] = None

    # Student context (snapshot at conversation start)
    student_profile_snapshot: Optional[Dict[str, Any]] = None

    # Aggregated data from conversation
    topics_discussed: List[str] = Field(default_factory=list)
    courses_mentioned: List[str] = Field(default_factory=list)
    decisions_made: List[Dict[str, Any]] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None

    # Analytics
    total_messages: int = 0
    total_agent_calls: int = 0
    total_conflicts_resolved: int = 0

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }


class ConversationSummary(BaseModel):
    """Lightweight conversation summary for listing."""
    id: str
    user_id: str
    title: Optional[str]
    created_at: datetime
    last_message_at: Optional[datetime]
    total_messages: int
    is_active: bool
    preview: Optional[str] = None  # First ~100 chars of last message


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    conversation_id: Optional[str] = None  # None = new conversation
    include_workflow_details: bool = True  # Include agent execution details
    stream: bool = False  # Enable streaming response


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    conversation_id: str
    message_id: str
    response: str

    # Workflow details (if requested)
    workflow: Optional[WorkflowState] = None

    # Quick access to key info
    agents_used: List[str] = Field(default_factory=list)
    conflicts_detected: int = 0
    sources: List[str] = Field(default_factory=list)

    # Performance
    total_time_ms: int = 0


class StreamingChunk(BaseModel):
    """Chunk for streaming responses."""
    type: str  # "status", "agent_start", "agent_complete", "content", "done"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
