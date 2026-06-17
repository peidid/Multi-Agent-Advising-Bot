# AdvisingBot Progress Report

**Date:** February 14, 2026
**Target:** ACL 2026 Demo Track
**Institution:** Carnegie Mellon University - Qatar

---

## Executive Summary

AdvisingBot is a **multi-agent academic advising system** designed to demonstrate novel coordination and negotiation protocols for the ACL 2026 Demo Track. The project has made **significant progress** from the initial vision, implementing core infrastructure and achieving approximately **70% overall completion**.

| Category | Status | Progress |
|----------|--------|----------|
| Core Architecture | Complete | 100% |
| Agent Implementation | Complete | 100% |
| LLM-Driven Coordination | Complete | 100% |
| RAG Knowledge Base | Complete | 100% |
| Conversation Memory | Complete | 100% |
| Academic Planning Agent | Complete | 100% |
| Streaming/UI Events | Complete | 100% |
| **Negotiation Protocol** | **Partial** | **40%** |
| Interactive Conflict Resolution | Partial | 30% |
| Evaluation Framework | Not Started | 0% |
| Paper & Demo | Not Started | 0% |

**Overall Progress: ~70%**

---

## 1. Original Vision (Proposals)

### 1.1 Proposal 1: System Design Vision

The first proposal outlined a comprehensive multi-agent academic advising system with:

- **5-12 Specialized Agents** covering:
  - Academic Departments (majors)
  - Course Information
  - Minor Requirements
  - University-level Policies
  - Events & Activities
  - Career Advice
  - Research Opportunities
  - People/Faculty Directory

- **Dynamic Workflow Orchestration:**
  - Hub-and-spoke topology with a central Coordinator
  - Blackboard-based shared state (no direct agent-to-agent communication)
  - Dynamic routing based on user intent

- **Key Features:**
  - History/memory integration for personalization
  - Interactive conflict resolution with user agency
  - Visible negotiation process

### 1.2 Proposal 2: Research-Level Refinement

The advisor feedback refined the vision into a **research-ready** system:

**Agent Consolidation** (5-7 core agents instead of 12):
1. **Orchestrator/Main Advisor** - Intent classification, workflow planning
2. **Student Profile & Memory Agent** - Personalization
3. **Programs & Requirements Agent** - Major/minor requirements
4. **Course & Scheduling Agent** - Course info, conflicts
5. **Policy & Compliance Agent** - University policies
6. **Opportunities Agent** - Career, research, events (optional)

**Research Contribution Requirements:**
- **Structured Negotiation Protocol:** Proposal + Critique mechanism
- **Interactive Conflict Resolution:** 3 canonical conflict types
- **Explicit Research Questions:** Clear RQs and evaluation metrics
- **Typed Blackboard Schema:** Structured data over free-form prose

**Evaluation Framework:**
- 50 test scenarios with gold standards
- 3 baseline systems for comparison
- Metrics: correctness, safety, user satisfaction

---

## 2. System Architecture (Comprehensive)

### 2.1 High-Level Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACES                                │
├──────────────────┬──────────────────┬──────────────────┬───────────────────┤
│   chat.py        │  Streamlit App   │  FastAPI Server  │  Next.js Frontend │
│   (Terminal)     │  (Demo UI)       │  (REST API)      │  (Web App)        │
└────────┬─────────┴────────┬─────────┴────────┬─────────┴─────────┬─────────┘
         │                  │                  │                   │
         └──────────────────┴────────┬─────────┴───────────────────┘
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         MULTI-AGENT WORKFLOW                                │
│                          (multi_agent.py)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                    LangGraph StateGraph                               │  │
│  │  START → coordinator_node → parallel_agents_node → synthesize → END  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   COORDINATOR   │     │   SPECIALIZED       │     │    BLACKBOARD       │
│   (Orchestrator)│◄───►│   AGENTS            │◄───►│    (Shared State)   │
└─────────────────┘     └─────────────────────┘     └─────────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  LLM-Driven     │     │  Domain-Specific    │     │  Structured Schema  │
│  Coordination   │     │  RAG Retrieval      │     │  (Pydantic Models)  │
└─────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### 2.2 Complete Project Structure

