"""
Academic Planning Agent

Responsibilities:
- Generate semester-by-semester course plans
- Ensure prerequisite sequencing
- Balance workload across semesters
- Consider course availability patterns

Knowledge Base: chroma_db_planning/ (programs + schedules + courses)
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, PlanOption, Risk
from langchain_core.messages import SystemMessage
import json
import re


class AcademicPlanningAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="academic_planning",
            domain="planning"  # Combined domain: programs + schedules + courses
        )

    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Academic Planning agent.

        Simple pattern matching Programs Agent:
        1. Read state
        2. Retrieve context via RAG
        3. Build prompt
        4. Call LLM
        5. Parse and return
        """
        # Emit start event
        self.emit_start()

        # Set enhanced retrieval k if provided (for confidence-based re-retrieval)
        self.set_retrieval_k_from_state(state)

        try:
            # 1. Read from Blackboard
            raw_query = state.get("user_query", "")
            effective_query = self.get_effective_query(state)
            user_goal = state.get("user_goal", "")
            student_profile = state.get("student_profile", {})
            agent_outputs = state.get("agent_outputs", {})

            # Get memory context (conversation history + student profile)
            memory_context = self.get_memory_context(state)
            # Resolved short-term memory block
            resolved_memory_block = self.format_resolved_context_for_prompt(state)

            # Get coordinator feedback if this is a re-run
            coordinator_guidance = self.get_coordinator_guidance()

            # Get specific task assignment from coordinator
            assigned_task = self.get_assigned_task()

            # 2. Retrieve domain-specific context — use resolved query so
            # retrieval pulls docs about the actual entities (not pronouns).
            query_for_rag = f"{effective_query} {user_goal}"
            if coordinator_guidance:
                gaps = state.get("coordinator_feedback", {}).get(self.name, {}).get("gaps", [])
                if gaps:
                    query_for_rag += " " + " ".join(gaps[:3])
            # Boost retrieval with focus entities from short-term memory.
            rc_entities = self.get_resolved_context(state).get("focus_entities", {})
            entity_terms = (rc_entities.get("courses", []) +
                            rc_entities.get("programs", []) +
                            rc_entities.get("semesters", []))
            if entity_terms:
                query_for_rag += " " + " ".join(entity_terms)

            self.emit_thinking("Retrieving course and schedule information...")
            context = self.retrieve_context(query_for_rag)

            # Also get schedule-specific context for availability
            schedule_context = self._get_schedule_context(effective_query)

            # Get relevant info from other agents if available
            other_agent_info = self._summarize_other_agents(agent_outputs)

            # 3. Build prompt
            self.emit_thinking("Generating academic plan...")
            prompt = self._build_prompt(
                query=effective_query,
                raw_query=raw_query,
                goal=user_goal,
                profile=student_profile,
                context=context,
                schedule_context=schedule_context,
                other_agent_info=other_agent_info,
                memory_context=memory_context,
                coordinator_guidance=coordinator_guidance,
                assigned_task=assigned_task,
                resolved_memory_block=resolved_memory_block,
            )

            # 4. Call LLM
            response = self.llm.invoke([SystemMessage(content=prompt)])

            # 5. Parse and return structured output
            result = self._parse_response(response.content)

            # Emit output
            self.emit_output(result)
            plan_count = len(result.plan_options) if result.plan_options else 0
            self.emit_complete(
                confidence=result.confidence,
                summary=f"Generated {plan_count} plan option(s)"
            )

            return result

        except Exception as e:
            self.emit_error(str(e))
            raise

    def _get_schedule_context(self, query: str) -> str:
        """Get additional schedule-specific context via RAG."""
        try:
            # Use the schedules retriever for targeted schedule queries
            from rag_engine_improved import get_retriever
            schedules_retriever = get_retriever(domain="schedules", k=5)

            # Extract semester if mentioned
            semester_match = re.search(r'(spring|fall|summer)\s*(\d{4})', query, re.IGNORECASE)
            if semester_match:
                semester = f"{semester_match.group(1)} {semester_match.group(2)}"
                schedule_query = f"course schedule offerings {semester}"
            else:
                schedule_query = "course schedule offerings availability"

            results = schedules_retriever.invoke(schedule_query)
            return "\n".join([doc.page_content for doc in results])
        except Exception as e:
            print(f"Warning: Could not retrieve schedule context: {e}")
            return ""

    def _summarize_other_agents(self, agent_outputs: dict) -> str:
        """Summarize relevant info from other agents."""
        summaries = []

        # Programs agent may have already analyzed requirements
        if "programs_requirements" in agent_outputs:
            prog = agent_outputs["programs_requirements"]
            if hasattr(prog, 'answer') and prog.answer:
                summaries.append(f"Programs Agent found:\n{prog.answer[:500]}")

        # Courses agent may have schedule/prereq info
        if "course_scheduling" in agent_outputs:
            course = agent_outputs["course_scheduling"]
            if hasattr(course, 'answer') and course.answer:
                summaries.append(f"Courses Agent found:\n{course.answer[:500]}")

        return "\n\n".join(summaries) if summaries else ""

    def _build_prompt(self, query: str, goal: str, profile: dict, context: str,
                      schedule_context: str, other_agent_info: str,
                      memory_context: str = "", coordinator_guidance: str = "",
                      assigned_task: str = "", raw_query: str = "",
                      resolved_memory_block: str = "") -> str:
        """Build prompt for Planning agent - let LLM do the reasoning."""

        profile_text = json.dumps(profile, indent=2) if profile else "Not provided"

        # Resolved short-term working memory (authoritative for what the
        # student means right now — pronouns expanded, focus entities listed).
        working_memory_section = ""
        if resolved_memory_block:
            working_memory_section = f"\n{resolved_memory_block}\n"

        # Include conversation context if available
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: The RESOLVED WORKING MEMORY block above is the ground truth for what the student is asking about right now. Use the raw conversation history only as supporting context for richer history.
"""

        # Include coordinator's task assignment
        task_section = ""
        if assigned_task:
            task_section = f"""
{assigned_task}
"""

        # Include coordinator guidance if this is a re-run
        guidance_section = ""
        if coordinator_guidance:
            guidance_section = f"""
{coordinator_guidance}
IMPORTANT: The coordinator has identified gaps in your previous response. Focus on addressing these specific areas.
"""

        # Include other agents' findings
        other_agents_section = ""
        if other_agent_info:
            other_agents_section = f"""
