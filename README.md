# CMU-Q Academic Advising Chatbot

Multi-agent academic advising chatbot for CMU-Qatar undergraduates.

## Quick Start

### 1. Setup Environment

```bash
conda create -n advisingbot python=3.11 -y
conda activate advisingbot
pip install -r requirements.txt
```

### 2. Set API Key

Create `.env` file:
```
OPENAI_API_KEY=your_api_key_here
```

### 3. Run

**Option A: Interactive Advisor (Recommended)**
```bash
python interactive_advisor.py
```

**Option B: Full Agent System**
```bash
python chat_with_agent.py
```

## Files

### Core System
- `agent.py` - Main LangGraph agent system
- `rag_engine.py` - RAG engine (used by agent.py)
- `rag_engine_improved.py` - Improved RAG (used by interactive_advisor.py)
- `course_tools.py` - Course lookup tools

### Interfaces
- `interactive_advisor.py` - Standalone advisor chat
- `chat_with_agent.py` - Full agent system interface

### Data
- `data/` - Comprehensive academic data
- `info/` - Current data (used by rag_engine.py)
- `chroma_db/` - Vector database (auto-generated)

### Research
- `IMPLEMENTATION_PLAN.md` - Implementation roadmap
- `Modal Proposal.md` - Research proposal
- `General Feedback.md` - Research feedback

## Usage

### Interactive Advisor
Provides advisor-like answers with RAG + LLM synthesis:
```bash
python interactive_advisor.py
```

### Full Agent System
Uses LangGraph workflow with retrieve → advisor nodes:
```bash
python chat_with_agent.py
```

## Requirements

See `requirements.txt` for dependencies.

