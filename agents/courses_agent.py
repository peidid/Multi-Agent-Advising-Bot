"""
Course & Scheduling Agent

Responsibilities:
- Find course offerings (semester, instructor)
- Check schedule conflicts
- Provide course availability info

Knowledge Base: chroma_db_courses/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk
from langchain_core.messages import SystemMessage
from course_tools import (
    look_up_course_info, find_course_codes_in_text,
    find_course_by_name, search_courses_by_name,
    get_course_schedule, check_schedule_conflict
)
import json
import re

class CourseSchedulingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="course_scheduling",
            domain="courses"  # Uses chroma_db_courses/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """Execute Course & Scheduling agent with streaming events."""
        # Emit start event
        self.emit_start()

        try:
            user_query = state.get("user_query", "")
            plan_options = state.get("plan_options", [])
            agent_outputs = state.get("agent_outputs", {})
            messages = state.get("messages", [])

            # Get memory context (conversation history + student profile)
            memory_context = self.get_memory_context(state)

            # Check if this is a schedule conflict query
            conflict_info = self._detect_schedule_conflict_query(user_query)
            if conflict_info:
                self.emit_thinking("Checking schedule conflicts...")
                result = self._handle_schedule_conflict(conflict_info, user_query, memory_context)
                self.emit_output(result)
                self.emit_complete(confidence=result.confidence, summary="Checked schedule conflict")
                return result

            # Extract courses from plan or query
            courses = self._extract_courses(plan_options, user_query, agent_outputs, messages)

            if not courses:
                result = self._answer_general_question(user_query, messages, memory_context)
                self.emit_output(result)
                self.emit_complete(confidence=result.confidence, summary="Answered course question")
                return result

            # Check each course
            course_info = []
            risks = []

            self.emit_thinking(f"Looking up {len(courses)} courses...")

            for course_code in courses:
                # Get structured data
                course_data = look_up_course_info(course_code)

                # Get RAG context - improved query to capture all course details
                rag_query = f"course {course_code} prerequisites assessment structure content description"
                context = self.retrieve_context(rag_query)

                course_info.append({
                    "code": course_code,
                    "data": course_data,
                    "context": context
                })

            # Build prompt and call LLM
            self.emit_thinking("Generating course information...")
            prompt = self._build_prompt(user_query, course_info, risks, memory_context)
            response = self.llm.invoke([SystemMessage(content=prompt)])

            result = AgentOutput(
                agent_name=self.name,
                answer=response.content,
                confidence=0.9,
                relevant_policies=[],
                risks=risks,
                constraints=[]
            )

            self.emit_output(result)
            self.emit_complete(confidence=0.9, summary=f"Found info for {len(courses)} courses")
            return result

        except Exception as e:
            self.emit_error(str(e))
            raise
    
    def _extract_courses(self, plan_options: list, query: str, agent_outputs: dict, messages: list = None) -> list:
        """Extract course codes from various sources."""
        courses = set()
        
        # From query - improved extraction
        courses.update(find_course_codes_in_text(query))
        
        # Also check for course mentions in context (e.g., "this course", "67-364")
        # Look for patterns like "COURSE 67-364" or "course 67-364"
        course_mentions = re.findall(r'(?:course|COURSE)\s+(\d{2}-\d{3})', query, re.IGNORECASE)
        courses.update(course_mentions)
        
        # From plan options
        for plan in plan_options:
            if isinstance(plan, dict):
                courses.update(plan.get("courses", []))
            elif hasattr(plan, "courses"):
                courses.update(plan.courses)
        
        # From Programs agent output
        programs_output = agent_outputs.get("programs_requirements")
        if programs_output and programs_output.plan_options:
            for plan_option in programs_output.plan_options:
                courses.update(plan_option.courses)
        
        # Also check previous messages/context for course codes
        # This helps when user says "this course" referring to a previously mentioned course
        if not courses and messages:
            # Try to extract from the full conversation context
            for msg in messages:
                if hasattr(msg, 'content'):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    courses.update(find_course_codes_in_text(content))
                    # Also check for course mentions in messages
                    course_mentions = re.findall(r'(?:course|COURSE)\s+(\d{2}-\d{3})', content, re.IGNORECASE)
                    courses.update(course_mentions)
        
        return list(courses)
    
    def _answer_general_question(self, query: str, messages: list = None, memory_context: str = "") -> AgentOutput:
        """Answer general course questions."""
        # Try to extract course codes even if not explicitly mentioned
        course_codes = find_course_codes_in_text(query)

        # Also check for course mentions
        course_mentions = re.findall(r'(?:course|COURSE)\s+(\d{2}-\d{3})', query, re.IGNORECASE)
        course_codes.extend(course_mentions)

        # Check previous messages if no course found in current query
        if not course_codes and messages:
            for msg in messages:
                if hasattr(msg, 'content'):
                    content = msg.content if isinstance(msg.content, str) else str(msg.content)
                    course_codes.extend(find_course_codes_in_text(content))
                    course_mentions = re.findall(r'(?:course|COURSE)\s+(\d{2}-\d{3})', content, re.IGNORECASE)
                    course_codes.extend(course_mentions)

        if course_codes:
            # If we found course codes, try to get their info
            course_info = []
            for course_code in course_codes:
                course_data = look_up_course_info(course_code)
                if course_data:
                    context = self.retrieve_context(f"course {course_code} {query}")
                    course_info.append({
                        "code": course_code,
                        "data": course_data,
                        "context": context
                    })

            if course_info:
                prompt = self._build_prompt(query, course_info, [], memory_context)
                response = self.llm.invoke([SystemMessage(content=prompt)])
                return AgentOutput(
                    agent_name=self.name,
                    answer=response.content,
                    confidence=0.85,
                    relevant_policies=[],
                    risks=[],
                    constraints=[]
                )

        # Fallback to general RAG search
        context = self.retrieve_context(query)

        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what "it", "the course", "this class" etc. refer to.
"""

        prompt = f"""You are the Course & Scheduling Agent for CMU-Q.
{context_section}
Query: {query}
RAG Context: {context}

IMPORTANT:
- If the student refers to "it", "the course", "this class", look at the CONVERSATION CONTEXT above to understand what they mean
- Each retrieved chunk includes [DOCUMENT CONTEXT] metadata showing the source
- Answer questions about course offerings, schedules, availability, prerequisites, assessment structure, and course content
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.7,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
    
    def _build_prompt(self, query: str, course_info: list, risks: list, memory_context: str = "") -> str:
        """Build prompt for course checking."""
        courses_text = json.dumps(course_info, indent=2, default=str)

        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand what "it", "the course", "this class" etc. refer to.
"""

        return f"""You are the Course & Scheduling Agent for CMU-Q.
{context_section}
Your Responsibilities:
- Provide detailed information about specific courses
- Answer questions about prerequisites, assessment structure, course content, description
- Provide course offering details, schedules, and availability
- Check for schedule conflicts

Current Query: {query}

Course Information:
{courses_text}

IMPORTANT:
- If the student refers to "it", "the course", "this class", look at the CONVERSATION CONTEXT above to understand what they mean
- If course data is provided, use it directly to answer questions about prerequisites, assessment structure, course content, etc.
- The "data" field contains structured course information including:
  * prereqs.text: Prerequisites text
  * custom_fields.assessment_structure: Assessment structure
  * custom_fields.goals: Course goals
  * custom_fields.key_topics: Key topics covered
  * custom_fields.prerequisite_knowledge: Prerequisite knowledge needed
  * long_desc: Course description
  * units, min_units, max_units: Course units
- The "context" field contains RAG-retrieved information
- Be specific and accurate - cite exact information from the course data

Provide a comprehensive answer that directly addresses the user's query using the course information provided.
"""

    def _detect_schedule_conflict_query(self, query: str) -> dict:
        """
        Detect if the query is about schedule conflicts.

        Returns dict with course_name, semester, busy_day, busy_start, busy_end if detected.
        """
        query_lower = query.lower()

        # Check for conflict-related keywords
        conflict_keywords = ["busy", "conflict", "available", "free", "can i take", "will this work", "schedule"]
        has_conflict_keyword = any(kw in query_lower for kw in conflict_keywords)

        if not has_conflict_keyword:
            return None

        result = {}

        # Extract course name (look for common patterns)
        # "take Evolution", "take the Evolution course", "enroll in Evolution"
        course_patterns = [
            r'take\s+(?:the\s+)?([A-Za-z\s]+?)(?:\s+course)?(?:\s+in|\s+for|\.|,|\?|$)',
            r'enroll\s+in\s+([A-Za-z\s]+?)(?:\s+course)?(?:\s+in|\s+for|\.|,|\?|$)',
            r'(?:course|class)\s+(?:called\s+)?([A-Za-z\s]+?)(?:\s+in|\s+for|\.|,|\?|$)',
        ]
        for pattern in course_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                course_name = match.group(1).strip()
                # Filter out common non-course words
                if course_name.lower() not in ['it', 'this', 'that', 'the', 'a', 'an']:
                    result["course_name"] = course_name
                    break

        # Extract semester (Spring/Fall + year)
        semester_match = re.search(r'(spring|fall|summer)\s*(\d{4})', query, re.IGNORECASE)
        if semester_match:
            result["semester"] = f"{semester_match.group(1).lower()}_{semester_match.group(2)}"

        # Extract day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            if day in query_lower:
                result["busy_day"] = day
                break

        # Extract time range (e.g., "9-11am", "9am-11am", "09:00-11:00")
        time_patterns = [
            r'(\d{1,2}(?::\d{2})?)\s*(?:am|pm)?\s*[-–to]+\s*(\d{1,2}(?::\d{2})?)\s*(am|pm)?',
            r'(\d{1,2})\s*(am|pm)\s*[-–to]+\s*(\d{1,2})\s*(am|pm)',
        ]
        for pattern in time_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) >= 2:
                    start = groups[0]
                    end = groups[1] if len(groups) == 3 else groups[2]
                    suffix = groups[-1] if groups[-1] else "am"

                    # Add am/pm suffix if not present
                    if not re.search(r'am|pm', start, re.IGNORECASE):
                        start = f"{start}{suffix}"
                    if not re.search(r'am|pm', end, re.IGNORECASE):
                        end = f"{end}{suffix}"

                    result["busy_start"] = start
                    result["busy_end"] = end
                    break

        # Only return if we have enough info to check
        if result.get("course_name") or find_course_codes_in_text(query):
            return result

        return None

    def _handle_schedule_conflict(self, conflict_info: dict, query: str, memory_context: str) -> AgentOutput:
        """
        Handle a schedule conflict query by looking up actual schedule data.
        """
        course_name = conflict_info.get("course_name", "")
        semester = conflict_info.get("semester", "")
        busy_day = conflict_info.get("busy_day", "")
        busy_start = conflict_info.get("busy_start", "")
        busy_end = conflict_info.get("busy_end", "")

        # Try to find course by name
        course_code = None
        course_data = None

        # First try course codes in query
        codes = find_course_codes_in_text(query)
        if codes:
            course_code = codes[0]
            course_data = look_up_course_info(course_code)

        # Then try by name
        if not course_data and course_name:
            course_data = find_course_by_name(course_name)
            if course_data:
                course_code = course_data.get("code")

        # Search by name if still not found
        if not course_data and course_name:
            matches = search_courses_by_name(course_name, limit=5)
            if matches:
                # Show potential matches
                match_info = "\n".join([f"- {m['code']}: {m['name']}" for m in matches])
            else:
                match_info = "No matching courses found."
        else:
            match_info = ""

        # Get schedule info
        schedule_info = None
        conflict_result = None
        all_semesters_offered = []

        if course_code:
            # Get schedule for this specific semester
            schedule_info = get_course_schedule(course_code, semester)

            # Also check ALL semesters to see when the course is offered
            all_offerings = get_course_schedule(course_code)  # No semester filter
            all_semesters_offered = [o.get("semester", "") for o in all_offerings]

            # Check for conflicts if we have enough info
            if busy_day and busy_start and busy_end and semester and schedule_info:
                conflict_result = check_schedule_conflict(
                    course_code, semester, busy_day, busy_start, busy_end
                )

        # Determine offering status
        course_not_offered_this_semester = course_code and not schedule_info
        course_offered_other_semesters = len(all_semesters_offered) > 0

        # Also get RAG context
        rag_query = f"{course_name or course_code} schedule {semester} offerings times"
        rag_context = self.retrieve_context(rag_query)

        # Build response with LLM
        context_section = ""
        if memory_context:
            context_section = f"""
{memory_context}

IMPORTANT: Use the conversation context above to understand references.
"""

        schedule_data_str = json.dumps({
            "course_code": course_code,
            "course_name": course_data.get("name") if course_data else course_name,
            "course_found": course_data is not None,
            "semester_requested": semester,
            "schedule_info": schedule_info,
            "course_not_offered_this_semester": course_not_offered_this_semester,
            "semesters_offered": all_semesters_offered,
            "conflict_check": conflict_result,
            "potential_matches": match_info if not course_data else None
        }, indent=2, default=str)

        prompt = f"""You are the Course & Scheduling Agent for CMU-Q.
{context_section}
The student is asking about a SCHEDULE CONFLICT. Your job is to:
1. Look up the actual course schedule for the semester requested
2. Check if it conflicts with their stated availability
3. Give a DIRECT answer about whether they can take the course

User Query: {query}

SCHEDULE DATA FROM DATABASE:
{schedule_data_str}

RAG CONTEXT:
{rag_context}

IMPORTANT INSTRUCTIONS:
- If schedule_info is EMPTY but course_found is True:
  * The course EXISTS but is NOT OFFERED in the requested semester
  * Tell the student clearly: "[Course Name] is NOT offered in [Semester]"
  * If semesters_offered is empty, say "This course is not scheduled for any upcoming semester in our data"
  * If semesters_offered has entries, tell them which semesters it IS offered
- If schedule_info has data and conflict_check shows has_conflict=True, explain the conflict
- If schedule_info has data and conflict_check shows has_conflict=False, confirm they CAN take the course
- If the course wasn't found at all, suggest the potential_matches if any
- Be DIRECT and SPECIFIC - give a clear YES/NO/NOT OFFERED answer
"""

        response = self.llm.invoke([SystemMessage(content=prompt)])

        confidence = 0.9 if conflict_result and conflict_result.get("has_conflict") is not None else 0.6

        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=confidence,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )

