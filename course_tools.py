import json
import os
import re
from typing import Optional, List, Dict, Any

# Use absolute path based on project root (same pattern as rag_engine_improved.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "courses")
SCHEDULES_PATH = os.path.join(PROJECT_ROOT, "data", "schedules")
DB = {"courses": {}, "schedules": {}, "course_names": {}}


def load_data():
    """Load all JSON course files into memory."""
    if not os.path.exists(DATA_PATH):
        print(f"Warning: Course data path not found: {DATA_PATH}")
        print(f"   Course lookup features will be limited.")
        return

    try:
        files = os.listdir(DATA_PATH)
        json_files = [f for f in files if f.endswith(".json")]

        if not json_files:
            print(f"Warning: No JSON files found in {DATA_PATH}")
            return

        for filename in json_files:
            try:
                file_path = os.path.join(DATA_PATH, filename)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Each JSON file is a single course object with a "code" field
                    if isinstance(data, dict) and "code" in data:
                        DB["courses"][data["code"]] = data
                        # Also index by name for lookup
                        if "name" in data:
                            name_lower = data["name"].lower()
                            DB["course_names"][name_lower] = data["code"]
                    # Handle legacy format where JSON might be a list
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "code" in item:
                                DB["courses"][item["code"]] = item
                                if "name" in item:
                                    name_lower = item["name"].lower()
                                    DB["course_names"][name_lower] = item["code"]
            except Exception as e:
                # Continue loading other files even if one fails
                print(f"Error loading {filename}: {e}")
                continue

        if DB["courses"]:
            print(f"Loaded {len(DB['courses'])} courses from {DATA_PATH}")
        else:
            print(f"Warning: No valid course data loaded from {DATA_PATH}")

    except Exception as e:
        print(f"Error accessing course data directory: {e}")
        print(f"   Course lookup features will be limited.")