```
AdvisingBot/
│
├── 📁 agents/                          # SPECIALIZED AGENTS (2,340 LOC)
│   ├── __init__.py
│   ├── base_agent.py                   # Abstract base class (311 LOC)
│   │   ├── BaseAgent ABC
│   │   ├── RAG retriever initialization
│   │   ├── Streaming event emitters
│   │   ├── Coordinator task/feedback handling
│   │   └── Memory context formatting
│   ├── programs_agent.py               # Programs & Requirements (223 LOC)
│   │   └── ProgramsRequirementsAgent
│   ├── courses_agent.py                # Course & Scheduling (555 LOC)
│   │   ├── CourseSchedulingAgent
│   │   ├── Reference resolution (_is_reference_query, _get_most_recent_course)
│   │   └── Schedule lookup integration
│   ├── policy_agent.py                 # Policy & Compliance (242 LOC)
│   │   └── PolicyComplianceAgent
│   └── planning_agent.py               # Academic Planning (1,009 LOC)
│       ├── AcademicPlanningAgent
│       ├── Semester-by-semester planning
│       ├── Prerequisite validation
│       └── Workload balancing
│
├── 📁 coordinator/                     # ORCHESTRATION LAYER (2,235 LOC)
│   ├── __init__.py
│   ├── coordinator.py                  # Main Coordinator (748 LOC)
│   │   ├── Coordinator class
│   │   ├── classify_intent() - LLM-driven intent analysis
│   │   ├── plan_workflow() - Dynamic agent selection
│   │   ├── detect_conflicts() - Conflict detection
│   │   ├── manage_negotiation() - Negotiation loop
│   │   ├── synthesize_answer() - Final answer generation
│   │   └── evaluate_outputs_for_sufficiency() - Quality scoring
│   ├── llm_driven_coordinator.py       # LLM Reasoning Engine (523 LOC)
│   │   ├── LLMDrivenCoordinator class
│   │   ├── AgentCapability dataclass
│   │   ├── WorkflowPlan dataclass
│   │   ├── understand_and_plan() - Full LLM reasoning
│   │   └── adapt_workflow() - Dynamic adaptation
│   ├── clarification_handler.py        # User Clarification (231 LOC)
│   │   └── ClarificationHandler
│   ├── intent_classifier_enhanced.py   # Enhanced Classification (419 LOC)
│   │   └── IntentClassifierEnhanced
│   └── finetuned_classifier.py         # Fine-tuned Fast Routing (314 LOC)
│       └── FineTunedClassifier
│
├── 📁 blackboard/                      # SHARED STATE SCHEMA
│   ├── __init__.py
│   └── schema.py                       # Typed Schema Definitions
│       ├── Enums: ConflictType, WorkflowStep
│       ├── Pydantic Models:
│       │   ├── Constraint
│       │   ├── Risk
│       │   ├── PlanOption
│       │   ├── AgentOutput
│       │   ├── Conflict
│       │   └── ExecutionMetadata
│       └── BlackboardState TypedDict
│
├── 📁 memory/                          # CONVERSATION MEMORY SYSTEM
│   ├── __init__.py
│   ├── memory_manager.py               # Central Memory Manager
│   │   ├── MemoryManager class
│   │   ├── Short-term entity tracking
│   │   ├── Long-term profile management
│   │   ├── Query enhancement
│   │   └── Profile auto-detection from conversation
│   ├── entity_tracker.py               # Entity Extraction & Tracking
│   │   ├── EntityTracker class
│   │   ├── Course code extraction
│   │   ├── Semester detection
│   │   └── Reference resolution
│   ├── context_formatter.py            # Context Formatting
│   │   ├── format_conversation_context()
│   │   ├── format_student_profile()
│   │   └── build_agent_context()
│   └── profile_manager.py              # Student Profile Persistence
│       ├── StudentProfile dataclass
│       ├── CourseRecord dataclass
│       └── ProfileManager class
│
├── 📁 planning/                        # COLLABORATIVE PLANNING MODE
│   ├── __init__.py
│   ├── schema.py                       # Planning Data Structures
│   │   ├── SemesterPlan
│   │   ├── CoursePlanJSON
│   │   ├── AgentCritique
│   │   ├── PlanningRound
│   │   └── PlanningSession
│   └── coordinator.py                  # Planning Coordinator
│       └── Multi-round negotiation logic
│
├── 📁 streaming/                       # REAL-TIME EVENT SYSTEM
│   ├── __init__.py
│   ├── events.py                       # Event Type Definitions
│   │   ├── EventType enum (20+ event types)
│   │   ├── AgentPhase enum
│   │   ├── StreamEvent dataclass
│   │   └── Event factory functions
│   └── callback.py                     # Event Emission
│       └── emit_event() - SSE broadcasting
│
├── 📁 backend/                         # FASTAPI REST API SERVER
│   ├── __init__.py
│   ├── server.py                       # FastAPI Application (1,200+ LOC)
│   │   ├── JWT Authentication
│   │   ├── REST Endpoints:
│   │   │   ├── POST /auth/login
│   │   │   ├── POST /auth/register
│   │   │   ├── GET /conversations
│   │   │   ├── POST /conversations
│   │   │   ├── POST /chat (streaming SSE)
│   │   │   └── GET /profile
│   │   └── MongoDB integration
│   ├── database.py                     # MongoDB Atlas Connection
│   │   ├── User CRUD operations
│   │   ├── Conversation management
│   │   └── Message persistence
│   └── requirements.txt
│
├── 📁 frontend/                        # NEXT.JS WEB APPLICATION
│   ├── src/
│   │   └── (Next.js pages & components)
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── 📁 data/                            # KNOWLEDGE BASE SOURCES
│   ├── programs/                       # Program Requirements
│   │   ├── Computer Science & AI/
│   │   ├── Information Systems/
│   │   ├── Business Administration/
│   │   ├── Biological Science/
│   │   └── Minors/
│   ├── courses/                        # Course Catalog (~2,400 JSON files)
│   │   └── {course_code}.json          # e.g., 15-112.json, 67-272.json
│   ├── policies/                       # University Policies (~30 files)
│   ├── schedules/                      # Semester Schedules
│   │   └── {term}_{year}_courses.json  # e.g., Spring_2026_courses.json
│   ├── Academic & Studies/             # Additional Resources
│   └── Your Life/                      # Student Life Resources
│
├── 📁 chroma_db_programs/              # Vector DB - Programs Domain
├── 📁 chroma_db_courses/               # Vector DB - Courses Domain
├── 📁 chroma_db_policies/              # Vector DB - Policies Domain
├── 📁 chroma_db_schedules/             # Vector DB - Schedules Domain
├── 📁 chroma_db_planning/              # Vector DB - Planning Domain
│
├── 📄 multi_agent.py                   # LANGGRAPH WORKFLOW (590 LOC)
│   ├── AGENT_REGISTRY - Agent instances
│   ├── coordinator_node() - Intent classification
│   ├── parallel_agents_node() - Parallel execution + evaluation loop
│   ├── synthesize_node() - Answer synthesis
│   ├── route_after_coordinator() - Conditional routing
│   ├── route_after_parallel() - Conflict checking
│   └── StateGraph compilation
│
├── 📄 rag_engine_improved.py           # RAG ENGINE (600+ LOC)
│   ├── DOMAIN_PATHS configuration
│   ├── Document loaders (MD, JSON, TXT)
│   ├── Text splitters (RecursiveCharacterTextSplitter)
│   ├── OpenAI embeddings
│   ├── ChromaDB vector stores
│   ├── Metadata extraction
│   └── get_retriever(domain, k) function
│
├── 📄 course_tools.py                  # COURSE UTILITIES (700+ LOC)
│   ├── load_data() - Course JSON loading
│   ├── load_schedules() - Schedule loading
│   ├── look_up_course_info(code)
│   ├── get_course_schedule(code, semester)
│   ├── check_prereqs_satisfied(course, completed)
│   ├── check_courses_conflict(courses, semester)
│   ├── validate_semester_plan(plan, profile)
│   └── validate_full_plan(plans, profile)
│
├── 📄 planning_tools.py                # PLANNING UTILITIES (400+ LOC)
│   ├── Workload calculation
│   ├── Prerequisite analysis
│   └── Schedule optimization
│
├── 📄 config.py                        # MODEL CONFIGURATION
│   ├── COORDINATOR_MODEL = "gpt-4-turbo"
│   ├── COORDINATOR_EVAL_MODEL = "gpt-5.2"
│   ├── AGENT_MODEL = "gpt-5.2"
│   ├── Temperature settings
│   └── OpenAI proxy support
│
├── 📄 chat.py                          # TERMINAL INTERFACE (1,400+ LOC)
│   ├── Interactive chat loop
│   ├── Development mode (@agent commands)
│   ├── Profile management
│   └── Conversation history display
│
├── 📄 streamlit_app_agent_view.py      # STREAMLIT DEMO UI
│   ├── Chat interface
│   ├── Agent visualization
│   ├── Workflow display
│   └── Blackboard state viewer
│
└── 📄 Supporting Files
    ├── setup_domain_indexes.py         # Build vector databases
    ├── rebuild_indexes_with_metadata.py
    ├── generate_document_metadata.py
    ├── requirements.txt
    ├── Dockerfile
    └── *.md documentation files
```

