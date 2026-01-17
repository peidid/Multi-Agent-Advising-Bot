"""
Planning Tools and Utilities

Helper functions for academic planning:
- Prerequisite checking
- Course offering pattern analysis
- Workload calculation
- Semester scheduling
"""

import json
import os
import re
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


# ============================================================================
# Course Data Loading
# ============================================================================

def load_course_schedules() -> Dict[str, dict]:
    """Load all available course schedules."""
    schedules = {}

    # Check multiple possible locations
    search_dirs = [
        "./data/schedules",
        "./data/courses/Schedule",
        "./data/courses/schedule"
    ]

    for schedule_dir in search_dirs:
        if not os.path.exists(schedule_dir):
            continue

        for filename in os.listdir(schedule_dir):
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(schedule_dir, filename)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Extract term identifier
                if "semester" in data:
                    term = data["semester"]
                    key = f"{term.get('year', '')}_{term.get('term', '')}".lower()
                    schedules[key] = data

            except Exception as e:
                print(f"Warning: Could not load {filename}: {e}")

    return schedules


def load_program_requirements(program_name: str) -> Optional[dict]:
    """Load degree requirements for a specific program."""

    # Map common program names to file patterns
    program_map = {
        "computer science": "computer_science",
        "cs": "computer_science",
        "information systems": "information_systems",
        "is": "information_systems",
        "business": "business_administration"
    }

    search_pattern = program_map.get(program_name.lower(), program_name.lower())

    # Search in program directories
    programs_dir = "./data/programs"

    if not os.path.exists(programs_dir):
        return None

    for root, dirs, files in os.walk(programs_dir):
        for filename in files:
            if filename.endswith('_degree_requirements.json'):
                if search_pattern in filename.lower():
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except:
                        continue

    return None


def load_sample_curriculum(program_name: str) -> Optional[List[dict]]:
    """Load sample curriculum for a program."""

    program_map = {
        "computer science": "CS",
        "cs": "CS",
        "information systems": "IS",
        "is": "IS",
        "business": "BA"
    }

    search_pattern = program_map.get(program_name.lower(), program_name)

    programs_dir = "./data/programs"

    if not os.path.exists(programs_dir):
        return None

    for root, dirs, files in os.walk(programs_dir):
        for filename in files:
            if 'sample_curriculum' in filename.lower() and filename.endswith('.json'):
                if search_pattern in filename:
                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    except:
                        continue

    return None


# ============================================================================
# Course Offering Analysis
# ============================================================================

def analyze_course_offerings(schedules: Dict[str, dict]) -> Dict[str, dict]:
    """Analyze when courses are typically offered."""

    offering_patterns = defaultdict(lambda: {
        "fall": False,
        "spring": False,
        "semesters_offered": [],
        "instructors": set(),
        "sections": []
    })

    for schedule_key, schedule_data in schedules.items():
        term = schedule_data.get("semester", {})
        term_name = term.get("term", "").lower()
        year = term.get("year", "")

        for offering in schedule_data.get("offerings", []):
            course_code = offering.get("course_code", "")

            if not course_code:
                continue

            # Mark semester type
            if "fall" in term_name:
                offering_patterns[course_code]["fall"] = True
            elif "spring" in term_name:
                offering_patterns[course_code]["spring"] = True

            # Record specific semester
            offering_patterns[course_code]["semesters_offered"].append(
                f"{term_name.title()} {year}"
            )

            # Collect instructors
            for section in offering.get("sections", []):
                instructor = section.get("instructor", "")
                if instructor:
                    offering_patterns[course_code]["instructors"].add(instructor)

    # Convert sets to lists for JSON serialization
    result = {}
    for course_code, data in offering_patterns.items():
        result[course_code] = {
            "fall": data["fall"],
            "spring": data["spring"],
            "frequency": _determine_frequency(data["fall"], data["spring"]),
            "semesters_offered": data["semesters_offered"],
            "typical_instructors": list(data["instructors"])[:3]
        }

    return result


def _determine_frequency(fall: bool, spring: bool) -> str:
    """Determine offering frequency."""
    if fall and spring:
        return "every_semester"
    elif fall:
        return "fall_only"
    elif spring:
        return "spring_only"
    else:
        return "unknown"


