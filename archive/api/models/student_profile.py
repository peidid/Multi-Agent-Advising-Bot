"""
Student Profile models for MongoDB storage.
Stores academic information for personalized advising.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class AcademicStanding(str, Enum):
    """Academic standing status."""
    GOOD = "good"
    PROBATION = "probation"
    WARNING = "warning"
    SUSPENSION = "suspension"


class CompletedCourse(BaseModel):
    """A completed course record."""
    course_code: str  # e.g., "15-122"
    course_name: str
    credits: float
    grade: Optional[str] = None  # A, B, C, etc.
    semester: str  # e.g., "Fall 2025"
    quality_points: Optional[float] = None


class CurrentEnrollment(BaseModel):
    """Currently enrolled course."""
    course_code: str
    course_name: str
    credits: float
    semester: str


class DegreeProgress(BaseModel):
    """Progress toward a degree or minor."""
    program_name: str  # e.g., "B.S. Information Systems"
    program_type: str  # major, minor, additional_major
    required_credits: float
    completed_credits: float
    remaining_credits: float
    completion_percentage: float
    remaining_requirements: List[str] = Field(default_factory=list)


class StudentProfileBase(BaseModel):
    """Base student profile with academic data."""
    # Basic info
    user_id: str  # Reference to User
    andrew_id: Optional[str] = None

    # Academic program
    primary_major: str  # e.g., "Information Systems"
    additional_majors: List[str] = Field(default_factory=list)
    minors: List[str] = Field(default_factory=list)
    expected_graduation: Optional[str] = None  # e.g., "Spring 2027"

    # Academic standing
    current_gpa: Optional[float] = None
    cumulative_credits: float = 0.0
    current_semester_credits: float = 0.0
    academic_standing: AcademicStanding = AcademicStanding.GOOD

    # Flags and constraints
    on_probation: bool = False
    has_overload_approval: bool = False
    max_credits_allowed: float = 54.0  # Default CMU max
    work_hours_per_week: Optional[int] = None  # If student works

    # Interests for recommendations
    career_interests: List[str] = Field(default_factory=list)
    research_interests: List[str] = Field(default_factory=list)


class StudentProfileCreate(StudentProfileBase):
    """Model for creating a new student profile."""
    completed_courses: List[CompletedCourse] = Field(default_factory=list)
    current_enrollment: List[CurrentEnrollment] = Field(default_factory=list)


class StudentProfileUpdate(BaseModel):
    """Model for updating student profile."""
    primary_major: Optional[str] = None
    additional_majors: Optional[List[str]] = None
    minors: Optional[List[str]] = None
    expected_graduation: Optional[str] = None
    current_gpa: Optional[float] = None
    cumulative_credits: Optional[float] = None
    current_semester_credits: Optional[float] = None
    academic_standing: Optional[AcademicStanding] = None
    on_probation: Optional[bool] = None
    has_overload_approval: Optional[bool] = None
    max_credits_allowed: Optional[float] = None
    work_hours_per_week: Optional[int] = None
    career_interests: Optional[List[str]] = None
    research_interests: Optional[List[str]] = None
    completed_courses: Optional[List[CompletedCourse]] = None
    current_enrollment: Optional[List[CurrentEnrollment]] = None


class StudentProfile(StudentProfileBase):
    """Full student profile as stored in MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")

    # Course history
    completed_courses: List[CompletedCourse] = Field(default_factory=list)
    current_enrollment: List[CurrentEnrollment] = Field(default_factory=list)

    # Degree progress (computed)
    degree_progress: List[DegreeProgress] = Field(default_factory=list)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Advisor notes (for advisor access)
    advisor_notes: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
        "from_attributes": True
    }


class StudentProfileSummary(BaseModel):
    """Lightweight summary for agent consumption."""
    user_id: str
    primary_major: str
    additional_majors: List[str]
    minors: List[str]
    current_gpa: Optional[float]
    cumulative_credits: float
    academic_standing: AcademicStanding
    on_probation: bool
    completed_course_codes: List[str]  # Just codes for quick lookup
    current_course_codes: List[str]
    career_interests: List[str]
    research_interests: List[str]
    flags: List[str] = Field(default_factory=list)  # Risk flags

    @classmethod
    def from_profile(cls, profile: StudentProfile) -> "StudentProfileSummary":
        """Create summary from full profile."""
        flags = []
        if profile.on_probation:
            flags.append("ON_PROBATION")
        if profile.current_semester_credits > profile.max_credits_allowed:
            flags.append("OVERLOAD")
        if profile.current_gpa and profile.current_gpa < 2.0:
            flags.append("LOW_GPA")
        if profile.work_hours_per_week and profile.work_hours_per_week > 15:
            flags.append("HEAVY_WORKLOAD")

        return cls(
            user_id=profile.user_id,
            primary_major=profile.primary_major,
            additional_majors=profile.additional_majors,
            minors=profile.minors,
            current_gpa=profile.current_gpa,
            cumulative_credits=profile.cumulative_credits,
            academic_standing=profile.academic_standing,
            on_probation=profile.on_probation,
            completed_course_codes=[c.course_code for c in profile.completed_courses],
            current_course_codes=[c.course_code for c in profile.current_enrollment],
            career_interests=profile.career_interests,
            research_interests=profile.research_interests,
            flags=flags
        )