### 2.3 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

1. USER INPUT
   ┌─────────────┐
   │ User Query  │ "Can I add a CS minor as an IS student?"
   └──────┬──────┘
          │
          ▼
2. WORKFLOW INITIALIZATION
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ multi_agent.py: app.invoke(initial_state)                               │
   │                                                                          │
   │ BlackboardState = {                                                      │
   │   user_query: "Can I add a CS minor...",                                │
   │   student_profile: {major: ["IS"], gpa: 3.5, ...},                      │
   │   conversation_history: [...],                                           │
   │   agent_outputs: {},                                                     │
   │   workflow_step: WorkflowStep.INITIAL                                   │
   │ }                                                                        │
   └──────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
3. COORDINATOR NODE (Intent Classification + Workflow Planning)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ coordinator_node(state)                                                  │
   │                                                                          │
   │ ┌─────────────────────────────────────────────────────────────────────┐ │
   │ │ LLMDrivenCoordinator.understand_and_plan()                          │ │
   │ │                                                                      │ │
   │ │ Analysis:                                                            │ │
   │ │   • Understanding: Student wants to add CS minor                    │ │
   │ │   • Agents needed: programs_requirements, course_scheduling         │ │
   │ │   • Workflow: parallel execution                                    │ │
   │ │   • Tasks: {programs: "Check IS+CS minor compatibility",            │ │
   │ │            courses: "List CS minor requirements"}                   │ │
   │ └─────────────────────────────────────────────────────────────────────┘ │
   │                                                                          │
   │ Returns: {active_agents: [...], agent_tasks: {...}, ...}                │
   └──────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
