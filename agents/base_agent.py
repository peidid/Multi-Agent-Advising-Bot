"""
Base Agent Class

All specialized agents inherit from this base class.
Supports streaming callbacks for real-time progress updates.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from langchain_openai import ChatOpenAI
from rag_engine_improved import get_retriever
from blackboard.schema import BlackboardState, AgentOutput
from config import get_agent_model, get_agent_temperature, get_openai_base_url


class BaseAgent(ABC):
    """
    Base class for all specialized agents.

    Each agent:
    - Has its own domain-specific RAG index
    - Communicates only via Blackboard (no direct communication)
    - Reads/writes specific fields in Blackboard
    - Emits streaming events for real-time UI updates
    """

    def __init__(self, name: str, domain: str):
        """
        Initialize agent with domain-specific RAG.

        Args:
            name: Agent name (e.g., "programs_requirements")
            domain: Domain for RAG (e.g., "programs", "courses", "policies")
        """
        self.name = name
        self.domain = domain

        # Track enhanced retrieval k (set from state during execute)
        # This allows confidence-based re-retrieval to override default k
        self._state_retrieval_k = None

        # Domain-specific RAG retriever
        # This automatically loads the correct vector database
        # Programs/planning domains need higher k due to structured requirements data
        default_k = 8 if domain in ["programs", "planning"] else 5
        self.retriever = get_retriever(domain=domain, k=default_k)
        self._default_k = default_k

        # LLM for agent reasoning - uses faster, cost-effective model
        model = get_agent_model()
        temperature = get_agent_temperature()
        base_url = get_openai_base_url()

        # Configure HTTP client with SSL verification disabled and longer timeout
        import httpx
        http_client = httpx.Client(verify=False, timeout=180.0)  # 3 minutes

        # Build ChatOpenAI with optional proxy support
        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "http_client": http_client,
            "request_timeout": 180.0
        }
        if base_url:
            llm_kwargs["base_url"] = base_url

        self.llm = ChatOpenAI(**llm_kwargs)

    def _emit_event(self, event) -> None:
        """
        Emit a streaming event if streaming is enabled.
        Safe to call even when not streaming.
        """
        try:
            from streaming.callback import emit_event
            emit_event(event)
        except ImportError:
            pass  # Streaming module not available

    def emit_start(self) -> None:
        """Emit agent start event."""
        try:
            from streaming.events import agent_start_event
            self._emit_event(agent_start_event(self.name))
        except ImportError:
            pass

    def emit_retrieving(self, query: str = "", doc_count: int = 0) -> None:
        """Emit retrieval event."""
        try:
            from streaming.events import agent_retrieving_event
            self._emit_event(agent_retrieving_event(self.name, query, doc_count))
        except ImportError:
            pass

    def emit_thinking(self, message: str = "Analyzing information...") -> None:
        """Emit thinking event."""
        try:
            from streaming.events import agent_thinking_event
            self._emit_event(agent_thinking_event(self.name, message))
        except ImportError:
            pass

    def emit_complete(self, confidence: float = 0.0, summary: str = "") -> None:
        """Emit completion event."""
        try:
            from streaming.events import agent_complete_event
            self._emit_event(agent_complete_event(self.name, confidence, summary))
        except ImportError:
            pass

    def emit_output(self, output: AgentOutput) -> None:
        """
        Emit full agent output for real-time display.
        This allows users to see agent responses as they complete.
        """
        try:
            from streaming.events import agent_output_event
            risks = [{"type": r.type, "severity": r.severity, "description": r.description}
                     for r in (output.risks or [])]
            self._emit_event(agent_output_event(
                self.name,
                answer=output.answer,
                confidence=output.confidence,
                risks=risks,
                relevant_policies=output.relevant_policies or []
            ))
        except ImportError:
            pass

    def emit_error(self, error: str) -> None:
        """Emit error event."""
        try:
            from streaming.events import agent_error_event
            self._emit_event(agent_error_event(self.name, error))
        except ImportError:
            pass

    def set_retrieval_k_from_state(self, state: BlackboardState) -> None:
        """
        Set enhanced retrieval k from state (for confidence-based re-retrieval).
        Call this at the start of execute() to enable enhanced retrieval.
        """
        self._state_retrieval_k = state.get("retrieval_k")
        # Also store coordinator feedback if available
        self._coordinator_feedback = state.get("coordinator_feedback", {}).get(self.name, {})
        # Store specific task from coordinator
        self._assigned_task = state.get("agent_tasks", {}).get(self.name, "")

    def get_assigned_task(self) -> str:
        """
        Get the specific task assigned by the coordinator for this query.

        Returns the task instruction that tells this agent exactly what
        to focus on for the current user query.
        """
        if not hasattr(self, '_assigned_task') or not self._assigned_task:
            return ""

        return f"""
