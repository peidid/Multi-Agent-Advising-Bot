# AdvisingBot: Technical Report & Research Progress Assessment

**Date**: February 2026
**Version**: 1.0
**Authors**: Development Team

---

## Executive Summary

AdvisingBot is a production-grade multi-agent academic advising system that demonstrates several novel concepts for AI-assisted decision support. The system currently implements **dynamic workflow coordination**, **parallel agent execution**, **a proposal-critique-revision negotiation protocol**, and **process-visible UI design**. This report provides a comprehensive technical overview and maps current capabilities to the proposed ACL Demo Track 2026 research contributions.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Detailed Component Analysis](#2-detailed-component-analysis)
3. [Mapping Current System to Research Contributions](#3-mapping-current-system-to-research-contributions)
4. [Mapping to Proposal B: Constraint-Verified Academic Advising](#4-mapping-to-proposal-b-constraint-verified-academic-advising)
5. [Current Technical Metrics](#5-current-technical-metrics)
6. [Assessment: Research Readiness for ACL Demo Track 2026](#6-assessment-research-readiness-for-acl-demo-track-2026)
7. [Conclusion](#7-conclusion)

---

## 1. System Architecture Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (Next.js)                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────────┐  │
│  │ ChatMessage │  │ AgentStatus  │  │WorkflowDetails│ │ PlanningPanel   │  │
│  │  (answers)  │  │ (real-time)  │  │ (transparency)│ │ (negotiation)   │  │
│  └─────────────┘  └──────────────┘  └─────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │ SSE Stream
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI + LangGraph)                      │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         COORDINATOR                                     │ │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐    │ │
│  │   │    Intent    │───▶│   Workflow   │───▶│  Answer Synthesis    │    │ │
│  │   │Classification│    │   Planning   │    │ + Conflict Detection │    │ │
│  │   └──────────────┘    └──────────────┘    └──────────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│                    ┌───────────────┼───────────────┐                        │
│                    ▼               ▼               ▼                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    PARALLEL AGENT EXECUTION                           │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │  │
│  │  │  Programs   │ │   Courses   │ │   Policy    │ │    Planning     │ │  │
│  │  │Requirements │ │ Scheduling  │ │ Compliance  │ │   (Proposer)    │ │  │
│  │  │    Agent    │ │    Agent    │ │    Agent    │ │     Agent       │ │  │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └────────┬────────┘ │  │
│  │         │               │               │                  │          │  │
│  │         ▼               ▼               ▼                  ▼          │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │  │
│  │  │ RAG: programs│ │RAG: courses │ │RAG: policies│ │ RAG: planning   │ │  │
│  │  │  ChromaDB   │ │  ChromaDB   │ │  ChromaDB   │ │   ChromaDB      │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                    ┌───────────────┴───────────────┐                        │
│                    ▼                               ▼                        │
│  ┌────────────────────────────┐    ┌────────────────────────────────────┐  │
│  │      BLACKBOARD STATE      │    │         MEMORY SYSTEM              │  │
│  │  • agent_outputs           │    │  • Student Profile (persistent)    │  │
│  │  • constraints / risks     │    │  • Conversation History            │  │
│  │  • plan_options            │    │  • Entity Tracker (short-term)     │  │
│  │  • conflicts               │    │                                    │  │
│  └────────────────────────────┘    └────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │      MongoDB Atlas            │
                    │  • users / profiles           │
                    │  • conversations / messages   │
                    │  • planning_sessions          │
                    └───────────────────────────────┘
```

### 1.2 Core Components

| Component | Implementation | Purpose |
|-----------|---------------|---------|
| **Coordinator** | `coordinator/coordinator.py`, `llm_driven_coordinator.py` | Intent classification, dynamic workflow planning, answer synthesis |
| **Domain Agents (4)** | `agents/{programs,courses,policy,planning}_agent.py` | Specialized knowledge retrieval and reasoning |
| **Blackboard** | `blackboard/schema.py` | Structured shared state for agent communication |
| **RAG Engine** | `rag_engine_improved.py` + 4 ChromaDB instances | Domain-specific knowledge retrieval |
| **Planning Coordinator** | `planning/coordinator.py` | Multi-round negotiation protocol |
| **Streaming** | `streaming/callback.py`, `streaming/events.py` | Real-time SSE for process visibility |
| **Memory** | `memory/profile_manager.py`, `memory/memory_manager.py` | Persistent student profiles + conversation context |

### 1.3 Technology Stack

**Backend:**
- FastAPI (async HTTP framework)
- LangGraph (workflow orchestration)
- LangChain (LLM + RAG abstraction)
- OpenAI (GPT-4-Turbo, GPT-5.2, embeddings)
- Chroma (vector database)
- MongoDB Atlas (persistent storage)
- Python 3.9+

**Frontend:**
- Next.js 14 (React framework)
- Tailwind CSS (styling)
- TypeScript (type safety)
- Server-Sent Events (real-time streaming)

---

## 2. Detailed Component Analysis

### 2.1 The Coordinator: Dynamic Workflow Planning

The Coordinator serves as the "meta-reasoning" layer that decides which agents to activate and how to synthesize their outputs.

#### Intent Classification (Phase 1)

```python
# coordinator/coordinator.py
def classify_intent(query, conversation_history, student_profile):
    """
    Two paths:
    1. Fast path: Fine-tuned classifier (~100ms) for common intents
    2. Fallback: LLM-driven reasoning for complex queries (~3-5s)
    """
    # Returns: required_agents, confidence, reasoning, context_text
```

#### LLM-Driven Workflow Planning (Phase 2)

The `LLMDrivenCoordinator` implements semantic workflow composition:

```python
# coordinator/llm_driven_coordinator.py
class LLMDrivenCoordinator:
    """
    Key innovation: No predefined intent types or routing rules.
    The LLM reasons about:
    1. Which agents to activate based on query semantics
    2. Execution order based on information dependencies
    3. Expected challenges and success criteria
    """

    AGENT_CAPABILITIES = {
        "programs_requirements": {
            "role": "Degree requirements expert",
            "capabilities": ["Check major/minor requirements", "Validate graduation progress"],
            "knowledge_domains": ["Program curricula", "Concentration requirements"],
            "limitations": ["Cannot verify course availability"]
        },
        # ... similar for other agents
    }

    def plan_workflow(self, query, context) -> WorkflowPlan:
        """Returns: goal, reasoning, agents_to_use, execution_order, decision_points"""
```

#### Answer Synthesis (Phase 3)

```python
def synthesize_answer(state: BlackboardState) -> str:
    """
    Combines all agent outputs into coherent response.
    Format: Direct Answer → Key Points → Detailed Explanation → Next Steps

    Also performs:
    - Conflict detection (hard violations, high risks, trade-offs)
    - Policy citation aggregation
    - Risk summarization
    """
```

### 2.2 Domain Agents: Specialized Knowledge Workers

Each agent follows the same pattern but with domain-specific knowledge:

```python
# agents/base_agent.py
class BaseAgent(ABC):
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        self.retriever = get_retriever(domain=domain, k=8)  # Domain-specific RAG
        self.llm = ChatOpenAI(model="gpt-5.2")  # Capable model for agents

    def execute(self, state: BlackboardState) -> AgentOutput:
        # 1. Read from Blackboard (query, profile, constraints)
        # 2. Retrieve domain context via RAG
        # 3. Build prompt with memory context
        # 4. Generate response with LLM
        # 5. Return structured AgentOutput

    def retrieve_context(self, query: str, k: int = None) -> str:
        """Emit streaming events during retrieval for UI visibility"""
        self.emit_retrieving(query)
        results = self.retriever.invoke(query)
        self.emit_retrieving(query, len(results))
        return "\n".join([doc.page_content for doc in results])
```

#### Agent Specializations

| Agent | Domain | Key Capabilities |
|-------|--------|------------------|
| **ProgramsRequirementsAgent** | `programs` | Proposes course plans, validates degree progress, checks major/minor/concentration requirements |
| **CourseSchedulingAgent** | `courses` | Course info lookup, prerequisite chains, schedule conflicts, availability checking |
| **PolicyComplianceAgent** | `policies` | Critiques plans for policy violations (unit limits, probation rules, registration policies) |
| **AcademicPlanningAgent** | `planning` | Generates/revises semester-by-semester JSON plans in Planning Mode |

### 2.3 Blackboard Pattern: Structured Agent Communication

The Blackboard serves as the single source of truth for all agent communication:

```python
# blackboard/schema.py
class BlackboardState(TypedDict):
    # Input
    user_query: str
    user_goal: Optional[str]
    student_profile: Optional[Dict]
    conversation_history: List[Message]

    # Agent outputs (structured)
    agent_outputs: Dict[str, AgentOutput]  # {agent_name: output}

    # Constraints & Risks (aggregated from all agents)
    constraints: List[Constraint]
    risks: List[Risk]

    # Plans & Conflicts
    plan_options: List[PlanOption]
    conflicts: List[Conflict]

    # Workflow state
    active_agents: List[str]
    workflow_step: WorkflowStep  # INITIAL → AGENT_EXECUTION → SYNTHESIS
    iteration_count: int         # For negotiation loops

    # Metadata
    execution_metadata: Optional[Dict]  # Parallel execution stats
    phase_timing: Optional[Dict]        # Timing per phase
```

#### Structured Data Models

```python
@dataclass
class AgentOutput:
    answer: str
    confidence: float  # 0.0 - 1.0
    risks: List[Risk]
    constraints: List[Constraint]
    plan_options: List[PlanOption]
    relevant_policies: List[str]

@dataclass
class Risk:
    type: str           # "overload_risk", "prerequisite_missing", "gpa_risk"
    severity: str       # "high", "medium", "low"
    description: str
    policy_citation: Optional[str]

@dataclass
class Constraint:
    source: str         # "policy", "student", "financial"
    description: str
    hard: bool          # True = violation, False = soft preference
    policy_citation: Optional[str]

class ConflictType(Enum):
    HARD_VIOLATION = "hard_violation"   # Impossible to satisfy
    HIGH_RISK = "high_risk"             # Possible but risky
    TRADE_OFF = "trade_off"             # Multiple valid options
```

### 2.4 RAG Engine: Domain-Specific Knowledge Retrieval

```python
# rag_engine_improved.py

# Domain → Data folder mapping
DOMAIN_PATHS = {
    "programs": ["programs"],              # Degree requirements
    "courses": ["courses", "schedules"],   # Course catalog + schedules
    "policies": ["policies"],              # University policies
    "planning": ["programs", "schedules"]  # Combined for planning
}

# Domain-specific chunking strategy
if domain in ["programs", "schedules", "planning"]:
    chunk_size = 3000   # Larger chunks for structured data
    chunk_overlap = 300
else:
    chunk_size = 1000   # Standard for prose documents
    chunk_overlap = 100
```

#### Specialized JSON-to-Text Conversion

```python
def load_json_as_text(file_path: str) -> str:
    """
    Converts structured JSON to semantic-search-friendly text:

    Before: {"requirements": {"technical_core": {"mathematics": {"choose_one_from": [...]}}}}

    After:
    ### Information Systems Core
    First Year Colloquium: 67-100 Information Systems First Year Colloquium (REQUIRED)
    Database Design And Development: 67-262 Database Design and Development (REQUIRED)
    HCI Requirement: Choose ONE from: 05-391, 05-410, 05-452, 05-897
    """
```

#### Knowledge Base Contents

| Domain | Files | Content |
|--------|-------|---------|
| `chroma_db_programs` | 55 docs, 253 chunks | Degree requirements (IS, CS, BA, Bio), concentrations, minors, sample curricula |
| `chroma_db_courses` | Course JSON files | Course descriptions, prerequisites, learning outcomes |
| `chroma_db_schedules` | 7 docs, 92 chunks | Fall/Spring course offerings, academic calendars |
| `chroma_db_policies` | Policy markdown files | Registration policies, grading policies, academic standing rules |

### 2.5 Planning Mode: Proposal-Critique-Revision Protocol

This is the **key innovation** implementing structured negotiation:

```python
# planning/coordinator.py
class PlanningModeCoordinator:
    MAX_ROUNDS = 3
    CONFIDENCE_THRESHOLD = 0.85  # Re-retrieve if below

    async def execute_planning_session(self, request, student_profile) -> PlanningSession:
        """
        Multi-round negotiation:

        Round N:
        1. Planning Agent proposes/revises JSON plan
        2. Programs, Courses, Policy agents critique IN PARALLEL
        3. If all approve → consensus reached → finalize
        4. Else → Planning Agent reads critiques → revise → Round N+1
        """

        for round_num in range(1, self.MAX_ROUNDS + 1):
            # Step 1: Propose/Revise
            proposed_plan = await self._propose_plan(
                round_num, request, student_profile, previous_critiques
            )

            # Step 2: Parallel Critique
            critiques = await self._gather_critiques_parallel(proposed_plan, student_profile)

            # Step 3: Check Consensus
            all_approved = all(c.approved for c in critiques)

            if all_approved:
                session.finalize(proposed_plan, status="completed")
                return session

            # Prepare for next round
            previous_critiques = critiques
```

#### Critique Schema

```python
@dataclass
class AgentCritique:
    agent_name: str              # "policy_compliance"
    approved: bool               # Must be True from all agents
    issues: List[str]            # ["Fall 2025: 54 units exceeds 51 max"]
    suggestions: List[str]       # ["Move 15-213 to Spring 2026"]
    confidence: float            # If < 0.85, re-retrieve with k=10
    details: Dict[str, Any]      # Additional structured data
```

#### Confidence-Based Re-Retrieval

```python
async def _gather_critiques_parallel(self, plan, student_profile):
    # Initial critique with k=5
    critiques = await asyncio.gather(
        self._critique_programs(plan, student_profile, k=5),
        self._critique_courses(plan, student_profile, k=5),
        self._critique_policy(plan, student_profile, k=5)
    )

    # Check confidence and re-retrieve if needed
    for i, critique in enumerate(critiques):
        if critique.confidence < self.CONFIDENCE_THRESHOLD:
            # Re-run with enhanced retrieval (k=10)
            critiques[i] = await self._critique_X(plan, student_profile, k=10)

    return critiques
```

### 2.6 Streaming System: Process Visibility

The streaming system enables real-time UI updates showing the deliberation process:

```python
# streaming/events.py
class EventType(Enum):
    WORKFLOW_START = "workflow_start"
    COORDINATOR_THINKING = "coordinator_thinking"
    COORDINATOR_ROUTING = "coordinator_routing"
    AGENT_START = "agent_start"
    AGENT_RETRIEVING = "agent_retrieving"
    AGENT_THINKING = "agent_thinking"
    AGENT_OUTPUT = "agent_output"
    AGENT_COMPLETE = "agent_complete"
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    WORKFLOW_COMPLETE = "workflow_complete"

    # Planning mode events
    PLANNING_ROUND_START = "planning_round_start"
    PLANNING_PROPOSAL = "planning_proposal"
    PLANNING_CRITIQUE = "planning_critique"
    PLANNING_ENHANCED_RETRIEVAL = "planning_enhanced_retrieval"
    PLANNING_ROUND_COMPLETE = "planning_round_complete"
    PLANNING_COMPLETE = "planning_complete"
```

#### Event Flow Example

```
1. workflow_start: "Starting to process your question..."
2. coordinator_thinking: "Analyzing your question..."
3. coordinator_routing: "Routing to 3 agents: Programs, Courses, Policy"
4. agent_start (programs): "Checking degree requirements..."
5. agent_retrieving (programs): "Found 8 relevant documents"
6. agent_thinking (programs): "Analyzing program requirements..."
7. agent_output (programs): {answer, confidence: 0.85, risks: [...]}
8. agent_complete (programs): "Found 3 relevant policies"
   [Similar for courses, policy agents - IN PARALLEL]
9. synthesis_start: "Synthesizing final answer..."
10. synthesis_complete: {final_answer, workflow_details}
11. workflow_complete: "Response complete"
```

### 2.7 Memory System: Student Profiles & Context

```python
# memory/profile_manager.py
@dataclass
class StudentProfile:
    user_id: str

    # Academic standing
    major: str                      # "Information Systems"
    minors: List[str]               # ["Computer Science"]
    concentration: str              # "Data Science"
    current_semester: str           # "Spring 2026"
    expected_graduation: str        # "Spring 2027"
    gpa: Optional[float]            # 3.8

    # Course history
    courses_taken: List[CourseTaken]  # [{code, grade, semester}]
    courses_in_progress: List[str]
    courses_planned: List[str]

    # Goals & preferences
    career_goals: List[str]         # ["Software Engineer", "Data Scientist"]
    interests: List[str]            # ["AI/ML", "Web Development"]
    workload_preference: str        # "balanced"

    # Constraints
    must_take_courses: List[str]
    avoid_courses: List[str]
    scheduling_constraints: List[str]  # ["No 8am classes"]
```

#### Context Injection into Agent Prompts

```python
# memory/context_formatter.py
def build_agent_context(conversation_history, student_profile):
    return f"""
=== STUDENT PROFILE ===
Major: {student_profile.major}
Minor: {student_profile.minors}
GPA: {student_profile.gpa}
Completed: {format_courses(student_profile.courses_taken)}
Expected Graduation: {student_profile.expected_graduation}
Career Goals: {student_profile.career_goals}

=== RECENT CONVERSATION ===
{format_recent_messages(conversation_history[-5:])}
"""
```

---

## 3. Mapping Current System to Research Contributions

### 3.1 Research Idea 1: Dynamic Workflow Planning & Coordination with Meta-Reasoning

**Current Implementation Status: ✅ Partially Implemented**

| Proposed Feature | Current Status | Implementation Location |
|------------------|----------------|------------------------|
| LLM coordinator reasons about query semantics | ✅ Implemented | `llm_driven_coordinator.py` |
| Select which agents to activate | ✅ Implemented | `classify_intent()` returns `required_agents` |
| Order agent execution | ⚠️ Parallel only | Currently all agents run in parallel; no sequential ordering |
| Adapt workflow mid-execution | ❌ Not implemented | Static workflow once started |
| Explainable routing decisions | ✅ Implemented | `reasoning` field in intent classification |

**Gap Analysis:**
- The system activates agents dynamically but always runs them in parallel
- No mid-execution adaptation based on intermediate results
- No explicit information dependency modeling

**Recommended Enhancements:**
```python
# Proposed: Add execution_order to WorkflowPlan
class WorkflowPlan:
    agents_to_use: List[str]
    execution_order: List[List[str]]  # [[parallel_group_1], [parallel_group_2], ...]
    dependencies: Dict[str, List[str]]  # {agent: [depends_on_agents]}
    decision_points: List[DecisionPoint]  # Where to check & adapt
```

### 3.2 Research Idea 2: Structured Negotiation Protocol (Proposal-Critique-Revision)

**Current Implementation Status: ✅ Fully Implemented**

| Proposed Feature | Current Status | Implementation Location |
|------------------|----------------|------------------------|
| Proposal step | ✅ Implemented | `AcademicPlanningAgent.propose()` |
| Parallel critique | ✅ Implemented | `_gather_critiques_parallel()` |
| Structured issues/suggestions | ✅ Implemented | `AgentCritique` dataclass |
| Revision based on feedback | ✅ Implemented | `_propose_plan()` with `critique_context` |
| Max rounds limit | ✅ Implemented | `MAX_ROUNDS = 3` |
| Consensus detection | ✅ Implemented | `all(c.approved for c in critiques)` |
| Confidence-based re-retrieval | ✅ Implemented | If confidence < 0.85, k=10 |

**Strengths:**
- Clean separation of proposal vs critique roles
- Parallel critique execution for efficiency
- Explicit feedback loop with revision notes
- Structured output (JSON plans, typed critiques)

**Potential Research Contributions:**
- Empirical study: Does multi-round negotiation improve plan quality vs single-pass?
- Ablation: Which critique agent contributes most to plan improvement?
- User study: Does visible negotiation increase trust?

### 3.3 Research Idea 3: Process-Centric UI Design

**Current Implementation Status: ✅ Fully Implemented**

| Proposed Feature | Current Status | Implementation Location |
|------------------|----------------|------------------------|
| Real-time agent status | ✅ Implemented | `AgentStatus.tsx` |
| Show which agents are active | ✅ Implemented | SSE `agent_start`/`agent_complete` events |
| Phase indicators | ✅ Implemented | Retrieving → Analyzing → Generating |
| Workflow details panel | ✅ Implemented | `WorkflowDetails.tsx` |
| Conflict/risk display | ✅ Implemented | Risk badges, conflict explanations |
| Execution timing | ✅ Implemented | `phase_timing`, parallel speedup |
| Planning negotiation UI | ✅ Implemented | `PlanningPanel.tsx` with round-by-round display |

**Current UI Flow:**
```
User sends message
    ↓
[AgentStatus] Shows: "Programs Agent ⏳ Retrieving..."
              Shows: "Courses Agent ⏳ Analyzing..."
              Shows: "Policy Agent ✅ Complete (87% confidence)"
    ↓
[WorkflowDetails] Shows:
    • Agents used: Programs, Courses, Policy
    • Execution time: 2.3s (3.2x parallel speedup)
    • Risks identified: [overload_risk: medium]
    • Policies cited: [Registration Policy §3.2]
    ↓
[ChatMessage] Shows final answer with agent badges
```

**Planning Mode UI:**
```
[PlanningPanel]
    Round 1:
      📋 Planning Agent Proposal: [Plan display]
      Agent Reviews:
        ✅ Programs: Approved
        ⚠️ Courses: Issues - "15-213 not offered Fall 2025"
        ✅ Policy: Approved
    Round 2:
      📋 Revised Proposal: [Updated plan]
      Agent Reviews: All ✅
    Final Plan: [Approve & Save button]
```

### 3.4 Research Idea 4: Holistic Student Modeling

**Current Implementation Status: ⚠️ Partially Implemented**

| Proposed Feature | Current Status | Implementation Location |
|------------------|----------------|------------------------|
| Multi-dimensional profile | ✅ Implemented | `StudentProfile` dataclass |
| Academic standing | ✅ Implemented | major, GPA, courses_taken |
| Career trajectory | ✅ Implemented | `career_goals`, `interests` |
| Learning preferences | ⚠️ Basic | `workload_preference` only |
| Progressive enrichment | ❌ Not implemented | Profile is manually edited |
| Auto-detection from conversation | ⚠️ Partial | Entity tracker exists but doesn't update profile |
| Cold-start handling | ❌ Not implemented | System requires profile to be set |

**Gap Analysis:**
- Profile exists but is not automatically enriched through conversation
- No inference of preferences from behavior (e.g., "user always asks about AI courses")
- Cold-start: New users must manually fill profile

**Recommended Enhancements:**
```python
# Proposed: Auto-enrichment from conversation
class ConversationProfileEnricher:
    def extract_profile_updates(self, message, current_profile):
        """
        Detects implicit profile information:
        - "I'm struggling with 15-213" → learning_challenges: ["systems programming"]
        - "I want to work at Google" → career_goals: ["tech industry"]
        - "I hate morning classes" → scheduling_constraints: ["no 8am"]
        """
```

---

## 4. Mapping to Proposal B: Constraint-Verified Academic Advising

### 4.1 Current Constraint Checking Capabilities

| Proposal B Requirement | Current Status | Implementation |
|------------------------|----------------|----------------|
| **Hard constraints** | ⚠️ Implicit | Policy agent checks unit limits, prerequisites |
| **Soft objectives** | ⚠️ Implicit | Workload preferences in profile |
| **Constraint templates** | ❌ Not formalized | Constraints are in natural language prompts |
| **Solver-based verification** | ❌ Not implemented | LLM-based checking only |
| **Proof artifacts** | ⚠️ Partial | `policy_citation` field exists but not systematic |
| **Clarification module** | ❌ Not implemented | System doesn't ask clarifying questions |
| **Infeasibility certificates** | ❌ Not implemented | No formal violation explanation |

### 4.2 What Would Need to Be Built

#### Phase 1: Constraint Formalization

```python
# Proposed: Formal constraint representation
class HardConstraint:
    name: str                    # "max_units_per_semester"
    predicate: Callable          # lambda plan: all(sem.units <= 51 for sem in plan)
    policy_reference: str        # "Registration Policy §2.3"
    violation_message: str       # "Semester {X} has {Y} units, max is 51"

class SoftObjective:
    name: str                    # "minimize_morning_classes"
    objective: Callable          # lambda plan: -count_morning_classes(plan)
    weight: float                # 0.3
```

#### Phase 2: Solver Integration

```python
# Proposed: Constraint solver backend
class AcademicPlanSolver:
    def __init__(self, constraints: List[HardConstraint], objectives: List[SoftObjective]):
        self.model = cp_model.CpModel()  # OR-Tools CP-SAT

    def solve(self, student_state, goal) -> SolverResult:
        """
        Returns:
        - feasible: bool
        - plan: Optional[CoursePlan]
        - violations: List[ConstraintViolation]  # If infeasible
        - proof: ProofArtifact
        """

    def verify(self, plan: CoursePlan) -> VerificationResult:
        """Check LLM-proposed plan against formal constraints"""
```

#### Phase 3: Proof Artifact Generation

```python
@dataclass
class ProofArtifact:
    constraints_satisfied: List[ConstraintCheck]
    constraints_violated: List[ConstraintViolation]
    assumptions_made: List[Assumption]  # "Assuming 15-213 offered Spring 2026"
    policy_provenance: Dict[str, PolicyCitation]
    alternatives_if_violated: List[AlternativePlan]
```

#### Phase 4: AdvisingBench Scenarios

```python
# Proposed: Benchmark scenario generator
SCENARIO_FAMILIES = [
    "add_minor_with_prerequisites",
    "switch_major_credit_transfer",
    "overload_request",
    "accelerate_graduation",
    "retake_for_gpa",
    "conflicting_requirements",  # Intentionally infeasible
    "missing_information",       # Forces clarification
]

def generate_scenario(family: str, seed: int) -> AdvisingScenario:
    """Generate synthetic but realistic advising scenario"""
```

---

## 5. Current Technical Metrics

### 5.1 Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Chat latency (sequential)** | ~7-10s | 4 agents × ~2s each |
| **Chat latency (parallel)** | ~2-3s | ThreadPoolExecutor, 3-4x speedup |
| **Planning mode (per round)** | ~5-8s | Proposal + 3 parallel critiques |
| **RAG retrieval** | ~200-500ms | Per agent, k=8 documents |
| **Intent classification (fast)** | ~100ms | Fine-tuned classifier |
| **Intent classification (LLM)** | ~3-5s | GPT-4-Turbo reasoning |

### 5.2 Knowledge Base Statistics

| Domain | Documents | Chunks | Chunk Size |
|--------|-----------|--------|------------|
| Programs | 55 | 253 | 3000 chars |
| Courses | ~200 | ~800 | 1000 chars |
| Schedules | 7 | 92 | 3000 chars |
| Policies | ~30 | ~200 | 1000 chars |
| Planning | 62 | 345 | 3000 chars |

### 5.3 Model Configuration

| Component | Model | Temperature | Purpose |
|-----------|-------|-------------|---------|
| Coordinator | GPT-4-Turbo | 0.3 | Intent classification, synthesis |
| Domain Agents | GPT-5.2 | 0.3 | Specialized reasoning |
| Embeddings | text-embedding-3-large | - | RAG retrieval |

---

## 6. Assessment: Research Readiness for ACL Demo Track 2026

### 6.1 Strengths (What's Working Well)

1. **Multi-Agent Architecture**: Clean separation of concerns, parallel execution, structured communication
2. **Proposal-Critique-Revision Protocol**: Fully implemented negotiation with consensus detection
3. **Process Visibility**: Real-time streaming UI shows deliberation process
4. **Knowledge Base**: Comprehensive coverage of CMU-Q programs, policies, schedules
5. **Production Quality**: FastAPI backend, Next.js frontend, MongoDB persistence

### 6.2 Gaps for Research Contributions

| Gap | Priority | Effort to Address |
|-----|----------|-------------------|
| **Sequential workflow ordering** | Medium | 2-3 days |
| **Mid-execution adaptation** | High | 1-2 weeks |
| **Formal constraint representation** | High (for Proposal B) | 2-3 weeks |
| **Solver integration** | High (for Proposal B) | 2-3 weeks |
| **Proof artifact generation** | High (for Proposal B) | 1-2 weeks |
| **Clarification module** | Medium | 1 week |
| **Auto profile enrichment** | Low | 1 week |
| **AdvisingBench generator** | High (for Proposal B) | 2-3 weeks |

### 6.3 Recommended Next Steps

#### For Proposal A (Demo Paper - Process-Centric Multi-Agent Advising)

1. Add sequential workflow ordering (information dependencies)
2. Implement mid-execution adaptation checkpoints
3. Conduct user study on process visibility vs black-box
4. Document negotiation protocol formally

#### For Proposal B (Constraint-Verified Advising)

1. Formalize 10-20 constraint templates
2. Integrate CP-SAT or similar solver
3. Build proof artifact generator
4. Create AdvisingBench scenario generator (100-500 scenarios)
5. Implement LLM-propose → solver-verify → repair loop

---

## 7. Conclusion

AdvisingBot represents a sophisticated multi-agent academic advising system with several research-worthy innovations already implemented:

1. **Dynamic workflow coordination** via LLM-driven intent classification and routing
2. **Structured negotiation protocol** with proposal-critique-revision loop
3. **Process-centric UI** showing real-time deliberation to users
4. **Domain-specific RAG** with semantic-search-optimized knowledge representation

The system is well-positioned for an ACL Demo Track submission. The main gaps are:
- For **Proposal A**: Add sequential ordering and mid-execution adaptation
- For **Proposal B**: Build constraint formalization, solver integration, and benchmark generator

The codebase is production-quality and extensible, making it a strong foundation for either research direction.

---

## Appendix A: File Structure Reference

```
AdvisingBot/
├── backend/
│   └── server.py              # FastAPI server, REST + SSE endpoints
├── agents/
│   ├── base_agent.py          # Abstract base class for all agents
│   ├── programs_agent.py      # Degree requirements agent
│   ├── courses_agent.py       # Course scheduling agent
│   ├── policy_agent.py        # Policy compliance agent
│   └── planning_agent.py      # Academic planning agent
├── coordinator/
│   ├── coordinator.py         # Main coordinator logic
│   └── llm_driven_coordinator.py  # LLM-based workflow planning
├── planning/
│   ├── coordinator.py         # Planning mode negotiation
│   └── schema.py              # PlanningSession, AgentCritique, etc.
├── blackboard/
│   └── schema.py              # BlackboardState, AgentOutput, Risk, etc.
├── streaming/
│   ├── callback.py            # StreamCallbackManager
│   └── events.py              # Event types and constructors
├── memory/
│   ├── profile_manager.py     # StudentProfile management
│   ├── memory_manager.py      # Combined memory handling
│   ├── entity_tracker.py      # Short-term entity tracking
│   └── context_formatter.py   # Context building for prompts
├── rag_engine_improved.py     # Domain-specific RAG with ChromaDB
├── course_tools.py            # Course lookup utilities
├── config.py                  # Model configuration
├── multi_agent.py             # LangGraph workflow definition
├── chroma_db_*/               # Vector databases (4 domains)
├── data/
│   ├── programs/              # Degree requirements data
│   ├── courses/               # Course catalog data
│   ├── schedules/             # Schedule data
│   └── policies/              # Policy documents
└── frontend/
    └── src/
        ├── app/page.tsx       # Main chat page
        ├── lib/api.ts         # API client with SSE handling
        └── components/
            ├── ChatMessage.tsx
            ├── ChatInput.tsx
            ├── AgentStatus.tsx
            ├── WorkflowDetails.tsx
            ├── PlanningPanel.tsx
            └── ProfileModal.tsx
```

---

## Appendix B: API Reference

### Chat Endpoints

```
POST /api/chat
  Body: { message: string, conversation_id?: string }
  Returns: { answer: string, conversation_id: string, workflow_details: object }

POST /api/chat/stream
  Body: { message: string, conversation_id?: string }
  Returns: SSE stream with events

POST /api/planning/start
  Body: { request: string, conversation_id?: string }
  Returns: SSE stream with planning events

POST /api/planning/{session_id}/approve
  Returns: { success: boolean }
```

### SSE Event Format

```json
{
  "type": "agent_start",
  "agent": "programs_requirements",
  "message": "Checking degree requirements...",
  "timestamp": "2026-02-13T10:30:00Z"
}
```

---

*Last updated: February 2026*
