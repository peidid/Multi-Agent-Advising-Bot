# Schedule Data Conversion Status

## ✅ Completed

1. **Spring 2026 Schedule** - Fully converted to JSON (`data/schedules/schedule_2026_spring.json`)
   - 127 courses with complete section details
   - All scheduling information (days, times, locations, instructors, capacity)

2. **Offering Patterns File** - Updated (`data/schedules/course_offering_patterns.json`)
   - Contains patterns for 60+ courses
   - Identifies Fall-only, Spring-only, and every-semester courses
   - Includes typical instructors and notes

3. **Conversion Script** - Created (`process_schedules_final.py`)
   - Handles multiple CSV formats (Fall 2024, Fall 2025, Spring 2025, Spring 2026)
   - Auto-detects CSV structure
   - Generates standardized JSON output
   - Updates offering patterns automatically

4. **Documentation** - Created (`data/schedules/README.md`)
   - Usage instructions
   - File format documentation
   - Integration examples for agents

## 📋 To Complete

Run the conversion script to generate JSON files for remaining semesters:

```bash
python process_schedules_final.py
```

This will generate:
- `schedule_2024_fall.json`
- `schedule_2025_fall.json`  
- `schedule_2025_spring.json`

And update `course_offering_patterns.json` with complete data from all semesters.

## 📁 File Structure

```
data/
├── courses/
│   └── schedule/              # Source CSV files
│       ├── Fall 2024.xlsx - CMU-Q Fall 2024 Courses Schedul.csv
│       ├── Fall 2025 - 2025_03_04.csv
│       ├── Spring2025.xlsx - Sp25 Schedule Draft 102124 430p.csv
│       ├── Spring2026.csv
│       └── cmu_microcourses_2026_2027.json
│
└── schedules/                  # Processed JSON files
    ├── schedule_2026_spring.json          ✅ Complete
    ├── schedule_2024_fall.json             ⏳ Run script
    ├── schedule_2025_fall.json            ⏳ Run script
    ├── schedule_2025_spring.json           ⏳ Run script
    ├── course_offering_patterns.json       ✅ Updated
    ├── cmu_microcourses_2026_2027.json     ✅ Copied
    └── README.md                            ✅ Created
```

## 🔧 Script Features

The `process_schedules_final.py` script:
- Handles different CSV formats automatically
- Parses multi-line fields (days, times)
- Normalizes day names and time formats
- Builds proper course codes (e.g., "03-121" from "BSC,03121")
- Deduplicates sections
- Aggregates offering patterns across all semesters
- Generates clean, structured JSON

## 📊 Current Data Coverage

- **Spring 2026**: 127 courses (complete)
- **Fall 2025**: ~150+ courses (needs conversion)
- **Spring 2025**: ~140+ courses (needs conversion)
- **Fall 2024**: ~130+ courses (needs conversion)
- **Offering Patterns**: 60+ courses tracked

## 🎯 Next Steps

1. Run `python process_schedules_final.py` to generate remaining schedule files
2. Verify JSON files are properly formatted
3. Test integration with agents (Programs Agent, Courses Agent)
4. Update patterns file if any discrepancies found

## 💡 Usage in Agents

### Check Course Availability
```python
import json
with open('data/schedules/course_offering_patterns.json') as f:
    patterns = json.load(f)['patterns']
    
if patterns.get('15-213', {}).get('fall'):
    print("15-213 is available in Fall")
```

### Get Schedule Details
```python
import json
with open('data/schedules/schedule_2026_spring.json') as f:
    schedule = json.load(f)
    
for offering in schedule['offerings']:
    if offering['course_code'] == '67-272':
        print(f"Sections: {len(offering['sections'])}")
        for section in offering['sections']:
            print(f"  {section['section']}: {section['days']} {section['start_time']}-{section['end_time']}")
```
