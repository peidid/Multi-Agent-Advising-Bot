# Bug Fix: Clarification Loop Issue

## Problem

The system entered an infinite clarification loop:
1. Asked for major → User provided "IS"
2. Re-analyzed and asked for "specific_degree_requirement" → User provided "IS" again
3. System showed "Waiting for clarification" and stopped

## Root Causes

### Issue 1: No Retry Limit
- The clarification loop had no maximum retry limit
- If the LLM kept asking for clarification, it would loop forever

### Issue 2: Over-Clarification
- The prompt was too aggressive in asking for details
- After knowing the major, it asked for "specific degree requirement"
- This is unnecessary - the system should proceed with available info

### Issue 3: Empty Workflow
- When clarification was still needed after retries, workflow was empty
- The system hit the "skip agent execution" check and stopped

## Fixes Applied

### Fix 1: Add Retry Limit (`chat.py`)

```python
# Before:
if clarification:
    # Update profile
    # Re-classify
    intent, workflow, _ = show_intent_classification(...)

# After:
clarification_retries = 0
max_clarification_retries = 1  # Only allow ONE clarification round

while clarification and clarification_retries < max_clarification_retries:
    # Update profile
    # Re-classify
    intent, workflow, clarification = show_intent_classification(...)
    clarification_retries += 1

# If still needs clarification after max retries, proceed anyway
if clarification and clarification_retries >= max_clarification_retries:
    print("\n   ⚠️  Proceeding with available information...")
    workflow = intent.get('required_agents', [])
```

**Result:** Maximum 1 clarification round, then proceeds regardless

### Fix 2: More Conservative Prompt (`coordinator/clarification_handler.py`)

Added to the prompt:

```python
IMPORTANT: 
- NEVER ask for clarification if you can make a reasonable answer with available information
- For grade/course questions, if major is known, proceed even if specific details are unclear
- Only ask for ONE type of missing information at a time (typically major/program)
```

**Result:** LLM is more conservative about asking for clarification

## Testing

### Test Case 1: Grade Question (Your Example)

```
You: is my 76-100 grade enough for the degree requirement?

System: What is your major?

You: IS

System: [Should proceed to agents - NOT ask for more details]
```

### Test Case 2: Simple Requirement Question

```
You: Do I need 15-122?

System: What is your major?

You: CS

System: [Should proceed to agents]
```

### Test Case 3: Already Clear

```
You: As a CS student, do I need 15-122?

System: [Should proceed immediately - no clarification]
```

## Expected Behavior

**After this fix:**

1. ✅ Maximum 1 clarification round
2. ✅ Only asks for major/program (not detailed requirements)
3. ✅ Proceeds with available information after clarification
4. ✅ Never enters infinite loop
5. ✅ More conservative about asking

**Example flow:**
```
Query: "is my 76-100 grade enough?"
  ↓
Ask: "What's your major?"
  ↓
User: "IS"
  ↓
Proceed to agents (with major=IS)
  ↓
Agents analyze grade requirements for IS
  ↓
Synthesize answer
```

## Files Modified

1. `chat.py` - Added retry limit and fallback
2. `coordinator/clarification_handler.py` - More conservative prompt

## Status

✅ Fixed - Ready for testing

## Next Test

Try the same query again:

```bash
python chat.py
```

```
You: is my 76-100 grade enough for the degree requirement?

[Should ask for major once]

You: IS

[Should proceed to agents - NOT ask again]
```
