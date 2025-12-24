# Database Organization: Domain-Specific Knowledge Bases

## Overview

Each agent needs its own **focused knowledge base** (domain-specific RAG index). This document explains how to organize data files and vector databases so each agent only accesses relevant information.

---

## 1. Data File Organization

### Current Structure (Already Good!)

Your `data/` folder is already well-organized:

```
data/
├── Academic & Studies/
│   ├── Academic Programs/          → Programs Agent
│   │   ├── Biological Science/
│   │   ├── Business Administration/
│   │   ├── Computer Science and Artificial Intelligence/
│   │   ├── Information Systems/
│   │   └── Minors/
│   ├── Academic Resource Center/   → Programs Agent
│   ├── Courses/                    → Courses Agent (4736 JSON files)
│   ├── Exams and grading policies/ → Policy Agent
│   ├── Registration/               → Policy Agent
│   └── Research/                   → Opportunities Agent (future)
│
└── Your Life/
    ├── Career Development/         → Opportunities Agent (future)
    ├── Student Travel/             → Opportunities Agent (future)
    └── ...
```

### Mapping: Data Folders → Agents

| Agent | Data Folders | Purpose |
|-------|-------------|---------|
| **Programs & Requirements** | `Academic Programs/`<br>`Academic Resource Center/`<br>`Minors/` | Major/minor requirements, degree structure |
| **Course & Scheduling** | `Courses/` (4736 JSON files) | Course info, schedules, offerings |
| **Policy & Compliance** | `Exams and grading policies/`<br>`Registration/` | University policies, compliance rules |
| **Opportunities** (future) | `Research/`<br>`Career Development/`<br>`Student Travel/` | Research, career, travel opportunities |

---

## 2. Vector Database Organization

### Separate Vector Databases per Domain

**Key Principle:** Each agent has its own vector database, built from its domain-specific data.

```
chroma_db/
├── chroma_db_programs/          # Programs Agent's knowledge base
│   ├── chroma.sqlite3
│   └── [vector data]
│
├── chroma_db_courses/           # Courses Agent's knowledge base
│   ├── chroma.sqlite3
│   └── [vector data]
│
└── chroma_db_policies/          # Policy Agent's knowledge base
    ├── chroma.sqlite3
    └── [vector data]
```

### Why Separate Databases?

1. **Focused Retrieval**: Each agent only searches its domain
2. **Better Performance**: Smaller indexes = faster retrieval
3. **Easier Maintenance**: Update one domain without affecting others
4. **Research Ablations**: Can test with/without specific domains
5. **Token Efficiency**: Only relevant information retrieved

---

## 3. RAG Engine Configuration

**File: `rag_engine_improved.py`**

```python
"""
Domain-Specific RAG Engine
Each domain gets its own vector database.
"""

# ============================================================================
# DOMAIN MAPPING: Data Folders → Domain Names
# ============================================================================

DOMAIN_PATHS = {
    "programs": [
        # Programs & Requirements Agent
        "Academic & Studies/Academic Programs",  # All majors, minors
        "Academic & Studies/Academic Resource Center"
    ],
    
    "courses": [
        # Course & Scheduling Agent
        "Academic & Studies/Courses"  # All 4736 course JSON files
    ],
    
    "policies": [
        # Policy & Compliance Agent
        "Academic & Studies/Exams and grading policies",
        "Academic & Studies/Registration"
    ],
    
    "opportunities": [
        # Opportunities Agent (future)
        "Academic & Studies/Research",
        "Your Life/Career Development",
        "Your Life/Student Travel"
    ]
}

# ============================================================================
# VECTOR DATABASE PATHS
# ============================================================================

BASE_DB_PATH = "./chroma_db"

def get_db_path(domain: Optional[str] = None) -> str:
    """
    Get vector database path for a domain.
    
    Args:
        domain: Domain name (e.g., "programs", "courses", "policies")
                If None, returns base path (for general/all domains)
    
    Returns:
        Path to domain-specific vector database
    """
    if domain:
        return f"{BASE_DB_PATH}_{domain}"
    return BASE_DB_PATH

# Example:
# get_db_path("programs") → "./chroma_db_programs"
# get_db_path("courses") → "./chroma_db_courses"
# get_db_path("policies") → "./chroma_db_policies"
```

---

## 4. Building Domain-Specific Indexes

### Step-by-Step Process

**1. Load Domain-Specific Documents**

```python
def load_domain_documents(domain: str) -> List[Document]:
    """
    Load documents for a specific domain.
    
    Args:
        domain: Domain name ("programs", "courses", "policies")
    
    Returns:
        List of Document objects for this domain
    """
    if domain not in DOMAIN_PATHS:
        raise ValueError(f"Unknown domain: {domain}")
    
    all_docs = []
    base_path = "./data"
    
    for relative_path in DOMAIN_PATHS[domain]:
        full_path = os.path.join(base_path, relative_path)
        docs = load_documents_from_path(full_path, domain=domain)
        all_docs.extend(docs)
    
    return all_docs
```

**2. Create Domain-Specific Vector Database**

```python
def build_domain_index(domain: str, force_rebuild: bool = False):
    """
    Build vector database for a specific domain.
    
    Args:
        domain: Domain name
        force_rebuild: If True, rebuild even if database exists
    """
    db_path = get_db_path(domain)
    
    # Check if database exists
    if os.path.exists(db_path) and os.listdir(db_path) and not force_rebuild:
        print(f"✅ Domain '{domain}' database already exists at {db_path}")
        return
    
    print(f"🔨 Building vector database for domain: {domain}")
    
    # 1. Load documents
    documents = load_domain_documents(domain)
    print(f"   Loaded {len(documents)} documents")
    
    if not documents:
        print(f"   ⚠️  No documents found for domain '{domain}'")
        return
    
    # 2. Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = splitter.split_documents(documents)
    print(f"   Created {len(chunks)} chunks")
    
    # 3. Create embeddings and store
    embedding_model = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding_function=embedding_model,
        persist_directory=db_path
    )
    
    print(f"✅ Domain '{domain}' database created at {db_path}")
    print(f"   Total chunks: {len(chunks)}")
```

**3. Build All Domain Indexes**

```python
def build_all_domain_indexes(force_rebuild: bool = False):
    """Build vector databases for all domains."""
    for domain in DOMAIN_PATHS.keys():
        print(f"\n{'='*60}")
        print(f"Building index for domain: {domain}")
        print('='*60)
        build_domain_index(domain, force_rebuild=force_rebuild)
```

---

## 5. Agent Access Pattern

### How Agents Access Their Knowledge Base

**In `agents/base_agent.py`:**

```python
class BaseAgent(ABC):
    def __init__(self, name: str, domain: str):
        self.name = name
        self.domain = domain
        
        # Each agent gets its own domain-specific retriever
        self.retriever = get_retriever(domain=domain, k=5)
        # This automatically:
        # - Loads the correct vector database (chroma_db_{domain})
        # - Only searches within that domain's documents
        # - Returns domain-specific results
```

**Example:**

```python
# Programs Agent
programs_agent = ProgramsRequirementsAgent()
# → Uses chroma_db_programs
# → Only searches: Academic Programs, Academic Resource Center

# Courses Agent  
courses_agent = CourseSchedulingAgent()
# → Uses chroma_db_courses
# → Only searches: Courses folder (4736 JSON files)

# Policy Agent
policy_agent = PolicyComplianceAgent()
# → Uses chroma_db_policies
# → Only searches: Exams/grading policies, Registration
```

---

## 6. Complete RAG Engine Implementation

**File: `rag_engine_improved.py` (Updated)**

```python
"""
Improved RAG Engine with Domain-Specific Indexes
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

# Domain-specific paths (maps domain → data folders)
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
    ],
    "opportunities": [
        "Academic & Studies/Research",
        "Your Life/Career Development",
        "Your Life/Student Travel"
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
    """Convert JSON file to readable text."""
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
    """
    Load all documents for a specific domain.
    
    Args:
        domain: Domain name ("programs", "courses", "policies")
    
    Returns:
        List of Document objects
    """
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
        domain: Domain name (None = all domains, not recommended)
        k: Number of documents to retrieve
    
    Returns:
        Retriever instance for the domain
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
    """
    Build vector database for a specific domain.
    
    Args:
        domain: Domain name
        force_rebuild: If True, rebuild even if exists
    """
    db_path = get_db_path(domain)
    
    if os.path.exists(db_path) and os.listdir(db_path) and not force_rebuild:
        print(f"✅ Domain '{domain}' database already exists")
        return
    
    # Delete old database if rebuilding
    if force_rebuild and os.path.exists(db_path):
        import shutil
        shutil.rmtree(db_path)
        print(f"🗑️  Deleted old database for domain '{domain}'")
    
    # Build new database
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

def get_domain_retrievers(k: int = 5) -> Dict[str, any]:
    """
    Get retrievers for all domains.
    
    Returns:
        Dictionary mapping domain names to retrievers
    """
    retrievers = {}
    for domain in DOMAIN_PATHS.keys():
        retrievers[domain] = get_retriever(domain=domain, k=k)
    return retrievers

# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test: Build all indexes
    print("Building all domain indexes...")
    build_all_domain_indexes(force_rebuild=False)
    
    # Test: Get retrievers
    print("\n" + "=" * 70)
    print("Testing Domain-Specific Retrievers")
    print("=" * 70)
    
    test_queries = {
        "programs": "What are the IS major requirements?",
        "courses": "When is 15-112 offered?",
        "policies": "What is the course overload policy?"
    }
    
    for domain, query in test_queries.items():
        print(f"\n🔍 Domain: {domain}")
        print(f"   Query: {query}")
        retriever = get_retriever(domain=domain, k=3)
        results = retriever.invoke(query)
        print(f"   ✅ Retrieved {len(results)} documents")
        for i, doc in enumerate(results[:2], 1):
            source = doc.metadata.get('source', 'Unknown')
            if len(source) > 60:
                source = "..." + source[-57:]
            print(f"      {i}. {source}")
```

