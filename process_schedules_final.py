#!/usr/bin/env python3
"""
Process all schedule CSV files and generate JSON schedules + update offering patterns.
Handles multiple CSV formats from different semesters.
"""

import os
import json
import csv
import re
from collections import defaultdict

SCHEDULE_INPUT_DIR = "./data/courses/schedule"
SCHEDULE_OUTPUT_DIR = "./data/schedules"

DAY_MAPPINGS = {
    'Sunday': 'Sun', 'Sun': 'Sun', 'S': 'Sun', 'U': 'Sun',
    'Monday': 'Mon', 'Mon': 'Mon', 'M': 'Mon',
    'Tuesday': 'Tue', 'Tue': 'Tue', 'T': 'Tue',
    'Wednesday': 'Wed', 'Wed': 'Wed', 'W': 'Wed',
    'Thursday': 'Thu', 'Thu': 'Thu', 'R': 'Thu',
    'Friday': 'Fri', 'Fri': 'Fri', 'F': 'Fri',
    'Saturday': 'Sat', 'Sat': 'Sat'
}

DEPT_PREFIXES = {
    'CB': '02', 'BSC': '03', 'HCI': '05', 'SCS': '07', 'CMY': '09',
    'INI': '14', 'CS': '15', 'S3D': '17', 'MSC': '21', 'PHY': '33',
    'STA': '36', 'MCS': '38', 'ARC': '48', 'HSS': '66', 'ISP': '67',
    'PE': '69', 'BUS': '70', 'ECO': '73', 'ENG': '76', 'HIS': '79',
    'PHI': '80', 'LCL': '82', 'PSY': '85', 'ISM': '95', 'STU': '98',
    'CMU': '99', 'COR': 'QC'
}

def normalize_day(day):
    if not day:
        return None
    day = str(day).strip()
    return DAY_MAPPINGS.get(day, day if len(day) == 3 else None)

def parse_time(time_str):
    if not time_str or str(time_str).strip().lower() in ['nan', '', 'none']:
        return None
    time_str = str(time_str).strip()
    if ':' in time_str:
        parts = time_str.split(':')
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return f"{hour:02d}:{minute:02d}"
        except:
            return None
    return None

def parse_multiline_field(field):
    if not field or str(field).strip().lower() in ['nan', '', 'none']:
        return []
    values = [v.strip() for v in str(field).split('\n') if v.strip() and v.strip().lower() != 'nan']
    return values

def build_course_code(dept, course_id):
    if not course_id:
        return None
    course_id = str(course_id).strip()
    
    # Handle course IDs that already include department (e.g., "03121")
    if len(course_id) >= 5 and course_id[:2].isdigit():
        prefix = course_id[:2]
        course_num = course_id[2:]
        return f"{prefix}-{course_num}"
    
    if not dept:
        return None
    
    prefix = DEPT_PREFIXES.get(dept, dept)
    if course_id.isdigit():
        course_id = course_id.zfill(3)
    
    return f"{prefix}-{course_id}"

def parse_csv_fall2025(csv_path):
    """Parse Fall 2025 CSV format."""
    offerings = defaultdict(lambda: {"sections": []})
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                course_id_full = row.get('Course - ID', '').strip()
                section_id = row.get('Section', 'W').strip()
                days_raw = row.get('Delivery times - Day', '')
                start_time_raw = row.get('Delivery times - Start time', '')
                end_time_raw = row.get('Delivery times - End time', '')
                room = row.get('Assigned room - ID', '').strip()
                instructor = row.get('Professor - Last name', '').strip()
                capacity = row.get('Max Enrollment', '0').strip()
                
                if not course_id_full or len(course_id_full) < 5:
                    continue
                
                course_code = build_course_code(None, course_id_full)
                if not course_code:
                    continue
                
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
                
                if not days and not start_time:
                    continue  # Skip sections with no schedule info
                
                section = {
                    "section": section_id if section_id else "W",
                    "days": list(set(days)),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": room,
                    "instructor": instructor.replace('\n', ', '),
                    "capacity": cap
                }
                
                offerings[course_code]["course_code"] = course_code
                offerings[course_code]["sections"].append(section)
            except Exception as e:
                continue
    
    return dict(offerings)