4. PARALLEL AGENTS NODE (Concurrent Execution)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ parallel_agents_node(state)                                              │
   │                                                                          │
   │ ThreadPoolExecutor(max_workers=N)                                       │
   │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
   │ │  Programs   │  │  Courses    │  │  Policy     │  │  Planning   │      │
   │ │  Agent      │  │  Agent      │  │  Agent      │  │  Agent      │      │
   │ │             │  │             │  │             │  │             │      │
   │ │ 1. RAG      │  │ 1. RAG      │  │ 1. RAG      │  │ 1. RAG      │      │
   │ │ 2. LLM      │  │ 2. LLM      │  │ 2. LLM      │  │ 2. LLM      │      │
   │ │ 3. Output   │  │ 3. Output   │  │ 3. Output   │  │ 3. Output   │      │
   │ └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │
   │        │                │                │                │              │
   │        └────────────────┴────────────────┴────────────────┘              │
   │                                    │                                     │
   │                                    ▼                                     │
   │ ┌─────────────────────────────────────────────────────────────────────┐ │
   │ │ COORDINATOR EVALUATION LOOP (max 3 rounds)                          │ │
   │ │                                                                      │ │
   │ │ evaluate_outputs_for_sufficiency()                                  │ │
   │ │   • Quality score: 0-100                                            │ │
   │ │   • Per-agent feedback: {gaps, guidance, score}                     │ │
   │ │   • Decision: sufficient OR agents_to_rerun                         │ │
   │ │                                                                      │ │
   │ │ If insufficient → re-run agents with enhanced_k=10                  │ │
   │ └─────────────────────────────────────────────────────────────────────┘ │
   │                                                                          │
   │ Returns: {agent_outputs: {...}, risks: [...], execution_metadata: {...}}│
   └──────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
