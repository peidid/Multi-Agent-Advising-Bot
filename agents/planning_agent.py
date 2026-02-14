"""
Academic Planning Agent

Responsibilities:
- Generate semester-by-semester course plans
- Ensure prerequisite sequencing
- Balance workload across semesters
- Consider course availability patterns

Knowledge Base: chroma_db_planning/ (programs + schedules)
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
            domain="planning"  # Combined domain: programs + schedules
        )
        # Keep separate schedules retriever for targeted schedule queries
        self.schedules_retriever = get_retriever(domain="schedules", k=5)

    def execute(self, state: BlackboardState) -> AgentOutput:
        """Generate multi-semester academic plan with streaming events."""
        # Emit start event
        self.emit_start()

        # Set enhanced retrieval k if provided (for confidence-based re-retrieval)
        self.set_retrieval_k_from_state(state)

        try:
            user_query = state.get("user_query", "")
            student_profile = state.get("student_profile", {})
            agent_outputs = state.get("agent_outputs", {})

            # Get memory context (conversation history + student profile)
            memory_context = self.get_memory_context(state)

            # Get coordinator feedback if this is a re-run
            coordinator_guidance = self.get_coordinator_guidance()

            # Enhance query with coordinator guidance if available
            if coordinator_guidance:
                gaps = state.get("coordinator_feedback", {}).get(self.name, {}).get("gaps", [])
                if gaps:
                    # Use gaps to improve retrieval
                    self._coordinator_gaps = gaps

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
        Determine if the user is asking for an academic plan (full or partial).

        Returns True if user asks for any kind of plan/schedule.
        The SCOPE of the plan is determined separately in _extract_planning_parameters.
        """
        query_lower = query.lower()

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

        # Keywords that indicate a planning request (any scope)
        planning_keywords = [
            "plan", "schedule", "curriculum", "course plan", "courses for",
            "what courses", "which courses", "semester plan",
            "first year", "second year", "third year", "fourth year",
            "fall", "spring", "sample"
        ]

        # Check for planning indicators
        for keyword in planning_keywords:
            if keyword in query_lower:
                return True

        return False

    def _extract_plan_scope(self, query: str) -> dict:
        """
        Extract the SCOPE of the planning request.

        Returns:
            {
                "scope": "full" | "first_year" | "specific_semesters" | "next_semester",
                "semesters": ["Fall 2025", "Spring 2026"],  # specific semesters if mentioned
                "target_program": "CS" | "IS" | None,  # if switching majors
                "is_transfer": bool  # if user wants to switch majors
            }
        """
        query_lower = query.lower()
        scope = {
            "scope": "full",
            "semesters": [],
            "target_program": None,
            "is_transfer": False
        }

        # Detect major transfer intent
        transfer_patterns = [
            r'switch\s+(?:from\s+)?(\w+)\s+to\s+(\w+)',
            r'transfer\s+(?:from\s+)?(\w+)\s+to\s+(\w+)',
            r'change\s+(?:from\s+)?(\w+)\s+to\s+(\w+)',
            r'switch\s+to\s+(\w+)',
            r'transfer\s+to\s+(\w+)',
            r'change\s+to\s+(\w+)'
        ]
        for pattern in transfer_patterns:
            match = re.search(pattern, query_lower)
            if match:
                scope["is_transfer"] = True
                groups = match.groups()
                # Last group is always the target
                scope["target_program"] = groups[-1].upper()
                break

        # Detect scope limitations
        if re.search(r'first\s*year|year\s*1|freshman', query_lower):
            scope["scope"] = "first_year"
        elif re.search(r'second\s*year|year\s*2|sophomore', query_lower):
            scope["scope"] = "second_year"
        elif re.search(r'next\s*semester', query_lower):
            scope["scope"] = "next_semester"

        # Extract specific semesters mentioned
        semester_pattern = r'(fall|spring|summer)\s*(\d{4})'
        matches = re.findall(semester_pattern, query_lower)
        if matches:
            scope["semesters"] = [f"{term.title()} {year}" for term, year in matches]
            scope["scope"] = "specific_semesters"

        return scope

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
        # Get scope first
        scope_info = self._extract_plan_scope(query)

        # Determine the target program (for transfers) or current program
        target_program = scope_info.get("target_program")
        if not target_program:
            # Use profile major, extract first if it's a list
            major = profile.get("major", "Computer Science")
            if isinstance(major, list) and major:
                target_program = major[0]
            else:
                target_program = major or "Computer Science"

        params = {
            "program": target_program,
            "current_program": profile.get("major", "Information Systems"),  # What they're currently in
            "current_semester": profile.get("current_semester", "First-Year Fall"),
            "completed_courses": profile.get("completed_courses", []),
            "target_graduation": None,
            "include_minor": None,
            "workload_preference": "balanced",  # balanced, light, heavy
            "constraints": [],
            # Scope-related fields
            "scope": scope_info["scope"],
            "specific_semesters": scope_info["semesters"],
            "is_transfer": scope_info["is_transfer"],
            "target_program": scope_info["target_program"]
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

        return params

    def _get_program_requirements(self, params: dict, outputs: dict) -> dict:
        """Retrieve program requirements from RAG or previous agent outputs."""
        program = params.get("program", "Computer Science")
        is_transfer = params.get("is_transfer", False)
        target_program = params.get("target_program")

        # Use Programs agent output if available (it has already done research)
        if "programs_requirements" in outputs:
            prog_output = outputs["programs_requirements"]
            context = prog_output.answer if hasattr(prog_output, 'answer') else ""
        else:
            # Query RAG for requirements
            if is_transfer and target_program:
                # For transfers, search for transfer requirements and target program
                rag_query = f"{target_program} internal transfer requirements prerequisites policy switch major"
            else:
                rag_query = f"{program} major requirements core courses electives sample curriculum"
            context = self.retrieve_context(rag_query)

        # Also get schedule context from schedules RAG
        schedule_program = target_program if is_transfer else program
        schedule_rag_query = f"{schedule_program} course offerings schedule availability"
        try:
            schedule_docs = self.schedules_retriever.invoke(schedule_rag_query)
            schedule_context = "\n\n".join([doc.page_content for doc in schedule_docs])
        except Exception as e:
            print(f"Warning: Could not retrieve schedule context: {e}")
            schedule_context = ""

        return {
            "program": program,
            "target_program": target_program,
            "is_transfer": is_transfer,
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
        """Build comprehensive planning prompt based on scope."""

        # Summarize available schedules
        schedule_summary = self._summarize_schedules(schedules)

        # Get RAG-retrieved schedule context
        schedule_rag_context = requirements.get('schedule_context', '')

        # Include conversation context if available
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what courses, semesters, or constraints the student has mentioned.
"""

        # Determine scope-specific instructions
        scope = params.get("scope", "full")
        specific_semesters = params.get("specific_semesters", [])
        is_transfer = params.get("is_transfer", False)
        target_program = params.get("target_program")

        # Build scope-aware planning instructions
        if scope == "specific_semesters" and specific_semesters:
            scope_instruction = f"""**SCOPE: SPECIFIC SEMESTERS ONLY**
The user is asking for a plan for ONLY these semesters: {', '.join(specific_semesters)}
DO NOT generate a full 4-year or 8-semester plan.
ONLY provide the courses for the requested semesters."""
            output_format = f"""**Output Format:**
For each requested semester ({', '.join(specific_semesters)}), provide:

{specific_semesters[0]}:
- XX-XXX: Course Name (X units)
- XX-XXX: Course Name (X units)
- ...
Total: X units

{specific_semesters[1] if len(specific_semesters) > 1 else ''}
..."""
        elif scope == "first_year":
            scope_instruction = """**SCOPE: FIRST YEAR ONLY**
The user is asking for a FIRST-YEAR plan only (typically Fall and Spring of year 1).
DO NOT generate a full 4-year plan. ONLY provide courses for the first year (2 semesters)."""
            output_format = """**Output Format:**
Fall [Year]:
- XX-XXX: Course Name (X units)
- XX-XXX: Course Name (X units)
Total: X units

Spring [Year]:
- XX-XXX: Course Name (X units)
- XX-XXX: Course Name (X units)
Total: X units

Key Notes:
- [Important sequencing/prerequisite notes]
- [What to prioritize]"""
        elif scope == "next_semester":
            scope_instruction = """**SCOPE: NEXT SEMESTER ONLY**
The user is asking for recommendations for the NEXT semester only.
DO NOT generate a full plan."""
            output_format = """**Output Format:**
[Semester Year]:
- XX-XXX: Course Name (X units)
- XX-XXX: Course Name (X units)
Total: X units"""
        else:
            scope_instruction = """**SCOPE: FULL GRADUATION PLAN**
Create a complete semester-by-semester plan from current status to graduation."""
            output_format = """**Output Format:**
PLAN A: [Brief description]
Semester 1 (Term Year):
- XX-XXX: Course Name (X units)
...
[Continue for all semesters until graduation]

RATIONALE FOR PLAN A:
[Explain sequencing strategy]"""

        # Add transfer-specific context if switching majors
        transfer_section = ""
        if is_transfer and target_program:
            transfer_section = f"""
**MAJOR TRANSFER CONTEXT:**
The student wants to SWITCH TO {target_program}. This plan must:
1. Prioritize courses required for internal transfer to {target_program}
2. Include any transfer-prerequisite courses (check transfer policy requirements)
3. Focus on meeting transfer eligibility, not the current major's requirements
4. Note the transfer application timing and requirements
"""

        prompt = f"""You are an expert academic advisor creating a course plan for CMU-Q.
{context_section}
{scope_instruction}
{transfer_section}
**Student Profile:**
- Current Program: {params.get('current_program', 'N/A')}
- Target Program: {params.get('program', params.get('current_program', 'N/A'))}
- Current Status: {params.get('current_semester', 'Starting')}
- Completed Courses: {', '.join(params.get('completed_courses', [])) or 'None'}
- Workload Preference: {params.get('workload_preference', 'balanced')}

**Program Requirements:**
{requirements.get('requirements_context', 'See program requirements')}

**Course Schedule Data:**
{schedule_summary}

**Additional Context:**
{schedule_rag_context[:2000] if schedule_rag_context else 'No additional context'}

**Planning Instructions:**
1. RESPECT THE SCOPE - only plan for the semesters requested
2. Use specific course codes (XX-XXX format), not placeholders
3. Ensure prerequisites are satisfied
4. Balance workload (typically 45-54 units per semester)
5. If this is a transfer plan, prioritize transfer requirements

{output_format}

**Important:**
- If scope is limited, DO NOT extend beyond requested semesters
- Flag any risks (overload, prerequisite issues, availability)
- Be specific with course recommendations
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
