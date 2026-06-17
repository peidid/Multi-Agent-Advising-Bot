# How Agents Communicate
## Blackboard Pattern: Indirect Communication Through Shared State

---

## 🎯 **Core Principle: No Direct Communication**

**Key Fact**: Agents **NEVER** talk to each other directly. They only communicate through the **Blackboard** (shared state).

```
Agent A ──X── Agent B  ❌ NO DIRECT COMMUNICATION

Agent A ──┐
          │
          ▼
    Blackboard  ✅ SHARED STATE
          │
          ▼
Agent B ──┘
```

---

## 📋 **The Blackboard: Shared State**

**File**: `blackboard/schema.py` → `BlackboardState`

The Blackboard is a **TypedDict** that contains all shared information:

```python
class BlackboardState(TypedDict):
    # User Information
    user_query: str
    user_goal: Optional[str]
    student_profile: Optional[Dict[str, Any]]
    
    # Agent Outputs (THE KEY COMMUNICATION MECHANISM)
    agent_outputs: Dict[str, AgentOutput]
    # Format: {
    #   "programs_requirements": AgentOutput(...),
    #   "course_scheduling": AgentOutput(...),
    #   "policy_compliance": AgentOutput(...)
    # }
    
    # Aggregated Information
    constraints: List[Constraint]
    risks: List[Risk]
    plan_options: List[PlanOption]
    conflicts: List[Conflict]
    
    # Workflow Control
    active_agents: List[str]
    workflow_step: WorkflowStep
    next_agent: Optional[str]
```

---

## 🔄 **How Communication Works: Step-by-Step**

### **Example: Programs Agent → Policy Agent**

**Scenario**: Programs Agent proposes a plan, Policy Agent critiques it.

#### **Step 1: Programs Agent Executes**

**File**: `multi_agent.py` → `programs_node()`

```python
def programs_node(state: BlackboardState) -> Dict[str, Any]:
    # Programs Agent reads from Blackboard
    output = programs_agent.execute(state)  # ← Reads state
    
    # Programs Agent writes to Blackboard
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["programs_requirements"] = output  # ← Writes output
    
    return {
        "agent_outputs": agent_outputs,  # ← Updates Blackboard
        "plan_options": plan_options,
        "risks": state.get("risks", []) + output.risks
    }
```

**What Programs Agent does** (`agents/programs_agent.py`):

```python
def execute(self, state: BlackboardState) -> AgentOutput:
    # READ from Blackboard
    user_query = state.get("user_query", "")  # ← Reads user query
    student_profile = state.get("student_profile", {})  # ← Reads profile
    constraints = state.get("constraints", [])  # ← Reads existing constraints
    
    # Process (uses RAG, LLM, etc.)
    # ... generates plan ...
    
    # WRITE to Blackboard (via return)
    return AgentOutput(
        agent_name="programs_requirements",
        answer="...",
        plan_options=[PlanOption(...)],  # ← Plan written here
        risks=[],
        constraints=[]
    )
```

**Blackboard State After Programs Agent**:
```python
{
    "agent_outputs": {
        "programs_requirements": AgentOutput(
            plan_options=[PlanOption(
                semesters=[...],
                courses=["15-150", "15-210", ...],
                justification="4-year plan..."
            )]
        )
    },
    "plan_options": [PlanOption(...)]  # ← Copied to top level
}
```

#### **Step 2: Policy Agent Reads Programs Agent's Output**

**File**: `agents/policy_agent.py` → `execute()`

```python
def execute(self, state: BlackboardState) -> AgentOutput:
    # READ from Blackboard
    user_query = state.get("user_query", "")
    agent_outputs = state.get("agent_outputs", {})  # ← Reads ALL agent outputs
    
    # READ Programs Agent's output specifically
    programs_output = agent_outputs.get("programs_requirements")  # ← Reads Programs Agent!
    
    # Check if Programs Agent proposed a plan
    has_plan = programs_output and programs_output.plan_options
    
    if has_plan:
        # CRITIQUE the plan from Programs Agent
        return self._critique_plan(
            programs_output.plan_options[0],  # ← Uses Programs Agent's plan
            student_profile
        )
```

**Key Point**: Policy Agent reads `state["agent_outputs"]["programs_requirements"]` to see what Programs Agent wrote!

#### **Step 3: Policy Agent Writes Critique**

