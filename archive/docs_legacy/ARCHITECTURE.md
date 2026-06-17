# System Architecture

## Overview

This is a **LLM-Driven Multi-Agent Academic Advising System** that uses intelligent coordination to provide comprehensive academic advice.

---

## Core Components

### 1. LLM-Driven Coordinator (`coordinator/`)

**Purpose:** Intelligent orchestration of specialized agents

**Key Features:**
- **Full LLM Reasoning:** No predefined intent types or routing rules
- **Dynamic Workflow Planning:** Plans agent execution based on query understanding
- **Context-Aware:** Uses conversation history and student profile
- **Adaptive:** Adjusts workflow based on intermediate results

**Process:**
```
Query → Understand Problem → Analyze Agent Capabilities 
     → Plan Workflow → Set Decision Points → Execute & Adapt
```

**Implementation:** `coordinator/llm_driven_coordinator.py`

---

### 2. Specialized Agents (`agents/`)

Three domain-expert agents with RAG capabilities:

#### Programs Requirements Agent
- Major/minor requirements
- Degree progress tracking
- Plan validation
- Transfer credit policies

#### Course Scheduling Agent
- Course information (prerequisites, content, instructors)
- Schedule planning
- Time conflict detection
- Course availability

#### Policy Compliance Agent
- University policies
- Registration rules
- Academic integrity
- Financial aid policies

**Base Class:** `agents/base_agent.py`

---

### 3. RAG Engine (`rag_engine_improved.py`)

**Purpose:** Domain-specific knowledge retrieval

**Features:**
- Separate vector databases per domain
- OpenAI embeddings
- ChromaDB storage
- Automatic index building

**Data Sources:**
- `data/programs/` - Program requirements (MD + JSON)
- `data/courses/` - Course information (JSON)
- `data/policies/` - University policies (MD)

---

### 4. Blackboard State (`blackboard/`)

**Purpose:** Shared state for agent communication

**Contains:**
- User query
- Student profile
- Agent outputs
- Conflicts detected
- Plan options
- Conversation history

**Schema:** `blackboard/schema.py`

---

### 5. LangGraph Workflow (`multi_agent.py`)

**Purpose:** Orchestrate agent execution flow

**Nodes:**
1. `classify_intent` - LLM-driven coordination
2. `execute_agents` - Parallel/sequential agent execution
3. `detect_conflicts` - Identify issues/trade-offs
4. `synthesize_answer` - Generate final response

**Flow:**
```
Start → Classify Intent → Execute Agents → Detect Conflicts → Synthesize → End
```

---

## LLM-Driven Coordination (Key Innovation)

### Traditional Approach (Rule-Based)
```python
# Extract keywords
if "prerequisite" in query:
    intent = "course_info"
    agents = ["course_scheduling"]
```

**Problems:**
- Brittle keyword matching
- Fixed intent types
- No context awareness
- Over-simplifies complex queries

### Our Approach (LLM-Driven)
```python
# Full LLM reasoning
plan = llm.understand_and_plan(
    query=query,
    history=conversation_history,
    profile=student_profile
)
# Returns: goal, agents, workflow, decision_points, reasoning
```

**Advantages:**
- Understands underlying intent
- Dynamic agent selection
- Context-aware planning
- Handles complex/ambiguous queries
- Explainable reasoning

---

## Example: LLM-Driven Coordination

### Query
```
"I probably will get a D in 15-112 this semester. 
 As a CS student, do I need to retake it next semester?"
```

### LLM Analysis
```json
{
  "understanding": {
    "student_goal": "Determine if they need to retake 15-112",
    "underlying_concern": "Impact of D grade on CS major requirements",
    "complexity": "high"
  },
  "agent_analysis": {
    "policy_compliance": {
      "priority": "high",
      "reasoning": "Need to check if D is passing grade university-wide"
    },
    "programs_requirements": {
      "priority": "high", 
      "reasoning": "Core question about major requirements"
    },
    "course_scheduling": {
      "priority": "medium",
      "reasoning": "Helpful for understanding course dependencies"
    }
  },
  "workflow": {
    "execution_order": [
      "policy_compliance",
      "programs_requirements", 
      "course_scheduling"
    ],
    "decision_points": [
      {
        "after_agent": "policy_compliance",
        "check": "Is D a passing grade university-wide?",
        "if_no": "Stop - must retake regardless of major"
      },
      {
        "after_agent": "programs_requirements",
        "check": "Does CS major accept D for 15-112?",
        "if_no": "Must retake for major requirement"
      }
    ]
  }
}
```

### Why This is Better