5. SYNTHESIS NODE (Answer Generation)
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ synthesize_node(state)                                                   │
   │                                                                          │
   │ coordinator.synthesize_answer()                                         │
   │   • Combines all agent outputs                                          │
   │   • Resolves any remaining conflicts                                    │
   │   • Generates human-like advisor response                               │
   │   • Includes policy citations                                           │
   │                                                                          │
   │ Returns: {messages: [final_answer], workflow_step: COMPLETE}            │
   └──────┬──────────────────────────────────────────────────────────────────┘
          │
          ▼
6. FINAL OUTPUT
   ┌─────────────┐
   │ Answer to   │ "Yes, as an IS student you can add the CS minor..."
   │ User        │
   └─────────────┘
```

### 2.4 Agent Execution Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SINGLE AGENT EXECUTION FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

BaseAgent.execute(state)
          │
          ▼
    ┌─────────────┐
    │ emit_start  │ ─────► Streaming: agent_start_event
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ get_memory_context(state)                                        │
    │   • Format conversation history                                  │
    │   • Format student profile                                       │
    │   • Build context string for prompt                              │
    └──────┬──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ get_assigned_task()                                              │
    │   • Retrieve coordinator's specific task for this query          │
    │   • E.g., "Check if 15-213 satisfies CS minor requirements"     │
    └──────┬──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │emit_retrieving│ ─────► Streaming: agent_retrieving_event
    └──────┬───────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ retrieve_context(query, k)                                       │
    │   • ChromaDB similarity search                                   │
    │   • Domain-specific vector store (chroma_db_{domain})           │
    │   • Default k=5-8, enhanced k=10 for re-retrieval               │
    │   • Returns concatenated document chunks                         │
    └──────┬──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────┐
    │emit_thinking │ ─────► Streaming: agent_thinking_event
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ LLM Generation (self.llm.invoke)                                 │
    │   • System prompt: Agent role + capabilities                     │
    │   • User prompt: Query + Context + Task                          │
    │   • Model: gpt-5.2 (AGENT_MODEL)                                │
    │   • Temperature: 0.3                                             │
    └──────┬──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │ Parse Response → AgentOutput                                     │
    │   • answer: str                                                  │
    │   • confidence: float (0.0-1.0)                                  │
    │   • relevant_policies: List[str]                                 │
    │   • risks: List[Risk]                                            │
    │   • constraints: List[Constraint]                                │
    │   • plan_options: Optional[List[PlanOption]]                     │
    └──────┬──────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │emit_complete │ ─────► Streaming: agent_complete_event
    └──────┬───────┘
           │
           ▼
    ┌─────────────┐
    │ Return      │ AgentOutput to multi_agent.py
    │ AgentOutput │
    └─────────────┘
```

### 2.5 Model Configuration

| Component | Model | Temperature | Purpose |
|-----------|-------|-------------|---------|
| **Coordinator (Routing)** | gpt-4-turbo | 0.3 | Intent classification, workflow planning, synthesis |
| **Coordinator (Evaluation)** | gpt-5.2 | 0.2 | Quality scoring, gap analysis, re-retrieval decisions |
| **All Agents** | gpt-5.2 | 0.3 | Domain-specific RAG + reasoning |

### 2.6 Knowledge Base Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE BASE SYSTEM                                │
└─────────────────────────────────────────────────────────────────────────────┘

DOMAIN_PATHS (rag_engine_improved.py):
─────────────────────────────────────────────────────────────────────────────
Domain        │ Source Folders              │ ChromaDB Path
─────────────────────────────────────────────────────────────────────────────
programs      │ data/programs/              │ chroma_db_programs/
courses       │ data/courses/, schedules/   │ chroma_db_courses/
policies      │ data/policies/              │ chroma_db_policies/
schedules     │ data/schedules/             │ chroma_db_schedules/
planning      │ data/programs/, schedules/  │ chroma_db_planning/
─────────────────────────────────────────────────────────────────────────────

Document Processing Pipeline:
─────────────────────────────────────────────────────────────────────────────
1. Load documents (DirectoryLoader)
   ├── .md files → TextLoader
   ├── .json files → Custom JSON parser
   └── .txt files → TextLoader

