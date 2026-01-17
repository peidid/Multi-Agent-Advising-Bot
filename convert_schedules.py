"""
Convert schedule files (CSV, XLSX) to structured JSON format for academic planning.

This script processes CMU-Q course schedule data and outputs standardized JSON
files that can be used by the multi-agent advising system.
"""

import os
import json
import csv
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Try to import pandas for xlsx support
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    print("Warning: pandas not installed. XLSX files will be skipped.")

# ============================================================================
# CONFIGURATION
# ============================================================================

SCHEDULE_INPUT_DIR = "./data/courses/Schedule"
SCHEDULE_OUTPUT_DIR = "./data/schedules"

# Day name mappings
DAY_MAPPINGS = {
    'Sunday': 'Sun', 'Sun': 'Sun', 'S': 'Sun', 'U': 'Sun',
    'Monday': 'Mon', 'Mon': 'Mon', 'M': 'Mon',
    'Tuesday': 'Tue', 'Tue': 'Tue', 'T': 'Tue',
    'Wednesday': 'Wed', 'Wed': 'Wed', 'W': 'Wed',
    'Thursday': 'Thu', 'Thu': 'Thu', 'R': 'Thu',
    'Friday': 'Fri', 'Fri': 'Fri', 'F': 'Fri',
    'Saturday': 'Sat', 'Sat': 'Sat'
}