def get_course_availability(course_code: str, semester: str,
                            schedules: Dict[str, dict]) -> bool:
    """Check if a course is available in a specific semester."""

    # semester format: "2026_spring" or "fall_2025"
    semester_key = semester.lower().replace(" ", "_")

    if semester_key in schedules:
        schedule = schedules[semester_key]
        for offering in schedule.get("offerings", []):
            if offering.get("course_code") == course_code:
                return True

    return False


# ============================================================================
# Prerequisite Checking
# ============================================================================

def extract_prerequisites(course_description: str) -> List[str]:
    """Extract prerequisite course codes from description text."""

    prereqs = []

    # Common patterns
    patterns = [
        r'prerequisite[s]?:?\s*([0-9\-,\s]+)',
        r'requires?:?\s*([0-9\-,\s]+)',
        r'must have completed:?\s*([0-9\-,\s]+)'
    ]

    for pattern in patterns:
        matches = re.findall(pattern, course_description, re.IGNORECASE)
        for match in matches:
            # Extract course codes
            codes = re.findall(r'\d{2}-\d{3}', match)
            prereqs.extend(codes)

    return list(set(prereqs))


def check_prerequisites_met(course_code: str, completed_courses: List[str],
                            prereq_map: Dict[str, List[str]]) -> Tuple[bool, List[str]]:
    """Check if prerequisites are met for a course."""

    required = prereq_map.get(course_code, [])

    if not required:
        return True, []

    missing = [req for req in required if req not in completed_courses]

    return len(missing) == 0, missing


# ============================================================================
# Workload Calculation
# ============================================================================

def calculate_semester_units(courses: List[str], unit_map: Dict[str, int]) -> int:
    """Calculate total units for a list of courses."""

    total = 0
    for course in courses:
        total += unit_map.get(course, 12)  # Default 12 units

    return total


def is_overload(total_units: int, max_units: int = 54) -> bool:
    """Check if semester is an overload."""
    return total_units > max_units


def recommend_workload(student_gpa: float = None,
                       preference: str = "balanced") -> Tuple[int, int]:
    """Recommend min/max units based on student profile and preferences."""

    if preference == "light":
        return 36, 48
    elif preference == "heavy":
        return 48, 60
    else:  # balanced
        return 45, 54


# ============================================================================
# Plan Generation Helpers
# ============================================================================

def generate_semester_sequence(start_term: str, num_semesters: int) -> List[str]:
    """Generate sequence of semester names."""

    # Parse start term
    parts = start_term.lower().split()

    if "fall" in start_term.lower():
        current_term = "Fall"
        year_match = re.search(r'(\d{4})', start_term)
        current_year = int(year_match.group(1)) if year_match else 2026
    else:
        current_term = "Spring"
        year_match = re.search(r'(\d{4})', start_term)
        current_year = int(year_match.group(1)) if year_match else 2026

    sequence = []

    for i in range(num_semesters):
        sequence.append(f"{current_term} {current_year}")

        # Alternate semesters
        if current_term == "Fall":
            current_term = "Spring"
            current_year += 1
        else:
            current_term = "Fall"

    return sequence


def validate_plan(plan: Dict, requirements: Dict) -> Tuple[bool, List[str]]:
    """Validate a plan against degree requirements."""

    issues = []

    # Extract all courses in plan
    all_courses = set()
    for semester in plan.get("semesters", []):
        all_courses.update(semester.get("courses", []))

    # Check core requirements
    # This is simplified - you'd need to check against actual requirement structure

    return len(issues) == 0, issues


# ============================================================================
# Export Functions
# ============================================================================

def export_plan_to_json(plan: Dict, output_path: str):
    """Export a plan to JSON file."""

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)


def format_plan_for_display(plan: Dict) -> str:
    """Format plan for human-readable display."""

    output_lines = []

    output_lines.append(f"ACADEMIC PLAN: {plan.get('title', 'Untitled')}")
    output_lines.append(f"Program: {plan.get('program', 'N/A')}")
    output_lines.append("=" * 70)

    for semester in plan.get("semesters", []):
        term = semester.get("term", "")
        courses = semester.get("courses", [])
        units = semester.get("total_units", 0)

        output_lines.append(f"\n{term} ({units} units):")

        for course in courses:
            if isinstance(course, dict):
                code = course.get("code", "")
                title = course.get("title", "")
                course_units = course.get("units", "")
                output_lines.append(f"  - {code}: {title} ({course_units} units)")
            else:
                output_lines.append(f"  - {course}")

    return "\n".join(output_lines)
