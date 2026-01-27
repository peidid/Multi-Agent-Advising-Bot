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

# Use absolute paths based on this file's location (project root)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
BASE_DB_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

# Configure HTTP client with SSL verification disabled and longer timeout for embeddings
import httpx
http_client = httpx.Client(verify=False, timeout=180.0)  # 3 minutes
EMBEDDING_MODEL = OpenAIEmbeddings(
    http_client=http_client,
    request_timeout=180.0
)

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

def extract_course_codes(text: str) -> List[str]:
    """Extract course codes (e.g., 15-213, 67-250) from text."""
    import re
    pattern = r'\b\d{2}-\d{3,4}\b'
    return list(set(re.findall(pattern, text)))

def infer_program(file_path: str, content: str) -> Optional[str]:
    """Infer which program this document is about."""
    path_lower = file_path.lower()
    content_lower = content.lower()
    
    # Check path first
    if 'information systems' in path_lower or '/is/' in path_lower or '\\is\\' in path_lower:
        return 'Information Systems'
    if 'computer science' in path_lower or '/cs/' in path_lower or '\\cs\\' in path_lower:
        return 'Computer Science'
    if 'biological science' in path_lower or '/bio/' in path_lower or '\\bio\\' in path_lower:
        return 'Biological Sciences'
    if 'business administration' in path_lower or '/ba/' in path_lower or '\\ba\\' in path_lower:
        return 'Business Administration'
    
    # Check content
    program_keywords = {
        'Information Systems': ['information systems', 'is major', 'is student', 'is program'],
        'Computer Science': ['computer science', 'cs major', 'cs student', 'cs program'],
        'Biological Sciences': ['biological sciences', 'biology', 'bio major', 'bio student'],
        'Business Administration': ['business administration', 'ba major', 'ba student']
    }
    
    for program, keywords in program_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            return program
    
    return None

def infer_content_type(file_path: str, content: str) -> str:
    """Infer the type of content in this document."""
    path_lower = file_path.lower()
    content_lower = content.lower()
    
    # Check by folder structure
    if 'programs' in path_lower or 'program' in path_lower:
        if 'requirement' in path_lower or 'curriculum' in path_lower:
            return 'program_requirements'
        if 'concentration' in path_lower:
            return 'concentration_info'
        if 'sample' in path_lower:
            return 'sample_curriculum'
        return 'program_info'
    
    if 'courses' in path_lower or 'course' in path_lower:
        return 'course_description'
    
    if 'policies' in path_lower or 'policy' in path_lower:
        if 'registration' in path_lower:
            return 'registration_policy'
        if 'exam' in path_lower or 'grading' in path_lower:
            return 'exam_grading_policy'
        if 'finance' in path_lower:
            return 'financial_policy'
        if 'health' in path_lower or 'wellness' in path_lower:
            return 'health_policy'
        return 'general_policy'
    
    # Check by content
    if 'prerequisite' in content_lower or 'prereq' in content_lower:
        return 'course_prerequisites'
    if 'concentration' in content_lower and 'requirement' in content_lower:
        return 'concentration_requirements'
    if 'general education' in content_lower or 'gened' in content_lower:
        return 'gened_requirements'
    
    return 'general_info'