```python
def _critique_plan(self, plan_option, student_profile: dict) -> AgentOutput:
    # Analyzes the plan from Programs Agent
    # Checks for violations
    # Returns critique
    
    return AgentOutput(
        agent_name="policy_compliance",
        answer="Critique: Semester 3 has 60 units, exceeds 54-unit limit",
        constraints=[
            Constraint(
                source="policy",
                description="Semester 3 exceeds unit limit",
                hard=True
            )
        ],
        risks=[...]
    )
```

**Blackboard State After Policy Agent**:
```python
{
    "agent_outputs": {
        "programs_requirements": AgentOutput(...),  # ← Still there!
        "policy_compliance": AgentOutput(           # ← Policy Agent's critique
            constraints=[Constraint(...)]
        )
    },
    "constraints": [Constraint(...)]  # ← Aggregated constraints
}
```

#### **Step 4: Coordinator Reads Both Outputs**

**File**: `coordinator/coordinator.py` → `detect_conflicts()`

```python
def detect_conflicts(self, state: BlackboardState) -> List[Conflict]:
    # READ from Blackboard
    agent_outputs = state.get("agent_outputs", {})  # ← Reads ALL outputs
    
    # READ Policy Agent's output
    policy_output = agent_outputs.get("policy_compliance")
    
    # READ Programs Agent's output
    programs_output = agent_outputs.get("programs_requirements")
    
    # Compare them to detect conflicts
    if policy_output:
        hard_constraints = [c for c in policy_output.constraints if c.hard]
        # ... detects conflicts ...
```

---

## 📊 **Communication Patterns**

### **Pattern 1: Sequential Reading**

**Agent B reads Agent A's output:**

```python
# In Agent B's execute() method:
def execute(self, state: BlackboardState) -> AgentOutput:
    # Read other agent's output
    agent_outputs = state.get("agent_outputs", {})
    other_agent_output = agent_outputs.get("other_agent_name")
    
    if other_agent_output:
        # Use other agent's information
        plan = other_agent_output.plan_options[0]
        # Process based on other agent's output
```

**Example**: 
- **Policy Agent** reads `agent_outputs["programs_requirements"]` to critique plans
- **Courses Agent** reads `agent_outputs["programs_requirements"]` to check course availability in plans
- **Planning Agent** reads `agent_outputs["programs_requirements"]` to get requirements

### **Pattern 2: Aggregated Reading**

**Agent reads aggregated information:**

```python
# Read aggregated constraints/risks
constraints = state.get("constraints", [])  # ← All agents' constraints combined
risks = state.get("risks", [])  # ← All agents' risks combined
plan_options = state.get("plan_options", [])  # ← All plans from all agents
```

**Example**:
- Any agent can read `state["constraints"]` to see all constraints from all agents
- Any agent can read `state["risks"]` to see all risks identified

### **Pattern 3: Coordinator-Mediated**

**Coordinator reads all outputs and manages flow:**

```python
# Coordinator reads everything
agent_outputs = state.get("agent_outputs", {})
programs_output = agent_outputs.get("programs_requirements")
courses_output = agent_outputs.get("course_scheduling")
policy_output = agent_outputs.get("policy_compliance")

# Coordinator decides what to do next
if conflicts:
    return {"workflow_step": WorkflowStep.NEGOTIATION}
else:
    return {"workflow_step": WorkflowStep.SYNTHESIS}
```

---

## 🔍 **Real Examples from Code**

### **Example 1: Courses Agent Reading Programs Agent**

**File**: `agents/courses_agent.py` (line 88-92)

```python
def _extract_courses(self, plan_options: list, query: str, agent_outputs: dict, ...):
    # ...
    
    # From Programs agent output
    programs_output = agent_outputs.get("programs_requirements")  # ← READS Programs Agent
    if programs_output and programs_output.plan_options:
        for plan_option in programs_output.plan_options:
            courses.update(plan_option.courses)  # ← Uses Programs Agent's courses
```

**Communication Flow**:
```
Programs Agent → Writes plan_options to Blackboard
     ↓
Courses Agent → Reads agent_outputs["programs_requirements"]
     ↓
Courses Agent → Extracts courses from Programs Agent's plan
     ↓
Courses Agent → Checks course availability
```

### **Example 2: Policy Agent Reading Programs Agent**

**File**: `agents/policy_agent.py` (line 35-43)

