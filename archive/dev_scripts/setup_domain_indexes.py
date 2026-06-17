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