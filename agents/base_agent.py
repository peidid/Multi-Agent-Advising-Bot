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

        # Domain-specific RAG retriever
        # This automatically loads the correct vector database
        self.retriever = get_retriever(domain=domain, k=5)

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

    def retrieve_context(self, query: str) -> str:
        """
        Retrieve domain-specific context using RAG.
        Emits streaming events for real-time visibility.

        This is the agent's "superpower" - access to domain-specific knowledge.
        """
        # Emit that we're starting retrieval
        self.emit_retrieving(query)

        results = self.retriever.invoke(query)

        # Emit retrieval complete with doc count
        self.emit_retrieving(query, len(results))

        return "\n".join([doc.page_content for doc in results])
    
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

