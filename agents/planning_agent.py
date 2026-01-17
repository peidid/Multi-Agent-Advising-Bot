"""
Academic Planning Agent

Responsibilities:
- Generate semester-by-semester course plans
- Ensure prerequisite sequencing
- Balance workload across semesters
- Consider course availability patterns

Knowledge Base: chroma_db_programs/ + chroma_db_courses/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, PlanOption, Risk
from langchain_core.messages import SystemMessage
from typing import List, Dict, Set
import json
import re

class AcademicPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="academic_planning",
            domain="programs"  # Primary domain, but will also use course data
        )

    def execute(self, state: BlackboardState) -> AgentOutput:
        """Generate multi-semester academic plan."""
        user_query = state.get("user_query", "")
        student_profile = state.get("student_profile", {})
        agent_outputs = state.get("agent_outputs", {})

        # Extract planning parameters
        planning_params = self._extract_planning_parameters(
            user_query, student_profile, agent_outputs
        )

        # Get relevant data from other agents
        program_requirements = self._get_program_requirements(planning_params, agent_outputs)
        course_schedules = self._get_course_schedules(planning_params)

        # Build planning prompt
        prompt = self._build_planning_prompt(
            planning_params,
            program_requirements,
            course_schedules,
            student_profile
        )

        # Generate plan
        response = self.llm.invoke([SystemMessage(content=prompt)])

        # Parse generated plans
        plan_options = self._parse_plan_options(response.content)
        risks = self._identify_risks(plan_options, planning_params)

        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.85,
            plan_options=plan_options,
            risks=risks,
            relevant_policies=["Course prerequisites", "Graduation requirements"],
            constraints=planning_params.get("constraints", [])
        )

    def _extract_planning_parameters(self, query: str, profile: dict, outputs: dict) -> dict:
        """Extract planning parameters from query and context."""
        params = {
            "program": profile.get("major", "Computer Science"),
            "current_semester": profile.get("current_semester", "First-Year Fall"),
            "completed_courses": profile.get("completed_courses", []),
            "target_graduation": None,
            "include_minor": None,
            "workload_preference": "balanced",  # balanced, light, heavy
            "constraints": []
        }

        # Extract from query
        query_lower = query.lower()

        # Graduation timeline
        if "4 years" in query_lower or "four years" in query_lower:
            params["target_graduation"] = "4 years"
        elif "3.5 years" in query_lower or "early" in query_lower:
            params["target_graduation"] = "3.5 years"

        # Minor mentions
        minor_match = re.search(r'(\w+)\s+minor', query_lower)
        if minor_match:
            params["include_minor"] = minor_match.group(1).title()

        # Workload preferences
        if "light" in query_lower or "easy" in query_lower:
            params["workload_preference"] = "light"
        elif "heavy" in query_lower or "aggressive" in query_lower:
            params["workload_preference"] = "heavy"

        # Get program from Programs agent if available
        if "programs_requirements" in outputs:
            prog_output = outputs["programs_requirements"]
            if hasattr(prog_output, 'answer'):
                # Extract program mentions
                pass

        return params

    def _get_program_requirements(self, params: dict, outputs: dict) -> dict:
        """Retrieve program requirements from RAG or previous agent outputs."""
        program = params.get("program", "Computer Science")

        # Try to get from Programs agent output first
        if "programs_requirements" in outputs:
            prog_output = outputs["programs_requirements"]
            context = prog_output.answer if hasattr(prog_output, 'answer') else ""
        else:
            # Query RAG for requirements
            rag_query = f"{program} major requirements core courses electives sample curriculum"
            context = self.retrieve_context(rag_query)

        return {
            "program": program,
            "requirements_context": context
        }

    def _get_course_schedules(self, params: dict) -> dict:
        """Load course schedule data for planning."""
        # Load schedule JSONs
        schedules = {}

        try:
            # Load available schedules
            import os
            schedule_dir = "./data/schedules"

            if os.path.exists(schedule_dir):
                for filename in os.listdir(schedule_dir):
                    if filename.endswith('.json') and 'schedule_' in filename:
                        filepath = os.path.join(schedule_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            term = data.get("semester", {})
                            key = f"{term.get('year', '')}_{term.get('term', '')}".lower()
                            schedules[key] = data

            # Also check the Schedule folder for existing JSON
            alt_schedule_dir = "./data/courses/Schedule"
            if os.path.exists(alt_schedule_dir):
                for filename in os.listdir(alt_schedule_dir):
                    if filename.endswith('.json') and 'schedule_' in filename:
                        filepath = os.path.join(alt_schedule_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if "semester" in data:
                                term = data.get("semester", {})
                                key = f"{term.get('year', '')}_{term.get('term', '')}".lower()
                                schedules[key] = data

        except Exception as e:
            print(f"Warning: Could not load schedules: {e}")

        return schedules

    def _build_planning_prompt(self, params: dict, requirements: dict,
                               schedules: dict, profile: dict) -> str:
        """Build comprehensive planning prompt."""

        # Summarize available schedules
        schedule_summary = self._summarize_schedules(schedules)

        prompt = f"""You are an expert academic advisor creating a semester-by-semester course plan.

