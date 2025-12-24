# Dynamic Multi-Agent System Architecture

## Overview

This document outlines the architecture for a dynamic multi-agent academic advising system using LangGraph, implementing a hub-and-spoke topology with a Coordinator managing specialized agents through a structured Blackboard (shared state).

---

## System Architecture

```
                    ┌─────────────────┐
                    │   Coordinator   │
                    │   (Orchestrator)│
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Blackboard    │
                    │  (Shared State) │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Programs &  │    │   Course &   │    │   Policy &   │
│ Requirements │    │  Scheduling  │    │  Compliance  │
│    Agent     │    │    Agent     │    │    Agent     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────┴────────┐
                    │   Blackboard    │
                    │  (Updated)      │
                    └────────┬────────┘
                             │
                    ┌────────┴────────┐
                    │   Coordinator   │
                    │  (Synthesizes)  │
                    └─────────────────┘
```

**Key Principles:**
1. **Hub-and-Spoke**: Coordinator is the hub, agents are spokes
2. **No Direct Communication**: Agents communicate only via Blackboard
3. **Dynamic Routing**: Coordinator decides which agents to activate
4. **Structured State**: Blackboard uses typed schema, not free text
5. **Negotiation Protocol**: Proposal + Critique mechanism

---

## 1. Blackboard (Shared State) Schema

The Blackboard is a **structured data structure** (not free text) that agents read/write to.

```python
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

class ConflictType(str, Enum):
    HARD_VIOLATION = "hard_violation"  # Plan breaks policy (impossible)
    HIGH_RISK = "high_risk"           # Plan possible but risky
    TRADE_OFF = "trade_off"           # Multiple valid options

class Constraint(BaseModel):
    source: str  # "policy", "student", "finance"
    description: str
    hard: bool  # Hard vs soft constraint
    policy_citation: Optional[str] = None

class Risk(BaseModel):
    type: str  # "overload_risk", "time_conflict", "gpa_below_threshold"
    severity: str  # "high", "medium", "low"
    description: str
    policy_citation: Optional[str] = None

class PlanOption(BaseModel):
    semesters: List[Dict[str, Any]]  # Semester-by-semester plan
    courses: List[str]  # List of course codes
    risks: List[Risk]
    policy_citations: List[str]
    confidence: float  # 0.0 to 1.0
    justification: str

class AgentOutput(BaseModel):
    agent_name: str
    answer: str
    confidence: float
    relevant_policies: List[str]
    risks: List[Risk]
    constraints: List[Constraint]
    plan_options: Optional[List[PlanOption]] = None

class BlackboardState(TypedDict):
    # Student Information
    student_profile: Optional[Dict[str, Any]]  # major, minor, GPA, completed_courses, flags
    
    # User Intent
    user_goal: Optional[str]  # "add CS minor", "plan next semester", etc.
    user_query: str
    
    # Agent Outputs (structured)
    agent_outputs: Dict[str, AgentOutput]  # Key: agent_name, Value: AgentOutput
    
    # Constraints & Risks
    constraints: List[Constraint]
    risks: List[Risk]
    
    # Plans & Options
    plan_options: List[PlanOption]
    
    # Conflict Resolution
    conflicts: List[Dict[str, Any]]  # Conflict type, affected agents, options
    open_questions: List[str]  # Questions for user
    
    # Conversation History
    messages: List[Any]  # LangChain messages
    
    # Coordinator State
    active_agents: List[str]  # Which agents are currently active
    workflow_step: str  # Current step in workflow
    iteration_count: int  # For negotiation loops (max 3)
```

---

## 2. Coordinator Architecture

The Coordinator is the **orchestrator** that:
- Classifies user intent
- Plans workflow dynamically
- Routes to appropriate agents
- Detects conflicts
- Manages negotiation
- Synthesizes final answer

### Coordinator Responsibilities

