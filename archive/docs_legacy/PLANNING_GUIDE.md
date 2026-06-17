# Academic Planning Agent Guide

## Overview

The **Academic Planning Agent** is a new specialized agent in your multi-agent advising system that generates semester-by-semester course plans for students.

This agent demonstrates **multi-agent collaboration** where planning requires coordination between:
- **Programs Agent** (degree requirements)
- **Courses Agent** (course availability, schedules)
- **Policy Agent** (overload rules, prerequisites)
- **Planning Agent** (sequencing, workload balancing)

---

## What It Does

The Planning Agent can:

✅ **Generate multi-semester course plans** from current status to graduation
✅ **Ensure prerequisite sequencing** (courses taken in correct order)
✅ **Balance workload** across semesters (45-54 units typically)
✅ **Consider course availability** (Fall-only, Spring-only, every semester)
✅ **Integrate minors** into the plan
✅ **Adapt to constraints** (early graduation, light workload, etc.)
✅ **Flag risks** (overload semesters, course availability issues)

---

## Architecture

### How It Fits in Your Multi-Agent System

```
Student Query: "Help me plan my courses for the next 2 years"
       ↓
   COORDINATOR (Intent Classification)
       ↓
   Activates: Planning Agent, Programs Agent, Courses Agent, Policy Agent
       ↓
   BLACKBOARD (Shared State)
   ├── Student Profile
   ├── Degree Requirements (from Programs Agent)
   ├── Course Schedules (from Courses Agent)
   ├── Policy Constraints (from Policy Agent)
   └── Generated Plans (from Planning Agent)
       ↓
   NEGOTIATION (if conflicts detected)
   ├── Policy Agent: "This semester has 60 units - exceeds limit!"
   └── Planning Agent: "Revised plan to redistribute courses"
       ↓
   SYNTHESIS (Coordinator)
       ↓
   Final Answer to Student
```

### Key Research Contributions

This implementation demonstrates:

1. **Dynamic Agent Collaboration**
   - Planning agent doesn't work in isolation
   - Dynamically calls upon other agents' expertise
   - Agents communicate through structured blackboard

2. **Negotiation Protocol**
   - Policy agent can critique plans
   - Planning agent revises based on feedback
   - Visible to user (transparency)

3. **Emergent Behavior**
   - No hardcoded rules for "how to plan"
   - LLM reasons about prerequisites, availability, workload
   - System adapts to novel scenarios

---

## Files Created

### 1. **agents/planning_agent.py**
The main planning agent implementation.

**Key Methods:**
- `execute()` - Generate semester-by-semester plans
- `_extract_planning_parameters()` - Parse user requirements
- `_get_course_schedules()` - Load schedule data
- `_build_planning_prompt()` - Create LLM prompt with all context
- `handle_critique()` - Respond to feedback from other agents

### 2. **planning_tools.py**
Utility functions for planning algorithms.

**Key Functions:**
- `load_course_schedules()` - Load semester schedules from JSON
- `load_program_requirements()` - Get degree requirements
- `analyze_course_offerings()` - Determine when courses are offered
- `check_prerequisites_met()` - Validate prerequisite chains
- `calculate_semester_units()` - Compute workload
- `generate_semester_sequence()` - Create timeline
- `validate_plan()` - Check plan completeness

### 3. **test_planning.py**
Test script with example queries.

**Test Cases:**
- Basic graduation planning
- Planning with minor integration
- Accelerated graduation (3.5 years)
- Complete 4-year plan for new students

---

## Usage Examples

### Example 1: Basic Planning

```python
# In chat interface or test script
query = "Can you help me plan what courses to take each semester until graduation?"

# The coordinator will:
# 1. Detect this is a planning query
# 2. Activate Planning Agent + Programs Agent + Courses Agent
# 3. Planning Agent generates 2-3 plan options
# 4. Policy Agent validates for overload/conflicts
# 5. Coordinator synthesizes final answer
```

**Expected Output:**
```
PLAN A: Balanced 4-Year Path

Semester 1 (Fall 2026):
- 15-150: Principles of Functional Programming (12 units)
- 21-241: Matrices and Linear Transformations (10 units)
- 76-270: Writing for the Professions (9 units)
- 15-281: AI: Representation and Problem Solving (12 units)
Total: 43 units

Semester 2 (Spring 2027):
- 15-210: Parallel and Sequential Data Structures (12 units)
...

RATIONALE:
This plan ensures prerequisites are met in order, balances
workload across semesters (avg 48 units), and includes all
degree requirements. Core CS courses front-loaded to enable
electives later.
```

