# MVP Implementation Guide

## Quick Start: Building Your First 3 Agents + Coordinator

This guide walks you through implementing the MVP step-by-step.

---

## Step 1: Set Up Project Structure

Create these folders and files:

```
Product/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── programs_agent.py
│   ├── courses_agent.py
│   └── policy_agent.py
│
├── coordinator/
│   ├── __init__.py
│   └── coordinator.py
│
├── blackboard/
│   ├── __init__.py
│   └── schema.py
│
└── multi_agent.py  # Main workflow file
```

---

## Step 2: Create Blackboard Schema

**File: `blackboard/schema.py`**

```python
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel

class Constraint(BaseModel):
    source: str  # "policy", "student", "finance"
    description: str
    hard: bool

class Risk(BaseModel):
    type: str
    severity: str  # "high", "medium", "low"
    description: str

class AgentOutput(BaseModel):
    agent_name: str
    answer: str
    confidence: float
    relevant_policies: List[str]
    risks: List[Risk]
    constraints: List[Constraint]

class BlackboardState(TypedDict):
    user_query: str
    student_profile: Optional[Dict[str, Any]]
    agent_outputs: Dict[str, AgentOutput]
    constraints: List[Constraint]
    risks: List[Risk]
    active_agents: List[str]
    workflow_step: str
    messages: List[Any]
```

---

## Step 3: Create Base Agent

**File: `agents/base_agent.py`**

```python
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from rag_engine_improved import get_retriever
from blackboard.schema import BlackboardState, AgentOutput

class BaseAgent(ABC):
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.retriever = get_retriever(domain=domain, k=5)
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def retrieve_context(self, query: str) -> str:
        """Retrieve domain-specific context."""
        results = self.retriever.invoke(query)
        return "\n".join([doc.page_content for doc in results])
    
    @abstractmethod
    def execute(self, state: BlackboardState) -> AgentOutput:
        """Each agent implements this."""
        pass
```

---

## Step 4: Implement Programs Agent

**File: `agents/programs_agent.py`**

```python
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint
from langchain_core.messages import SystemMessage

class ProgramsRequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="programs_requirements",
            domain="programs"
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        user_query = state.get("user_query", "")
        student_profile = state.get("student_profile", {})
        
        # Retrieve context
        context = self.retrieve_context(user_query)
        
        # Build prompt
        prompt = f"""You are the Programs & Requirements Agent for CMU-Q.

Student Profile: {student_profile}
Query: {user_query}

Retrieved Context:
{context}

Answer questions about major/minor requirements, check degree progress, and validate plans.
Be specific and cite relevant policies.

Format your response as:
ANSWER: [your answer]
CONFIDENCE: [0.0-1.0]
POLICIES: [list of policy citations]
RISKS: [any risks identified]
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        # Parse response (simplified - in production use structured output)
        return self._parse_response(response.content)
    
    def _parse_response(self, text: str) -> AgentOutput:
        # Simple parsing (improve with structured output later)
        lines = text.split("\n")
        answer = ""
        confidence = 0.8
        policies = []
        risks = []
        
        for line in lines:
            if line.startswith("ANSWER:"):
                answer = line.replace("ANSWER:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                except:
                    pass
            elif line.startswith("POLICIES:"):
                policies = [p.strip() for p in line.replace("POLICIES:", "").split(",")]
        
        return AgentOutput(
            agent_name=self.name,
            answer=answer or text,
            confidence=confidence,
            relevant_policies=policies,
            risks=risks,
            constraints=[]
        )
```

---

## Step 5: Implement Courses Agent

**File: `agents/courses_agent.py`**

