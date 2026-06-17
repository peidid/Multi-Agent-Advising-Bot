# File Guide

## 📁 Project Files Overview

### 🚀 **Start Here**
- **PROJECT_SUMMARY.md** - High-level overview of the entire project
- **QUICK_START.md** - Setup and usage instructions
- **README.md** - Main documentation

---

## 💻 **Core System Files**

### Main Entry Points
- **chat.py** - Interactive chat interface (run this!)
- **multi_agent.py** - LangGraph workflow orchestration
- **config.py** - LLM model configuration

### Coordinator (Brain)
- **coordinator/coordinator.py** - Main coordinator class
- **coordinator/llm_driven_coordinator.py** - LLM-driven coordination logic
- **coordinator/__init__.py** - Package initialization

### Agents (Domain Experts)
- **agents/base_agent.py** - Base agent class with RAG
- **agents/programs_agent.py** - Program requirements agent
- **agents/courses_agent.py** - Course scheduling agent
- **agents/policy_agent.py** - Policy compliance agent
- **agents/__init__.py** - Package initialization

### Infrastructure
- **rag_engine_improved.py** - RAG implementation (vector DB)
- **blackboard/schema.py** - Shared state schema
- **blackboard/__init__.py** - Package initialization
- **course_tools.py** - Course data utilities

### Setup
- **setup_domain_indexes.py** - Build RAG indexes (run once)
- **requirements.txt** - Python dependencies

---

## 📚 **Documentation Files**

### Getting Started
- **PROJECT_SUMMARY.md** ⭐ - Start here for overview
- **QUICK_START.md** ⭐ - Setup and first steps
- **README.md** - Main documentation

### Architecture & Design
- **ARCHITECTURE.md** - Detailed system design
- **RULE_BASED_VS_LLM_DRIVEN.md** - Comparison of approaches

### Testing & Development
- **TESTING_LLM_DRIVEN_COORDINATOR.md** - Testing guide
- **DEV_MODE_GUIDE.md** - Development mode usage
- **CONVERSATION_MEMORY.md** - Conversation memory feature
- **test_classifier_only.py** - Test coordinator without agents

### Research (ACL 2026)
- **ACL2026_GAP_ANALYSIS.md** ⭐ - Gap between current system and vision
- **ACL2026_IMPLEMENTATION_PLAN.md** ⭐ - 17-week plan to publication
- **ACL2026_RESEARCH_ROADMAP.md** - Original research ideas

### Utilities
- **verify_models.py** - Verify model configuration
- **FILE_GUIDE.md** - This file!

---

## 📊 **Data Files** (not in repo, generated)

### Vector Databases (ChromaDB)
- **chroma_db_programs/** - Programs requirements index
- **chroma_db_courses/** - Course information index
- **chroma_db_policies/** - University policies index

### Source Data
- **data/programs/** - Program requirements (MD + JSON)
- **data/courses/** - Course information (JSON)
- **data/policies/** - University policies (MD)

---

## 🗂️ **File Organization**

```
Product 0110/
│
├── 📄 Entry Points
│   ├── chat.py                    # Run this!
│   ├── multi_agent.py             # Workflow
│   └── config.py                  # Configuration
│
├── 🧠 Coordinator/
│   ├── coordinator.py             # Main coordinator
│   └── llm_driven_coordinator.py  # LLM logic
│
├── 🤖 Agents/
│   ├── base_agent.py              # Base class
│   ├── programs_agent.py          # Programs
│   ├── courses_agent.py           # Courses
│   └── policy_agent.py            # Policies
│
├── 🔧 Infrastructure/
│   ├── rag_engine_improved.py     # RAG
│   ├── blackboard/schema.py       # State
│   └── course_tools.py            # Utilities
│
├── 📚 Documentation/
│   ├── PROJECT_SUMMARY.md         # Overview ⭐
│   ├── QUICK_START.md             # Setup ⭐
│   ├── README.md                  # Main docs
│   ├── ARCHITECTURE.md            # Design
│   ├── TESTING_LLM_DRIVEN_COORDINATOR.md
│   ├── DEV_MODE_GUIDE.md
│   ├── RULE_BASED_VS_LLM_DRIVEN.md
│   ├── ACL2026_RESEARCH_ROADMAP.md
│   └── FILE_GUIDE.md              # This file
│
├── 🧪 Testing/
│   ├── test_classifier_only.py    # Test coordinator
│   └── verify_models.py           # Verify config
│
├── ⚙️ Setup/
│   ├── setup_domain_indexes.py    # Build indexes
│   └── requirements.txt           # Dependencies
│
└── 📊 Data/ (not tracked)
    ├── data/                      # Source data
    └── chroma_db_*/               # Vector DBs