**Student Profile:**
- Program: {params.get('program', 'N/A')}
- Current Status: {params.get('current_semester', 'Starting')}
- Completed Courses: {', '.join(params.get('completed_courses', [])) or 'None'}
- Target Graduation: {params.get('target_graduation', 'Standard 4 years')}
- Minor Interest: {params.get('include_minor', 'None')}
- Workload Preference: {params.get('workload_preference', 'balanced')}

**Program Requirements:**
{requirements.get('requirements_context', 'See program requirements')}

**Course Availability (from schedules):**
{schedule_summary}

**Planning Instructions:**
1. Create a semester-by-semester plan from current status to graduation
2. Ensure prerequisites are satisfied in correct order
3. Consider course availability patterns (Fall-only, Spring-only, every semester)
4. Balance workload (typically 45-54 units per semester)
5. Include specific course codes, not just placeholders
6. If minor is requested, integrate minor requirements
7. Account for already completed courses

**Output Format:**
Provide 1-2 alternative plans in this structure:

PLAN A: [Brief description]
Semester 1 (Term Year):
- XX-XXX: Course Name (X units)
- XX-XXX: Course Name (X units)
Total: X units

Semester 2 (Term Year):
- XX-XXX: Course Name (X units)
...

Continue for all semesters until graduation.

RATIONALE FOR PLAN A:
[Explain the sequencing strategy, workload distribution, and key decisions]

[If applicable, provide PLAN B with different approach]

**Important Considerations:**
- Flag any risky semesters (overload, high-difficulty courses together)
- Note if any required courses might not be available when needed
- Consider study abroad opportunities if mentioned
- Ensure all degree requirements are met
"""

        return prompt

    def _summarize_schedules(self, schedules: dict) -> str:
        """Summarize available schedule data."""
        if not schedules:
            return "No detailed schedule data available. Use general course offering patterns."

        summary_lines = []
        for key, data in sorted(schedules.items()):
            term = data.get("semester", {})
            term_name = f"{term.get('term', '')} {term.get('year', '')}"
            course_count = data.get("total_courses", len(data.get("offerings", [])))

            # Sample some courses
            offerings = data.get("offerings", [])[:5]
            course_codes = [o.get("course_code", "") for o in offerings]

            summary_lines.append(
                f"{term_name}: {course_count} courses (e.g., {', '.join(course_codes[:3])}...)"
            )

        return "\n".join(summary_lines) if summary_lines else "Schedule data loaded."

    def _parse_plan_options(self, response: str) -> List[PlanOption]:
        """Parse generated plans into structured format."""
        plan_options = []

        # Try to extract structured plans from response
        plan_sections = re.split(r'PLAN [A-Z]:', response)

        for section in plan_sections[1:]:  # Skip first split (before any PLAN)
            # Extract semesters and courses
            semesters = []
            semester_blocks = re.findall(
                r'Semester \d+\s*\(([^)]+)\):([^S]+?)(?=Semester \d+|RATIONALE|PLAN [A-Z]|$)',
                section,
                re.DOTALL
            )

            all_courses = []
            for term, courses_text in semester_blocks:
                # Extract course codes from this semester
                courses = re.findall(r'(\d{2}-\d{3})', courses_text)
                all_courses.extend(courses)

                # Extract total units if present
                units_match = re.search(r'Total:\s*(\d+)\s*units', courses_text)
                total_units = int(units_match.group(1)) if units_match else 0

                # Structure semester data
                semester_info = {
                    "term": term.strip(),
                    "courses": courses,
                    "total_units": total_units
                }
                semesters.append(semester_info)

            # Extract justification/rationale
            justification = ""
            rationale_match = re.search(r'RATIONALE[^:]*:(.*?)(?=PLAN [A-Z]|$)', section, re.DOTALL)
            if rationale_match:
                justification = rationale_match.group(1).strip()[:500]  # Limit to 500 chars

            if all_courses and semesters:
                plan_options.append(
                    PlanOption(
                        semesters=semesters,
                        courses=all_courses,
                        confidence=0.85,  # Default confidence
                        justification=justification or "Multi-semester academic plan",
                        risks=[],
                        policy_citations=[]
                    )
                )

        return plan_options

    def _identify_risks(self, plan_options: List[PlanOption], params: dict) -> List[Risk]:
        """Identify potential risks in the generated plans."""
        risks = []

        # This would need more sophisticated logic
        # For now, placeholder for common risks

        for plan in plan_options:
            # Check for overload semesters (would need unit counting)
            # Check for prerequisite violations
            # Check for course availability issues
            pass

        return risks

    def handle_critique(self, state: BlackboardState, critique: str) -> str:
        """Handle critiques from other agents (e.g., Policy agent flags overload)."""

        prompt = f"""You previously generated an academic plan. Another agent has provided feedback:

CRITIQUE: {critique}

Please revise your plan to address this feedback while maintaining the overall structure and goals.
Provide the REVISED PLAN with explanations of what changed.
"""

        response = self.llm.invoke([SystemMessage(content=prompt)])
        return response.content
