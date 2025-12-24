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
# NEW STRUCTURE: Each agent has its own folder for easier data management
DOMAIN_PATHS = {
    "programs": [
        "programs"  # All Programs Agent data in one folder
    ],
    "courses": [
        "courses"   # All Courses Agent data in one folder
    ],
    "policies": [
        "policies"   # All Policy Agent data in one folder
    ]
}

# LEGACY STRUCTURE (for backward compatibility if reorganization not done yet)
# Uncomment and comment out above if you haven't reorganized yet:
# DOMAIN_PATHS = {
#     "programs": [
#         "Academic & Studies/Academic Programs",
#         "Academic & Studies/Academic Resource Center"
#     ],
#     "courses": [
#         "Academic & Studies/Courses"
#     ],
#     "policies": [
#         "Academic & Studies/Exams and grading policies",
#         "Academic & Studies/Registration"
#     ]
# }

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
        embedding=EMBEDDING_MODEL,
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