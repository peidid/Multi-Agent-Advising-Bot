"""
Document Metadata Generator

This script analyzes documents in the data/ folder and generates metadata
to help agents better understand what information each document contains.

Metadata includes:
- Document summary
- Content type (requirements, course_info, policy, etc.)
- Key entities (programs, courses mentioned)
- Document purpose
"""

import os
import json
import re
from typing import Dict, List, Optional
from pathlib import Path

# ============================================================================
# METADATA EXTRACTION FUNCTIONS
# ============================================================================

def extract_course_codes(text: str) -> List[str]:
    """Extract course codes (e.g., 15-213, 67-250) from text."""
    # Pattern: XX-XXX or XX-XXXX
    pattern = r'\b\d{2}-\d{3,4}\b'
    return list(set(re.findall(pattern, text)))

def infer_program(file_path: str, content: str) -> Optional[str]:
    """Infer which program this document is about."""
    path_lower = file_path.lower()
    content_lower = content.lower()
    
    # Check path first
    if 'information systems' in path_lower or '/is/' in path_lower:
        return 'Information Systems'
    if 'computer science' in path_lower or 'cs' in path_lower or '/cs/' in path_lower:
        return 'Computer Science'
    if 'biological science' in path_lower or '/bio/' in path_lower:
        return 'Biological Sciences'
    if 'business administration' in path_lower or '/ba/' in path_lower:
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
    if 'programs' in path_lower:
        if 'requirement' in path_lower or 'curriculum' in path_lower:
            return 'program_requirements'
        if 'concentration' in path_lower:
            return 'concentration_info'
        if 'sample' in path_lower:
            return 'sample_curriculum'
        return 'program_info'
    
    if 'courses' in path_lower:
        return 'course_description'
    
    if 'policies' in path_lower:
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

def generate_summary_from_json(data: any, file_name: str) -> str:
    """Generate a human-readable summary from JSON data."""
    summaries = []
    
    if isinstance(data, list):
        # Handle list of items (e.g., requirements, concentrations)
        if len(data) > 0 and isinstance(data[0], dict):
            # Extract key information from first few items
            if 'Name' in data[0]:
                # Requirements structure
                names = [item.get('Name', '') for item in data[:5]]
                summaries.append(f"Contains {len(data)} requirement categories")
                if names:
                    summaries.append(f"Including: {', '.join(names[:3])}")
                    if len(names) > 3:
                        summaries.append(f"and {len(data) - 3} more")
            
            elif 'Concentration Name' in data[0]:
                # Concentrations structure
                conc_names = [item.get('Concentration Name', '') for item in data]
                summaries.append(f"Describes {len(data)} concentrations")
                summaries.append(f"Concentrations: {', '.join(conc_names)}")
            
            elif 'course_id' in data[0]:
                # Course structure
                course_id = data[0].get('course_id', '')
                course_name = data[0].get('long_title', data[0].get('short_title', ''))
                summaries.append(f"Course information for {course_id}")
                if course_name:
                    summaries.append(f"Title: {course_name}")
                
                # Check for key fields
                if 'prereqs' in data[0]:
                    summaries.append("Includes prerequisites information")
                if 'custom_fields' in data[0] and data[0].get('custom_fields'):
                    fields = data[0]['custom_fields']
                    if 'assessment_structure' in fields:
                        summaries.append("Includes assessment structure")
                    if 'key_topics' in fields:
                        summaries.append("Includes key topics covered")
    
    elif isinstance(data, dict):
        # Handle dictionary structure
        if 'program' in data or 'Program' in data:
            program = data.get('program', data.get('Program', ''))
            summaries.append(f"Program information for {program}")
        
        # Check for common fields
        if 'requirements' in data:
            summaries.append("Contains program requirements")
        if 'courses' in data:
            summaries.append("Lists required courses")
    
    if not summaries:
        summaries.append(f"Contains information from {file_name}")
    
    return "; ".join(summaries)

def generate_summary_from_markdown(content: str, file_name: str) -> str:
    """Generate a summary from markdown content."""
    lines = content.split('\n')
    summaries = []
    
    # Extract title (first heading)
    for line in lines[:10]:
        if line.strip().startswith('#'):
            title = line.strip('#').strip()
            summaries.append(f"Document: {title}")
            break
    
    if not summaries:
        summaries.append(f"Document: {file_name}")
    
    # Look for key sections
    content_lower = content.lower()
    if 'prerequisite' in content_lower:
        summaries.append("Discusses prerequisites")
    if 'requirement' in content_lower:
        summaries.append("Outlines requirements")
    if 'registration' in content_lower:
        summaries.append("Covers registration procedures")
    if 'policy' in content_lower or 'policies' in content_lower:
        summaries.append("Describes policies")
    if 'deadline' in content_lower:
        summaries.append("Includes deadlines")
    
    return "; ".join(summaries)