# Department code to prefix mapping
DEPT_PREFIXES = {
    'CB': '02', 'BSC': '03', 'HCI': '05', 'SCS': '07', 'CMY': '09',
    'INI': '14', 'CS': '15', 'S3D': '17', 'MSC': '21', 'PHY': '33',
    'STA': '36', 'MCS': '38', 'ARC': '48', 'HSS': '66', 'ISP': '67',
    'PE': '69', 'BUS': '70', 'ECO': '73', 'ENG': '76', 'HIS': '79',
    'PHI': '80', 'LCL': '82', 'PSY': '85', 'ISM': '95', 'STU': '98',
    'CMU': '99', 'COR': 'QC'
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def normalize_day(day: str) -> Optional[str]:
    """Normalize day name to standard 3-letter format."""
    day = day.strip()
    return DAY_MAPPINGS.get(day, day if len(day) == 3 else None)

def parse_time(time_str: str) -> Optional[str]:
    """Parse time string to HH:MM format."""
    if not time_str or not time_str.strip():
        return None
    
    time_str = time_str.strip()
    
    # Handle various formats
    if ':' in time_str:
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return f"{hour:02d}:{minute:02d}"
    
    return time_str

def parse_multiline_field(field: str) -> List[str]:
    """Parse a field that may contain newline-separated values."""
    if not field:
        return []
    
    # Split by newlines and filter empty
    values = [v.strip() for v in str(field).split('\n') if v.strip()]
    return values

def build_course_code(dept: str, course_id: str) -> str:
    """Build full course code from department and ID."""
    prefix = DEPT_PREFIXES.get(dept, dept)
    
    # Pad course ID if needed
    if course_id.isdigit():
        course_id = course_id.zfill(3)
    
    return f"{prefix}-{course_id}"

# ============================================================================
# CSV PARSING
# ============================================================================

def parse_csv_schedule(csv_path: str) -> Dict[str, Any]:
    """Parse CMU-Q schedule CSV file."""
    
    offerings = defaultdict(lambda: {"sections": []})
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Read entire content first to handle multi-line cells
        content = f.read()
    
    # Use csv reader with proper handling
    lines = content.split('\n')
    
    # Manual parsing due to multi-line cells
    current_row = []
    in_quotes = False
    rows = []
    header = None
    
    for line in lines:
        if not header and line.startswith('State'):
            header = line.split(',')
            continue
        
        # Track if we're in a multi-line cell
        quote_count = line.count('"')
        
        if in_quotes:
            current_row[-1] += '\n' + line
            if quote_count % 2 == 1:
                in_quotes = False
                rows.append(current_row)
                current_row = []
        else:
            parts = line.split(',')
            
            # Check for embedded quotes indicating multi-line
            if quote_count % 2 == 1:
                in_quotes = True
                current_row = parts
            else:
                rows.append(parts)
    
    # Process rows
    for row in rows:
        if len(row) < 15:
            continue
        
        try:
            state = row[0].strip() if row[0] else ''
            dept = row[3].strip() if len(row) > 3 else ''
            course_id = row[4].strip() if len(row) > 4 else ''
            section_id = row[5].strip() if len(row) > 5 else ''
            delivery = row[9].strip() if len(row) > 9 else ''
            days_raw = row[10] if len(row) > 10 else ''
            duration_raw = row[11] if len(row) > 11 else ''
            start_time_raw = row[12] if len(row) > 12 else ''
            end_time_raw = row[13] if len(row) > 13 else ''
            room = row[15].strip() if len(row) > 15 else ''
            instructor = row[16].strip() if len(row) > 16 else ''
            capacity = row[17].strip() if len(row) > 17 else ''
            start_date = row[18].strip() if len(row) > 18 else ''
            end_date = row[19].strip() if len(row) > 19 else ''
            
            # Skip disabled or invalid
            if state != 'Enabled' or not course_id:
                continue
            
            # Build course code
            course_code = build_course_code(dept, course_id)
            
            # Parse days
            days = []
            for d in parse_multiline_field(days_raw):
                normalized = normalize_day(d)
                if normalized:
                    days.append(normalized)
            
            # Get first start/end time (primary time)
            start_times = parse_multiline_field(start_time_raw)
            end_times = parse_multiline_field(end_time_raw)
            
            start_time = parse_time(start_times[0]) if start_times else None
            end_time = parse_time(end_times[0]) if end_times else None
            
            # Parse capacity
            try:
                cap = int(capacity) if capacity else 0
            except:
                cap = 0
            
            # Add section
            section = {
                "section": section_id,
                "days": list(set(days)),  # Remove duplicates
                "start_time": start_time,
                "end_time": end_time,
                "location": room,
                "instructor": instructor.replace('\n', ', '),  # Handle multi-instructor
                "capacity": cap,
                "delivery": delivery
            }
            
            offerings[course_code]["course_code"] = course_code
            offerings[course_code]["sections"].append(section)
            
        except Exception as e:
            continue  # Skip problematic rows
    
    return dict(offerings)

# ============================================================================
# XLSX PARSING
# ============================================================================

def parse_xlsx_schedule(xlsx_path: str) -> Dict[str, Any]:
    """Parse CMU-Q schedule XLSX file."""
    
    if not HAS_PANDAS:
        print(f"Skipping {xlsx_path}: pandas not installed")
        return {}
    
    try:
        df = pd.read_excel(xlsx_path)
    except Exception as e:
        print(f"Error reading {xlsx_path}: {e}")
        return {}
    
    offerings = defaultdict(lambda: {"sections": []})
    
    # Try to identify columns
    columns = df.columns.tolist()
    
    # Map column names (handle variations)
    col_map = {}
    for col in columns:
        col_lower = str(col).lower()
        if 'course' in col_lower and 'id' in col_lower:
            col_map['course_id'] = col
        elif 'department' in col_lower or 'dept' in col_lower:
            col_map['dept'] = col
        elif 'section' in col_lower:
            col_map['section'] = col
        elif 'day' in col_lower:
            col_map['days'] = col
        elif 'start' in col_lower and 'time' in col_lower:
            col_map['start_time'] = col
        elif 'end' in col_lower and 'time' in col_lower:
            col_map['end_time'] = col
        elif 'room' in col_lower or 'location' in col_lower:
            col_map['room'] = col
        elif 'instructor' in col_lower or 'professor' in col_lower:
            col_map['instructor'] = col
        elif 'capacity' in col_lower or 'enrollment' in col_lower:
            col_map['capacity'] = col
    
    for idx, row in df.iterrows():
        try:
            dept = str(row.get(col_map.get('dept', ''), '')).strip()
            course_id = str(row.get(col_map.get('course_id', ''), '')).strip()
            
            if not course_id or course_id == 'nan':
                continue
            
            course_code = build_course_code(dept, course_id) if dept else course_id
            
            section = {
                "section": str(row.get(col_map.get('section', ''), 'W')).strip(),
                "days": parse_multiline_field(str(row.get(col_map.get('days', ''), ''))),
                "start_time": parse_time(str(row.get(col_map.get('start_time', ''), ''))),
                "end_time": parse_time(str(row.get(col_map.get('end_time', ''), ''))),
                "location": str(row.get(col_map.get('room', ''), '')).strip(),
                "instructor": str(row.get(col_map.get('instructor', ''), '')).strip(),
                "capacity": int(row.get(col_map.get('capacity', ''), 0) or 0)
            }
            
            offerings[course_code]["course_code"] = course_code
            offerings[course_code]["sections"].append(section)
            
        except Exception as e:
            continue
    
    return dict(offerings)

# ============================================================================
# MAIN CONVERSION
# ============================================================================

def create_schedule_json(offerings: Dict, term: str, year: int) -> Dict:
    """Create standardized schedule JSON structure."""
    
    # Convert offerings dict to list
    offerings_list = []
    for course_code, data in sorted(offerings.items()):
        # Deduplicate sections
        seen_sections = set()
        unique_sections = []
        
        for section in data.get("sections", []):
            section_key = (
                section.get("section", ""),
                tuple(section.get("days", [])),
                section.get("start_time", ""),
                section.get("end_time", "")
            )
            
            if section_key not in seen_sections:
                seen_sections.add(section_key)
                unique_sections.append(section)
        
        if unique_sections:
            offerings_list.append({
                "course_code": course_code,
                "sections": unique_sections
            })
    
    return {
        "semester": {
            "term": term,
            "year": year,
            "academic_year": f"{year}-{year+1}" if term == "Fall" else f"{year-1}-{year}"
        },
        "total_courses": len(offerings_list),
        "offerings": offerings_list,
        "metadata": {
            "generated_by": "convert_schedules.py",
            "source": "CMU-Q Schedule Data"
        }
    }

def extract_term_year(filename: str) -> tuple:
    """Extract term and year from filename."""
    # Patterns: "Fall 2025.xlsx", "Spring2026.csv", etc.
    filename_lower = filename.lower()
    
    term = "Spring" if "spring" in filename_lower else "Fall"
    
    # Extract year
    year_match = re.search(r'(\d{4})', filename)
    year = int(year_match.group(1)) if year_match else 2026
    
    return term, year

def convert_all_schedules():
    """Convert all schedule files in the input directory."""
    
    os.makedirs(SCHEDULE_OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("CONVERTING SCHEDULE FILES TO JSON")
    print("=" * 70)
    
    input_files = os.listdir(SCHEDULE_INPUT_DIR)
    converted = []
    
    for filename in input_files:
        filepath = os.path.join(SCHEDULE_INPUT_DIR, filename)
        
        if filename.endswith('.csv'):
            print(f"\n📄 Processing CSV: {filename}")
            offerings = parse_csv_schedule(filepath)
            
        elif filename.endswith('.xlsx'):
            print(f"\n📄 Processing XLSX: {filename}")
            offerings = parse_xlsx_schedule(filepath)
            
        elif filename.endswith('.json'):
            print(f"\n📄 Skipping existing JSON: {filename}")
            continue
            
        else:
            continue
        
        if offerings:
            term, year = extract_term_year(filename)
            schedule_json = create_schedule_json(offerings, term, year)
            
            # Output filename
            output_filename = f"schedule_{year}_{term.lower()}.json"
            output_path = os.path.join(SCHEDULE_OUTPUT_DIR, output_filename)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(schedule_json, f, indent=2, ensure_ascii=False)
            
            print(f"   ✅ Created: {output_filename}")
            print(f"   📊 Courses: {schedule_json['total_courses']}")
            converted.append(output_filename)
        else:
            print(f"   ⚠️  No data extracted from {filename}")
    
    # Create course offering patterns from all schedules
    create_offering_patterns(converted)
    
    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"\n📁 Output directory: {SCHEDULE_OUTPUT_DIR}")
    print(f"📄 Files created: {len(converted)}")

def create_offering_patterns(schedule_files: List[str]):
    """Analyze schedules to create offering pattern file."""
    
    patterns = defaultdict(lambda: {"fall": False, "spring": False, "instructors": set()})
    
    for filename in schedule_files:
        filepath = os.path.join(SCHEDULE_OUTPUT_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            continue
        
        term = data.get("semester", {}).get("term", "").lower()
        
        for offering in data.get("offerings", []):
            course_code = offering.get("course_code", "")
            
            if term == "fall":
                patterns[course_code]["fall"] = True
            elif term == "spring":
                patterns[course_code]["spring"] = True
            
            for section in offering.get("sections", []):
                instructor = section.get("instructor", "")
                if instructor:
                    patterns[course_code]["instructors"].add(instructor)
    
    # Convert to serializable format
    output_patterns = {}
    for course_code, data in sorted(patterns.items()):
        output_patterns[course_code] = {
            "fall": data["fall"],
            "spring": data["spring"],
            "frequency": determine_frequency(data["fall"], data["spring"]),
            "typical_instructors": list(data["instructors"])[:3]  # Top 3
        }
    
    # Save patterns
    patterns_path = os.path.join(SCHEDULE_OUTPUT_DIR, "course_offering_patterns.json")
    with open(patterns_path, 'w', encoding='utf-8') as f:
        json.dump({
            "description": "Course offering patterns based on historical schedule data",
            "patterns": output_patterns
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n   ✅ Created: course_offering_patterns.json")
    print(f"   📊 Courses tracked: {len(output_patterns)}")

def determine_frequency(fall: bool, spring: bool) -> str:
    """Determine offering frequency based on semester data."""
    if fall and spring:
        return "every_semester"
    elif fall:
        return "fall_only"
    elif spring:
        return "spring_only"
    else:
        return "unknown"

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    convert_all_schedules()
