# Schedule Data Files

This directory contains processed course schedule data in JSON format for use by the academic planning system.

## Files

### Schedule Files (by Semester)
- `schedule_2024_fall.json` - Fall 2024 course offerings
- `schedule_2025_fall.json` - Fall 2025 course offerings  
- `schedule_2025_spring.json` - Spring 2025 course offerings
- `schedule_2026_spring.json` - Spring 2026 course offerings (complete)

### Pattern Files
- `course_offering_patterns.json` - Aggregated offering patterns across all semesters
- `cmu_microcourses_2026_2027.json` - Microcourse offerings

## Generating Schedule Files

To process CSV schedule files and generate JSON:

```bash
python process_schedules_final.py
```

This script will:
1. Parse all CSV files in `data/courses/schedule/`
2. Generate individual semester JSON files
3. Update `course_offering_patterns.json` with aggregated data

## File Format

Each schedule JSON file contains:
```json
{
  "semester": {
    "term": "Fall|Spring",
    "year": 2025,
    "academic_year": "2025-2026"
  },
  "total_courses": 150,
  "offerings": [
    {
      "course_code": "67-272",
      "sections": [
        {
          "section": "4",
          "days": ["Mon", "Wed"],
          "start_time": "08:30",
          "end_time": "09:45",
          "location": "3035",
          "instructor": "Mohanty, Bouamor",
          "capacity": 35
        }
      ]
    }
  ]
}
```

## Usage in Agents

### Programs Agent
```python
import json
with open('data/schedules/course_offering_patterns.json') as f:
    patterns = json.load(f)
    
if patterns['patterns']['15-213']['fall']:
    # Course is available in Fall
```

### Courses Agent  
```python
import json
with open('data/schedules/schedule_2026_spring.json') as f:
    schedule = json.load(f)
    
# Find course offerings
for offering in schedule['offerings']:
    if offering['course_code'] == '67-272':
        # Check sections, times, conflicts
```