2. Extract metadata
   ├── Program/course detection
   ├── Course code extraction (regex: \b\d{2}-\d{3,4}\b)
   └── Document type classification

3. Split into chunks
   └── RecursiveCharacterTextSplitter
       ├── chunk_size: 1000
       └── chunk_overlap: 200

4. Generate embeddings
   └── OpenAIEmbeddings()

5. Store in ChromaDB
   └── Separate collection per domain
─────────────────────────────────────────────────────────────────────────────

Document Statistics:
─────────────────────────────────────────────────────────────────────────────
Domain      │ Files  │ Description
─────────────────────────────────────────────────────────────────────────────
programs    │ ~50    │ Major/minor requirements (MD + JSON)
courses     │ ~2,400 │ Full course catalog (JSON per course)
policies    │ ~30    │ University policies (MD)
schedules   │ ~200   │ Semester offerings (JSON)
─────────────────────────────────────────────────────────────────────────────
Total       │ ~2,700 │ Source files → 5 vector databases
─────────────────────────────────────────────────────────────────────────────
```

### 2.7 Streaming Event System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STREAMING EVENTS                                     │
└─────────────────────────────────────────────────────────────────────────────┘

Event Categories:
─────────────────────────────────────────────────────────────────────────────

WORKFLOW EVENTS:
  • workflow_start         → Query received
  • workflow_complete      → Final answer ready

COORDINATOR EVENTS:
  • coordinator_thinking   → Analyzing query
  • coordinator_routing    → Agent selection decision
  • coordinator_conflict   → Conflict detected
  • coordinator_evaluation → Quality evaluation result

AGENT LIFECYCLE:
  • agent_start            → Agent activated
  • agent_retrieving       → RAG search in progress
  • agent_thinking         → LLM processing
  • agent_output           → Full response available
  • agent_complete         → Agent finished
  • agent_error            → Agent failed

SYNTHESIS EVENTS:
  • synthesis_start        → Combining outputs
  • synthesis_streaming    → Token-by-token output
  • synthesis_complete     → Final answer generated

PLANNING MODE EVENTS:
  • planning_session_start → Planning session begins
  • planning_round_start   → Negotiation round begins
  • planning_proposing     → Agent proposing plan
  • planning_proposal      → Plan proposed
  • planning_critiquing    → Agent critiquing plan
  • planning_critique      → Critique received
  • planning_round_complete→ Round finished
  • planning_complete      → Planning finished

─────────────────────────────────────────────────────────────────────────────

StreamEvent Format (SSE):
─────────────────────────────────────────────────────────────────────────────
{
  "type": "agent_complete",
  "timestamp": "2026-02-14T12:30:00.000Z",
  "agent": "programs_requirements",
  "phase": "complete",
  "message": "Analysis complete",
  "data": {
    "confidence": 0.92,
    "summary": "IS student can add CS minor..."
  }
}
─────────────────────────────────────────────────────────────────────────────
```

### 2.8 Memory System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MEMORY SYSTEM                                        │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────┐
                    │       MemoryManager         │
                    │    (memory_manager.py)      │
                    └──────────────┬──────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │  EntityTracker  │  │ ProfileManager  │  │ContextFormatter │
    │  (Short-term)   │  │  (Long-term)    │  │    (Utility)    │
    └─────────────────┘  └─────────────────┘  └─────────────────┘
              │                    │                    │
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ • Course codes  │  │ • StudentProfile│  │ • History format│
    │ • Semesters     │  │ • CourseRecord  │  │ • Profile format│
    │ • Recent topics │  │ • DB persistence│  │ • Agent context │
    └─────────────────┘  └─────────────────┘  └─────────────────┘

Short-term Memory (per conversation):
─────────────────────────────────────────────────────────────────────────────
• Recent entities mentioned (courses, semesters, topics)
• Last N conversation turns
• Reference tracking ("it" → last mentioned course)