```python
class Coordinator:
    """
    Main orchestrator for multi-agent system.
    
    Responsibilities:
    1. Intent Classification: Understand what user wants
    2. Workflow Planning: Decide which agents to activate
    3. Access Control: Control which agents can read/write what
    4. Conflict Detection: Identify conflicts between agent outputs
    5. Negotiation Management: Orchestrate proposal + critique protocol
    6. Synthesis: Generate final answer from agent outputs
    """
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent to determine which agents are needed.
        
        Returns:
            {
                "intent_type": "plan_semester" | "check_requirements" | "add_minor" | ...
                "required_agents": ["programs", "courses", "policy"],
                "priority": "high" | "medium" | "low"
            }
        """
        pass
    
    def plan_workflow(self, intent: Dict[str, Any]) -> List[str]:
        """
        Plan the workflow: which agents to call in what order.
        
        Returns:
            List of agent names in execution order
            Example: ["programs", "courses", "policy"]
        """
        pass
    
    def detect_conflicts(self, state: BlackboardState) -> List[Dict[str, Any]]:
        """
        Detect conflicts between agent outputs.
        
        Conflict Types:
        - HARD_VIOLATION: Plan breaks policy
        - HIGH_RISK: Plan possible but risky
        - TRADE_OFF: Multiple valid options
        
        Returns:
            List of conflict objects
        """
        pass
    
    def synthesize_answer(self, state: BlackboardState) -> str:
        """
        Synthesize final answer from all agent outputs.
        
        Handles:
        - Combining agent outputs
        - Resolving conflicts
        - Generating user-friendly response
        """
        pass
```

### Coordinator Node Implementation

```python
def coordinator_node(state: BlackboardState) -> Dict[str, Any]:
    """
    Coordinator node in LangGraph workflow.
    
    Flow:
    1. Classify intent
    2. Plan workflow
    3. Update state with active agents
    4. Route to next agent or synthesize
    """
    user_query = state.get("user_query", "")
    
    # 1. Classify intent
    intent = classify_intent(user_query)
    
    # 2. Plan workflow
    workflow = plan_workflow(intent)
    
    # 3. Check if we need to synthesize or continue
    if state.get("workflow_step") == "synthesize":
        # All agents have run, synthesize answer
        answer = synthesize_answer(state)
        return {
            "messages": [HumanMessage(content=answer)],
            "workflow_step": "complete"
        }
    
    # 4. Update state for next agent
    return {
        "active_agents": workflow,
        "workflow_step": "agent_execution",
        "next_agent": workflow[0] if workflow else None
    }
```

---

## 3. Agent Architecture

Each agent follows a **standard structure**:

### Agent Base Class

```python
from abc import ABC, abstractmethod
from rag_engine_improved import get_retriever

class BaseAgent(ABC):
    """
    Base class for all specialized agents.
    
    Each agent:
    - Has its own RAG retriever (domain-specific knowledge base)
    - Reads from Blackboard
    - Writes structured output to Blackboard
    - Never talks to other agents directly
    """
    
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.retriever = get_retriever(domain=domain, k=5)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    @abstractmethod
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Main execution method for agent.
        
        Steps:
        1. Read relevant fields from Blackboard
        2. Use RAG to retrieve domain-specific information
        3. Process with LLM
        4. Return structured AgentOutput
        """
        pass
    
    def retrieve_context(self, query: str) -> str:
        """Retrieve relevant context using domain-specific RAG."""
        results = self.retriever.invoke(query)
        return "\n".join([doc.page_content for doc in results])
```

### Programs & Requirements Agent

```python
class ProgramsRequirementsAgent(BaseAgent):
    """
    Agent responsible for:
    - Major/minor requirements
    - Degree progress checking
    - Course requirement validation
    - Program-specific policies
    """
    
    def __init__(self):
        super().__init__(
            name="programs_requirements",
            domain="programs"  # Uses programs domain RAG
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Programs & Requirements agent logic.
        """
        # 1. Read from Blackboard
        student_profile = state.get("student_profile", {})
        user_query = state.get("user_query", "")
        user_goal = state.get("user_goal", "")
        
        # 2. Retrieve relevant context
        context = self.retrieve_context(user_query)
        
        # 3. Build prompt
        prompt = f"""
        You are the Programs & Requirements Agent for CMU-Q.
        
        Student Profile: {student_profile}
        User Goal: {user_goal}
        Query: {user_query}
        
        Retrieved Context:
        {context}
        
        Your tasks:
        1. Answer questions about major/minor requirements
        2. Check if proposed plan satisfies requirements
        3. Validate degree progress
        4. Identify any requirement violations
        
        Return structured output with:
        - Answer to the question
        - Confidence level (0.0-1.0)
        - Relevant policies cited
        - Any risks or constraints identified
        - If applicable, proposed plan options
        """
        
        # 4. Call LLM
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        # 5. Parse response into structured format
        # (In practice, use structured output or JSON parsing)
        output = self._parse_response(response.content)
        
        return AgentOutput(
            agent_name=self.name,
            answer=output["answer"],
            confidence=output["confidence"],
            relevant_policies=output["policies"],
            risks=output["risks"],
            constraints=output["constraints"],
            plan_options=output.get("plan_options")
        )
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        # Implementation: Use JSON parsing or structured output
        pass
```

