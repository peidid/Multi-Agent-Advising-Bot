"""
Structured Blackboard Schema
Based on General Feedback Section 3.1: Shared State as structured data
"""
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class ConflictType(str, Enum):
    """Canonical conflict types (from feedback Section 5)"""
    HARD_VIOLATION = "hard_violation"  # Plan breaks policy (impossible)
    HIGH_RISK = "high_risk"           # Plan possible but risky
    TRADE_OFF = "trade_off"           # Multiple valid options

class WorkflowStep(str, Enum):
    """Workflow states"""
    INITIAL = "initial"
    INTENT_CLASSIFICATION = "intent_classification"
    AGENT_EXECUTION = "agent_execution"
    NEGOTIATION = "negotiation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    USER_INPUT = "user_input"

# ============================================================================
# PYDANTIC MODELS (Structured Data)
# ============================================================================

class Constraint(BaseModel):
    """Constraint from policy, student, or finance"""
    source: str = Field(description="Source: 'policy', 'student', or 'finance'")
    description: str = Field(description="Description of the constraint")
    hard: bool = Field(description="True if hard constraint, False if soft")
    policy_citation: Optional[str] = Field(None, description="Policy document citation")

class Risk(BaseModel):
    """Risk identified by agents"""
    type: str = Field(description="Risk type: 'overload_risk', 'time_conflict', 'gpa_below_threshold'")
    severity: str = Field(description="Severity: 'high', 'medium', 'low'")
    description: str = Field(description="Description of the risk")
    policy_citation: Optional[str] = Field(None, description="Relevant policy citation")

class PlanOption(BaseModel):
    """A candidate plan option (from feedback Section 3.1)"""
    semesters: List[Dict[str, Any]] = Field(description="Semester-by-semester plan")
    courses: List[str] = Field(description="List of course codes")
    risks: List[Risk] = Field(default_factory=list)
    policy_citations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    justification: str = Field(description="Why this plan is proposed")

class AgentOutput(BaseModel):
    """
    Structured output from each agent (from feedback Section 3.2)
    Each agent returns: answer, confidence, relevant_policies
    """
    agent_name: str
    answer: str = Field(description="Agent's answer/response")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score")
    relevant_policies: List[str] = Field(default_factory=list, description="Policy citations")
    risks: List[Risk] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    plan_options: Optional[List[PlanOption]] = Field(None, description="Proposed plans if applicable")

class Conflict(BaseModel):
    """Conflict detected between agents (from feedback Section 5)"""
    conflict_type: ConflictType
    affected_agents: List[str] = Field(description="Which agents are involved")
    description: str
    options: List[Dict[str, Any]] = Field(default_factory=list, description="Resolution options")

# ============================================================================
# BLACKBOARD STATE (TypedDict for LangGraph)
# ============================================================================

class BlackboardState(TypedDict):
    """
    Main Blackboard State - Structured Schema
    Based on General Feedback Section 3.1
    """
    # Student Information
    student_profile: Optional[Dict[str, Any]]
    # Format: {"major": ["IS"], "minor": [], "gpa": 3.5, "completed_courses": ["15-110", ...], "flags": []}
    
    # User Intent
    user_goal: Optional[str]  # e.g., "add CS minor" or "graduate in 4 years"
    user_query: str
    
    # Agent Outputs (Structured - Key: agent_name, Value: AgentOutput)
    agent_outputs: Dict[str, AgentOutput]
    
    # Constraints & Risks (Aggregated from all agents)
    constraints: List[Constraint]
    risks: List[Risk]
    
    # Plans & Options
    plan_options: List[PlanOption]
    
    # Conflict Resolution (from feedback Section 5)
    conflicts: List[Conflict]
    open_questions: List[str]  # Questions for user clarification
    
    # Conversation History
    messages: List[Any]  # LangChain messages
    
    # Coordinator State (Dynamic Workflow Management)
    active_agents: List[str]  # Which agents are currently active
    workflow_step: WorkflowStep  # Current step in workflow
    iteration_count: int  # For negotiation loops (max 3, from feedback)
    next_agent: Optional[str]  # Next agent to execute