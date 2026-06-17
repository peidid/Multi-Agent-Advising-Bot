"""
Entity Tracker - Short-term conversation memory

Tracks entities mentioned in conversation:
- Courses (15-112, Evolution, etc.)
- Semesters (Spring 2026, Fall 2025)
- Programs (CS major, Math minor)
- Other references (pronouns, "the course", "that class")
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrackedEntity:
    """A tracked entity from conversation."""
    entity_type: str  # "course", "semester", "program", "professor", etc.
    value: str        # The actual value (e.g., "15-112", "Spring 2026")
    aliases: List[str] = field(default_factory=list)  # Alternative names
    context: str = ""  # Context where it was mentioned
    turn_mentioned: int = 0  # Which conversation turn
    confidence: float = 1.0


class EntityTracker:
    """
    Tracks entities across a conversation session.
    Enables reference resolution ("the course" -> "Evolution").
    """

    # Regex patterns for entity extraction
    COURSE_CODE_PATTERN = r'\b(\d{2}-\d{3})\b'
    SEMESTER_PATTERN = r'\b(Spring|Fall|Summer)\s*(20\d{2})\b'

    # Common course name patterns
    COURSE_NAMES = {
        "15-112": "Fundamentals of Programming",
        "15-122": "Principles of Imperative Computation",
        "15-150": "Principles of Functional Programming",
        "15-213": "Introduction to Computer Systems",
        "15-251": "Great Ideas in Theoretical Computer Science",
        "15-410": "Operating System Design and Implementation",
        "21-127": "Concepts of Mathematics",
        "21-241": "Matrices and Linear Transformations",
        "03-121": "Evolution",
        # Add more as needed
    }

    def __init__(self):
        self.entities: Dict[str, TrackedEntity] = {}
        self.current_turn = 0
        self.conversation_topic: Optional[str] = None
        self.last_mentioned_course: Optional[str] = None
        self.last_mentioned_semester: Optional[str] = None

    def extract_and_track(self, message: str, role: str = "user") -> Dict[str, Any]:
        """
        Extract entities from a message and track them.

        Args:
            message: The message text
            role: "user" or "assistant"

        Returns:
            Dict of extracted entities
        """
        self.current_turn += 1
        extracted = {
            "courses": [],
            "semesters": [],
            "references": []
        }

        # Extract course codes
        course_codes = re.findall(self.COURSE_CODE_PATTERN, message)
        for code in course_codes:
            name = self.COURSE_NAMES.get(code, "")
            entity = TrackedEntity(
                entity_type="course",
                value=code,
                aliases=[name] if name else [],
                context=message[:100],
                turn_mentioned=self.current_turn
            )
            self.entities[code] = entity
            self.last_mentioned_course = code
            extracted["courses"].append(code)

        # Extract course names (case-insensitive)
        message_lower = message.lower()
        for code, name in self.COURSE_NAMES.items():
            if name.lower() in message_lower:
                entity = TrackedEntity(
                    entity_type="course",
                    value=code,
                    aliases=[name],
                    context=message[:100],
                    turn_mentioned=self.current_turn
                )
                self.entities[code] = entity
                self.entities[name.lower()] = entity
                self.last_mentioned_course = code
                if code not in extracted["courses"]:
                    extracted["courses"].append(code)

        # Extract semesters
        semester_matches = re.findall(self.SEMESTER_PATTERN, message, re.IGNORECASE)
        for term, year in semester_matches:
            semester_str = f"{term.title()} {year}"
            entity = TrackedEntity(
                entity_type="semester",
                value=semester_str,
                context=message[:100],
                turn_mentioned=self.current_turn
            )
            self.entities[semester_str.lower()] = entity
            self.last_mentioned_semester = semester_str
            extracted["semesters"].append(semester_str)

        # Track references (pronouns, "the course", etc.)
        references = self._extract_references(message)
        extracted["references"] = references

        return extracted

    def _extract_references(self, message: str) -> List[str]:
        """Extract reference phrases that need resolution."""
        references = []
        message_lower = message.lower()

        # Common reference patterns
        reference_patterns = [
            r'\b(the course)\b',
            r'\b(that course)\b',
            r'\b(this course)\b',
            r'\b(the class)\b',
            r'\b(that class)\b',
            r'\b(it)\b',  # Only track if context suggests course
        ]

        for pattern in reference_patterns:
            if re.search(pattern, message_lower):
                match = re.search(pattern, message_lower)
                references.append(match.group(1))

        return references

    def resolve_reference(self, reference: str) -> Optional[str]:
        """
        Resolve a reference to its actual entity.

        Args:
            reference: The reference phrase (e.g., "the course", "it")

        Returns:
            The resolved entity value or None
        """
        reference_lower = reference.lower()

        # Course references
        if reference_lower in ["the course", "that course", "this course",
                               "the class", "that class", "it"]:
            return self.last_mentioned_course

        # Semester references
        if reference_lower in ["this semester", "that semester", "the semester"]:
            return self.last_mentioned_semester

        return None

    def enhance_query(self, query: str) -> str:
        """
        Enhance a query by resolving references.

        Args:
            query: Original user query

        Returns:
            Enhanced query with resolved references
        """
        enhanced = query

        # Extract references from query
        references = self._extract_references(query)

        for ref in references:
            resolved = self.resolve_reference(ref)
            if resolved:
                # Get full course info if it's a course
                course_name = self.COURSE_NAMES.get(resolved, "")
                if course_name:
                    replacement = f"{resolved} ({course_name})"
                else:
                    replacement = resolved

                # Replace reference with resolved value
                # Use word boundaries to avoid partial replacements
                pattern = r'\b' + re.escape(ref) + r'\b'
                enhanced = re.sub(pattern, replacement, enhanced, flags=re.IGNORECASE)

        return enhanced

    def get_conversation_context(self, max_entities: int = 5) -> Dict[str, Any]:
        """
        Get current conversation context summary.

        Returns:
            Dict with recent entities and topic
        """
        # Get most recent entities
        recent_entities = sorted(
            self.entities.values(),
            key=lambda e: e.turn_mentioned,
            reverse=True
        )[:max_entities]

        return {
            "current_turn": self.current_turn,
            "topic": self.conversation_topic,
            "last_course": self.last_mentioned_course,
            "last_semester": self.last_mentioned_semester,
            "recent_entities": [
                {
                    "type": e.entity_type,
                    "value": e.value,
                    "aliases": e.aliases
                }
                for e in recent_entities
            ]
        }

    def clear(self):
        """Clear all tracked entities (new conversation)."""
        self.entities.clear()
        self.current_turn = 0
        self.conversation_topic = None
        self.last_mentioned_course = None
        self.last_mentioned_semester = None