### Course & Scheduling Agent

```python
class CourseSchedulingAgent(BaseAgent):
    """
    Agent responsible for:
    - Course offerings (semester, instructor, times)
    - Schedule conflicts
    - Add/drop deadlines
    - Course availability
    """
    
    def __init__(self):
        super().__init__(
            name="course_scheduling",
            domain="courses"  # Uses courses domain RAG
        )
        # Also has access to course tools
        from course_tools import look_up_course_info
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Course & Scheduling agent logic.
        """
        # 1. Read from Blackboard
        plan_options = state.get("plan_options", [])
        user_query = state.get("user_query", "")
        
        # 2. Extract course codes from plan or query
        courses = self._extract_courses(plan_options, user_query)
        
        # 3. Check offerings and conflicts
        schedule_info = []
        conflicts = []
        
        for course_code in courses:
            # Use RAG for course descriptions
            context = self.retrieve_context(f"course {course_code}")
            
            # Use course tools for structured data
            course_data = look_up_course_info(course_code)
            
            # Check for conflicts (simplified)
            conflict = self._check_conflicts(course_code, courses)
            if conflict:
                conflicts.append(conflict)
            
            schedule_info.append({
                "course": course_code,
                "data": course_data,
                "context": context
            })
        
        # 4. Build response
        prompt = f"""
        You are the Course & Scheduling Agent.
        
        Courses to check: {courses}
        Schedule Information: {schedule_info}
        Conflicts Found: {conflicts}
        
        Provide:
        - Course offering details
        - Schedule conflicts
        - Availability information
        """
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=[Risk(type="time_conflict", severity="high", description=str(c)) for c in conflicts],
            constraints=[]
        )
```

### Policy & Compliance Agent

```python
class PolicyComplianceAgent(BaseAgent):
    """
    Agent responsible for:
    - University-level policies
    - Compliance checking
    - Overload limits
    - Probation rules
    - Financial policies
    """
    
    def __init__(self):
        super().__init__(
            name="policy_compliance",
            domain="policies"  # Uses policies domain RAG
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Policy & Compliance agent logic.
        
        This agent CRITIQUES plans proposed by other agents.
        """
        # 1. Read from Blackboard
        plan_options = state.get("plan_options", [])
        agent_outputs = state.get("agent_outputs", {})
        
        # 2. Get proposed plan from Programs agent
        programs_output = agent_outputs.get("programs_requirements")
        proposed_plan = programs_output.plan_options[0] if programs_output and programs_output.plan_options else None
        
        if not proposed_plan:
            # No plan to critique, just answer policy questions
            return self._answer_policy_question(state)
        
        # 3. Critique the plan
        context = self.retrieve_context("overload limits probation rules")
        
        prompt = f"""
        You are the Policy & Compliance Agent.
        
        Proposed Plan: {proposed_plan}
        
        Check compliance with:
        - Overload limits
        - Probation rules
        - Course repeat policies
        - Financial implications
        
        Retrieved Policies:
        {context}
        
        Provide:
        - Compliance check results
        - Policy violations (if any)
        - Suggested modifications
        - Policy citations
        """
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        # 4. Parse critique
        critique = self._parse_critique(response.content)
        
        return AgentOutput(
            agent_name=self.name,
            answer=critique["critique"],
            confidence=critique["confidence"],
            relevant_policies=critique["policies"],
            risks=critique["risks"],
            constraints=critique["constraints"]
        )
```

---

## 4. Negotiation Protocol: Proposal + Critique

Based on feedback, implement a concrete negotiation mechanism:

