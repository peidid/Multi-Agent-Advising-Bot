# Multi-Agent Academic Advising System

**A dynamic multi-agent system for academic advising with real-time visualization**

🎯 **Target:** ACL 2026 Demo Track
🏛️ **Institution:** Carnegie Mellon University - Qatar
🤖 **Architecture:** 5 collaborative AI agents (1 coordinator + 4 specialists)

---

## 🎯 Overview

This system implements a **multi-agent architecture** where specialized agents collaborate through a Coordinator to answer student questions:

- **Programs & Requirements Agent** - Handles major/minor requirements, degree progress, plan validation
- **Course & Scheduling Agent** - Provides course information, schedules, and conflict detection
- **Policy & Compliance Agent** - Ensures compliance with university policies and regulations
- **Academic Planning Agent** - Generates semester-by-semester course plans until graduation ✨ **NEW!**
- **Coordinator** - Orchestrates workflow, detects conflicts, manages negotiation, synthesizes answers

## ✨ Key Features

- **Dynamic Workflow** - Coordinator intelligently routes queries to appropriate agents
- **Negotiation Protocol** - Agents collaborate through Proposal + Critique mechanism
- **Conflict Detection** - Automatically identifies and resolves conflicts between agent recommendations
- **Domain-Specific Knowledge** - Each agent has its own focused RAG knowledge base
- **Human-like Responses** - Synthesized answers that read like a real academic advisor

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Anaconda/Conda (recommended)

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd Product
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the project root:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

4. **Build domain-specific knowledge bases:**
   ```bash
   python setup_domain_indexes.py
   ```
   This creates separate vector databases for each agent (takes a few minutes).

5. **Test the system:**
   ```bash
   python test.py
   ```

6. **Start chatting:**
   ```bash
   python chat.py
   ```

## 🆕 Document Metadata Enhancement (NEW!)

**Added**: January 14, 2026

The system now includes **enhanced document metadata** to help agents better understand their knowledge base and cite sources!

### What's New?

Every document chunk now includes rich context:

```
[DOCUMENT CONTEXT]
File: IS_Requirements.json
Type: program_requirements
Program: Information Systems
Mentions courses: 15-110, 15-112, 15-121, 21-112, 21-120
Summary: Contains 20 requirements | Examples: Technical Core - Mathematics, ...

[DOCUMENT CONTENT]
(original document content)
```

### Benefits

✅ **Source Citations** - Agents now cite specific documents (e.g., "According to IS_Requirements.json...")  
✅ **Better Context** - Agents understand document types and can prioritize appropriately  
✅ **Improved Accuracy** - Metadata helps distinguish between similar information  
✅ **User Trust** - Clear sources build confidence in answers

### Quick Start with Metadata

**1. Rebuild indexes with metadata:**
```bash
python rebuild_indexes_with_metadata.py
```

This adds metadata to all vector databases (~5-10 minutes, one-time).

**2. Test the improvements:**
```bash
python chat.py
```

Try: "What are the IS core requirements?" and look for source citations!

### Documentation

- **Quick Start**: `QUICK_START_METADATA.md` - Beginner's guide
- **README**: `README_METADATA.md` - Quick reference  
- **Technical Details**: `METADATA_ENHANCEMENTS.md` - Complete documentation

### Optional: Use Old Indexes

If you prefer to use the system without metadata (not recommended):
```bash
python setup_domain_indexes.py  # Use old method
```

However, we **strongly recommend** using metadata-enhanced indexes for better results!

---

## 🗓️ Academic Planning Feature (NEW!)

**Added**: January 18, 2026

The system now includes a **semester-by-semester course planning agent** that helps students plan their entire academic journey!

### What It Does

✅ **Generates complete course plans** from current semester to graduation
✅ **Balances workload** across semesters (45-54 units typically)
✅ **Respects prerequisites** automatically
✅ **Considers course availability** (Fall-only, Spring-only courses)
✅ **Integrates minors** into graduation plans
✅ **Adapts to constraints** (early graduation, study abroad, etc.)
✅ **Multi-agent collaboration** - Planning + Programs + Courses + Policy agents work together

