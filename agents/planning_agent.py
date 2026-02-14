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

# Import validation tools
try:
    from course_tools import (
        check_prereqs_satisfied,
        check_courses_conflict,
        validate_semester_plan,
        look_up_course_info
    )
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False

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

            # Get specific task assignment from coordinator (initial run)
            assigned_task = self.get_assigned_task()

            # Store for use in prompt building
            self._current_assigned_task = assigned_task
            self._current_coordinator_guidance = coordinator_guidance

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

    def _normalize_course_code(self, code: str) -> str:
        """
        Normalize course codes to XX-XXX format.

        Handles:
        - "03121" -> "03-121"
        - "03-121" -> "03-121" (already normalized)
        - "15112" -> "15-112"
        """
        if not code:
            return code

        # Remove any existing hyphens and whitespace
        clean_code = code.replace("-", "").replace(" ", "")

        # If it's 5-6 digits, insert hyphen after first 2
        if clean_code.isdigit() and len(clean_code) >= 5:
            return f"{clean_code[:2]}-{clean_code[2:]}"

        return code

    def _lookup_course_availability(self, course_code: str, semester: str, schedules: dict) -> dict:
        """
        Look up if a specific course is offered in a specific semester.

        Args:
            course_code: Course code like "15-122" or "15122"
            semester: Semester like "Fall 2025" or "Spring 2026"
            schedules: Loaded schedule data

        Returns:
            {
                "available": bool,
                "sections": [...],  # List of sections with times
                "semester_key": str  # Which schedule file matched
            }
        """
        normalized_code = self._normalize_course_code(course_code)
        semester_lower = semester.lower().replace(" ", "_")

        result = {
            "available": False,
            "sections": [],
            "semester_key": None,
            "course_code": normalized_code
        }

        for key, data in schedules.items():
            # Check if this schedule matches the requested semester
            key_lower = key.lower()
            term_info = data.get("semester", {})

            # Match by semester term
            semester_matches = False
            if isinstance(term_info, dict):
                term_str = f"{term_info.get('term', '')} {term_info.get('year', '')}".lower()
                semester_matches = semester.lower() in term_str or term_str in semester.lower()
            else:
                # Match by key (e.g., "fall_2025_courses")
                semester_matches = any(part in key_lower for part in semester_lower.split("_"))

            if not semester_matches:
                continue

            # Search for the course
            offerings = data.get("offerings", [])
            for offering in offerings:
                # Handle different field names
                offer_code = offering.get("course_code") or offering.get("Course - ID", "")
                offer_code_normalized = self._normalize_course_code(str(offer_code))

                if offer_code_normalized == normalized_code:
                    result["available"] = True
                    result["semester_key"] = key

                    # Extract section info
                    if "sections" in offering:
                        # New format (schedule_2026_spring.json)
                        for section in offering["sections"]:
                            result["sections"].append({
                                "section": section.get("section", ""),
                                "days": section.get("days", []),
                                "start_time": section.get("start_time", ""),
                                "end_time": section.get("end_time", ""),
                                "instructor": section.get("instructor", "TBA"),
                                "capacity": section.get("capacity", 0)
                            })
                    else:
                        # Old format (Fall_2025_courses.json)
                        result["sections"].append({
                            "section": offering.get("Section", ""),
                            "days": offering.get("Delivery times - Day", "").split(),
                            "start_time": offering.get("Delivery times - Start time", "").split()[0] if offering.get("Delivery times - Start time") else "",
                            "end_time": offering.get("Delivery times - End time", "").split()[0] if offering.get("Delivery times - End time") else "",
                            "instructor": offering.get("Professor - Last name", "TBA"),
                            "capacity": int(offering.get("Max Enrollment", 0)) if offering.get("Max Enrollment") else 0
                        })

        return result

    def _get_detailed_schedule_for_semester(self, semester: str, schedules: dict,
                                             relevant_courses: List[str] = None) -> str:
        """
        Get detailed schedule information for a specific semester.

        If relevant_courses is provided, only show those courses.
        Otherwise show all courses (limited to first 30).
        """
        semester_lower = semester.lower()
        details = []

        for key, data in schedules.items():
            # Check semester match
            term_info = data.get("semester", {})
            if isinstance(term_info, dict):
                term_str = f"{term_info.get('term', '')} {term_info.get('year', '')}".lower()
                matches = semester_lower in term_str or any(part in key.lower() for part in semester_lower.split())
            else:
                matches = any(part in key.lower() for part in semester_lower.split())

            if not matches:
                continue

            offerings = data.get("offerings", [])
            course_count = 0

            for offering in offerings:
                # Get course code
                code = offering.get("course_code") or offering.get("Course - ID", "")
                code_normalized = self._normalize_course_code(str(code))

                # If filtering by relevant courses, check if this one matches
                if relevant_courses:
                    if not any(self._normalize_course_code(rc) == code_normalized for rc in relevant_courses):
                        continue

                # Limit to 30 courses if not filtering
                if not relevant_courses and course_count >= 30:
                    details.append(f"... and {len(offerings) - 30} more courses")
                    break

                course_count += 1

                # Build schedule string
                if "sections" in offering:
                    for section in offering["sections"]:
                        days = ", ".join(section.get("days", []))
                        time_str = f"{section.get('start_time', '')}-{section.get('end_time', '')}"
                        instructor = section.get("instructor", "TBA")
                        details.append(f"  {code_normalized}: {days} {time_str} ({instructor})")
                else:
                    days = offering.get("Delivery times - Day", "TBA")
                    start = offering.get("Delivery times - Start time", "").split()[0] if offering.get("Delivery times - Start time") else "TBA"
                    end = offering.get("Delivery times - End time", "").split()[0] if offering.get("Delivery times - End time") else ""
                    instructor = offering.get("Professor - Last name", "TBA")
                    details.append(f"  {code_normalized}: {days} {start}-{end} ({instructor})")

        if not details:
            return f"No schedule data found for {semester}"

        return f"\n{semester}:\n" + "\n".join(details)

    def _build_planning_prompt(self, params: dict, requirements: dict,
                               schedules: dict, profile: dict,
                               memory_context: str = "") -> str:
        """Build comprehensive planning prompt based on scope."""

        # Get target semesters for focused schedule summary
        scope = params.get("scope", "full")
        specific_semesters = params.get("specific_semesters", [])
        target_program = params.get("target_program") or params.get("program", "")

        # For first_year scope, determine the likely semesters
        target_semesters = specific_semesters
        if scope == "first_year" and not target_semesters:
            # Assume current year's fall and next year's spring
            import datetime
            year = datetime.datetime.now().year
            target_semesters = [f"Fall {year}", f"Spring {year + 1}"]
        elif scope == "next_semester" and not target_semesters:
            import datetime
            month = datetime.datetime.now().month
            year = datetime.datetime.now().year
            if month < 6:
                target_semesters = [f"Fall {year}"]
            else:
                target_semesters = [f"Spring {year + 1}"]

        # Summarize available schedules with focus on target semesters
        schedule_summary = self._summarize_schedules(
            schedules,
            target_semesters=target_semesters,
            program=target_program
        )

        # Get RAG-retrieved schedule context
        schedule_rag_context = requirements.get('schedule_context', '')

        # Include conversation context if available
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what courses, semesters, or constraints the student has mentioned.
"""

        # Include coordinator's task assignment if available
        task_section = ""
        if hasattr(self, '_current_assigned_task') and self._current_assigned_task:
            task_section = f"""
{self._current_assigned_task}
"""

        # Include coordinator guidance if this is a re-run
        guidance_section = ""
        if hasattr(self, '_current_coordinator_guidance') and self._current_coordinator_guidance:
            guidance_section = f"""
{self._current_coordinator_guidance}
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
{context_section}{task_section}{guidance_section}
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

