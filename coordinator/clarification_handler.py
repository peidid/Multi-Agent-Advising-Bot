"""
Clarification Handler for Interactive Multi-Agent System

This module handles intelligent detection of ambiguous queries
and interactive clarification with users.

Research Contribution: Coordinator knows when to ask for clarification
"""

from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
import json
import re
import sys
import os

# Add parent directory to path to import course_name_mapping
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from course_name_mapping import infer_major_from_course


class ClarificationHandler:
    """
    Handles ambiguity detection and clarification question generation.
    
    This is integrated into the coordinator's workflow planning.
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def check_for_clarification(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        student_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if the query requires clarification before proceeding.
        
        Returns:
            Dict with:
            - needs_clarification: bool
            - confidence: float
            - missing_info: List[str]
            - questions: List[Dict]
            - reasoning: str
        """
        # Extract what we know from profile
        known_major = student_profile.get('major') or student_profile.get('program')
        known_semester = student_profile.get('semester') or student_profile.get('current_semester')
        
        # PRE-CHECK: Extract major from query if explicitly mentioned
        query_lower = query.lower()
        major_patterns = {
            'Computer Science': ['cs student', 'computer science student', 'i\'m a cs', 'i am a cs', 'as a cs'],
            'Information Systems': ['is student', 'information systems student', 'i\'m an is', 'i am an is', 'as an is'],
            'Biological Sciences': ['bio student', 'biology student', 'biological sciences student', 'i\'m a bio', 'i am a bio', 'as a bio'],
            'Business Administration': ['ba student', 'business administration student', 'business student', 'i\'m a ba', 'i am a ba', 'as a ba']
        }
        
        for major, patterns in major_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                # Major is explicitly mentioned in query!
                return {
                    'needs_clarification': False,
                    'confidence': 1.0,
                    'missing_info': [],
                    'reasoning': f'Major ({major}) explicitly mentioned in query',
                    'questions': [],
                    'extracted_major': major  # Pass this to coordinator
                }
        
        # NEW: Try to infer major from course mentions ONLY if query doesn't need major for answer
        # Check if the query explicitly asks about requirements/retaking/degree progress
        needs_major_keywords = [
            'required', 'requirement', 'need to take', 'must take', 'have to take',
            'retake', 'degree', 'major', 'graduation', 'count for', 'fulfill'
        ]
        query_needs_major = any(keyword in query.lower() for keyword in needs_major_keywords)
        
        if not known_major and not query_needs_major:
            # Only infer if query is general (e.g., "What are prerequisites?")
            inferred_major = infer_major_from_course(query)
            if inferred_major != "Unknown":
                # Don't ask for clarification - we can infer it!
                return {
                    'needs_clarification': False,
                    'confidence': 0.85,
                    'missing_info': [],
                    'reasoning': f'Inferred major ({inferred_major}) from course context for general query',
                    'questions': [],
                    'inferred_major': inferred_major  # Pass this to coordinator
                }
        
        # Build context
        history_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
            for msg in conversation_history[-4:]  # Last 2 turns
        ]) if conversation_history else "No previous conversation"
        
        prompt = f"""You are an academic advisor analyzing a student's query for ambiguity.

Query: "{query}"

Current Knowledge:
- Major/Program: {known_major if known_major else "UNKNOWN"}
- Semester: {known_semester if known_semester else "UNKNOWN"}
- Recent conversation: {history_text}

Your task: Determine if you have enough information to answer this query accurately.

Critical information needed for advising:
1. Student's major/program (CS, IS, Biological Sciences, Business Administration)
2. Current semester/year (for course sequencing)
3. Completed courses (for prerequisite checking)
4. Academic standing (for special cases)

QUERIES THAT NEED MAJOR (clarification required if major unknown):
- "Do I need to take [specific course]?" → Requirements vary by major
- "Is [course] required for me?" → Depends on major
- "What courses are required for my major?" → Major-specific
- "Can I graduate on time?" → Need major + semester + courses taken
- "Does [course] count for my concentration?" → Major-specific requirements

QUERIES THAT DON'T NEED MAJOR (NO clarification needed):
1. General Policies & Procedures (apply to ALL students):
   - "How do I enroll in a course?"
   - "What happens if I drop/withdraw/fail a course?"
   - "Can I take more than X units?"
   - "How do I declare a minor?"
   - "What is Pass/Fail policy?"
   - "What is the minimum QPA?"
   - "How do I request a transcript?"
   - "Can I take courses at another university?"
   
2. Course Information (not major-specific):
   - "What are prerequisites for [course]?"
   - "Can I take grad courses as undergrad?"
   - "What happens if a course is full?"
   - "How do I get instructor permission?"
   
3. General Academic Advice (applicable to all):
   - "What should I do if I have time conflicts?"
   - "How often should I meet my advisor?"
   - "When should I look for internships?"
   - "Can I study abroad?"

4. Major Already Specified:
   - "As a CS student, what courses do I need?"
   - "I'm an IS junior, can I..."

IMPORTANT - DO NOT infer major from course mentions if:
- Query asks about requirements ("Do I need X?", "Is X required?", "Should I retake?")
- Query asks about degree progress ("Can I graduate?", "Am I on track?")
- Query asks about counting towards degree ("Does this count for my major?")
- Answer varies significantly by major

Students from ANY major can take courses from ANY department:
- CS students take Bio courses (science requirements)
- Bio students take CS courses (electives)
- Taking a course ≠ Being in that major's program

Only skip asking for major if:
- Major is explicitly stated in the query
- Query is purely informational (prerequisites, policy, course content)

Analyze the query and respond in JSON format:
{{
    "needs_clarification": true/false,
    "confidence": 0.0-1.0,
    "missing_info": ["major", "semester", "courses_taken"],
    "can_answer_without": true/false,
    "reasoning": "Why clarification is or isn't needed",
    "questions": [
        {{
            "question": "What is your major or program? (Please spell out full name)",
            "why": "Requirements differ significantly between programs",
            "type": "major",
            "options": ["Computer Science (CS)", "Information Systems (IS)", "Biological Sciences (Bio)", "Business Administration (BA)"],
            "note": "Please use full major name to avoid confusion (e.g., 'Biological Sciences' not 'BS')"
        }}
    ]
}}

DECISION RULES (FOLLOW STRICTLY):
1. ✅ NO clarification if query asks about:
   - University policies (grading, dropping, QPA, etc.)
   - Enrollment procedures (how to register, add/drop, etc.)
   - General academic processes (advising, transcripts, etc.)
   - Course logistics (prerequisites, waitlists, permissions)
   - Career/life advice (internships, study abroad, etc.)
   → These have UNIVERSAL answers that apply to all students

2. ⚠️ YES clarification if query asks about:
   - "My requirements" or "What do I need?" (major-specific)
   - "Does this count for my major/concentration?" (major-specific)
   - "Should I retake this for my degree?" (major-specific)
   - Course planning specific to graduation requirements
   → These answers VARY significantly by major

3. 🎯 Special cases:
   - If major is mentioned in query → NO clarification
   - If query is from conversation context → Check history for major
   - If student profile has major → NO clarification
   - If query has general tone (e.g., "students can...") → NO clarification

BE CONSERVATIVE: Default to NOT asking unless answer CRITICALLY depends on major
"""
        
        try:
            response = self.llm.invoke([SystemMessage(content=prompt)])
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
            
        except Exception as e:
            print(f"⚠️  Clarification check error: {e}")
        
        # Default: proceed without clarification
        return {
            'needs_clarification': False,
            'confidence': 0.8,
            'missing_info': [],
            'reasoning': 'Proceeding with available information',
            'questions': []
        }
