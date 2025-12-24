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
        
        # Extract courses from plan or query
        courses = self._extract_courses(plan_options, user_query, agent_outputs)
        
        if not courses:
            return self._answer_general_question(user_query)
        
        # Check each course
        course_info = []
        risks = []
        
        for course_code in courses:
            # Get structured data
            course_data = look_up_course_info(course_code)
            
            # Get RAG context
            context = self.retrieve_context(f"course {course_code} offering schedule")
            
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
    
    def _extract_courses(self, plan_options: list, query: str, agent_outputs: dict) -> list:
        """Extract course codes from various sources."""
        courses = set()
        
        # From query
        courses.update(find_course_codes_in_text(query))
        
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
        
        return list(courses)
    
    def _answer_general_question(self, query: str) -> AgentOutput:
        """Answer general course questions."""
        context = self.retrieve_context(query)
        prompt = f"""You are the Course & Scheduling Agent.

Query: {query}
Context: {context}

Answer questions about course offerings, schedules, and availability.
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.8,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
    
    def _build_prompt(self, query: str, course_info: list, risks: list) -> str:
        """Build prompt for course checking."""
        courses_text = json.dumps(course_info, indent=2)
        return f"""You are the Course & Scheduling Agent.

Query: {query}

Courses to Check:
{courses_text}

Provide:
- Course offering details
- Schedule information
- Any conflicts or constraints
- Availability status
"""

