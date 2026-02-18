"""
Baseline Runners for Ablation Study — ACL 2026 Submission

Each runner implements the same interface as AgentRunner in backend/server.py:
    async def run(query, user_profile, history) -> dict
    def run_sync(query, user_profile, history) -> dict   # for streaming thread

All runners return a dict with the SAME keys as the full multi_agent workflow,
so server.py can process results identically regardless of which system ran.

Systems
-------
multi_agent        : Full system — LLM routing, 4 parallel agents, iterative
                     coordinator evaluation (3 rounds), LLM synthesis, streaming.
multi_agent_opaque : IDENTICAL processing to multi_agent, but streaming events
                     are suppressed. User sees only the final answer.
                     → Isolates: does transparency change user trust/quality?
single_agent       : One GPT-5.2 call. All 5 RAG domains concatenated into a
                     single prompt. No agents, no coordinator.
                     → Isolates: does multi-agent specialization add value at all?
single_agent_cot   : Same as single_agent + explicit chain-of-thought instructions.
                     → Isolates: does structured reasoning within one call match
                       multi-agent negotiation?
one_shot           : LLM-driven coordinator routes to the right agents. Agents
                     run in parallel. Single-pass synthesis. NO evaluation loop.
                     → Isolates: does the iterative coordinator evaluation (3 rounds)
                       actually improve answer quality?
"""

import asyncio
import json
import re
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import httpx
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

# Project root on path (handled by server.py, but be safe)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from blackboard.schema import AgentOutput, BlackboardState, WorkflowStep
from config import get_agent_model, get_agent_temperature, get_openai_base_url
from course_tools import (
    find_course_codes_in_text,
    get_course_schedule,
    look_up_course_info,
)
from memory.context_formatter import build_agent_context, format_student_profile
from rag_engine_improved import get_retriever

# ============================================================================
# Shared helpers
# ============================================================================

