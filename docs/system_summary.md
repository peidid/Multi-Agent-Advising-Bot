# TartanMaroon: System Summary & Technical Details

## Overview

TartanMaroon is a multi-agent LLM system for academic advising at Carnegie Mellon University Qatar. It coordinates four domain-specialized agents through an LLM-driven coordinator, using iterative semantic evaluation for chat queries and a structured proposal--critique negotiation protocol for planning tasks. A real-time transparency layer exposes the entire collaboration process to users via Server-Sent Events (SSE).

---

## Architecture

```
User Query (Frontend: Next.js + TypeScript)
        │
        ▼
   FastAPI Backend (SSE streaming)
        │
        ▼
┌─────────────────────────────────────────────────┐
│            LLM-Driven Coordinator               │
│  ┌────────────────┐  ┌───────────────────────┐  │
│  │ Intent/Workflow │  │ Sufficiency Evaluator │  │
│  │ Planner (GPT-4)│  │ (GPT-5.2)            │  │
│  └────────────────┘  └───────────────────────┘  │
│  ┌──────────────────────────────────────────┐   │
│  │ Optional: Fine-Tuned Intent Classifier   │   │
│  │ (Fast path: ~100ms vs ~5s)               │   │
│  └──────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────┘
                   │ WorkflowPlan
                   ▼
     ┌─────────────────────────────┐
     │  Parallel Agent Execution   │
     │  (ThreadPoolExecutor)       │
     │                             │
     │  ┌──────────┐ ┌──────────┐ │
     │  │Programs  │ │Courses   │ │
     │  │Agent     │ │Agent     │ │
     │  │(programs │ │(courses  │ │
     │  │ RAG, k=8)│ │ RAG, k=5)│ │
     │  └──────────┘ └──────────┘ │
     │  ┌──────────┐ ┌──────────┐ │
     │  │Policy    │ │Planning  │ │
     │  │Agent     │ │Agent     │ │
     │  │(policies │ │(planning │ │
     │  │ RAG, k=5)│ │ RAG, k=8)│ │
     │  └──────────┘ └──────────┘ │
     └─────────────┬───────────────┘
                   │ AgentOutputs
                   ▼
     ┌─────────────────────────────┐
     │  Coordinator Evaluation     │
     │  (Holistic sufficiency      │
     │   check, max 3 rounds)      │
     │                             │
     │  If insufficient:           │
     │    → semantic feedback      │
     │    → re-run agents (k=10)   │
     └─────────────┬───────────────┘
                   │
                   ▼
     ┌─────────────────────────────┐
     │  Answer Synthesis           │
     │  (Coordinator merges all    │
     │   agent outputs into final  │
     │   response)                 │
     └─────────────────────────────┘
```

---

## Core Components

### 1. LLM-Driven Coordinator

**Files:** `coordinator/llm_driven_coordinator.py`, `coordinator/coordinator.py`

The coordinator replaces traditional hard-coded intent routing with full LLM reasoning. Given a user query, conversation history, and student profile, it:

1. **Understands** the student's underlying goal (not just keyword matching)
2. **Analyzes** which agents can help, their capabilities, and limitations
3. **Plans** a workflow: execution order, parallelizable stages, decision points
4. **Adapts** the workflow if intermediate results reveal new needs

**Key data structures:**
- `AgentCapability`: Declares each agent's capabilities, knowledge domains, tools, and explicit limitations
- `WorkflowPlan`: Contains goal, reasoning, agent list, execution order, parallel stages, decision points, expected challenges, success criteria, and per-agent task assignments

**Dual routing modes:**
- **Fast path** (~100ms): Fine-tuned intent classifier for quick routing decisions
- **Full reasoning path** (~5s): Complete LLM analysis for complex/ambiguous queries

**Output evaluation** uses a separate, more powerful model (GPT-5.2) for holistic assessment of combined agent outputs, scoring 0--100 with per-agent semantic feedback (strengths, gaps, specific retrieval guidance).

### 2. Domain-Specialized Agents

**Files:** `agents/base_agent.py`, `agents/courses_agent.py`, `agents/programs_agent.py`, `agents/policy_agent.py`, `agents/planning_agent.py`

All agents inherit from `BaseAgent`, which provides:
- **Domain-specific RAG retriever** (ChromaDB collection per domain)
- **Configurable retrieval depth** (default k=5 for courses/policies, k=8 for programs/planning; enhanced to k=10 during re-retrieval)
- **Streaming event emission** (start, retrieving, thinking, output, complete, error)
- **Coordinator feedback integration** (assigned task, guidance from evaluation)
- **Memory context** (conversation history, student profile)

