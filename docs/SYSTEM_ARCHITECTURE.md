# AdvisingBot System Architecture

A multi-agent academic advising system for CMU-Q students, powered by LangGraph and LLMs.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Agent System](#agent-system)
6. [Dynamic Workflow Planning & Coordination](#dynamic-workflow-planning--coordination)
7. [Visible Collaboration & Negotiation Protocol](#visible-collaboration--negotiation-protocol)
8. [Coordinator Mechanism](#coordinator-mechanism)
9. [RAG Engine](#rag-engine)
10. [Streaming & Real-time Updates](#streaming--real-time-updates)
11. [Planning Mode (Proposal + Critique Protocol)](#planning-mode-proposal--critique-protocol)
12. [Data Structures](#data-structures)
13. [Tech Stack](#tech-stack)

---

## System Overview

AdvisingBot is a **multi-agent system** that helps CMU-Q students with academic advising tasks:

- Course selection and scheduling
- Degree requirement tracking
- Academic planning (multi-semester)
- Policy compliance checking

**Key Design Principles:**

1. **Blackboard Architecture** - Agents communicate via shared state, not directly
2. **LLM-Driven Coordination** - No hard-coded routing rules; LLM reasons about workflow
3. **Parallel Execution** - Agents run concurrently for faster responses
4. **Domain-Specific RAG** - Each agent has its own knowledge base
5. **Iterative Refinement** - Coordinator evaluates outputs and requests re-runs if needed

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Chat UI    │  │ Agent Status│  │ Profile Mgmt│  │Planning View│        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                    │ HTTP/SSE
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND (FastAPI)                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  /api/chat/stream  │  /api/auth  │  /api/conversations  │ /api/planning │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│                                    ▼                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      MULTI-AGENT WORKFLOW (LangGraph)                 │   │
│  │                                                                       │   │
│  │   START → [Coordinator] → [Parallel Agents] → [Eval Loop] → [Synth]  │   │
│  │                │                  │                │                  │   │
│  │                ▼                  ▼                ▼                  │   │
│  │         ┌──────────┐      ┌──────────────┐  ┌──────────────┐         │   │
│  │         │  Intent  │      │   Programs   │  │  Coordinator │         │   │
│  │         │ Classify │      │   Courses    │  │  Evaluation  │         │   │
│  │         │ + Route  │      │   Policy     │  │  (GPT-5.2)   │         │   │
│  │         └──────────┘      │   Planning   │  └──────────────┘         │   │
│  │                           └──────────────┘                            │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   ChromaDB      │      │    MongoDB      │      │  OpenAI API     │
│  (Vector DBs)   │      │   (User Data)   │      │  (LLM Calls)    │
│                 │      │                 │      │                 │
│ - courses       │      │ - users         │      │ - gpt-4-turbo   │
│ - programs      │      │ - conversations │      │ - gpt-5.2       │
│ - policies      │      │ - messages      │      │                 │
│ - schedules     │      │ - plans         │      │                 │
│ - planning      │      │                 │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## Core Components

### 1. Frontend (`frontend/`)

- **Framework:** Next.js 14 with TypeScript
- **Styling:** Tailwind CSS
- **Key Components:**
  - `ChatMessage.tsx` - Renders chat bubbles with markdown
  - `AgentStatus.tsx` - Real-time agent activity display
  - `PlanningPanel.tsx` - Multi-round planning visualization
  - `ProfileModal.tsx` - Student profile management

### 2. Backend (`backend/server.py`)

- **Framework:** FastAPI with async support
- **Authentication:** JWT tokens
- **Database:** MongoDB Atlas
- **Key Endpoints:**
  - `POST /api/chat/stream` - SSE streaming chat
  - `POST /api/planning/start` - Start planning session
  - `GET /api/conversations` - List conversations

### 3. Multi-Agent Workflow (`multi_agent.py`)

- **Framework:** LangGraph (state machine)
- **Nodes:**
  - `coordinator_node` - Intent classification and routing
  - `parallel_agents_node` - Execute agents concurrently
  - `synthesize_node` - Combine outputs into final answer

### 4. Coordinator (`coordinator/coordinator.py`)

- **Philosophy:** "Let the LLM be the coordinator, not just a classifier"
- **Key Methods:**
  - `classify_intent()` - LLM-driven intent analysis
  - `plan_workflow()` - Determine which agents to call
  - `evaluate_outputs_for_sufficiency()` - Quality assessment
  - `synthesize_answer()` - Combine agent outputs

### 5. Domain Agents (`agents/`)

| Agent | File | Domain | Purpose |
|-------|------|--------|---------|
| Programs | `programs_agent.py` | `programs` | Degree requirements, majors, minors |
| Courses | `courses_agent.py` | `courses` | Course info, prerequisites, schedules |
| Policy | `policy_agent.py` | `policies` | University policies, compliance |
| Planning | `planning_agent.py` | `planning` | Multi-semester academic plans |

---

## Data Flow

### Chat Request Flow

```
1. User sends message via frontend
                ↓
2. FastAPI receives POST /api/chat/stream
                ↓
3. Coordinator classifies intent (via LLM or fine-tuned model)
   → Returns: required_agents, reasoning, agent_tasks
                ↓
4. Parallel Agents Node executes selected agents concurrently
   → Each agent: RAG retrieval → LLM processing → AgentOutput
                ↓
5. Coordinator Evaluation Loop (max 3 rounds)
   → GPT-5.2 evaluates quality score (0-100)
   → If score < 75: specify agents to re-run with enhanced k
   → Pass semantic feedback to agents for focused retrieval
                ↓
6. Synthesize Node combines all outputs
   → LLM generates user-friendly response
                ↓
7. Stream final answer via SSE to frontend
```

### Blackboard State (`BlackboardState`)

All agents read/write to shared state:

```python
class BlackboardState(TypedDict):
    # User context
    user_query: str
    student_profile: Dict[str, Any]
    conversation_history: List[Dict]

    # Agent outputs
    agent_outputs: Dict[str, AgentOutput]

    # Aggregated data
    risks: List[Risk]
    constraints: List[Constraint]
    plan_options: List[PlanOption]
    conflicts: List[Conflict]

    # Workflow control
    workflow_step: WorkflowStep
    active_agents: List[str]

    # Metadata
    execution_metadata: Dict
    phase_timing: Dict
```

---

## Agent System

### Base Agent (`agents/base_agent.py`)

All agents inherit from `BaseAgent`:

```python
class BaseAgent(ABC):
    def __init__(self, name: str, domain: str):
        self.name = name
        self.retriever = get_retriever(domain=domain, k=default_k)
        self.llm = ChatOpenAI(model=AGENT_MODEL)

    def retrieve_context(self, query: str) -> str:
        """RAG retrieval from domain-specific vector DB"""

    def get_memory_context(self, state: BlackboardState) -> str:
        """Format conversation history for prompt"""

    def get_coordinator_guidance(self) -> str:
        """Get feedback from coordinator for re-runs"""

    @abstractmethod
    def execute(self, state: BlackboardState) -> AgentOutput:
        """Main execution - each agent implements this"""
```

### Agent Output Structure

```python
class AgentOutput(BaseModel):
    agent_name: str
    answer: str                    # Natural language response
    confidence: float              # 0.0 - 1.0
    relevant_policies: List[str]   # Policy citations
    risks: List[Risk]              # Identified risks
    constraints: List[Constraint]  # Hard/soft constraints
    plan_options: List[PlanOption] # Optional: proposed plans
```

### Streaming Events

Each agent emits events for real-time UI:

```python
# In agent execution
self.emit_start()                    # Agent started
self.emit_retrieving(query, count)   # RAG retrieval
self.emit_thinking(message)          # LLM processing
self.emit_output(result)             # Full output ready
self.emit_complete(confidence)       # Done
```

---

## Dynamic Workflow Planning & Coordination

### Philosophy: LLM as Coordinator, Not Router


1. **Understands** the student's underlying goal
2. **Reasons** about which agents can help and why
3. **Plans** a dynamic workflow with decision points
4. **Adapts** based on intermediate results

### WorkflowPlan Structure

The coordinator generates a structured plan for each query:

```python
@dataclass
class WorkflowPlan:
    goal: str                    # "Help student understand CS minor requirements"
    reasoning: str               # "Need Programs for requirements, Courses for prereqs"
    agents: List[str]            # ["programs_requirements", "course_scheduling"]
    execution_order: List[str]   # Order of execution
    parallel_stages: List[List[str]]  # Which agents can run together
    decision_points: List[Dict]  # Where to check results and adapt
    expected_challenges: List[str]    # What might go wrong
    success_criteria: str        # How we know we succeeded
    agent_tasks: Dict[str, str]  # Specific task instruction per agent
```

### LLM-Driven Coordination Prompt

The coordinator receives a rich prompt with:

```
YOUR TASK AS COORDINATOR:

1. UNDERSTAND THE PROBLEM:
   - What is the student really asking for?
   - What is the underlying goal or concern?
   - What information do we need to provide a good answer?

2. ANALYZE WHICH AGENTS CAN HELP:
   - Which agents have the capabilities needed?
   - What are the limitations of each agent?
   - Do we need multiple agents? If so, why?

3. PLAN THE WORKFLOW:
   - In what order should agents be consulted?
   - Can any agents work in parallel?
   - Are there decision points where we need to check results?

4. DEFINE SUCCESS:
   - How will we know if we've answered the question well?
```

### Agent Capability Awareness

The coordinator knows each agent's strengths and limitations:

```python
"programs_requirements": AgentCapability(
    name="Programs Requirements Agent",
    role="Academic program specialist",
    capabilities=[
        "Validate if a course plan satisfies major/minor requirements",
        "Check degree progress toward graduation",
        "Explain what courses are needed for a specific program",
    ],
    limitations=[
        "Does NOT know specific course details (prerequisites, schedule)",
        "Does NOT know university-wide policies",
        "Cannot check time conflicts or course availability",
    ]
)
```

### Dynamic Agent Task Assignment

Each agent receives a **specific task** from the coordinator:

```python
# Coordinator assigns tasks based on query analysis
agent_tasks = {
    "programs_requirements": "Check if 15-213 is required for the CS minor",
    "course_scheduling": "Get schedule and prerequisites for 15-213 in Fall 2025",
    "policy_compliance": "Verify unit limit policies for adding a minor"
}
```

Agents receive this in their prompt:
```
--- COORDINATOR TASK ASSIGNMENT ---
Your specific task for this query: Check if 15-213 is required for the CS minor

Focus on accomplishing this task. Retrieve relevant information and provide a focused response.
--- END TASK ---
```

### Adaptive Workflow (Decision Points)

The coordinator can adapt mid-workflow:

```python
decision_points = [
    {
        "after_agent": "programs_requirements",
        "check": "Did we find all required courses?",
        "if_problem": "Add course_scheduling agent to get details"
    }
]
```

---

## Visible Collaboration & Negotiation Protocol

### Design Goal: Transparency

Users can **see** the multi-agent collaboration in real-time:

1. Which agents are active
2. What each agent is doing (retrieving, thinking)
3. Agent outputs and confidence scores
4. Coordinator evaluation and feedback
5. Re-run decisions and reasoning

### Real-Time Agent Status Display

The frontend shows live agent activity:

```
┌─────────────────────────────────────────────────┐
│  🧠 Coordinator: Analyzing your question...      │
├─────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐    │
│  │ 📚 Programs Agent        [Running ⏳]   │    │
│  │ → Checking degree requirements...       │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ 📖 Courses Agent         [Running ⏳]   │    │
│  │ → Retrieving course schedules...        │    │
│  └─────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────┐    │
│  │ 🛡️ Policy Agent          [Waiting]      │    │
│  └─────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Coordinator Evaluation Panel

Users see the quality assessment process:

```
┌─────────────────────────────────────────────────┐
│  🧠 Coordinator Evaluation (Round 1/3)          │
│                                                 │
│  Quality Score: ████████░░ 78/100               │
│  Decision: ✅ Sufficient                        │
│                                                 │
│  Agent Scores:                                  │
│  • Programs: 85/100 ✓                           │
│  • Courses: 72/100 (minor gaps)                 │
│  • Policy: 80/100 ✓                             │
│                                                 │
│  Reasoning: Good coverage of requirements,      │
│  course schedule details could be more specific │
└─────────────────────────────────────────────────┘
```

### Semantic Feedback Loop

When quality is insufficient, coordinator provides **semantic feedback**:

```python
agent_feedback = {
    "course_scheduling": {
        "score": 65,
        "strengths": ["Listed available courses"],
        "gaps": ["Missing prerequisite chain", "No Fall 2025 schedule"],
        "guidance": "Search for 15-213 prerequisites and Fall 2025 offerings"
    }
}
```

Agents receive this guidance and focus their re-retrieval:

```
--- COORDINATOR FEEDBACK (Focus on these areas) ---
Coordinator Guidance: Search for 15-213 prerequisites and Fall 2025 offerings
Information Gaps to Address: Missing prerequisite chain, No Fall 2025 schedule
Previous Response Score: 65/100
--- END FEEDBACK ---
```

### Visible Re-Run Process

When agents re-run, users see:

```
┌─────────────────────────────────────────────────┐
│  🔄 Re-running Courses Agent (Round 2)          │
│  → Enhanced retrieval (k=10)                    │
│  → Applying coordinator feedback                │
│  → Searching: "15-213 prerequisites Fall 2025"  │
└─────────────────────────────────────────────────┘
```

### Streaming Event Types for Visibility

```python
# Events that show collaboration process
EventType.COORDINATOR_THINKING      # "Analyzing your question..."
EventType.COORDINATOR_ROUTING       # "Routing to 3 agents: Programs, Courses, Policy"
EventType.COORDINATOR_EVALUATION    # Quality score, agent feedback
EventType.AGENT_RERUN_START         # "Re-running Courses with k=10"
EventType.AGENT_RERUN_COMPLETE      # "Re-run complete (2.3s)"
```

### Conflict Detection & Resolution

When agents disagree, conflicts are surfaced:

```python
class ConflictType(Enum):
    HARD_VIOLATION = "hard_violation"  # Plan breaks policy
    HIGH_RISK = "high_risk"            # Plan is risky
    TRADE_OFF = "trade_off"            # Multiple valid options

# Detected conflicts shown to user
conflicts = [
    Conflict(
        conflict_type=ConflictType.HIGH_RISK,
        affected_agents=["programs_requirements", "policy_compliance"],
        description="Taking 54 units exceeds recommended load",
        options=[
            {"option": "Proceed with overload approval"},
            {"option": "Reduce to 48 units"}
        ]
    )
]
```

### Negotiation Rounds in Chat Mode

```
Query: "Can I take 67-272 and 67-373 together?"

Round 1:
├── Programs Agent: "Both are required for IS major"
├── Courses Agent: "67-272 has 67-250 as co-req; 67-373 requires 67-272"
├── Policy Agent: "No policy violations"
└── Coordinator: Score 85/100 - Sufficient ✅

Final Answer: "67-373 requires 67-272 as a prerequisite, so they cannot be
taken in the same semester. You should take 67-272 first..."
```

---

## Coordinator Mechanism

### Intent Classification

Two modes available:

1. **Fine-Tuned Classifier** (fast, ~100ms)
   - Custom model trained on advising queries
   - Returns agent routing directly

2. **LLM-Driven Coordination** (slower, ~5s, more detailed)
   - Full GPT-4-turbo reasoning
   - Returns detailed workflow plan with agent tasks

### Coordinator Evaluation Loop

After agents execute, coordinator evaluates quality:

```python
def evaluate_outputs_for_sufficiency(user_query, agent_outputs, round):
    # GPT-5.2 evaluates holistically
    # Returns:
    #   - quality_score (0-100)
    #   - sufficient (bool)
    #   - agents_to_rerun (list)
    #   - agent_feedback (semantic guidance)
```

**Loop Logic:**
1. Round 1: All agents run with default k=5-8
2. If score < 75 and round < 3:
   - Coordinator specifies agents to re-run
   - Enhanced k=10 for broader retrieval
   - Semantic feedback guides agent focus
3. Repeat until sufficient or max rounds

---

## RAG Engine

### Domain-Specific Vector Databases

```
chroma_db_programs/   → Program requirements, sample curricula
chroma_db_courses/    → Course descriptions, prerequisites
chroma_db_policies/   → University policies
chroma_db_schedules/  → Course schedules, calendars
chroma_db_planning/   → Planning-specific docs
```

### Data Sources (`data/`)

```
data/
├── courses/          # 2,478 course JSON files
│   ├── 15-112.json
│   ├── 67-250.json
│   └── ...
├── programs/         # Program requirements
│   ├── IS_requirements.json
│   └── CS_requirements.json
├── policies/         # University policies
├── schedules/        # Semester offerings
│   ├── Spring_2025_courses.json
│   ├── Fall_2025_courses.json
│   └── schedule_2026_spring.json
└── finetune/         # Training data for classifier
```

### Course Data Structure

```json
{
  "code": "67-250",
  "name": "The Information Systems Milieux",
  "units": 9.0,
  "prereqs": {"text": ""},
  "co_reqs": [],
  "anti_reqs": [],
  "long_desc": "...",
  "custom_fields": {
    "goals": "...",
    "key_topics": "...",
    "assessment_structure": "..."
  }
}
```

---

## Streaming & Real-time Updates

### Server-Sent Events (SSE)

Backend streams events via `/api/chat/stream`:

```python
# Event types (streaming/events.py)
class EventType(Enum):
    WORKFLOW_START = "workflow_start"
    COORDINATOR_THINKING = "coordinator_thinking"
    COORDINATOR_ROUTING = "coordinator_routing"
    AGENT_START = "agent_start"
    AGENT_RETRIEVING = "agent_retrieving"
    AGENT_THINKING = "agent_thinking"
    AGENT_OUTPUT = "agent_output"
    AGENT_COMPLETE = "agent_complete"
    COORDINATOR_EVALUATION = "coordinator_evaluation"
    AGENT_RERUN_START = "agent_rerun_start"
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    WORKFLOW_COMPLETE = "workflow_complete"
```

### Frontend Event Handling

```typescript
// EventSource for SSE
const eventSource = new EventSource(`${API_URL}/api/chat/stream`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'agent_start':
      setActiveAgents(prev => [...prev, data.agent]);
      break;
    case 'agent_output':
      setAgentOutputs(prev => ({...prev, [data.agent]: data.data}));
      break;
    // ...
  }
};
```

---

## Planning Mode (Proposal + Critique Protocol)

### Overview

Planning Mode handles complex multi-semester academic planning through a **Proposal + Critique negotiation protocol**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLANNING MODE WORKFLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Round 1:                                                      │
│   ┌──────────────┐                                              │
│   │   Planning   │──── Proposes ────▶ Course Plan (JSON)        │
│   │    Agent     │                                              │
│   └──────────────┘                                              │
│           │                                                     │
│           ▼                                                     │
│   ┌──────────────┬──────────────┬──────────────┐               │
│   │   Programs   │   Courses    │    Policy    │  ◀── PARALLEL │
│   │    Agent     │    Agent     │    Agent     │               │
│   └──────┬───────┴──────┬───────┴──────┬───────┘               │
│          │              │              │                        │
│          └──────────────┼──────────────┘                        │
│                         ▼                                       │
│              ┌─────────────────────┐                            │
│              │  All Approved?      │                            │
│              └─────────┬───────────┘                            │
│                        │                                        │
│         ┌──────────────┴──────────────┐                         │
│         ▼                             ▼                         │
│    [YES: Finalize]            [NO: Round 2...]                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### The Proposal + Critique Protocol

**Phase 1: Proposal**
- Planning Agent generates a complete semester-by-semester plan
- Output is structured JSON with courses, units, prerequisites

**Phase 2: Parallel Critique**
- Three agents evaluate simultaneously (ThreadPoolExecutor)
- Each returns: `approved`, `issues[]`, `suggestions[]`

**Phase 3: Consensus Check**
- If all approve → Finalize plan
- If any reject → Planning Agent revises with feedback
- Maximum 3 rounds

### Agent Critique Structure

```python
@dataclass
class AgentCritique:
    agent_name: str
    approved: bool
    issues: List[str]       # Problems that must be fixed
    suggestions: List[str]  # Optional improvements
    confidence: float

# Example critique from Programs Agent
critique = AgentCritique(
    agent_name="programs_requirements",
    approved=False,
    issues=[
        "Missing required course 67-373 for IS major",
        "Statistics requirement not satisfied"
    ],
    suggestions=[
        "Consider adding 67-373 in Spring 2026",
        "36-200 or 36-225 would satisfy statistics"
    ],
    confidence=0.9
)
```

### Planning Round Data Structure

```python
@dataclass
class PlanningRound:
    round_number: int
    proposed_plan: CoursePlanJSON
    critiques: List[AgentCritique]
    all_approved: bool
    revision_notes: str  # How plan changed from previous round
```

### Visible Negotiation Process

Users see each round of negotiation in real-time:

```
┌─────────────────────────────────────────────────────────────────┐
│  📋 Planning Session: plan_a1b2c3d4                              │
│                                                                 │
│  Round 1/3                                                      │
│  ├── Planning Agent: Proposing initial plan...                  │
│  │   └── 📄 Proposed 8-semester plan (Spring 2025 → Fall 2028)  │
│  │                                                              │
│  ├── Critiquing in parallel...                                  │
│  │   ├── Programs: ⚠️ Found 2 issues                           │
│  │   │   └── Missing 67-373, Statistics not satisfied           │
│  │   ├── Courses: ✅ Approved                                   │
│  │   │   └── All prerequisites satisfied                        │
│  │   └── Policy: ⚠️ Found 1 issue                               │
│  │       └── Semester 3 exceeds 54 units                        │
│  │                                                              │
│  └── Status: 🔄 Revision needed                                 │
│                                                                 │
│  Round 2/3                                                      │
│  ├── Planning Agent: Revising based on feedback...              │
│  │   └── Added 67-373, reduced Semester 3 to 48 units           │
│  │                                                              │
│  ├── Re-critiquing...                                           │
│  │   ├── Programs: ✅ Approved                                  │
│  │   ├── Courses: ✅ Approved                                   │
│  │   └── Policy: ✅ Approved                                    │
│  │                                                              │
│  └── Status: ✅ Consensus reached!                              │
└─────────────────────────────────────────────────────────────────┘
```

### Planning Streaming Events

```python
# Planning-specific events
EventType.PLANNING_SESSION_START    # Session begins
EventType.PLANNING_ROUND_START      # New round
EventType.PLANNING_PROPOSING        # Agent generating plan
EventType.PLANNING_PROPOSAL         # Plan ready (with JSON)
EventType.PLANNING_CRITIQUING       # Critique agents starting
EventType.PLANNING_CRITIQUE         # Single agent critique done
EventType.PLANNING_ROUND_COMPLETE   # Round summary
EventType.PLANNING_COMPLETE         # Final result
```

### Plan Validation with Automated Checks

Before synthesis, plans are validated programmatically:

```python
# Automated validation in coordinator
validation_result = validate_full_plan(parsed_plan, completed_courses)

if not validation_result["valid"]:
    for sem_result in validation_result["semester_results"]:
        # Prereq violations
        for violation in sem_result.get("prereq_violations", []):
            issues.append(
                f"⚠️ PREREQ VIOLATION in {sem_result['semester']}: "
                f"{violation['course']} requires {', '.join(violation['missing'])}"
            )
        # Schedule conflicts
        for conflict in sem_result.get("schedule_conflicts", []):
            issues.append(
                f"⚠️ SCHEDULE CONFLICT: "
                f"{', '.join(conflict['courses'])} have overlapping times"
            )
```

### Planning Session Result

```python
@dataclass
class PlanningSession:
    session_id: str
    user_id: str
    request: str
    student_profile: Dict
    rounds: List[PlanningRound]
    final_plan: Optional[CoursePlanJSON]
    status: str  # "completed" | "max_rounds_reached" | "error"

# Final plan structure
@dataclass
class CoursePlanJSON:
    program: str
    start_semester: str
    target_graduation: str
    total_units: int
    semesters: List[SemesterPlan]
    requirements_met: List[str]
    requirements_pending: List[str]
```

### Planning Coordinator Implementation

```python
class PlanningModeCoordinator:
    MAX_ROUNDS = 3

    async def execute_planning_session(
        self, user_id, conversation_id, request, student_profile
    ) -> PlanningSession:

        session = PlanningSession(...)
        previous_critiques = []

        for round_num in range(1, self.MAX_ROUNDS + 1):
            # Emit round start event (visible to user)
            self._emit({"type": "planning_round_start", "round": round_num})

            # 1. Planning Agent proposes/revises
            proposed_plan = await self._propose_plan(
                round_num=round_num,
                request=request,
                student_profile=student_profile,
                previous_critiques=previous_critiques  # Feedback from last round
            )

            # 2. All agents critique in PARALLEL (ThreadPoolExecutor)
            critiques = await self._gather_critiques_parallel(
                proposed_plan, student_profile
            )

            # 3. Check consensus
            all_approved = all(c.approved for c in critiques)

            # Record round (visible in session history)
            session.rounds.append(PlanningRound(
                round_number=round_num,
                proposed_plan=proposed_plan,
                critiques=critiques,
                all_approved=all_approved
            ))

            if all_approved:
                session.final_plan = proposed_plan
                session.status = "completed"
                return session

            # Save critiques for next round revision
            previous_critiques = critiques

        # Max rounds reached - return best effort
        session.status = "max_rounds_reached"
        session.final_plan = proposed_plan
        return session
```

### User Approval Flow

After planning completes, users can approve and save:

```
POST /api/planning/{session_id}/approve
```

This saves the approved plan to `approved_plans` collection for future reference.

---

## Data Structures

### Key Pydantic Models (`blackboard/schema.py`)

```python
class Risk(BaseModel):
    type: str           # "overload_risk", "time_conflict", "gpa_below_threshold"
    severity: str       # "high", "medium", "low"
    description: str
    policy_citation: Optional[str]

class Constraint(BaseModel):
    source: str         # "policy", "student", "finance"
    description: str
    hard: bool          # True = must satisfy, False = preference
    policy_citation: Optional[str]

class PlanOption(BaseModel):
    semesters: List[Dict]
    courses: List[str]
    risks: List[Risk]
    confidence: float
    justification: str

class Conflict(BaseModel):
    conflict_type: ConflictType  # HARD_VIOLATION, HIGH_RISK, TRADE_OFF
    affected_agents: List[str]
    description: str
    options: List[Dict]
```

### Workflow Steps

```python
class WorkflowStep(Enum):
    INITIAL = "initial"
    INTENT_CLASSIFICATION = "intent_classification"
    AGENT_EXECUTION = "agent_execution"
    NEGOTIATION = "negotiation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    USER_INPUT = "user_input"
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | Next.js 14, TypeScript, Tailwind | User interface |
| Backend | FastAPI, Python 3.11 | API server |
| Workflow | LangGraph | State machine for agent orchestration |
| LLM | OpenAI GPT-4-turbo, GPT-5.2 | Reasoning and generation |
| Vector DB | ChromaDB | RAG retrieval |
| Database | MongoDB Atlas | User data, conversations |
| Auth | JWT | Authentication |
| Streaming | Server-Sent Events | Real-time updates |

---

## Configuration (`config.py`)

```python
# Coordinator - Complex routing and synthesis
COORDINATOR_MODEL = "gpt-4-turbo"
COORDINATOR_TEMPERATURE = 0.3

# Coordinator Evaluation - Quality assessment
COORDINATOR_EVAL_MODEL = "gpt-5.2"
COORDINATOR_EVAL_TEMPERATURE = 0.2

# Agents - Domain-specific tasks
AGENT_MODEL = "gpt-5.2"
AGENT_TEMPERATURE = 0.3
```

---

## File Structure Summary

```
AdvisingBot/
├── agents/                 # Domain agents
│   ├── base_agent.py       # Abstract base class
│   ├── courses_agent.py    # Course & scheduling
│   ├── programs_agent.py   # Programs & requirements
│   ├── policy_agent.py     # Policy compliance
│   └── planning_agent.py   # Academic planning
├── backend/                # FastAPI server
│   ├── server.py           # Main API endpoints
│   └── database.py         # MongoDB operations
├── blackboard/             # Shared state schema
│   └── schema.py           # Pydantic models
├── coordinator/            # Orchestration
│   ├── coordinator.py      # Main coordinator
│   ├── llm_driven_coordinator.py  # LLM reasoning
│   └── finetuned_classifier.py    # Fast routing
├── data/                   # Knowledge base
│   ├── courses/            # 2,478 course JSONs
│   ├── programs/           # Program requirements
│   ├── policies/           # University policies
│   └── schedules/          # Semester offerings
├── frontend/               # Next.js app
│   └── src/
│       ├── app/            # Pages
│       ├── components/     # React components
│       └── lib/            # API client
├── memory/                 # Conversation context
│   ├── memory_manager.py   # History management
│   └── context_formatter.py # Prompt formatting
├── planning/               # Planning mode
│   ├── coordinator.py      # Multi-round negotiation
│   └── schema.py           # Planning data models
├── streaming/              # Real-time events
│   ├── events.py           # Event types
│   └── callback.py         # Event emission
├── chroma_db_*/            # Vector databases
├── multi_agent.py          # LangGraph workflow
├── rag_engine_improved.py  # RAG setup
├── course_tools.py         # Course data utilities
├── config.py               # Model configuration
└── requirements.txt        # Python dependencies
```

---

## Running the System

### Development

```bash
# Backend
cd AdvisingBot
pip install -r requirements.txt
python -m backend.server

# Frontend
cd frontend
npm install
npm run dev
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=sk-...
MONGODB_URI=mongodb+srv://...
JWT_SECRET_KEY=...
OPENAI_API_BASE=...  # Optional: for proxy
```

---

*Last Updated: February 2026*
