# AdvisingBot — System Technical Report (Ground Truth)

**Status:** Authoritative. Verified directly against source on **2026-06-17**.
**Supersedes:** the ~60 historical `.md` files in the repo root and `docs/` (most are stale or
describe removed/never-wired features — see §11 Documentation Trust Map).
**Rule of thumb:** when this report and any other doc disagree, trust the code and this report.
For models, trust `config.py`, not prose anywhere.

---

## 1. Executive Summary

AdvisingBot ("TartanMaroon") is a **multi-agent academic advising chatbot for Carnegie
Mellon University–Qatar**. It is simultaneously (a) a working web product — Next.js UI over a
FastAPI backend with MongoDB persistence, JWT auth, and real-time SSE streaming of agent
reasoning — and (b) the experimental apparatus for a research paper (ACL 2026; an older
AIED 2026 "Proposal B" framing survives only in docs).

The core design is a **blackboard-coordinated multi-agent system** built on LangGraph:

```
user query
  → Coordinator (triage → memory-resolve → intent-classify → select agents)
  → N domain agents run IN PARALLEL, each with its own Chroma RAG index,
    writing structured AgentOutput into a shared BlackboardState
  → Coordinator EVALUATES all outputs holistically (gpt-5.2); if insufficient,
    forces up to 2 more re-retrieval rounds (k bumped 5/8 → 10)
  → Coordinator SYNTHESIZES the final answer (gpt-4-turbo)
  → events streamed to UI; conversation + assistant message persisted
```

The research story is a **5-system ablation ladder** (full multi-agent → opaque →
single-agent → single-agent+CoT → one-shot) selectable at runtime via one `system` request
parameter, intended to be evaluated against a **284-task benchmark** (T1 lookup → T5
adversarial-impossible).

**The single most important fact for anyone working on this code:** the repo contains roughly
four overlapping generations of code, and **a large amount of clean, plausible-looking code is
dead** (never deployed). The *cleaner-looking* backend (`api/`) is the dead one. See §3 and §9.

---

## 2. Deployment & Runtime Model

