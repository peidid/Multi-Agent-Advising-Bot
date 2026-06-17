"""
Enhanced Intent Classification for ACL 2026 Research

Key Improvements:
1. Entity extraction (courses, programs, policies)
2. Conversation history awareness
3. Confidence scoring
4. Ambiguity detection
5. Reasoning traces
"""

from typing import Dict, List, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import json
import re
from dataclasses import dataclass, asdict
from enum import Enum


class IntentType(Enum):
    """Supported intent types."""
    COURSE_INFO = "course_info"
    CHECK_REQUIREMENTS = "check_requirements"
    PLAN_SEMESTER = "plan_semester"
    ADD_MINOR = "add_minor"
    POLICY_QUESTION = "policy_question"
    VALIDATE_PLAN = "validate_plan"
    GENERAL = "general"


@dataclass
class ExtractedEntities:
    """Entities extracted from query."""
    courses: List[str]  # e.g., ["15-213", "15-251"]
    programs: List[str]  # e.g., ["CS major", "Business minor"]
    policies: List[str]  # e.g., ["overload", "prerequisites"]
    temporal: List[str]  # e.g., ["next semester", "fall 2026"]
    people: List[str]  # e.g., ["advisor", "professor"]


@dataclass
class Intent:
    """Structured intent with confidence and reasoning."""
    intent_type: IntentType
    sub_intents: List[str]  # e.g., ["check_prerequisites", "check_conflicts"]
    required_agents: List[str]
    confidence: float  # 0-1
    reasoning: str
    entities: ExtractedEntities
    ambiguities: List[str]  # Things that are unclear
    needs_clarification: bool
    clarification_questions: List[str]


@dataclass
class ReasoningStep:
    """One step in the reasoning trace."""
    step_name: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str


class ReasoningTrace:
    """Tracks reasoning for explainability."""
    
    def __init__(self):
        self.steps: List[ReasoningStep] = []
    
    def add_step(self, step_name: str, input_data: Dict, output_data: Dict, reasoning: str):
        self.steps.append(ReasoningStep(step_name, input_data, output_data, reasoning))
    
    def to_dict(self) -> Dict:
        return {"steps": [asdict(step) for step in self.steps]}
    
    def explain(self) -> str:
        """Generate human-readable explanation."""
        explanation = "Reasoning Trace:\n"
        for i, step in enumerate(self.steps, 1):
            explanation += f"\n{i}. {step.step_name}\n"
            explanation += f"   {step.reasoning}\n"
        return explanation