```python
def execute(self, state: BlackboardState) -> AgentOutput:
    # ...
    agent_outputs = state.get("agent_outputs", {})  # ← READS Blackboard
    
    # Check if Programs agent has proposed a plan
    programs_output = agent_outputs.get("programs_requirements")  # ← READS Programs Agent
    
    has_plan = programs_output and programs_output.plan_options
    
    if has_plan:
        return self._critique_plan(
            programs_output.plan_options[0],  # ← USES Programs Agent's plan
            student_profile
        )
```

**Communication Flow**:
```
Programs Agent → Writes plan_options to Blackboard
     ↓
Policy Agent → Reads agent_outputs["programs_requirements"]
     ↓
Policy Agent → Critiques Programs Agent's plan
     ↓
Policy Agent → Writes critique to Blackboard
```

### **Example 3: Planning Agent Reading Multiple Agents**

**File**: `agents/planning_agent.py` (line 38-39)

```python
def execute(self, state: BlackboardState) -> AgentOutput:
    # ...
    agent_outputs = state.get("agent_outputs", {})  # ← READS Blackboard
    
    # Get relevant data from other agents
    program_requirements = self._get_program_requirements(planning_params, agent_outputs)
    # ↑ Reads from Programs Agent
    
    course_schedules = self._get_course_schedules(planning_params)
    # ↑ Could read from Courses Agent
```

**Communication Flow**:
```
Programs Agent → Writes requirements
     ↓
Courses Agent → Writes schedule info
     ↓
Planning Agent → Reads BOTH agents' outputs
     ↓
Planning Agent → Creates plan using both sources
```

---

## 🚫 **What Agents CANNOT Do**

### **❌ Direct Function Calls**

```python
# Agents CANNOT do this:
programs_agent.propose_plan()
policy_agent.critique(programs_agent.plan)  # ❌ NO!
```

### **❌ Direct Object Access**

```python
# Agents CANNOT do this:
other_agent = get_agent("programs_requirements")
plan = other_agent.current_plan  # ❌ NO!
```

### **❌ Direct Message Passing**

```python
# Agents CANNOT do this:
send_message("policy_agent", "Here's my plan")  # ❌ NO!
```

---

## ✅ **What Agents CAN Do**

### **✅ Read from Blackboard**

```python
# Any agent can read:
state.get("agent_outputs", {})  # ← All agent outputs
state.get("constraints", [])    # ← All constraints
state.get("risks", [])          # ← All risks
state.get("plan_options", [])   # ← All plans
```

### **✅ Write to Blackboard**

```python
# Agents write via return dictionary:
return {
    "agent_outputs": {
        "my_agent_name": AgentOutput(...)
    },
    "risks": [...],
    "constraints": [...]
}
```

### **✅ Read Other Agents' Outputs**

```python
# Agent B can read Agent A's output:
agent_outputs = state.get("agent_outputs", {})
agent_a_output = agent_outputs.get("agent_a_name")
if agent_a_output:
    # Use agent_a_output.answer, agent_a_output.plan_options, etc.
```

---

## 🔄 **Complete Communication Flow Example**

### **Scenario: "Can I graduate in 3.5 years?"**

```
1. User Query → Blackboard
   state["user_query"] = "Can I graduate in 3.5 years?"

2. Coordinator → Reads query → Decides agents needed
   state["active_agents"] = ["programs_requirements", "academic_planning", "policy_compliance"]

3. Programs Agent → Executes
   - Reads: state["user_query"], state["student_profile"]
   - Writes: state["agent_outputs"]["programs_requirements"] = AgentOutput(plan_options=[...])
   - Blackboard now has Programs Agent's plan

4. Planning Agent → Executes
   - Reads: state["agent_outputs"]["programs_requirements"]  ← Reads Programs Agent!
   - Reads: state["user_query"]
   - Uses Programs Agent's requirements to create plan
   - Writes: state["agent_outputs"]["academic_planning"] = AgentOutput(plan_options=[...])
   - Blackboard now has Planning Agent's plan

5. Policy Agent → Executes
   - Reads: state["agent_outputs"]["academic_planning"]  ← Reads Planning Agent!
   - Reads: state["plan_options"]  ← Could also read aggregated plans
   - Critiques Planning Agent's plan
   - Writes: state["agent_outputs"]["policy_compliance"] = AgentOutput(constraints=[...])
   - Blackboard now has Policy Agent's critique

6. Coordinator → Reads ALL outputs
   - Reads: state["agent_outputs"]  ← Reads everything!
   - Detects conflicts between Planning Agent's plan and Policy Agent's critique
   - If conflicts → Triggers negotiation
   - If no conflicts → Synthesizes answer

7. Coordinator → Synthesizes
   - Reads: state["agent_outputs"]["programs_requirements"]
   - Reads: state["agent_outputs"]["academic_planning"]
   - Reads: state["agent_outputs"]["policy_compliance"]
   - Combines all into final answer
```

