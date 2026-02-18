# AdvisingBot — Ablation Systems Technical Report

> ACL 2026 Demo Track · CMU-Q Multi-Agent Academic Advising System
> Generated from codebase analysis of `baselines/runners.py`, `multi_agent.py`, `coordinator/coordinator.py`

---

## Table of Contents

1. [Overview & Ablation Design](#1-overview--ablation-design)
2. [System S0 — Full Multi-Agent Transparent (Experiment)](#2-system-s0--full-multi-agent-transparent)
3. [System S1 — Full Multi-Agent Opaque](#3-system-s1--full-multi-agent-opaque)
4. [System S2 — One-Shot Multi-Agent](#4-system-s2--one-shot-multi-agent)
5. [System S3 — Single Agent (Baseline A)](#5-system-s3--single-agent-baseline-a)
6. [System S4 — Single Agent + CoT (Baseline B)](#6-system-s4--single-agent--cot-baseline-b)
7. [Head-to-Head Comparison](#7-head-to-head-comparison)
8. [Data Flow Diagrams](#8-data-flow-diagrams)
9. [What Each Comparison Isolates](#9-what-each-comparison-isolates)

---

## 1. Overview & Ablation Design

The experiment follows a **controlled ablation ladder**: each step up removes exactly one variable from the full system. This lets us attribute any performance difference to that single variable.

```
S3 single_agent          ← no specialisation, no coordination, no CoT
  ↕  Δ = CoT reasoning within one call
S4 single_agent_cot      ← adds structured reasoning, still no specialisation
  ↕  Δ = agent specialisation (4 domain experts vs 1 generalist)
S2 one_shot              ← full routing + parallel agents, no eval loop
  ↕  Δ = iterative coordinator evaluation (up to 3 rounds + k=10 re-retrieval)
S1 multi_agent_opaque    ← full processing, no user visibility
  ↕  Δ = real-time transparency (streaming agent reasoning to user)
S0 multi_agent           ← FULL SYSTEM (experiment)
```

### Shared Infrastructure (all systems)

| Component | Spec |
|---|---|
| LLM for agents / synthesis | GPT-5.2 (`AGENT_MODEL`) |
| LLM for coordinator routing | GPT-4-turbo (`COORDINATOR_MODEL`) |
| LLM for sufficiency evaluation | GPT-5.2 (`COORDINATOR_EVAL_MODEL`) |
| RAG engine | ChromaDB, 5 domain collections |
| Default retrieval k | 5 chunks per domain |
| Enhanced retrieval k | 10 (used by evaluation loop re-runs only) |
| Course tools | `look_up_course_info()`, `get_course_schedule()`, `find_course_codes_in_text()` |

### The 5 RAG Domains

```
chroma_db_programs/   → degree requirements, sample curricula
chroma_db_courses/    → course catalog, prereqs, assessments
chroma_db_policies/   → registration, overload, grading, integrity
chroma_db_schedules/  → semester offerings, times, sections
chroma_db_planning/   → multi-semester plans (programs + schedules merged)
```

---

## 2. System S0 — Full Multi-Agent Transparent

**ID:** `multi_agent`
**Ablation variable:** None — this is the full experiment system
**Streaming:** Yes (real-time SSE events to frontend)
**Runner:** `AgentRunner` in `backend/server.py` (uses `multi_agent.app.invoke()`)

### Architecture

```
START
  │
  ▼
┌─────────────────────────────────────────────────────┐
│ COORDINATOR NODE                                    │
│  1. classify_intent()   ← fine-tuned classifier    │
│     (fast path ~100 ms) or LLM reasoning (~5 s)    │
│  2. plan_workflow()     → list of agent names       │
│  3. emit streaming events to frontend               │
└─────────────────────────────────────────────────────┘
  │ active_agents, agent_tasks, context_text
  ▼
┌─────────────────────────────────────────────────────┐
│ PARALLEL AGENTS NODE (ThreadPoolExecutor)           │
│                                                     │
│  Round 1: all agents run in parallel               │
│  ┌────────────┐ ┌─────────────┐ ┌────────────────┐ │
│  │ programs_  │ │ course_     │ │ policy_        │ │
│  │ requirements│ │ scheduling  │ │ compliance     │ │
│  └────────────┘ └─────────────┘ └────────────────┘ │
│  ┌────────────┐                                     │
│  │ academic_  │                                     │
│  │ planning   │                                     │
│  └────────────┘                                     │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ COORDINATOR EVALUATION LOOP (max 3 rounds)  │   │
│  │  evaluate_outputs_for_sufficiency()         │   │
│  │  GPT-5.2 scores each agent 0–100            │   │
│  │  → if insufficient: re-run weak agents      │   │
│  │    with k=10 + coordinator guidance text    │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
  │ agent_outputs, risks, constraints, plan_options
  ▼
┌─────────────────────────────────────────────────────┐
│ SYNTHESIZE NODE                                     │
│  synthesize_answer() — GPT-5.2                     │
│  Combines all agent outputs into final response     │
└─────────────────────────────────────────────────────┘
  │
  ▼
 END
```

### Core Code — LangGraph Workflow

```python
# multi_agent.py

MAX_EVALUATION_ROUNDS = 3
ENHANCED_K = 10

def parallel_agents_node(state: BlackboardState) -> Dict[str, Any]:
    active_agents = state.get("active_agents", [])
    agent_outputs = {}

    # ROUND 1 — all agents in parallel
    with ThreadPoolExecutor(max_workers=len(active_agents)) as executor:
        future_to_agent = {
            executor.submit(execute_single_agent, name, state): name
            for name in active_agents
        }
        for future in as_completed(future_to_agent):
            name, output, exec_time = future.result()
            if output is not None:
                agent_outputs[name] = output

    # COORDINATOR EVALUATION LOOP
    for round_num in range(1, MAX_EVALUATION_ROUNDS + 1):
        evaluation = coordinator.evaluate_outputs_for_sufficiency(
            user_query=user_query,
            agent_outputs=agent_outputs,
            current_round=round_num,
            student_profile=student_profile
        )

        emit_event(coordinator_evaluation_event(
            round_num=round_num,
            sufficient=evaluation["sufficient"],
            quality_score=evaluation["quality_score"],
            ...
        ))

        if evaluation["sufficient"]:
            break

        # RE-RUN weak agents with k=10 + guidance
        agents_to_rerun = evaluation.get("agents_to_rerun", [])
        rerun_state = dict(state)
        rerun_state["retrieval_k"] = ENHANCED_K
        rerun_state["coordinator_feedback"] = evaluation["agent_feedback"]

        with ThreadPoolExecutor(max_workers=len(agents_to_rerun)) as executor:
            ...  # re-run loop identical to round 1
```

### Coordinator Intent Classification

```python
# coordinator/coordinator.py — classify_intent()

# FAST PATH (USE_FINETUNED_CLASSIFIER = True)
if self.finetuned_classifier:
    result = asyncio.run(
        self.finetuned_classifier.classify(query, student_profile)
    )
    return {
        "intent_type": "finetuned_classified",
        "required_agents": result["agents"],  # e.g. ["programs_requirements", "course_scheduling"]
        "agent_tasks": {...},                  # specific instructions per agent
        "context_text": context_text,
        "confidence": 0.95
    }

# SLOW PATH — full LLM reasoning via LLMDrivenCoordinator
plan = self.llm_coordinator.understand_and_plan(query, history, profile)
return {
    "intent_type": "llm_planned",
    "required_agents": plan.agents,
    "goal": plan.goal,
    "agent_tasks": plan.agent_tasks,   # e.g. {"course_scheduling": "Check if 15-213 is offered Spring 2026"}
    "context_text": context_text,
}
```

### Streaming Events Emitted

| Event | When |
|---|---|
| `coordinator_thinking` | Intent classification starts |
| `coordinator_routing` | Agents selected, reasoning provided |
| `agent_start` | Each agent begins execution |
| `agent_complete` | Each agent finishes with confidence score |
| `coordinator_evaluation` | After each evaluation round with quality score |
| `agent_rerun_start` | Before re-running weak agents |
| `agent_rerun_complete` | After each re-run agent completes |
| `synthesis_start` | Synthesis begins |
| `synthesis_complete` | Final answer ready |
| `workflow_complete` | Entire workflow done, total time reported |

### Key Properties

- **LLM calls per query:** 1 (routing/classification) + N agents + ≤3 evaluations + 1 synthesis
  = typically **7–10 LLM calls** for 4-agent queries
- **Parallel speedup:** ~2–4× over sequential (measured via `parallel_speedup` in metadata)
- **Quality gate:** GPT-5.2 scores every agent 0–100; re-retrieves if score < threshold
- **Coordinator feedback loop:** Failing agents receive `guidance` text + `gaps` list injected into their re-run prompt

---

## 3. System S1 — Full Multi-Agent Opaque

**ID:** `multi_agent_opaque`
**Ablation variable:** Removes transparency (user visibility of agent reasoning)
**Streaming:** No (SSE events suppressed)
**Runner:** `OpaqueMultiAgentRunner` in `baselines/runners.py`

### Key Insight

**Identical computation to S0.** The same LangGraph `app.invoke()` runs. The same coordinator, same 4 agents, same evaluation loop, same synthesis. The only difference: no streaming events reach the frontend.

### How Streaming is Suppressed

```python
# baselines/runners.py — OpaqueMultiAgentRunner

class OpaqueMultiAgentRunner:
    def run_sync(self, query, user_profile=None, history=None):
        state = _build_blackboard_state(query, user_profile, history)
        state["workflow_step"] = WorkflowStep.INITIAL
        # No set_stream_manager() called → emit_event() is a no-op throughout
        return self._get_app().invoke(state)  # reuses the same compiled LangGraph
```

```python
# backend/server.py — streaming endpoint run_workflow()

if data.system == "multi_agent_opaque" and streaming_available:
    from streaming.callback import set_stream_manager as _ssm
    _ssm(None)  # deregister before app.invoke() — ALL emit_event() = no-op

runner = _get_runner(data.system)
result = runner.run_sync(query=data.message, ...)
# mark_done() still called in finally → SSE loop ends → answer delivered
```

```python
# streaming/callback.py — emit_event()

def emit_event(event: StreamEvent) -> None:
    manager = get_stream_manager()   # returns None for opaque system
    if manager is not None:          # False → silent no-op
        manager.emit(event)
```

The frontend receives:
1. `workflow_start` event (emitted BEFORE the thread starts, before suppression)
2. **Nothing** (all agent cards, evaluation scores, routing events suppressed)
3. `answer` event with the final synthesized response

### Research Purpose

This system is the most important comparison for **Claim 2** of the paper:
*"Does showing users the agent reasoning process (transparency) change their trust calibration and decision quality — independently of the answer itself?"*

Since S0 and S1 produce **exactly the same answer** (same model, same data, same computation), any difference in user outcomes is attributable purely to the transparency panel.

---

## 4. System S2 — One-Shot Multi-Agent

**ID:** `one_shot`
**Ablation variable:** Removes iterative coordinator evaluation loop
**Streaming:** No
**Runner:** `OneShotRunner` in `baselines/runners.py`

### Architecture

```
classify_intent()  →  plan_workflow()  →  [parallel agents]  →  synthesize_answer()
                                                ↑
                          NO evaluate_outputs_for_sufficiency()
                          NO re-runs, NO k=10 enhanced retrieval
                          NO coordinator feedback to agents
```

### Core Code

```python
# baselines/runners.py — OneShotRunner._sync()

def _sync(self, query, profile, history):
    t0 = time.time()

    # STEP 1 — identical to full system: LLM-driven routing
    intent  = self.coordinator.classify_intent(query, history or [], profile or {})
    workflow = self.coordinator.plan_workflow(intent)

    # STEP 2 — build state with coordinator's agent_tasks and context_text
    state = _build_blackboard_state(query, profile, history, intent, workflow)

    # STEP 3 — parallel agent execution (round 1 only)
    agent_times, agent_outputs = {}, {}

    def _exec(name):
        t = time.time()
        out = self.agents[name].execute(state)
        return name, out, time.time() - t

    with ThreadPoolExecutor(max_workers=max(len(workflow), 1)) as ex:
        for future in as_completed({ex.submit(_exec, n): n for n in workflow}):
            name, out, elapsed = future.result()
            if out is not None:
                agent_outputs[name] = out
                agent_times[name] = round(elapsed, 2)

    # *** EVALUATION LOOP INTENTIONALLY SKIPPED ***
    # evaluate_outputs_for_sufficiency() is NOT called.

    # STEP 4 — identical to full system: LLM synthesis
    state["agent_outputs"] = agent_outputs
    for out in agent_outputs.values():
        state["risks"].extend(out.risks)
        state["constraints"].extend(out.constraints)
        if out.plan_options:
            state["plan_options"].extend(out.plan_options)

    answer = self.coordinator.synthesize_answer(state)
    ...
    return _wrap_result(answer=answer, mode="one_shot", evaluation_rounds=0, ...)
```

### Separate Instances (No Shared State)

```python
class OneShotRunner:
    def __init__(self):
        # Dedicated instances — not the module-level singletons in multi_agent.py
        # This ensures concurrent requests don't share mutable agent state
        self.coordinator = Coordinator()
        self.agents = {
            "programs_requirements": ProgramsRequirementsAgent(),
            "course_scheduling":     CourseSchedulingAgent(),
            "policy_compliance":     PolicyComplianceAgent(),
            "academic_planning":     AcademicPlanningAgent(),
        }
```

### What's Missing vs S0/S1

| Component | S0 / S1 | S2 (One-Shot) |
|---|---|---|
| Intent routing | ✅ LLM coordinator | ✅ Same |
| Parallel agents | ✅ All selected agents | ✅ Same |
| Retrieval k | 5 (default) | 5 (always) |
| Evaluation after agents | ✅ GPT-5.2 scores 0–100 | ❌ Skipped |
| Re-run weak agents | ✅ Up to 2 extra rounds | ❌ Skipped |
| Enhanced k on re-run | ✅ k=10 | ❌ N/A |
| Coordinator guidance text | ✅ Passed to re-run agents | ❌ N/A |
| Synthesis | ✅ LLM | ✅ Same |
| LLM calls | 7–10 | 2 + N agents |

### Research Purpose

Isolates the contribution of the **iterative evaluation loop**:
*"Does asking GPT-5.2 to score outputs and trigger targeted re-retrieval actually improve answer quality over a single parallel pass?"*

---

## 5. System S3 — Single Agent (Baseline A)

**ID:** `single_agent`
**Ablation variable:** Removes multi-agent specialisation entirely
**Streaming:** No
**Runner:** `SingleAgentRunner` in `baselines/runners.py`

### Architecture

```
ALL 5 RAG domains retrieved  →  Single GPT-5.2 call  →  Answer
        (k=5 each)               with merged context
```

No coordinator. No routing. No specialised agents. One prompt, one LLM response.

### Core Code

```python
# baselines/runners.py — SingleAgentRunner

_COMBINED_SYSTEM_PROMPT = """You are a comprehensive academic advisor for CMU-Q.
You have deep expertise across ALL of the following domains:

## 1. Programs & Requirements
## 2. Course Information & Scheduling
## 3. University Policies & Compliance
## 4. Academic Planning
...
STRICT RULES:
- Use actual course codes (XX-XXX format)
- Check prerequisites from retrieved context before recommending
- Only recommend courses offered in the semester based on schedule data
- Do NOT hallucinate — only use information present in retrieved context
"""

def _sync(self, query, profile, history):
    t0 = time.time()

    # Retrieve from ALL 5 domains, concatenate
    context = _retrieve_all_domains(query)
    # Also get structured course JSON for any course codes in the query
    course_data = _get_structured_course_data(query)

    prompt = self._build_prompt(query, profile, history, context, course_data)
    resp = self.llm.invoke([SystemMessage(content=prompt)])

    total = time.time() - t0
    return _wrap_result(answer=resp.content, mode="single_agent",
                        agents_executed=[], total_time=total, llm_calls=1)
```

### Context Construction

```python
def _retrieve_all_domains(query: str) -> str:
    parts = []
    for domain, retriever in _get_retrievers().items():
        docs = retriever.invoke(query)
        if docs:
            chunks = "\n".join(d.page_content for d in docs)
            parts.append(f"=== {domain.upper()} ===\n{chunks}")
    return "\n\n".join(parts)

def _get_structured_course_data(query: str) -> str:
    codes = find_course_codes_in_text(query)   # regex: XX-XXX pattern
    for code in codes[:5]:
        info = look_up_course_info(code)        # structured JSON from course DB
        for sem in ["Spring 2026", "Fall 2025", "Fall 2026"]:
            sched = get_course_schedule(code, sem)
```

### Prompt Structure

```
[COMBINED_SYSTEM_PROMPT — 4 domains merged]

=== CONVERSATION CONTEXT ===
Student: <last 5 turns>
Advisor: <last 5 turns>

=== STUDENT PROFILE ===
Major: IS   Year: Junior   GPA: 3.4   Courses Completed: 15-110, 67-250...

=== RETRIEVED KNOWLEDGE BASE ===
=== PROGRAMS ===   [k=5 chunks from chroma_db_programs]
=== COURSES ===    [k=5 chunks from chroma_db_courses]
=== POLICIES ===   [k=5 chunks from chroma_db_policies]
=== SCHEDULES ===  [k=5 chunks from chroma_db_schedules]
=== PLANNING ===   [k=5 chunks from chroma_db_planning]

=== STRUCTURED COURSE DATA ===
--- 15-213 ---
{"name": "Introduction to Computer Systems", "prereqs": [...], ...}
Schedule 15-213 (Spring 2026): [{"time": "MWF 10:30", ...}]

=== USER QUERY ===
<query>

Provide a clear, complete, and specific answer using ONLY the information above.
```

### Key Properties

- **LLM calls:** 1 (no coordinator, no evaluation, no synthesis step)
- **Context window usage:** High — all 5 RAG domains concatenated (up to 25 chunks)
- **No specialisation:** The same prompt handles course lookups, policy checks, planning, and requirements
- **Failure mode:** Information from one domain may "dilute" or overshadow another; model must self-organise without agent specialisation

### Research Purpose

The **lowest baseline**: establishes whether multi-agent specialisation adds value at all.
*"Is our complex system actually better than a single well-prompted GPT-5.2 call with access to the same data?"*

---

## 6. System S4 — Single Agent + CoT (Baseline B)

**ID:** `single_agent_cot`
**Ablation variable:** Adds chain-of-thought reasoning to Baseline A; removes specialisation
**Streaming:** No
**Runner:** `SingleAgentCoTRunner(SingleAgentRunner)` in `baselines/runners.py`

### Architecture

Identical to S3, except the prompt is extended with a structured 5-step reasoning scaffold injected between the query and the answer instruction.

### Core Code

```python
class SingleAgentCoTRunner(SingleAgentRunner):
    """Subclass of SingleAgentRunner — overrides _build_prompt() only."""

    def _build_prompt(self, query, profile, history, context, course_data):
        base = super()._build_prompt(query, profile, history, context, course_data)
        return base.rstrip() + "\n" + _COT_INSTRUCTIONS
```

### The CoT Instruction Block

```python
_COT_INSTRUCTIONS = """
Before writing your answer, reason through the following steps INTERNALLY
(do not include these steps in your output — only show the final answer):

STEP 1 — CLASSIFY: What category is this?
  (a) Single-fact lookup (prereq, schedule time, units)
  (b) Policy/procedure question
  (c) Program requirements question
  (d) Cross-domain (needs info from multiple areas)
  (e) Academic planning (needs a semester or multi-year plan)

STEP 2 — IDENTIFY NEEDED DATA: What specific facts do I need?
  List each fact and whether the retrieved context contains it.

STEP 3 — CHECK CONSTRAINTS: Are there constraints to verify?
  - Prerequisites satisfied given the student's completed courses?
  - Schedule conflicts between recommended courses?
  - Policy limits (overload, unit caps, probation)?

STEP 4 — DRAFT ANSWER: Write using ONLY the retrieved context.

STEP 5 — SELF-VERIFY:
  - Did I address every part of the query?
  - Are all course codes in XX-XXX format?
  - Did I hallucinate anything not in the context?
  - Did I flag risks and uncertainties?

Now output ONLY your final answer:"""
```

### CoT vs Multi-Agent Comparison

| Mechanism | CoT (S4) | Multi-Agent (S0/S1) |
|---|---|---|
| Domain separation | Implicit (model must self-separate) | Explicit (4 specialist agents) |
| Constraint checking | Self-prompted (STEP 3) | Dedicated policy_compliance agent |
| Retrieval depth | k=5 per domain, single pass | k=5 default, k=10 on re-run |
| Verification | Self-verify prompt (STEP 5) | GPT-5.2 external evaluator |
| Refinement | None (single call) | Up to 3 re-run rounds |
| LLM calls | 1 | 7–10 |

### Research Purpose

Isolates the contribution of **structured reasoning within one call** vs **structured reasoning distributed across agents**:
*"Is the quality improvement from multi-agent architecture explained by structured domain separation — or can a single model achieve the same with explicit CoT prompting?"*

---

## 7. Head-to-Head Comparison

### Architecture Comparison

| | S3 | S4 | S2 | S1 | S0 |
|---|:---:|:---:|:---:|:---:|:---:|
| **LLM calls (typical)** | 1 | 1 | 2+N | 7–10 | 7–10 |
| **Coordinator routing** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Specialised agents** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Parallel execution** | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Coordinator evaluation** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Re-retrieval (k=10)** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Coordinator guidance** | ❌ | ❌ | ❌ | ✅ | ✅ |
| **CoT prompting** | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Streaming to user** | ❌ | ❌ | ❌ | ❌ | ✅ |

### Return Value Shape (Identical Across All Systems)

All runners return the same dict shape so `server.py` processes results identically:

```python
{
    "messages":          [HumanMessage(content=answer_text)],
    "agent_outputs":     {"agent_name": AgentOutput, ...},   # {} for single-agent
    "conflicts":         [],
    "risks":             [],
    "plan_options":      [],
    "workflow_step":     "WorkflowStep.COMPLETE",
    "active_agents":     ["programs_requirements", ...],     # [] for single-agent
    "execution_metadata": {
        "execution_mode":        "single_agent" | "one_shot" | "parallel_with_coordinator_evaluation",
        "agents_executed":       [...],
        "execution_times":       {"agent_name": 2.3, ...},
        "total_execution_time":  float,
        "sequential_equivalent": float,
        "parallel_speedup":      float,
        "evaluation_rounds":     int,         # 0 for S2, S3, S4
        "final_quality_score":   int,         # 0 for S2, S3, S4
    },
    "phase_timing":      {"total": float, ...},
}
```

### MongoDB Storage Per Request

Every query stores `system: "<system_id>"` alongside all workflow metadata, enabling post-hoc analysis of all 5 systems from a single deployment.

```python
full_metadata = {
    "system":             data.system,   # e.g. "single_agent_cot"
    "agents_used":        agents_used,
    "agent_outputs":      agent_outputs_data,
    "execution_metadata": exec_meta,
    "phase_timing":       phase_timing,
    ...
}
```

---

## 8. Data Flow Diagrams

### S0 / S1 — Full Multi-Agent

```
User Query
    │
    ▼
Fine-tuned Classifier (fast) or LLM Reasoning (slow)
    │ required_agents: ["programs_requirements", "course_scheduling", ...]
    │ agent_tasks: {"course_scheduling": "Check if 15-213 offered Spring 2026"}
    │
    ▼ (ThreadPoolExecutor — all agents simultaneously)
┌───────────────┐  ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  programs_    │  │  course_       │  │  policy_         │  │  academic_       │
│  requirements │  │  scheduling    │  │  compliance      │  │  planning        │
│               │  │                │  │                  │  │                  │
│ RAG: programs │  │ RAG: courses + │  │ RAG: policies    │  │ RAG: planning +  │
│               │  │ course_tools   │  │                  │  │ schedules        │
│ → AgentOutput │  │ → AgentOutput  │  │ → AgentOutput    │  │ → AgentOutput    │
└───────────────┘  └────────────────┘  └──────────────────┘  └──────────────────┘
    │                   │                   │                      │
    └───────────────────┴───────────────────┴──────────────────────┘
                                    │
                                    ▼
                    GPT-5.2 — evaluate_outputs_for_sufficiency()
                    Quality scores, gaps, guidance per agent
                                    │
                        ┌───────────┴────────────┐
                  sufficient?                 insufficient
                        │                         │
                        │            re-run weak agents
                        │            k=10, coordinator guidance
                        │            (max 3 total rounds)
                        │                         │
                        └───────────┬─────────────┘
                                    │
                                    ▼
                    GPT-5.2 — synthesize_answer()
                    Format: planning/requirements/policy/validation
                                    │
                                    ▼
                             Final Answer
```

### S3 / S4 — Single Agent

```
User Query
    │
    ├─ retrieve from programs (k=5)
    ├─ retrieve from courses (k=5)
    ├─ retrieve from policies (k=5)
    ├─ retrieve from schedules (k=5)
    ├─ retrieve from planning (k=5)
    └─ look_up_course_info() for any XX-XXX codes in query
    │
    ▼
COMBINED_SYSTEM_PROMPT + all context + [CoT instructions if S4] + query
    │
    ▼
Single GPT-5.2 call
    │
    ▼
Answer
```

---

## 9. What Each Comparison Isolates

### Comparison 1: S3 vs S4 — Value of CoT Reasoning

**Variable:** Structured chain-of-thought within a single call
**Held constant:** Same model, same RAG data, same prompt structure, 1 LLM call
**Expected finding:** CoT improves accuracy on complex multi-domain queries (prerequisite chains, planning with constraints) but the improvement is bounded by the single-call architecture
**Paper hypothesis:** Multi-agent negotiation outperforms CoT because agents access domain-specific prompts, not just a reasoning scaffold

### Comparison 2: S4 vs S2 — Value of Agent Specialisation

**Variable:** Replacing one generalist call with 4 domain-expert agents + coordinator routing
**Held constant:** CoT no longer applies; focus shifts to whether specialised prompts + dedicated RAG retrievers improve over one generalist call
**Expected finding:** Specialised agents perform better on cross-domain queries (e.g., "Can I add a CS minor and graduate on time?") because each agent focuses its prompt and retrieval on its domain
**Paper hypothesis:** Domain specialisation adds the most value on T4/T5 (cross-domain, planning) queries

### Comparison 3: S2 vs S1/S0 — Value of Iterative Evaluation

**Variable:** GPT-5.2 external evaluator scoring agent outputs + targeted re-retrieval
**Held constant:** Same routing, same 4 agents, same synthesis
**Expected finding:** Iterative evaluation improves recall on complex queries where the first pass misses key facts (e.g., a prereq chain 3 courses deep)
**Paper hypothesis:** Quality score improvement is most pronounced on T3/T4/T5 queries; T1/T2 queries see minimal benefit (already sufficient after round 1)

### Comparison 4: S1 vs S0 — Value of Transparency

**Variable:** Whether users can see agent reasoning in real time
**Held constant:** Identical computation — same answer, same quality, same latency
**Expected finding (human evaluation required):** Transparent users show better trust calibration (trust more when agents are confident, trust less when risks/uncertainties flagged), make better follow-up decisions, and engage more with the advisor
**Paper hypothesis:** Transparency improves user-reported helpfulness and reduces "blind trust" in incorrect answers

---

## Appendix — Shared Helper Functions

```python
# baselines/runners.py

def _build_blackboard_state(query, profile, history, intent=None, workflow=None):
    """Construct a fully-populated BlackboardState for agent execution."""
    messages = _build_lc_messages(history)
    messages.append(HumanMessage(content=query))
    return {
        "user_query":          query,
        "student_profile":     profile or {},
        "conversation_history": history or [],
        "agent_outputs":       {},
        "constraints":         [],
        "risks":               [],
        "plan_options":        [],
        "conflicts":           [],
        "open_questions":      [],
        "messages":            messages,
        "active_agents":       workflow or [],
        "workflow_step":       WorkflowStep.INITIAL,
        "iteration_count":     0,
        "next_agent":          None,
        # Prefer richer "goal" text from LLM path; fall back to intent_type label
        "user_goal":           (intent.get("goal") or intent.get("intent_type", "")) if intent else None,
        "execution_metadata":  None,
        "phase_timing":        {},
        "context_text":        intent.get("context_text", "") if intent else "",
        "agent_tasks":         intent.get("agent_tasks", {}) if intent else {},
        "coordinator_feedback": {},
        "retrieval_k":         None,
    }

def _wrap_result(answer, mode, agents_executed, agent_outputs=None,
                 agent_times=None, total_time=0.0, llm_calls=1, evaluation_rounds=0):
    """Package any answer into the same dict shape as app.invoke() output."""
    seq_time = round(sum((agent_times or {}).values()), 2)
    speedup = round(seq_time / total_time, 2) if total_time > 0 and len(agents_executed) > 1 else 1.0
    return {
        "messages":        [HumanMessage(content=answer)],
        "agent_outputs":   agent_outputs or {},
        "conflicts":       [],
        "risks":           [],
        "plan_options":    [],
        "workflow_step":   "WorkflowStep.COMPLETE",
        "active_agents":   agents_executed,
        "execution_metadata": {
            "execution_mode":        mode,
            "agents_executed":       agents_executed,
            "total_execution_time":  round(total_time, 2),
            "sequential_equivalent": seq_time,
            "parallel_speedup":      speedup,
            "evaluation_rounds":     evaluation_rounds,
            "final_quality_score":   0,
        },
        "phase_timing": {"total": round(total_time, 2)},
    }
```