```python
def negotiation_protocol(state: BlackboardState) -> Dict[str, Any]:
    """
    Proposal + Critique Protocol:
    
    Step 1: Programs Agent proposes plan
    Step 2: Policy Agent critiques plan
    Step 3: Coordinator synthesizes revised plan
    Step 4: If conflicts remain, loop (max 3 iterations)
    """
    
    iteration = state.get("iteration_count", 0)
    max_iterations = 3
    
    if iteration >= max_iterations:
        # Max iterations reached, return current state
        return {"workflow_step": "synthesize"}
    
    agent_outputs = state.get("agent_outputs", {})
    
    # Step 1: Programs Agent proposes
    if "programs_requirements" not in agent_outputs:
        return {"next_agent": "programs_requirements"}
    
    # Step 2: Policy Agent critiques
    if "policy_compliance" not in agent_outputs:
        return {"next_agent": "policy_compliance"}
    
    # Step 3: Check for conflicts
    conflicts = detect_conflicts(state)
    
    if conflicts:
        # Step 4: Coordinator resolves or asks user
        if any(c["type"] == "hard_violation" for c in conflicts):
            # Hard violation - ask user or modify plan
            return {
                "conflicts": conflicts,
                "open_questions": ["This plan violates policy X. Would you like to modify it?"],
                "workflow_step": "user_input"
            }
        else:
            # Soft conflicts - try to resolve
            return {
                "iteration_count": iteration + 1,
                "workflow_step": "negotiation",
                "next_agent": "programs_requirements"  # Re-propose with constraints
            }
    
    # No conflicts - ready to synthesize
    return {"workflow_step": "synthesize"}
```

---

## 5. File Structure

```
Product/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          # BaseAgent class
│   ├── programs_agent.py      # Programs & Requirements Agent
│   ├── courses_agent.py       # Course & Scheduling Agent
│   └── policy_agent.py         # Policy & Compliance Agent
│
├── coordinator/
│   ├── __init__.py
│   ├── coordinator.py         # Coordinator class
│   └── intent_classifier.py    # Intent classification logic
│
├── blackboard/
│   ├── __init__.py
│   ├── schema.py              # BlackboardState schema
│   └── validators.py           # State validation
│
├── data/
│   ├── programs/               # Programs domain RAG data
│   ├── courses/                # Courses domain RAG data
│   └── policies/               # Policies domain RAG data
│
├── rag_engine_improved.py      # Domain-specific RAG
├── course_tools.py             # Course lookup tools
├── agent.py                    # Main LangGraph workflow
└── requirements.txt
```

---

## 6. LangGraph Workflow

```python
from langgraph.graph import StateGraph, START, END
from blackboard.schema import BlackboardState
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from coordinator.coordinator import Coordinator

# Initialize agents
programs_agent = ProgramsRequirementsAgent()
courses_agent = CourseSchedulingAgent()
policy_agent = PolicyComplianceAgent()
coordinator = Coordinator()

# Create workflow
workflow = StateGraph(BlackboardState)

# Add nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("programs", programs_agent.execute)
workflow.add_node("courses", courses_agent.execute)
workflow.add_node("policy", policy_agent.execute)
workflow.add_node("synthesize", synthesize_node)

# Dynamic routing
def route_after_coordinator(state):
    """Route to next agent based on coordinator decision."""
    next_agent = state.get("next_agent")
    if next_agent == "programs":
        return "programs"
    elif next_agent == "courses":
        return "courses"
    elif next_agent == "policy":
        return "policy"
    elif state.get("workflow_step") == "synthesize":
        return "synthesize"
    else:
        return END

def route_after_agent(state):
    """After agent executes, check if more agents needed or synthesize."""
    workflow_step = state.get("workflow_step")
    if workflow_step == "synthesize":
        return "synthesize"
    elif workflow_step == "negotiation":
        return "coordinator"  # Re-negotiate
    else:
        return "coordinator"  # Check next agent

# Add edges
workflow.add_edge(START, "coordinator")
workflow.add_conditional_edges("coordinator", route_after_coordinator)
workflow.add_conditional_edges("programs", route_after_agent)
workflow.add_conditional_edges("courses", route_after_agent)
workflow.add_conditional_edges("policy", route_after_agent)
workflow.add_edge("synthesize", END)

app = workflow.compile()
```

---

## 7. MVP Implementation Plan