### Quick Start with Planning

**Test the planning feature:**
```bash
python test_planning.py
```

**Use in chat:**
```bash
python chat.py
```

Try asking:
- "Help me plan my courses until graduation"
- "I want to add a Business minor, can you make a semester plan?"
- "Can I graduate in 3.5 years? Show me a plan"

### How It Works

The Planning Agent demonstrates **multi-agent collaboration**:

1. **Coordinator** detects planning intent
2. **Programs Agent** provides degree requirements
3. **Planning Agent** generates semester-by-semester plans
4. **Courses Agent** validates course availability
5. **Policy Agent** checks for overload/conflicts
6. **Negotiation** if conflicts detected (e.g., "Semester exceeds unit limit")
7. **Planning Agent revises** based on feedback
8. **Coordinator synthesizes** final plan with explanations

### Documentation

- **Quick Guide**: [PLANNING_IMPLEMENTATION_SUMMARY.md](PLANNING_IMPLEMENTATION_SUMMARY.md)
- **Complete Guide**: [PLANNING_GUIDE.md](PLANNING_GUIDE.md)

### Example Output

```
PLAN A: Balanced 4-Year Path

Semester 1 (Fall 2026):
- 15-150: Principles of Functional Programming (12 units)
- 21-241: Matrices and Linear Transformations (10 units)
- 76-270: Writing for the Professions (9 units)
- 15-281: AI: Representation and Problem Solving (12 units)
Total: 43 units

[... continues for all semesters ...]

RATIONALE:
This plan ensures prerequisites are met in order, balances
workload across semesters, and completes core requirements
by junior year for maximum elective flexibility.
```

---

## 📁 Project Structure

```
Product/
├── agents/                    # Agent implementations
│   ├── base_agent.py         # Base agent class
│   ├── programs_agent.py     # Programs & Requirements Agent
│   ├── courses_agent.py      # Course & Scheduling Agent
│   ├── policy_agent.py       # Policy & Compliance Agent
│   └── planning_agent.py     # Academic Planning Agent ✨ NEW
│
├── coordinator/               # Coordinator/orchestrator
│   └── coordinator.py        # Main coordinator logic
│
├── blackboard/               # Shared state schema
│   └── schema.py             # Structured state definitions
│
├── data/                     # Source documents (agent-based structure)
│   ├── programs/             # Programs Agent data
│   ├── courses/              # Courses Agent data
│   └── policies/             # Policy Agent data
│
├── chroma_db_*/              # Vector databases (auto-generated)
│
├── multi_agent.py           # Main LangGraph workflow
├── rag_engine_improved.py   # RAG engine with domain-specific indexes
├── course_tools.py           # Course data utilities
├── planning_tools.py         # Planning utilities & algorithms ✨ NEW
├── config.py                 # Model configuration (Coordinator vs Agents)
├── chat.py                   # Interactive chat interface
├── setup_domain_indexes.py  # Setup script for knowledge bases
├── test.py                   # Test script
└── test_planning.py          # Planning agent test suite ✨ NEW
```

## 💬 Usage

### Streamlit Web Interface (NEW! - Perfect for Demos) 🎨

**Beautiful visual interface with real-time multi-agent visualization!**

```bash
pip install -r requirements_streamlit.txt
streamlit run streamlit_app_final.py
```

**Features:**
- 💬 **Chat Interface** - Natural conversation with visual agent activation
- 🔬 **Persistent Research Analytics** - Explore complete workflow after each answer (collapsible)
- 👤 **Optional Student Profile** - Set profile only when needed, coordinator adapts
- 📊 **Live Workflow Visualization** - Watch agents collaborate in real-time
- 🔄 **Negotiation Display** - See conflicts resolve through Proposal + Critique
- 📋 **Blackboard Evolution** - Terminal-style live state updates

**Perfect for ACL 2026 demos!** See `STREAMLIT_FINAL_FEATURES.md` for details.

**Share via link:** Deploy FREE on Streamlit Cloud - see `DEPLOYMENT_GUIDE.md`

