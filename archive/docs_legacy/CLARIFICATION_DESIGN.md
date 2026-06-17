# Interactive Clarification Design Document

## Overview

This document describes the design and implementation of the **interactive clarification feature** for the multi-agent academic advising system.

**Key Innovation:** The coordinator can detect ambiguous queries and proactively ask clarification questions before routing to agents, improving accuracy while maintaining efficiency.

---

## Research Motivation

### Problem

Traditional academic advising systems often:
1. **Guess** when information is missing (low accuracy)
2. **Ask too many questions** upfront (poor UX)
3. **Fail silently** on ambiguous queries (user frustration)

### Our Solution

**Intelligent, context-aware clarification:**
- Detect when information is **critical** and **missing**
- Ask **targeted questions** only when necessary
- Maintain **conversation context** to avoid redundant questions
- **Re-analyze** with full context after clarification

### Research Contribution (ACL 2026)

**RQ3:** Does intelligent clarification in LLM-driven coordination improve accuracy on ambiguous queries while maintaining efficiency on clear queries?

**Hypothesis:**
- Ambiguous queries: 95%+ accuracy with clarification vs. 60% without
- Clear queries: Similar accuracy (90%+) with no unnecessary questions
- Clarification precision: >90% (asks when needed, doesn't over-ask)

---

## Architecture

### High-Level Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Query                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Coordinator Receives Query                    │
│                                                                  │
│  • Extract known information from profile                       │
│  • Review conversation history                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              ClarificationHandler.check_for_clarification()      │
│                                                                  │
│  LLM analyzes:                                                  │
│  1. What information is needed to answer accurately?            │
│  2. What information is currently missing?                      │
│  3. Can we answer without it?                                   │
│  4. If not, what questions should we ask?                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
              [Ambiguous]          [Clear]
                    │                   │
                    ↓                   ↓
    ┌───────────────────────┐   ┌──────────────────┐
    │ Request Clarification │   │ Proceed Normally │
    │                       │   │                  │
    │ • Show reasoning      │   │ • Plan workflow  │
    │ • Ask questions       │   │ • Execute agents │
    │ • Get user input      │   │ • Synthesize     │
    └───────────────────────┘   └──────────────────┘
                    │
                    ↓
    ┌───────────────────────┐
    │ Update Profile        │
    │ Add to Conversation   │
    └───────────────────────┘
                    │
                    ↓
    ┌───────────────────────┐
    │ Re-analyze Query      │
    │ (with full context)   │
    └───────────────────────┘
                    │
                    ↓
    ┌───────────────────────┐
    │ Proceed Normally      │
    │                       │
    │ • Plan workflow       │
    │ • Execute agents      │
    │ • Synthesize answer   │
    └───────────────────────┘
```

---

## Component Design

### 1. ClarificationHandler

**Location:** `coordinator/clarification_handler.py`

**Responsibility:** Detect ambiguity and generate clarification questions

**Key Method:**

```python
def check_for_clarification(
    self,
    query: str,
    conversation_history: List[Dict[str, str]],
    student_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Returns:
    {
        "needs_clarification": bool,
        "confidence": float (0.0-1.0),
        "missing_info": List[str],
        "reasoning": str,
        "questions": [
            {
                "question": str,
                "why": str,
                "type": str,
                "options": List[str]
            }
        ]
    }
    """
```

**LLM Prompt Strategy:**

1. **Context Building:**
   - Current query
   - Known information (from profile)
   - Recent conversation history

2. **Pattern Recognition:**
   - Ambiguous patterns (e.g., "Do I need X?" without major)
   - Clear patterns (e.g., "As a CS student, do I need X?")

3. **Critical Information:**
   - Major/program (for requirements)
   - Semester (for timeline)
   - Courses taken (for progress)

4. **Conservative Approach:**
   - Only ask if information is **critical** and **missing**
   - Don't ask for general queries (e.g., "What are prerequisites?")
   - Don't ask if context is clear from query

### 2. Coordinator Integration

**Location:** `coordinator/coordinator.py`

**Changes:**

```python
def classify_intent(self, query, conversation_history, student_profile):
    # Step 0: Check for clarification
    clarification_check = self.clarification_handler.check_for_clarification(
        query, conversation_history, student_profile
    )
    
    if clarification_check.get('needs_clarification'):
        # Return special intent
        return {
            "intent_type": "needs_clarification",
            "required_agents": [],  # No agents yet
            "understanding": {
                "requires_clarification": True,
                "clarification_questions": [...],
                "clarification_reasoning": "...",
                "missing_information": [...]
            }
        }
    
    # Normal workflow planning
    plan = self.llm_coordinator.understand_and_plan(...)
    return plan
```

### 3. Chat Interface

**Location:** `chat.py`

**New Functions:**

```python
def show_clarification_needed(intent):
    """Display why clarification is needed"""
    # Show reasoning
    # Show missing information
    # Introduce questions

def get_user_clarification(intent):
    """Interactively collect answers"""
    # For each question:
    #   - Show question
    #   - Show why we're asking
    #   - Show options (if applicable)
    #   - Get user input
    # Return dict of responses
```

**Workflow Changes:**

```python
# After intent classification
if clarification:
    # Update profile
    student_profile.update(clarification)
    
    # Add to conversation
    conversation_messages.append(AIMessage(content=f"Noted: {clarification}"))
    
    # Re-classify with updated context
    intent, workflow, _ = show_intent_classification(
        query, conversation_history, student_profile
    )
```

**Persistent State:**

```python
# In chat() function
student_profile = {}  # Persists across queries in session

# On 'clear' command
student_profile = {}  # Reset
```

---

## Decision Logic

### When to Ask for Clarification

**Ask if:**
1. ✅ Information is **critical** for accurate answer
2. ✅ Information is **missing** from profile and query
3. ✅ Cannot reasonably answer without it
4. ✅ Confidence < threshold (typically 0.5)

**Don't ask if:**
1. ❌ Query is general/informational (e.g., "What are prerequisites?")
2. ❌ Information is specified in query (e.g., "As a CS student...")
3. ❌ Information can be inferred from context
4. ❌ Confidence > threshold (typically 0.7)

### Critical Information Types

| Information | When Critical | Example Query |
|-------------|--------------|---------------|
| **Major/Program** | Requirement questions | "Do I need 15-122?" |
| **Semester** | Timeline questions | "Can I graduate on time?" |
| **Courses Taken** | Progress questions | "Am I on track?" |
| **Academic Standing** | Special cases | "Can I overload?" |

### Confidence Thresholds

```
Confidence < 0.4: MUST ask (very ambiguous)
Confidence 0.4-0.6: Should ask (somewhat ambiguous)
Confidence 0.6-0.8: Probably don't ask (somewhat clear)
Confidence > 0.8: Don't ask (very clear)
```

---

## Example Scenarios

### Scenario 1: Ambiguous Query

**Input:**
```
Query: "Do I need to take 15-122 for my degree?"
Profile: {}
History: []
```

**Analysis:**
- Missing: major/program
- Critical: Yes (requirements vary by program)
- Can answer without: No
- Confidence: 0.35

**Output:**
```json
{
  "needs_clarification": true,
  "confidence": 0.35,
  "missing_info": ["major"],
  "reasoning": "Requirements for 15-122 vary significantly between programs. CS requires it, but IS, BA, and Bio do not.",
  "questions": [
    {
      "question": "What is your major or program?",
      "why": "Requirements differ significantly between programs",
      "type": "major",
      "options": ["Computer Science", "Information Systems", "Biological Sciences", "Business Administration"]
    }
  ]
}
```

**User Interaction:**
```
❓ CLARIFICATION NEEDED

   🤔 Why I need to ask:
      Requirements for 15-122 vary significantly between programs.
      CS requires it, but IS, BA, and Bio do not.

   📋 Missing information: major

   💡 To give you an accurate answer, I need to know:

--------------------------------------------------------------------------------

   1. What is your major or program?
      → Requirements differ significantly between programs
      Options: Computer Science, Information Systems, Biological Sciences, Business Administration

      Your answer: Computer Science

   ✅ Thank you! Now I can provide an accurate answer.
```

**After Clarification:**
```
Profile: {"major": "Computer Science"}
Re-analyze → Confidence: 0.95 → Proceed to agents
```

### Scenario 2: Clear Query

**Input:**
```
Query: "As a CS student, do I need to take 15-122?"
Profile: {}
History: []
```

**Analysis:**
- Missing: None (major specified in query)
- Critical: N/A
- Can answer without: Yes
- Confidence: 0.92

**Output:**
```json
{
  "needs_clarification": false,
  "confidence": 0.92,
  "missing_info": [],
  "reasoning": "Query clearly specifies CS major, sufficient context to answer"
}
```

**User Interaction:**
```
[No clarification - proceeds directly to agents]
```

### Scenario 3: Context from History

**Input:**
```
Query: "Do I need 15-122?"
Profile: {"major": "Computer Science"}
History: [
  {"role": "user", "content": "I'm a CS major"},
  {"role": "assistant", "content": "Great! How can I help you?"}
]
```

**Analysis:**
- Missing: None (major in profile from previous turn)
- Critical: N/A
- Can answer without: Yes
- Confidence: 0.90

**Output:**
```json
{
  "needs_clarification": false,
  "confidence": 0.90,
  "missing_info": [],
  "reasoning": "Major is known from previous conversation"
}
```

**User Interaction:**
```
[No clarification - proceeds directly to agents]
```

---

## Evaluation Plan

### Test Dataset

**20 Ambiguous Queries:**
1. "Do I need to take 15-122?"
2. "Is 15-213 required?"
3. "Can I graduate on time?"
4. "Am I on track for graduation?"
5. "What courses should I take next semester?"
6. "Can I overload?"
7. "Is this course required?"
8. "Do I have to retake this?"
9. "Can I substitute this course?"
10. "What's my graduation timeline?"
11. "How many units do I need?"
12. "Is independent study allowed?"
13. "Can I take this course?"
14. "What are my requirements?"
15. "Do I need an elective?"
16. "Can I drop this course?"
17. "What's the minimum GPA?"
18. "Am I eligible for this?"
19. "What do I need to graduate?"
20. "Is this course worth it?"

**20 Clear Queries:**
1. "As a CS student, do I need 15-122?"
2. "What are the prerequisites for 15-213?"
3. "What is the drop/add policy?"
4. "When is the registration deadline?"
5. "How many units is 15-122?"
6. "Who teaches 15-213?"
7. "What is the grading policy?"
8. "CS major requires what courses?"
9. "What is academic probation?"
10. "How do I declare a major?"
11. "What is the overload policy?"
12. "15-213 is offered when?"
13. "What is the prerequisite for 15-213?"
14. "Explain the drop policy"
15. "What is independent study?"
16. "How many units for CS degree?"
17. "What is the GPA requirement?"
18. "Explain academic integrity"
19. "What are core courses?"
20. "Define technical elective"

### Metrics

**1. Clarification Precision**
```
Precision = True Positives / (True Positives + False Positives)

True Positive: Asked when needed
False Positive: Asked when NOT needed (over-clarification)
```

**Target: >90%**

**2. Clarification Recall**
```
Recall = True Positives / (True Positives + False Negatives)

True Positive: Asked when needed
False Negative: Didn't ask when needed (missed ambiguity)
```

**Target: >95%**

**3. Accuracy Improvement**
```
Accuracy_with = Correct answers / Total queries (with clarification)
Accuracy_without = Correct answers / Total queries (without clarification)

Improvement = Accuracy_with - Accuracy_without
```

**Target on ambiguous queries: +35% (60% → 95%)**

**4. Efficiency (No Degradation)**
```
Accuracy_clear_with = Accuracy on clear queries (with clarification enabled)
Accuracy_clear_without = Accuracy on clear queries (without clarification)

Degradation = Accuracy_clear_with - Accuracy_clear_without
```

**Target: <2% degradation (ideally 0%)**

### Evaluation Protocol

**Step 1: Baseline (No Clarification)**
- Run all 40 queries without clarification
- Record accuracy for each
- Note: System will guess or fail on ambiguous queries

**Step 2: With Clarification**
- Run all 40 queries with clarification enabled
- For ambiguous queries: Provide clarification when asked
- For clear queries: Should NOT ask
- Record accuracy for each

**Step 3: Analysis**
- Calculate precision, recall, accuracy improvement
- Identify false positives (over-clarification)
- Identify false negatives (missed ambiguity)
- Compare efficiency on clear queries

**Step 4: Error Analysis**
- Categorize errors
- Identify patterns
- Propose improvements

---

## Implementation Checklist

- [✅] Create `ClarificationHandler` class
- [✅] Implement `check_for_clarification()` method
- [✅] Integrate into `Coordinator.classify_intent()`
- [✅] Add `show_clarification_needed()` to chat UI
- [✅] Add `get_user_clarification()` to chat UI
- [✅] Implement profile persistence across queries
- [✅] Implement re-analysis after clarification
- [✅] Add profile reset on 'clear' command
- [✅] Create test script (`test_clarification.py`)
- [✅] Write documentation
- [ ] Test on ambiguous queries
- [ ] Test on clear queries
- [ ] Test with conversation context
- [ ] Collect evaluation data
- [ ] Analyze results
- [ ] Tune confidence thresholds
- [ ] Write ACL paper section

---

## Future Enhancements

### Phase 2 (Post-ACL)

**1. Proactive Profile Building**
```
System: Hi! To help you better, may I ask a few quick questions?
        1. What's your major?
        2. What semester are you in?

[Build profile upfront for better experience]
```

**2. Smart Inference**
```
User: "I'm taking 15-122, 15-151, and 21-127"

System: [Infers: Likely CS major, probably freshman/sophomore]
        [Updates profile automatically]
```

**3. Persistent Profiles**
```python
# Save profile to file/database
save_profile(student_id, profile)

# Load on startup
profile = load_profile(student_id)
```

**4. Multi-Turn Clarification**
```
System: What's your major?
User: CS

System: Great! What semester are you in?
User: 5

System: And how many courses have you completed?
User: 20

[Conversational clarification instead of all at once]
```

**5. Confidence Calibration**
```python
# Learn optimal thresholds from data
threshold = calibrate_threshold(evaluation_results)

# Different thresholds for different query types
thresholds = {
    "requirement": 0.6,
    "timeline": 0.5,
    "policy": 0.8
}
```

---

## Key Files

- `coordinator/clarification_handler.py` - Core logic
- `coordinator/coordinator.py` - Integration
- `chat.py` - User interface
- `test_clarification.py` - Testing
- `CLARIFICATION_FEATURE_SUMMARY.md` - Quick reference
- `CLARIFICATION_DESIGN.md` - This document

---

## References

**Related Work:**
- Conversational question answering with clarification
- Ambiguity detection in NLU
- Interactive information retrieval
- User agency in AI systems

**Our Contribution:**
- Context-aware clarification in multi-agent coordination
- Conservative approach (only ask when necessary)
- Integration with LLM-driven workflow planning
- Evaluation on academic advising domain

---

## Contact

For questions or suggestions, see `README_FIRST.md` for project overview.

---

**Status:** ✅ Implemented, ready for testing and evaluation