def generate_document_summary(data: any, file_name: str, file_type: str) -> str:
    """Generate a concise summary of what the document contains."""
    summaries = []
    
    if file_type == 'json':
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Check for common structures
            first_item = data[0]
            
            if 'Name' in first_item:
                # Requirements structure
                names = [item.get('Name', '')[:50] for item in data[:3]]
                summaries.append(f"Contains {len(data)} requirements")
                if names:
                    summaries.append(f"Examples: {', '.join(names)}")
            
            elif 'Concentration Name' in first_item:
                # Concentrations structure
                conc_names = [item.get('Concentration Name', '') for item in data]
                summaries.append(f"Describes {len(data)} concentrations: {', '.join(conc_names)}")
            
            elif 'course_id' in first_item:
                # Course structure
                course_id = first_item.get('course_id', '')
                course_name = first_item.get('long_title', first_item.get('short_title', ''))
                summaries.append(f"Course {course_id}: {course_name}")
                
                # Key information available
                if first_item.get('prereqs'):
                    summaries.append("Has prerequisites")
                if first_item.get('custom_fields', {}).get('assessment_structure'):
                    summaries.append("Has assessment structure")
                if first_item.get('custom_fields', {}).get('key_topics'):
                    summaries.append("Has key topics")
        
        elif isinstance(data, dict):
            if 'program' in data or 'Program' in data:
                program = data.get('program', data.get('Program', ''))
                summaries.append(f"Program info: {program}")
    
    elif file_type == 'markdown':
        # For markdown, extract title from content
        if isinstance(data, str):
            lines = data.split('\n')
            for line in lines[:10]:
                if line.strip().startswith('#'):
                    title = line.strip('#').strip()
                    summaries.append(title)
                    break
    
    if not summaries:
        summaries.append(os.path.basename(file_name))
    
    return " | ".join(summaries)

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
    """Load documents from a path, handling both .md and .json files with metadata."""
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
        
        # Add metadata and contextual prefix
        for doc in md_docs:
            # Generate metadata
            content_type = infer_content_type(doc.metadata['source'], doc.page_content)
            program = infer_program(doc.metadata['source'], doc.page_content)
            courses = extract_course_codes(doc.page_content)
            summary = generate_document_summary(doc.page_content, doc.metadata['source'], 'markdown')
            
            # Update metadata (convert list to string for Chroma compatibility)
            doc.metadata['domain'] = domain
            doc.metadata['file_type'] = 'markdown'
            doc.metadata['content_type'] = content_type
            doc.metadata['program'] = program if program else ''
            doc.metadata['courses_mentioned'] = ', '.join(courses) if courses else ''
            doc.metadata['summary'] = summary
            
            path_parts = doc.metadata.get('source', '').split(os.sep)
            if len(path_parts) > 1:
                doc.metadata['category'] = path_parts[-2]
            
            # Add contextual prefix to content
            file_name = os.path.basename(doc.metadata['source'])
            context_prefix = f"""[DOCUMENT CONTEXT]
File: {file_name}
Type: {content_type}"""
            
            if program:
                context_prefix += f"\nProgram: {program}"
            
            if courses:
                context_prefix += f"\nMentions courses: {', '.join(courses[:5])}"
                if len(courses) > 5:
                    context_prefix += f" (+{len(courses)-5} more)"
            
            context_prefix += f"\nSummary: {summary}\n\n[DOCUMENT CONTENT]\n"
            
            # Prepend context to content
            doc.page_content = context_prefix + doc.page_content
        
        documents.extend(md_docs)
        print(f"   Loaded {len(md_docs)} markdown files with metadata")
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
                # Load JSON to analyze it
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                text_content = load_json_as_text(json_file)
                
                if text_content:
                    # Generate metadata
                    content_type = infer_content_type(json_file, text_content)
                    program = infer_program(json_file, text_content)
                    courses = extract_course_codes(text_content)
                    summary = generate_document_summary(json_data, json_file, 'json')
                    
                    # Build contextual prefix
                    file_name = os.path.basename(json_file)
                    context_prefix = f"""[DOCUMENT CONTEXT]
File: {file_name}
Type: {content_type}"""
                    
                    if program:
                        context_prefix += f"\nProgram: {program}"
                    
                    if courses:
                        context_prefix += f"\nMentions courses: {', '.join(courses[:5])}"
                        if len(courses) > 5:
                            context_prefix += f" (+{len(courses)-5} more)"
                    
                    context_prefix += f"\nSummary: {summary}\n\n[DOCUMENT CONTENT]\n"
                    
                    # Create document with metadata (convert list to string for Chroma compatibility)
                    doc = Document(
                        page_content=context_prefix + text_content,
                        metadata={
                            'source': json_file,
                            'domain': domain,
                            'file_type': 'json',
                            'content_type': content_type,
                            'program': program if program else '',
                            'courses_mentioned': ', '.join(courses) if courses else '',
                            'summary': summary,
                            'category': os.path.basename(os.path.dirname(json_file))
                        }
                    )
                    documents.append(doc)
            except Exception as e:
                print(f"Error processing JSON {json_file}: {e}")
        
        print(f"   Loaded {len(json_files)} JSON files with metadata")
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