```python
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk
from langchain_core.messages import SystemMessage
from course_tools import look_up_course_info, find_course_codes_in_text
import re

class CourseSchedulingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="course_scheduling",
            domain="courses"
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        user_query = state.get("user_query", "")
        
        # Extract course codes
        course_codes = find_course_codes_in_text(user_query)
        
        # Get course information
        course_info = []
        for code in course_codes:
            info = look_up_course_info(code)
            if info:
                course_info.append(f"Course {code}: {info}")
        
        # Retrieve context
        context = self.retrieve_context(user_query)
        
        prompt = f"""You are the Course & Scheduling Agent.

Query: {user_query}
Course Codes Found: {course_codes}
Course Information: {course_info}

Retrieved Context:
{context}

Provide information about course offerings, schedules, and any conflicts.
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
```

---

## Step 6: Implement Policy Agent

**File: `agents/policy_agent.py`**

```python
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint
from langchain_core.messages import SystemMessage

class PolicyComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="policy_compliance",
            domain="policies"
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        user_query = state.get("user_query", "")
        agent_outputs = state.get("agent_outputs", {})
        
        # Check if we need to critique a plan
        programs_output = agent_outputs.get("programs_requirements")
        
        context = self.retrieve_context(user_query)
        
        if programs_output:
            # Critique mode
            prompt = f"""You are the Policy & Compliance Agent.

Proposed Plan/Answer from Programs Agent:
{programs_output.answer}

Query: {user_query}

Retrieved Policies:
{context}

Critique the plan for compliance with:
- Overload limits
- Probation rules
- Course repeat policies
- Registration deadlines

Identify any policy violations or risks.
"""
        else:
            # Answer mode
            prompt = f"""You are the Policy & Compliance Agent.

Query: {user_query}

Retrieved Policies:
{context}

Answer questions about university policies, compliance, and regulations.
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
```

---

## Step 7: Create Coordinator

**File: `coordinator/coordinator.py`**

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from blackboard.schema import BlackboardState

class Coordinator:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """Classify user intent to determine which agents are needed."""
        prompt = f"""Classify this academic advising query and determine which agents are needed.

Query: {query}

Agents available:
- programs_requirements: For major/minor requirements, degree progress
- course_scheduling: For course offerings, schedules, conflicts
- policy_compliance: For university policies, compliance checking

Respond in JSON format:
{{
    "intent_type": "check_requirements" | "plan_semester" | "add_minor" | "policy_question",
    "required_agents": ["agent1", "agent2"],
    "priority": "high" | "medium" | "low"
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        # Parse JSON response (simplified)
        import json
        try:
            return json.loads(response.content)
        except:
            # Fallback
            return {
                "intent_type": "general",
                "required_agents": ["programs_requirements"],
                "priority": "medium"
            }
    
    def detect_conflicts(self, state: BlackboardState) -> List[Dict[str, Any]]:
        """Detect conflicts between agent outputs."""
        agent_outputs = state.get("agent_outputs", {})
        conflicts = []
        
        # Simple conflict detection
        # Check if policy agent flags violations
        policy_output = agent_outputs.get("policy_compliance")
        if policy_output and "violation" in policy_output.answer.lower():
            conflicts.append({
                "type": "policy_violation",
                "severity": "high",
                "description": "Policy agent identified violations"
            })
        
        return conflicts
    
    def synthesize_answer(self, state: BlackboardState) -> str:
        """Synthesize final answer from all agent outputs."""
        agent_outputs = state.get("agent_outputs", {})
        user_query = state.get("user_query", "")
        
        # Combine all agent outputs
        agent_summaries = []
        for agent_name, output in agent_outputs.items():
            agent_summaries.append(f"{agent_name}: {output.answer}")
        
        prompt = f"""You are the Coordinator synthesizing answers from multiple agents.

User Query: {user_query}

Agent Outputs:
{chr(10).join(agent_summaries)}

Synthesize a coherent, helpful answer that combines all relevant information.
Be clear and cite sources when appropriate.
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return response.content
```

---

## Step 8: Create Main Workflow

**File: `multi_agent.py`**

```python
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from blackboard.schema import BlackboardState
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from coordinator.coordinator import Coordinator
from langchain_core.messages import HumanMessage

# Initialize
coordinator = Coordinator()
programs_agent = ProgramsRequirementsAgent()
courses_agent = CourseSchedulingAgent()
policy_agent = PolicyComplianceAgent()