### Terminal Chat Interface

Run the terminal-based chat interface:

```bash
python chat.py
```

The interface shows:
- **Step 1:** Intent classification by Coordinator
- **Step 2:** Agent execution (which agents are activated)
- **Step 3:** Collaboration & negotiation process
- **Step 4:** Final human-like advisor response

### Development Mode (Manual Agent Selection)

For testing and debugging, enable development mode in the chat:
```
mode:dev
```

Then manually select agents:
- `@programs <query>` - Use only Programs Requirements Agent
- `@courses <query>` - Use only Course Scheduling Agent  
- `@policy <query>` - Use only Policy Compliance Agent
- `@all <query>` - Use all agents (bypass intent classification)

**Example:**
```
🔧 Dev: @courses What are the prerequisites for 15-213?
```

This bypasses intent classification and directly uses the specified agent. Useful for:
- Testing individual agents in isolation
- Debugging RAG retrieval
- Comparing agent responses
- Prompt engineering

See [DEV_MODE_GUIDE.md](DEV_MODE_GUIDE.md) for detailed usage and examples.

### Example Questions

**Requirements Questions:**
- "What are IS major requirements?"
- "Can I add a CS minor as an IS student?"
- "What courses do I need for a Business minor?"

**Course Planning:**
- "What courses should I take next semester?"
- "Can I take 15-112, 15-121, and 67-100 together?"
- "What are the prerequisites for 15-112?"

**Academic Planning (NEW!):**
- "Help me plan my courses until graduation"
- "I want to graduate in 3.5 years, can you make a plan?"
- "Can you create a 4-year plan with a Business minor?"
- "What should I take each semester to become a software engineer?"

**Policy Questions:**
- "Can I take course overload?"
- "What is the policy on repeating courses?"
- "What happens if I'm on academic probation?"

### Commands

- `quit` or `exit` - End conversation
- `clear` - Clear screen
- `help` - Show help message

## 🔧 Data Management

### Adding Data for an Agent

**Programs Agent:**
```bash
cp new_major_requirements.md data/programs/
python setup_domain_indexes.py  # Rebuild index
```

**Courses Agent:**
```bash
cp new_course.json data/courses/
python setup_domain_indexes.py  # Rebuild index
```

**Policy Agent:**
```bash
cp new_policy.md data/policies/
python setup_domain_indexes.py  # Rebuild index
```

### Rebuilding Indexes

After adding or modifying data files, rebuild the vector databases **with metadata** (recommended):

```bash
python rebuild_indexes_with_metadata.py
```

**Options:**
- `--domain programs` - Rebuild only programs domain
- `--domain courses` - Rebuild only courses domain
- `--domain policies` - Rebuild only policies domain
- `--force` - Skip confirmation prompt

**Legacy method (without metadata):**
```bash
python setup_domain_indexes.py
```

Note: Using metadata-enhanced indexes significantly improves answer quality and provides source attribution!

## 🏗️ Architecture

### Multi-Agent System

The system uses a **hub-and-spoke topology**:

```
                    Coordinator
                  (Orchestrator)
                        |
        +----------------+----------------+
        |                |                |
   Programs Agent   Courses Agent   Policy Agent
        |                |                |
   chroma_db_      chroma_db_      chroma_db_
   programs/       courses/        policies/
```

### Workflow

1. **Intent Classification** - Coordinator analyzes query and determines which agents are needed
2. **Workflow Planning** - Coordinator plans the execution order
3. **Agent Execution** - Agents execute in sequence, reading/writing to Blackboard
4. **Conflict Detection** - Coordinator detects conflicts between agent outputs
5. **Negotiation** - Agents collaborate through Proposal + Critique protocol
6. **Synthesis** - Coordinator synthesizes final answer from all agent contributions

### Blackboard Pattern

Agents communicate through a **structured Blackboard** (shared state):
- No direct agent-to-agent communication
- All interactions via Blackboard
- Typed schema ensures interpretability
- Enables conflict detection and negotiation

## 🧪 Testing

