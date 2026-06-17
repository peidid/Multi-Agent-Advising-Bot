# How to Run Schedule Conversion

## Quick Start

1. **Open a terminal/command prompt** in the project directory
2. **Run the conversion script:**
   ```bash
   python process_schedules_final.py
   ```

   Or on Windows:
   ```cmd
   python process_schedules_final.py
   ```

   Or double-click: `run_schedule_conversion.bat`

## What It Does

The script will:
1. ✅ Parse all CSV schedule files:
   - Fall 2024
   - Fall 2025  
   - Spring 2025
   - Spring 2026 (already done)

2. ✅ Generate JSON files:
   - `data/schedules/schedule_2024_fall.json`
   - `data/schedules/schedule_2025_fall.json`
   - `data/schedules/schedule_2025_spring.json`
   - `data/schedules/schedule_2026_spring.json` (already exists)

3. ✅ Update `course_offering_patterns.json` with aggregated data from all semesters

## Expected Output

```
======================================================================
PROCESSING ALL SCHEDULE FILES
======================================================================

📄 Processing: Fall 2024.xlsx - CMU-Q Fall 2024 Courses Schedul.csv
   Term: Fall 2024
   ✅ Created: schedule_2024_fall.json
   📊 Courses: 130

📄 Processing: Fall 2025 - 2025_03_04.csv
   Term: Fall 2025
   ✅ Created: schedule_2025_fall.json
   📊 Courses: 150

📄 Processing: Spring2025.xlsx - Sp25 Schedule Draft 102124 430p.csv
   Term: Spring 2025
   ✅ Created: schedule_2025_spring.json
   📊 Courses: 140

📄 Processing: Spring2026.csv
   Term: Spring 2026
   ✅ Created: schedule_2026_spring.json
   📊 Courses: 127

======================================================================
GENERATING OFFERING PATTERNS
======================================================================

✅ Created: course_offering_patterns.json
📊 Courses tracked: 200+

======================================================================
PROCESSING COMPLETE
======================================================================
```

## Troubleshooting

### If Python is not found:
- Try `python3` instead of `python`
- Check Python is installed: `python --version`
- Make sure you're in the project root directory

### If files are not found:
- Verify CSV files exist in `data/courses/schedule/`
- Check file names match exactly (case-sensitive)

### If you get encoding errors:
- The script handles UTF-8 encoding automatically
- If issues persist, check CSV file encoding

## Manual Alternative

If the script doesn't work, the Spring 2026 schedule is already complete. The other semesters can be processed manually by:
1. Opening each CSV file
2. Using the same structure as `schedule_2026_spring.json`
3. Converting course codes and section data

## Files Created

After successful run, you'll have:
- ✅ 4 semester schedule JSON files
- ✅ Updated offering patterns file
- ✅ All ready for use by the agents
