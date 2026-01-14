"""
Rebuild Vector Database Indexes with Document Metadata

This script rebuilds all domain-specific vector databases with enhanced
document metadata to help agents better understand their knowledge base.

Usage:
    python rebuild_indexes_with_metadata.py [--domain DOMAIN] [--force]

Options:
    --domain DOMAIN    Rebuild only specific domain (programs, courses, policies)
    --force           Force rebuild even if index exists
"""

import sys
import argparse
import shutil
import os
from rag_engine_improved import build_all_domain_indexes, build_domain_index, DOMAIN_PATHS

def confirm_rebuild(domain: str = None):
    """Ask user to confirm rebuild operation."""
    if domain:
        print(f"\n⚠️  WARNING: This will DELETE and REBUILD the '{domain}' index.")
    else:
        print(f"\n⚠️  WARNING: This will DELETE and REBUILD ALL domain indexes:")
        for d in DOMAIN_PATHS.keys():
            print(f"   - {d}")
    
    print("\nThis operation:")
    print("  ✓ Will add document metadata to all chunks")
    print("  ✓ Will help agents understand document sources better")
    print("  ✓ May take several minutes to complete")
    print("  ✓ Cannot be undone (old indexes will be deleted)")
    
    response = input("\nDo you want to proceed? (yes/no): ").strip().lower()
    return response in ['yes', 'y']

def main():
    parser = argparse.ArgumentParser(
        description="Rebuild vector database indexes with document metadata"
    )
    parser.add_argument(
        '--domain',
        type=str,
        choices=list(DOMAIN_PATHS.keys()),
        help='Rebuild only specific domain'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompt'
    )
    
    args = parser.parse_args()
    
    # Show header
    print("=" * 80)
    print("🔄 REBUILD VECTOR DATABASES WITH METADATA")
    print("=" * 80)
    
    # Confirm operation (unless --force)
    if not args.force:
        if not confirm_rebuild(args.domain):
            print("\n❌ Operation cancelled by user.")
            return
    
    print("\n" + "=" * 80)
    print("Starting rebuild...")
    print("=" * 80)
    
    try:
        if args.domain:
            # Rebuild specific domain
            print(f"\n📦 Rebuilding domain: {args.domain}")
            print("-" * 80)
            build_domain_index(args.domain, force_rebuild=True)
            print(f"\n✅ Successfully rebuilt '{args.domain}' index with metadata!")
        else:
            # Rebuild all domains
            build_all_domain_indexes(force_rebuild=True)
            print("\n" + "=" * 80)
            print("✅ Successfully rebuilt ALL domain indexes with metadata!")
            print("=" * 80)
        
        print("\n📊 What's New:")
        print("   ✓ Each chunk now includes [DOCUMENT CONTEXT] header")
        print("   ✓ Metadata shows file name, type, and summary")
        print("   ✓ Program associations are identified")
        print("   ✓ Course codes mentioned are extracted")
        print("   ✓ Agents can now cite specific source documents")
        
        print("\n🚀 Next Steps:")
        print("   1. Test the system with your queries")
        print("   2. Agents should now provide better context and citations")
        print("   3. Check agent responses for document source mentions")
        
    except Exception as e:
        print(f"\n❌ Error during rebuild: {e}")
        print("\nTroubleshooting:")
        print("   1. Check that data/ folder exists and contains documents")
        print("   2. Ensure OpenAI API key is set in .env file")
        print("   3. Check internet connection for embedding API calls")
        sys.exit(1)

if __name__ == "__main__":
    main()