---

## 📝 **Key Data Structures**

### **AgentOutput** (What agents write)

```python
class AgentOutput(BaseModel):
    agent_name: str  # e.g., "programs_requirements"
    answer: str  # Text response
    confidence: float  # 0.0-1.0
    relevant_policies: List[str]  # Policy citations
    risks: List[Risk]  # Identified risks
    constraints: List[Constraint]  # Constraints found
    plan_options: Optional[List[PlanOption]]  # Proposed plans
```

**Where it's stored**: `state["agent_outputs"]["agent_name"]`

### **How Agents Access Other Agents**

```python
# In any agent's execute() method:
agent_outputs = state.get("agent_outputs", {})

# Read specific agent:
programs_output = agent_outputs.get("programs_requirements")
if programs_output:
    plan = programs_output.plan_options[0]  # ← Use Programs Agent's plan
    answer = programs_output.answer  # ← Read Programs Agent's answer
```

---

## 🎯 **Communication Summary**

| Aspect | How It Works |
|--------|-------------|
| **Mechanism** | Blackboard Pattern (shared state) |
| **Read** | `state.get("agent_outputs", {})` |
| **Write** | Return dictionary that updates state |
| **Direct Communication** | ❌ None - all via Blackboard |
| **Visibility** | ✅ All agents can read all outputs |
| **Order** | Coordinator manages execution order |
| **Conflict Detection** | Coordinator reads all outputs and compares |

---

## 🔍 **Code Locations**

### **Where Agents Read**

- `agents/programs_agent.py` (line 32-35): Reads `user_query`, `student_profile`, `constraints`
- `agents/courses_agent.py` (line 27-30): Reads `user_query`, `plan_options`, `agent_outputs`
- `agents/policy_agent.py` (line 30-35): Reads `user_query`, `agent_outputs["programs_requirements"]`
- `agents/planning_agent.py` (line 28-30): Reads `user_query`, `student_profile`, `agent_outputs`

### **Where Agents Write**

- `multi_agent.py` → Each `*_node()` function:
  - `programs_node()` (line 80-96): Writes to `agent_outputs["programs_requirements"]`
  - `courses_node()` (line 98-108): Writes to `agent_outputs["course_scheduling"]`
  - `policy_node()` (line 110-121): Writes to `agent_outputs["policy_compliance"]`
  - `planning_node()` (line 123-135): Writes to `agent_outputs["academic_planning"]`

### **Where Coordinator Reads**

- `coordinator/coordinator.py`:
  - `detect_conflicts()` (line 209): Reads all `agent_outputs`
  - `synthesize_answer()` (line 250): Reads all `agent_outputs`
  - `manage_negotiation()` (line 313): Reads `agent_outputs` to manage negotiation

---

## ✅ **Key Takeaways**

1. **No Direct Communication**: Agents never call each other's methods
2. **Blackboard Only**: All communication through `BlackboardState`
3. **Read-Write Pattern**: Agents read from state, process, write back
4. **Coordinator Mediates**: Coordinator reads all outputs and manages flow
5. **Structured Data**: Communication uses structured `AgentOutput` objects
6. **Visibility**: All agents can see all other agents' outputs
7. **Sequential Execution**: Agents execute one at a time (managed by Coordinator)

---

## 🎓 **Why This Design?**

### **Benefits:**

✅ **Loose Coupling**: Agents don't depend on each other directly  
✅ **Scalability**: Easy to add new agents  
✅ **Debugging**: Can inspect Blackboard to see all communication  
✅ **Conflict Detection**: Coordinator can see all outputs at once  
✅ **Flexibility**: Agents can read any information they need  

### **Trade-offs:**

⚠️ **No Real-time Communication**: Agents execute sequentially  
⚠️ **No Direct Negotiation**: Must go through Coordinator  
⚠️ **State Management**: Need to manage state carefully  

---

**This is the Blackboard Pattern** - a classic multi-agent architecture where agents communicate indirectly through shared state! 🎯
