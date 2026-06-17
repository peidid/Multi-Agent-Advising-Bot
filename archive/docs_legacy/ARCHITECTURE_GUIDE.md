# Technical Architecture Guide
## Multi-Agent Academic Advising System

**Beginner-Friendly Explanation of How Everything Works**

---

## 🎯 What This System Does

Imagine you're a student asking: *"Can I add a CS minor? What courses do I need?"*

Instead of one AI trying to know everything, this system uses **5 specialized AI agents** that work together:
1. **Programs Agent** - Knows about majors/minors/requirements
2. **Courses Agent** - Knows about courses, schedules, prerequisites  
3. **Policy Agent** - Knows about university rules and policies
4. **Planning Agent** - Creates semester-by-semester course plans
5. **Coordinator** - The "boss" that makes them all work together

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                       │
│  (chat.py or streamlit_app_agent_view.py)              │
└────────────────────┬──────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              COORDINATOR (The Boss)                     │
│  (coordinator/coordinator.py)                           │
│  • Understands what user wants                          │
│  • Decides which agents to use                          │
│  • Manages workflow                                    │
│  • Detects conflicts                                    │
│  • Combines answers into final response                │
└─────┬───────────┬───────────┬───────────┬─────────────┘
      │           │           │           │
      ▼           ▼           ▼           ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Programs  │ │ Courses  │ │ Policy   │ │Planning  │
│ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │
└────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
     │            │             │            │
     ▼            ▼             ▼            ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│Vector DB │ │Vector DB │ │Vector DB │ │Uses other│
