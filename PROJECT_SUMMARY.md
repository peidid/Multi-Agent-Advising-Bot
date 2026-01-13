# Project Summary

## What Is This?

An **LLM-Driven Multi-Agent Academic Advising System** that uses intelligent coordination to provide comprehensive academic advice for CMU-Q students.

**Key Innovation:** Instead of rule-based routing, we use an LLM to understand queries and dynamically plan workflows across specialized agents.

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
$env:OPENAI_API_KEY="your-key"

# 3. Build indexes (one-time, ~2-3 min)
python setup_domain_indexes.py

# 4. Run
python chat.py
```

---

## Architecture

```
User Query
    ↓
LLM-Driven Coordinator
  • Understands problem
  • Analyzes agent capabilities
  • Plans dynamic workflow
    ↓
Specialized Agents (parallel execution)
  • Programs Requirements Agent
  • Course Scheduling Agent
  • Policy Compliance Agent
    ↓
Answer Synthesis
    ↓
Final Response
```

---

## Key Files

### Core System
- `chat.py` - Interactive interface
- `multi_agent.py` - LangGraph workflow
- `config.py` - LLM configuration

### Coordinator
- `coordinator/coordinator.py` - Main coordinator
- `coordinator/llm_driven_coordinator.py` - LLM-driven logic

### Agents
- `agents/base_agent.py` - Base agent class (with RAG)
- `agents/programs_agent.py` - Program requirements
- `agents/courses_agent.py` - Course information
- `agents/policy_agent.py` - University policies

### Infrastructure
- `rag_engine_improved.py` - RAG implementation
- `blackboard/schema.py` - Shared state schema
- `setup_domain_indexes.py` - Index builder

---

## Documentation

- **QUICK_START.md** - Setup and usage guide
- **ARCHITECTURE.md** - Detailed system design
- **TESTING_LLM_DRIVEN_COORDINATOR.md** - Testing guide
- **RULE_BASED_VS_LLM_DRIVEN.md** - Comparison of approaches
- **DEV_MODE_GUIDE.md** - Development mode usage
- **ACL2026_RESEARCH_ROADMAP.md** - Research plan

---

## Example Usage

### Simple Query
```
You: What are the prerequisites for 15-213?

System: 
  🧠 LLM Analysis:
     • Simple course info query
     • Activates: Course Scheduling Agent only
  
  💬 Response:
     The prerequisites for 15-213 are...
```

### Complex Query
```
You: I probably will get a D in 15-112. 
     As a CS student, do I need to retake it?

System:
  🧠 LLM Analysis:
     • Complex multi-faceted question
     • Involves: policies, requirements, dependencies
     • Activates: All 3 agents
     • Order: Policy → Programs → Courses
  
  💬 Response:
     [Comprehensive answer addressing all aspects]

You: What if I retake it next semester?
     ↑ System remembers "it" = 15-112

System:
  💭 Context: 1 previous turn(s) in conversation
  🧠 LLM Analysis:
     • Understands "it" refers to 15-112
     • Uses context from previous discussion
  
  💬 Response:
     [Explains retake policy with context]
```

---

## Why LLM-Driven?

### Traditional (Rule-Based)
```python
if "prerequisite" in query:
    intent = "course_info"
    agents = ["course_scheduling"]
```
❌ Brittle keyword matching  
❌ Fixed intent types  
❌ No context awareness  

### Our Approach (LLM-Driven)
```python
plan = llm.understand_and_plan(
    query=query,
    history=conversation_history,
    profile=student_profile
)
```
✅ Understands underlying intent  
✅ Dynamic agent selection  
✅ Context-aware planning  
✅ Explainable reasoning  

---

## Technology Stack

- **LangChain** - LLM framework
- **LangGraph** - Workflow orchestration
- **ChromaDB** - Vector database
- **OpenAI** - GPT-4 Turbo & GPT-4o
- **Pydantic** - Data validation

---

## Research Contribution (ACL 2026)

**Title:** "Structured Negotiation in Multi-Agent Academic Advising: LLM-Driven Coordination with Interactive Conflict Resolution"

**Main Idea:**  
Multi-agent systems with **structured negotiation protocols** and **interactive conflict resolution** produce safer, higher-quality academic advising compared to single-agent or static multi-agent approaches.

**Core Contributions:**
1. **Proposal + Critique Protocol:** Visible negotiation between specialized agents
2. **Interactive Conflict Resolution:** User agency in trade-off decisions
3. **Structured Blackboard:** Typed schema for agent communication
4. **Comprehensive Evaluation:** Comparison with 3 baseline systems

**Research Questions:**
- **RQ1:** Does multi-agent with negotiation improve quality and safety?
- **RQ2:** Does proposal-critique protocol improve conflict detection?
- **RQ3:** Does interactive resolution improve user alignment?
- **RQ4:** How does agent count affect performance? (ablation)

**Evaluation:**
- 50 test scenarios with gold standards from advisors
- 3 baseline systems (single-agent, rule-based, static multi-agent)
- Automatic metrics: correctness, safety, completeness
- Human evaluation: quality ratings from advisors
- Statistical significance testing

**See:** `ACL2026_GAP_ANALYSIS.md` and `ACL2026_IMPLEMENTATION_PLAN.md`

---

## Development Mode

Test individual agents:

```
You: mode:dev
System: 🔧 Development mode enabled!

You: @courses What are prerequisites for 15-213?
[Uses only Course Scheduling Agent]

You: @programs What are CS major requirements?
[Uses only Programs Requirements Agent]

You: @all I want to add a CS minor
[Uses all agents]

You: mode:normal
System: ✅ Returned to normal mode
```

---

## Configuration

`config.py`:
```python
COORDINATOR_MODEL = "gpt-4-turbo"      # Complex reasoning
COORDINATOR_TEMPERATURE = 0.3

AGENT_MODEL = "gpt-4o"                 # Fast + accurate
AGENT_TEMPERATURE = 0.3
```

**Why different models?**
- Coordinator: Needs strong reasoning for workflow planning
- Agents: Need speed for domain queries
- Cost: Optimize for parallel execution

---

## Data Sources

- `data/programs/` - Program requirements (23 MD, 29 JSON)
- `data/courses/` - Course information (4765 JSON)
- `data/policies/` - University policies (50 MD)

Total: ~5000 documents indexed via RAG

---

## Project Structure

```
Product 0110/
├── coordinator/           # LLM-driven coordination
├── agents/               # Specialized agents
├── blackboard/           # Shared state
├── data/                 # Knowledge base
├── chat.py              # Interface
├── multi_agent.py       # Workflow
├── config.py            # Configuration
└── *.md                 # Documentation
```

---

## Key Features

✅ **LLM-Driven Coordination** - Intelligent workflow planning  
✅ **Multi-Agent System** - Specialized domain experts  
✅ **RAG-Enhanced** - Retrieves relevant knowledge  
✅ **Conversation Memory** - Remembers context across turns  
✅ **Parallel Execution** - Fast responses  
✅ **Explainable** - Shows reasoning process  
✅ **Adaptive** - Context-aware decisions  
✅ **Development Mode** - Easy testing  

---

## Next Steps

1. **Try it:** `python chat.py`
2. **Read:** QUICK_START.md
3. **Understand:** ARCHITECTURE.md
4. **Test:** TESTING_LLM_DRIVEN_COORDINATOR.md

---

## Contact

For questions about this system or the research, contact the development team.

---

**Built for ACL 2026 Demo Track** 🚀
