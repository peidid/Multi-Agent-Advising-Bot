"""
Process all schedule CSV files and generate JSON schedules + update offering patterns.
"""

import os
import json
import csv
import re
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Configuration
SCHEDULE_INPUT_DIR = "./data/courses/schedule"
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

def normalize_day(day: str) -> Optional[str]:
    """Normalize day name to standard 3-letter format."""
    if not day:
        return None
    day = day.strip()
    return DAY_MAPPINGS.get(day, day if len(day) == 3 else None)

def parse_time(time_str: str) -> Optional[str]:
    """Parse time string to HH:MM format."""
    if not time_str or not time_str.strip() or time_str.strip().lower() == 'nan':
        return None
    
    time_str = str(time_str).strip()
    
    # Handle various formats
    if ':' in time_str:
        parts = time_str.split(':')
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return f"{hour:02d}:{minute:02d}"
        except:
            return None
    
    return None

def parse_multiline_field(field: str) -> List[str]:
    """Parse a field that may contain newline-separated values."""
    if not field or str(field).strip().lower() == 'nan':
        return []
    
    values = [v.strip() for v in str(field).split('\n') if v.strip() and v.strip().lower() != 'nan']
    return values

def build_course_code(dept: str, course_id: str) -> Optional[str]:
    """Build full course code from department and ID."""
    if not course_id or not str(course_id).strip():
        return None
    
    course_id = str(course_id).strip()
    
    # Handle course IDs that already include department (e.g., "03121" from Fall 2025)
    if len(course_id) >= 5 and course_id[:2].isdigit():
        # Already has prefix
        prefix = course_id[:2]
        course_num = course_id[2:]
        return f"{prefix}-{course_num}"
    
    # Need department prefix
    if not dept:
        return None
    
    prefix = DEPT_PREFIXES.get(dept, dept)
    
    # Pad course ID if needed
    if course_id.isdigit():
        course_id = course_id.zfill(3)
    
    return f"{prefix}-{course_id}"

def parse_csv_schedule_v1(csv_path: str) -> Dict[str, Any]:
    """Parse CSV with Department - ID and Course - ID columns (Spring 2025, Fall 2024)."""
    offerings = defaultdict(lambda: {"sections": []})
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                dept = row.get('Department - ID', '').strip()
                course_id = row.get('Course - ID', '').strip()
                section_id = row.get('Section - ID', row.get('Section', 'W')).strip()
                delivery = row.get('Delivery method', '').strip()
                days_raw = row.get('Delivery times - Day', '')
                start_time_raw = row.get('Delivery times - Start time', '')
                end_time_raw = row.get('Delivery times - End time', '')
                room = row.get('Assigned room - ID', '').strip()
                instructor = row.get('Professor - Last name', '').strip()
                capacity = row.get('Component - Scheduling enrollment', 
                                  row.get('MAX CAPACITY', 
                                         row.get('Max Enrollment', '0'))).strip()
                
                if not course_id or not dept:
                    continue
                
                course_code = build_course_code(dept, course_id)
                if not course_code:
                    continue
                
                # Parse days
                days = []
                for d in parse_multiline_field(days_raw):
                    normalized = normalize_day(d)
                    if normalized:
                        days.append(normalized)
                
                start_times = parse_multiline_field(start_time_raw)
                end_times = parse_multiline_field(end_time_raw)
                
                start_time = parse_time(start_times[0]) if start_times else None
                end_time = parse_time(end_times[0]) if end_times else None
                
                try:
                    cap = int(capacity) if capacity else 0
                except:
                    cap = 0
                
                section = {
                    "section": section_id if section_id else "W",
                    "days": list(set(days)),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": room,
                    "instructor": instructor.replace('\n', ', '),
                    "capacity": cap,
                    "delivery": delivery if delivery else "In class"
                }
                
                offerings[course_code]["course_code"] = course_code
                offerings[course_code]["sections"].append(section)
                
            except Exception as e:
                continue
    
    return dict(offerings)

def parse_csv_schedule_v2(csv_path: str) -> Dict[str, Any]:
    """Parse CSV with Course - ID column (Fall 2025 format)."""
    offerings = defaultdict(lambda: {"sections": []})
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                course_id_full = row.get('Course - ID', '').strip()
                section_id = row.get('Section', 'W').strip()
                delivery = row.get('Delivery method', '').strip()
                days_raw = row.get('Delivery times - Day', '')
                start_time_raw = row.get('Delivery times - Start time', '')
                end_time_raw = row.get('Delivery times - End time', '')
                room = row.get('Assigned room - ID', '').strip()
                instructor = row.get('Professor - Last name', '').strip()
                capacity = row.get('Max Enrollment', '0').strip()
                
                if not course_id_full:
                    continue
                
                # Course ID already includes department (e.g., "03121")
                if len(course_id_full) >= 5 and course_id_full[:2].isdigit():
                    prefix = course_id_full[:2]
                    course_num = course_id_full[2:]
                    course_code = f"{prefix}-{course_num}"
                else:
                    continue
                
                # Parse days
                days = []
                for d in parse_multiline_field(days_raw):
                    normalized = normalize_day(d)
                    if normalized:
                        days.append(normalized)
                
                start_times = parse_multiline_field(start_time_raw)
                end_times = parse_multiline_field(end_time_raw)
                
                start_time = parse_time(start_times[0]) if start_times else None
                end_time = parse_time(end_times[0]) if end_times else None
                
                try:
                    cap = int(capacity) if capacity else 0
                except:
                    cap = 0
                
                section = {
                    "section": section_id if section_id else "W",
                    "days": list(set(days)),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": room,
                    "instructor": instructor.replace('\n', ', '),
                    "capacity": cap,
                    "delivery": delivery if delivery else "In class"
                }
                
                offerings[course_code]["course_code"] = course_code
                offerings[course_code]["sections"].append(section)
                
            except Exception as e:
                continue
    
    return dict(offerings)