class EnhancedIntentClassifier:
    """
    Enhanced intent classifier with:
    - Entity extraction
    - Conversation history
    - Confidence scoring
    - Ambiguity detection
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def classify(self, 
                query: str, 
                conversation_history: List[Dict] = None,
                student_profile: Dict = None) -> Tuple[Intent, ReasoningTrace]:
        """
        Classify intent with full context.
        
        Returns:
            Intent object with confidence and reasoning
            ReasoningTrace for explainability
        """
        trace = ReasoningTrace()
        
        # Step 1: Entity Extraction
        entities = self._extract_entities(query, conversation_history or [])
        trace.add_step(
            "Entity Extraction",
            {"query": query},
            asdict(entities),
            f"Extracted {len(entities.courses)} courses, {len(entities.programs)} programs, {len(entities.policies)} policies"
        )
        
        # Step 2: Context Analysis
        context_signals = self._analyze_context(query, conversation_history or [], student_profile or {})
        trace.add_step(
            "Context Analysis",
            {"conversation_history": len(conversation_history or []), "has_profile": bool(student_profile)},
            context_signals,
            "Analyzed conversation history and student context"
        )
        
        # Step 3: Intent Classification
        intent_result = self._classify_with_llm(query, entities, context_signals)
        trace.add_step(
            "Intent Classification",
            {"query": query, "entities": asdict(entities), "context": context_signals},
            intent_result,
            f"Classified as {intent_result['intent_type']} with confidence {intent_result['confidence']}"
        )
        
        # Step 4: Ambiguity Detection
        ambiguities = self._detect_ambiguities(query, entities, intent_result)
        trace.add_step(
            "Ambiguity Detection",
            {"intent": intent_result['intent_type']},
            {"ambiguities": ambiguities},
            f"Found {len(ambiguities)} ambiguities"
        )
        
        # Step 5: Clarification Questions
        clarification_questions = []
        needs_clarification = False
        if intent_result['confidence'] < 0.7 or ambiguities:
            clarification_questions = self._generate_clarification_questions(query, entities, ambiguities)
            needs_clarification = True
            trace.add_step(
                "Clarification Generation",
                {"confidence": intent_result['confidence'], "ambiguities": ambiguities},
                {"questions": clarification_questions},
                "Generated clarification questions due to low confidence or ambiguities"
            )
        
        # Build Intent object
        intent = Intent(
            intent_type=IntentType(intent_result['intent_type']),
            sub_intents=intent_result.get('sub_intents', []),
            required_agents=intent_result['required_agents'],
            confidence=intent_result['confidence'],
            reasoning=intent_result['reasoning'],
            entities=entities,
            ambiguities=ambiguities,
            needs_clarification=needs_clarification,
            clarification_questions=clarification_questions
        )
        
        return intent, trace
    
    def _extract_entities(self, query: str, conversation_history: List[Dict]) -> ExtractedEntities:
        """
        Extract entities from query and conversation history.
        """
        # Extract course codes (e.g., 15-213, 67-364)
        course_pattern = r'\b\d{2}-\d{3}\b'
        courses = re.findall(course_pattern, query)
        
        # Check conversation history for course references
        for msg in conversation_history[-3:]:  # Last 3 messages
            if msg.get('role') == 'assistant':
                courses.extend(re.findall(course_pattern, msg.get('content', '')))
        
        # Remove duplicates while preserving order
        courses = list(dict.fromkeys(courses))
        
        # Extract programs (simple keyword matching for now)
        program_keywords = {
            'CS major': ['CS major', 'Computer Science major', 'computer science degree'],
            'IS major': ['IS major', 'Information Systems major'],
            'Business major': ['Business major', 'business degree'],
            'CS minor': ['CS minor', 'Computer Science minor'],
            'Business minor': ['Business minor', 'business minor'],
        }
        
        programs = []
        query_lower = query.lower()
        for program, keywords in program_keywords.items():
            if any(keyword.lower() in query_lower for keyword in keywords):
                programs.append(program)
        
        # Extract policies
        policy_keywords = {
            'overload': ['overload', 'more than 18 units', 'exceed unit limit'],
            'prerequisites': ['prerequisite', 'prereq', 'pre-req', 'pre-reqs', 'prereqs'],
            'corequisites': ['corequisite', 'co-req', 'coreq'],
            'drop/add': ['drop', 'add', 'withdraw'],
            'GPA': ['GPA', 'grade point average', 'grades'],
        }
        
        policies = []
        for policy, keywords in policy_keywords.items():
            if any(keyword.lower() in query_lower for keyword in keywords):
                policies.append(policy)
        
        # Extract temporal references
        temporal_keywords = [
            'next semester', 'this semester', 'fall 2026', 'spring 2026',
            'next year', 'this year', 'summer', 'fall', 'spring'
        ]
        temporal = [kw for kw in temporal_keywords if kw.lower() in query_lower]
        
        # Extract people references
        people_keywords = ['advisor', 'professor', 'instructor', 'dean', 'registrar']
        people = [kw for kw in people_keywords if kw.lower() in query_lower]
        
        return ExtractedEntities(
            courses=courses,
            programs=programs,
            policies=policies,
            temporal=temporal,
            people=people
        )
    
    def _analyze_context(self, query: str, conversation_history: List[Dict], 
                        student_profile: Dict) -> Dict[str, Any]:
        """
        Analyze conversation context for better routing.
        """
        signals = {
            "has_prior_context": len(conversation_history) > 0,
            "conversation_length": len(conversation_history),
            "has_student_profile": bool(student_profile),
            "references_previous": False,
            "is_follow_up": False,
        }
        
        # Check for references to previous conversation
        reference_words = ['this course', 'that course', 'it', 'they', 'the course', 'as mentioned']
        if any(word in query.lower() for word in reference_words):
            signals["references_previous"] = True
        
        # Check if this is a follow-up question
        if conversation_history and len(conversation_history) > 0:
            last_msg = conversation_history[-1]
            if last_msg.get('role') == 'assistant':
                # If assistant just answered, this is likely a follow-up
                signals["is_follow_up"] = True
        
        return signals
    
    def _classify_with_llm(self, query: str, entities: ExtractedEntities, 
                          context_signals: Dict) -> Dict[str, Any]:
        """
        Use LLM to classify intent with extracted entities and context.
        """
        prompt = f"""Classify this academic advising query with high precision.

Query: "{query}"

Extracted Entities:
- Courses mentioned: {', '.join(entities.courses) if entities.courses else 'None'}
- Programs mentioned: {', '.join(entities.programs) if entities.programs else 'None'}
- Policies mentioned: {', '.join(entities.policies) if entities.policies else 'None'}
- Temporal references: {', '.join(entities.temporal) if entities.temporal else 'None'}