| Agent | Domain | RAG Corpus | Role |
|-------|--------|-----------|------|
| **Programs** | programs | 8 degree programs, sample curricula, milestones | Validates degree requirements, tracks progress, identifies missing requirements |
| **Courses** | courses | 2,478 course JSONs (code, name, units, prereqs) | Retrieves course info, checks prerequisites, detects time conflicts |
| **Policy** | policies | 45 policy documents (registration, academic standing, finance) | Checks policy compliance, explains unit limits, flags violations |
| **Planning** | planning | Program requirements + schedule data | Generates multi-semester plans, balances workload, respects prerequisite chains |

**Agent execution protocol:**
1. Read relevant fields from Blackboard state
2. Retrieve domain-specific context via RAG (with coordinator's assigned task as query focus)
3. Process query + context + coordinator guidance with LLM
4. Return structured `AgentOutput` (answer, confidence, risks, constraints, policies cited)

### 3. Blackboard State

**File:** `blackboard/schema.py`

A `TypedDict` serving as the shared communication medium (no direct agent-to-agent communication):

```python
class BlackboardState(TypedDict):
    user_query: str
    student_profile: Dict[str, Any]       # major, GPA, completed courses, flags
    agent_outputs: Dict[str, AgentOutput]  # key: agent name
    constraints: List[Constraint]          # hard/soft, with policy citations
    risks: List[Risk]                      # severity levels, policy citations
    plan_options: List[PlanOption]
    conflicts: List[Conflict]              # hard_violation, high_risk, trade_off
    messages: List[Any]                    # LangChain messages
    active_agents: List[str]
    workflow_step: WorkflowStep            # INITIAL → AGENT_EXECUTION → SYNTHESIS → COMPLETE
    execution_metadata: Dict[str, Any]     # timing, speedup, evaluation history
    phase_timing: Dict[str, Any]
```

### 4. LangGraph Workflow (Chat Mode)

**File:** `multi_agent.py`

Three-node state machine:
```
START → coordinator → parallel_agents → synthesize → END
                           ↕
                  (evaluation loop, max 3 rounds)
```

**Iterative evaluation loop:**
1. All selected agents execute in parallel (ThreadPoolExecutor)
2. Coordinator evaluates combined outputs with GPT-5.2 → quality score (0--100)
3. If score < 75 and clear gaps exist: re-run specified agents with enhanced k=10 and semantic feedback
4. Maximum 3 rounds, then proceed to synthesis regardless

### 5. Proposal--Critique Protocol (Planning Mode)

**Files:** `planning/coordinator.py`, `planning/schema.py`

For complex multi-semester planning queries, a separate negotiation workflow:

1. **Proposal**: Planning Agent generates a structured semester-by-semester plan (`CoursePlanJSON`)
2. **Parallel Critique**: Three agents evaluate simultaneously:
   - Programs Agent: validates degree requirement satisfaction
   - Courses Agent: checks course availability, prerequisites, schedule conflicts (uses `course_tools` for deterministic validation)
   - Policy Agent: verifies unit limits, academic standing rules
3. **Consensus Check**: If all approve → finalize; if any reject → Planning Agent revises incorporating critique feedback
4. Repeat up to 3 rounds

**Schema:**
- `CoursePlanJSON`: plan_id, semesters (each with courses, units, notes), requirements_met/pending
- `AgentCritique`: agent_name, approved (bool), issues, suggestions, confidence, details
- `PlanningRound`: round_number, proposed_plan, critiques, all_approved, revision_notes
- `PlanningSession`: session_id, rounds[], final_plan, status

### 6. Streaming & Transparency Layer

**Files:** `streaming/events.py`, `streaming/callback.py`, `frontend/src/components/AgentStatus.tsx`, `frontend/src/components/PlanningPanel.tsx`

**Backend (27 event types):**
- Workflow: `WORKFLOW_START`, `WORKFLOW_COMPLETE`
- Coordinator: `COORDINATOR_THINKING`, `COORDINATOR_ROUTING`, `COORDINATOR_CONFLICT`, `COORDINATOR_EVALUATION`
- Agent lifecycle: `AGENT_START`, `AGENT_RETRIEVING`, `AGENT_THINKING`, `AGENT_OUTPUT`, `AGENT_COMPLETE`, `AGENT_ERROR`
- Re-retrieval: `AGENT_RERUN_START`, `AGENT_RERUN_COMPLETE`
- Synthesis: `SYNTHESIS_START`, `SYNTHESIS_STREAMING`, `SYNTHESIS_COMPLETE`
- Planning: `PLANNING_SESSION_START`, `PLANNING_ROUND_START`, `PLANNING_PROPOSING`, `PLANNING_PROPOSAL`, `PLANNING_CRITIQUING`, `PLANNING_CRITIQUE`, `PLANNING_ROUND_COMPLETE`, `PLANNING_COMPLETE`

Each event is a `StreamEvent` dataclass with: event_type, agent_name, phase, message, data payload, timestamp. Serialized as SSE (`data: {JSON}\n\n`).

**Thread-safe callback system:**
- `StreamCallback` uses a `Queue` with `Lock` for thread-safe emission from parallel agents
- `StreamCallbackManager` provides an async generator for FastAPI `StreamingResponse`
- Global `emit_event()` function is safe to call from any thread (no-op when not streaming)

**Frontend transparency panel:**
- **Coordinator status**: Shows current phase with animated indicator
- **Evaluation panel**: Quality score bar (color-coded: red <60, yellow 60--75, green >75), round counter, per-agent feedback with scores/gaps
- **Agent cards**: Collapsible, showing name/icon/status, confidence badge, risk count, expandable response, identified risks (severity-coded), referenced policies
- **Event stream**: Live feed of recent events
- **Planning panel**: Round-by-round display with plan, critique cards (per agent, with approval status, issues, suggestions), and final plan approval

### 7. Data Layer

**RAG Engine:** `rag_engine_improved.py`

Five ChromaDB collections with OpenAI `text-embedding-3-large` embeddings:
| Collection | Source | Documents |
|-----------|--------|-----------|
| `chroma_db_courses` | `data/courses/` | 2,478 course JSON files |
| `chroma_db_programs` | `data/programs/` | 8 degree programs with curricula |
| `chroma_db_policies` | `data/policies/` | 45 policy documents (markdown) |
| `chroma_db_schedules` | `data/schedules/` | 6 semester schedules (2024--2026) |
| `chroma_db_planning` | programs + schedules | Combined for planning queries |

**Deterministic tools:** `course_tools.py` provides programmatic validation:
- `check_prereqs_satisfied(course, completed)` — prerequisite chain checking
- `check_courses_conflict(course_a, course_b, semester)` — schedule conflict detection
- `validate_semester_plan(courses, semester)` — single-semester validation
- `validate_full_plan(plan, completed)` — multi-semester plan validation with prereq ordering

### 8. Backend API

**File:** `backend/server.py` (FastAPI)

Key endpoints:
- `POST /api/chat/stream` — SSE-streamed chat with real-time events
- `POST /api/planning/start` — SSE-streamed planning session (proposal--critique)
- `GET /api/systems` — Available system configurations (for ablation study)
- Auth, conversation management, profile management endpoints

---

## TartanBench

**Location:** `Benchmark/`

A difficulty-stratified benchmark of 355 queries across 5 tiers with 64 student personas.

### Tiers

| Tier | Name | Count | Description |
|------|------|-------|-------------|
| T1 | Single-fact lookup | 104 | Direct retrieval (e.g., "How many units is 15-213?") |
| T2 | Single-domain reasoning | 55 | Inference within one domain (e.g., prerequisite satisfaction check) |
| T3 | Cross-domain constraint checking | 55 | Multi-domain (courses + policies + schedules) |
| T4 | Multi-step planning with constraints | 54 | Personalized multi-semester planning |
| T5 | Adversarial/impossible cases | 34 | Hidden conflicts, impossible constraints |

### Personas (64 total)

Derived from real anonymized student data:
- **Programs**: CS (16), IS (16), BA (16), Bio (16)
- **Levels**: First-year (9), Sophomore (14), Junior (15), Senior (18), 5th year (8)
- **Edge cases**: Academic warning, dual concentrations, dual minors, Dean's List

Each persona includes: demographic info, academic record (courses by semester), narrative context (background notes, goals, concerns), academic standing.

### Reference Answer Structure

- **T1--T2**: Systematically generated with LLM assistance, spot-checked against source data. Fields: answer, source_file, source_field, domain, verification_note.
- **T3--T5**: Human-authored and cross-validated by students and advisors. Fields: expected_answer, reasoning_type, common_mistake, needs_verification, what_makes_this_hard, false_assumption_or_hidden_conflict, correct_response, why_multi_agent_helps, known_traps.

---

## Ablation Study Design

Five configurations tested against TartanBench:

1. **Single-agent baseline** — One LLM with all RAG data, no coordination
2. **Multi-agent without evaluation** — Agents + coordinator routing, no iterative evaluation
3. **Multi-agent with evaluation** — Full iterative evaluation loop (up to 3 rounds)
4. **Multi-agent with proposal--critique** — Full system including planning negotiation
5. **Fine-tuned classifier routing** — Fast-path intent classification replacing LLM reasoning

The `SystemSelector` frontend component and `/api/systems` endpoint enable runtime switching between configurations.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Lucide icons |
| Backend | FastAPI, Python 3.13, SSE streaming |
| Orchestration | LangGraph (state machine), ThreadPoolExecutor |
| LLMs | GPT-4-turbo (coordinator), GPT-5.2 (agents, evaluation) |
| Embeddings | OpenAI text-embedding-3-large |
| Vector Store | ChromaDB (5 domain-specific collections) |
| Database | MongoDB (user data, conversations, planning sessions) |
| Auth | JWT |
| Deployment | Docker Compose |