def analyze_document(file_path: str) -> Dict:
    """Analyze a document and extract metadata."""
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_name)[1].lower()
    
    metadata = {
        'file_path': file_path,
        'file_name': file_name,
        'file_type': file_ext[1:] if file_ext else 'unknown'
    }
    
    try:
        if file_ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Convert to string for analysis
            content_str = json.dumps(data, ensure_ascii=False)
            
            # Extract metadata
            metadata['content_type'] = infer_content_type(file_path, content_str)
            metadata['program'] = infer_program(file_path, content_str)
            metadata['courses_mentioned'] = extract_course_codes(content_str)
            metadata['summary'] = generate_summary_from_json(data, file_name)
            metadata['num_items'] = len(data) if isinstance(data, list) else 1
            
        elif file_ext == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata
            metadata['content_type'] = infer_content_type(file_path, content)
            metadata['program'] = infer_program(file_path, content)
            metadata['courses_mentioned'] = extract_course_codes(content)
            metadata['summary'] = generate_summary_from_markdown(content, file_name)
            metadata['word_count'] = len(content.split())
        
        else:
            metadata['content_type'] = 'unknown'
            metadata['summary'] = f"File: {file_name}"
    
    except Exception as e:
        metadata['error'] = str(e)
        metadata['summary'] = f"Error reading {file_name}: {e}"
    
    return metadata

def analyze_directory(directory_path: str, recursive: bool = True) -> List[Dict]:
    """Analyze all documents in a directory."""
    metadata_list = []
    
    for root, dirs, files in os.walk(directory_path):
        for file in files:
            if file.endswith(('.json', '.md')):
                file_path = os.path.join(root, file)
                metadata = analyze_document(file_path)
                metadata_list.append(metadata)
        
        if not recursive:
            break
    
    return metadata_list

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Analyze all documents and generate metadata report."""
    print("=" * 80)
    print("📊 DOCUMENT METADATA ANALYSIS")
    print("=" * 80)
    
    data_path = "./data"
    
    if not os.path.exists(data_path):
        print(f"❌ Data directory not found: {data_path}")
        return
    
    print(f"\n🔍 Analyzing documents in: {data_path}")
    print("This may take a few minutes...\n")
    
    # Analyze each domain separately
    domains = {
        'programs': os.path.join(data_path, 'programs'),
        'courses': os.path.join(data_path, 'courses'),
        'policies': os.path.join(data_path, 'policies')
    }
    
    all_metadata = {}
    
    for domain, domain_path in domains.items():
        if not os.path.exists(domain_path):
            print(f"⚠️  Domain directory not found: {domain_path}")
            continue
        
        print(f"\n📦 Analyzing domain: {domain.upper()}")
        print("-" * 80)
        
        metadata_list = analyze_directory(domain_path)
        all_metadata[domain] = metadata_list
        
        print(f"   ✅ Analyzed {len(metadata_list)} documents")
        
        # Show some examples
        content_types = {}
        for meta in metadata_list:
            ct = meta.get('content_type', 'unknown')
            content_types[ct] = content_types.get(ct, 0) + 1
        
        print(f"   📋 Content types found:")
        for ct, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {ct}: {count} documents")
    
    # Save metadata to file
    output_file = "document_metadata_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "=" * 80)
    print(f"✅ Metadata analysis complete!")
    print(f"📄 Results saved to: {output_file}")
    print("=" * 80)
    
    # Print summary statistics
    total_docs = sum(len(mlist) for mlist in all_metadata.values())
    print(f"\n📊 SUMMARY STATISTICS")
    print(f"   Total documents analyzed: {total_docs}")
    print(f"   Domains covered: {len(all_metadata)}")
    
    # Count documents with course mentions
    docs_with_courses = sum(
        1 for mlist in all_metadata.values() 
        for meta in mlist 
        if meta.get('courses_mentioned')
    )
    print(f"   Documents mentioning courses: {docs_with_courses}")
    
    # Count by program
    program_counts = {}
    for mlist in all_metadata.values():
        for meta in mlist:
            prog = meta.get('program')
            if prog:
                program_counts[prog] = program_counts.get(prog, 0) + 1
    
    if program_counts:
        print(f"\n   Documents by program:")
        for prog, count in sorted(program_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {prog}: {count} documents")

if __name__ == "__main__":
    main()