Context Signals:
- Has prior conversation: {context_signals['has_prior_context']}
- References previous context: {context_signals['references_previous']}
- Is follow-up question: {context_signals['is_follow_up']}

Available Agents:
- programs_requirements: Major/minor requirements, degree progress, program-level planning
- course_scheduling: Course information (prerequisites, assessment, content, offerings, schedules)
- policy_compliance: University policies, compliance checking, registration rules

Intent Types:
- course_info: Questions about specific course details
- check_requirements: Questions about program/major/minor requirements
- plan_semester: Planning courses for a semester
- add_minor: Adding a minor
- policy_question: Questions about policies
- validate_plan: Checking if a plan is valid
- general: General advising questions

ROUTING RULES:
1. If query mentions specific course codes AND asks about that course → course_info + course_scheduling
2. If query asks about major/minor requirements → check_requirements + programs_requirements
3. If query asks about policies/rules → policy_question + policy_compliance
4. If query plans a semester with multiple courses → plan_semester + all agents

Respond in JSON:
{{
    "intent_type": "course_info|check_requirements|plan_semester|add_minor|policy_question|validate_plan|general",
    "sub_intents": ["specific sub-tasks"],
    "required_agents": ["agent1", "agent2"],
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation of why this classification and these agents",
    "key_signals": ["signal1", "signal2"]
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        try:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure confidence is float
                result['confidence'] = float(result.get('confidence', 0.5))
                return result
        except Exception as e:
            print(f"Warning: Failed to parse LLM response: {e}")
        
        # Fallback
        return {
            "intent_type": "general",
            "sub_intents": [],
            "required_agents": ["programs_requirements"],
            "confidence": 0.3,
            "reasoning": "Fallback due to parsing error",
            "key_signals": []
        }
    
    def _detect_ambiguities(self, query: str, entities: ExtractedEntities, 
                           intent_result: Dict) -> List[str]:
        """
        Detect ambiguities that might need clarification.
        """
        ambiguities = []
        
        # Ambiguity 1: Course mentioned but no specific question
        if entities.courses and not any(word in query.lower() for word in 
                                       ['prerequisite', 'assessment', 'when', 'what', 'how', 'who']):
            ambiguities.append(f"What specifically do you want to know about {', '.join(entities.courses)}?")
        
        # Ambiguity 2: Temporal reference without clear action
        if entities.temporal and not any(word in query.lower() for word in 
                                        ['take', 'plan', 'schedule', 'enroll']):
            ambiguities.append(f"What do you want to do in {entities.temporal[0]}?")
        
        # Ambiguity 3: Multiple programs mentioned
        if len(entities.programs) > 1:
            ambiguities.append(f"Are you asking about {entities.programs[0]} or {entities.programs[1]}?")
        
        # Ambiguity 4: Vague pronouns without context
        if any(word in query.lower() for word in ['it', 'this', 'that', 'they']) and not entities.courses:
            ambiguities.append("Which course or program are you referring to?")
        
        return ambiguities
    
    def _generate_clarification_questions(self, query: str, entities: ExtractedEntities,
                                         ambiguities: List[str]) -> List[str]:
        """
        Generate clarification questions for low-confidence or ambiguous queries.
        """
        questions = []
        
        # Use detected ambiguities
        questions.extend(ambiguities)
        
        # Additional clarification based on entities
        if not entities.courses and not entities.programs:
            questions.append("Which course or program are you asking about?")
        
        if entities.temporal and not entities.courses:
            questions.append(f"Which courses are you considering for {entities.temporal[0]}?")
        
        # Limit to 3 most important questions
        return questions[:3]


# Example usage
if __name__ == "__main__":
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.3)
    classifier = EnhancedIntentClassifier(llm)
    
    # Test query
    query = "What are the prerequisites for 15-213?"
    intent, trace = classifier.classify(query)
    
    print("=" * 80)
    print("INTENT CLASSIFICATION RESULT")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print(f"\nIntent Type: {intent.intent_type.value}")
    print(f"Confidence: {intent.confidence:.2f}")
    print(f"Required Agents: {', '.join(intent.required_agents)}")
    print(f"\nEntities:")
    print(f"  Courses: {intent.entities.courses}")
    print(f"  Programs: {intent.entities.programs}")
    print(f"  Policies: {intent.entities.policies}")
    print(f"\nReasoning: {intent.reasoning}")
    
    if intent.needs_clarification:
        print(f"\n⚠️  Needs Clarification:")
        for q in intent.clarification_questions:
            print(f"  - {q}")
    
    print("\n" + "=" * 80)
    print("REASONING TRACE")
    print("=" * 80)
    print(trace.explain())
