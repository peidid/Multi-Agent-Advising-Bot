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
    """Extract course codes (e.g., 15-112) from text."""
    return re.findall(r"\d{2}-\d{3}", text)


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

    Args:
        query: Search term
        limit: Max results to return

    Returns:
        List of matching courses with code and name
    """
    results = []
    query_lower = query.lower()

    for code, course in DB["courses"].items():
        name = course.get("name", "")
        if query_lower in name.lower():
            results.append({
                "code": code,
                "name": name,
                "units": course.get("units", course.get("min_units", ""))
            })
            if len(results) >= limit:
                break

    return results
