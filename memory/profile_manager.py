"""
Profile Manager - Long-term student profile storage

Manages persistent student information:
- Academic info (major, minor, concentration)
- Course history with grades
- Career goals and interests
- Preferences and constraints
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


@dataclass
class CourseTaken:
    """A course the student has taken."""
    code: str                    # e.g., "15-112"
    name: str = ""               # e.g., "Fundamentals of Programming"
    grade: str = ""              # e.g., "A", "B+", "P"
    semester: str = ""           # e.g., "Fall 2023", "F23"
    units: int = 0               # e.g., 12
    category: str = ""           # e.g., "core", "elective", "gen_ed"

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "CourseTaken":
        return cls(**data)


@dataclass
class StudentProfile:
    """
    Complete student profile for academic advising.
    Stored in MongoDB for persistence across sessions.
    """
    user_id: str

    # === Academic Standing ===
    major: str = ""
    minors: List[str] = field(default_factory=list)
    concentration: str = ""
    current_semester: str = ""       # e.g., "Junior Fall"
    expected_graduation: str = ""    # e.g., "Spring 2026"
    gpa: Optional[float] = None
    academic_standing: str = "good"  # good, probation, etc.

    # === Course History ===
    courses_taken: List[CourseTaken] = field(default_factory=list)
    courses_in_progress: List[str] = field(default_factory=list)
    courses_planned: List[str] = field(default_factory=list)

    # === Goals & Interests ===
    career_goals: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    research_interests: List[str] = field(default_factory=list)

    # === Preferences ===
    workload_preference: str = "balanced"  # light, balanced, heavy
    study_abroad_interest: bool = False
    preferred_class_times: List[str] = field(default_factory=list)  # morning, afternoon, evening

    # === Constraints ===
    must_take_courses: List[str] = field(default_factory=list)
    avoid_courses: List[str] = field(default_factory=list)
    scheduling_constraints: List[str] = field(default_factory=list)

    # === Metadata ===
    profile_complete: bool = False
    last_updated: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary for MongoDB storage."""
        data = asdict(self)
        # Convert CourseTaken objects to dicts
        data["courses_taken"] = [c.to_dict() if isinstance(c, CourseTaken) else c
                                  for c in self.courses_taken]
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "StudentProfile":
        """Create from MongoDB document."""
        if not data:
            return cls(user_id="")

        # Convert courses_taken dicts to CourseTaken objects
        courses_taken = []
        for c in data.get("courses_taken", []):
            if isinstance(c, dict):
                courses_taken.append(CourseTaken.from_dict(c))
            elif isinstance(c, CourseTaken):
                courses_taken.append(c)

        return cls(
            user_id=data.get("user_id", ""),
            major=data.get("major", ""),
            minors=data.get("minors", []),
            concentration=data.get("concentration", ""),
            current_semester=data.get("current_semester", ""),
            expected_graduation=data.get("expected_graduation", ""),
            gpa=data.get("gpa"),
            academic_standing=data.get("academic_standing", "good"),
            courses_taken=courses_taken,
            courses_in_progress=data.get("courses_in_progress", []),
            courses_planned=data.get("courses_planned", []),
            career_goals=data.get("career_goals", []),
            interests=data.get("interests", []),
            research_interests=data.get("research_interests", []),
            workload_preference=data.get("workload_preference", "balanced"),
            study_abroad_interest=data.get("study_abroad_interest", False),
            preferred_class_times=data.get("preferred_class_times", []),
            must_take_courses=data.get("must_take_courses", []),
            avoid_courses=data.get("avoid_courses", []),
            scheduling_constraints=data.get("scheduling_constraints", []),
            profile_complete=data.get("profile_complete", False),
            last_updated=data.get("last_updated", ""),
            created_at=data.get("created_at", "")
        )

    def get_completed_course_codes(self) -> List[str]:
        """Get list of completed course codes."""
        return [c.code for c in self.courses_taken]

    def get_total_units_completed(self) -> int:
        """Calculate total units completed."""
        return sum(c.units for c in self.courses_taken)

    def get_courses_by_category(self, category: str) -> List[CourseTaken]:
        """Get courses of a specific category."""
        return [c for c in self.courses_taken if c.category == category]

    def add_course(self, course: CourseTaken) -> None:
        """Add a course to history."""
        # Check if already exists
        existing = [c for c in self.courses_taken if c.code == course.code]
        if existing:
            # Update existing
            idx = self.courses_taken.index(existing[0])
            self.courses_taken[idx] = course
        else:
            self.courses_taken.append(course)
        self.last_updated = datetime.now().isoformat()

    def remove_course(self, course_code: str) -> bool:
        """Remove a course from history."""
        original_len = len(self.courses_taken)
        self.courses_taken = [c for c in self.courses_taken if c.code != course_code]
        self.last_updated = datetime.now().isoformat()
        return len(self.courses_taken) < original_len

    def to_prompt_context(self) -> str:
        """
        Format profile for inclusion in agent prompts.
        This is what agents see about the student.
        """
        # Format courses taken
        courses_text = ""
        if self.courses_taken:
            courses_list = []
            for c in sorted(self.courses_taken, key=lambda x: x.semester or ""):
                grade_str = f" ({c.grade})" if c.grade else ""
                courses_list.append(f"  - {c.code}: {c.name}{grade_str} [{c.semester}]")
            courses_text = "\n".join(courses_list)
        else:
            courses_text = "  No courses recorded"

        # Format in-progress courses
        in_progress_text = ", ".join(self.courses_in_progress) if self.courses_in_progress else "None"

        # Format goals
        goals_text = "\n".join([f"  - {g}" for g in self.career_goals]) if self.career_goals else "  Not specified"

        context = f"""=== STUDENT PROFILE ===
Academic Info:
  Major: {self.major or 'Not specified'}
  Minor(s): {', '.join(self.minors) if self.minors else 'None'}
  Concentration: {self.concentration or 'None'}
  Current Semester: {self.current_semester or 'Not specified'}
  Expected Graduation: {self.expected_graduation or 'Not specified'}
  GPA: {self.gpa if self.gpa else 'Not provided'}
  Academic Standing: {self.academic_standing}

Courses Completed ({len(self.courses_taken)} courses, {self.get_total_units_completed()} units):
{courses_text}

Currently Taking: {in_progress_text}

Career Goals:
{goals_text}

Interests: {', '.join(self.interests) if self.interests else 'Not specified'}
Workload Preference: {self.workload_preference}
======================"""

        return context