def load_schedules():
    """Load all schedule JSON files into memory."""
    if not os.path.exists(SCHEDULES_PATH):
        print(f"Warning: Schedules path not found: {SCHEDULES_PATH}")
        return

    try:
        for filename in os.listdir(SCHEDULES_PATH):
            if filename.endswith('.json'):
                try:
                    filepath = os.path.join(SCHEDULES_PATH, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                        # Determine semester key
                        if isinstance(data, dict) and "semester" in data:
                            term = data.get("semester", {})
                            key = f"{term.get('term', '').lower()}_{term.get('year', '')}"
                        else:
                            # Parse from filename like "Spring_2025_courses.json"
                            match = re.search(r'(Fall|Spring|Summer)_(\d{4})', filename, re.IGNORECASE)
                            if match:
                                key = f"{match.group(1).lower()}_{match.group(2)}"
                            else:
                                key = filename.replace('.json', '').lower()

                        # Store schedule data
                        if isinstance(data, dict):
                            DB["schedules"][key] = data
                        elif isinstance(data, list):
                            DB["schedules"][key] = {
                                "offerings": data,
                                "total_courses": len(data)
                            }
                except Exception as e:
                    print(f"Error loading schedule {filename}: {e}")
                    continue

        if DB["schedules"]:
            print(f"Loaded {len(DB['schedules'])} schedule files")
    except Exception as e:
        print(f"Error loading schedules: {e}")


# Initialize on import
try:
    load_data()
    load_schedules()
except Exception as e:
    print(f"Failed to load data: {e}")
    print(f"   System will continue with limited functionality.")


def look_up_course_info(course_code: str) -> Optional[Dict]:
    """Look up course info by course code."""
    return DB["courses"].get(course_code, None)


def find_course_by_name(name: str) -> Optional[Dict]:
    """
    Find a course by its name (case-insensitive partial match).
    Returns course info dict or None.
    """
    name_lower = name.lower().strip()

    # Try exact match first
    if name_lower in DB["course_names"]:
        code = DB["course_names"][name_lower]
        return DB["courses"].get(code)

    # Try partial match
    for course_name, code in DB["course_names"].items():
        if name_lower in course_name or course_name in name_lower:
            return DB["courses"].get(code)

    # Search through all courses
    for code, course in DB["courses"].items():
        if "name" in course and name_lower in course["name"].lower():
            return course

    return None


def find_course_codes_in_text(text: str) -> List[str]:
    """
    Extract course codes from text.

    Handles both formats:
    - "15-112" (with hyphen)
    - "15112" (without hyphen, normalized to "15-112")
    """
    codes = []

    # First find codes with hyphens (XX-XXX)
    hyphenated = re.findall(r"\d{2}-\d{3}", text)
    codes.extend(hyphenated)

    # Then find 5-digit codes without hyphens
    # Use word boundaries to avoid matching parts of larger numbers
    for match in re.finditer(r"(?<!\d)(\d{5})(?!\d)", text):
        five_digit = match.group(1)
        # Normalize to XX-XXX format
        normalized = f"{five_digit[:2]}-{five_digit[2:]}"
        # Only add if not already found (avoid duplicates)
        if normalized not in codes:
            codes.append(normalized)

    return codes


def get_course_schedule(course_code: str, semester: str = None) -> List[Dict]:
    """
    Get schedule info for a course.

    Args:
        course_code: Course code like "03-121"
        semester: Optional semester like "spring_2026" or "Fall 2025"

    Returns:
        List of schedule sections with days, times, locations
    """
    results = []

    # Normalize semester format
    if semester:
        semester = semester.lower().replace(" ", "_")

    # Search through schedules
    for key, schedule_data in DB["schedules"].items():
        # Filter by semester if specified
        if semester and semester not in key:
            continue

        offerings = schedule_data.get("offerings", [])
        for offering in offerings:
            # Handle different field names
            code = offering.get("course_code") or offering.get("Course - ID", "")
            if code == course_code:
                sections = offering.get("sections", [])
                if sections:
                    results.append({
                        "semester": key,
                        "course_code": code,
                        "sections": sections
                    })
                else:
                    # Legacy format without sections array
                    results.append({
                        "semester": key,
                        "course_code": code,
                        "sections": [{
                            "days": offering.get("days", []),
                            "start_time": offering.get("start_time", ""),
                            "end_time": offering.get("end_time", ""),
                            "location": offering.get("location", ""),
                            "instructor": offering.get("instructor", "")
                        }]
                    })

    return results


def check_schedule_conflict(course_code: str, semester: str, busy_day: str, busy_start: str, busy_end: str) -> Dict[str, Any]:
    """
    Check if a course conflicts with a specified busy time.

    Args:
        course_code: Course code like "03-121"
        semester: Semester like "spring_2026"
        busy_day: Day like "Monday" or "Mon"
        busy_start: Start time like "09:00" or "9am"
        busy_end: End time like "11:00" or "11am"

    Returns:
        Dict with conflict info: {has_conflict, course_schedule, conflict_details}
    """
    # Normalize day name
    day_map = {
        "monday": "Mon", "mon": "Mon",
        "tuesday": "Tue", "tue": "Tue",
        "wednesday": "Wed", "wed": "Wed",
        "thursday": "Thu", "thu": "Thu",
        "friday": "Fri", "fri": "Fri",
        "saturday": "Sat", "sat": "Sat",
        "sunday": "Sun", "sun": "Sun"
    }
    busy_day_normalized = day_map.get(busy_day.lower(), busy_day)

    # Normalize times to 24h format
    def parse_time(t):
        t = t.strip().lower()
        # Handle "9am", "11:00am", etc.
        if "am" in t or "pm" in t:
            is_pm = "pm" in t
            t = t.replace("am", "").replace("pm", "").strip()
            if ":" in t:
                h, m = t.split(":")
            else:
                h, m = t, "00"
            h = int(h)
            if is_pm and h != 12:
                h += 12
            elif not is_pm and h == 12:
                h = 0
            return f"{h:02d}:{m}"
        return t  # Already in HH:MM format

    busy_start_norm = parse_time(busy_start)
    busy_end_norm = parse_time(busy_end)

    # Get course schedule
    schedules = get_course_schedule(course_code, semester)

    if not schedules:
        return {
            "has_conflict": None,  # Unknown - no schedule data
            "course_schedule": None,
            "message": f"No schedule found for {course_code} in {semester}"
        }

    conflicts = []
    all_sections = []

    for sched in schedules:
        for section in sched.get("sections", []):
            days = section.get("days", [])
            start = section.get("start_time", "")
            end = section.get("end_time", "")

            all_sections.append({
                "days": days,
                "start_time": start,
                "end_time": end,
                "location": section.get("location", ""),
                "instructor": section.get("instructor", "")
            })

            # Check if this section conflicts
            if busy_day_normalized in days:
                # Check time overlap
                if start and end:
                    # Times overlap if: start1 < end2 and start2 < end1
                    if start < busy_end_norm and busy_start_norm < end:
                        conflicts.append({
                            "section": section,
                            "reason": f"Course meets {', '.join(days)} {start}-{end}, conflicts with your {busy_day} {busy_start}-{busy_end} availability"
                        })

    return {
        "has_conflict": len(conflicts) > 0,
        "course_schedule": all_sections,
        "conflicts": conflicts,
        "message": f"Found {len(conflicts)} conflicting section(s)" if conflicts else "No conflicts found"
    }


def search_courses_by_name(query: str, limit: int = 10) -> List[Dict]:
    """
    Search courses by name (partial match).
    Priority: exact name match > starts with > contains

    Args:
        query: Search term
        limit: Max results to return

    Returns:
        List of matching courses with code and name
    """
    exact_name_matches = []  # Name exactly equals query
    starts_with_matches = []  # Name starts with query
    contains_matches = []     # Name contains query
    query_lower = query.lower().strip()

    for code, course in DB["courses"].items():
        name = course.get("name") or ""
        if not name:
            continue
        name_lower = name.lower()

        course_info = {
            "code": code,
            "name": name,
            "units": course.get("units", course.get("min_units", ""))
        }

        # Exact name match (highest priority)
        if name_lower == query_lower:
            exact_name_matches.append(course_info)
        # Starts with query
        elif name_lower.startswith(query_lower):
            starts_with_matches.append(course_info)
        # Contains query
        elif query_lower in name_lower:
            contains_matches.append(course_info)

    # Return in priority order: exact > starts with > contains
    results = exact_name_matches + starts_with_matches + contains_matches
    return results[:limit]


# ============================================================================
# PREREQUISITE CHECKING
# ============================================================================

def get_course_prereqs(course_code: str) -> Dict[str, Any]:
    """
    Get prerequisite information for a course.

    Returns:
        {
            "course_code": str,
            "prereq_text": str,  # Raw prereq text
            "prereq_courses": List[str],  # List of all course codes mentioned
            "has_prereqs": bool
        }
    """
    course = DB["courses"].get(course_code)
    if not course:
        return {
            "course_code": course_code,
            "prereq_text": None,
            "prereq_courses": [],
            "has_prereqs": False,
            "error": f"Course {course_code} not found"
        }

    prereq_text = course.get("prereqs", {}).get("text", "")
    if not prereq_text:
        return {
            "course_code": course_code,
            "prereq_text": None,
            "prereq_courses": [],
            "has_prereqs": False
        }

    # Extract all course codes from prereq text
    prereq_courses = re.findall(r'\d{2}-\d{3}', prereq_text)

    return {
        "course_code": course_code,
        "prereq_text": prereq_text,
        "prereq_courses": list(set(prereq_courses)),
        "has_prereqs": len(prereq_courses) > 0
    }


def parse_prereq_expression(prereq_text: str) -> Dict[str, Any]:
    """
    Parse prerequisite text into a structured logical expression.

    Handles formats like:
    - "15-213 [] at least C"
    - "(A) or (B)"
    - "(A) and (B)"
    - "((A) or (B)) and (C)"

    Returns:
        {
            "type": "and" | "or" | "course" | "none",
            "courses": [...] for simple cases,
            "conditions": [...] for complex cases
        }
    """
    if not prereq_text:
        return {"type": "none", "courses": []}

    # Extract all course codes
    all_courses = re.findall(r'\d{2}-\d{3}', prereq_text)
    if not all_courses:
        return {"type": "none", "courses": []}

    # Simple case: single course
    if len(all_courses) == 1:
        return {"type": "course", "courses": all_courses}

    # Check for AND/OR at the top level (outside parentheses)
    # Count parentheses depth
    def split_at_top_level(text: str, operator: str) -> List[str]:
        """Split text by operator only when at parentheses depth 0."""
        parts = []
        current = ""
        depth = 0
        i = 0
        op_lower = operator.lower()

        while i < len(text):
            char = text[i]
            if char == '(':
                depth += 1
                current += char
            elif char == ')':
                depth -= 1
                current += char
            elif depth == 0 and text[i:i+len(operator)].lower() == op_lower:
                if current.strip():
                    parts.append(current.strip())
                current = ""
                i += len(operator) - 1  # Skip operator
            else:
                current += char
            i += 1

        if current.strip():
            parts.append(current.strip())

        return parts if len(parts) > 1 else []

    # Try AND first (higher precedence in evaluation)
    and_parts = split_at_top_level(prereq_text, " and ")
    if and_parts:
        return {
            "type": "and",
            "conditions": [parse_prereq_expression(p) for p in and_parts],
            "courses": all_courses
        }

    # Try OR
    or_parts = split_at_top_level(prereq_text, " or ")
    if or_parts:
        return {
            "type": "or",
            "conditions": [parse_prereq_expression(p) for p in or_parts],
            "courses": all_courses
        }

    # If no top-level operators, it might be a single course or wrapped expression
    # Strip outer parentheses and try again
    stripped = prereq_text.strip()
    if stripped.startswith('(') and stripped.endswith(')'):
        return parse_prereq_expression(stripped[1:-1])

    # Default: treat as list of courses (OR relationship assumed)
    return {"type": "or", "courses": all_courses}


def evaluate_prereq_expression(expr: Dict, completed_courses: List[str]) -> bool:
    """
    Evaluate if a prerequisite expression is satisfied.

    Args:
        expr: Parsed prerequisite expression from parse_prereq_expression()
        completed_courses: List of course codes the student has completed

    Returns:
        True if prerequisites are satisfied
    """
    completed_set = set(completed_courses)

    if expr["type"] == "none":
        return True

    if expr["type"] == "course":
        # Single course requirement
        return any(c in completed_set for c in expr.get("courses", []))

    if expr["type"] == "or":
        # OR: at least one condition must be true
        if "conditions" in expr:
            return any(evaluate_prereq_expression(cond, completed_courses)
                      for cond in expr["conditions"])
        else:
            # Simple OR of courses
            return any(c in completed_set for c in expr.get("courses", []))

    if expr["type"] == "and":
        # AND: all conditions must be true
        if "conditions" in expr:
            return all(evaluate_prereq_expression(cond, completed_courses)
                      for cond in expr["conditions"])
        else:
            # Simple AND of courses
            return all(c in completed_set for c in expr.get("courses", []))

    return True  # Default to satisfied if unknown


def check_prereqs_satisfied(course_code: str, completed_courses: List[str]) -> Dict[str, Any]:
    """
    Check if prerequisites for a course are satisfied.

    Args:
        course_code: Course to check prerequisites for
        completed_courses: List of courses the student has completed

    Returns:
        {
            "course_code": str,
            "satisfied": bool,
            "prereq_text": str,
            "required_courses": List[str],  # All courses mentioned in prereqs
            "completed": List[str],  # Which prereq courses are completed
            "missing": List[str],  # Which prereq courses are missing
            "reason": str  # Human-readable explanation
        }
    """
    prereq_info = get_course_prereqs(course_code)

    if "error" in prereq_info:
        return {
            "course_code": course_code,
            "satisfied": None,  # Unknown
            "reason": prereq_info["error"]
        }

    if not prereq_info["has_prereqs"]:
        return {
            "course_code": course_code,
            "satisfied": True,
            "prereq_text": None,
            "required_courses": [],
            "completed": [],
            "missing": [],
            "reason": "No prerequisites required"
        }

    prereq_text = prereq_info["prereq_text"]
    required_courses = prereq_info["prereq_courses"]
    completed_set = set(completed_courses)

    # Parse and evaluate
    expr = parse_prereq_expression(prereq_text)
    satisfied = evaluate_prereq_expression(expr, completed_courses)

    # Find which are completed/missing
    completed_prereqs = [c for c in required_courses if c in completed_set]
    missing_prereqs = [c for c in required_courses if c not in completed_set]

    if satisfied:
        reason = "Prerequisites satisfied"
    else:
        reason = f"Missing prerequisites: {', '.join(missing_prereqs)}"

    return {
        "course_code": course_code,
        "satisfied": satisfied,
        "prereq_text": prereq_text,
        "required_courses": required_courses,
        "completed": completed_prereqs,
        "missing": missing_prereqs,
        "reason": reason
    }


# ============================================================================
# COURSE-TO-COURSE CONFLICT DETECTION
# ============================================================================

def check_courses_conflict(course1: str, course2: str, semester: str) -> Dict[str, Any]:
    """
    Check if two courses have schedule conflicts in a given semester.

    Args:
        course1: First course code
        course2: Second course code
        semester: Semester to check (e.g., "spring_2026", "Fall 2025")

    Returns:
        {
            "has_conflict": bool,
            "course1_schedule": List of sections,
            "course2_schedule": List of sections,
            "conflicts": List of conflict details,
            "message": str
        }
    """
    sched1 = get_course_schedule(course1, semester)
    sched2 = get_course_schedule(course2, semester)

    if not sched1:
        return {
            "has_conflict": None,
            "message": f"No schedule found for {course1} in {semester}"
        }
    if not sched2:
        return {
            "has_conflict": None,
            "message": f"No schedule found for {course2} in {semester}"
        }

    conflicts = []

    # Compare all sections
    for s1 in sched1:
        for section1 in s1.get("sections", []):
            days1 = set(section1.get("days", []))
            start1 = section1.get("start_time", "")
            end1 = section1.get("end_time", "")

            for s2 in sched2:
                for section2 in s2.get("sections", []):
                    days2 = set(section2.get("days", []))
                    start2 = section2.get("start_time", "")
                    end2 = section2.get("end_time", "")

                    # Check for day overlap
                    common_days = days1 & days2
                    if not common_days:
                        continue

                    # Check for time overlap
                    if start1 and end1 and start2 and end2:
                        # Times overlap if: start1 < end2 and start2 < end1
                        if start1 < end2 and start2 < end1:
                            conflicts.append({
                                "days": list(common_days),
                                "course1": {
                                    "code": course1,
                                    "time": f"{start1}-{end1}"
                                },
                                "course2": {
                                    "code": course2,
                                    "time": f"{start2}-{end2}"
                                },
                                "reason": f"{course1} ({start1}-{end1}) overlaps with {course2} ({start2}-{end2}) on {', '.join(common_days)}"
                            })

    return {
        "has_conflict": len(conflicts) > 0,
        "course1": course1,
        "course2": course2,
        "semester": semester,
        "conflicts": conflicts,
        "message": f"Found {len(conflicts)} schedule conflict(s)" if conflicts else "No conflicts found"
    }


# ============================================================================
# PLAN VALIDATION
# ============================================================================

def validate_semester_plan(
    semester: str,
    courses: List[str],
    completed_courses: List[str]
) -> Dict[str, Any]:
    """
    Validate a single semester's course plan.

    Checks:
    1. Prerequisites are satisfied for each course
    2. No schedule conflicts between courses

    Args:
        semester: Semester name (e.g., "Fall 2025")
        courses: List of course codes planned for this semester
        completed_courses: Courses completed BEFORE this semester

    Returns:
        {
            "semester": str,
            "courses": List[str],
            "valid": bool,
            "prereq_violations": List of violations,
            "schedule_conflicts": List of conflicts,
            "warnings": List of warnings
        }
    """
    prereq_violations = []
    schedule_conflicts = []
    warnings = []

    # Check prerequisites for each course
    for course in courses:
        prereq_check = check_prereqs_satisfied(course, completed_courses)
        if prereq_check.get("satisfied") is False:
            prereq_violations.append({
                "course": course,
                "missing": prereq_check.get("missing", []),
                "prereq_text": prereq_check.get("prereq_text", ""),
                "reason": prereq_check.get("reason", "")
            })
        elif prereq_check.get("satisfied") is None:
            warnings.append(f"Could not verify prerequisites for {course}")

    # Check for schedule conflicts between all pairs of courses
    semester_normalized = semester.lower().replace(" ", "_")
    checked_pairs = set()

    for i, course1 in enumerate(courses):
        for course2 in courses[i+1:]:
            pair = tuple(sorted([course1, course2]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            conflict_check = check_courses_conflict(course1, course2, semester_normalized)
            if conflict_check.get("has_conflict"):
                schedule_conflicts.append({
                    "courses": [course1, course2],
                    "conflicts": conflict_check.get("conflicts", []),
                    "message": conflict_check.get("message", "")
                })
            elif conflict_check.get("has_conflict") is None:
                warnings.append(f"Could not verify schedule for {course1} or {course2} in {semester}")

    return {
        "semester": semester,
        "courses": courses,
        "valid": len(prereq_violations) == 0 and len(schedule_conflicts) == 0,
        "prereq_violations": prereq_violations,
        "schedule_conflicts": schedule_conflicts,
        "warnings": warnings
    }


def validate_full_plan(
    plan: List[Dict],
    initial_completed_courses: List[str] = None
) -> Dict[str, Any]:
    """
    Validate a full multi-semester academic plan.

    Args:
        plan: List of semester plans, each with:
            {"semester": "Fall 2025", "courses": ["15-112", "21-127", ...]}
        initial_completed_courses: Courses already completed before the plan

    Returns:
        {
            "valid": bool,
            "semester_results": List of per-semester validation results,
            "total_prereq_violations": int,
            "total_schedule_conflicts": int,
            "summary": str
        }
    """
    completed = list(initial_completed_courses or [])
    semester_results = []
    total_prereq_violations = 0
    total_schedule_conflicts = 0

    for semester_plan in plan:
        semester = semester_plan.get("semester", "Unknown")
        courses = semester_plan.get("courses", [])

        # Validate this semester
        result = validate_semester_plan(semester, courses, completed)
        semester_results.append(result)

        total_prereq_violations += len(result["prereq_violations"])
        total_schedule_conflicts += len(result["schedule_conflicts"])

        # Add this semester's courses to completed for next semester
        completed.extend(courses)

    valid = total_prereq_violations == 0 and total_schedule_conflicts == 0

    if valid:
        summary = "Plan is valid: all prerequisites satisfied, no schedule conflicts"
    else:
        issues = []
        if total_prereq_violations > 0:
            issues.append(f"{total_prereq_violations} prerequisite violation(s)")
        if total_schedule_conflicts > 0:
            issues.append(f"{total_schedule_conflicts} schedule conflict(s)")
        summary = f"Plan has issues: {', '.join(issues)}"

    return {
        "valid": valid,
        "semester_results": semester_results,
        "total_prereq_violations": total_prereq_violations,
        "total_schedule_conflicts": total_schedule_conflicts,
        "summary": summary
    }
