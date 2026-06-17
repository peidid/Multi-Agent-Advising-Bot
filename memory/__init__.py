"""
Memory Module for Multi-Agent Advising System

Provides:
- Short-term conversation memory (entity tracking, reference resolution)
- Long-term student profile management (courses, goals, preferences)
- Query enhancement with context injection
"""

# NOTE: This package now only provides `context_formatter` (the live module).
# The former MemoryManager / EntityTracker / ProfileManager modules were unused
# by the running system and were moved to archive/dead_modules/memory/.
# Short-term memory is handled by
# coordinator.llm_driven_coordinator.LLMDrivenCoordinator.resolve_context().
