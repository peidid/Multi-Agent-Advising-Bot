"""
Student Profile service for academic data management.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.models.student_profile import (
    StudentProfile, StudentProfileCreate, StudentProfileUpdate,
    StudentProfileSummary, CompletedCourse, CurrentEnrollment,
    DegreeProgress, AcademicStanding
)
from api.database import PROFILES_COLLECTION


class ProfileService:
    """Service for student profile operations."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db[PROFILES_COLLECTION]

    async def create_profile(self, profile_data: StudentProfileCreate) -> StudentProfile:
        """Create a new student profile."""
        # Check if profile already exists for user
        existing = await self.collection.find_one({"user_id": profile_data.user_id})
        if existing:
            raise ValueError("Profile already exists for this user")

        # Create profile document
        profile_doc = {
            "user_id": profile_data.user_id,
            "andrew_id": profile_data.andrew_id,
            "primary_major": profile_data.primary_major,
            "additional_majors": profile_data.additional_majors,
            "minors": profile_data.minors,
            "expected_graduation": profile_data.expected_graduation,
            "current_gpa": profile_data.current_gpa,
            "cumulative_credits": profile_data.cumulative_credits,
            "current_semester_credits": profile_data.current_semester_credits,
            "academic_standing": profile_data.academic_standing.value,
            "on_probation": profile_data.on_probation,
            "has_overload_approval": profile_data.has_overload_approval,
            "max_credits_allowed": profile_data.max_credits_allowed,
            "work_hours_per_week": profile_data.work_hours_per_week,
            "career_interests": profile_data.career_interests,
            "research_interests": profile_data.research_interests,
            "completed_courses": [c.model_dump() for c in profile_data.completed_courses],
            "current_enrollment": [c.model_dump() for c in profile_data.current_enrollment],
            "degree_progress": [],
            "advisor_notes": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        result = await self.collection.insert_one(profile_doc)
        profile_doc["_id"] = str(result.inserted_id)

        return self._doc_to_profile(profile_doc)

    async def get_profile_by_user_id(self, user_id: str) -> Optional[StudentProfile]:
        """Get student profile by user ID."""
        profile_doc = await self.collection.find_one({"user_id": user_id})
        if not profile_doc:
            return None
        return self._doc_to_profile(profile_doc)

    async def get_profile_summary(self, user_id: str) -> Optional[StudentProfileSummary]:
        """Get lightweight profile summary for agent use."""
        profile = await self.get_profile_by_user_id(user_id)
        if not profile:
            return None
        return StudentProfileSummary.from_profile(profile)

    async def update_profile(
        self,
        user_id: str,
        update_data: StudentProfileUpdate
    ) -> Optional[StudentProfile]:
        """Update student profile."""
        update_doc = {"updated_at": datetime.utcnow()}

        # Add non-None fields to update
        update_dict = update_data.model_dump(exclude_none=True)
        for key, value in update_dict.items():
            if key == "academic_standing" and value is not None:
                update_doc[key] = value.value if hasattr(value, 'value') else value
            elif key == "completed_courses" and value is not None:
                update_doc[key] = [c.model_dump() if hasattr(c, 'model_dump') else c for c in value]
            elif key == "current_enrollment" and value is not None:
                update_doc[key] = [c.model_dump() if hasattr(c, 'model_dump') else c for c in value]
            else:
                update_doc[key] = value

        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": update_doc}
        )

        if result.modified_count == 0 and result.matched_count == 0:
            return None

        return await self.get_profile_by_user_id(user_id)

    async def add_completed_course(
        self,
        user_id: str,
        course: CompletedCourse
    ) -> Optional[StudentProfile]:
        """Add a completed course to profile."""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"completed_courses": course.model_dump()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.modified_count == 0:
            return None

        # Update cumulative credits
        profile = await self.get_profile_by_user_id(user_id)
        if profile:
            new_credits = sum(c.credits for c in profile.completed_courses)
            await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"cumulative_credits": new_credits}}
            )

        return await self.get_profile_by_user_id(user_id)

    async def update_current_enrollment(
        self,
        user_id: str,
        courses: List[CurrentEnrollment]
    ) -> Optional[StudentProfile]:
        """Update current semester enrollment."""
        current_credits = sum(c.credits for c in courses)

        result = await self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "current_enrollment": [c.model_dump() for c in courses],
                    "current_semester_credits": current_credits,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if result.modified_count == 0:
            return None

        return await self.get_profile_by_user_id(user_id)

    async def add_advisor_note(
        self,
        user_id: str,
        note: str,
        advisor_id: str
    ) -> Optional[StudentProfile]:
        """Add an advisor note to profile."""
        note_doc = {
            "advisor_id": advisor_id,
            "note": note,
            "timestamp": datetime.utcnow()
        }

        result = await self.collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"advisor_notes": note_doc},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        if result.modified_count == 0:
            return None

        return await self.get_profile_by_user_id(user_id)

    async def calculate_degree_progress(
        self,
        user_id: str
    ) -> List[DegreeProgress]:
        """Calculate and update degree progress."""
        profile = await self.get_profile_by_user_id(user_id)
        if not profile:
            return []

        # This would integrate with your program requirements
        # For now, return placeholder
        progress_list = []

        # Primary major progress
        progress_list.append(DegreeProgress(
            program_name=f"B.S. {profile.primary_major}",
            program_type="major",
            required_credits=360.0,  # Example
            completed_credits=profile.cumulative_credits,
            remaining_credits=max(0, 360.0 - profile.cumulative_credits),
            completion_percentage=min(100, (profile.cumulative_credits / 360.0) * 100),
            remaining_requirements=[]  # Would be populated by programs agent
        ))

        # Update in database
        await self.collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "degree_progress": [p.model_dump() for p in progress_list],
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return progress_list

    async def delete_profile(self, user_id: str) -> bool:
        """Delete a student profile."""
        result = await self.collection.delete_one({"user_id": user_id})
        return result.deleted_count > 0

    def _doc_to_profile(self, doc: Dict[str, Any]) -> StudentProfile:
        """Convert MongoDB document to StudentProfile model."""
        return StudentProfile(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            andrew_id=doc.get("andrew_id"),
            primary_major=doc["primary_major"],
            additional_majors=doc.get("additional_majors", []),
            minors=doc.get("minors", []),
            expected_graduation=doc.get("expected_graduation"),
            current_gpa=doc.get("current_gpa"),
            cumulative_credits=doc.get("cumulative_credits", 0.0),
            current_semester_credits=doc.get("current_semester_credits", 0.0),
            academic_standing=AcademicStanding(doc.get("academic_standing", "good")),
            on_probation=doc.get("on_probation", False),
            has_overload_approval=doc.get("has_overload_approval", False),
            max_credits_allowed=doc.get("max_credits_allowed", 54.0),
            work_hours_per_week=doc.get("work_hours_per_week"),
            career_interests=doc.get("career_interests", []),
            research_interests=doc.get("research_interests", []),
            completed_courses=[
                CompletedCourse(**c) for c in doc.get("completed_courses", [])
            ],
            current_enrollment=[
                CurrentEnrollment(**c) for c in doc.get("current_enrollment", [])
            ],
            degree_progress=[
                DegreeProgress(**p) for p in doc.get("degree_progress", [])
            ],
            advisor_notes=doc.get("advisor_notes", []),
            created_at=doc.get("created_at", datetime.utcnow()),
            updated_at=doc.get("updated_at", datetime.utcnow())
        )
