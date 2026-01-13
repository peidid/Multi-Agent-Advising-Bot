# Conversation Memory Feature

## ✅ Short-Term Memory Enabled!

The system now maintains **conversation history** across multiple turns, allowing you to have natural, contextual conversations.

---

## How It Works

### Conversation History Tracking

The system maintains a list of all messages in the current conversation:
- **Your questions** (HumanMessage)
- **System responses** (AIMessage)

This history is passed to:
1. **LLM Coordinator** - For context-aware workflow planning
2. **Agents** - For understanding references to previous topics

---

## Example Conversations

### Example 1: Course References

```
You: What are the prerequisites for 15-213?

System: [Explains 15-213 prerequisites: 15-122 and 15-112]

You: What about its assessment structure?
     ↑ "its" refers to 15-213 from previous question

System: [Understands "its" = 15-213, provides assessment info]

You: Is it offered in Spring?
     ↑ "it" still refers to 15-213

System: [Provides 15-213 offering schedule]
```

### Example 2: Following Up on Advice

```
You: I probably will get a D in 15-112. Do I need to retake it?

System: [Explains D grade policy and CS major requirements]

You: What if I retake it next semester?
     ↑ "it" refers to 15-112, context understood

System: [Explains retake policy with context from previous answer]

You: Will that affect my GPA?
     ↑ "that" refers to retaking the course

System: [Explains GPA calculation for retakes]
```

### Example 3: Multi-Topic Discussion

```
You: What courses do I need for a CS major?

System: [Lists CS major requirements]

You: Can I add an IS minor too?
     ↑ System remembers you're asking about CS major

System: [Explains IS minor requirements in context of CS major]

You: Would that delay my graduation?
     ↑ "that" refers to adding IS minor while doing CS major

System: [Analyzes timeline with both majors in mind]
```

---

## Visual Indicators

When you ask a follow-up question, you'll see:

```
🎯 STEP 1: Intent Classification

   Query: "What about its assessment structure?"
   💭 Context: 1 previous turn(s) in conversation
   
   Analyzing query to determine which agents are needed...
```

This shows the system is using conversation history!

---

## Commands

### Clear Conversation History
```
You: clear
System: 🧹 Conversation history cleared.
```

Use this to:
- Start a completely new topic
- Reset context if the system seems confused
- Begin a fresh conversation

### Quit
```
You: quit
```
Exits the system (conversation history is lost)

---

## Technical Details

### Implementation

**In `chat.py`:**
```python
# Initialize conversation memory
conversation_messages = []

# For each user query:
conversation_messages.append(HumanMessage(content=query))

# Pass to coordinator
intent = coordinator.classify_intent(query, conversation_messages)

# After system response:
conversation_messages.append(AIMessage(content=answer))
```

### What Gets Remembered

✅ **Remembered:**
- All user queries in current session
- All system responses
- Topics discussed
- Entities mentioned (courses, programs, policies)

❌ **Not Remembered:**
- Previous sessions (no persistence)
- After typing 'clear'
- After restarting the program

---

## How LLM Uses History

### 1. Understanding References

**Without History:**
```
You: Tell me more about it
LLM: ❌ "What does 'it' refer to?"
```

**With History:**
```
Previous: "What are prerequisites for 15-213?"
You: Tell me more about it
LLM: ✅ "it" = 15-213, provides more info
```

### 2. Context-Aware Planning

**Without History:**
```
You: Would that delay graduation?
LLM: ❌ "What is 'that'?"
```

**With History:**
```
Previous: "Can I add an IS minor?"
You: Would that delay graduation?
LLM: ✅ Understands "that" = adding IS minor
     Plans workflow: programs_requirements + course_scheduling
```

### 3. Building on Previous Answers

**Without History:**
```
You: What if I retake it?
LLM: ❌ "Retake what?"
```

**With History:**
```
Previous: Discussion about failing 15-112
You: What if I retake it?
LLM: ✅ Knows context: failing 15-112, retake policy
     Provides relevant retake information
```

---

## Best Practices

### 1. Natural Follow-Ups
✅ **Good:**
```
You: What are prerequisites for 15-213?
You: Is it offered in Fall?
You: What about the workload?
```

❌ **Unnecessary (but still works):**
```
You: What are prerequisites for 15-213?
You: Is 15-213 offered in Fall?  ← No need to repeat course code
You: What about 15-213's workload?  ← System already knows
```

### 2. Clear When Switching Topics
```
You: What are prerequisites for 15-213?
System: [Answers about 15-213]

You: clear  ← Clear before switching to unrelated topic

You: What are the IS major requirements?
```

### 3. Use Pronouns Naturally
```
You: I'm thinking about adding a CS minor
You: What courses would I need for it?  ← "it" is clear
You: How long would that take?  ← "that" is clear
```

---

## Limitations

### Current Limitations

1. **No Persistence**
   - History is lost when you close the program
   - Each session starts fresh

2. **No Long-Term Memory**
   - Doesn't remember your name, major, or courses
   - Each conversation is independent

3. **Limited Context Window**
   - Very long conversations may exceed LLM context limits
   - Use 'clear' for very long sessions

### Future Enhancements

Potential improvements:
- **Session persistence** - Save/load conversation history
- **Student profile memory** - Remember your major, completed courses
- **Conversation summarization** - Compress long histories
- **Multi-session memory** - Learn from past conversations

---

## Testing Conversation Memory

### Test 1: Simple Reference
```bash
python chat.py
```
```
You: What are the prerequisites for 15-213?
[Wait for response]

You: What about its assessment structure?
[Should understand "its" = 15-213]
```

### Test 2: Multi-Turn Context
```
You: I'm a CS major
You: What courses do I need?
[Should understand "I" refers to CS major student]

You: Can I add an IS minor?
[Should remember CS major context]

You: Would that delay graduation?
[Should understand "that" = adding IS minor as CS major]
```

### Test 3: Clear Command
```
You: What are prerequisites for 15-213?
[Response about 15-213]

You: clear
[Conversation cleared]

You: What about its prerequisites?
[Should ask for clarification - no context]
```

---

## Comparison

### Before (No Memory)
```
You: What are prerequisites for 15-213?
System: [Lists prerequisites]

You: Is it offered in Fall?
System: ❌ "What course are you asking about?"
```

### After (With Memory)
```
You: What are prerequisites for 15-213?
System: [Lists prerequisites]

You: Is it offered in Fall?
System: ✅ [Provides 15-213 Fall offering info]
       💭 Context: 1 previous turn(s) in conversation
```

---

## Files Modified

- **chat.py**
  - Added `conversation_messages` list
  - Appends HumanMessage for each query
  - Appends AIMessage for each response
  - Passes full history to coordinator
  - Clears history on 'clear' command

- **coordinator/coordinator.py**
  - Already accepts `conversation_history` parameter
  - Passes to `llm_driven_coordinator.py`

- **coordinator/llm_driven_coordinator.py**
  - Already uses conversation history in prompts
  - LLM analyzes full context for planning

---

## Summary

✅ **Conversation memory is now enabled!**

You can:
- Ask follow-up questions naturally
- Use pronouns like "it", "that", "this"
- Build on previous answers
- Have multi-turn conversations

The system will:
- Remember all previous turns
- Understand references to earlier topics
- Plan workflows with full context
- Provide contextually relevant answers

**Try it now:** `python chat.py` 🚀
