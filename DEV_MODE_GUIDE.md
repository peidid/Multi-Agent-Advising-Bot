# Development Mode Guide

## Overview

The chat interface now includes a **Development Mode** that allows you to manually select which agents to use, bypassing the automatic intent classification. This is useful for:

- Testing specific agents in isolation
- Debugging agent behavior
- Comparing agent responses
- Developing and refining agent prompts

## How to Use

### Enabling Development Mode

In the chat interface, type:
```
mode:dev
```

You'll see the prompt change from `💬 You:` to `🔧 Dev:` and new commands will be available.

### Manual Agent Selection Commands

Once in development mode, use these commands:

#### 1. Test Programs Requirements Agent Only
```
@programs <your query>
```

**Example:**
```
@programs What are the requirements for a CS major?
```

This will:
- Skip intent classification
- Use only the Programs Requirements Agent
- Show you exactly what this agent retrieves and responds

#### 2. Test Course Scheduling Agent Only
```
@courses <your query>
```

**Example:**
```
@courses What are the prerequisites for 15-213?
```

This will:
- Skip intent classification
- Use only the Course Scheduling Agent
- Show you course-specific information retrieval

#### 3. Test Policy Compliance Agent Only
```
@policy <your query>
```

**Example:**
```
@policy Can I take more than 18 units?
```

This will:
- Skip intent classification
- Use only the Policy Compliance Agent
- Show you policy-specific information retrieval

#### 4. Test All Agents Together
```
@all <your query>
```

**Example:**
```
@all Plan my fall semester with 15-213, 15-251, and 21-241
```

This will:
- Skip intent classification
- Run all three agents in sequence
- Show collaboration and negotiation between all agents

### Switching Back to Normal Mode

To return to automatic intent classification:
```
mode:normal
```

## Use Cases

### Use Case 1: Testing Agent Isolation
**Problem:** You want to see if the Programs Agent correctly retrieves major requirements.

**Solution:**
```
mode:dev
@programs What courses do I need for a CS major?
```

You'll see exactly what the Programs Agent retrieves from its RAG database and how it processes the query.

### Use Case 2: Comparing Agent Responses
**Problem:** You're not sure which agent should handle a query about prerequisites.

**Solution:**
```
mode:dev
@programs What are the prerequisites for 15-213?
@courses What are the prerequisites for 15-213?
```

Compare how each agent handles the same query.

### Use Case 3: Debugging RAG Retrieval
**Problem:** The system isn't finding course information correctly.

**Solution:**
```
mode:dev
@courses Tell me about course 67-364
```

Watch the Course Scheduling Agent's RAG retrieval process to see what documents it finds.

### Use Case 4: Testing Multi-Agent Collaboration
**Problem:** You want to see how all agents work together without the coordinator's intent classification.

**Solution:**
```
mode:dev
@all I want to add a minor in Business, what courses do I need?
```

This forces all agents to run and shows their collaboration process.

## Tips

1. **Use `@programs` for:**
   - Major/minor requirements
   - Degree progress questions
   - Program-level planning

2. **Use `@courses` for:**
   - Specific course information
   - Prerequisites, corequisites
   - Course schedules and offerings
   - Assessment structure

3. **Use `@policy` for:**
   - University policies
   - Unit limits
   - Compliance questions
   - Academic regulations

4. **Use `@all` when:**
   - You want to see full collaboration
   - Testing complex queries
   - Debugging multi-agent interactions

## Example Session

```
💬 You: mode:dev
✅ Development mode enabled! You can now manually select agents.

🔧 Dev: @courses What are the prerequisites for 15-213?

🔧 Manual agent selection: Course Scheduling Agent

   Query: "What are the prerequisites for 15-213?"
   🔧 Skipping intent classification (manual mode)

================================================================================
🤖 STEP 2: Agent Execution
================================================================================

🤖 Executing Course Scheduling Agent
--------------------------------------------------------------------------------
   ⏳ Course Scheduling is processing your query...
   ...
   
🔧 Dev: @programs What are the requirements for a CS major?

🔧 Manual agent selection: Programs Requirements Agent

   Query: "What are the requirements for a CS major?"
   🔧 Skipping intent classification (manual mode)
   ...

🔧 Dev: mode:normal
✅ Normal mode enabled! Intent classification will run automatically.

💬 You: What are the requirements for a CS major?

================================================================================
🎯 STEP 1: Intent Classification
================================================================================
   ...
```

## Benefits for Development

1. **Faster Iteration**: Test specific agents without running the full workflow
2. **Better Debugging**: Isolate issues to specific agents
3. **Prompt Engineering**: Refine agent prompts by seeing isolated responses
4. **RAG Tuning**: Verify that agents retrieve correct documents
5. **Performance Testing**: Measure individual agent response times
6. **Comparison**: Compare automatic vs manual agent selection

## Notes

- Development mode persists until you switch back with `mode:normal`
- Manual agent selection bypasses intent classification but still runs negotiation/collaboration
- The coordinator still synthesizes the final answer from agent outputs
- All workflow steps (execution, negotiation, synthesis) still run normally
