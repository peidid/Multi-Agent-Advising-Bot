"""
Memory Manager - Central memory management for the advising system

Combines:
- Short-term conversation memory (EntityTracker)
- Long-term student profile (ProfileManager)
- Query enhancement and context injection
"""

from typing import Dict, List, Optional, Any
from memory.entity_tracker import EntityTracker
from memory.profile_manager import ProfileManager, StudentProfile
import re


class MemoryManager:
    """
    Central memory manager for the multi-agent advising system.

    Responsibilities:
    1. Track entities across conversation (short-term)
    2. Manage student profiles (long-term)
    3. Enhance queries with context
    4. Provide context to agents
    """

    def __init__(self, db=None):
        """
        Initialize memory manager.

        Args:
            db: Database connection for profile persistence
        """
        # Short-term memory (per conversation)
        self.entity_tracker = EntityTracker()

        # Long-term memory (persistent)
        self.profile_manager = ProfileManager(db)

        # Current user context
        self.current_user_id: Optional[str] = None
        self.current_profile: Optional[StudentProfile] = None

    async def set_user(self, user_id: str) -> StudentProfile:
        """
        Set current user and load their profile.

        Args:
            user_id: The user's ID

        Returns:
            The user's profile
        """
        self.current_user_id = user_id
        self.current_profile = await self.profile_manager.get_profile(user_id)
        return self.current_profile

    def process_message(self, message: str, role: str = "user") -> Dict[str, Any]:
        """
        Process a message and extract/track entities.

        Args:
            message: The message content
            role: "user" or "assistant"

        Returns:
            Extracted entities and context
        """
        # Extract and track entities
        extracted = self.entity_tracker.extract_and_track(message, role)

        # Auto-detect profile info from conversation
        profile_updates = self._detect_profile_info(message)

        return {
            "extracted_entities": extracted,
            "profile_updates": profile_updates,
            "conversation_context": self.entity_tracker.get_conversation_context()
        }

    def _detect_profile_info(self, message: str) -> Dict[str, Any]:
        """
        Detect profile information mentioned in conversation.
        E.g., "I'm a CS major" -> major: "Computer Science"
        """
        updates = {}
        message_lower = message.lower()

        # Detect major mentions
        major_patterns = [
            (r"i(?:'m| am) (?:a |an )?(\w+) major", 1),
            (r"my major is (\w+)", 1),
            (r"majoring in (\w+)", 1),
        ]
        for pattern, group in major_patterns:
            match = re.search(pattern, message_lower)
            if match:
                major = match.group(group).title()
                # Map abbreviations
                major_map = {
                    "Cs": "Computer Science",
                    "Is": "Information Systems",
                    "Bio": "Biological Sciences",
                    "Ba": "Business Administration"
                }
                updates["major"] = major_map.get(major, major)
                break

        # Detect semester mentions
        semester_patterns = [
            (r"i(?:'m| am) (?:a |an )?(freshman|sophomore|junior|senior)", 1),
            (r"(first|second|third|fourth)[- ]year", 1),
        ]
        for pattern, group in semester_patterns:
            match = re.search(pattern, message_lower)
            if match:
                year = match.group(group)
                year_map = {
                    "freshman": "First-Year",
                    "first": "First-Year",
                    "sophomore": "Sophomore",
                    "second": "Sophomore",
                    "junior": "Junior",
                    "third": "Junior",
                    "senior": "Senior",
                    "fourth": "Senior"
                }
                updates["year"] = year_map.get(year, year.title())
                break

        # Detect course completion mentions
        # E.g., "I took 15-112" or "I've completed 15-122"
        course_pattern = r"i(?:'ve)?\s+(?:took|taken|completed|finished)\s+(\d{2}-\d{3})"
        course_matches = re.findall(course_pattern, message_lower)
        if course_matches:
            updates["courses_mentioned"] = course_matches

        return updates

    def enhance_query(self, query: str) -> str:
        """
        Enhance a query with context from memory.

        This resolves references like "the course" -> "15-112 (Fundamentals of Programming)"
        and adds relevant context.

        Args:
            query: Original user query

        Returns:
            Enhanced query with resolved references
        """
        # First, let entity tracker resolve references
        enhanced = self.entity_tracker.enhance_query(query)

        return enhanced

    def get_agent_context(self) -> Dict[str, Any]:
        """
        Get context to pass to agents.

        Returns:
            Dict with conversation context and profile info
        """
        context = {
            "conversation": self.entity_tracker.get_conversation_context(),
            "profile": None,
            "profile_text": ""
        }

        if self.current_profile:
            context["profile"] = self.current_profile.to_dict()
            context["profile_text"] = self.current_profile.to_prompt_context()

        return context

    def get_enhanced_student_profile(self) -> Dict[str, Any]:
        """
        Get student profile in format expected by agents.

        Returns:
            Profile dict compatible with existing agent code
        """
        if not self.current_profile:
            return {}

        profile = self.current_profile

        return {
            "major": [profile.major] if profile.major else [],
            "minors": profile.minors,
            "concentration": profile.concentration,
            "current_semester": profile.current_semester,
            "expected_graduation": profile.expected_graduation,
            "gpa": profile.gpa,
            "completed_courses": profile.get_completed_course_codes(),
            "courses_in_progress": profile.courses_in_progress,
            "career_goals": profile.career_goals,
            "interests": profile.interests,
            "workload_preference": profile.workload_preference,
            # Full course details for planning agent
            "course_history": [c.to_dict() for c in profile.courses_taken],
            # Summary stats
            "total_units_completed": profile.get_total_units_completed(),
            "courses_count": len(profile.courses_taken)
        }

    def get_conversation_summary(self, max_turns: int = 5) -> str:
        """
        Get a text summary of recent conversation context.

        Args:
            max_turns: Maximum number of turns to include

        Returns:
            Text summary for inclusion in prompts
        """
        context = self.entity_tracker.get_conversation_context()

        summary_parts = []

        if context["last_course"]:
            course_name = self.entity_tracker.COURSE_NAMES.get(
                context["last_course"], ""
            )
            if course_name:
                summary_parts.append(
                    f"Recently discussed: {context['last_course']} ({course_name})"
                )
            else:
                summary_parts.append(f"Recently discussed course: {context['last_course']}")

        if context["last_semester"]:
            summary_parts.append(f"Referenced semester: {context['last_semester']}")

        if context["recent_entities"]:
            entities_str = ", ".join([
                f"{e['value']}" for e in context["recent_entities"][:3]
            ])
            summary_parts.append(f"Entities mentioned: {entities_str}")

        return "\n".join(summary_parts) if summary_parts else ""

    def clear_conversation(self):
        """Clear short-term conversation memory (start fresh)."""
        self.entity_tracker.clear()

    async def save_current_profile(self):
        """Save current profile to database."""
        if self.current_profile:
            await self.profile_manager.save_profile(self.current_profile)


# Global instance (can be overridden)
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get or create global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def set_memory_manager(manager: MemoryManager):
    """Set global memory manager instance."""
    global _memory_manager
    _memory_manager = manager
