# CMU-Q Academic Advising Multi-Agent System

A dynamic multi-agent academic advising chatbot for CMU-Qatar undergraduates, demonstrating collaborative AI agents working together to provide comprehensive academic guidance.

## 🎯 Overview

This system implements a **multi-agent architecture** where specialized agents collaborate through a Coordinator to answer student questions:

- **Programs & Requirements Agent** - Handles major/minor requirements, degree progress, plan validation
- **Course & Scheduling Agent** - Provides course information, schedules, and conflict detection  
- **Policy & Compliance Agent** - Ensures compliance with university policies and regulations
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

## 📁 Project Structure

```
Product/
├── agents/                    # Agent implementations
│   ├── base_agent.py         # Base agent class
│   ├── programs_agent.py     # Programs & Requirements Agent
│   ├── courses_agent.py      # Course & Scheduling Agent
│   └── policy_agent.py       # Policy & Compliance Agent
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
├── chat.py                   # Interactive chat interface
├── setup_domain_indexes.py  # Setup script for knowledge bases
└── test.py                   # Test script
```

## 💬 Usage

### Interactive Chat Interface

Run the chat interface to interact with the system:

```bash
python chat.py
```

The interface shows:
- **Step 1:** Intent classification by Coordinator
- **Step 2:** Agent execution (which agents are activated)
- **Step 3:** Collaboration & negotiation process
- **Step 4:** Final human-like advisor response

### Example Questions

**Requirements Questions:**
- "What are IS major requirements?"
- "Can I add a CS minor as an IS student?"
- "What courses do I need for a Business minor?"

**Course Planning:**
- "What courses should I take next semester?"
- "Can I take 15-112, 15-121, and 67-100 together?"
- "What are the prerequisites for 15-112?"

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

After adding or modifying data files, rebuild the vector databases:

```bash
python setup_domain_indexes.py
```

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

- **README_CHAT.md** - Detailed chat interface guide
- **PROJECT_STRUCTURE.md** - Project organization details

## 🔍 Troubleshooting

### "Domain database not found"
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

