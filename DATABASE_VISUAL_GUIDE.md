# Database Organization: Visual Guide

## How Domain-Specific Knowledge Bases Work

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA FILES (Source)                       │
│                    (Organized by Topic)                      │
└─────────────────────────────────────────────────────────────┘

data/
├── Academic & Studies/
│   ├── Academic Programs/          ──┐
│   │   ├── IS/                      │
│   │   ├── CS/                      │
│   │   └── Minors/                  │──→ Programs Domain
│   ├── Academic Resource Center/   ──┘
│   │
│   ├── Courses/                     ──┐
│   │   └── [4736 JSON files]         │──→ Courses Domain
│   │                                  │
│   ├── Registration/                ──┼──→ Policies Domain
│   └── Exams and grading policies/  ──┘

┌─────────────────────────────────────────────────────────────┐
│              VECTOR DATABASES (Indexes)                       │
│         (One per Domain, Built from Data Files)              │
└─────────────────────────────────────────────────────────────┘

chroma_db/
├── chroma_db_programs/              ← Programs Agent searches here
│   ├── chroma.sqlite3
│   └── [embeddings from Academic Programs + ARC]
│
├── chroma_db_courses/               ← Courses Agent searches here
│   ├── chroma.sqlite3
│   └── [embeddings from Courses folder]
│
└── chroma_db_policies/             ← Policy Agent searches here
    ├── chroma.sqlite3
    └── [embeddings from Registration + Exams policies]

┌─────────────────────────────────────────────────────────────┐
│                      AGENTS                                   │
│         (Each Uses Its Own Domain Database)                  │
└─────────────────────────────────────────────────────────────┘

Programs Agent          Courses Agent          Policy Agent
     │                       │                      │
     │                       │                      │
     ▼                       ▼                      ▼
chroma_db_programs    chroma_db_courses     chroma_db_policies
     │                       │                      │
     │                       │                      │
     └───────────────────────┴──────────────────────┘
                            │
                    ┌───────┴────────┐
                    │   Blackboard   │
                    │  (Shared State)│
                    └────────────────┘
```

---

## Data Flow

### Building Indexes (One-Time Setup)

```
Step 1: Load Domain Documents
┌─────────────────────────────┐
│ data/Academic Programs/      │
│ data/Academic Resource Ctr/  │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────┐
│   Split into Chunks         │
│   Create Embeddings         │
└──────────────┬───────────────┘
               │
               ▼
┌─────────────────────────────┐
│   chroma_db_programs/       │
│   (Vector Database)         │
└─────────────────────────────┘
```

### Agent Query Flow

```
User Query: "What are IS major requirements?"
     │
     ▼
┌─────────────────────────────┐
│  Programs Agent             │
│  domain="programs"          │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  get_retriever(domain=     │
│              "programs")    │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Loads: chroma_db_programs/ │
│  Searches ONLY in:          │
│  - Academic Programs docs   │
│  - Academic Resource docs   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Returns: Relevant chunks   │
│  from Programs domain only  │
└─────────────────────────────┘
```

---

## Domain Mapping Table

| Domain | Data Folders | Vector DB | Agent | Documents |
|--------|-------------|-----------|-------|-----------|
| **programs** | `Academic Programs/`<br>`Academic Resource Center/` | `chroma_db_programs/` | Programs & Requirements | ~50-100 files |
| **courses** | `Courses/` | `chroma_db_courses/` | Course & Scheduling | 4736 JSON files |
| **policies** | `Registration/`<br>`Exams and grading policies/` | `chroma_db_policies/` | Policy & Compliance | ~20-30 files |
| **opportunities** | `Research/`<br>`Career Development/`<br>`Student Travel/` | `chroma_db_opportunities/` | Opportunities (future) | ~15-20 files |

---

## Key Benefits Visualized

### ❌ Without Domain Separation

```
Single Database (chroma_db/)
├── All Academic Programs docs
├── All 4736 course files
├── All policy docs
└── All other docs

Query: "IS major requirements"
↓
Searches ALL documents (4800+ files)
↓
Might return:
- IS requirements ✅
- Random course info ❌
- Unrelated policies ❌
- Noise and irrelevant results
```

### ✅ With Domain Separation

```
Programs Database (chroma_db_programs/)
└── Only Academic Programs docs (~50 files)

Query: "IS major requirements"
↓
Searches ONLY Programs domain (~50 files)
↓
Returns:
- IS requirements ✅
- Related major/minor info ✅
- Focused, relevant results
```

---

## Setup Process

### Step 1: Organize Data Files (Already Done ✅)

Your `data/` folder is already organized by topic.

### Step 2: Build Domain Indexes

```bash
python setup_domain_indexes.py
```

This creates:
- `chroma_db_programs/` from Programs folders
- `chroma_db_courses/` from Courses folder
- `chroma_db_policies/` from Policies folders

### Step 3: Agents Use Domain-Specific Retrievers

```python
# Each agent automatically uses its domain
programs_agent = ProgramsRequirementsAgent()
# → Uses chroma_db_programs/

courses_agent = CourseSchedulingAgent()
# → Uses chroma_db_courses/

policy_agent = PolicyComplianceAgent()
# → Uses chroma_db_policies/
```

---

## Verification

### Test Domain Separation

```python
# Test Programs domain
programs_retriever = get_retriever(domain="programs", k=3)
results = programs_retriever.invoke("IS major requirements")
# Should return: IS program docs, major requirements
# Should NOT return: Course schedules, policies

# Test Courses domain
courses_retriever = get_retriever(domain="courses", k=3)
results = courses_retriever.invoke("15-112")
# Should return: Course 15-112 info
# Should NOT return: Program requirements, policies

# Test Policies domain
policy_retriever = get_retriever(domain="policies", k=3)
results = policy_retriever.invoke("course overload")
# Should return: Overload policy docs
# Should NOT return: Course info, program requirements
```

---

## Maintenance

### When to Rebuild

**Rebuild a domain index when:**
- New documents added to that domain's folders
- Documents updated/corrected
- Need to refresh embeddings

**Don't rebuild when:**
- Only using the system (reading is fine)
- Other domains changed (only rebuild changed domain)

### Rebuild Command

```python
from rag_engine_improved import build_domain_index

# Rebuild specific domain
build_domain_index("programs", force_rebuild=True)

# Rebuild all
build_all_domain_indexes(force_rebuild=True)
```

---

## Summary

**Organization Strategy:**
1. **Data Files**: Organized by topic in `data/` folder ✅ (already done)
2. **Vector Databases**: One per domain in `chroma_db_{domain}/`
3. **Agent Access**: Each agent uses `get_retriever(domain="...")`

**Result:**
- ✅ Focused knowledge bases
- ✅ Better retrieval accuracy
- ✅ Faster searches
- ✅ Clear separation
- ✅ Easy maintenance

This ensures each agent has its own focused, efficient knowledge base!

