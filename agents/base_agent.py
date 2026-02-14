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

