# How to Chat with the Academic Advising System

## Quick Start

### 🎯 **RECOMMENDED: Workflow Demonstration** (Shows negotiation/collaboration)
```bash
python chat_demo_enhanced.py
```

**Features:**
- **Shows complete workflow step-by-step**
- **Demonstrates negotiation/collaboration between agents**
- **Displays each agent's contribution**
- **Shows conflict detection and resolution**
- **Final human-like advisor response**

### Option 2: Full-featured Chat Interface
```bash
python chat.py
```

**Features:**
- Clean, formatted output
- Shows which agents were consulted
- Displays confidence scores
- Shows conflicts and follow-up questions
- Command support (help, clear, quit)

### Option 3: Simple Chat Interface
```bash
python chat_simple.py
```

**Features:**
- Minimal, straightforward interface
- Just ask questions and get answers
- Perfect for quick testing

## Example Conversation (Workflow Demonstration)

```
💬 You: Can I add a CS minor as an IS student?

================================================================================
🎯 STEP 1: Intent Classification
================================================================================
   ✅ Intent Type: Add Minor
   📊 Priority: high
   🤖 Agents to Activate:
      1. Programs Requirements
      2. Policy Compliance

================================================================================
🤖 STEP 2: Agent Execution
================================================================================
   🤖 Executing Programs Requirements Agent
   ✅ Programs Requirements completed!
      Confidence: 0.85
   💭 Agent's Contribution:
      Based on the IS program requirements, adding a CS minor is possible...
   📋 Plan Options Proposed: 1

================================================================================
🔄 STEP 3: Collaboration & Negotiation
================================================================================
   📝 Programs Agent has proposed a plan.
   🔍 Policy Agent is critiquing the proposal...
   ✅ Policy Agent critique completed!
   ✅ No conflicts detected!

================================================================================
💬 STEP 4: Final Advisor Response
================================================================================
💡 ADVISOR'S ANSWER
================================================================================

Yes, you can add a CS minor as an IS student. Based on the program 
requirements and university policies, here's what you need to know...

[Full human-like advisor response continues...]
```

## Example Questions

### Requirements Questions
- "What are IS major requirements?"
- "What courses do I need for a CS minor?"
- "Can I add a CS minor as an IS student?"

### Course Planning
- "What courses should I take next semester?"
- "Can I take 15-112, 15-121, and 67-100 together?"
- "What are the prerequisites for 15-112?"

### Policy Questions
- "Can I take course overload?"
- "What is the policy on repeating courses?"
- "What happens if I'm on academic probation?"

### Degree Progress
- "Am I on track to graduate in 4 years?"
- "How many credits do I have left?"

## Commands

- `quit` or `exit` - End conversation
- `clear` - Clear screen (full chat only)
- `help` - Show help message (full chat only)

## Tips

1. **Be specific**: Ask clear, specific questions for best results
2. **Use course codes**: Include course codes (e.g., "15-112") when asking about specific courses
3. **Ask follow-ups**: The system can handle follow-up questions in the same session
4. **Check conflicts**: If the system detects conflicts, it will ask follow-up questions

## Troubleshooting

### "No response generated"
- Try rephrasing your question
- Be more specific
- Check that your OpenAI API key is set correctly

### Slow responses
- The system consults multiple agents, so responses may take 10-30 seconds
- This is normal for complex queries

### Import errors
- Make sure you've completed all implementation steps
- Check that all agent files exist
- Verify domain indexes are built (`python setup_domain_indexes.py`)

## Advanced: Customize Student Profile

To personalize responses, you can modify the `student_profile` in the chat scripts:

```python
state = {
    "user_query": user_input,
    "student_profile": {
        "major": ["IS"],
        "minor": [],
        "gpa": 3.5,
        "completed_courses": ["15-110", "67-100"],
        "flags": []
    },
    # ... rest of state
}
```

This allows the system to provide more personalized advice based on your academic history.