## Information from Other Agents
{other_agent_info}

Use this information to inform your plan. Do not contradict verified requirements or schedule data from other agents.
"""

        query_block = f"## User Query (resolved)\n{query}"
        if raw_query and raw_query != query:
            query_block += f"\n\n## User Query (original)\n{raw_query}"

        return f"""You are the Academic Planning Agent for CMU-Q.
{working_memory_section}{context_section}{task_section}{guidance_section}

## Your Responsibilities
1. Generate semester-by-semester course plans
2. Ensure prerequisites are satisfied BEFORE taking each course
3. Verify courses are actually offered in the planned semester
4. Balance workload (typically 45-54 units per semester)
5. Consider the student's goals, constraints, and timeline

## Student Profile
{profile_text}

## User Goal
{goal}

{query_block}

## Retrieved Context (Programs, Schedules, and Course Prerequisites)
{context}

## Schedule Information
{schedule_context if schedule_context else "Use the schedule data from retrieved context above."}
{other_agents_section}

## CRITICAL Instructions

### Prerequisites
- BEFORE recommending any course, check its prerequisites in the retrieved context
- The student's completed courses are listed in their profile
- DO NOT recommend a course if its prerequisites are not satisfied
- If you cannot verify prerequisites, explicitly state this uncertainty

### Course Availability
- Only recommend courses that are offered in the planned semester
- The schedule data shows which courses are offered when
- If a course is NOT in the schedule for a semester, it may not be offered
- If you cannot verify availability, explicitly state this uncertainty

### Department Codes
- 67-XXX = Information Systems (IS)
- 15-XXX = Computer Science (CS)
- 03-XXX = Biological Sciences
- 73-XXX = Statistics
- 70-XXX = Business Administration
- 79-XXX = Dietrich College
- 36-XXX = Statistics & Data Science

### Output Quality
- Use specific course codes (XX-XXX format)
- Explain your reasoning for course sequencing
- Flag any risks or uncertainties
- If adding a minor, show how it integrates with major requirements

## Response Format
Provide your response as JSON:
{{
    "answer": "Your detailed plan with explanations",
    "confidence": 0.85,
    "relevant_policies": ["Prerequisite policy", "Unit limits"],
    "risks": [
        {{"type": "prerequisite_uncertainty", "severity": "medium", "description": "Could not verify prereqs for 15-251"}}
    ],
    "plan_options": [
        {{
            "semesters": [
                {{"term": "Spring 2026", "courses": ["15-122", "67-250"], "total_units": 24}},
                {{"term": "Fall 2026", "courses": ["15-150", "67-262"], "total_units": 24}}
            ],
            "courses": ["15-122", "67-250", "15-150", "67-262"],
            "confidence": 0.8,
            "justification": "This sequence ensures prerequisites are met..."
        }}
    ]
}}

REMEMBER: Quality over completeness. It's better to propose fewer courses with verified prerequisites than many courses with unverified ones.
"""

    def _parse_response(self, response_text: str) -> AgentOutput:
        """Parse LLM response into structured AgentOutput."""
        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback
                data = {
                    "answer": response_text,
                    "confidence": 0.7,
                    "relevant_policies": [],
                    "risks": [],
                    "plan_options": []
                }

            # Convert to AgentOutput
            risks = []
            for r in data.get("risks", []):
                if isinstance(r, dict):
                    risks.append(Risk(
                        type=r.get("type", "unknown"),
                        severity=r.get("severity", "medium"),
                        description=r.get("description", "")
                    ))

            plan_options = []
            for p in data.get("plan_options", []):
                if isinstance(p, dict):
                    plan_options.append(PlanOption(
                        semesters=p.get("semesters", []),
                        courses=p.get("courses", []),
                        confidence=p.get("confidence", 0.7),
                        justification=p.get("justification", ""),
                        risks=[],
                        policy_citations=[]
                    ))

            return AgentOutput(
                agent_name=self.name,
                answer=data.get("answer", response_text),
                confidence=data.get("confidence", 0.8),
                relevant_policies=data.get("relevant_policies", []),
                risks=risks,
                constraints=[],
                plan_options=plan_options if plan_options else None
            )
        except Exception as e:
            print(f"Error parsing Planning agent response: {e}")
            return AgentOutput(
                agent_name=self.name,
                answer=response_text,
                confidence=0.7,
                relevant_policies=[],
                risks=[],
                constraints=[]
            )
