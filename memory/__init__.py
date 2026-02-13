"""
Memory Module for Multi-Agent Advising System

Provides:
- Short-term conversation memory (entity tracking, reference resolution)
- Long-term student profile management (courses, goals, preferences)
- Query enhancement with context injection
"""

from memory.memory_manager import MemoryManager
from memory.entity_tracker import EntityTracker
from memory.profile_manager import StudentProfile, ProfileManager

__all__ = [
    "MemoryManager",
    "EntityTracker",
    "StudentProfile",
    "ProfileManager"
]
