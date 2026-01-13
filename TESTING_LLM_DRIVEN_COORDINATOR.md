# Testing LLM-Driven Coordinator

## ✅ Integration Complete!

The LLM-driven coordinator is now integrated and ready to test!

---

## What's Different?

### Before (Rule-Based)
```
Query → Extract keywords → Match intent → Apply rules → Return agents
```

### Now (LLM-Driven)
```
Query → LLM understands problem → LLM analyzes agent capabilities 
     → LLM plans workflow → LLM sets decision points → Dynamic execution
```

---

## How to Test

### Run Chat Interface
```bash
python chat.py
```

The system will automatically use **LLM-driven mode** (default).

### What You'll See

When you ask a question, you'll see:

```
🎯 STEP 1: Intent Classification

   Query: "I probably will get a D in 15-112 this semester. 
           as a CS student, do I need to retake it next semester?"

   Analyzing query to determine which agents are needed...

   🧠 LLM-Driven Coordination (Full Reasoning)
   📊 Priority: high
   🎯 Confidence: ████████ (0.90)

   🔍 Problem Understanding:
      • Goal: Determine if they need to retake 15-112
      • Concern: Impact of D grade on CS major requirements

   🎯 Coordination Goal:
      Help student understand if they need to retake 15-112 
      and the implications of their decision

   💭 Reasoning:
      This is a complex question involving:
      1. Major requirements (programs agent)
      2. University policies (policy agent)
      3. Course dependencies (course agent)
      
      We need all three agents because...

   🤖 Agent Analysis:
      • policy_compliance: high priority
        → Critical for understanding if D is acceptable
      • programs_requirements: high priority
        → Core question is about major requirements
      • course_scheduling: medium priority
        → Helpful for understanding course dependencies

   🤖 Agents to Activate:
      1. Policy Compliance
      2. Programs Requirements
      3. Course Scheduling

   📋 Workflow Order:
      1. Policy Compliance
      2. Programs Requirements
      3. Course Scheduling

   ⚙️  Decision Points:
      • After policy_compliance: Is D a passing grade university-wide?...
      • After programs_requirements: Does CS major accept D for 15-112?...
```

---

## Test Queries

### 1. Complex Query (Tests Multi-Agent Reasoning)
```
I probably will get a D in 15-112 this semester. as a CS student, do I need to retake it next semester?
```

**Expected LLM Reasoning:**
- Understands: Student worried about D grade impact
- Analyzes: Needs policy (is D passing?), programs (does major accept it?), course (dependencies?)
- Plans: policy → programs → course (logical order)
- Decision points: Check policy first, then major requirements

### 2. Simple Query (Tests Efficiency)
```
What are the prerequisites for 15-213?
```

**Expected LLM Reasoning:**
- Understands: Simple course information query
- Analyzes: Only course_scheduling agent needed
- Plans: Single agent, no decision points
- Efficient: Doesn't over-activate agents

### 3. Ambiguous Query (Tests Clarification)
```
Tell me about this course
```

**Expected LLM Reasoning:**
- Understands: Ambiguous reference
- Identifies: Missing information (which course?)
- Asks: Clarification question
- Plans: Tentative workflow pending clarification

---

## Switching Modes

You can test different coordination modes:

### Mode 1: LLM-Driven (Default)
```python
# In multi_agent.py
coordinator = Coordinator(mode="llm_driven")
```

**Features:**
- Full LLM reasoning
- No predefined intents
- Dynamic workflow planning
- Adaptive coordination

### Mode 2: Enhanced Rule-Based
```python
# In multi_agent.py
coordinator = Coordinator(mode="enhanced")
```

**Features:**
- Entity extraction
- Confidence scoring
- Predefined routing rules
- Fixed workflows

### Mode 3: Basic Rule-Based
```python
# In multi_agent.py
coordinator = Coordinator(mode="basic")
```

**Features:**
- Simple keyword matching
- Fixed intent types
- Hard-coded rules

---

## Comparing Modes

Try the same query in different modes:

### Test Script
```python
from coordinator.coordinator import Coordinator

query = "I probably will get a D in 15-112. Do I need to retake it?"

# Test LLM-driven
coord_llm = Coordinator(mode="llm_driven")
intent_llm = coord_llm.classify_intent(query)
print("LLM-Driven:", intent_llm['required_agents'])

# Test enhanced
coord_enh = Coordinator(mode="enhanced")
intent_enh = coord_enh.classify_intent(query)
print("Enhanced:", intent_enh['required_agents'])

# Test basic
coord_basic = Coordinator(mode="basic")
intent_basic = coord_basic.classify_intent(query)
print("Basic:", intent_basic['required_agents'])
```

**Expected Results:**
- **LLM-Driven**: `['policy_compliance', 'programs_requirements', 'course_scheduling']`
  - Reasoning: Understands complexity, needs all three
- **Enhanced**: `['programs_requirements']`
  - Reasoning: Extracts "15-112" and "CS", matches to programs
- **Basic**: `['programs_requirements']`
  - Reasoning: Matches "retake" keyword

---

## What to Look For

### 1. Better Understanding
LLM-driven should show deeper understanding:
- Not just keywords, but underlying concerns
- Not just matching, but reasoning

### 2. Better Agent Selection
LLM-driven should select agents more intelligently:
- Considers agent capabilities and limitations
- Explains why each agent is needed
- Doesn't over-activate or under-activate

### 3. Better Workflow Planning
LLM-driven should plan better workflows:
- Logical execution order
- Decision points for adaptation
- Parallel execution where possible

### 4. Better Explainability
LLM-driven should explain better:
- Why these agents?
- Why this order?
- What might go wrong?
- How do we know we succeeded?

---

## Network Issue Note

⚠️ **You may still get network errors during agent execution** (RAG retrieval).

This is separate from coordination. The coordination works (LLM classifies intent), but agent execution fails (can't get embeddings).

**To test coordination only:**
```bash
python test_classifier_only.py
```

This tests just the coordination logic without executing agents.

---

## Next Steps

1. **Test both modes** - Compare LLM-driven vs rule-based
2. **Measure differences** - Which makes better decisions?
3. **Document examples** - Collect cases where LLM-driven is better
4. **Use for paper** - This is your research contribution!

---

## For ACL 2026

This LLM-driven coordination is your **main research contribution**:

**Title:** "LLM as Coordinator: Dynamic Multi-Agent Workflow Planning for Academic Advising"

**Contribution:**
1. Show LLM can be intelligent coordinator (not just classifier)
2. LLM-driven coordination > rule-based routing
3. Dynamic workflow planning improves efficiency and quality

**Evaluation:**
- Compare LLM-driven vs rule-based on 50 test queries
- Measure: agent selection accuracy, workflow quality, efficiency
- User study: which mode gives better advice?

---

## Files Modified

- `coordinator/coordinator.py` - Added LLM-driven mode
- `multi_agent.py` - Default to LLM-driven mode
- `chat.py` - Display LLM reasoning in UI

## Files Created

- `coordinator/llm_driven_coordinator.py` - LLM-driven implementation
- `RULE_BASED_VS_LLM_DRIVEN.md` - Comparison and philosophy
- `TESTING_LLM_DRIVEN_COORDINATOR.md` - This file

---

**You're ready to test!** Run `python chat.py` and see the LLM reasoning in action! 🚀