Long-term Memory (persistent):
─────────────────────────────────────────────────────────────────────────────
• Student profile (major, GPA, completed courses)
• Course history with grades
• Career goals and interests
• MongoDB Atlas storage (backend/)
```

---

## 3. Current Implementation Status

### 3.1 Completed Components (100%)

| Component | Description | LOC |
|-----------|-------------|-----|
| **agents/** | 4 specialized agents with RAG | 2,340 |
| **coordinator/** | LLM-driven orchestration | 2,235 |
| **blackboard/** | Typed state schema | 200 |
| **memory/** | Conversation + profile memory | 600 |
| **planning/** | Collaborative planning schema | 200 |
| **streaming/** | Real-time event system | 500 |
| **multi_agent.py** | LangGraph workflow | 590 |
| **rag_engine_improved.py** | Domain RAG engine | 600 |
| **course_tools.py** | Course utilities | 700 |
| **chat.py** | Terminal interface | 1,400 |
| **backend/** | FastAPI + MongoDB | 1,500+ |
| **frontend/** | Next.js web app | - |

**Total Core Code:** ~10,000+ lines

### 3.2 Agent Capabilities Summary

| Agent | Domain | Capabilities | RAG Index |
|-------|--------|--------------|-----------|
| **Programs** | programs | Major/minor requirements, degree progress, plan validation | chroma_db_programs |
| **Courses** | courses | Course info, prerequisites, schedules, conflicts | chroma_db_courses |
| **Policy** | policies | University policies, compliance, risk flagging | chroma_db_policies |
| **Planning** | planning | Semester plans, workload balance, prereq ordering | chroma_db_planning |

### 3.3 Recent Commits (Feb 2026)

| Commit | Description |
|--------|-------------|
| dfc0c77 | Fix course code extraction for 5-digit format |
| 86b3bea | Add coordinator task instructions for agents |
| 2764a51 | Fix plan validation to use student's completed courses |
| caedac1 | Add prerequisite and schedule conflict validation |
| 1f5624e | Enhance Planning agent schedule access |
| 73b22c5 | Fix planning agent query scope detection |
| 99953ae | Fix synthesis format adaptation |
| 49be179 | Coordinator-evaluated confidence with GPT-5.2 |

---

## 4. Gap Analysis: What's Missing

### 4.1 Structured Negotiation Protocol (40% Complete)

**Current State:**
- Conflict detection exists in `coordinator.detect_conflicts()`
- `planning/schema.py` has `AgentCritique`, `PlanningRound` structures
- Coordinator evaluation loop implemented

**What's Missing:**
- Formal **Proposal + Critique** execution flow
- **Visible negotiation** UI to users
- Multi-round agent back-and-forth for non-planning queries
- Structured resolution tracking

### 4.2 Interactive Conflict Resolution (30% Complete)

**Current State:**
- `ConflictType` enum: HARD_VIOLATION, HIGH_RISK, TRADE_OFF
- Conflicts detected but only logged

**What's Missing:**
- UI widgets for each conflict type
- User input handling mid-workflow
- Workflow adaptation based on user choice

### 4.3 Evaluation Framework (0% Complete)

| Component | Status |
|-----------|--------|
| 50 test scenarios | Not started |
| Gold standard answers | Not started |
| 3 baseline systems | Not started |
| Automatic metrics | Not started |
| Human evaluation | Not started |

### 4.4 Paper & Demo (0% Complete)

- 4-6 page paper
- Demo video (3-5 min)
- Code release

---

## 5. Research Contribution Position

### Unique Contribution:

> **"Structured negotiation protocols in multi-agent systems with interactive conflict resolution for safety-critical domains"**

### Research Questions:

- **RQ1:** Does coordinator-based multi-agent advising improve recommendation quality/safety vs. single-agent RAG?
- **RQ2:** Does visible agent negotiation increase user trust?
- **RQ3:** Does interactive conflict resolution lead to better-aligned decisions?

---

## 6. Recommended Next Steps

| Phase | Timeline | Goal |
|-------|----------|------|
| Negotiation Protocol | Feb-Mar 2026 | Visible agent negotiation |
| Interactive Conflicts | Mar 2026 | User agency in conflicts |
| Evaluation | Apr 2026 | Prove approach works |
| Paper & Demo | May-Jun 2026 | ACL 2026 submission |

---

**Report Generated:** February 14, 2026
**Target Deadline:** ACL 2026 (~June 2026)