def parse_csv_standard(csv_path):
    """Parse standard CSV format with Department - ID and Course - ID."""
    offerings = defaultdict(lambda: {"sections": []})
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        # Skip header rows if needed
        lines = f.readlines()
        reader_start = 0
        for i, line in enumerate(lines):
            if 'Department - ID' in line or 'Course - ID' in line:
                reader_start = i
                break
        
        f.seek(0)
        for _ in range(reader_start):
            next(f)
        
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dept = row.get('Department - ID', '').strip()
                course_id = row.get('Course - ID', '').strip()
                section_id = row.get('Section - ID', row.get('Section', 'W')).strip()
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
                
                if not days and not start_time:
                    continue
                
                section = {
                    "section": section_id if section_id else "W",
                    "days": list(set(days)),
                    "start_time": start_time,
                    "end_time": end_time,
                    "location": room,
                    "instructor": instructor.replace('\n', ', '),
                    "capacity": cap
                }
                
                offerings[course_code]["course_code"] = course_code
                offerings[course_code]["sections"].append(section)
            except Exception as e:
                continue
    
    return dict(offerings)

def create_schedule_json(offerings, term, year):
    """Create standardized schedule JSON structure."""
    offerings_list = []
    for course_code, data in sorted(offerings.items()):
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
            "generated_by": "process_schedules_final.py",
            "source": "CMU-Q Schedule Data"
        }
    }

def main():
    os.makedirs(SCHEDULE_OUTPUT_DIR, exist_ok=True)
    
    print("=" * 70)
    print("PROCESSING ALL SCHEDULE FILES")
    print("=" * 70)
    
    files_to_process = [
        ("Fall 2024.xlsx - CMU-Q Fall 2024 Courses Schedul.csv", "Fall", 2024, parse_csv_standard),
        ("Fall 2025 - 2025_03_04.csv", "Fall", 2025, parse_csv_fall2025),
        ("Spring2025.xlsx - Sp25 Schedule Draft 102124 430p.csv", "Spring", 2025, parse_csv_standard),
        ("Spring2026.csv", "Spring", 2026, parse_csv_standard),
    ]
    
    all_offerings = {}
    
    for filename, term, year, parser_func in files_to_process:
        filepath = os.path.join(SCHEDULE_INPUT_DIR, filename)
        
        if not os.path.exists(filepath):
            print(f"\n⚠️  File not found: {filename}")
            continue
        
        print(f"\n📄 Processing: {filename}")
        print(f"   Term: {term} {year}")
        
        try:
            offerings = parser_func(filepath)
            
            if offerings:
                schedule_json = create_schedule_json(offerings, term, year)
                
                output_filename = f"schedule_{year}_{term.lower()}.json"
                output_path = os.path.join(SCHEDULE_OUTPUT_DIR, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(schedule_json, f, indent=2, ensure_ascii=False)
                
                print(f"   ✅ Created: {output_filename}")
                print(f"   📊 Courses: {schedule_json['total_courses']}")
                
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
            "typical_instructors": sorted(list(data["instructors"]))[:5],
            "years_observed": sorted(list(data["years"]))
        }
    
    patterns_path = os.path.join(SCHEDULE_OUTPUT_DIR, "course_offering_patterns.json")
    with open(patterns_path, 'w', encoding='utf-8') as f:
        json.dump({
            "description": "Course offering patterns for CMU-Q. Used for academic planning to determine course availability by semester.",
            "last_updated": "2026-01-16",
            "data_sources": [f[0] for f in files_to_process],
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
    main()