def parse_csv_schedule(csv_path: str) -> Dict[str, Any]:
    """Auto-detect CSV format and parse accordingly."""
    # Read first few lines to detect format
    with open(csv_path, 'r', encoding='utf-8') as f:
        first_line = f.readline()
        second_line = f.readline()
    
    # Check if it has "Department - ID" column
    if 'Department - ID' in first_line:
        return parse_csv_schedule_v1(csv_path)
    elif 'Course - ID' in first_line and 'Department' not in first_line:
        return parse_csv_schedule_v2(csv_path)
    else:
        # Try v1 format (most common)
        return parse_csv_schedule_v1(csv_path)

def extract_term_year(filename: str) -> tuple:
    """Extract term and year from filename."""
    filename_lower = filename.lower()
    
    term = "Spring" if "spring" in filename_lower else "Fall"
    
    # Extract year
    year_match = re.search(r'(\d{4})', filename)
    year = int(year_match.group(1)) if year_match else 2026
    
    return term, year

def create_schedule_json(offerings: Dict, term: str, year: int) -> Dict:
    """Create standardized schedule JSON structure."""
    
    offerings_list = []
    for course_code, data in sorted(offerings.items()):
        # Deduplicate sections
        seen_sections = set()
        unique_sections = []
        
        for section in data.get("sections", []):
            section_key = (
                section.get("section", ""),
                tuple(sorted(section.get("days", []))),
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
            "generated_by": "process_all_schedules.py",
            "source": "CMU-Q Schedule Data"
        }
    }

def process_all_schedules():
    """Process all schedule files."""
    os.makedirs(SCHEDULE_OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("PROCESSING ALL SCHEDULE FILES")
    print("=" * 70)
    
    csv_files = [
        ("Fall 2024.xlsx - CMU-Q Fall 2024 Courses Schedul.csv", "Fall", 2024),
        ("Fall 2025 - 2025_03_04.csv", "Fall", 2025),
        ("Spring2025.xlsx - Sp25 Schedule Draft 102124 430p.csv", "Spring", 2025),
        ("Spring2026.csv", "Spring", 2026),
    ]
    
    all_offerings = {}  # Track all courses across semesters
    
    for filename, term, year in csv_files:
        filepath = os.path.join(SCHEDULE_INPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"\n⚠️  File not found: {filename}")
            continue
        
        print(f"\n📄 Processing: {filename}")
        print(f"   Term: {term} {year}")
        
        try:
            offerings = parse_csv_schedule(filepath)
            
            if offerings:
                schedule_json = create_schedule_json(offerings, term, year)
                
                # Save individual schedule
                output_filename = f"schedule_{year}_{term.lower()}.json"
                output_path = os.path.join(SCHEDULE_OUTPUT_DIR, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(schedule_json, f, indent=2, ensure_ascii=False)
                
                print(f"   ✅ Created: {output_filename}")
                print(f"   📊 Courses: {schedule_json['total_courses']}")
                
                # Track for pattern analysis
                for course_code, data in offerings.items():
                    if course_code not in all_offerings:
                        all_offerings[course_code] = {
                            "fall": False,
                            "spring": False,
                            "instructors": set(),
                            "years": set()
                        }
                    
                    if term == "Fall":
                        all_offerings[course_code]["fall"] = True
                    else:
                        all_offerings[course_code]["spring"] = True
                    
                    all_offerings[course_code]["years"].add(year)
                    
                    for section in data.get("sections", []):
                        instructor = section.get("instructor", "")
                        if instructor:
                            all_offerings[course_code]["instructors"].add(instructor)
            else:
                print(f"   ⚠️  No data extracted")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Generate offering patterns
    print("\n" + "=" * 70)
    print("GENERATING OFFERING PATTERNS")
    print("=" * 70)
    
    patterns = {}
    for course_code, data in sorted(all_offerings.items()):
        fall = data["fall"]
        spring = data["spring"]
        
        if fall and spring:
            frequency = "every_semester"
        elif fall:
            frequency = "fall_only"
        elif spring:
            frequency = "spring_only"
        else:
            frequency = "unknown"
        
        patterns[course_code] = {
            "fall": fall,
            "spring": spring,
            "frequency": frequency,
            "typical_instructors": list(data["instructors"])[:5],  # Top 5
            "years_observed": sorted(list(data["years"]))
        }
    
    # Save patterns
    patterns_path = os.path.join(SCHEDULE_OUTPUT_DIR, "course_offering_patterns.json")
    with open(patterns_path, 'w', encoding='utf-8') as f:
        json.dump({
            "description": "Course offering patterns for CMU-Q. Used for academic planning to determine course availability by semester.",
            "last_updated": "2026-01-16",
            "data_sources": [f[0] for f in csv_files],
            "total_courses_tracked": len(patterns),
            "patterns": patterns,
            "special_notes": {
                "cs_minor_planning": "15-150 (Fall) → 15-210 (Spring) → 15-213 (Fall) or 15-251 (Spring). Plan carefully!",
                "is_concentration_capstones": "67-425, 67-426, 67-427 are only offered in Spring",
                "math_sequence": "21-120 (Fall) → 21-122 (Spring) for calculus track"
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Created: course_offering_patterns.json")
    print(f"📊 Courses tracked: {len(patterns)}")
    
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    process_all_schedules()
