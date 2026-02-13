"""
Planning Mode Coordinator

Orchestrates the multi-round negotiation workflow:
1. Planning Agent proposes plan (JSON)
2. Programs, Courses, Policy agents critique in PARALLEL
3. Planning Agent revises based on feedback
4. Repeat until consensus or max rounds (5)
"""
import asyncio
import uuid
import json
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from planning.schema import (
    SemesterPlan,
    CoursePlanJSON,
    AgentCritique,
    PlanningRound,
    PlanningSession
)


class PlanningModeCoordinator:
    """Coordinates the collaborative planning process."""

    MAX_ROUNDS = 6

    def __init__(
        self,
        planning_agent,
        programs_agent,
        courses_agent,
        policy_agent,
        emit_event: Optional[Callable] = None,
        db=None
    ):
        """
        Initialize the coordinator with agent instances.

        Args:
            planning_agent: AcademicPlanningAgent instance
            programs_agent: ProgramsRequirementsAgent instance
            courses_agent: CourseSchedulingAgent instance
            policy_agent: PolicyComplianceAgent instance
            emit_event: Optional callback to emit SSE events
            db: MongoDB database instance for persistence
        """
        self.planning_agent = planning_agent
        self.programs_agent = programs_agent
        self.courses_agent = courses_agent
        self.policy_agent = policy_agent
        self.emit_event = emit_event or (lambda x: None)
        self.db = db
        self.executor = ThreadPoolExecutor(max_workers=3)

    async def execute_planning_session(
        self,
        user_id: str,
        conversation_id: str,
        request: str,
        student_profile: Dict[str, Any]
    ) -> PlanningSession:
        """
        Main entry point for planning mode.

        Flow:
        1. Create planning session
        2. Loop (max 5 rounds):
           a. Planning Agent proposes plan
           b. All agents critique in PARALLEL
           c. If all approve → finalize
           d. Else → Planning Agent revises
        3. Store final plan
        4. Return session with all rounds
        """
        # Create session
        session = PlanningSession(
            session_id=f"plan_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            conversation_id=conversation_id,
            request=request,
            student_profile=student_profile,
            rounds=[],
            final_plan=None,
            status="in_progress"
        )

        # Emit session start
        self._emit({
            "type": "planning_session_start",
            "session_id": session.session_id,
            "request": request,
            "max_rounds": self.MAX_ROUNDS
        })

        # Save initial session to MongoDB
        await self._save_session(session)

        previous_critiques: List[AgentCritique] = []
        revision_notes = "Initial proposal"

        for round_num in range(1, self.MAX_ROUNDS + 1):
            # Emit round start
            self._emit({
                "type": "planning_round_start",
                "round": round_num,
                "session_id": session.session_id
            })

            # Step 1: Planning Agent proposes/revises plan
            self._emit({
                "type": "planning_proposing",
                "round": round_num,
                "agent": "academic_planning"
            })

            proposed_plan = await self._propose_plan(
                round_num=round_num,
                request=request,
                student_profile=student_profile,
                previous_critiques=previous_critiques
            )

            # Emit proposed plan
            self._emit({
                "type": "planning_proposal",
                "round": round_num,
                "plan": proposed_plan.to_dict()
            })

            # Step 2: All agents critique in PARALLEL
            self._emit({
                "type": "planning_critiquing",
                "round": round_num,
                "agents": ["programs_requirements", "course_scheduling", "policy_compliance"]
            })

            critiques = await self._gather_critiques_parallel(proposed_plan, student_profile)

            # Emit each critique
            for critique in critiques:
                self._emit({
                    "type": "planning_critique",
                    "round": round_num,
                    "agent": critique.agent_name,
                    "approved": critique.approved,
                    "issues": critique.issues,
                    "suggestions": critique.suggestions
                })

            # Step 3: Check consensus
            all_approved = all(c.approved for c in critiques)

            # Create round record
            planning_round = PlanningRound(
                round_number=round_num,
                proposed_plan=proposed_plan,
                critiques=critiques,
                all_approved=all_approved,
                revision_notes=revision_notes
            )
            session.add_round(planning_round)

            # Save updated session
            await self._save_session(session)

            # Emit round complete
            self._emit({
                "type": "planning_round_complete",
                "round": round_num,
                "all_approved": all_approved,
                "critiques_summary": {
                    "programs": next((c.approved for c in critiques if "programs" in c.agent_name), None),
                    "courses": next((c.approved for c in critiques if "course" in c.agent_name), None),
                    "policy": next((c.approved for c in critiques if "policy" in c.agent_name), None)
                }
            })

            if all_approved:
                # Consensus reached!
                session.finalize(proposed_plan, status="completed")
                await self._save_session(session)

                self._emit({
                    "type": "planning_complete",
                    "session_id": session.session_id,
                    "status": "completed",
                    "total_rounds": round_num,
                    "final_plan": proposed_plan.to_dict()
                })

                return session

            # Prepare for next round
            previous_critiques = critiques
            revision_notes = self._summarize_revisions_needed(critiques)

        # Max rounds reached - use last proposal as final
        final_plan = session.rounds[-1].proposed_plan if session.rounds else None
        session.finalize(final_plan, status="max_rounds_reached")
        await self._save_session(session)

        self._emit({
            "type": "planning_complete",
            "session_id": session.session_id,
            "status": "max_rounds_reached",
            "total_rounds": self.MAX_ROUNDS,
            "final_plan": final_plan.to_dict() if final_plan else None,
            "message": f"Maximum {self.MAX_ROUNDS} rounds reached. Final plan may have unresolved issues."
        })

        return session

    async def _propose_plan(
        self,
        round_num: int,
        request: str,
        student_profile: Dict[str, Any],
        previous_critiques: List[AgentCritique]
    ) -> CoursePlanJSON:
        """Planning agent generates or revises a plan."""

        # Build critique context for revision
        critique_context = ""
        if previous_critiques:
            critique_lines = []
            for c in previous_critiques:
                status = "APPROVED" if c.approved else "NEEDS REVISION"
                critique_lines.append(f"\n{c.agent_name.upper()} [{status}]:")
                if c.issues:
                    critique_lines.append("  Issues:")
                    for issue in c.issues:
                        critique_lines.append(f"    - {issue}")
                if c.suggestions:
                    critique_lines.append("  Suggestions:")
                    for suggestion in c.suggestions:
                        critique_lines.append(f"    - {suggestion}")
            critique_context = "\n".join(critique_lines)

        # Call planning agent to generate plan
        plan_json = await asyncio.to_thread(
            self._generate_plan_json,
            request,
            student_profile,
            round_num,
            critique_context
        )

        return plan_json

    def _get_program_name(self, student_profile: Dict[str, Any]) -> str:
        """Safely extract program/major name from student profile."""
        major = student_profile.get('major')
        if isinstance(major, list) and len(major) > 0:
            return major[0]
        elif isinstance(major, str) and major:
            return major
        return 'CS'  # Default fallback

    def _generate_plan_json(
        self,
        request: str,
        student_profile: Dict[str, Any],
        round_num: int,
        critique_context: str
    ) -> CoursePlanJSON:
        """Generate plan using planning agent's LLM."""
        from langchain_core.messages import SystemMessage

        # Safely get program name
        program_name = self._get_program_name(student_profile)

        revision_instruction = ""
        if critique_context:
            revision_instruction = f"""
PREVIOUS ROUND FEEDBACK - YOU MUST ADDRESS THESE ISSUES:
{critique_context}

Revise your plan to fix ALL issues mentioned above. Explain what you changed.
"""

        prompt = f"""You are an expert academic advisor. Generate a semester-by-semester course plan.

REQUEST: {request}

STUDENT PROFILE:
- Program: {student_profile.get('major', ['Not specified'])}
- Minor: {student_profile.get('minor', 'None')}
- Completed Courses: {student_profile.get('completed_courses', [])}
- Current Semester: {student_profile.get('current_semester', 'Not specified')}

{revision_instruction}

OUTPUT FORMAT - You MUST respond with ONLY valid JSON, no other text:
{{
    "plan_id": "plan_{round_num}",
    "student_id": "{student_profile.get('_id', 'unknown')}",
    "program": "{program_name}",
    "start_semester": "Fall 2025",
    "target_graduation": "Spring 2029",
    "semesters": [
        {{
            "semester": "Fall 2025",
            "courses": ["15-122", "21-127", "76-101"],
            "total_units": 36,
            "notes": "Foundation courses"
        }},
        {{
            "semester": "Spring 2026",
            "courses": ["15-150", "21-241", "15-213"],
            "total_units": 36,
            "notes": "Core CS courses"
        }}
    ],
    "total_units": 360,
    "requirements_met": ["Core CS", "Math Foundation"],
    "requirements_pending": ["Technical Electives", "Humanities"]
}}

IMPORTANT RULES:
1. Each semester should have 36-48 units (typically 3-4 courses)
2. Respect prerequisite chains (e.g., 15-112 before 15-122)
3. Include all required courses for the major
4. Balance workload across semesters
5. Only use courses that exist at CMU-Q

Respond with ONLY the JSON, no explanation."""

        response = self.planning_agent.llm.invoke([SystemMessage(content=prompt)])

        # Parse JSON from response
        try:
            # Try to extract JSON from response
            content = response.content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            plan_data = json.loads(content)
            return CoursePlanJSON.from_dict(plan_data)

        except (json.JSONDecodeError, IndexError) as e:
            # Fallback: create a minimal plan
            print(f"Warning: Failed to parse plan JSON: {e}")
            return CoursePlanJSON(
                plan_id=f"plan_{round_num}",
                student_id=str(student_profile.get('_id', 'unknown')),
                program=program_name,
                start_semester="Fall 2025",
                target_graduation="Spring 2029",
                semesters=[
                    SemesterPlan(semester="Fall 2025", courses=["15-112"], total_units=12, notes="Fallback plan")
                ],
                total_units=12,
                requirements_met=[],
                requirements_pending=["Unable to generate full plan"]
            )

    async def _gather_critiques_parallel(
        self,
        plan: CoursePlanJSON,
        student_profile: Dict[str, Any]
    ) -> List[AgentCritique]:
        """Run all three critique agents in PARALLEL."""

        # Create tasks for parallel execution
        loop = asyncio.get_event_loop()

        tasks = [
            loop.run_in_executor(
                self.executor,
                self._critique_programs,
                plan,
                student_profile
            ),
            loop.run_in_executor(
                self.executor,
                self._critique_courses,
                plan,
                student_profile
            ),
            loop.run_in_executor(
                self.executor,
                self._critique_policy,
                plan,
                student_profile
            )
        ]

        # Wait for all critiques in parallel
        critiques = await asyncio.gather(*tasks)

        return list(critiques)

    def _critique_programs(
        self,
        plan: CoursePlanJSON,
        student_profile: Dict[str, Any]
    ) -> AgentCritique:
        """Programs agent checks if plan meets degree requirements."""
        from langchain_core.messages import SystemMessage

        # Get program requirements context
        context = self.programs_agent.retrieve_context(
            f"{plan.program} degree requirements courses needed"
        )

        prompt = f"""You are the Programs & Requirements Agent. Critique this course plan for requirement compliance.

PROPOSED PLAN:
{json.dumps(plan.to_dict(), indent=2)}

STUDENT PROFILE:
- Major: {student_profile.get('major', 'Not specified')}
- Completed Courses: {student_profile.get('completed_courses', [])}

PROGRAM REQUIREMENTS CONTEXT:
{context}

Analyze the plan and respond with ONLY valid JSON:
{{
    "approved": true/false,
    "issues": ["list of requirement issues found"],
    "suggestions": ["list of suggestions to fix issues"],
    "confidence": 0.0-1.0,
    "details": {{
        "requirements_checked": ["list"],
        "missing_requirements": ["list"]
    }}
}}

Check for:
1. All required core courses included
2. Sufficient electives
3. Minor requirements (if applicable)
4. Prerequisites satisfied before advanced courses

Respond with ONLY JSON."""

        response = self.programs_agent.llm.invoke([SystemMessage(content=prompt)])

        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)
            return AgentCritique(
                agent_name="programs_requirements",
                approved=data.get("approved", False),
                issues=data.get("issues", []),
                suggestions=data.get("suggestions", []),
                confidence=data.get("confidence", 0.7),
                details=data.get("details", {})
            )
        except Exception as e:
            print(f"Warning: Failed to parse programs critique: {e}")
            return AgentCritique(
                agent_name="programs_requirements",
                approved=True,  # Default to approved if parsing fails
                issues=[],
                suggestions=[],
                confidence=0.5,
                details={"error": str(e)}
            )

    def _critique_courses(
        self,
        plan: CoursePlanJSON,
        student_profile: Dict[str, Any]
    ) -> AgentCritique:
        """Courses agent checks course availability and scheduling."""
        from langchain_core.messages import SystemMessage
        from course_tools import get_course_schedule, look_up_course_info

        # Check each course in the plan for availability
        availability_issues = []
        for sem_plan in plan.semesters:
            semester_key = sem_plan.semester.lower().replace(" ", "_")
            for course_code in sem_plan.courses:
                # Check if course exists
                course_info = look_up_course_info(course_code)
                if not course_info:
                    availability_issues.append(f"{course_code} not found in course catalog")
                    continue

                # Check schedule availability
                schedule = get_course_schedule(course_code, semester_key)
                if not schedule:
                    availability_issues.append(
                        f"{course_code} may not be offered in {sem_plan.semester}"
                    )

        # Get additional context from RAG
        context = self.courses_agent.retrieve_context(
            "course offerings schedule availability prerequisites"
        )

        prompt = f"""You are the Course Scheduling Agent. Critique this course plan for scheduling feasibility.

PROPOSED PLAN:
{json.dumps(plan.to_dict(), indent=2)}

AVAILABILITY CHECK RESULTS:
{json.dumps(availability_issues, indent=2) if availability_issues else "All courses appear available"}

SCHEDULE CONTEXT:
{context}

Analyze and respond with ONLY valid JSON:
{{
    "approved": true/false,
    "issues": ["list of scheduling/availability issues"],
    "suggestions": ["list of suggestions"],
    "confidence": 0.0-1.0,
    "details": {{
        "courses_checked": [],
        "unavailable_courses": []
    }}
}}

Check for:
1. Course availability in specified semesters
2. Schedule conflicts within semesters
3. Reasonable course load per semester

Respond with ONLY JSON."""

        response = self.courses_agent.llm.invoke([SystemMessage(content=prompt)])

        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            # Merge pre-computed issues
            all_issues = availability_issues + data.get("issues", [])

            return AgentCritique(
                agent_name="course_scheduling",
                approved=data.get("approved", False) and len(availability_issues) == 0,
                issues=all_issues,
                suggestions=data.get("suggestions", []),
                confidence=data.get("confidence", 0.7),
                details=data.get("details", {})
            )
        except Exception as e:
            print(f"Warning: Failed to parse courses critique: {e}")
            return AgentCritique(
                agent_name="course_scheduling",
                approved=len(availability_issues) == 0,
                issues=availability_issues,
                suggestions=[],
                confidence=0.5,
                details={"error": str(e)}
            )

    def _critique_policy(
        self,
        plan: CoursePlanJSON,
        student_profile: Dict[str, Any]
    ) -> AgentCritique:
        """Policy agent checks for policy compliance."""
        from langchain_core.messages import SystemMessage

        # Check unit limits
        policy_issues = []
        MAX_UNITS_PER_SEMESTER = 51  # CMU-Q max without overload approval

        for sem_plan in plan.semesters:
            if sem_plan.total_units > MAX_UNITS_PER_SEMESTER:
                policy_issues.append(
                    f"{sem_plan.semester}: {sem_plan.total_units} units exceeds maximum {MAX_UNITS_PER_SEMESTER}"
                )

        # Get policy context from RAG
        context = self.policy_agent.retrieve_context(
            "unit limits overload registration policies academic standing"
        )

        prompt = f"""You are the Policy & Compliance Agent. Critique this course plan for policy compliance.

PROPOSED PLAN:
{json.dumps(plan.to_dict(), indent=2)}

UNIT LIMIT CHECK:
{json.dumps(policy_issues, indent=2) if policy_issues else "All semesters within unit limits"}

POLICY CONTEXT:
{context}

Analyze and respond with ONLY valid JSON:
{{
    "approved": true/false,
    "issues": ["list of policy violations"],
    "suggestions": ["list of suggestions"],
    "confidence": 0.0-1.0,
    "details": {{
        "policies_checked": [],
        "violations": []
    }}
}}

Check for:
1. Unit limits per semester (max 51 without overload)
2. Minimum units for full-time status
3. Course repeat policies
4. Academic standing requirements

Respond with ONLY JSON."""

        response = self.policy_agent.llm.invoke([SystemMessage(content=prompt)])

        try:
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            # Merge pre-computed issues
            all_issues = policy_issues + data.get("issues", [])

            return AgentCritique(
                agent_name="policy_compliance",
                approved=data.get("approved", False) and len(policy_issues) == 0,
                issues=all_issues,
                suggestions=data.get("suggestions", []),
                confidence=data.get("confidence", 0.7),
                details=data.get("details", {})
            )
        except Exception as e:
            print(f"Warning: Failed to parse policy critique: {e}")
            return AgentCritique(
                agent_name="policy_compliance",
                approved=len(policy_issues) == 0,
                issues=policy_issues,
                suggestions=[],
                confidence=0.5,
                details={"error": str(e)}
            )

    def _summarize_revisions_needed(self, critiques: List[AgentCritique]) -> str:
        """Summarize what needs to be revised for next round."""
        lines = []
        for c in critiques:
            if not c.approved:
                lines.append(f"{c.agent_name}: {', '.join(c.issues[:3])}")
        return "; ".join(lines) if lines else "No issues"

    def _emit(self, event: dict):
        """Emit an SSE event."""
        self.emit_event(event)

    async def _save_session(self, session: PlanningSession):
        """Save session to MongoDB."""
        if self.db is not None:
            try:
                collection = self.db["planning_sessions"]
                await asyncio.to_thread(
                    collection.update_one,
                    {"session_id": session.session_id},
                    {"$set": session.to_dict()},
                    True  # upsert
                )
            except Exception as e:
                print(f"Warning: Failed to save planning session: {e}")
