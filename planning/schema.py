"""
Schema definitions for Collaborative Planning Mode.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class SemesterPlan:
    """A single semester in the course plan."""
    semester: str           # "Fall 2025"
    courses: List[str]      # ["15-122", "21-127", "76-101"]
    total_units: int
    notes: str = ""         # Optional notes

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CoursePlanJSON:
    """Complete course plan in JSON format."""
    plan_id: str
    student_id: str
    program: str
    start_semester: str
    target_graduation: str
    semesters: List[SemesterPlan]
    total_units: int
    requirements_met: List[str]
    requirements_pending: List[str]

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "student_id": self.student_id,
            "program": self.program,
            "start_semester": self.start_semester,
            "target_graduation": self.target_graduation,
            "semesters": [s.to_dict() for s in self.semesters],
            "total_units": self.total_units,
            "requirements_met": self.requirements_met,
            "requirements_pending": self.requirements_pending
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CoursePlanJSON':
        semesters = [
            SemesterPlan(**s) if isinstance(s, dict) else s
            for s in data.get("semesters", [])
        ]
        return cls(
            plan_id=data.get("plan_id", str(uuid.uuid4())),
            student_id=data.get("student_id", ""),
            program=data.get("program", ""),
            start_semester=data.get("start_semester", ""),
            target_graduation=data.get("target_graduation", ""),
            semesters=semesters,
            total_units=data.get("total_units", 0),
            requirements_met=data.get("requirements_met", []),
            requirements_pending=data.get("requirements_pending", [])
        )


@dataclass
class AgentCritique:
    """Critique from a single agent."""
    agent_name: str         # "policy_compliance", "programs_requirements", "course_scheduling"
    approved: bool
    issues: List[str]       # ["Overload in Fall 2025: 54 units exceeds 51 max"]
    suggestions: List[str]  # ["Move 15-213 to Spring 2026"]
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)  # Additional structured data

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'AgentCritique':
        return cls(
            agent_name=data.get("agent_name", ""),
            approved=data.get("approved", False),
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            confidence=data.get("confidence", 0.0),
            details=data.get("details", {})
        )


@dataclass
class PlanningRound:
    """A single round of the negotiation process."""
    round_number: int
    proposed_plan: CoursePlanJSON
    critiques: List[AgentCritique]
    all_approved: bool
    revision_notes: str     # What planning agent changed from previous round
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "round_number": self.round_number,
            "proposed_plan": self.proposed_plan.to_dict(),
            "critiques": [c.to_dict() for c in self.critiques],
            "all_approved": self.all_approved,
            "revision_notes": self.revision_notes,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PlanningRound':
        return cls(
            round_number=data.get("round_number", 0),
            proposed_plan=CoursePlanJSON.from_dict(data.get("proposed_plan", {})),
            critiques=[AgentCritique.from_dict(c) for c in data.get("critiques", [])],
            all_approved=data.get("all_approved", False),
            revision_notes=data.get("revision_notes", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow()
        )


@dataclass
class PlanningSession:
    """Complete planning session with all rounds."""
    session_id: str
    user_id: str
    conversation_id: str
    request: str            # Original user request
    student_profile: Dict[str, Any]
    rounds: List[PlanningRound]
    final_plan: Optional[CoursePlanJSON]
    status: str             # "in_progress", "completed", "failed", "max_rounds_reached"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_id": self.conversation_id,
            "request": self.request,
            "student_profile": self.student_profile,
            "rounds": [r.to_dict() for r in self.rounds],
            "final_plan": self.final_plan.to_dict() if self.final_plan else None,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'PlanningSession':
        return cls(
            session_id=data.get("session_id", ""),
            user_id=data.get("user_id", ""),
            conversation_id=data.get("conversation_id", ""),
            request=data.get("request", ""),
            student_profile=data.get("student_profile", {}),
            rounds=[PlanningRound.from_dict(r) for r in data.get("rounds", [])],
            final_plan=CoursePlanJSON.from_dict(data["final_plan"]) if data.get("final_plan") else None,
            status=data.get("status", "in_progress"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )

    def add_round(self, round_data: PlanningRound):
        """Add a round to the session."""
        self.rounds.append(round_data)

    def finalize(self, plan: CoursePlanJSON, status: str = "completed"):
        """Finalize the session with the final plan."""
        self.final_plan = plan
        self.status = status
        self.completed_at = datetime.utcnow()