def _make_llm() -> ChatOpenAI:
    """Instantiate an LLM with the same model and settings as the agents."""
    model = get_agent_model()
    temp = get_agent_temperature()
    base_url = get_openai_base_url()
    http_client = httpx.Client(verify=False, timeout=180.0)
    kwargs: Dict[str, Any] = {
        "model": model,
        "temperature": temp,
        "http_client": http_client,
        "request_timeout": 180.0,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


# Module-level retriever cache — shared across all single-agent runners
# so that chroma DBs are only loaded once per process.
_retrievers: Optional[Dict[str, Any]] = None


def _get_retrievers() -> Dict[str, Any]:
    global _retrievers
    if _retrievers is None:
        _retrievers = {
            domain: get_retriever(domain=domain, k=5)
            for domain in ["programs", "courses", "policies", "schedules", "planning"]
        }
    return _retrievers


def _retrieve_all_domains(query: str) -> str:
    """Retrieve top-k chunks from every RAG domain and join them."""
    parts = []
    for domain, ret in _get_retrievers().items():
        docs = ret.invoke(query)
        if docs:
            chunks = "\n".join(d.page_content for d in docs)
            parts.append(f"=== {domain.upper()} ===\n{chunks}")
    return "\n\n".join(parts)


def _get_structured_course_data(query: str) -> str:
    """
    Extract course codes from the query and fetch structured JSON data
    (description, prereqs, schedule) — the same lookup the course_scheduling
    agent performs via course_tools.
    """
    codes = find_course_codes_in_text(query)
    if not codes:
        return ""
    parts: List[str] = []
    for code in codes[:5]:
        info = look_up_course_info(code)
        if info:
            parts.append(f"--- {code} ---\n{json.dumps(info, indent=2, default=str)}")
        for sem in ["Spring 2026", "Fall 2025", "Fall 2026"]:
            sched = get_course_schedule(code, sem)
            if sched:
                parts.append(
                    f"Schedule {code} ({sem}):\n{json.dumps(sched, indent=2, default=str)}"
                )
    return "\n".join(parts)


def _build_lc_messages(history: Optional[List[Dict]]) -> List:
    """Convert conversation history to LangChain message objects."""
    msgs = []
    if not history:
        return msgs
    for m in history[-10:]:
        if m.get("role") == "user":
            msgs.append(HumanMessage(content=m["content"]))
        elif m.get("role") in ("assistant", "agent"):
            msgs.append(AIMessage(content=m["content"]))
    return msgs


def _build_blackboard_state(
    query: str,
    profile: Optional[Dict],
    history: Optional[List[Dict]],
    intent: Optional[Dict] = None,
    workflow: Optional[List[str]] = None,
) -> BlackboardState:
    """Build a fully-populated BlackboardState dict for agent execution."""
    messages = _build_lc_messages(history)
    messages.append(HumanMessage(content=query))
    return {
        "user_query": query,
        "student_profile": profile or {},
        "conversation_history": history or [],
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "plan_options": [],
        "conflicts": [],
        "open_questions": [],
        "messages": messages,
        "active_agents": workflow or [],
        "workflow_step": WorkflowStep.INITIAL,
        "iteration_count": 0,
        "next_agent": None,
        # "goal" is set by the LLM-driven path; "intent_type" by the fine-tuned
        # classifier path. Prefer the richer goal text for synthesize_answer().
        "user_goal": (
            intent.get("goal") or intent.get("intent_type", "")
        ) if intent else None,
        "execution_metadata": None,
        "phase_timing": {},
        "context_text": intent.get("context_text", "") if intent else "",
        "agent_tasks": intent.get("agent_tasks", {}) if intent else {},
        "coordinator_feedback": {},
        "retrieval_k": None,
    }


def _run_agents_parallel(
    agents: Dict[str, Any], active: List[str], state: BlackboardState
) -> Dict[str, AgentOutput]:
    """Execute a subset of agents in parallel, returning {name: AgentOutput}."""
    outputs: Dict[str, AgentOutput] = {}
    if not active:
        return outputs

    def _exec(name: str):
        t = time.time()
        out = agents[name].execute(state)
        return name, out, time.time() - t

    with ThreadPoolExecutor(max_workers=len(active)) as ex:
        futures = {ex.submit(_exec, n): n for n in active}
        for future in as_completed(futures):
            name, out, elapsed = future.result()
            if out is not None:
                outputs[name] = out

    return outputs


def _wrap_result(
    answer: str,
    mode: str,
    agents_executed: List[str],
    agent_outputs: Optional[Dict] = None,
    agent_times: Optional[Dict] = None,
    total_time: float = 0.0,
    llm_calls: int = 1,
    evaluation_rounds: int = 0,
) -> Dict[str, Any]:
    """
    Package any answer into the same dict shape that multi_agent.app.invoke()
    returns — so server.py can process all systems identically.
    """
    seq_time = round(sum((agent_times or {}).values()), 2)
    # Parallel speedup only meaningful when >1 agent ran in parallel
    speedup = round(seq_time / total_time, 2) if total_time > 0 and len(agents_executed) > 1 else 1.0

    return {
        "messages": [HumanMessage(content=answer)],
        "agent_outputs": agent_outputs or {},
        "conflicts": [],
        "risks": [],
        "plan_options": [],
        "workflow_step": "WorkflowStep.COMPLETE",
        "iteration_count": 0,
        "active_agents": agents_executed,
        "user_goal": mode,
        "execution_metadata": {
            "execution_mode": mode,
            "agents_executed": agents_executed,
            "execution_times": agent_times or {},
            "total_execution_time": round(total_time, 2),
            "sequential_equivalent": seq_time,
            "parallel_speedup": speedup,
            "evaluation_rounds": evaluation_rounds,
            "final_quality_score": 0,
            "final_agent_feedback": {},
            "evaluation_history": [],
            "final_confidences": {
                name: round(out.confidence, 2)
                for name, out in (agent_outputs or {}).items()
                if hasattr(out, "confidence")
            },
        },
        "phase_timing": {"total": round(total_time, 2)},
    }


# Combined system prompt used by both single-agent baselines.
# Merges the role descriptions from all four specialized agent prompts.
_COMBINED_SYSTEM_PROMPT = """You are a comprehensive academic advisor for CMU-Q.

You have deep expertise across ALL of the following domains:

## 1. Programs & Requirements (programs_requirements agent role)
- Major/minor/concentration requirements and degree progress
- What courses satisfy which requirements
- Double-counting rules between majors and minors
- Sample curricula and graduation timelines

## 2. Course Information & Scheduling (course_scheduling agent role)
- Course descriptions, prerequisites, co-requisites, anti-requisites
- Course schedules: when courses are offered, times, instructors, sections
- Schedule conflict detection between two courses
- Assessment structures and course content overview
- Each retrieved chunk includes [DOCUMENT CONTEXT] metadata — use it to
  identify the source document (file name, program, courses mentioned).

## 3. University Policies & Compliance (policy_compliance agent role)
- Registration policies: add/drop/withdrawal deadlines
- Overload limits (max units per semester)
- Probation rules and course repeat policies
- Exam, grading, and academic integrity policies
- Micro-course and mini-course policies
- Cite the specific policy document when answering.

## 4. Academic Planning (academic_planning agent role)
- Semester-by-semester course plans
- 4-year graduation plans
- Prerequisite sequencing (never recommend a course before its prereqs)
- Workload balancing: typically 45–54 units per semester
- Department codes: 67-XXX = IS, 15-XXX = CS, 03-XXX = Bio, 70-XXX = BA,
  36-XXX = Stats, 79-XXX = Dietrich, 73-XXX = Economics

STRICT RULES:
- Use actual course codes (XX-XXX format) when referring to courses.
- Check prerequisites from the retrieved context before recommending a course.
- Only recommend courses offered in the semester based on schedule data.
- Do NOT hallucinate — only use information present in the retrieved context.
- Flag uncertainties and risks explicitly.
"""


# ============================================================================
# BASELINE A — Single Agent
# ============================================================================

class SingleAgentRunner:
    """
    Baseline A: One GPT-5.2 call with context retrieved from ALL 5 RAG domains.

    Same model as the specialized agents. Same RAG databases. Same course tools.
    No coordinator. No agent specialization. No iterative refinement.

    Tests: Does multi-agent specialization add value over one capable LLM call?
    """

    def __init__(self):
        self.llm = _make_llm()

    def _build_prompt(
        self,
        query: str,
        profile: Optional[Dict],
        history: Optional[List[Dict]],
        context: str,
        course_data: str,
    ) -> str:
        profile_text = format_student_profile(profile or {})
        history_text = build_agent_context(history or [], profile or {})

        course_section = (
            f"\n## STRUCTURED COURSE DATA (from course_tools)\n{course_data}"
            if course_data
            else ""
        )

        return f"""{_COMBINED_SYSTEM_PROMPT}

{history_text}

## RETRIEVED KNOWLEDGE BASE
{context}
{course_section}

## USER QUERY
{query}

Provide a clear, complete, and specific answer using ONLY the information above."""

    def _sync(
        self,
        query: str,
        profile: Optional[Dict],
        history: Optional[List[Dict]],
    ) -> Dict[str, Any]:
        t0 = time.time()
        context = _retrieve_all_domains(query)
        course_data = _get_structured_course_data(query)
        prompt = self._build_prompt(query, profile, history, context, course_data)
        resp = self.llm.invoke([SystemMessage(content=prompt)])
        total = time.time() - t0
        return _wrap_result(
            answer=resp.content,
            mode="single_agent",
            agents_executed=[],
            total_time=total,
            llm_calls=1,
        )

    def run_sync(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        return self._sync(query, user_profile, history)

    async def run(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.run_sync, query, user_profile, history
        )


# ============================================================================
# BASELINE B — Single Agent + Chain-of-Thought
# ============================================================================

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


class SingleAgentCoTRunner(SingleAgentRunner):
    """
    Baseline B: Single agent with explicit chain-of-thought prompting.

    Same as Baseline A but with structured step-by-step reasoning injected
    into the prompt before the answer is generated.

    Tests: Does CoT structured reasoning within one LLM call match the
    quality improvement from multi-agent negotiation and specialization?
    """

    def _build_prompt(
        self,
        query: str,
        profile: Optional[Dict],
        history: Optional[List[Dict]],
        context: str,
        course_data: str,
    ) -> str:
        base = super()._build_prompt(query, profile, history, context, course_data)
        # Append CoT instructions between the query and answer
        return base.rstrip() + "\n" + _COT_INSTRUCTIONS

    def _sync(
        self,
        query: str,
        profile: Optional[Dict],
        history: Optional[List[Dict]],
    ) -> Dict[str, Any]:
        t0 = time.time()
        context = _retrieve_all_domains(query)
        course_data = _get_structured_course_data(query)
        prompt = self._build_prompt(query, profile, history, context, course_data)
        resp = self.llm.invoke([SystemMessage(content=prompt)])
        total = time.time() - t0
        return _wrap_result(
            answer=resp.content,
            mode="single_agent_cot",
            agents_executed=[],
            total_time=total,
            llm_calls=1,
        )


# ============================================================================
# BASELINE D — One-Shot Multi-Agent (no evaluation loop)
# ============================================================================

class OneShotRunner:
    """
    Baseline D: LLM-driven coordinator + parallel agents + LLM synthesis.
    The evaluation loop (evaluate_outputs_for_sufficiency) is SKIPPED entirely.

    This is the full multi-agent pipeline minus the iterative refinement:
      Coordinator routing → Parallel agents (default k) → Synthesis → Done.

    Tests: Does the iterative coordinator evaluation (up to 3 rounds with
    enhanced k=10 re-retrieval) actually improve answer quality?

    Uses SEPARATE agent instances from the full system (multi_agent.py) to
    avoid any shared mutable state across concurrent requests.
    """

    def __init__(self):
        # Import here so the full system's module-level singletons are
        # unaffected — these are dedicated instances for the one-shot baseline.
        from agents.courses_agent import CourseSchedulingAgent
        from agents.planning_agent import AcademicPlanningAgent
        from agents.policy_agent import PolicyComplianceAgent
        from agents.programs_agent import ProgramsRequirementsAgent
        from coordinator.coordinator import Coordinator

        self.coordinator = Coordinator()
        self.agents: Dict[str, Any] = {
            "programs_requirements": ProgramsRequirementsAgent(),
            "course_scheduling": CourseSchedulingAgent(),
            "policy_compliance": PolicyComplianceAgent(),
            "academic_planning": AcademicPlanningAgent(),
        }

    def _sync(
        self,
        query: str,
        profile: Optional[Dict],
        history: Optional[List[Dict]],
    ) -> Dict[str, Any]:
        t0 = time.time()

        # 1. LLM-driven intent classification (identical to full system)
        intent = self.coordinator.classify_intent(
            query, history or [], profile or {}
        )
        workflow = self.coordinator.plan_workflow(intent)

        # 2. Build BlackboardState
        state = _build_blackboard_state(query, profile, history, intent, workflow)

        # 3. Parallel agent execution (identical to full system, round 1 only)
        agent_times: Dict[str, float] = {}
        agent_outputs: Dict[str, AgentOutput] = {}

        def _exec(name: str):
            t = time.time()
            out = self.agents[name].execute(state)
            return name, out, time.time() - t

        with ThreadPoolExecutor(max_workers=max(len(workflow), 1)) as ex:
            futures = {ex.submit(_exec, n): n for n in workflow}
            for future in as_completed(futures):
                name, out, elapsed = future.result()
                if out is not None:
                    agent_outputs[name] = out
                    agent_times[name] = round(elapsed, 2)

        # 4. *** EVALUATION LOOP INTENTIONALLY SKIPPED ***
        #    evaluate_outputs_for_sufficiency() is NOT called.
        #    This is the key ablation variable distinguishing this
        #    baseline from the full system.

        # 5. LLM synthesis — identical to full system
        state["agent_outputs"] = agent_outputs
        for out in agent_outputs.values():
            state["risks"].extend(out.risks)
            state["constraints"].extend(out.constraints)
            if out.plan_options:
                state["plan_options"].extend(out.plan_options)

        answer = self.coordinator.synthesize_answer(state)
        total = time.time() - t0

        return _wrap_result(
            answer=answer,
            mode="one_shot",
            agents_executed=list(agent_outputs.keys()),
            agent_outputs=agent_outputs,
            agent_times=agent_times,
            total_time=total,
            llm_calls=len(agent_outputs) + 2,  # routing LLM + agents + synthesis LLM
            evaluation_rounds=0,
        )

    def run_sync(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        return self._sync(query, user_profile, history)

    async def run(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.run_sync, query, user_profile, history
        )


# ============================================================================
# NEW — Opaque Multi-Agent (full system, no user visibility)
# ============================================================================

class OpaqueMultiAgentRunner:
    """
    Full multi-agent system — IDENTICAL processing to the transparent system
    (multi_agent) — but streaming events are suppressed.

    The user receives only the final synthesized answer. No agent cards, no
    coordinator evaluation scores, no negotiation panel.

    How it works: app.invoke() runs the full LangGraph workflow. Inside the
    agents and coordinator, emit_event() calls check for a registered
    StreamCallbackManager. When none is registered (set_stream_manager(None)),
    those calls are silent no-ops — so the processing is bit-for-bit identical
    but the frontend sees nothing until the final answer arrives.

    Tests: Does TRANSPARENCY itself change user trust and decision quality,
    independent of the underlying answer quality?

    This is the most important comparison for the paper's Claim 2.
    """

    def __init__(self):
        self._app = None

    def _get_app(self):
        if self._app is None:
            from multi_agent import app  # reuses the full compiled LangGraph workflow
            self._app = app
        return self._app

    def run_sync(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Run the full workflow in a thread without a StreamCallbackManager
        registered, so all emit_event() calls inside agents/coordinator
        are silent no-ops.
        """
        state = _build_blackboard_state(query, user_profile, history)
        # Re-set workflow_step to INITIAL explicitly (already set by helper)
        state["workflow_step"] = WorkflowStep.INITIAL
        return self._get_app().invoke(state)

    async def run(
        self,
        query: str,
        user_profile: Optional[Dict] = None,
        history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.run_sync, query, user_profile, history
        )