# Define nodes
def coordinator_node(state: BlackboardState):
    """Coordinator decides which agents to activate."""
    user_query = state.get("user_query", "")
    
    # Classify intent
    intent = coordinator.classify_intent(user_query)
    required_agents = intent.get("required_agents", ["programs_requirements"])
    
    return {
        "active_agents": required_agents,
        "workflow_step": "agent_execution",
        "next_agent": required_agents[0] if required_agents else None
    }

def programs_node(state: BlackboardState):
    """Programs agent execution."""
    output = programs_agent.execute(state)
    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "programs_requirements": output
        }
    }

def courses_node(state: BlackboardState):
    """Courses agent execution."""
    output = courses_agent.execute(state)
    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "course_scheduling": output
        }
    }

def policy_node(state: BlackboardState):
    """Policy agent execution."""
    output = policy_agent.execute(state)
    return {
        "agent_outputs": {
            **state.get("agent_outputs", {}),
            "policy_compliance": output
        }
    }

def synthesize_node(state: BlackboardState):
    """Synthesize final answer."""
    answer = coordinator.synthesize_answer(state)
    return {
        "messages": [HumanMessage(content=answer)],
        "workflow_step": "complete"
    }

# Routing functions
def route_after_coordinator(state):
    """Route to appropriate agent."""
    next_agent = state.get("next_agent")
    if next_agent == "programs_requirements":
        return "programs"
    elif next_agent == "course_scheduling":
        return "courses"
    elif next_agent == "policy_compliance":
        return "policy"
    else:
        return "synthesize"

def route_after_agent(state):
    """After agent, check if more agents needed."""
    active_agents = state.get("active_agents", [])
    executed_agents = list(state.get("agent_outputs", {}).keys())
    
    # Check if all agents have executed
    if len(executed_agents) >= len(active_agents):
        return "synthesize"
    else:
        # More agents needed - go back to coordinator
        return "coordinator"

# Build workflow
workflow = StateGraph(BlackboardState)

# Add nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("programs", programs_node)
workflow.add_node("courses", courses_node)
workflow.add_node("policy", policy_node)
workflow.add_node("synthesize", synthesize_node)

# Add edges
workflow.add_edge(START, "coordinator")
workflow.add_conditional_edges("coordinator", route_after_coordinator)
workflow.add_conditional_edges("programs", route_after_agent)
workflow.add_conditional_edges("courses", route_after_agent)
workflow.add_conditional_edges("policy", route_after_agent)
workflow.add_edge("synthesize", END)

app = workflow.compile()

# Usage
if __name__ == "__main__":
    result = app.invoke({
        "user_query": "Can I add a CS minor as an IS student?",
        "student_profile": {"major": "IS"},
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "active_agents": [],
        "workflow_step": "",
        "messages": [HumanMessage(content="Can I add a CS minor as an IS student?")]
    })
    
    print(result["messages"][-1].content)
```

---

## Step 9: Test Incrementally

1. **Test each agent individually:**
```python
# Test Programs Agent
state = {"user_query": "What are IS major requirements?", ...}
output = programs_agent.execute(state)
print(output.answer)
```

2. **Test Coordinator:**
```python
intent = coordinator.classify_intent("Can I add CS minor?")
print(intent)
```

3. **Test full workflow:**
```python
result = app.invoke({...})
```

---

## Step 10: Next Steps

1. **Improve parsing:** Use structured output for agent responses
2. **Add conflict detection:** Implement proper conflict detection logic
3. **Add negotiation:** Implement proposal + critique protocol
4. **Add user interaction:** Handle open_questions and user responses
5. **Optimize:** Improve prompts, add error handling, optimize performance

---

## Key Points

- **Start simple:** Get basic workflow working first
- **Test incrementally:** Test each component separately
- **Iterate:** Improve prompts and logic based on results
- **Extend gradually:** Add features one at a time

This MVP gives you a working multi-agent system that you can then refine and extend!

