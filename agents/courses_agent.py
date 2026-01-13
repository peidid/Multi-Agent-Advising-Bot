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
from course_tools import look_up_course_info, find_course_codes_in_text
import json
import re

class CourseSchedulingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="course_scheduling",
            domain="courses"  # Uses chroma_db_courses/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """Execute Course & Scheduling agent."""
        user_query = state.get("user_query", "")
        plan_options = state.get("plan_options", [])
        agent_outputs = state.get("agent_outputs", {})
        messages = state.get("messages", [])
        
        # Extract courses from plan or query
        courses = self._extract_courses(plan_options, user_query, agent_outputs, messages)
        
        if not courses:
            return self._answer_general_question(user_query, messages)
        
        # Check each course
        course_info = []
        risks = []
        
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
        prompt = self._build_prompt(user_query, course_info, risks)
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=risks,
            constraints=[]
        )
    
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
    
    def _answer_general_question(self, query: str, messages: list = None) -> AgentOutput:
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
                prompt = self._build_prompt(query, course_info, [])
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
        prompt = f"""You are the Course & Scheduling Agent for CMU-Q.

Query: {query}
Context: {context}

Answer questions about course offerings, schedules, availability, prerequisites, assessment structure, and course content.
If the query mentions a specific course but no course code was found, try to infer which course is being discussed from the context.
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
    
    def _build_prompt(self, query: str, course_info: list, risks: list) -> str:
        """Build prompt for course checking."""
        courses_text = json.dumps(course_info, indent=2, default=str)
        return f"""You are the Course & Scheduling Agent for CMU-Q.

Your Responsibilities:
- Provide detailed information about specific courses
- Answer questions about prerequisites, assessment structure, course content, description
- Provide course offering details, schedules, and availability
- Check for schedule conflicts

Query: {query}

Course Information:
{courses_text}

IMPORTANT: 
- If course data is provided, use it directly to answer questions about prerequisites, assessment structure, course content, etc.
- The "data" field contains structured course information including:
  * prereqs.text: Prerequisites text
  * custom_fields.assessment_structure: Assessment structure
  * custom_fields.goals: Course goals
  * custom_fields.key_topics: Key topics covered
  * custom_fields.prerequisite_knowledge: Prerequisite knowledge needed
  * long_desc: Course description
  * units, min_units, max_units: Course units
- The "context" field contains additional RAG-retrieved information
- Be specific and accurate - cite exact information from the course data
- If asked about prerequisites, provide the exact text from prereqs.text
- If asked about assessment structure, provide details from custom_fields.assessment_structure

Provide a comprehensive answer that directly addresses the user's query using the course information provided.
"""