### Example 2: Planning with Minor

```python
query = "I want to add a Business Administration minor. Can you create a plan?"

# Multi-agent collaboration:
# - Programs Agent: Retrieves BA minor requirements
# - Planning Agent: Integrates minor courses into plan
# - Policy Agent: Checks for double-counting rules
# - Courses Agent: Verifies course availability
```

### Example 3: Interactive Conflict Resolution

```
User: "Can I graduate in 3.5 years with a heavy course load?"

Planning Agent: Generates aggressive plan with 54-60 units/semester

Policy Agent: ⚠ "Semesters 3, 5, 6 exceed 54 units - requires overload approval"

Coordinator: Presents trade-offs to user
  Option A: Graduate in 3.5 years (requires 3 overload petitions)
  Option B: Graduate in 4 years (no overload needed)

User: Selects Option A

Planning Agent: Revises plan with overload noted

Final Answer: "Here's your 3.5-year plan. You'll need to petition for
overload in Fall 2026, Fall 2027, and Spring 2028..."
```

---

## Data Requirements

The Planning Agent needs:

### 1. **Program Requirements** (Already exists)
Location: `data/programs/*/cmu_*_degree_requirements.json`

Example structure:
```json
{
  "program": {
    "title": "BS in Computer Science"
  },
  "requirements": {
    "computer_science": {
      "core_courses": [
        {"code": "15-122", "title": "..."},
        ...
      ]
    }
  }
}
```

### 2. **Course Schedules** (Already exists - JSON format)
Location: `data/courses/Schedule/schedule_*.json`

Example structure:
```json
{
  "semester": {
    "term": "Spring",
    "year": 2026
  },
  "offerings": [
    {
      "course_code": "15-122",
      "sections": [
        {
          "section": "W",
          "days": ["Sun", "Tue", "Thu"],
          "start_time": "14:30",
          "instructor": "..."
        }
      ]
    }
  ]
}
```

### 3. **Sample Curricula** (Already exists)
Location: `data/programs/*/CS_Major_sample_curriculum.json`

These provide example sequencing that the agent can reference.

---

## Integration with Coordinator

The LLM-driven coordinator will automatically detect planning queries:

**Trigger Phrases:**
- "plan my courses"
- "what should I take each semester"
- "help me graduate in X years"
- "create a semester-by-semester plan"
- "I want to add a minor, how do I fit it in"

**Coordinator's Role:**
1. Classify intent as "academic_planning"
2. Determine which agents needed (usually 3-4 agents)
3. Set execution order:
   - Programs Agent first (get requirements)
   - Planning Agent second (generate plans using requirements)
   - Courses Agent third (check availability)
   - Policy Agent last (validate)
4. Detect conflicts between agent outputs
5. Trigger negotiation if needed
6. Synthesize final answer

---

## Negotiation Example

This showcases your **Proposal + Critique protocol**:

```
STEP 1: Planning Agent Proposes
Plan: 6 semesters, avg 54 units, includes BA minor

STEP 2: Policy Agent Critiques
"Semester 4 has 60 units - exceeds max 54.
 BA minor courses cannot double-count with IS major core."

STEP 3: Planning Agent Revises
Revised Plan: Redistributes 2 courses to Semester 5,
              replaces double-counted course

STEP 4: Policy Agent Approves
"Revised plan complies with all policies."

STEP 5: Coordinator Synthesizes
Presents final plan to student with explanations
```

---

## Testing

### Quick Test

```bash
python test_planning.py
```

This runs 4 test scenarios and shows agent collaboration.

### Interactive Testing

```bash
python chat.py
```

Then ask planning questions:
- "Help me plan my next 4 semesters"
- "I want to graduate early, can you make a plan?"
- "Can you plan a 4-year schedule with CS minor?"

### Development Mode Testing

```bash
python chat.py
> mode:dev
> @planning Help me plan my courses for next year
```

This directly invokes the planning agent for debugging.

---

## Customization

### Adjust Planning Preferences

