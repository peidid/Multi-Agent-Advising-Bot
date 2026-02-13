"""
Academic Planning Agent

Responsibilities:
- Generate semester-by-semester course plans
- Ensure prerequisite sequencing
- Balance workload across semesters
- Consider course availability patterns

Knowledge Base: chroma_db_programs/ + chroma_db_schedules/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, PlanOption, Risk
from langchain_core.messages import SystemMessage
from rag_engine_improved import get_retriever
from typing import List, Dict, Set
import json
import re
import os

# Use absolute path based on project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class AcademicPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="academic_planning",
            domain="programs"  # Primary domain for program requirements
        )
        # Add schedules retriever for course availability
        self.schedules_retriever = get_retriever(domain="schedules", k=5)

    def execute(self, state: BlackboardState) -> AgentOutput:
        """Generate multi-semester academic plan with streaming events."""
        # Emit start event
        self.emit_start()

        try:
            user_query = state.get("user_query", "")
            student_profile = state.get("student_profile", {})
            agent_outputs = state.get("agent_outputs", {})

            # Get memory context (conversation history + student profile)
            memory_context = self.get_memory_context(state)

            # Check if user is asking for a full academic plan or just a specific question
            if not self._is_planning_request(user_query):
                # This is NOT a planning request - defer to other agents or answer briefly
                self.emit_thinking("Analyzing query...")
                result = self._answer_non_planning_question(user_query, student_profile, memory_context)
                self.emit_output(result)
                self.emit_complete(confidence=result.confidence, summary="Answered planning question")
                return result

            # Extract planning parameters
            self.emit_thinking("Analyzing planning parameters...")
            planning_params = self._extract_planning_parameters(
                user_query, student_profile, agent_outputs
            )

            # Get relevant data from other agents
            self.emit_thinking("Gathering program requirements...")
            program_requirements = self._get_program_requirements(planning_params, agent_outputs)
            course_schedules = self._get_course_schedules(planning_params)

            # Build planning prompt
            self.emit_thinking("Generating semester-by-semester plan...")
            prompt = self._build_planning_prompt(
                planning_params,
                program_requirements,
                course_schedules,
                student_profile,
                memory_context
            )

            # Generate plan
            response = self.llm.invoke([SystemMessage(content=prompt)])

            # Parse generated plans
            plan_options = self._parse_plan_options(response.content)
            risks = self._identify_risks(plan_options, planning_params)

            result = AgentOutput(
                agent_name=self.name,
                answer=response.content,
                confidence=0.85,
                plan_options=plan_options,
                risks=risks,
                relevant_policies=["Course prerequisites", "Graduation requirements"],
                constraints=planning_params.get("constraints", [])
            )

            plan_count = len(plan_options) if plan_options else 0
            self.emit_output(result)
            self.emit_complete(
                confidence=0.85,
                summary=f"Generated {plan_count} plan option(s)"
            )

            return result

        except Exception as e:
            self.emit_error(str(e))
            raise

    def _is_planning_request(self, query: str) -> bool:
        """
        Determine if the user is asking for a full academic plan.

        Returns True only if user explicitly asks for a plan, schedule, or curriculum.
        Returns False for specific questions about courses, conflicts, single semesters, etc.
        """
        query_lower = query.lower()

        # Keywords that indicate a FULL PLANNING request
        planning_keywords = [
            "plan my", "create a plan", "make a plan", "generate a plan",
            "semester plan", "course plan", "academic plan", "graduation plan",
            "full schedule", "full plan", "entire plan",
            "plan for all semesters", "plan from now", "plan until graduation",
            "how should i plan", "help me plan my courses",
            "4 year plan", "four year plan", "remaining semesters"
        ]

        # Keywords that indicate NOT a planning request (specific questions)
        non_planning_keywords = [
            "can i take", "will this work", "is it possible", "conflict",
            "busy on", "available", "time slot", "schedule conflict",
            "specific course", "this course", "that course",
            "what time", "when is", "does it conflict"
        ]

        # Check for non-planning indicators first
        for keyword in non_planning_keywords:
            if keyword in query_lower:
                return False

        # Check for planning indicators
        for keyword in planning_keywords:
            if keyword in query_lower:
                return True

        # Default: if asking about a single course/semester with constraints, not a plan
        # If asking broadly about "my plan" or "courses to take", it's a plan
        if re.search(r'plan\s+(my|for|to)', query_lower):
            return True
        if "semester by semester" in query_lower:
            return True

        # Otherwise, default to NOT a planning request
        return False

    def _answer_non_planning_question(self, query: str, profile: dict, memory_context: str) -> AgentOutput:
        """
        Answer a specific question that doesn't require full academic planning.

        This is for questions like "Can I take X in Spring 2026 given constraint Y?"
        """
        # Get relevant schedule context
        schedule_context = ""
        try:
            # Extract semester if mentioned
            semester_match = re.search(r'(spring|fall|summer)\s*(\d{4})', query, re.IGNORECASE)
            if semester_match:
                semester = f"{semester_match.group(1)} {semester_match.group(2)}"
                schedule_docs = self.schedules_retriever.invoke(f"schedule {semester} course offerings")
                schedule_context = "\n".join([doc.page_content for doc in schedule_docs])
        except Exception as e:
            print(f"Warning: Could not retrieve schedule context: {e}")

        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand references.
"""

        prompt = f"""You are an Academic Planning Agent for CMU-Q.

The user has a SPECIFIC QUESTION - they are NOT asking for a full semester-by-semester plan.
Do NOT generate a full academic plan unless explicitly asked.

{context_section}

User Query: {query}

Student Profile:
- Program: {profile.get('major', 'Not specified')}
- Completed Courses: {profile.get('completed_courses', [])}

Schedule Context:
{schedule_context if schedule_context else 'No specific schedule data available.'}

INSTRUCTIONS:
1. Answer the SPECIFIC question the user asked
2. Do NOT generate a full 4-year or 8-semester plan
3. If they ask about taking a specific course with a time constraint:
   - Look up when that course is offered
   - Check if it conflicts with their constraint
   - Give a direct yes/no answer with explanation
4. If schedule data is not available, say so clearly
5. Be concise and direct
"""

        response = self.llm.invoke([SystemMessage(content=prompt)])

        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.8,
            plan_options=[],
            risks=[],
            relevant_policies=[],
            constraints=[]
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

        # Also get schedule context from schedules RAG
        schedule_rag_query = f"{program} course offerings schedule availability"
        try:
            schedule_docs = self.schedules_retriever.invoke(schedule_rag_query)
            schedule_context = "\n\n".join([doc.page_content for doc in schedule_docs])
        except Exception as e:
            print(f"Warning: Could not retrieve schedule context: {e}")
            schedule_context = ""

        return {
            "program": program,
            "requirements_context": context,
            "schedule_context": schedule_context
        }

    def _get_course_schedules(self, params: dict) -> dict:
        """Load course schedule data for planning."""
        schedules = {}

        try:
            # Load all JSON files from data/schedules/
            schedule_dir = os.path.join(PROJECT_ROOT, "data", "schedules")

            if os.path.exists(schedule_dir):
                for filename in os.listdir(schedule_dir):
                    if filename.endswith('.json'):
                        filepath = os.path.join(schedule_dir, filename)
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)

                            # Handle different JSON formats
                            if isinstance(data, list):
                                # List format (e.g., Fall_2025_courses.json)
                                # Wrap in a dict structure
                                key = filename.replace('.json', '').lower()
                                schedules[key] = {
                                    "offerings": data,
                                    "total_courses": len(data),
                                    "semester": self._parse_semester_from_filename(filename)
                                }
                            elif isinstance(data, dict):
                                # Dict format (e.g., schedule_2026_spring.json)
                                if "semester" in data:
                                    term = data.get("semester", {})
                                    key = f"{term.get('year', '')}_{term.get('term', '')}".lower()
                                else:
                                    key = filename.replace('.json', '').lower()
                                schedules[key] = data
                            # Skip other formats

                print(f"📅 Loaded {len(schedules)} schedule files from {schedule_dir}")

        except Exception as e:
            print(f"Warning: Could not load schedules: {e}")

        return schedules

    def _parse_semester_from_filename(self, filename: str) -> dict:
        """Extract semester info from filename like 'Fall_2025_courses.json'."""
        import re
        match = re.search(r'(Fall|Spring|Summer)_(\d{4})', filename, re.IGNORECASE)
        if match:
            return {"term": match.group(1).title(), "year": int(match.group(2))}
        return {}

    def _build_planning_prompt(self, params: dict, requirements: dict,
                               schedules: dict, profile: dict,
                               memory_context: str = "") -> str:
        """Build comprehensive planning prompt."""

        # Summarize available schedules
        schedule_summary = self._summarize_schedules(schedules)

        # Get RAG-retrieved schedule context
        schedule_rag_context = requirements.get('schedule_context', '')

        # Include conversation context if available
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what courses, semesters, or constraints the student has mentioned. If they refer to "it", "the course", or "that semester", look at the context to understand what they mean.
"""

        prompt = f"""You are an expert academic advisor creating a semester-by-semester course plan.
{context_section}
**Student Profile:**
- Program: {params.get('program', 'N/A')}
- Current Status: {params.get('current_semester', 'Starting')}
- Completed Courses: {', '.join(params.get('completed_courses', [])) or 'None'}
- Target Graduation: {params.get('target_graduation', 'Standard 4 years')}
- Minor Interest: {params.get('include_minor', 'None')}
- Workload Preference: {params.get('workload_preference', 'balanced')}

**Program Requirements:**
{requirements.get('requirements_context', 'See program requirements')}

**Course Schedule Data (from database):**
{schedule_summary}

**Additional Schedule Context (from RAG):**
{schedule_rag_context[:2000] if schedule_rag_context else 'No additional context'}

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
            # Skip if data is not a dict (shouldn't happen after _get_course_schedules fix)
            if not isinstance(data, dict):
                continue

            term = data.get("semester", {})
            if isinstance(term, dict):
                term_name = f"{term.get('term', '')} {term.get('year', '')}".strip()
            else:
                term_name = key.replace('_', ' ').title()

            course_count = data.get("total_courses", 0)
            offerings = data.get("offerings", [])
            if not course_count and offerings:
                course_count = len(offerings)

            # Sample some courses - handle different field names
            sample_offerings = offerings[:5] if offerings else []
            course_codes = []
            for o in sample_offerings:
                if isinstance(o, dict):
                    code = o.get("course_code") or o.get("Course - ID", "")
                    if code:
                        course_codes.append(code)

            if term_name:
                sample_str = f"(e.g., {', '.join(course_codes[:3])}...)" if course_codes else ""
                summary_lines.append(f"{term_name}: {course_count} courses {sample_str}")

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