**Rule-Based Would:**
- Match "retake" → `check_requirements` intent
- Route to `programs_requirements` only
- Miss policy implications
- Miss course dependencies

**LLM-Driven Does:**
- Understands multi-faceted question
- Recognizes need for policy check first
- Plans logical workflow
- Sets decision points for adaptation

---

## Data Flow

```
User Query
    ↓
Coordinator (LLM-driven)
    ↓ (understands & plans)
Blackboard State
    ↓
Agent 1 → RAG Retrieval → Response
    ↓
Agent 2 → RAG Retrieval → Response
    ↓
Agent 3 → RAG Retrieval → Response
    ↓
Conflict Detection
    ↓
Answer Synthesis
    ↓
Final Response
```

---

## Configuration (`config.py`)

```python
COORDINATOR_MODEL = "gpt-4-turbo"      # For complex reasoning
COORDINATOR_TEMPERATURE = 0.3

AGENT_MODEL = "gpt-4o"                 # For domain queries
AGENT_TEMPERATURE = 0.3
```

**Why Different Models?**
- Coordinator needs stronger reasoning (gpt-4-turbo)
- Agents need speed + accuracy (gpt-4o)
- Cost optimization for parallel agent calls

---

## File Structure

```
Product 0110/
├── coordinator/
│   ├── coordinator.py              # Main coordinator
│   └── llm_driven_coordinator.py   # LLM-driven logic
├── agents/
│   ├── base_agent.py               # Base agent class
│   ├── programs_agent.py
│   ├── courses_agent.py
│   └── policy_agent.py
├── blackboard/
│   ├── schema.py                   # State schema
│   └── __init__.py
├── data/
│   ├── programs/                   # Program data
│   ├── courses/                    # Course data
│   └── policies/                   # Policy data
├── multi_agent.py                  # LangGraph workflow
├── chat.py                         # Interactive interface
├── rag_engine_improved.py          # RAG implementation
├── config.py                       # LLM configuration
└── setup_domain_indexes.py         # Index builder
```

---

## Key Design Decisions

### 1. Why LLM-Driven Coordination?
- **Research Contribution:** Novel approach for multi-agent systems
- **Better Understanding:** LLM interprets intent, not just matches keywords
- **Flexibility:** No need to predefine all possible intents
- **Explainability:** LLM provides reasoning for decisions

### 2. Why Separate Agents?
- **Domain Expertise:** Each agent specializes in one area
- **Parallel Execution:** Can run agents simultaneously
- **Maintainability:** Easy to update individual agents
- **RAG Efficiency:** Smaller, focused knowledge bases

### 3. Why Blackboard Pattern?
- **Loose Coupling:** Agents don't need to know about each other
- **Flexibility:** Easy to add new agents
- **Transparency:** All state changes visible
- **Debugging:** Can inspect state at any point

### 4. Why LangGraph?
- **Visual Workflow:** Easy to understand execution flow
- **State Management:** Built-in state handling
- **Conditional Routing:** Dynamic workflow based on state
- **Debugging:** Can trace execution path

---

## Research Contribution (ACL 2026)

**Title:** "LLM as Coordinator: Dynamic Multi-Agent Workflow Planning for Academic Advising"

**Main Contribution:**
Demonstrating that LLM-driven coordination outperforms rule-based routing in multi-agent systems by:
1. Better understanding complex queries
2. More intelligent agent selection
3. Dynamic workflow planning
4. Context-aware adaptation

**Evaluation:**
- Compare LLM-driven vs rule-based on 50 test queries
- Metrics: agent selection accuracy, workflow quality, response quality
- User study: which approach gives better advice?

---

## Future Enhancements

1. **Interactive Conflict Resolution**
   - User chooses between trade-offs
   - System explains implications

2. **Structured Negotiation Protocol**
   - Agents negotiate solutions
   - Visible reasoning process

3. **Learning from History**
   - Improve coordination over time
   - Personalized workflows

4. **Multi-Turn Planning**
   - Break complex queries into sub-goals
   - Progressive refinement

---

## Testing

### Run Full System
```bash
python chat.py
```

### Test Coordinator Only
```bash
python test_classifier_only.py
```

### Development Mode
```
mode:dev
@courses What are prerequisites for 15-213?
@all I want to add a CS minor
mode:normal
```

---

## Dependencies

- `langchain` - LLM framework
- `langgraph` - Workflow orchestration
- `chromadb` - Vector database
- `openai` - LLM API
- `pydantic` - Data validation

See `requirements.txt` for full list.

---

This architecture enables intelligent, explainable, and adaptive academic advising through LLM-driven multi-agent coordination.
