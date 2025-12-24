# Chat Interface Guide

## Quick Start

Run the interactive chat interface:

```bash
python chat.py
```

## Features

The chat interface demonstrates the complete multi-agent workflow:

- **Step 1: Intent Classification** - Shows how Coordinator analyzes your query
- **Step 2: Agent Execution** - Displays which agents are activated and their contributions
- **Step 3: Collaboration & Negotiation** - Shows Proposal + Critique protocol in action
- **Step 4: Final Answer** - Synthesized human-like advisor response

## Example Conversation

```
💬 You: Can I add a CS minor as an IS student?

🎯 STEP 1: Intent Classification
   ✅ Intent Type: Add Minor
   🤖 Agents to Activate: Programs Requirements, Policy Compliance

🤖 STEP 2: Agent Execution
   🤖 Programs Agent: Proposes plan...
   🤖 Policy Agent: Critiques plan...

🔄 STEP 3: Collaboration & Negotiation
   ✅ No conflicts detected!

💬 STEP 4: Final Advisor Response
   [Human-like advisor answer combining all insights]
```

## Example Questions

### Requirements
- "What are IS major requirements?"
- "Can I add a CS minor as an IS student?"
- "What courses do I need for a Business minor?"

### Course Planning
- "What courses should I take next semester?"
- "Can I take 15-112, 15-121, and 67-100 together?"
- "What are the prerequisites for 15-112?"

### Policies
- "Can I take course overload?"
- "What is the policy on repeating courses?"
- "What happens if I'm on academic probation?"

## Commands

- `quit` or `exit` - End conversation
- `clear` - Clear screen
- `help` - Show help message

## Tips

1. **Be specific** - Clear, specific questions get better results
2. **Use course codes** - Include course codes (e.g., "15-112") when asking about specific courses
3. **Ask follow-ups** - The system handles follow-up questions
4. **Check conflicts** - If conflicts are detected, the system will ask follow-up questions

## Troubleshooting

### "No response generated"
- Try rephrasing your question
- Be more specific
- Check that your OpenAI API key is set correctly

### Slow responses
- Normal for complex queries (10-30 seconds)
- The system consults multiple agents and synthesizes answers

### Import errors
- Make sure you've completed setup: `python setup_domain_indexes.py`
- Check that all agent files exist
- Verify domain indexes are built

## Customizing Student Profile

To personalize responses, you can modify the student profile in `chat.py`:

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

This allows the system to provide more personalized advice based on academic history.