### Phase 1: Foundation (Week 1-2)
1. ✅ Create Blackboard schema (`blackboard/schema.py`)
2. ✅ Create BaseAgent class (`agents/base_agent.py`)
3. ✅ Set up domain-specific RAG indexes
4. ✅ Create Coordinator skeleton (`coordinator/coordinator.py`)

### Phase 2: Implement Agents (Week 3-4)
1. ✅ Programs & Requirements Agent
   - Domain RAG: `data/programs/` or use existing `data/Academic & Studies/Academic Programs/`
   - Implement `execute()` method
   - Test with sample queries

2. ✅ Course & Scheduling Agent
   - Domain RAG: `data/courses/` (use existing course JSON files)
   - Integrate `course_tools.py`
   - Implement conflict detection

3. ✅ Policy & Compliance Agent
   - Domain RAG: `data/policies/` or use `data/Academic & Studies/Registration/`
   - Implement critique logic
   - Policy citation extraction

### Phase 3: Coordinator & Workflow (Week 5-6)
1. ✅ Intent classification
2. ✅ Workflow planning
3. ✅ Conflict detection
4. ✅ Negotiation protocol
5. ✅ Answer synthesis

### Phase 4: Integration & Testing (Week 7-8)
1. ✅ Integrate all components
2. ✅ Test end-to-end workflows
3. ✅ Debug and refine
4. ✅ Performance optimization

---

## 8. Key Implementation Details

### Domain-Specific RAG Setup

```python
# In rag_engine_improved.py, ensure domain paths are set:
DOMAIN_PATHS = {
    "programs": [
        "Academic & Studies/Academic Programs",
        "Academic & Studies/Academic Resource Center"
    ],
    "courses": [
        "Academic & Studies/Courses"
    ],
    "policies": [
        "Academic & Studies/Exams and grading policies",
        "Academic & Studies/Registration"
    ]
}
```

### Agent Output Parsing

Use structured output or JSON parsing:

```python
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=AgentOutput)

prompt = f"""
{instructions}

{parser.get_format_instructions()}
"""

response = llm.invoke([SystemMessage(content=prompt)])
output = parser.parse(response.content)
```

### State Management

```python
# Agents read/write specific fields
def programs_agent_node(state: BlackboardState):
    # Read
    student_profile = state.get("student_profile")
    user_query = state.get("user_query")
    
    # Execute
    output = programs_agent.execute(state)
    
    # Write (update specific fields)
    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "programs_requirements": output
        },
        "risks": state.get("risks", []) + output.risks,
        "constraints": state.get("constraints", []) + output.constraints
    }
```

---

## 9. Example Workflow

**User Query:** "I want to add a CS minor as an IS student. Can I do it in 4 years?"

### Step 1: Coordinator classifies intent
```python
intent = {
    "intent_type": "add_minor",
    "required_agents": ["programs", "courses", "policy"],
    "priority": "high"
}
```

### Step 2: Coordinator plans workflow
```python
workflow = ["programs", "courses", "policy"]
```

### Step 3: Programs Agent executes
- Reads: student_profile (IS major), user_goal (add CS minor)
- Retrieves: CS minor requirements, IS major requirements
- Outputs: Plan option with courses needed, confidence, risks

### Step 4: Courses Agent executes
- Reads: plan_options from Programs Agent
- Checks: Course offerings, schedule conflicts
- Outputs: Schedule information, conflicts

### Step 5: Policy Agent executes
- Reads: plan_options from Programs Agent
- Critiques: Overload limits, policy compliance
- Outputs: Compliance check, violations, suggestions

### Step 6: Coordinator detects conflicts
- Checks: All agent outputs for conflicts
- Identifies: High course load, potential overload

### Step 7: Negotiation (if conflicts)
- Programs Agent re-proposes with constraints
- Policy Agent critiques again
- Loop until resolved or max iterations

### Step 8: Coordinator synthesizes
- Combines all agent outputs
- Resolves conflicts
- Generates final answer

---

## 10. Next Steps

1. **Create file structure** as outlined above
2. **Implement Blackboard schema** with Pydantic models
3. **Create BaseAgent class** with standard interface
4. **Implement each agent** following the pattern
5. **Build Coordinator** with intent classification and workflow planning
6. **Create LangGraph workflow** with dynamic routing
7. **Test incrementally** - one agent at a time
8. **Integrate and refine**

This architecture provides a solid foundation for your MVP while being extensible for future agents and features.