│Programs  │ │Courses   │ │Policies  │ │agents    │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
```

**Key Concept**: Agents don't talk to each other directly. They all write to and read from a shared "blackboard" (like a whiteboard everyone can see).

---

## 📁 File Structure Explained

### 🎮 **Entry Points** (Where Users Start)

#### `chat.py`
- **What it does**: Terminal-based chat interface
- **How it works**: 
  - Takes user input
  - Calls `multi_agent.py` to process query
  - Displays the response
- **When to use**: Testing, development, simple interactions

#### `streamlit_app_agent_view.py` 
- **What it does**: Beautiful web interface with visualizations
- **How it works**:
  - Creates web UI using Streamlit
  - Shows real-time agent activity
  - Displays workflow visualization
- **When to use**: Demos, presentations, user-facing application

---

### 🧠 **Core System Files**

#### `multi_agent.py` ⭐ **THE MAIN WORKFLOW**
- **What it does**: Defines the entire multi-agent workflow using LangGraph
- **Key Components**:
  - **Nodes**: Functions that represent each step (coordinator, programs, courses, etc.)
  - **Edges**: Routes between nodes (decides what happens next)
  - **State Graph**: Manages the flow from start to finish
- **How it works**:
  1. User query comes in
  2. Goes to Coordinator node
  3. Coordinator decides which agents to activate
  4. Each agent executes in sequence
  5. Results go back to Coordinator
  6. Coordinator synthesizes final answer
- **Think of it as**: The "conductor" of an orchestra - it doesn't play music, but makes sure everyone plays at the right time

#### `coordinator/coordinator.py` 🎯 **THE BOSS**
- **What it does**: Orchestrates the entire system
- **Key Responsibilities**:
  1. **Intent Classification**: Understands what user wants
     - "What are IS requirements?" → Needs Programs Agent
     - "When is 15-112 offered?" → Needs Courses Agent
     - "Can I take overload?" → Needs Policy Agent
  2. **Workflow Planning**: Decides execution order
     - Some queries need multiple agents
     - Plans the sequence
  3. **Conflict Detection**: Finds contradictions
     - Programs Agent: "You need 15-213"
     - Policy Agent: "You can't take 15-213 yet"
     - Coordinator detects this conflict
  4. **Negotiation Management**: Makes agents resolve conflicts
  5. **Answer Synthesis**: Combines all agent outputs into one coherent answer
- **Uses**: `coordinator/llm_driven_coordinator.py` for smart decision-making

#### `blackboard/schema.py` 📋 **THE SHARED WHITEBOARD**
- **What it does**: Defines the structure of shared state
- **Key Concept**: All agents read/write to this shared state
- **Contains**:
  - `BlackboardState`: The main state dictionary
    - `user_query`: What the user asked
    - `student_profile`: Student info (major, GPA, completed courses)
    - `agent_outputs`: What each agent said
    - `conflicts`: Any conflicts detected
    - `workflow_step`: Current stage (initial, execution, synthesis, etc.)
  - `AgentOutput`: Structured format for agent responses
  - `Conflict`: Format for conflicts
  - `PlanOption`: Format for course plans
- **Why it matters**: Ensures agents can understand each other's outputs

---

### 🤖 **Agent Files** (The Specialists)

All agents inherit from `agents/base_agent.py`:

#### `agents/base_agent.py` 🏛️ **THE FOUNDATION**
- **What it does**: Base class that all agents inherit from
- **Provides**:
  - Connection to domain-specific vector database (RAG)
  - LLM instance for reasoning
  - `retrieve_context()` method to search knowledge base
  - `execute()` method (each agent implements differently)
- **Key Pattern**: Each agent has its own "domain" (programs, courses, policies)

#### `agents/programs_agent.py` 📚 **THE REQUIREMENTS EXPERT**
- **What it does**: Handles major/minor requirements, degree progress
- **Knowledge Base**: `data/programs/` folder
- **Capabilities**:
  - Checks if student meets requirements
  - Validates course plans against degree requirements
  - Identifies missing courses
  - Suggests course sequences
- **Example Query**: "What are the IS major requirements?"
- **Uses**: Programs vector database (`chroma_db_programs/`)

#### `agents/courses_agent.py` 📅 **THE SCHEDULING EXPERT**
- **What it does**: Provides course information, schedules, prerequisites
- **Knowledge Base**: `data/courses/` folder + `data/schedules/` folder
- **Capabilities**:
  - Course descriptions and prerequisites
  - Schedule information (when courses are offered)
  - Time conflict detection
  - Course availability checking
- **Example Query**: "When is 15-112 offered? What are its prerequisites?"
- **Uses**: Courses vector database (`chroma_db_courses/`)

#### `agents/policy_agent.py` ⚖️ **THE RULES EXPERT**
- **What it does**: Ensures compliance with university policies
- **Knowledge Base**: `data/policies/` folder
- **Capabilities**:
  - Checks course overload limits
  - Validates registration policies
  - Identifies policy violations
  - Explains academic rules
- **Example Query**: "Can I take more than 54 units?"
- **Uses**: Policies vector database (`chroma_db_policies/`)

#### `agents/planning_agent.py` 📊 **THE PLANNER**
- **What it does**: Creates semester-by-semester course plans
- **Knowledge Base**: Uses other agents! (collaborates)
- **Capabilities**:
  - Generates complete graduation plans
  - Balances workload across semesters
  - Respects prerequisites
  - Considers course availability (Fall-only, Spring-only)
- **Example Query**: "Help me plan my courses until graduation"
- **How it works**:
  1. Asks Programs Agent for requirements
  2. Asks Courses Agent for availability
  3. Asks Policy Agent for constraints
  4. Creates optimized plan
  5. Revises if conflicts found

---

### 🔍 **RAG (Retrieval-Augmented Generation) System**

#### `rag_engine_improved.py` 🔎 **THE KNOWLEDGE RETRIEVER**
- **What it does**: Manages domain-specific vector databases
- **How it works**:
  1. **Loading**: Reads documents from `data/` folders
  2. **Splitting**: Breaks documents into chunks
  3. **Embedding**: Converts text to vectors (numbers that represent meaning)
  4. **Storing**: Saves to ChromaDB vector database
  5. **Retrieving**: Searches for relevant chunks when agents query
- **Key Function**: `get_retriever(domain, k=5)`
  - Returns a retriever for a specific domain
  - `k=5` means "return top 5 most relevant chunks"
- **Domains**:
  - `"programs"` → `chroma_db_programs/`
  - `"courses"` → `chroma_db_courses/`
  - `"policies"` → `chroma_db_policies/`

#### `setup_domain_indexes.py` 🏗️ **THE BUILDER**
- **What it does**: Builds vector databases from source documents
- **When to run**: 
  - First time setup
  - After adding new documents
  - When rebuilding indexes
- **How it works**:
  1. Scans `data/` folders
  2. Loads documents (JSON, Markdown, PDF)
  3. Splits into chunks
  4. Creates embeddings
  5. Stores in ChromaDB
- **Output**: Creates `chroma_db_programs/`, `chroma_db_courses/`, `chroma_db_policies/`

#### `rebuild_indexes_with_metadata.py` ✨ **THE ENHANCED BUILDER**
- **What it does**: Same as above, but adds rich metadata
- **Metadata includes**:
  - File name and type
  - Program mentioned
  - Courses mentioned
  - Document summary
- **Why better**: Agents can cite sources and understand context better

---

### ⚙️ **Configuration & Utilities**

#### `config.py` 🎛️ **THE SETTINGS**
- **What it does**: Centralized model configuration
- **Key Settings**:
  - `COORDINATOR_MODEL`: Model for Coordinator (default: "gpt-4-turbo")
  - `AGENT_MODEL`: Model for Agents (default: "gpt-4o")
  - Temperature settings (controls randomness)
- **Why separate models**: 
  - Coordinator needs powerful reasoning → GPT-4 Turbo
  - Agents do simpler tasks → GPT-4o (faster, cheaper)

#### `course_tools.py` 🛠️ **COURSE UTILITIES**
- **What it does**: Helper functions for course data
- **Functions**:
  - Course code parsing
  - Prerequisite checking
  - Course information lookup
- **Used by**: Courses Agent, Planning Agent

#### `planning_tools.py` 📋 **PLANNING UTILITIES**
- **What it does**: Helper functions for course planning
- **Functions**:
  - Semester planning algorithms
  - Workload balancing
  - Prerequisite resolution
- **Used by**: Planning Agent

#### `course_name_mapping.py` 🔄 **NAME MAPPING**
- **What it does**: Maps course names to course codes
- **Example**: "Introduction to Programming" → "15-112"
- **Used by**: Agents to normalize course references

---

### 📊 **Data Files**

#### `data/programs/` 📚
- **Contains**: Major/minor requirements, degree information
- **Formats**: JSON, Markdown
- **Examples**:
  - `IS_Requirements.json` - IS major requirements
  - `CS_Major_sample_curriculum.json` - CS curriculum
  - `Concentration_Requirement.md` - Concentration info

#### `data/courses/` 📅
- **Contains**: Course descriptions, prerequisites, schedules
- **Formats**: JSON
- **Examples**:
  - `15-112.json` - Course description
  - `schedule_2026_spring.json` - Spring 2026 schedule
  - `course_offering_patterns.json` - Which semesters courses are offered

#### `data/policies/` ⚖️
- **Contains**: University policies, rules, regulations
- **Formats**: Markdown, JSON
- **Examples**:
  - Course overload policies
  - Registration rules
  - Academic standing policies

#### `data/schedules/` 📆 **NEW!**
- **Contains**: Processed schedule data in JSON format
- **Files**:
  - `schedule_2024_fall.json` - Fall 2024 offerings
  - `schedule_2025_fall.json` - Fall 2025 offerings
  - `schedule_2025_spring.json` - Spring 2025 offerings
  - `schedule_2026_spring.json` - Spring 2026 offerings
  - `course_offering_patterns.json` - Aggregated patterns
- **Generated by**: `process_schedules_final.py`

---

### 🔧 **Setup & Maintenance Scripts**

#### `setup_domain_indexes.py`
- **Purpose**: Build vector databases (basic version)
- **Run when**: First setup, adding documents

#### `rebuild_indexes_with_metadata.py`
- **Purpose**: Build vector databases with metadata (recommended)
- **Run when**: First setup, adding documents, want better citations

#### `process_schedules_final.py`
- **Purpose**: Converts CSV schedule files to JSON
- **Input**: CSV files in `data/courses/schedule/`
- **Output**: JSON files in `data/schedules/`
- **Run when**: New schedule data available

#### `generate_document_metadata.py`
- **Purpose**: Analyzes documents and generates metadata
- **Used by**: `rebuild_indexes_with_metadata.py`

---

## 🔄 **How It All Works Together: Step-by-Step**

### Example: "Can I add a CS minor? What courses do I need?"

**Step 1: User Input** (`chat.py`)
```
User: "Can I add a CS minor? What courses do I need?"
```

**Step 2: Workflow Starts** (`multi_agent.py`)
- Creates initial `BlackboardState`
- Sets `user_query` = "Can I add a CS minor..."
- Sets `workflow_step` = `INITIAL`

**Step 3: Coordinator Node** (`coordinator/coordinator.py`)
- **Intent Classification**:
  - Analyzes query
  - Determines: Needs Programs Agent + Courses Agent
  - Sets `active_agents` = ["programs_requirements", "course_scheduling"]
  - Sets `workflow_step` = `AGENT_EXECUTION`

**Step 4: Programs Agent Executes** (`agents/programs_agent.py`)
- Reads `user_query` from Blackboard
- Calls `retrieve_context("CS minor requirements")`
  - `rag_engine_improved.py` searches `chroma_db_programs/`
  - Returns relevant chunks about CS minor
- Uses LLM to process information
- Writes `AgentOutput` to Blackboard:
  ```python
  {
    "agent_name": "programs_requirements",
    "answer": "Yes, you can add a CS minor. You need: 15-150, 15-210, 15-213 or 15-251...",
    "confidence": 0.95,
    "relevant_policies": ["CS_Minor_Requirements.json"],
    "risks": [],
    "constraints": []
  }
  ```

**Step 5: Courses Agent Executes** (`agents/courses_agent.py`)
- Reads `user_query` and Programs Agent output
- Calls `retrieve_context("15-150 prerequisites schedule")`
  - Searches `chroma_db_courses/`
- Checks `data/schedules/course_offering_patterns.json` for availability
- Writes `AgentOutput`:
  ```python
  {
    "agent_name": "course_scheduling",
    "answer": "15-150 is offered Fall only. Prerequisites: 15-112...",
    "confidence": 0.90
  }
  ```

**Step 6: Coordinator Checks** (`coordinator/coordinator.py`)
- Reads all `agent_outputs` from Blackboard
- **Conflict Detection**: No conflicts found
- Sets `workflow_step` = `SYNTHESIS`

**Step 7: Coordinator Synthesizes** (`coordinator/coordinator.py`)
- Combines Programs + Courses outputs
- Creates human-like response:
  ```
  "Yes, you can add a CS minor! Here's what you need:
  
  Required Courses:
  - 15-150: Principles of Functional Programming (Fall only)
  - 15-210: Parallel Data Structures (Spring only)
  - 15-213: Computer Systems (Fall only) OR 15-251: Theoretical CS (Spring)
  
  Note: Plan carefully - 15-150 must be taken in Fall before 15-210 in Spring..."
  ```

**Step 8: Response Returned** (`chat.py`)
- Displays final answer to user

---

## 🎨 **Key Design Patterns**

### 1. **Blackboard Pattern**
- **What**: Shared state that all agents read/write to
- **Why**: Agents don't communicate directly (cleaner, more scalable)
- **File**: `blackboard/schema.py`
- **📖 Detailed Guide**: See `AGENT_COMMUNICATION.md` for complete explanation of how agents communicate

### 2. **Hub-and-Spoke Topology**
- **What**: Coordinator in center, agents around it
- **Why**: Centralized control, easier to manage
- **File**: `multi_agent.py` (graph structure)

### 3. **Domain-Specific RAG**
- **What**: Each agent has its own knowledge base
- **Why**: More focused, better accuracy, faster retrieval
- **File**: `rag_engine_improved.py`

### 4. **Structured Output**
- **What**: Agents return `AgentOutput` objects (not just text)
- **Why**: Enables conflict detection, structured reasoning
- **File**: `blackboard/schema.py`

### 5. **Workflow State Machine**
- **What**: System moves through defined states
- **States**: INITIAL → AGENT_EXECUTION → SYNTHESIS → COMPLETE
- **Why**: Clear control flow, easier debugging
- **File**: `blackboard/schema.py` (WorkflowStep enum)

---

## 🔍 **Understanding the Flow**

### State Transitions

```
INITIAL
  ↓ (Coordinator classifies intent)