Run the test script to verify everything works:

```bash
python test.py
```

This tests:
- Domain index loading
- Agent execution
- Coordinator intent classification
- Full workflow

## 📚 Documentation

### Core Documentation
- **README.md** (this file) - Main documentation
- **ARCHITECTURE_GUIDE.md** ⭐ **NEW!** - Beginner-friendly technical architecture guide
- **ARCHITECTURE.md** - Technical architecture details
- **README_CHAT.md** - Detailed chat interface guide
- **PROJECT_STRUCTURE.md** - Project organization details

### Metadata Enhancement Documentation (NEW!)
- **README_METADATA.md** - Quick reference for metadata system
- **QUICK_START_METADATA.md** - Beginner's guide to metadata
- **METADATA_ENHANCEMENTS.md** - Complete technical documentation

### Other Documentation
- **RESTORED_FIXES_SUMMARY.md** - System improvements and fixes
- **DEV_MODE_GUIDE.md** - Development mode usage guide

## 🔍 Troubleshooting

### "Domain database not found"
Build indexes with metadata (recommended):
```bash
python rebuild_indexes_with_metadata.py
```

Or use legacy method:
```bash
python setup_domain_indexes.py
```

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### "OpenAI API error"
- Check your `.env` file has `OPENAI_API_KEY` set
- Verify your API key is valid

### Slow responses
- Normal for complex queries (10-30 seconds)
- System consults multiple agents and synthesizes answers

### List metadata error during rebuild
```
Expected metadata value to be a str... got [...] which is a list
```
**Status**: ✅ Already fixed in code (v1.0)  
**Solution**: Metadata is automatically converted to comma-separated strings

## ⚙️ Model Configuration

The system uses a **hybrid model strategy** for optimal performance and cost:

- **Coordinator**: Uses `gpt-4-turbo` (or `gpt-5` when available) for complex reasoning tasks
  - Intent classification
  - Workflow planning
  - Conflict resolution
  - Answer synthesis

- **Agents**: Use `gpt-4o` for fast, cost-effective domain-specific tasks
  - Course information retrieval
  - Program requirements checking
  - Policy compliance verification

### Changing Models

Edit `config.py` to change models:

```python
# Coordinator Model - Best available for complex tasks
COORDINATOR_MODEL = "gpt-4-turbo"  # Change to "gpt-5" when available

# Agent Models - Fast and cost-effective
AGENT_MODEL = "gpt-4o"
```

**To upgrade to GPT-5 when available:**
1. Open `config.py`
2. Change `COORDINATOR_MODEL = "gpt-5"`
3. Restart the system

View current configuration:
```bash
python config.py
```

Verify models are configured correctly:
```bash
python verify_models.py
```

## 🛠️ Development

### Adding a New Agent

1. Create agent class in `agents/`:
   ```python
   from agents.base_agent import BaseAgent
   
   class NewAgent(BaseAgent):
       def __init__(self):
           super().__init__("new_agent", "domain_name")
       
       def execute(self, state):
           # Implementation
   ```

2. Add domain to `rag_engine_improved.py`:
   ```python
   DOMAIN_PATHS = {
       "new_domain": ["data/new_domain/"]
   }
   ```

3. Register in `coordinator.py` and `multi_agent.py`

4. Rebuild indexes: `python setup_domain_indexes.py`

## 📝 Requirements

See `requirements.txt` for full list. Key dependencies:
- `langchain` - LLM framework
- `langgraph` - Multi-agent workflow
- `chromadb` - Vector database
- `openai` - LLM API
- `pydantic` - Data validation

## 🎓 Research Context

This system is designed for the **ACL 2026 demo track**, demonstrating:
- Dynamic multi-agent collaboration
- Negotiation protocols
- Conflict resolution
- Emergent collaborative behavior
- Visible agent interactions

## 📄 License

[Add your license here]

## 👥 Authors

[Add author information]

## 🙏 Acknowledgments

Built for CMU-Qatar academic advising research.

---

**Ready to chat?** Run `python chat.py` and start asking questions!


