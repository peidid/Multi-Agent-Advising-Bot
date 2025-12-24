# Full Implementation Guide: Dynamic Multi-Agent System
## Beginner-Friendly Step-by-Step Guide

This guide provides complete, ready-to-use code to build your dynamic multi-agent academic advising system. Follow each step sequentially.

---

## Prerequisites Checklist

Before starting, make sure you have:
- [ ] Python 3.10+ installed
- [ ] Anaconda/Conda environment set up
- [ ] OpenAI API key (in `.env` file)
- [ ] Your `data/` folder with academic documents
- [ ] Basic Python knowledge (classes, functions, imports)

---

## Table of Contents

1. [Project Setup](#1-project-setup)
2. [Database Setup (Domain-Specific Indexes)](#2-database-setup-domain-specific-indexes)
3. [Blackboard Schema](#3-blackboard-schema-structured-state)
4. [RAG Engine Setup](#4-rag-engine-setup)
5. [Base Agent Implementation](#5-base-agent-implementation)
6. [Programs & Requirements Agent](#6-programs--requirements-agent)
7. [Course & Scheduling Agent](#7-course--scheduling-agent)
8. [Policy & Compliance Agent](#8-policy--compliance-agent)
9. [Coordinator Implementation](#9-coordinator-implementation)
10. [Negotiation Protocol](#10-negotiation-protocol)
11. [LangGraph Workflow](#11-langgraph-workflow)
12. [Testing & Verification](#12-testing--verification)

---

## 1. Project Setup

### Step 1.1: Create Directory Structure

**In Anaconda Prompt:**
```bash
cd E:\CMU\Research\AdvisingBot\Product

# Create folders
mkdir agents
mkdir coordinator
mkdir blackboard

# Create __init__.py files (makes them Python packages)
echo. > agents\__init__.py
echo. > coordinator\__init__.py
echo. > blackboard\__init__.py
```

**Or manually:**
- Create folders: `agents/`, `coordinator/`, `blackboard/`
- Create empty files: `agents/__init__.py`, `coordinator/__init__.py`, `blackboard/__init__.py`

**Final Structure:**
```
Product/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py
│   ├── programs_agent.py
│   ├── courses_agent.py
│   └── policy_agent.py
│
├── coordinator/
│   ├── __init__.py
│   └── coordinator.py
│
├── blackboard/
│   ├── __init__.py
│   └── schema.py
│
├── data/                    # ✅ Already exists
├── rag_engine_improved.py   # Will create/update
├── course_tools.py          # ✅ Already exists
├── multi_agent.py          # Main workflow (will create)
├── setup_domain_indexes.py # Setup script (will create)
└── requirements.txt        # ✅ Already exists
```

### Step 1.2: Verify Requirements

**File: `requirements.txt`** (update if needed)
```txt
langchain>=0.1.0
langchain-openai>=0.0.5
langchain-community>=0.0.20
langgraph>=0.0.20
chromadb>=0.4.0
openai>=1.0.0
python-dotenv>=1.0.0
pydantic>=2.0.0
```

**Install:**
```bash
conda activate advisingbot
pip install -r requirements.txt
```

### Step 1.3: Verify .env File

Make sure you have `.env` file with:
```
OPENAI_API_KEY=your_api_key_here
```

---

## 2. Database Setup (Domain-Specific Indexes)

**CRITICAL FIRST STEP:** Build separate vector databases for each agent domain.

### Step 2.1: Update RAG Engine

**File: `rag_engine_improved.py`** (Complete implementation)

```python
"""
Domain-Specific RAG Engine
Each agent gets its own focused knowledge base (vector database).
"""
import os
import json
from typing import List, Optional, Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_PATH = "./data"
BASE_DB_PATH = "./chroma_db"
EMBEDDING_MODEL = OpenAIEmbeddings()

# Domain mapping: Domain name → Data folders
DOMAIN_PATHS = {
    "programs": [
        "Academic & Studies/Academic Programs",
        "Academic & Studies/Academic Resource Center"
    ],
    "courses": [
        "Academic & Studies/Courses"
    ],
    "policies": [
        "Academic & Studies/Exams and grading policies",
        "Academic & Studies/Registration"
    ]
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_db_path(domain: Optional[str] = None) -> str:
    """Get vector database path for a domain."""
    if domain:
        return f"{BASE_DB_PATH}_{domain}"
    return BASE_DB_PATH

def load_json_as_text(file_path: str) -> str:
    """Convert JSON file to readable text for RAG."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            text_parts = []
            for item in data:
                if isinstance(item, dict):
                    parts = []
                    for key, value in item.items():
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value, ensure_ascii=False)
                        parts.append(f"{key}: {value}")
                    text_parts.append("\n".join(parts))
            return "\n\n".join(text_parts)
        elif isinstance(data, dict):
            parts = []
            for key, value in data.items():
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, ensure_ascii=False)
                parts.append(f"{key}: {value}")
            return "\n".join(parts)
        else:
            return str(data)
    except Exception as e:
        print(f"Warning: Could not load JSON {file_path}: {e}")
        return ""

def load_documents_from_path(data_path: str, domain: str = "general") -> List[Document]:
    """Load documents from a path, handling both .md and .json files."""
    documents = []
    
    if not os.path.exists(data_path):
        print(f"Warning: Path {data_path} does not exist")
        return documents
    
    # Load markdown files
    try:
        md_loader = DirectoryLoader(
            data_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={'encoding': 'utf-8'},
            recursive=True
        )
        md_docs = md_loader.load()
        
        # Add metadata
        for doc in md_docs:
            doc.metadata['domain'] = domain
            doc.metadata['file_type'] = 'markdown'
            path_parts = doc.metadata.get('source', '').split(os.sep)
            if len(path_parts) > 1:
                doc.metadata['category'] = path_parts[-2]
        
        documents.extend(md_docs)
        print(f"   Loaded {len(md_docs)} markdown files")
    except Exception as e:
        print(f"Error loading markdown files: {e}")
    
    # Load JSON files
    try:
        json_files = []
        for root, dirs, files in os.walk(data_path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
        
        for json_file in json_files:
            try:
                text_content = load_json_as_text(json_file)
                if text_content:
                    doc = Document(
                        page_content=text_content,
                        metadata={
                            'source': json_file,
                            'domain': domain,
                            'file_type': 'json',
                            'category': os.path.basename(os.path.dirname(json_file))
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                print(f"Error processing JSON {json_file}: {e}")
        
        print(f"   Loaded {len(json_files)} JSON files")
    except Exception as e:
        print(f"Error loading JSON files: {e}")
    
    return documents

def load_domain_documents(domain: str) -> List[Document]:
    """Load all documents for a specific domain."""
    if domain not in DOMAIN_PATHS:
        raise ValueError(f"Unknown domain: {domain}. Available: {list(DOMAIN_PATHS.keys())}")
    
    all_docs = []
    
    for relative_path in DOMAIN_PATHS[domain]:
        full_path = os.path.join(DATA_PATH, relative_path)
        docs = load_documents_from_path(full_path, domain=domain)
        all_docs.extend(docs)
    
    return all_docs

# ============================================================================
# MAIN RETRIEVER FUNCTION
# ============================================================================

def get_retriever(domain: Optional[str] = None, k: int = 5):
    """
    Get retriever for a specific domain.
    
    Args:
        domain: Domain name ("programs", "courses", "policies")
        k: Number of documents to retrieve
    
    Returns:
        Retriever instance
    """
    db_path = get_db_path(domain)
    
    # Check if database exists
    if os.path.exists(db_path) and os.listdir(db_path):
        print(f"📚 Loading domain '{domain}' database from {db_path}")
        vectorstore = Chroma(
            persist_directory=db_path,
            embedding_function=EMBEDDING_MODEL
        )
        return vectorstore.as_retriever(search_kwargs={"k": k})
    
    # Build new database
    print(f"🔨 Building domain '{domain}' database...")
    
    if domain not in DOMAIN_PATHS:
        print(f"⚠️  Unknown domain: {domain}")
        return Chroma(embedding_function=EMBEDDING_MODEL).as_retriever(search_kwargs={"k": k})
    
    # Load domain-specific documents
    documents = load_domain_documents(domain)
    
    if not documents:
        print(f"⚠️  No documents found for domain '{domain}'")
        return Chroma(embedding_function=EMBEDDING_MODEL).as_retriever(search_kwargs={"k": k})
    
    print(f"   Total documents: {len(documents)}")
    
    # Split documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    
    print(f"   Total chunks: {len(chunks)}")
    
    # Create vector store
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding_function=EMBEDDING_MODEL,
        persist_directory=db_path
    )
    
    print(f"✅ Domain '{domain}' database created at {db_path}")
    
    return vectorstore.as_retriever(search_kwargs={"k": k})

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def build_domain_index(domain: str, force_rebuild: bool = False):
    """Build vector database for a specific domain."""
    db_path = get_db_path(domain)
    
    if os.path.exists(db_path) and os.listdir(db_path) and not force_rebuild:
        print(f"✅ Domain '{domain}' database already exists")
        return
    
    if force_rebuild and os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)
        print(f"🗑️  Deleted old database for domain '{domain}'")
    
    retriever = get_retriever(domain=domain, k=5)
    print(f"✅ Domain '{domain}' index built successfully")

def build_all_domain_indexes(force_rebuild: bool = False):
    """Build all domain indexes."""
    print("=" * 70)
    print("Building All Domain-Specific Indexes")
    print("=" * 70)
    
    for domain in DOMAIN_PATHS.keys():
        print(f"\n📦 Domain: {domain}")
        print("-" * 70)
        build_domain_index(domain, force_rebuild=force_rebuild)
```

### Step 2.2: Create Setup Script

**File: `setup_domain_indexes.py`**

```python
"""
Setup Domain-Specific Knowledge Bases
Run this once to build all agent knowledge bases.
"""
from rag_engine_improved import build_all_domain_indexes, DOMAIN_PATHS
import os

def main():
    print("=" * 70)
    print("Domain-Specific Knowledge Base Setup")
    print("=" * 70)
    print("\nThis will create separate vector databases for each agent:")
    print("\n  📚 Programs Agent    → chroma_db_programs/")
    print("  📚 Courses Agent     → chroma_db_courses/")
    print("  📚 Policy Agent      → chroma_db_policies/")
    print("\nEach agent will have its own focused knowledge base.")
    
    # Check existing databases
    existing_domains = []
    for domain in DOMAIN_PATHS.keys():
        db_path = f"./chroma_db_{domain}"
        if os.path.exists(db_path) and os.listdir(db_path):
            existing_domains.append(domain)
    
    if existing_domains:
        print(f"\n⚠️  Found existing databases for: {', '.join(existing_domains)}")
        response = input("\nRebuild existing indexes? (y/n): ").strip().lower()
        force_rebuild = (response == 'y')
    else:
        print("\nNo existing databases found. Building new indexes...")
        force_rebuild = False
    
    print("\n" + "=" * 70)
    build_all_domain_indexes(force_rebuild=force_rebuild)
    
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
```

### Step 2.3: Build Domain Indexes

**Run this command:**
```bash
python setup_domain_indexes.py
```

**What happens:**
1. Creates `chroma_db_programs/` from Programs folders
2. Creates `chroma_db_courses/` from Courses folder  
3. Creates `chroma_db_policies/` from Policies folders

**Expected output:**
```
Building All Domain-Specific Indexes
======================================================================

📦 Domain: programs
----------------------------------------------------------------------
🔨 Building domain 'programs' database...
   Loaded X markdown files
   Loaded Y JSON files
   Total documents: Z
   Total chunks: W
✅ Domain 'programs' database created at ./chroma_db_programs
```

**Verify it worked:**
```python
# Test each domain
from rag_engine_improved import get_retriever

programs_retriever = get_retriever(domain="programs", k=3)
results = programs_retriever.invoke("IS major requirements")
print(f"Programs domain: Found {len(results)} documents")
```

---

## 3. Blackboard Schema (Structured State)

**Key Concept:** The Blackboard is like a shared whiteboard where agents write structured information (not free text).

**File: `blackboard/schema.py`**

```python
"""
Structured Blackboard Schema
Based on General Feedback Section 3.1: Shared State as structured data

This defines the "shared state" that agents read/write to.
Each field has a specific type and purpose.
"""
from typing import TypedDict, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

# ============================================================================
# ENUMS
# ============================================================================

class ConflictType(str, Enum):
    """Types of conflicts agents can detect"""
    HARD_VIOLATION = "hard_violation"  # Plan breaks policy (impossible)
    HIGH_RISK = "high_risk"           # Plan possible but risky
    TRADE_OFF = "trade_off"           # Multiple valid options

class WorkflowStep(str, Enum):
    """Current step in the workflow"""
    INITIAL = "initial"
    INTENT_CLASSIFICATION = "intent_classification"
    AGENT_EXECUTION = "agent_execution"
    NEGOTIATION = "negotiation"
    CONFLICT_RESOLUTION = "conflict_resolution"
    SYNTHESIS = "synthesis"
    COMPLETE = "complete"
    USER_INPUT = "user_input"

# ============================================================================
# PYDANTIC MODELS (Structured Data)
# ============================================================================

class Constraint(BaseModel):
    """A constraint (from policy, student, or finance)"""
    source: str = Field(description="'policy', 'student', or 'finance'")
    description: str
    hard: bool = Field(description="True if hard constraint, False if soft")
    policy_citation: Optional[str] = None

class Risk(BaseModel):
    """A risk identified by an agent"""
    type: str = Field(description="e.g., 'overload_risk', 'time_conflict'")
    severity: str = Field(description="'high', 'medium', or 'low'")
    description: str
    policy_citation: Optional[str] = None

class PlanOption(BaseModel):
    """A candidate plan option"""
    semesters: List[Dict[str, Any]] = Field(description="Semester-by-semester plan")
    courses: List[str] = Field(description="List of course codes")
    risks: List[Risk] = Field(default_factory=list)
    policy_citations: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str

class AgentOutput(BaseModel):
    """
    Structured output from each agent
    
    Each agent returns this structure (not free text).
    This makes it easy to:
    - Detect conflicts
    - Aggregate information
    - Debug issues
    """
    agent_name: str
    answer: str = Field(description="Agent's answer/response")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    relevant_policies: List[str] = Field(default_factory=list)
    risks: List[Risk] = Field(default_factory=list)
    constraints: List[Constraint] = Field(default_factory=list)
    plan_options: Optional[List[PlanOption]] = None

class Conflict(BaseModel):
    """A conflict detected between agents"""
    conflict_type: ConflictType
    affected_agents: List[str]
    description: str
    options: List[Dict[str, Any]] = Field(default_factory=list)

# ============================================================================
# BLACKBOARD STATE (TypedDict for LangGraph)
# ============================================================================

class BlackboardState(TypedDict):
    """
    Main Blackboard State - Structured Schema
    
    This is the "shared state" that flows through the LangGraph workflow.
    Agents read from and write to specific fields.
    """
    # Student Information
    student_profile: Optional[Dict[str, Any]]
    # Example: {"major": ["IS"], "minor": [], "gpa": 3.5, "completed_courses": ["15-110"], "flags": []}
    
    # User Intent
    user_goal: Optional[str]  # e.g., "add CS minor"
    user_query: str
    
    # Agent Outputs (Structured)
    agent_outputs: Dict[str, AgentOutput]
    # Key: agent_name (e.g., "programs_requirements")
    # Value: AgentOutput object
    
    # Constraints & Risks (Aggregated)
    constraints: List[Constraint]
    risks: List[Risk]
    
    # Plans & Options
    plan_options: List[PlanOption]
    
    # Conflict Resolution
    conflicts: List[Conflict]
    open_questions: List[str]  # Questions for user
    
    # Conversation History
    messages: List[Any]  # LangChain messages
    
    # Coordinator State
    active_agents: List[str]  # Which agents are currently active
    workflow_step: WorkflowStep  # Current step
    iteration_count: int  # For negotiation loops (max 3)
    next_agent: Optional[str]  # Next agent to execute
```

**Verify it works:**
```python
# Test the schema
from blackboard.schema import AgentOutput, Risk, Constraint

# Create a test AgentOutput
output = AgentOutput(
    agent_name="test_agent",
    answer="Test answer",
    confidence=0.8,
    relevant_policies=["policy1"],
    risks=[Risk(type="test", severity="low", description="Test risk")],
    constraints=[Constraint(source="policy", description="Test constraint", hard=True)]
)

print(f"Created: {output.agent_name} with confidence {output.confidence}")
```

---

## 4. RAG Engine Setup

**✅ Already done in Step 2!** The `rag_engine_improved.py` file is complete.

**Just verify it works:**
```python
from rag_engine_improved import get_retriever

# Test each domain
for domain in ["programs", "courses", "policies"]:
    retriever = get_retriever(domain=domain, k=3)
    results = retriever.invoke("test query")
    print(f"{domain}: {len(results)} documents")
```

---

## 5. Base Agent Implementation

**File: `agents/base_agent.py`**

```python
"""
Base Agent Class
All specialized agents inherit from this base class.
"""
from abc import ABC, abstractmethod
from langchain_openai import ChatOpenAI
from rag_engine_improved import get_retriever
from blackboard.schema import BlackboardState, AgentOutput

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
        
        # LLM for agent reasoning
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
    
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
```

**Test BaseAgent:**
```python
# This will fail (as expected) because execute() is abstract
from agents.base_agent import BaseAgent

# This is correct - you can't instantiate BaseAgent directly
# You need to create a subclass that implements execute()
```

---

## 6. Programs & Requirements Agent

**File: `agents/programs_agent.py`**

```python
"""
Programs & Requirements Agent

Responsibilities:
- Answer questions about major/minor requirements
- Check degree progress
- Validate plans
- PROPOSE semester-by-semester plans

Knowledge Base: chroma_db_programs/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint, PlanOption
from langchain_core.messages import SystemMessage
import json
import re

class ProgramsRequirementsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="programs_requirements",
            domain="programs"  # Uses chroma_db_programs/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Programs & Requirements agent.
        
        This agent PROPOSES plans (part of Proposal + Critique protocol).
        """
        # 1. Read from Blackboard
        user_query = state.get("user_query", "")
        user_goal = state.get("user_goal", "")
        student_profile = state.get("student_profile", {})
        constraints = state.get("constraints", [])
        
        # 2. Retrieve domain-specific context
        query_for_rag = f"{user_query} {user_goal}"
        context = self.retrieve_context(query_for_rag)
        
        # 3. Build prompt
        prompt = self._build_prompt(user_query, user_goal, student_profile, context, constraints)
        
        # 4. Call LLM
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        # 5. Parse and return structured output
        return self._parse_response(response.content)
    
    def _build_prompt(self, query: str, goal: str, profile: dict, context: str, constraints: list) -> str:
        """Build detailed prompt for Programs agent."""
        constraints_text = "\n".join([f"- {c.description}" for c in constraints]) if constraints else "None"
        profile_text = json.dumps(profile, indent=2) if profile else "Not provided"
        
        return f"""You are the Programs & Requirements Agent for CMU-Q.

Your Responsibilities:
1. Answer questions about major/minor requirements
2. Check degree progress
3. Validate whether plans satisfy requirements
4. PROPOSE semester-by-semester plans when asked

Student Profile: {profile_text}
User Goal: {goal}
User Query: {query}
Existing Constraints: {constraints_text}

Retrieved Context (from program requirements documents):
{context}

Instructions:
- Be specific and cite relevant policies
- If proposing a plan, provide semester-by-semester breakdown
- Identify any requirement violations or risks
- Provide confidence score (0.0-1.0)

Format your response as JSON:
{{
    "answer": "Your detailed answer",
    "confidence": 0.85,
    "relevant_policies": ["policy1", "policy2"],
    "risks": [
        {{"type": "overload_risk", "severity": "high", "description": "..."}}
    ],
    "constraints": [
        {{"source": "policy", "description": "...", "hard": true}}
    ],
    "plan_options": [
        {{
            "semesters": [
                {{"semester": "Fall 2026", "courses": ["15-112", "67-100"]}},
                {{"semester": "Spring 2027", "courses": ["15-121", "67-200"]}}
            ],
            "courses": ["15-112", "67-100", "15-121", "67-200"],
            "confidence": 0.8,
            "justification": "This plan satisfies all requirements..."
        }}
    ]
}}
"""
    
    def _parse_response(self, response_text: str) -> AgentOutput:
        """Parse LLM response into structured AgentOutput."""
        try:
            # Try to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Fallback
                data = {
                    "answer": response_text,
                    "confidence": 0.7,
                    "relevant_policies": [],
                    "risks": [],
                    "constraints": [],
                    "plan_options": []
                }
            
            # Convert to AgentOutput
            risks = [Risk(**r) for r in data.get("risks", [])]
            constraints = [Constraint(**c) for c in data.get("constraints", [])]
            plan_options = None
            if data.get("plan_options"):
                plan_options = [PlanOption(**p) for p in data["plan_options"]]
            
            return AgentOutput(
                agent_name=self.name,
                answer=data.get("answer", response_text),
                confidence=data.get("confidence", 0.8),
                relevant_policies=data.get("relevant_policies", []),
                risks=risks,
                constraints=constraints,
                plan_options=plan_options
            )
        except Exception as e:
            print(f"Error parsing Programs agent response: {e}")
            return AgentOutput(
                agent_name=self.name,
                answer=response_text,
                confidence=0.7,
                relevant_policies=[],
                risks=[],
                constraints=[]
            )
```

**Test Programs Agent:**
```python
from agents.programs_agent import ProgramsRequirementsAgent
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

agent = ProgramsRequirementsAgent()

state = {
    "user_query": "What are IS major requirements?",
    "student_profile": {"major": ["IS"]},
    "agent_outputs": {},
    "constraints": [],
    "risks": [],
    "plan_options": [],
    "conflicts": [],
    "open_questions": [],
    "messages": [HumanMessage(content="What are IS major requirements?")],
    "active_agents": [],
    "workflow_step": WorkflowStep.INITIAL,
    "iteration_count": 0,
    "next_agent": None,
    "user_goal": None
}

output = agent.execute(state)
print(f"Answer: {output.answer[:200]}...")
print(f"Confidence: {output.confidence}")
```

---

## 7. Course & Scheduling Agent

**File: `agents/courses_agent.py`**

```python
"""
Course & Scheduling Agent

Responsibilities:
- Find course offerings (semester, instructor)
- Check schedule conflicts
- Provide course availability info

Knowledge Base: chroma_db_courses/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk
from langchain_core.messages import SystemMessage
from course_tools import look_up_course_info, find_course_codes_in_text
import json

class CourseSchedulingAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="course_scheduling",
            domain="courses"  # Uses chroma_db_courses/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """Execute Course & Scheduling agent."""
        user_query = state.get("user_query", "")
        plan_options = state.get("plan_options", [])
        agent_outputs = state.get("agent_outputs", {})
        
        # Extract courses from plan or query
        courses = self._extract_courses(plan_options, user_query, agent_outputs)
        
        if not courses:
            return self._answer_general_question(user_query)
        
        # Check each course
        course_info = []
        risks = []
        
        for course_code in courses:
            # Get structured data
            course_data = look_up_course_info(course_code)
            
            # Get RAG context
            context = self.retrieve_context(f"course {course_code} offering schedule")
            
            course_info.append({
                "code": course_code,
                "data": course_data,
                "context": context
            })
        
        # Build prompt and call LLM
        prompt = self._build_prompt(user_query, course_info, risks)
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=risks,
            constraints=[]
        )
    
    def _extract_courses(self, plan_options: list, query: str, agent_outputs: dict) -> list:
        """Extract course codes from various sources."""
        courses = set()
        
        # From query
        courses.update(find_course_codes_in_text(query))
        
        # From plan options
        for plan in plan_options:
            if isinstance(plan, dict):
                courses.update(plan.get("courses", []))
            elif hasattr(plan, "courses"):
                courses.update(plan.courses)
        
        # From Programs agent output
        programs_output = agent_outputs.get("programs_requirements")
        if programs_output and programs_output.plan_options:
            for plan_option in programs_output.plan_options:
                courses.update(plan_option.courses)
        
        return list(courses)
    
    def _answer_general_question(self, query: str) -> AgentOutput:
        """Answer general course questions."""
        context = self.retrieve_context(query)
        prompt = f"""You are the Course & Scheduling Agent.

Query: {query}
Context: {context}

Answer questions about course offerings, schedules, and availability.
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.8,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
    
    def _build_prompt(self, query: str, course_info: list, risks: list) -> str:
        """Build prompt for course checking."""
        courses_text = json.dumps(course_info, indent=2)
        return f"""You are the Course & Scheduling Agent.

Query: {query}

Courses to Check:
{courses_text}

Provide:
- Course offering details
- Schedule information
- Any conflicts or constraints
- Availability status
"""
```

---

## 8. Policy & Compliance Agent

**File: `agents/policy_agent.py`**

```python
"""
Policy & Compliance Agent

Responsibilities:
- Check plan compliance with policies
- Identify violations
- CRITIQUE plans proposed by Programs agent

Knowledge Base: chroma_db_policies/
"""
from agents.base_agent import BaseAgent
from blackboard.schema import BlackboardState, AgentOutput, Risk, Constraint
from langchain_core.messages import SystemMessage
import json
import re

class PolicyComplianceAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="policy_compliance",
            domain="policies"  # Uses chroma_db_policies/
        )
    
    def execute(self, state: BlackboardState) -> AgentOutput:
        """
        Execute Policy & Compliance agent.
        
        This agent CRITIQUES plans (part of Proposal + Critique protocol).
        """
        user_query = state.get("user_query", "")
        agent_outputs = state.get("agent_outputs", {})
        student_profile = state.get("student_profile", {})
        
        # Check if we need to critique a plan
        programs_output = agent_outputs.get("programs_requirements")
        has_plan = (
            programs_output and 
            programs_output.plan_options and 
            len(programs_output.plan_options) > 0
        )
        
        if has_plan:
            return self._critique_plan(programs_output.plan_options[0], student_profile)
        else:
            return self._answer_policy_question(user_query)
    
    def _critique_plan(self, plan_option, student_profile: dict) -> AgentOutput:
        """Critique a proposed plan for policy compliance."""
        context = self.retrieve_context(
            "overload limits probation rules course repeat policies registration deadlines"
        )
        
        prompt = f"""You are the Policy & Compliance Agent for CMU-Q.

Your role: CRITIQUE proposed plans for policy compliance.

Student Profile: {json.dumps(student_profile, indent=2)}

Proposed Plan:
Semesters: {json.dumps(plan_option.semesters, indent=2)}
Courses: {plan_option.courses}
Justification: {plan_option.justification}

Retrieved Policies:
{context}

Check compliance with:
1. Overload limits (max units per semester)
2. Probation rules
3. Course repeat policies
4. Registration deadlines
5. Prerequisites

For each violation or risk, provide:
- Type of violation/risk
- Severity (high/medium/low)
- Policy citation
- Suggested modification

Format as JSON:
{{
    "answer": "Your critique",
    "confidence": 0.9,
    "relevant_policies": ["policy1"],
    "risks": [
        {{"type": "overload_risk", "severity": "high", "description": "...", "policy_citation": "..."}}
    ],
    "constraints": [
        {{"source": "policy", "description": "...", "hard": true, "policy_citation": "..."}}
    ]
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return self._parse_response(response.content)
    
    def _answer_policy_question(self, query: str) -> AgentOutput:
        """Answer general policy questions."""
        context = self.retrieve_context(query)
        prompt = f"""You are the Policy & Compliance Agent.

Query: {query}

Retrieved Policies:
{context}

Answer questions about university policies, compliance, and regulations.
"""
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return AgentOutput(
            agent_name=self.name,
            answer=response.content,
            confidence=0.9,
            relevant_policies=[],
            risks=[],
            constraints=[]
        )
    
    def _parse_response(self, response_text: str) -> AgentOutput:
        """Parse critique response."""
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = {"answer": response_text, "confidence": 0.8, "relevant_policies": [], "risks": [], "constraints": []}
            
            risks = [Risk(**r) for r in data.get("risks", [])]
            constraints = [Constraint(**c) for c in data.get("constraints", [])]
            
            return AgentOutput(
                agent_name=self.name,
                answer=data.get("answer", response_text),
                confidence=data.get("confidence", 0.8),
                relevant_policies=data.get("relevant_policies", []),
                risks=risks,
                constraints=constraints
            )
        except Exception as e:
            print(f"Error parsing Policy agent response: {e}")
            return AgentOutput(
                agent_name=self.name,
                answer=response_text,
                confidence=0.7,
                relevant_policies=[],
                risks=[],
                constraints=[]
            )
```

---

## 9. Coordinator Implementation

**File: `coordinator/coordinator.py`**

```python
"""
Coordinator / Orchestrator

Key Responsibilities:
- Intent classification & routing
- Workflow planning (dynamic)
- Conflict detection
- Negotiation management
- Answer synthesis
"""
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from blackboard.schema import (
    BlackboardState, Conflict, ConflictType, WorkflowStep, AgentOutput
)
import json
import re

class Coordinator:
    """Main orchestrator for multi-agent system."""
    
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0.3)
        self.available_agents = [
            "programs_requirements",
            "course_scheduling",
            "policy_compliance"
        ]
    
    def classify_intent(self, query: str) -> Dict[str, Any]:
        """
        Classify user intent to determine which agents are needed.
        """
        prompt = f"""Classify this academic advising query and determine which agents are needed.

Query: {query}

Available Agents:
- programs_requirements: For major/minor requirements, degree progress, plan validation
- course_scheduling: For course offerings, schedules, time conflicts
- policy_compliance: For university policies, compliance checking

Intent Types:
- check_requirements: Questions about requirements
- plan_semester: Planning courses for a semester
- add_minor: Adding a minor
- policy_question: Questions about policies
- validate_plan: Checking if a plan is valid
- general: General advising questions

Respond in JSON format:
{{
    "intent_type": "check_requirements" | "plan_semester" | "add_minor" | "policy_question" | "validate_plan" | "general",
    "required_agents": ["agent1", "agent2"],
    "priority": "high" | "medium" | "low",
    "reasoning": "Why these agents are needed"
}}
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        
        try:
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback
        return {
            "intent_type": "general",
            "required_agents": ["programs_requirements"],
            "priority": "medium",
            "reasoning": "Default fallback"
        }
    
    def plan_workflow(self, intent: Dict[str, Any]) -> List[str]:
        """
        Plan the workflow: which agents to call in what order.
        """
        required_agents = intent.get("required_agents", [])
        intent_type = intent.get("intent_type", "general")
        
        # Dynamic workflow planning
        if intent_type == "validate_plan" or intent_type == "plan_semester":
            # Full workflow: propose → check schedule → check compliance
            workflow = []
            if "programs_requirements" in required_agents:
                workflow.append("programs_requirements")
            if "course_scheduling" in required_agents:
                workflow.append("course_scheduling")
            if "policy_compliance" in required_agents:
                workflow.append("policy_compliance")
            return workflow
        elif intent_type == "add_minor":
            return [a for a in required_agents if a in ["programs_requirements", "policy_compliance"]]
        else:
            return required_agents
    
    def detect_conflicts(self, state: BlackboardState) -> List[Conflict]:
        """
        Detect conflicts between agent outputs.
        """
        agent_outputs = state.get("agent_outputs", {})
        conflicts = []
        
        # Check Policy agent for violations
        policy_output = agent_outputs.get("policy_compliance")
        if policy_output:
            hard_constraints = [c for c in policy_output.constraints if c.hard]
            high_risks = [r for r in policy_output.risks if r.severity == "high"]
            
            if hard_constraints:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HARD_VIOLATION,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"Plan violates policies: {[c.description for c in hard_constraints]}",
                    options=[]
                ))
            
            if high_risks:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HIGH_RISK,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"High-risk plan: {[r.description for r in high_risks]}",
                    options=[]
                ))
        
        # Check for trade-offs
        plan_options = state.get("plan_options", [])
        if len(plan_options) > 1:
            conflicts.append(Conflict(
                conflict_type=ConflictType.TRADE_OFF,
                affected_agents=["programs_requirements"],
                description="Multiple valid plan options available",
                options=[{"plan": p.dict()} for p in plan_options]
            ))
        
        return conflicts
    
    def synthesize_answer(self, state: BlackboardState) -> str:
        """Synthesize final answer from all agent outputs."""
        agent_outputs = state.get("agent_outputs", {})
        user_query = state.get("user_query", "")
        conflicts = state.get("conflicts", [])
        
        # Combine agent outputs
        agent_summaries = []
        for agent_name, output in agent_outputs.items():
            agent_summaries.append(f"""
{agent_name.upper()}:
Answer: {output.answer}
Confidence: {output.confidence}
Policies: {', '.join(output.relevant_policies)}
Risks: {len(output.risks)}
""")
        
        conflicts_text = ""
        if conflicts:
            conflicts_text = "\nConflicts Detected:\n"
            for conflict in conflicts:
                conflicts_text += f"- {conflict.conflict_type.value}: {conflict.description}\n"
        
        prompt = f"""You are the Coordinator synthesizing answers from multiple specialized agents.

User Query: {user_query}

Agent Outputs:
{chr(10).join(agent_summaries)}
{conflicts_text}

Synthesize a coherent, helpful answer that:
1. Combines relevant information from all agents
2. Addresses conflicts if any
3. Provides clear, actionable advice
4. Cites policies when relevant
5. Is professional and friendly

Write a comprehensive answer (2-4 paragraphs).
"""
        
        response = self.llm.invoke([SystemMessage(content=prompt)])
        return response.content
    
    def manage_negotiation(self, state: BlackboardState) -> Dict[str, Any]:
        """
        Manage Proposal + Critique Protocol.
        
        Protocol:
        1. Programs Agent proposes plan
        2. Policy Agent critiques plan
        3. If conflicts, loop (max 3 iterations)
        """
        iteration = state.get("iteration_count", 0)
        max_iterations = 3
        
        agent_outputs = state.get("agent_outputs", {})
        
        # Step 1: Check if Programs agent has proposed
        if "programs_requirements" not in agent_outputs:
            return {
                "next_agent": "programs_requirements",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 2: Check if Policy agent has critiqued
        if "policy_compliance" not in agent_outputs:
            return {
                "next_agent": "policy_compliance",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 3: Detect conflicts
        conflicts = self.detect_conflicts(state)
        
        if conflicts:
            has_hard_violation = any(c.conflict_type == ConflictType.HARD_VIOLATION for c in conflicts)
            
            if iteration >= max_iterations:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["The proposed plan has conflicts. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT
                }
            
            if has_hard_violation:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["This plan violates university policies. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT,
                    "iteration_count": iteration + 1
                }
            else:
                # Soft conflicts - try to resolve
                return {
                    "conflicts": conflicts,
                    "workflow_step": WorkflowStep.NEGOTIATION,
                    "next_agent": "programs_requirements",
                    "iteration_count": iteration + 1
                }
        
        # No conflicts - ready to synthesize
        return {
            "workflow_step": WorkflowStep.SYNTHESIS
        }
```

---

## 10. Negotiation Protocol

**✅ Already included in Coordinator!** See `manage_negotiation()` method above.

---

## 11. LangGraph Workflow

**File: `multi_agent.py`**

```python
"""
Main Multi-Agent Workflow
Implements dynamic routing with Coordinator managing agent execution.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage

from blackboard.schema import BlackboardState, WorkflowStep
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from coordinator.coordinator import Coordinator

# Initialize components
coordinator = Coordinator()
programs_agent = ProgramsRequirementsAgent()
courses_agent = CourseSchedulingAgent()
policy_agent = PolicyComplianceAgent()

# ============================================================================
# NODES
# ============================================================================

def coordinator_node(state: BlackboardState) -> Dict[str, Any]:
    """Coordinator node: Classifies intent, plans workflow."""
    user_query = state.get("user_query", "")
    workflow_step = state.get("workflow_step", WorkflowStep.INITIAL)
    
    if workflow_step == WorkflowStep.INITIAL:
        intent = coordinator.classify_intent(user_query)
        workflow = coordinator.plan_workflow(intent)
        
        return {
            "active_agents": workflow,
            "workflow_step": WorkflowStep.AGENT_EXECUTION,
            "next_agent": workflow[0] if workflow else None,
            "user_goal": intent.get("intent_type", "")
        }
    
    elif workflow_step == WorkflowStep.NEGOTIATION:
        negotiation_result = coordinator.manage_negotiation(state)
        return negotiation_result
    
    else:
        conflicts = coordinator.detect_conflicts(state)
        if conflicts:
            return {
                "conflicts": conflicts,
                "workflow_step": WorkflowStep.CONFLICT_RESOLUTION
            }
        else:
            return {
                "workflow_step": WorkflowStep.SYNTHESIS
            }

def programs_node(state: BlackboardState) -> Dict[str, Any]:
    """Programs agent execution."""
    output = programs_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["programs_requirements"] = output
    
    plan_options = []
    if output.plan_options:
        plan_options = output.plan_options
    
    return {
        "agent_outputs": agent_outputs,
        "plan_options": plan_options,
        "risks": state.get("risks", []) + output.risks,
        "constraints": state.get("constraints", []) + output.constraints
    }

def courses_node(state: BlackboardState) -> Dict[str, Any]:
    """Courses agent execution."""
    output = courses_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["course_scheduling"] = output
    
    return {
        "agent_outputs": agent_outputs,
        "risks": state.get("risks", []) + output.risks
    }

def policy_node(state: BlackboardState) -> Dict[str, Any]:
    """Policy agent execution."""
    output = policy_agent.execute(state)
    
    agent_outputs = state.get("agent_outputs", {})
    agent_outputs["policy_compliance"] = output
    
    return {
        "agent_outputs": agent_outputs,
        "risks": state.get("risks", []) + output.risks,
        "constraints": state.get("constraints", []) + output.constraints
    }

def synthesize_node(state: BlackboardState) -> Dict[str, Any]:
    """Synthesize final answer."""
    answer = coordinator.synthesize_answer(state)
    
    return {
        "messages": [HumanMessage(content=answer)],
        "workflow_step": WorkflowStep.COMPLETE
    }

# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_after_coordinator(state: BlackboardState) -> str:
    """Route after coordinator decides next step."""
    workflow_step = state.get("workflow_step")
    next_agent = state.get("next_agent")
    
    if workflow_step == WorkflowStep.SYNTHESIS:
        return "synthesize"
    elif workflow_step == WorkflowStep.USER_INPUT:
        return END
    elif next_agent == "programs_requirements":
        return "programs"
    elif next_agent == "course_scheduling":
        return "courses"
    elif next_agent == "policy_compliance":
        return "policy"
    else:
        return "synthesize"

def route_after_agent(state: BlackboardState) -> str:
    """Route after agent execution."""
    active_agents = state.get("active_agents", [])
    agent_outputs = state.get("agent_outputs", {})
    executed_agents = list(agent_outputs.keys())
    
    if len(executed_agents) >= len(active_agents):
        conflicts = state.get("conflicts", [])
        if conflicts:
            return "coordinator"
        else:
            return "synthesize"
    else:
        remaining = [a for a in active_agents if a not in executed_agents]
        if remaining:
            return "coordinator"
        else:
            return "synthesize"

# ============================================================================
# BUILD WORKFLOW
# ============================================================================

workflow = StateGraph(BlackboardState)

# Add nodes
workflow.add_node("coordinator", coordinator_node)
workflow.add_node("programs", programs_node)
workflow.add_node("courses", courses_node)
workflow.add_node("policy", policy_node)
workflow.add_node("synthesize", synthesize_node)

# Add edges
workflow.add_edge(START, "coordinator")
workflow.add_conditional_edges("coordinator", route_after_coordinator)
workflow.add_conditional_edges("programs", route_after_agent)
workflow.add_conditional_edges("courses", route_after_agent)
workflow.add_conditional_edges("policy", route_after_agent)
workflow.add_edge("synthesize", END)

# Compile
app = workflow.compile()

# ============================================================================
# USAGE
# ============================================================================

if __name__ == "__main__":
    initial_state = {
        "user_query": "Can I add a CS minor as an IS student?",
        "student_profile": {"major": ["IS"], "gpa": 3.5},
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "plan_options": [],
        "conflicts": [],
        "open_questions": [],
        "messages": [HumanMessage(content="Can I add a CS minor as an IS student?")],
        "active_agents": [],
        "workflow_step": WorkflowStep.INITIAL,
        "iteration_count": 0,
        "next_agent": None,
        "user_goal": None
    }
    
    result = app.invoke(initial_state)
    
    print("=" * 70)
    print("FINAL ANSWER:")
    print("=" * 70)
    print(result["messages"][-1].content)
    print("\n" + "=" * 70)
    print("AGENT OUTPUTS:")
    for agent_name, output in result.get("agent_outputs", {}).items():
        print(f"\n{agent_name}:")
        print(f"  Answer: {output.answer[:200]}...")
        print(f"  Confidence: {output.confidence}")
```

---

## 12. Testing & Verification

### Step 12.1: Test Each Component

**Test 1: Domain Indexes**
```python
from rag_engine_improved import get_retriever

# Test each domain
for domain in ["programs", "courses", "policies"]:
    retriever = get_retriever(domain=domain, k=3)
    results = retriever.invoke("test")
    print(f"{domain}: {len(results)} documents")
```

**Test 2: Blackboard Schema**
```python
from blackboard.schema import AgentOutput, Risk

output = AgentOutput(
    agent_name="test",
    answer="Test",
    confidence=0.8,
    relevant_policies=[],
    risks=[],
    constraints=[]
)
print("✅ Schema works!")
```

**Test 3: Each Agent**
```python
from agents.programs_agent import ProgramsRequirementsAgent
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

agent = ProgramsRequirementsAgent()
state = {
    "user_query": "What are IS requirements?",
    "student_profile": {},
    "agent_outputs": {},
    "constraints": [],
    "risks": [],
    "plan_options": [],
    "conflicts": [],
    "open_questions": [],
    "messages": [HumanMessage(content="test")],
    "active_agents": [],
    "workflow_step": WorkflowStep.INITIAL,
    "iteration_count": 0,
    "next_agent": None,
    "user_goal": None
}

output = agent.execute(state)
print(f"✅ Programs agent works! Answer: {output.answer[:100]}...")
```

**Test 4: Coordinator**
```python
from coordinator.coordinator import Coordinator

coordinator = Coordinator()
intent = coordinator.classify_intent("Can I add CS minor?")
print(f"✅ Coordinator works! Intent: {intent['intent_type']}")
print(f"   Required agents: {intent['required_agents']}")
```

**Test 5: Full Workflow**
```python
from multi_agent import app
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

state = {
    "user_query": "What are IS major requirements?",
    "student_profile": {},
    "agent_outputs": {},
    "constraints": [],
    "risks": [],
    "plan_options": [],
    "conflicts": [],
    "open_questions": [],
    "messages": [HumanMessage(content="What are IS major requirements?")],
    "active_agents": [],
    "workflow_step": WorkflowStep.INITIAL,
    "iteration_count": 0,
    "next_agent": None,
    "user_goal": None
}

result = app.invoke(state)
print("✅ Full workflow works!")
print(f"Answer: {result['messages'][-1].content[:200]}...")
```

### Step 12.2: Test Scenarios

**Scenario 1: Simple Query (One Agent)**
```python
query = "What are IS major requirements?"
# Expected: Only Programs agent runs
```

**Scenario 2: Multi-Agent Query**
```python
query = "Can I take 15-112, 15-121, and 67-100 next semester?"
# Expected: Programs → Courses → Policy → Synthesize
```

**Scenario 3: Plan with Conflicts**
```python
query = "I want to add CS minor as IS student"
# Expected: Programs proposes → Policy critiques → Negotiation → Synthesize
```

---

## Implementation Checklist

Follow this checklist in order:

- [ ] **Step 1**: Create directory structure
- [ ] **Step 2**: Build domain indexes (`python setup_domain_indexes.py`)
- [ ] **Step 3**: Create Blackboard schema
- [ ] **Step 4**: Verify RAG engine works
- [ ] **Step 5**: Create BaseAgent class
- [ ] **Step 6**: Implement Programs agent
- [ ] **Step 7**: Implement Courses agent
- [ ] **Step 8**: Implement Policy agent
- [ ] **Step 9**: Implement Coordinator
- [ ] **Step 10**: Create LangGraph workflow
- [ ] **Step 11**: Test each component
- [ ] **Step 12**: Test full workflow

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'rag_engine_improved'"

**Solution:**
- Make sure `rag_engine_improved.py` is in the project root
- Check your Python path

### Issue: "Domain database not found"

**Solution:**
- Run `python setup_domain_indexes.py` first
- Check that `chroma_db_{domain}/` folders exist

### Issue: "No documents found for domain"

**Solution:**
- Verify `data/` folder structure matches `DOMAIN_PATHS`
- Check file paths are correct

### Issue: "JSON parsing errors"

**Solution:**
- LLM might not return perfect JSON
- The fallback parser handles this
- Improve prompts for better JSON output

### Issue: "Workflow routing errors"

**Solution:**
- Check `workflow_step` values match `WorkflowStep` enum
- Verify routing functions return correct node names

---

## Key Principles

1. **Structured State**: Always use typed schema (Pydantic models)
2. **No Direct Communication**: Agents only via Blackboard
3. **Domain Separation**: Each agent has its own knowledge base
4. **Dynamic Routing**: Coordinator decides workflow
5. **Incremental Testing**: Test each component before integrating

---

## Next Steps After MVP

1. **Improve Structured Output**: Use LangChain's structured output parsers
2. **Add Error Handling**: Wrap all agent calls in try-except
3. **Add Logging**: Track execution for debugging
4. **Optimize Prompts**: Refine based on test results
5. **Add More Agents**: Student Profile, Opportunities agents
6. **UI Integration**: Build interactive interface

---

## Quick Start Summary

1. **Setup**: Create folders, install dependencies
2. **Build Indexes**: `python setup_domain_indexes.py`
3. **Create Schema**: `blackboard/schema.py`
4. **Create Agents**: One at a time, test each
5. **Create Coordinator**: Intent classification, workflow planning
6. **Create Workflow**: LangGraph integration
7. **Test**: Incrementally, then end-to-end

Start with Step 1 and work through sequentially. Each step builds on the previous one!
