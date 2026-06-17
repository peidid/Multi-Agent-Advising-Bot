# Quick Start Guide

## Setup (One-Time)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set OpenAI API Key
```bash
# Windows PowerShell
$env:OPENAI_API_KEY="your-api-key-here"

# Linux/Mac
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Build RAG Indexes
```bash
python setup_domain_indexes.py
```

This creates vector databases for:
- Programs requirements
- Course information
- University policies

**Takes ~2-3 minutes**

---

## Run the System

```bash
python chat.py
```

You'll see:
```
================================================================================
🎓 CMU-Q Academic Advising Chatbot - Workflow Demonstration
================================================================================

🧠 Coordination Mode:
  • LLM-Driven Coordination
    (Full LLM reasoning for dynamic workflow planning)

💬 Model Configuration:
   Coordinator: gpt-4-turbo (temp: 0.3)
   Agents: gpt-4o (temp: 0.3)

Type 'quit' to exit
--------------------------------------------------------------------------------

You: 
```

---

## Example Queries

### 1. Simple Course Query
```
You: What are the prerequisites for 15-213?
```

**What You'll See:**
- LLM understands: Simple course information query
- Activates: Course Scheduling Agent only
- Response: Prerequisites with explanations

### 2. Complex Multi-Agent Query
```
You: I probably will get a D in 15-112 this semester. 
     As a CS student, do I need to retake it next semester?
```

**What You'll See:**
- LLM understands: Multi-faceted question about grades, policies, and requirements
- Analyzes: Which agents are needed and why
- Plans: Logical execution order (policy → programs → courses)
- Activates: All three agents with reasoning
- Response: Comprehensive answer addressing all aspects

### 3. Program Requirements
```
You: What courses do I need for a CS major?
```

**What You'll See:**
- LLM understands: Program requirements query
- Activates: Programs Requirements Agent
- Response: Complete major requirements

### 4. Policy Question
```
You: What happens if I fail a course?
```

**What You'll See:**
- LLM understands: Policy question
- Activates: Policy Compliance Agent
- Response: University policies on failing grades

---

## Understanding the Output

### Step 1: Intent Classification
```
🎯 STEP 1: Intent Classification

   Query: "I probably will get a D in 15-112..."

   🧠 LLM-Driven Coordination (Full Reasoning)
   🎯 Confidence: ████████ (0.90)

   🔍 Problem Understanding:
      • Goal: Determine if they need to retake 15-112
      • Concern: Impact of D grade on CS major requirements

   🎯 Coordination Goal:
      Help student understand retake requirements and implications

   💭 Reasoning:
      This is a complex question involving:
      1. University policy on D grades
      2. CS major requirements
      3. Course dependencies
      
      Need all three agents because...

   🤖 Agent Analysis:
      • policy_compliance: high priority
        → Must check if D is passing grade
      • programs_requirements: high priority
        → Core question about major requirements
      • course_scheduling: medium priority
        → Helpful for dependencies

   🤖 Agents to Activate:
      1. Policy Compliance
      2. Programs Requirements
      3. Course Scheduling

   📋 Workflow Order:
      1. Policy Compliance
      2. Programs Requirements
      3. Course Scheduling
```

**Key Points:**
- Shows LLM's understanding of the problem
- Explains why each agent is needed
- Plans logical execution order
- Provides confidence score

### Step 2: Agent Execution
```
🤖 STEP 2: Agent Execution

🤖 Executing Policy Compliance Agent
⏳ Policy Compliance is processing your query...
✅ Policy Compliance completed

🤖 Executing Programs Requirements Agent
⏳ Programs Requirements is processing your query...
✅ Programs Requirements completed

🤖 Executing Course Scheduling Agent
⏳ Course Scheduling is processing your query...
✅ Course Scheduling completed
```

### Step 3: Final Response
```
💬 FINAL ANSWER

[Comprehensive response combining all agent outputs]
```

---

## Development Mode

For testing individual agents:

### Enable Dev Mode
```
You: mode:dev
System: 🔧 Development mode enabled!
```

### Test Individual Agents
```
You: @courses What are prerequisites for 15-213?
[Uses only Course Scheduling Agent]

You: @programs What are CS major requirements?
[Uses only Programs Requirements Agent]

You: @policy What is the grade appeal process?
[Uses only Policy Compliance Agent]

You: @all I want to add a CS minor
[Uses all agents, bypasses LLM coordination]
```

### Return to Normal Mode
```
You: mode:normal
System: ✅ Returned to normal mode
```

---

## Configuration

Edit `config.py` to change LLM models:

```python
COORDINATOR_MODEL = "gpt-4-turbo"      # For coordination
COORDINATOR_TEMPERATURE = 0.3

AGENT_MODEL = "gpt-4o"                 # For agents
AGENT_TEMPERATURE = 0.3
```

**Why different models?**
- Coordinator needs stronger reasoning (complex workflow planning)
- Agents need speed + accuracy (domain queries)
- Cost optimization

---

## Troubleshooting

### "No module named 'langchain'"
```bash
pip install -r requirements.txt
```

### "OpenAI API key not found"
```bash
# Set environment variable
$env:OPENAI_API_KEY="your-key"
```

### "No index found for domain 'programs'"
```bash
# Build indexes
python setup_domain_indexes.py
```

### Slow responses
- First query is slower (loading indexes)
- Subsequent queries are faster
- Complex queries take longer (multiple agents)

### Network errors
- Check internet connection
- Verify OpenAI API key is valid
- Check if API has credits

---

## What Makes This Special?

### Traditional Rule-Based Routing
```
Query → Extract keywords → Match intent → Route to agent
```
**Problems:**
- Brittle keyword matching
- Fixed intent types
- No context awareness

### Our LLM-Driven Coordination
```
Query → LLM understands problem → LLM analyzes capabilities 
     → LLM plans workflow → Dynamic execution
```
**Advantages:**
- Understands underlying intent
- Dynamic agent selection
- Context-aware planning
- Explainable reasoning

---

## Next Steps

1. **Try different queries** - See how LLM adapts
2. **Use dev mode** - Test individual agents
3. **Read ARCHITECTURE.md** - Understand system design
4. **Read TESTING_LLM_DRIVEN_COORDINATOR.md** - Testing guide

---

## Key Files

- `chat.py` - Interactive interface
- `multi_agent.py` - Workflow orchestration
- `coordinator/coordinator.py` - Main coordinator
- `coordinator/llm_driven_coordinator.py` - LLM-driven logic
- `agents/` - Specialized agents
- `config.py` - Configuration

---

**You're ready to go!** Run `python chat.py` and start asking questions! 🚀