---

## 7. Setup Script

**File: `setup_domain_indexes.py`**

```python
"""
Setup script to build all domain-specific indexes.
Run this once to set up all agent knowledge bases.
"""
from rag_engine_improved import build_all_domain_indexes

if __name__ == "__main__":
    print("=" * 70)
    print("Setting Up Domain-Specific Knowledge Bases")
    print("=" * 70)
    print("\nThis will create separate vector databases for each agent.")
    print("Each agent will have its own focused knowledge base.\n")
    
    response = input("Rebuild existing indexes? (y/n): ").strip().lower()
    force_rebuild = (response == 'y')
    
    build_all_domain_indexes(force_rebuild=force_rebuild)
    
    print("\n" + "=" * 70)
    print("✅ Setup Complete!")
    print("=" * 70)
    print("\nDomain indexes created:")
    print("  - chroma_db_programs/   (Programs & Requirements Agent)")
    print("  - chroma_db_courses/    (Course & Scheduling Agent)")
    print("  - chroma_db_policies/   (Policy & Compliance Agent)")
    print("\nEach agent will automatically use its domain-specific index.")
```

---

## 8. Verification & Testing

### Verify Domain Separation

```python
# Test that each agent only retrieves from its domain

# Programs Agent
programs_retriever = get_retriever(domain="programs", k=5)
results = programs_retriever.invoke("course overload policy")
# Should NOT find policy documents (they're in policies domain)

# Policy Agent
policy_retriever = get_retriever(domain="policies", k=5)
results = policy_retriever.invoke("course overload policy")
# SHOULD find policy documents
```

### Check Database Sizes

```python
import os

def check_domain_sizes():
    """Check size of each domain database."""
    for domain in ["programs", "courses", "policies"]:
        db_path = f"./chroma_db_{domain}"
        if os.path.exists(db_path):
            # Count files or check size
            files = os.listdir(db_path)
            print(f"{domain}: {len(files)} files")
```

---

## 9. Best Practices

### ✅ DO:

1. **Separate Databases**: One vector DB per domain
2. **Clear Domain Mapping**: Document which folders belong to which domain
3. **Metadata Tagging**: Tag documents with domain in metadata
4. **Incremental Updates**: Rebuild only changed domains
5. **Version Control**: Track which data version each index was built from

### ❌ DON'T:

1. **Mix Domains**: Don't put programs data in courses database
2. **Duplicate Data**: Don't store same document in multiple domains
3. **Overlap Unnecessarily**: Keep domains focused and distinct
4. **Rebuild Everything**: Only rebuild changed domains

---

## 10. Maintenance

### Updating a Domain

```python
# If you add new documents to a domain:
# 1. Add files to the appropriate data folder
# 2. Rebuild that domain's index

from rag_engine_improved import build_domain_index

# Rebuild only programs domain
build_domain_index("programs", force_rebuild=True)
```

### Adding a New Domain

```python
# 1. Add domain to DOMAIN_PATHS
DOMAIN_PATHS["new_domain"] = ["path/to/data"]

# 2. Build index
build_domain_index("new_domain")

# 3. Create agent that uses it
class NewAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="new_agent", domain="new_domain")
```

---

## Summary

### Database Organization:

```
Data Files (Source):
data/
├── Academic & Studies/Academic Programs/  → Programs Agent
├── Academic & Studies/Courses/             → Courses Agent
└── Academic & Studies/Registration/          → Policy Agent

Vector Databases (Indexes):
chroma_db/
├── chroma_db_programs/    → Programs Agent's knowledge base
├── chroma_db_courses/     → Courses Agent's knowledge base
└── chroma_db_policies/    → Policy Agent's knowledge base
```

### Key Benefits:

1. **Focused Retrieval**: Each agent only searches relevant documents
2. **Better Performance**: Smaller indexes = faster searches
3. **Clear Separation**: Easy to understand what each agent knows
4. **Easy Maintenance**: Update one domain without affecting others
5. **Research Ready**: Can test ablations (with/without domains)

### Implementation:

1. Run `setup_domain_indexes.py` to build all indexes
2. Each agent automatically uses its domain-specific retriever
3. No code changes needed - agents just specify their domain

This organization ensures each agent has a focused, efficient knowledge base!