| Concern | Reality | Evidence |
|---|---|---|
| Process started in prod | `uvicorn backend.server:app` | `Procfile:1`; `Dockerfile:45-46` (`WORKDIR /app/backend`, `CMD uvicorn server:app`) |
| Platform | Railway, via Dockerfile | `railway.json` (`builder: DOCKERFILE`, healthcheck `/api/health`) |
| Frontend | Next.js 14 app in `frontend/`, base URL `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) | `frontend/src/lib/api.ts:5` |
| Database | MongoDB | `backend/database.py` |
| LLM provider | OpenAI via `langchain_openai.ChatOpenAI`; optional proxy via `OPENAI_API_BASE` | `config.py:16`; every agent builds its own `httpx.Client(verify=False, timeout=180s)` |
| Concurrency model | The LangGraph workflow runs in a **daemon `Thread`** per request; the request coroutine concurrently drains an SSE event queue | `backend/server.py:874-877`, `:882` |
| Engine instantiation | `multi_agent.py` builds the coordinator + 4 agents + compiled graph **once at import** (module-level singletons) | `multi_agent.py:67-83`, `:591-605` |

**Important runtime consequence:** because the agents are module-level singletons and the
evaluation loop mutates the shared `state` dict during re-runs, the live path is **not designed
for safe concurrency** (see §10, risk R1).

---

## 3. System Topology — Four Generations (Live vs Dead)

| Gen | Component | Status | How you can tell |
|---|---|---|---|
| 1 | `chat.py` — CLI demo loop over `multi_agent.app` | **Live, dev-only** | standalone `__main__`; imports `from multi_agent import app, coordinator, ...` (`chat.py:10`); no server/SSE/DB |
| 2 | `multi_agent.py` — the **core LangGraph engine** | **LIVE — the heart of everything** | imported by the live backend, by `chat.py`, by Streamlit, and by all baselines |
| 2 | `streamlit_app_agent_view.py` — research-visualization UI | **Live, dev-only** | `from multi_agent import app` (`:19`); separate entry point, never deployed |
| 3a | `api/` package — modular FastAPI rewrite (6 routers, services layer, 5 Mongo collections incl. `student_profiles`, `sessions`, `audit_logs`) | **DEAD — never deployed** | only `run_api.py:62` (local dev) and `api/main.py:217`'s own `__main__` reference `api.main:app`; frontend never calls its `/api/v1/*` routes |
| 3b | `backend/server.py` — 1342-line monolith + Next.js `frontend/` | **LIVE — this is production** | `Procfile`/`Dockerfile` deploy it; frontend hits its flat `/api/*` routes |
| 4 | `baselines/runners.py` — 4 ablation runners | **Live, runtime-selectable** | registered in `backend/server.py:245-274` `SYSTEM_RUNNERS`; chosen via `system` param |

**Two backends, divergent schemas.** `backend/database.py` (live) uses **3 collections**
(`users` with the student profile *embedded*, `conversations`, `messages`, plus
`planning_sessions`/`approved_plans` for the dead planning mode). The dead `api/database.py`
uses **5 collections** with a *separate* `student_profiles` collection. Building on `api/` will
silently diverge from production.

---

## 4. The Live Request Path (end-to-end, hop by hop)

Tracing a real query: *"Can I add a CS minor as an IS student?"*

### 4.1 Frontend
1. `frontend/src/app/page.tsx:169` `handleSendMessage()` — sets `sending=true`, resets
   `activeAgents/completedAgents/streamEvents`, creates an `AbortController`.
2. `page.tsx:294` calls `chat.sendStreaming(message, conversationId, callbacks, selectedSystem, signal)`.
   `selectedSystem` defaults to `'multi_agent'` (`page.tsx:48`).
3. `frontend/src/lib/api.ts:250` `fetch(POST ${API_URL}/api/chat/stream)` with
   `Authorization: Bearer <jwt>` and body `{message, conversation_id, system}`.
   **`planning_mode` is never sent** (the streaming chat client omits it).

### 4.2 Backend ingress (`backend/server.py`)
4. `@app.post("/api/chat/stream")` handler `chat_stream(data, user=Depends(get_current_user))`
   (`server.py:682`). JWT validated by `get_current_user` (`server.py:145-165`, `jose.jwt.decode`).
5. Get-or-create conversation; `add_message(conversation_id, "user", data.message)` persists the
   user turn (`server.py:691-704`).
6. Build `history` (last 10 messages) and a `student_profile` dict from `user["profile"]`
   (major→list, year, minors, gpa, completed_courses, etc.) (`server.py:707-723`).
7. Register the **process-global** stream manager: `set_stream_manager(stream_manager)`
   (`server.py:729-737`) so deeply-nested `emit_event()` calls reach the SSE queue. Emit
   `workflow_start`.
8. Define `run_workflow()` and spawn it as a **daemon thread** (`server.py:745`, `:874-877`).
   Because `data.system == "multi_agent"` (`server.py:747`), build the initial `BlackboardState`
   (`workflow_step=INITIAL`) and call `workflow_app.invoke(state)` (`server.py:785`,
   `from multi_agent import app as workflow_app` at `:755`).

### 4.3 LangGraph engine (`multi_agent.py`, graph compiled at `:591-605`)
Graph: `START → coordinator → parallel_agents → synthesize → END`, with conditional edges
`route_after_coordinator` (`:600`) and `route_after_parallel` (`:601`).

9. **`coordinator_node`** (`multi_agent.py:125-252`):
   - `coordinator.triage_query(query)` (`coordinator/coordinator.py:218`) — `triage_llm` =
     **gpt-4o-mini @ 0.0** (`config.py:44-45`). 3-way: `greeting` / `general` / `academic`.
     Greeting/general short-circuit with a canned reply; academic continues.
   - `coordinator.classify_intent(query, history, profile)` (`coordinator.py:333`):
     - `llm_coordinator.resolve_context(...)` (`coordinator/llm_driven_coordinator.py:341`) —
       one LLM call that expands pronouns and extracts `focus_entities {courses, programs,
       semesters, professors}`. First turn returns an empty skeleton with **no** LLM call.
     - Routing: if `USE_FINETUNED_CLASSIFIER` and the fine-tuned model loaded →
       `finetuned_classifier.classify(...)` (`coordinator.py` ~393-415); **else**
       `llm_coordinator.understand_and_plan(...)` (`:420-447`) using **gpt-4-turbo @ 0.3**.
       Produces `required_agents`, per-agent `agent_tasks`, and `resolved_context`.
   - `coordinator.plan_workflow(intent)` (`coordinator.py:466-493`) narrows to the agent list.
     For this query → `["programs_requirements", "policy_compliance"]`.
   - Emits `coordinator_routing`; writes `active_agents`, `agent_tasks`, `resolved_context`,
     `context_text`, `workflow_step=AGENT_EXECUTION`.
10. **`parallel_agents_node`** (`multi_agent.py:255-506`):
    - **Round 1:** `ThreadPoolExecutor(max_workers=len(active_agents))` (`:296`) submits
      `execute_single_agent(name, state)` (`:96-118`) per agent; each resolves `AGENT_REGISTRY`
      (`:78-83`) and calls `agent.execute(state)`.
    - Each agent (`agents/base_agent.py:394` `execute`): emit `agent_start`; pick the effective
      query (resolved vs raw, `get_effective_query`, `base_agent.py:228`); `retrieve_context`
      (`:304`) via its domain Chroma retriever; emit `agent_retrieving`; build the domain prompt
      (resolved-context block + `agent_tasks` + `coordinator_guidance` + RAG chunks + structured
      tool output for courses/planning); `self.llm.invoke([...])` — **gpt-5.2 @ 0.3**
      (`config.py:37`); parse JSON → `AgentOutput`; emit `agent_output` / `agent_complete`.
    - **Evaluation loop** (`:313-450`, ≤ `MAX_EVALUATION_ROUNDS=3`):
      `coordinator.evaluate_outputs_for_sufficiency(query, outputs, round, profile)`
      (`coordinator.py:696`) — `eval_llm` = **gpt-5.2 @ 0.2** (`config.py:33`). Returns
      `{sufficient, quality_score, agents_to_rerun, agent_feedback}`; emits
      `coordinator_evaluation`. If `quality_score >= 75` or round 3 → break; else set
      `coordinator_feedback`, `retrieval_k = ENHANCED_K = 10` (`multi_agent.py:92-93`), re-run
      the named agents (emits `agent_rerun_start/complete`). If `academic_planning` ran, plan
      validation (`course_tools.validate_full_plan`) is invoked inside the eval.
    - Aggregates `risks`/`constraints`/`plan_options`; builds `execution_metadata`.
11. `route_after_parallel` (`multi_agent.py:563`) calls `coordinator.detect_conflicts(state)`
    (`coordinator.py:495`); none → `synthesize`.
12. **`synthesize_node`** (`multi_agent.py:509`): `coordinator.synthesize_answer(state)`
    (`coordinator.py:536`) — `self.llm` = **gpt-4-turbo @ 0.3**; emit `synthesis_complete` +
    `workflow_complete`; returns final `messages` + `workflow_step=COMPLETE`. `app.invoke`
    returns the final state to `server.py:785`.

### 4.4 Streaming + persistence (`backend/server.py`)
13. Concurrently, `server.py:882` `async for sse_data in stream_manager.stream_events(): yield`
    — `streaming/callback.py` polls a thread-safe `Queue` and yields `event.to_sse()`
    (`streaming/events.py:97`, `data: {json}\n\n`). The browser parser (`api.ts:270-357`)
    dispatches `agent_*`/`coordinator_*` events to update `AgentStatus.tsx` live.
14. `server.py:888` joins the workflow thread (timeout 300s), extracts
    `response_text = result["messages"][-1].content`, flattens `agent_outputs` → `agent_details`.
15. `add_message(conversation_id, "assistant", response_text, metadata=...)` persists the
    assistant turn with full workflow metadata (agents_used, agent_outputs, conflicts, risks,
    execution_metadata, phase_timing, **and `system`**) (`server.py` ~971).
16. Yields terminal `{"type":"answer", data:{content, conversation_id, agents_used,
    agent_details, execution_stats, phase_timing}}` then `{"type":"done"}`; resets
    `set_stream_manager(None)` (`server.py:983`).

### 4.5 Breakpoint cheat-sheet
- triage decision → `coordinator.py:295`
- agent routing → `coordinator.py:420`
- an agent's LLM call → `agents/base_agent.py` `self.llm.invoke`
- the re-run decision → `coordinator.py` (`evaluate_outputs_for_sufficiency`, ~`:910`)
- final synthesis → `coordinator.py:609`
- bytes leaving for the browser → `backend/server.py:974`

---

## 5. Component Reference

### 5.1 Coordinator (`coordinator/coordinator.py`, `coordinator/llm_driven_coordinator.py`)
`class Coordinator` (`coordinator.py:67`) holds **four** LLM clients:
`self.llm` (gpt-4-turbo, routing+synthesis), `self.triage_llm` (gpt-4o-mini),
`self.eval_llm` (gpt-5.2), and a `clarification_llm` (built but its handler is unused).
Public methods (all live unless noted):
- `triage_query` (`:218`) — greeting/general/academic gate.
- `classify_intent` (`:333`) — calls `LLMDrivenCoordinator.resolve_context` then either the
  fine-tuned classifier or `understand_and_plan`. Produces `required_agents`, `agent_tasks`,
  `resolved_context`.
- `plan_workflow` (`:466`) — hardcoded `intent_type → agent list` mapping
  (`course_info`, `validate_plan`/`plan_semester`, `add_minor`, else passthrough).
- `evaluate_outputs_for_sufficiency` (`:696`) — the holistic re-run judge (gpt-5.2).
- `detect_conflicts` (`:495`), `synthesize_answer` (`:536`).
- `manage_negotiation` (`:612`), `build_context_for_agents` (`:674`).

`class LLMDrivenCoordinator` (`llm_driven_coordinator.py:48`): `resolve_context` (`:341`,
short-term memory), `understand_and_plan` (`:182`, agent selection + per-agent task strings),
`adapt_workflow` (`:495`), and `_create_fallback_plan` (`:647`).

**Dead within the coordinator package:** `ClarificationHandler`
(`coordinator/clarification_handler.py`, instantiated but never invoked) and
`EnhancedIntentClassifier` (`coordinator/intent_classifier_enhanced.py`, never imported).

### 5.2 Domain Agents (`agents/`)
`class BaseAgent(ABC)` (`base_agent.py:15`) is the framework. `__init__(name, domain)` loads a
domain retriever with `default_k = 8 if domain in {programs, planning} else 5`
(`base_agent.py:44-45`). Key methods: `execute(state)→AgentOutput` (`:394`, abstract per agent),
`retrieve_context` (`:304`), `get_effective_query` (`:228`), `get_resolved_context` (`:204`),
`format_resolved_context_for_prompt` (`:246`), `set_retrieval_k_from_state` (`:139`),
`get_assigned_task` (`:150`), `get_coordinator_guidance` (`:168`), plus `emit_*` helpers.

The four concrete agents, registered in `AGENT_REGISTRY` (`multi_agent.py:78-83`):

| Registry key | Class | Domain index | Notes |
|---|---|---|---|
| `programs_requirements` | `ProgramsRequirementsAgent` | `programs` (k=8) | *Proposes* `plan_options` |
| `course_scheduling` | `CourseSchedulingAgent` | `courses` (= courses + schedules, k=5) | Uses `course_tools` for structured lookups; course-code extraction + recency-based reference fallback |
| `policy_compliance` | `PolicyComplianceAgent` | `policies` (k=5) | *Critiques* programs' `plan_options` by reading `agent_outputs["programs_requirements"]` |
| `academic_planning` | `AcademicPlanningAgent` | `planning` (= programs + schedules + planning, k=8) | Also queries `schedules` retriever (k=5) directly (`planning_agent.py:127`) |

**Agent communication is blackboard-only** — agents never call each other directly; they read
prior `AgentOutput`s from shared state. Recent commits (`59d7ce6`, `324b54d`) deliberately
removed per-query conditionals — agents now fetch all relevant data and let the LLM reason.
**No LLM function/tool-calling anywhere** — tools are plain Python calls; LLM output is JSON
parsed with regex.

### 5.3 Blackboard (`blackboard/schema.py`)
`BlackboardState` is a `TypedDict` (unvalidated). Fields: `student_profile`, `user_goal`,
`user_query`, `agent_outputs: Dict[str, AgentOutput]`, `constraints`, `risks`, `plan_options`,
`conflicts`, `open_questions`, `messages`, `active_agents`, `workflow_step: WorkflowStep`,
`iteration_count`, `next_agent` (**dead** — sequential-era vestige), `execution_metadata`,
`phase_timing`, `resolved_context`. (Live code also threads `conversation_history`,
`context_text`, `agent_tasks`, `coordinator_feedback`, `retrieval_k` that are set on the dict
but not declared in the schema.)

Pydantic models: `AgentOutput{agent_name, answer, confidence, relevant_policies[], risks[],
constraints[], plan_options?}`; `Risk{type, severity, description, policy_citation?}`;
`Constraint{source, description, hard, policy_citation?}`; `PlanOption{semesters[], courses[],
risks[], policy_citations[], confidence, justification}`; `Conflict{conflict_type:ConflictType,
affected_agents[], description, options[]}`; `ExecutionMetadata{...}`. Enums:
`ConflictType{HARD_VIOLATION, HIGH_RISK, TRADE_OFF}`, `WorkflowStep{INITIAL, INTENT_CLASSIFICATION,
AGENT_EXECUTION, NEGOTIATION, CONFLICT_RESOLUTION, SYNTHESIS, COMPLETE, USER_INPUT}` (several
states are unused by the live 3-node graph).

### 5.4 RAG Engine & Tools (`rag_engine_improved.py`, `course_tools.py`, `planning_tools.py`)
- Embeddings: `OpenAIEmbeddings` (default model), SSL-disabled httpx client, 180s timeout
  (`rag_engine_improved.py:33`). Vector store: **Chroma**, persisted to `chroma_db_<domain>/`.
- `DOMAIN_PATHS` (`:40-59`) — 5 domains → data folders:
  `programs→[programs]`, `courses→[courses, schedules]`, `policies→[policies]`,
  `schedules→[schedules]`, `planning→[programs, schedules, planning]`. (A commented-out LEGACY
  mapping with the old `Academic & Studies/...` folders sits below at `:61-75` — informational.)
- `get_retriever(domain, k)` (`:504`) loads the persisted Chroma collection; `build_domain_index`
  / `build_all_domain_indexes` (re)build them. Chunking: `chunk_size = 3000` for some domains
  else `1000` (`:545-548`).
- `course_tools.py` — **structured, non-vector** lookups. All ~2,478 course JSONs are
  eager-loaded into an in-memory `DB` dict at import (`:13-56`) for O(1) access. Functions used
  by agents: `get_course_schedule`, `look_up_course_info`, `find_course_codes_in_text`, plus the
  **deterministic validators** `check_prereqs_satisfied`, `check_courses_conflict`,
  `validate_semester_plan`, `validate_full_plan` (`:539-827`) — these are correct but **only
  invoked inside the coordinator's evaluation when the planning agent ran**, not generally (see
  §10, R6 / §12 leverage).
- `planning_tools.py` — prerequisite/plan helpers (largely overlaps `course_tools`; planning
  mode is dead, see §9).

### 5.5 Short-term Memory / Context Resolution
The **only live** memory mechanism is `LLMDrivenCoordinator.resolve_context`
(`llm_driven_coordinator.py:341`), one LLM call per non-first turn producing `resolved_context`
(threaded to agents via `state["resolved_context"]`). The long-term student profile is loaded
fresh from MongoDB per request in `backend/server.py`. The entire `memory/` package
(`entity_tracker.py`, `memory_manager.py`, `profile_manager.py`) is **dead** — superseded
(see §9). `memory/context_formatter.py` functions are used only for prompt string formatting.

### 5.6 Streaming (`streaming/events.py`, `streaming/callback.py`)
`EventType` (`events.py:11`): workflow (`workflow_start/complete`), coordinator
(`coordinator_thinking/routing/conflict/memory_resolved/greeting/shortcircuit/evaluation`),
agent (`agent_start/retrieving/thinking/output/complete/error/rerun_start/rerun_complete`),
synthesis (`synthesis_start/streaming/complete`), planning_* (8 types — **dead**, planning UI
removed), and `status`/`error`. `AgentPhase`: starting/retrieving/analyzing/generating/
complete/error. `StreamEvent.to_sse()` (`events.py:97`) emits `data: {json}\n\n`.
`StreamCallbackManager` (`callback.py`) is a thread-safe `Queue`; a **process-global**
manager is registered per request via `set_stream_manager` (note: process-scoped, not
request-scoped — see §10, R1).

### 5.7 Backend Server, Persistence, Auth (`backend/server.py`, `backend/database.py`)
Routes (all live, flat `/api/*`): `POST /api/auth/register|login`, `GET /api/auth/me`,
`PUT /api/auth/profile`, `GET|POST /api/conversations`, `GET|DELETE /api/conversations/{id}`,
`POST /api/chat`, `POST /api/chat/stream`, `GET /api/systems`, `GET /api/health`, `GET /`.
Planning routes (`POST /api/planning/start`, `GET /api/planning/{id}`, `/user/history`,
`/{id}/approve`) exist but are **orphaned** (no live UI calls them).
DB (`backend/database.py`): MongoDB collections `users` (email-unique, `password_hash`, embedded
`profile`), `conversations` (`user_id`, `updated_at`), `messages` (`conversation_id`, `role`,
`content`, `metadata`), plus `planning_sessions`/`approved_plans` (dead).
Auth: JWT via `python-jose` (`server.py:142,149`); **password hashing is
`sha256(password + SECRET_KEY)`** (`server.py:128-131`) — not bcrypt, not per-user-salted
(see §10, R11). `SECRET_KEY` defaults to `"dev-secret-key-change-in-production"` if unset.

### 5.8 Frontend (`frontend/`, Next.js 14)
`page.tsx` is the app state machine (messages, `activeAgents`/`completedAgents`, `streamEvents`,
`selectedSystem`). `lib/api.ts` is the client: flat `/api/*` calls; `chat.sendStreaming`
(`:243`) drives the SSE reader and dispatches events to callbacks. **`SystemSelector` is live**
(imported `page.tsx:12`, default `'multi_agent'`, passed at `:294`) — this is the ablation
selector. `AgentStatus.tsx`/`WorkflowDetails.tsx` render multi-agent progress (with the 4 agent
IDs **hardcoded in TS**). `PlanningPanel/PlanningToggle/PlanningProgress` and the `planning` API
client exist but are **imported nowhere** in `src` → dead UI.

### 5.9 Baselines / Ablation Harness (`baselines/runners.py`) + Benchmark
`SYSTEM_RUNNERS` (`backend/server.py:245-274`) exposes 5 systems via `GET /api/systems`, selected
per-request by `_get_runner(data.system)`:

| `system` value | Runner | What differs from full system |
|---|---|---|
| `multi_agent` | `agent_runner` → `multi_agent.app` | the full system (this report's §4) |
| `multi_agent_opaque` | `OpaqueMultiAgentRunner` | **identical computation**, streaming events suppressed (tests whether transparency itself matters) |
| `single_agent` | `SingleAgentRunner` | one gpt-5.2 call, all 5 RAG domains concatenated, no coordinator/specialization |
| `single_agent_cot` | `SingleAgentCoTRunner` | single_agent + explicit chain-of-thought prompt |
| `one_shot` | `OneShotRunner` | LLM routing → parallel agents → synthesis, but **evaluation loop skipped** |

Each runner normalizes to `app.invoke()`'s return shape via `_wrap_result` (`runners.py:206`).
Notably, `OneShotRunner` builds **fresh** agent instances (`runners.py:487-499`), unlike the
shared singletons on the live path. `Benchmark/` defines the T1–T5 task taxonomy; there is
**no automated harness** that runs the 284 tasks across the 5 systems yet (see §12).

---

## 6. Models & Prompting (`config.py`)

| Role | Model | Temp | Source |
|---|---|---|---|
| Triage (greeting/general/academic) | `gpt-4o-mini` | 0.0 | `config.py:44-45` |
| Coordinator routing + synthesis | `gpt-4-turbo` | 0.3 | `config.py:28-29` |
| Output evaluation (re-run judge) | **`gpt-5.2`** | 0.2 | `config.py:33-34` |
| Domain agents | **`gpt-5.2`** | 0.3 | `config.py:37-38` |
| Single-agent baselines | `gpt-5.2` | — | `baselines/runners.py:62` |
| Embeddings | `OpenAIEmbeddings` (default) | — | `rag_engine_improved.py:33` |

⚠️ **`gpt-5.2` is a placeholder id** (`config.py:27` has `# TODO: Change to "gpt-5" when OpenAI
releases GPT-5`). Every academic query depends on it for both agents and evaluation, **with no
fallback** — if it doesn't resolve at the configured endpoint, all academic queries fail. Using
the same model for agents and their judge also introduces self-evaluation bias in the ablation
study. **Verify this id resolves before anything else.**

Per-agent prompts inject: (1) a formatted `resolved_context` memory block, (2) the coordinator's
`agent_tasks` instruction, (3) `coordinator_guidance` (gaps/score) on re-runs, (4) domain RAG
chunks, and (5) raw structured tool output (courses/planning). The eval prompt scores 0–100 with
per-agent strengths/gaps/guidance.

---

## 7. Data Layer (`data/`, `chroma_db_*`)

- **~2,478 course JSONs** in `data/courses/` (verified count). Schema (freeform, lossy):
  `{code, name (NULLABLE), short_name, units/min_units/max_units, prereqs:{text} (freeform
  string), co_reqs, anti_reqs, equiv, long_desc, student_sets, website, custom_fields:{goals,
  key_topics, prerequisite_knowledge, assessment_structure, ...}}`. `QV-118.json` and
  `73-260.json` have `name: null` (known issue, §10 R7).
- **7 schedule JSONs** in `data/schedules/` — arrays of sections `{Department-ID, Course-ID,
  Section-ID, Component-ID, Term-ID, Delivery method, Delivery times:{Day,Start time,End time},
  room, Professor, MAX CAPACITY}`.
- `data/programs/` and `data/policies/` markdown feed the programs/policies RAG indexes;
  `data/planning/course_prerequisites.md` feeds the planning index.
- One-time ingestion scripts: `convert_schedules.py`, `process_all_schedules.py`,
  `process_schedules_final.py`, `generate_document_metadata.py`, `setup_domain_indexes.py`,
  `rebuild_indexes_with_metadata.py`.
- **Cruft / not in `DOMAIN_PATHS`:** `data/Your Life/`, `data/Academic & Studies/`,
  `data/new_0116/`, top-level `info/` and `info - 副本/` (a duplicate). These do not feed any
  live index.
- The 5 `chroma_db_*` directories correspond 1:1 to the 5 `DOMAIN_PATHS` keys.

---

## 8. The 3-node Graph vs. the Documented "Negotiation"

The compiled graph is exactly three nodes (`coordinator → parallel_agents → synthesize`,
`multi_agent.py:594-602`). The `WorkflowStep.NEGOTIATION`/`CONFLICT_RESOLUTION` states and the
"proposal → critique → revise negotiation" narrative in several docs describe **either the dead
planning mode or an aspiration**. What the live chat path actually does is **parallel execution
+ a holistic gpt-5.2 evaluation/re-retrieval loop** — not a visible multi-round agent
negotiation. Reconciling the paper's claim with this behavior is a real open item (§12).

---

## 9. What Is DEAD (inventory — safe to ignore, quarantine, or delete)

1. **The entire `api/` package** (`api/main.py`, `api/routes/*`, `api/services/*`,
   `api/database.py`, `api/models/*`) + `run_api.py`. An abandoned parallel backend with a
   *different* DB schema. Highest-confusion item in the repo.
2. **`memory/` package** (`entity_tracker.py`, `memory_manager.py`, `profile_manager.py`) —
   superseded by `LLMDrivenCoordinator.resolve_context` + Mongo profile. ~700 lines.
3. **Planning mode, end to end:** `planning/` package, `backend/server.py` planning routes and
   `if data.planning_mode` branch (`server.py:873`), frontend `PlanningPanel/PlanningToggle/
   PlanningProgress` + the `planning` API client (imported nowhere), and the 8 `planning_*`
   stream event types. UI removed in commit `1ccf2a0`; the `planning_mode` flag is never sent.
4. **Coordinator extras:** `ClarificationHandler`, `EnhancedIntentClassifier`.
5. **`BlackboardState.next_agent`** field; several `WorkflowStep` enum states.
6. **`course_tools` validators** are defined and correct but **not on the general live path**
   (only inside planning-aware evaluation). Not "dead" so much as under-wired (see §12).
7. **Data cruft:** `info - 副本/` (duplicate), `data/Your Life/`, `data/Academic & Studies/`,
   `data/new_0116/`, `Benchmark.zip`, `out*.txt`/`in.txt`, `info - 副本/`.
8. **`chat.py` and `streamlit_app_agent_view.py`** are live but **dev/demo-only** (not in any
   deploy path).

---

## 10. Known Issues, Risks & Tech Debt (ranked)

| # | Issue | Location | Why it matters |
|---|---|---|---|
| R1 | **Shared singleton agents + shared `state` mutation under concurrency** | `multi_agent.py:67-83`, `:296`, `:410-414`; global stream manager `:737` | Concurrent requests can interleave agent state / stream events → nondeterministic wrong answers. Baselines avoid this with fresh instances; the live path does not. |
| R2 | **`gpt-5.2` placeholder model, no fallback** | `config.py:33,37` | If unresolved at the endpoint, all academic queries fail. Verify first. |
| R3 | **No per-agent timeout / no per-agent exception isolation** | `multi_agent.py:296-302` | A hung or erroring agent stalls/kills the whole turn (only the 180s httpx timeout backstops). |
| R4 | **Two backends, divergent Mongo schemas** | `backend/database.py` vs `api/database.py` | Editing the wrong one ships nothing; reading the wrong one misleads. |
| R5 | **`/api/chat` and `/api/chat/stream` duplicate ~150 lines** | `server.py:465-614` vs `682-993` | Bug fixes must be applied twice; the non-streaming `/api/chat` may itself be unused by the live UI. |
| R6 | **Deterministic validators not wired into agents** | `course_tools.py:539-827` | Prereq/conflict checking is done by LLM prose-critique instead of the existing correct functions. Biggest missed correctness lever. |
| R7 | **Null course names ingested as garbage** | `data/courses/QV-118.json`, `73-260.json`; `rag_engine_improved.py` load path | Embeds garbage text for those codes (pollutes retrieval). `course_tools` guards the dict path; RAG does not. |
| R8 | **Fragile JSON extraction via greedy `r'\{.*\}'`** | `programs_agent.py`, `policy_agent.py` | Breaks on multiple/nested JSON blocks; silently degrades to plain-text `AgentOutput`, losing structured risks/constraints. |
| R9 | **Weak password hashing** | `server.py:128-131` | `sha256(pw + shared secret)`, not bcrypt/per-user salt; `SECRET_KEY` has an insecure default. |
| R10 | **Eval-loop errors swallowed into a synthetic "sufficient"** | `coordinator.py` (~`:942-951`) | On exception, returns `{sufficient:True, quality_score:70}` with no log → silently disables the quality mechanism. |
| R11 | **`resolved_context.confidence` computed but effectively ignored** | `base_agent.py:228-244` | Low-confidence pronoun resolutions flow to agents as ground truth. |
| R12 | **Hardcoded constants & 4-place agent registry** | `multi_agent.py:78-83,92-93`; `coordinator.py:466-493`; `AgentStatus.tsx`, `WorkflowDetails.tsx` | Adding/renaming an agent ripples to 4 locations (2 in TS); `MAX_EVALUATION_ROUNDS`/`ENHANCED_K` not configurable. |
| R13 | **Fine-tuned router of unknown runtime status** | `coordinator.py` (`USE_FINETUNED_CLASSIFIER`), `data/finetune/finetune_job.json` | If the job never succeeded, it silently falls back to the ~slow LLM path; you may be paying latency without the intended router. |

---

## 11. Documentation Trust Map

**Trust (current / code-matching):** this `SYSTEM_REPORT.md`; `config.py` for models;
`docs/system_summary.md` (newest); `Benchmark/outline.md` for the research framing;
`docs/ablation_systems_report.md` *for the architecture of the 5 systems only* (its numeric
result tables are **illustrative placeholders, not measurements** — do not cite).

**Do not trust (stale / aspirational):**
- `CURRENT_STATUS.md` — predates negotiation/ablation/memory work; its "0%/100%" figures are old.
- `ARCHITECTURE.md`, `ARCHITECTURE_GUIDE.md` — omit the gpt-5.2 eval split and the live
  `backend/server.py` layer.
- `docs/TECHNICAL_REPORT.md`, `NEGOTIATION_PROTOCOL_ANALYSIS.md` — "negotiation implemented" is
  true only of the dead planning mode; live chat uses parallel + evaluation.
- `PLANNING_*.md`, `CLARIFICATION_*.md` — describe removed/never-wired features.
- `AIED2026_PROPOSAL_B_GAP_ANALYSIS.md` — a SAT/constraint-solver direction with no code.
- The dozens of `BUGFIX_*.md`/`*_SUMMARY.md` — historical changelog notes, not current design.

---

## 12. Highest-Leverage Refinement Points (opinionated)

1. **De-risk the repo first:** quarantine/delete `api/` + `run_api.py`, the `memory/` package,
   and dead planning code so future work stops reading non-running code. Confirm `gpt-5.2`
   resolves and log which routing path (fine-tuned vs LLM) actually executes.
2. **Biggest correctness win:** wire the deterministic `course_tools` validators
   (`check_prereqs_satisfied`, `validate_semester_plan`, `validate_full_plan`) directly into
   `courses_agent.execute()` / `planning_agent.execute()`, injecting verified facts into the
   prompt ("VERIFIED: 67-272 requires 67-262, which the student has NOT completed"). Converts the
   LLM from "prereq guesser" to "explainer of verified facts" — directly helps T3/T5.
3. **Latency:** gate `resolve_context` behind a cheap regex (skip the LLM call when no
   pronouns/references); lower `MAX_EVALUATION_ROUNDS` to 2 or short-circuit at `quality_score >=
   85` on round 1. Eval rounds are the main latency multiplier.
4. **The paper's keystone:** build the missing automated eval harness — loop the 284 benchmark
   tasks × 5 systems through `_get_runner(system).run_sync()`, log a results table, and use a
   **different judge model** than the agents to avoid self-evaluation bias. Delete the
   placeholder numbers in `docs/ablation_systems_report.md` before anyone cites them.
5. **Planning mode:** decide *revive or delete* before touching it. If revived, wire
   `validate_full_plan` into the critique step so it's deterministic, and re-import the frontend
   `PlanningPanel`.

---

## 13. Open Questions (need a runtime trace or your input)

1. Does `gpt-5.2` resolve at the configured `OPENAI_API_BASE`/account?
2. Fine-tuned router: live or silently falling back? (`finetune_job.json` last showed
   `validating_files`.)
3. Under real concurrency, do shared singleton agents corrupt state? (load test needed)
4. Is the ablation study assigning real users to systems, or is all traffic defaulting to
   `multi_agent`?
5. Do the coordinator's per-agent `agent_tasks` / `coordinator_feedback` actually change agent
   behavior, or are they cosmetic? (compare round-1 vs round-2 prompts)
6. Real latency breakdown across resolve_context / eval rounds / RAG (the `phase_timing` data is
   collected but not aggregated anywhere).
7. Does last-10-message truncation (`server.py`) drop load-bearing context in long advising
   sessions?