```

---

## 🎯 **What to Read When**

### First Time Setup
1. **PROJECT_SUMMARY.md** - Understand what this is
2. **QUICK_START.md** - Get it running
3. Run `python chat.py` - Try it out!

### Understanding the System
1. **ARCHITECTURE.md** - How it works
2. **RULE_BASED_VS_LLM_DRIVEN.md** - Why LLM-driven?
3. Look at `coordinator/llm_driven_coordinator.py` - See the code

### Development & Testing
1. **DEV_MODE_GUIDE.md** - Manual agent testing
2. **TESTING_LLM_DRIVEN_COORDINATOR.md** - Test cases
3. Run `python test_classifier_only.py` - Test coordinator

### Research & Evaluation
1. **ACL2026_RESEARCH_ROADMAP.md** - Research plan
2. **RULE_BASED_VS_LLM_DRIVEN.md** - Contribution
3. Design experiments

---

## 🔍 **Finding Specific Information**

### "How do I run this?"
→ **QUICK_START.md**

### "How does the coordinator work?"
→ **ARCHITECTURE.md** + `coordinator/llm_driven_coordinator.py`

### "How do I test individual agents?"
→ **DEV_MODE_GUIDE.md**

### "What's the research contribution?"
→ **ACL2026_RESEARCH_ROADMAP.md**

### "How do I add a new agent?"
→ **ARCHITECTURE.md** (Specialized Agents section)

### "How does RAG work?"
→ `rag_engine_improved.py` + **ARCHITECTURE.md** (RAG Engine section)

### "How do I change the LLM models?"
→ `config.py`

### "What queries should I test?"
→ **TESTING_LLM_DRIVEN_COORDINATOR.md**

---

## 📝 **File Sizes (Approximate)**

### Small (< 100 lines)
- config.py
- course_tools.py
- blackboard/schema.py
- All __init__.py files

### Medium (100-300 lines)
- chat.py
- multi_agent.py
- coordinator/coordinator.py
- agents/base_agent.py
- agents/*_agent.py
- rag_engine_improved.py

### Large (> 300 lines)
- coordinator/llm_driven_coordinator.py (~470 lines)
- README.md
- ARCHITECTURE.md

---

## 🗑️ **Files Removed (Cleanup)**

These old files have been removed to simplify the project:

### Old Coordinator Approaches
- ~~coordinator/intent_classifier_enhanced.py~~ (rule-based)
- ~~TESTING_ENHANCED_CLASSIFIER.md~~
- ~~COORDINATOR_IMPROVEMENTS_SUMMARY.txt~~
- ~~IMPLEMENTATION_PRIORITY.md~~

### Old Documentation
- ~~EXAMPLE_DEV_SESSION.md~~
- ~~DEVELOPMENT_MODE_SUMMARY.txt~~
- ~~CHEATSHEET.md~~
- ~~NETWORK_ISSUE_SOLUTION.md~~
- ~~COORDINATOR_IMPROVEMENTS_FOR_ACL2026.md~~
- ~~QUICK_START_ACL2026.md~~ (replaced by QUICK_START.md)
- ~~README_CHAT.md~~
- ~~Modal proposal 1.md~~
- ~~Modal proposal 2.md~~

### Old Test/Setup Scripts
- ~~test_enhanced_integration.py~~
- ~~test.py~~
- ~~clean_courses.ps1~~

**Result:** Cleaner, more focused project structure!

---

## 🎓 **For New Team Members**

### Day 1
1. Read **PROJECT_SUMMARY.md**
2. Follow **QUICK_START.md**
3. Run `python chat.py` and try queries

### Day 2
1. Read **ARCHITECTURE.md**
2. Read **RULE_BASED_VS_LLM_DRIVEN.md**
3. Look at `coordinator/llm_driven_coordinator.py`

### Day 3
1. Read **DEV_MODE_GUIDE.md**
2. Test individual agents
3. Read **TESTING_LLM_DRIVEN_COORDINATOR.md**

### Week 2+
1. Read **ACL2026_RESEARCH_ROADMAP.md**
2. Design experiments
3. Start development

---

## 💡 **Pro Tips**

1. **Always start with PROJECT_SUMMARY.md** - Best overview
2. **Use dev mode for testing** - `mode:dev` in chat
3. **Check config.py first** - Model settings
4. **Read ARCHITECTURE.md for deep dive** - Complete system design
5. **Test coordinator only** - `python test_classifier_only.py` (no RAG)

---

**Questions?** Check the relevant documentation file above! 📖