**Department Codes (first 2 digits of course code):**
- 67-XXX = Information Systems (IS)
- 15-XXX = Computer Science (CS)
- 03-XXX = Biological Sciences
- 73-XXX = Statistics
- 70-XXX = Business Administration
- 79-XXX = Dietrich College (History, Philosophy, etc.)
- 88-XXX = Social Sciences
- 76-XXX = Humanities

**Planning Instructions:**
1. RESPECT THE SCOPE - only plan for the semesters requested
2. Use specific course codes (XX-XXX format), not placeholders
3. Ensure prerequisites are satisfied
4. Balance workload (typically 45-54 units per semester)
5. If this is a transfer plan, prioritize transfer requirements
6. If a course is NOT in the schedule data for a semester, it is NOT offered that semester

{output_format}

**Important:**
- If scope is limited, DO NOT extend beyond requested semesters
- Flag any risks (overload, prerequisite issues, availability)
- Be specific with course recommendations
"""

        return prompt

    def _summarize_schedules(self, schedules: dict, target_semesters: List[str] = None,
                             program: str = None) -> str:
        """
        Summarize available schedule data with enhanced details.

        Args:
            schedules: Loaded schedule data
            target_semesters: Specific semesters to focus on (e.g., ["Fall 2025", "Spring 2026"])
            program: Target program to filter relevant courses (e.g., "CS", "IS")

        Returns:
            Detailed schedule summary with course availability info
        """
        if not schedules:
            return "No detailed schedule data available. Use general course offering patterns."

        summary_lines = []
        detailed_sections = []

        # Program-relevant course prefixes
        program_prefixes = {
            "CS": ["15-", "02-"],
            "Computer Science": ["15-", "02-"],
            "IS": ["67-", "95-", "15-"],
            "Information Systems": ["67-", "95-", "15-"],
            "BA": ["70-", "73-"],
            "Business Administration": ["70-", "73-"],
            "BIO": ["03-", "02-"],
            "Biological Sciences": ["03-", "02-"]
        }
        relevant_prefixes = program_prefixes.get(program, [])

        for key, data in sorted(schedules.items()):
            if not isinstance(data, dict):
                continue

            term = data.get("semester", {})
            if isinstance(term, dict):
                term_name = f"{term.get('term', '')} {term.get('year', '')}".strip()
            else:
                term_name = key.replace('_', ' ').title()

            # Check if this is a target semester
            is_target = False
            if target_semesters:
                for target in target_semesters:
                    if target.lower() in term_name.lower() or term_name.lower() in target.lower():
                        is_target = True
                        break

            offerings = data.get("offerings", [])
            course_count = data.get("total_courses", len(offerings))

            # Build course list with schedule details
            course_details = []
            for offering in offerings:
                code = offering.get("course_code") or offering.get("Course - ID", "")
                code_normalized = self._normalize_course_code(str(code))

                # For target semesters, show more courses (especially relevant ones)
                if is_target or (relevant_prefixes and any(code_normalized.startswith(p) for p in relevant_prefixes)):
                    if "sections" in offering:
                        for section in offering["sections"][:2]:  # Limit sections
                            days = ", ".join(section.get("days", ["TBA"]))
                            time_str = f"{section.get('start_time', 'TBA')}-{section.get('end_time', '')}"
                            instructor = section.get("instructor", "TBA")
                            course_details.append(f"    {code_normalized}: {days} {time_str} ({instructor})")
                    else:
                        days = offering.get("Delivery times - Day", "TBA")
                        start = offering.get("Delivery times - Start time", "").split()[0] if offering.get("Delivery times - Start time") else "TBA"
                        instructor = offering.get("Professor - Last name", "TBA")
                        course_details.append(f"    {code_normalized}: {days} {start} ({instructor})")

                # Limit to 20 courses per semester for prompt length
                if len(course_details) >= 20:
                    course_details.append(f"    ... and {len(offerings) - 20} more courses")
                    break

            # Add summary line
            if term_name:
                summary_lines.append(f"\n📅 {term_name}: {course_count} courses offered")
                if is_target and course_details:
                    summary_lines.append("  Relevant courses with schedules:")
                    summary_lines.extend(course_details[:15])  # Limit to prevent huge prompts
                elif course_details:
                    summary_lines.append("  Sample courses:")
                    summary_lines.extend(course_details[:8])

        result = "\n".join(summary_lines) if summary_lines else "Schedule data loaded."

        # Add availability lookup instructions
        result += "\n\n📌 Note: Use the course codes shown above when planning. If a course doesn't appear in a semester, it may not be offered that term."

        return result

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
        """
        Identify potential risks in the generated plans.

        Checks for:
        1. Prerequisite violations (course taken before prereqs completed)
        2. Schedule conflicts (overlapping class times)
        3. Overload semesters (> 54 units)
        """
        risks = []
        completed_courses = list(params.get("completed_courses", []))

        if not VALIDATION_AVAILABLE:
            return risks

        for plan in plan_options:
            semester_completed = list(completed_courses)  # Track cumulative completed

            for semester_info in plan.semesters:
                semester_name = semester_info.get("term", "Unknown Semester")
                courses = semester_info.get("courses", [])

                # Check prerequisites for each course
                for course in courses:
                    prereq_check = check_prereqs_satisfied(course, semester_completed)
                    if prereq_check.get("satisfied") is False:
                        missing = prereq_check.get("missing", [])
                        risks.append(Risk(
                            risk_type="prerequisite_violation",
                            severity="high",
                            description=f"{course} in {semester_name}: missing prerequisites {', '.join(missing)}",
                            affected_courses=[course] + missing,
                            mitigation=f"Take {', '.join(missing)} before {course}"
                        ))

                # Check for schedule conflicts between courses in same semester
                semester_normalized = semester_name.lower().replace(" ", "_")
                checked_pairs = set()

                for i, course1 in enumerate(courses):
                    for course2 in courses[i+1:]:
                        pair = tuple(sorted([course1, course2]))
                        if pair in checked_pairs:
                            continue
                        checked_pairs.add(pair)

                        conflict_check = check_courses_conflict(course1, course2, semester_normalized)
                        if conflict_check.get("has_conflict"):
                            risks.append(Risk(
                                risk_type="schedule_conflict",
                                severity="high",
                                description=f"Schedule conflict in {semester_name}: {course1} and {course2} have overlapping times",
                                affected_courses=[course1, course2],
                                mitigation=f"Choose a different section or take one course in a different semester"
                            ))

                # Check for overload (> 54 units)
                total_units = semester_info.get("total_units", 0)
                if not total_units and VALIDATION_AVAILABLE:
                    # Calculate units from course data
                    total_units = 0
                    for course in courses:
                        course_info = look_up_course_info(course)
                        if course_info:
                            total_units += course_info.get("units", 0) or course_info.get("min_units", 0) or 0

                if total_units > 54:
                    risks.append(Risk(
                        risk_type="overload",
                        severity="medium",
                        description=f"Semester {semester_name} has {total_units} units (max recommended: 54)",
                        affected_courses=courses,
                        mitigation="Consider moving one course to another semester"
                    ))

                # Add this semester's courses to completed for next iteration
                semester_completed.extend(courses)

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
