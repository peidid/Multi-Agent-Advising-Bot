# Quick Start: Interactive Clarification Feature

## 🚀 What's New?

The coordinator can now **intelligently detect ambiguous queries** and **ask clarification questions** before routing to agents!

---

## ✨ Try It Now

### Example 1: Ambiguous Query

```bash
python chat.py
```

```
You: Do I need to take 15-122?

❓ CLARIFICATION NEEDED

   🤔 Why I need to ask:
      Requirements for 15-122 vary significantly between programs.
      CS requires it, but IS, BA, and Bio do not.

   1. What is your major or program?
      → Requirements differ significantly between programs
      Options: Computer Science, Information Systems, Biological Sciences, Business Administration

      Your answer: Computer Science

   ✅ Thank you! Now I can provide an accurate answer.

[System proceeds with high confidence]
```

### Example 2: Clear Query (No Clarification)

```
You: As a CS student, do I need to take 15-122?

[System proceeds immediately - no clarification needed]
```

---

## 🧪 Test It

Run the test script:

```bash
python test_clarification.py
```

This will test:
- ✅ Ambiguous queries (should ask)
- ✅ Clear queries (should NOT ask)
- ✅ Queries with profile context (should NOT ask)

---

## 📋 Commands

| Command | Description |
|---------|-------------|
| `python chat.py` | Start interactive chat |
| `clear` | Clear conversation history and profile |
| `quit` | Exit |
| `python test_clarification.py` | Run automated tests |

---

## 🎯 Key Features

1. **Smart Detection**
   - Only asks when information is **critical** and **missing**
   - Doesn't over-ask on clear queries

2. **Context Awareness**
   - Remembers information from previous turns
   - Updates student profile automatically

3. **Conversational**
   - Explains **why** it's asking
   - Provides **options** when applicable
   - Re-analyzes with full context

---

## 📊 What to Test

### Ambiguous Queries (Should Ask)
- "Do I need 15-122?"
- "Can I graduate on time?"
- "Is this course required?"
- "What courses should I take?"

### Clear Queries (Should NOT Ask)
- "As a CS student, do I need 15-122?"
- "What are the prerequisites for 15-213?"
- "What is the drop policy?"
- "CS major requires what courses?"

### Context Queries (Should NOT Ask After First Time)
```
You: I'm a CS major
You: Do I need 15-122?
[Should NOT ask for major - already knows from previous turn]
```

---

## 🔧 Configuration

To adjust clarification sensitivity, edit:

`coordinator/clarification_handler.py`

```python
# Line ~95: Adjust the prompt's "IMPORTANT" section

# More conservative (asks less):
"Only set needs_clarification=true if information is CRITICAL"

# More aggressive (asks more):
"Set needs_clarification=true if any information could improve answer"
```

---

## 📁 Key Files

- `coordinator/clarification_handler.py` - Core logic
- `coordinator/coordinator.py` - Integration
- `chat.py` - User interface
- `test_clarification.py` - Automated tests

---

## 📖 Documentation

- `CLARIFICATION_FEATURE_SUMMARY.md` - Feature overview with examples
- `CLARIFICATION_DESIGN.md` - Detailed design and evaluation plan
- `ACL2026_GAP_ANALYSIS.md` - Research roadmap

---

## ✅ Status

**Implemented:**
- ✅ Ambiguity detection
- ✅ Interactive clarification UI
- ✅ Profile persistence
- ✅ Conversation context
- ✅ Re-analysis after clarification

**Next Steps:**
- [ ] Test on real queries
- [ ] Collect evaluation data
- [ ] Tune confidence thresholds

---

## 🎓 Research Contribution

**For ACL 2026 Demo Track:**

This feature demonstrates **intelligent, context-aware clarification** in multi-agent coordination:
- Detects ambiguity automatically
- Asks targeted questions only when necessary
- Maintains conversation context
- Improves accuracy on ambiguous queries without degrading efficiency on clear ones

**Expected Results:**
- Ambiguous queries: 95%+ accuracy (vs. 60% without clarification)
- Clear queries: 90%+ accuracy (no degradation)
- Clarification precision: >90% (asks when needed, not when not)

---

**Start testing:** `python chat.py` 🚀

**Questions?** See `CLARIFICATION_DESIGN.md` for detailed documentation.