class ProfileManager:
    """
    Manages student profile CRUD operations.
    Works with MongoDB through the database module.
    """

    def __init__(self, db=None):
        """
        Initialize profile manager.

        Args:
            db: Database connection (if None, will use in-memory storage)
        """
        self.db = db
        self._cache: Dict[str, StudentProfile] = {}

    async def get_profile(self, user_id: str) -> StudentProfile:
        """
        Get a student's profile.

        Args:
            user_id: The user's ID

        Returns:
            StudentProfile (creates empty one if not found)
        """
        # Check cache first
        if user_id in self._cache:
            return self._cache[user_id]

        # Try database
        if self.db:
            doc = await self.db.student_profiles.find_one({"user_id": user_id})
            if doc:
                profile = StudentProfile.from_dict(doc)
                self._cache[user_id] = profile
                return profile

        # Return empty profile
        profile = StudentProfile(
            user_id=user_id,
            created_at=datetime.now().isoformat()
        )
        self._cache[user_id] = profile
        return profile

    async def save_profile(self, profile: StudentProfile) -> bool:
        """
        Save a student's profile.

        Args:
            profile: The profile to save

        Returns:
            True if successful
        """
        profile.last_updated = datetime.now().isoformat()
        self._cache[profile.user_id] = profile

        if self.db:
            await self.db.student_profiles.update_one(
                {"user_id": profile.user_id},
                {"$set": profile.to_dict()},
                upsert=True
            )

        return True

    async def add_course_to_profile(
        self,
        user_id: str,
        code: str,
        name: str = "",
        grade: str = "",
        semester: str = "",
        units: int = 0,
        category: str = ""
    ) -> StudentProfile:
        """
        Add a course to a student's profile.

        Returns:
            Updated profile
        """
        profile = await self.get_profile(user_id)
        course = CourseTaken(
            code=code,
            name=name,
            grade=grade,
            semester=semester,
            units=units,
            category=category
        )
        profile.add_course(course)
        await self.save_profile(profile)
        return profile

    async def remove_course_from_profile(self, user_id: str, course_code: str) -> StudentProfile:
        """Remove a course from profile."""
        profile = await self.get_profile(user_id)
        profile.remove_course(course_code)
        await self.save_profile(profile)
        return profile

    async def update_academic_info(
        self,
        user_id: str,
        major: str = None,
        minors: List[str] = None,
        concentration: str = None,
        current_semester: str = None,
        expected_graduation: str = None,
        gpa: float = None
    ) -> StudentProfile:
        """Update academic information."""
        profile = await self.get_profile(user_id)

        if major is not None:
            profile.major = major
        if minors is not None:
            profile.minors = minors
        if concentration is not None:
            profile.concentration = concentration
        if current_semester is not None:
            profile.current_semester = current_semester
        if expected_graduation is not None:
            profile.expected_graduation = expected_graduation
        if gpa is not None:
            profile.gpa = gpa

        await self.save_profile(profile)
        return profile

    async def update_goals(
        self,
        user_id: str,
        career_goals: List[str] = None,
        interests: List[str] = None,
        research_interests: List[str] = None
    ) -> StudentProfile:
        """Update goals and interests."""
        profile = await self.get_profile(user_id)

        if career_goals is not None:
            profile.career_goals = career_goals
        if interests is not None:
            profile.interests = interests
        if research_interests is not None:
            profile.research_interests = research_interests

        await self.save_profile(profile)
        return profile

    def clear_cache(self, user_id: str = None):
        """Clear profile cache."""
        if user_id:
            self._cache.pop(user_id, None)
        else:
            self._cache.clear()
