"""
Course Name to Code Mapping

Maps common course names to official course codes.
"""

# Common course name variations
COURSE_NAME_MAPPING = {
    # Biology courses
    "honors modern bio": "03-121",
    "modern biology": "03-121",
    "honors modern biology": "03-121",
    "intro bio": "03-121",
    "modern bio": "03-121",
    "genetics": "03-251",
    "biochemistry": "03-231",
    "cell biology": "03-232",
    
    # CS courses
    "fundamentals": "15-112",
    "principles of imperative computation": "15-122",
    "principles of functional programming": "15-150",
    "computer systems": "15-213",
    "algorithms": "15-210",
    "parallel and sequential algorithms": "15-210",
    "great theoretical ideas": "15-251",
    "discrete math": "21-127",
    
    # IS courses
    "intro to is": "67-250",
    "information systems": "67-250",
    
    # Business courses
    "marketing": "70-381",
    "strategy": "70-387",
    
    # Math courses
    "calc": "21-120",
    "calculus": "21-120",
    "integration and approximation": "21-122",
    "linear algebra": "21-241",
    "matrices": "21-241",
    
    # Communication courses
    "professional writing": "76-100",
    "technical writing": "76-100",
    "interpretation and argument": "76-101",
}

def get_course_code(course_name: str) -> str:
    """
    Get course code from course name.
    
    Args:
        course_name: Course name (case insensitive)
    
    Returns:
        Course code if found, else original name
    """
    # Normalize: lowercase, strip whitespace
    normalized = course_name.lower().strip()
    
    # Direct lookup
    if normalized in COURSE_NAME_MAPPING:
        return COURSE_NAME_MAPPING[normalized]
    
    # Try partial match (for longer names)
    for name, code in COURSE_NAME_MAPPING.items():
        if name in normalized or normalized in name:
            return code
    
    # No match found
    return course_name

def infer_major_from_course(course_name: str) -> str:
    """
    Infer likely major from course name/code.
    
    Args:
        course_name: Course name or code
    
    Returns:
        Likely major name or "Unknown"
    """
    normalized = course_name.lower().strip()
    
    # Check by course code prefix
    if normalized.startswith("03-") or "bio" in normalized or "genetics" in normalized:
        return "Biological Sciences"
    elif normalized.startswith("15-") or "computer" in normalized or "algorithms" in normalized:
        return "Computer Science"
    elif normalized.startswith("67-") or "information systems" in normalized:
        return "Information Systems"
    elif normalized.startswith("70-") or "marketing" in normalized or "strategy" in normalized or "business" in normalized:
        return "Business Administration"
    elif normalized.startswith("76-") or "writing" in normalized:
        return "Unknown"  # Communication courses are for all majors
    
    return "Unknown"