AGENT_EXECUTION
  ↓ (Agents execute)
CONFLICT_RESOLUTION (if conflicts found)
  ↓ (Agents negotiate)
SYNTHESIS
  ↓ (Coordinator combines answers)
COMPLETE
```

### Data Flow

```
User Query
  ↓
BlackboardState (user_query)
  ↓
Coordinator (classifies, plans)
  ↓
BlackboardState (active_agents, workflow_step)
  ↓
Agent 1 (reads state, writes output)
  ↓
BlackboardState (agent_outputs["agent1"])
  ↓
Agent 2 (reads state, writes output)
  ↓
BlackboardState (agent_outputs["agent2"])
  ↓
Coordinator (reads all outputs, detects conflicts)
  ↓
BlackboardState (conflicts, if any)
  ↓
Coordinator (synthesizes final answer)
  ↓
User Response
```

---

## 🛠️ **Common Tasks & Which Files to Edit**

### Adding a New Agent
1. Create `agents/new_agent.py` (inherit from `BaseAgent`)
2. Add domain to `rag_engine_improved.py` (`DOMAIN_PATHS`)
3. Register in `multi_agent.py` (create node function)
4. Add to `coordinator.py` (`available_agents` list)
5. Rebuild indexes: `python rebuild_indexes_with_metadata.py`

### Adding New Data
1. **Programs Data**: Add files to `data/programs/`
2. **Courses Data**: Add files to `data/courses/`
3. **Policy Data**: Add files to `data/policies/`
4. Rebuild indexes: `python rebuild_indexes_with_metadata.py`

### Changing Models
1. Edit `config.py`
2. Change `COORDINATOR_MODEL` or `AGENT_MODEL`
3. Restart system

### Modifying Workflow
1. Edit `multi_agent.py`
2. Modify nodes or edges
3. Test with `python chat.py`

---

## 📚 **Key Concepts for Beginners**

### **What is RAG?**
- **RAG** = Retrieval-Augmented Generation
- **Problem**: LLMs don't know your specific data
- **Solution**: 
  1. Store your data in a vector database
  2. When query comes, search database for relevant info
  3. Give that info to LLM along with query
  4. LLM generates answer using your data
- **File**: `rag_engine_improved.py`

### **What is LangGraph?**
- **LangGraph** = Framework for building agent workflows
- **Concepts**:
  - **Nodes**: Functions that do work (agents, coordinator)
  - **Edges**: Routes between nodes (decides what happens next)
  - **State**: Shared data that flows through graph
- **File**: `multi_agent.py`

### **What is a Vector Database?**
- **Vector Database** = Database that stores text as vectors (numbers)
- **Why**: Can search by meaning, not just keywords
- **Example**: "programming course" matches "15-112: Fundamentals of Programming"
- **Technology**: ChromaDB (used here)
- **Files**: `chroma_db_programs/`, `chroma_db_courses/`, `chroma_db_policies/`

### **What is the Blackboard?**
- **Blackboard** = Shared state that all agents can read/write
- **Like**: A whiteboard everyone can see and write on
- **Why**: Agents don't need to know about each other
- **File**: `blackboard/schema.py`

---

## 🎓 **Learning Path**

### **Beginner** (Start Here)
1. Read this document
2. Run `python chat.py` and try some queries
3. Look at `agents/base_agent.py` to understand agent structure
4. Check `blackboard/schema.py` to see data structures

### **Intermediate**
1. Read `multi_agent.py` to understand workflow
2. Study `coordinator/coordinator.py` to see coordination logic
3. Look at one agent implementation (e.g., `agents/programs_agent.py`)
4. Understand RAG in `rag_engine_improved.py`

### **Advanced**
1. Modify workflow in `multi_agent.py`
2. Add new agent capabilities
3. Customize conflict detection
4. Optimize RAG retrieval

---

## 🐛 **Debugging Guide**

### **Agent Not Responding**
- Check: Is vector database built? (`chroma_db_*/` folders exist?)
- Fix: Run `python rebuild_indexes_with_metadata.py`

### **Wrong Agent Activated**
- Check: `coordinator/coordinator.py` intent classification
- Fix: Adjust prompts in `coordinator/llm_driven_coordinator.py`

### **Poor Quality Answers**
- Check: Is metadata enabled? (better citations)
- Fix: Rebuild with `python rebuild_indexes_with_metadata.py`
- Check: Is data in correct folders?
- Fix: Verify `data/programs/`, `data/courses/`, `data/policies/`

### **Slow Performance**
- Check: Model configuration (`config.py`)
- Fix: Use faster models for agents (`gpt-4o` is good)
- Check: RAG retrieval count (`k=5` in `get_retriever()`)
- Fix: Reduce `k` for faster retrieval (but less context)

---

## 📖 **Further Reading**

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangChain Docs**: https://python.langchain.com/
- **ChromaDB Docs**: https://www.trychroma.com/
- **Project README**: `README.md` (overview and quick start)
- **Planning Guide**: `PLANNING_GUIDE.md` (academic planning feature)

---

## ✅ **Summary**

**The Big Picture:**
1. **User asks question** → `chat.py`
2. **Coordinator understands** → `coordinator/coordinator.py`
3. **Agents retrieve knowledge** → `rag_engine_improved.py` + vector DBs
4. **Agents process** → `agents/*.py`
5. **Coordinator combines** → `coordinator/coordinator.py`
6. **User gets answer** → `chat.py`

**Key Files:**
- `multi_agent.py` - Main workflow
- `coordinator/coordinator.py` - The boss
- `agents/base_agent.py` - Agent foundation
- `blackboard/schema.py` - Shared state
- `rag_engine_improved.py` - Knowledge retrieval

**Remember**: Agents don't talk to each other - they all write to the Blackboard, and the Coordinator reads it all and makes decisions!

---

**Questions?** Check the other documentation files or explore the code - it's well-commented! 🚀
