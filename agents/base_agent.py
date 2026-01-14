"""
Base Agent Class
All specialized agents inherit from this base class.
"""
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from rag_engine_improved import get_retriever
from blackboard.schema import BlackboardState, AgentOutput
from config import get_agent_model, get_agent_temperature

class BaseAgent(ABC):
    """
    Base class for all specialized agents.
    
    Each agent:
    - Has its own domain-specific RAG index
    - Communicates only via Blackboard (no direct communication)
    - Reads/writes specific fields in Blackboard
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
        
        # Configure HTTP client with SSL verification disabled and longer timeout
        import httpx
        http_client = httpx.Client(verify=False, timeout=180.0)  # 3 minutes
        self.llm = ChatOpenAI(
            model=model, 
            temperature=temperature,
            http_client=http_client,
            request_timeout=180.0
        )
    
    def retrieve_context(self, query: str) -> str:
        """
        Retrieve domain-specific context using RAG.
        
        This is the agent's "superpower" - access to domain-specific knowledge.
        """
        results = self.retriever.invoke(query)
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