In `agents/planning_agent.py`, modify `_extract_planning_parameters()`:

```python
# Default workload preference
"workload_preference": "balanced"  # Options: light, balanced, heavy

# Default graduation timeline
"target_graduation": "4 years"  # Can be 3.5, 4, or custom
```

### Add Planning Heuristics

In `planning_tools.py`, enhance algorithms:

```python
def prioritize_courses(courses, student_profile):
    """
    Custom logic to prioritize which courses to schedule first.
    E.g., prerequisites before electives, hard courses in lighter semesters
    """
    pass
```

### Integrate External APIs

Future enhancement - add to `planning_tools.py`:

```python
def check_stellic_progress(student_id):
    """Query Stellic API for actual student progress"""
    pass

def get_scottylab_schedule(semester):
    """Get latest schedules from ScottyLabs API"""
    pass
```

---

## Research Implications for ACL 2026

### What This Demonstrates

1. **Multi-Agent Collaboration**
   - 4 agents working together on complex task
   - Dynamic workflow (not hardcoded)
   - Visible agent reasoning

2. **Negotiation & Conflict Resolution**
   - Policy agent flags issues
   - Planning agent responds and revises
   - User sees the back-and-forth

3. **Emergent Intelligent Behavior**
   - No explicit prerequisite graph
   - LLM infers sequencing from course descriptions
   - Adapts to novel constraints

4. **Interactive Agency**
   - System asks clarifying questions
   - Presents trade-offs (fast graduation vs. lighter load)
   - User retains decision-making power

### Evaluation Metrics

For your ACL paper, you can measure:

**Correctness:**
- % of plans that satisfy all degree requirements
- % of plans with correct prerequisite sequencing
- % of plans that respect university policies

**Quality:**
- Human advisor ratings of plan quality
- Workload balance (variance in units/semester)
- Feasibility given course offering patterns

**Collaboration:**
- Number of agent interactions per query
- Success rate of conflict resolution
- User satisfaction with transparency

**Comparison Baselines:**
- Single-agent RAG planner
- Rule-based planning system
- Human advisor plans (gold standard)

---

## Troubleshooting

### "No schedules loaded"
- Check that schedule JSON files exist in `data/courses/Schedule/`
- Run `convert_schedules.py` if needed (already done)

### "Planning agent not activated"
- Make sure `academic_planning` is in coordinator's `available_agents`
- Check that query contains planning keywords

### "No plan generated"
- Check that program requirements JSON exists
- Ensure LLM has sufficient context (may need longer prompt)

### Performance Issues
- Planning queries can take 20-40 seconds (multiple agents + LLM calls)
- Consider caching schedule analysis results
- Use faster model (gpt-4o) for agents if needed

---

## Next Steps

### Recommended Enhancements

1. **Prerequisite Graph Building**
   - Automatically extract prerequisites from course descriptions
   - Build dependency graph
   - Use for constraint-based planning

2. **Student Progress Integration**
   - Connect to Stellic API
   - Auto-populate completed courses
   - Show degree audit alongside plan

3. **What-If Analysis**
   - "What if I fail this course?"
   - "What if I study abroad Spring 2027?"
   - Dynamic re-planning

4. **Visual Plan Editor**
   - Drag-and-drop course scheduling UI
   - Instant validation feedback
   - Export to calendar

5. **Long-Term Memory**
   - Remember student's planning preferences
   - Track plan revisions over time
   - Learn from successful graduation paths

---

## Contributing

To extend the planning functionality:

1. **Add new planning algorithms** → `planning_tools.py`
2. **Enhance agent prompts** → `agents/planning_agent.py`
3. **Add new data sources** → Update loaders in `planning_tools.py`
4. **Improve negotiation** → Modify `handle_critique()` method
5. **Add evaluation metrics** → Create `evaluate_planning.py`

---

## Summary

You now have a **fully integrated academic planning agent** that:

✅ Generates semester-by-semester course plans
✅ Collaborates with 3+ other agents
✅ Demonstrates negotiation and conflict resolution
✅ Provides transparent, explainable recommendations
✅ Fits perfectly into your ACL 2026 research narrative

**Perfect for demonstrating:**
- Dynamic multi-agent orchestration
- LLM-powered collaborative planning
- Interactive academic advising
- Emergent intelligent behavior

Ready to test and iterate! 🚀