--- COORDINATOR TASK ASSIGNMENT ---
Your specific task for this query: {self._assigned_task}

Focus on accomplishing this task. Retrieve relevant information and provide a focused response.
--- END TASK ---
"""

    def get_coordinator_guidance(self) -> str:
        """
        Get coordinator guidance for this agent (if available from re-retrieval).

        Returns semantic feedback from the coordinator about what information
        is missing or needs improvement. This helps the agent focus its
        retrieval on what's actually needed.
        """
        if not hasattr(self, '_coordinator_feedback') or not self._coordinator_feedback:
            return ""

        guidance_parts = []

        # Add guidance text
        guidance = self._coordinator_feedback.get("guidance", "")
        if guidance:
            guidance_parts.append(f"Coordinator Guidance: {guidance}")

        # Add identified gaps
        gaps = self._coordinator_feedback.get("gaps", [])
        if gaps:
            guidance_parts.append(f"Information Gaps to Address: {', '.join(gaps)}")

        # Add score context
        score = self._coordinator_feedback.get("score", 0)
        if score > 0:
            guidance_parts.append(f"Previous Response Score: {score}/100")

        if guidance_parts:
            return "\n".join([
                "\n--- COORDINATOR FEEDBACK (Focus on these areas) ---",
                *guidance_parts,
                "--- END FEEDBACK ---\n"
            ])
        return ""

    def get_resolved_context(self, state: BlackboardState) -> dict:
        """
        Read the short-term memory (resolved working memory) produced by the
        coordinator. Returns an empty-shape dict if not present, so callers
        can always rely on the keys.
        """
        rc = state.get("resolved_context") or {}
        if not rc:
            return {}
        # Defensive defaults: agents can rely on these keys existing.
        rc.setdefault("resolved_query", "")
        rc.setdefault("focus_entities", {
            "courses": [], "programs": [], "semesters": [], "professors": []
        })
        fe = rc["focus_entities"]
        for k in ("courses", "programs", "semesters", "professors"):
            fe.setdefault(k, [])
        rc.setdefault("topic_continuity", "new_topic")
        rc.setdefault("prior_facts_summary", "")
        rc.setdefault("unresolved_references", [])
        rc.setdefault("needs_clarification", False)
        rc.setdefault("confidence", 0.0)
        return rc

    def get_effective_query(self, state: BlackboardState) -> str:
        """
        Return the query the agent should reason over.

        Prefers the resolved (pronoun-expanded) query when the coordinator's
        short-term memory produced one with reasonable confidence. Falls back
        to the raw user_query otherwise — never returns an empty string.
        """
        rc = self.get_resolved_context(state)
        resolved = (rc.get("resolved_query") or "").strip()
        confidence = float(rc.get("confidence", 0.0) or 0.0)
        raw = state.get("user_query", "") or ""
        # Use resolved only when (a) it exists, (b) confidence is non-trivial,
        # (c) it's actually different from the raw query OR confidence is high.
        if resolved and confidence >= 0.3:
            return resolved
        return raw

    def format_resolved_context_for_prompt(self, state: BlackboardState) -> str:
        """
        Build a compact, readable block describing the short-term memory for
        inclusion in an agent prompt. Returns "" when there's nothing useful
        (e.g., first-turn query with no resolution).
        """
        rc = self.get_resolved_context(state)
        if not rc:
            return ""

        raw_query = state.get("user_query", "") or ""
        resolved_query = (rc.get("resolved_query") or "").strip()
        fe = rc.get("focus_entities", {})
        continuity = rc.get("topic_continuity", "new_topic")
        prior = (rc.get("prior_facts_summary") or "").strip()
        unresolved = rc.get("unresolved_references", []) or []
        needs_clar = rc.get("needs_clarification", False)
        confidence = rc.get("confidence", 0.0)

        # First-turn or no-op resolution → don't pollute the prompt.
        no_entities = not any(fe.get(k) for k in ("courses", "programs", "semesters", "professors"))
        no_prior    = not prior
        same_query  = resolved_query == raw_query or not resolved_query
        if continuity == "new_topic" and no_entities and no_prior and same_query:
            return ""

        lines = ["--- RESOLVED WORKING MEMORY (from coordinator short-term memory) ---"]
        if resolved_query and resolved_query != raw_query:
            lines.append(f"Resolved query: {resolved_query}")
            lines.append(f"Original query: {raw_query}")
        else:
            lines.append(f"Query: {raw_query}")

        focus_lines = []
        if fe.get("courses"):
            focus_lines.append(f"  • Courses in focus: {', '.join(fe['courses'])}")
        if fe.get("programs"):
            focus_lines.append(f"  • Programs in focus: {', '.join(fe['programs'])}")
        if fe.get("semesters"):
            focus_lines.append(f"  • Semesters in focus: {', '.join(fe['semesters'])}")
        if fe.get("professors"):
            focus_lines.append(f"  • Professors in focus: {', '.join(fe['professors'])}")
        if focus_lines:
            lines.append("Focus entities:")
            lines.extend(focus_lines)

        lines.append(f"Topic continuity: {continuity}")
        if prior:
            lines.append(f"Prior facts: {prior}")
        if unresolved:
            lines.append(f"Unresolved references: {', '.join(unresolved)}")
        if needs_clar:
            lines.append("NOTE: needs_clarification=true — if you cannot proceed confidently, say so and ask the student to clarify.")
        lines.append(f"Resolution confidence: {confidence:.2f}")
        lines.append("Use the resolved query and focus entities as the ground truth for what the student is asking about right now.")
        lines.append("--- END WORKING MEMORY ---")
        return "\n".join(lines)

    def retrieve_context(self, query: str, k: int = None) -> str:
        """
        Retrieve domain-specific context using RAG.
        Emits streaming events for real-time visibility.

        This is the agent's "superpower" - access to domain-specific knowledge.

        Args:
            query: The search query
            k: Number of documents to retrieve (optional, uses state/default if not specified)
        """
        # Emit that we're starting retrieval
        self.emit_retrieving(query)

        # Determine effective k value:
        # 1. Explicit k parameter (from method call)
        # 2. State retrieval_k (from confidence-based re-retrieval)
        # 3. Default k for this domain
        effective_k = k if k is not None else self._state_retrieval_k

        if effective_k is not None and effective_k != self._default_k:
            # Use custom k value - get a new retriever with different k
            from rag_engine_improved import get_retriever
            custom_retriever = get_retriever(domain=self.domain, k=effective_k)
            results = custom_retriever.invoke(query)
        else:
            results = self.retriever.invoke(query)

        # Emit retrieval complete with doc count
        self.emit_retrieving(query, len(results))

        return "\n".join([doc.page_content for doc in results])

    def get_memory_context(self, state: BlackboardState) -> str:
        """
        Get formatted memory context from state.

        This includes:
        - Recent conversation history (so agent understands "it", "the course", etc.)
        - Student profile (major, courses taken, goals)

        Args:
            state: Current workflow state

        Returns:
            Formatted context string for inclusion in prompts
        """
        # Check if context_text was pre-built by coordinator
        if state.get("context_text"):
            return state["context_text"]

        # Build context from state components
        try:
            from memory.context_formatter import build_agent_context
            conversation_history = state.get("conversation_history", [])
            student_profile = state.get("student_profile", {})
            return build_agent_context(conversation_history, student_profile)
        except ImportError:
            # Fallback: simple formatting
            return self._simple_context_format(state)

    def _simple_context_format(self, state: BlackboardState) -> str:
        """Simple fallback context formatting."""
        parts = []

        # Student profile
        profile = state.get("student_profile", {})
        if profile:
            major = profile.get("major")
            if isinstance(major, list) and major:
                major = major[0]
            if major:
                parts.append(f"Student Major: {major}")

            courses = profile.get("completed_courses", [])
            if courses:
                parts.append(f"Completed Courses: {', '.join(courses[:5])}")

        # Conversation history
        history = state.get("conversation_history", [])
        if history:
            recent = history[-3:]
            for msg in recent:
                role = "Student" if msg.get("role") == "user" else "Advisor"
                content = msg.get("content", "")[:200]
                parts.append(f"{role}: {content}")

        return "\n".join(parts) if parts else ""
    
    @abstractmethod
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Main execution method - each agent implements this.
        
        Steps:
        1. Read relevant fields from Blackboard
        2. Use RAG to retrieve domain-specific information
        3. Process with LLM
        4. Return structured AgentOutput
        
        Args:
            state: Current Blackboard state
            
        Returns:
            AgentOutput: Structured output
        """
        pass

