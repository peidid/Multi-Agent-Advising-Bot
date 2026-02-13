"""
Context Formatter - Lightweight context formatting for agents

Instead of processing/enhancing queries, we simply format context
and let the LLM in each agent understand references naturally.
"""

from typing import Dict, List, Any, Optional


def format_conversation_context(history: List[Dict[str, str]], max_turns: int = 5) -> str:
    """
    Format recent conversation history for agent prompts.

    Args:
        history: List of {"role": "user/assistant", "content": "..."}
        max_turns: Maximum number of recent turns to include

    Returns:
        Formatted string for inclusion in prompts
    """
    if not history:
        return "No prior conversation."

    recent = history[-max_turns:]

    lines = []
    for msg in recent:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Truncate long messages
        if len(content) > 300:
            content = content[:300] + "..."
        prefix = "Student" if role == "user" else "Advisor"
        lines.append(f"{prefix}: {content}")

    return "\n".join(lines)


def format_student_profile(profile: Dict[str, Any]) -> str:
    """
    Format student profile for agent prompts.

    Args:
        profile: Student profile dict with major, courses_taken, etc.

    Returns:
        Formatted string for inclusion in prompts
    """
    if not profile:
        return "No student profile available."

    parts = []

    # Basic info
    major = profile.get("major")
    if isinstance(major, list) and major:
        major = major[0]
    if major:
        parts.append(f"Major: {major}")

    year = profile.get("year")
    if year:
        parts.append(f"Year: {year}")

    concentration = profile.get("concentration")
    if concentration:
        parts.append(f"Concentration: {concentration}")

    gpa = profile.get("gpa")
    if gpa:
        parts.append(f"GPA: {gpa}")

    minors = profile.get("minors", [])
    if minors:
        parts.append(f"Minors: {', '.join(minors)}")

    expected_grad = profile.get("expected_graduation")
    if expected_grad:
        parts.append(f"Expected Graduation: {expected_grad}")

    # Courses taken (with grades)
    courses_taken = profile.get("courses_taken", [])
    if courses_taken:
        course_strs = []
        for c in courses_taken[:10]:  # Limit to 10 most recent
            if isinstance(c, dict):
                code = c.get("code", "")
                grade = c.get("grade", "")
                course_strs.append(f"{code}({grade})")
            else:
                course_strs.append(str(c))
        parts.append(f"Courses Completed: {', '.join(course_strs)}")
    elif profile.get("completed_courses"):
        courses = profile.get("completed_courses", [])[:10]
        parts.append(f"Courses Completed: {', '.join(courses)}")

    # Career goals
    goals = profile.get("career_goals", [])
    if goals:
        parts.append(f"Career Goals: {', '.join(goals[:3])}")

    # Interests
    interests = profile.get("interests", [])
    if interests:
        parts.append(f"Interests: {', '.join(interests[:3])}")

    return "\n".join(parts) if parts else "No profile details available."


def build_agent_context(
    conversation_history: List[Dict[str, str]],
    student_profile: Dict[str, Any],
    max_conversation_turns: int = 5
) -> str:
    """
    Build complete context string for agent prompts.

    Args:
        conversation_history: Recent messages
        student_profile: Student profile data
        max_conversation_turns: How many recent turns to include

    Returns:
        Formatted context string ready for prompt injection
    """
    conversation_ctx = format_conversation_context(
        conversation_history,
        max_turns=max_conversation_turns
    )
    profile_ctx = format_student_profile(student_profile)

    return f"""=== CONVERSATION CONTEXT ===
{conversation_ctx}

=== STUDENT PROFILE ===
{profile_ctx}
"""


def get_context_for_state(
    conversation_history: List[Dict[str, str]],
    student_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Package context data for passing through workflow state.

    Args:
        conversation_history: Recent messages
        student_profile: Student profile data

    Returns:
        Dict to merge into workflow state
    """
    return {
        "conversation_history": conversation_history[-10:] if conversation_history else [],
        "student_profile": student_profile or {},
        "context_text": build_agent_context(conversation_history, student_profile)
    }
