"""
Project Cleanup Script
Removes unnecessary files to keep project clean and understandable
"""

import os
import shutil

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Files to DELETE (old/unused versions)
FILES_TO_DELETE = [
    # Old Streamlit versions (we only keep streamlit_app_agent_view.py)
    "streamlit_app.py",
    "streamlit_app_enhanced.py",
    "streamlit_app_final.py",
    "streamlit_app_working.py",

    # Old test files
    "test.py",
    "test_clarification.py",
    "test_classifier_only.py",

    # Old documentation (replaced by new comprehensive docs)
    "STREAMLIT_FIX.md",
    "STREAMLIT_FINAL_FEATURES.md",
    "DEPLOYMENT_GUIDE.md",  # Replaced by DEPLOYMENT_INSTRUCTIONS.md
    "FIX_APPLIED.md",
    "INTERFACE_COMPARISON.md",
    "AGENT_VIEW_INTERFACE.md",
    "PROFILE_HISTORY_ADDED.md",
]

# Directories to DELETE
DIRS_TO_DELETE = [
    "info - 副本",  # Duplicate info folder
    "chroma_db_programs",  # Will be regenerated
    "chroma_db_courses",
    "chroma_db_policies",
    "__pycache__",
]

def cleanup():
    """Remove unnecessary files and directories."""
    print("🧹 Cleaning up project...")
    print()

    deleted_files = 0
    deleted_dirs = 0
    errors = []

    # Delete files
    for file in FILES_TO_DELETE:
        file_path = os.path.join(BASE_DIR, file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"✅ Deleted file: {file}")
                deleted_files += 1
            except Exception as e:
                errors.append(f"❌ Error deleting {file}: {e}")
                print(errors[-1])
        else:
            print(f"⏭️  Skipped (not found): {file}")

    print()

    # Delete directories
    for dir_name in DIRS_TO_DELETE:
        dir_path = os.path.join(BASE_DIR, dir_name)
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"✅ Deleted directory: {dir_name}")
                deleted_dirs += 1
            except Exception as e:
                errors.append(f"❌ Error deleting {dir_name}: {e}")
                print(errors[-1])
        else:
            print(f"⏭️  Skipped (not found): {dir_name}")

    print()
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   Files deleted: {deleted_files}")
    print(f"   Directories deleted: {deleted_dirs}")
    print(f"   Errors: {len(errors)}")
    print("=" * 60)

    if errors:
        print()
        print("⚠️  Errors encountered:")
        for error in errors:
            print(f"   {error}")

    print()
    print("✨ Cleanup complete!")
    print()
    print("📁 Remaining key files:")
    print("   Core system:")
    print("   - multi_agent.py (main workflow)")
    print("   - agents/*.py (4 specialized agents)")
    print("   - coordinator/llm_driven_coordinator.py")
    print("   - blackboard/schema.py")
    print()
    print("   Interface:")
    print("   - streamlit_app_agent_view.py (THE interface)")
    print("   - chat.py (command-line alternative)")
    print()
    print("   Documentation:")
    print("   - README.md (project overview)")
    print("   - RESEARCH_DOCUMENTATION.md (comprehensive)")
    print("   - DEPLOYMENT_INSTRUCTIONS.md (how to share)")
    print()
    print("   Data:")
    print("   - data/programs/*.json (degree requirements)")
    print("   - data/courses/Schedule/*.json (course schedules)")
    print("   - data/policies/**/*.md (policy documents)")
    print()

if __name__ == "__main__":
    print()
    print("⚠️  WARNING: This will DELETE files!")
    print()
    response = input("Continue? (yes/no): ").strip().lower()

    if response in ['yes', 'y']:
        cleanup()
    else:
        print("❌ Cleanup cancelled.")
