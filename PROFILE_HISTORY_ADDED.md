# Student Profile & Chat History - Now Included! ✅

## What Was Added

I've enhanced `streamlit_app_agent_view.py` to include:

1. **Student Profile** (optional, in sidebar)
2. **Conversation History** (tracked across queries)
3. **Profile-aware query enhancement** (coordinator gets context)

---

## New Features

### 1. Student Profile (Sidebar)

**Location:** Left sidebar, always visible

**Fields:**
- **Major:** Dropdown (Computer Science, IS, Business, Biology, or "Not set")
- **Current Semester:** Dropdown (First-Year Fall through Fourth-Year Spring, or "Not set")
- **GPA:** Optional slider (0.0 - 4.0)

**Features:**
- ✅ **All fields optional** - system works fine without profile
- ✅ **Profile summary badge** - shows current profile at a glance
- ✅ **Clear Profile button** - reset all fields
- ✅ **Profile indicator** - main area shows when profile is being used

**How it works:**

```
Sidebar:
┌────────────────────────────┐
│ 👤 Student Profile          │
│ Optional - enhances advice │
│                            │
│ Major: [Computer Science ▼]│
│ Current Semester:          │
│   [Second-Year Fall ▼]     │
│ ☑ Set GPA                  │
│   [────●────] 3.5          │
│                            │
│ ✅ Major: Computer Science │
│    Semester: Second-Year   │
│    Fall | GPA: 3.5         │
│                            │
│ [🗑️ Clear Profile]         │
└────────────────────────────┘
```

### 2. Conversation History (Sidebar)

**Location:** Left sidebar, below profile

**Features:**
- ✅ **Tracks all exchanges** - user queries + AI responses
- ✅ **Exchange counter** - shows number of Q&A pairs
- ✅ **Expandable history viewer** - see past conversations
- ✅ **Clear History button** - start fresh
- ✅ **Used for context** - previous exchanges inform new queries

**How it works:**

```
Sidebar:
┌────────────────────────────┐
│ 💬 Conversation History    │
│ 3 exchanges                │
│                            │
│ ▼ View History             │
│   👤 You: What are CS...  │
│   🤖 AI: The CS major...  │
│   ───────────────────────  │
│   👤 You: Can I add...    │
│   🤖 AI: Yes, you can...  │
│   ───────────────────────  │
│   👤 You: Plan my...      │
│   🤖 AI: Here's a plan... │
│                            │
│ [🗑️ Clear History]         │
└────────────────────────────┘
```

### 3. Profile-Aware Query Enhancement

**How it works:**

When a student has profile set, their query is automatically enhanced:

**Without profile:**
```
User types: "What courses should I take next semester?"

Coordinator receives:
"What courses should I take next semester?"
```

**With profile:**
```
User types: "What courses should I take next semester?"

Profile:
- Major: Computer Science
- Semester: Second-Year Fall
- GPA: 3.5

Coordinator receives:
"I'm a Computer Science major currently in Second-Year Fall with a 3.5 GPA. What courses should I take next semester?"
```

The coordinator can now give **personalized recommendations** based on:
- Major requirements
- Current year level
- Academic performance

**Visual indicator:**
```
Main area shows:
┌──────────────────────────────────────────────┐
│ ℹ️ Using profile: Major: Computer Science | │
│    Semester: Second-Year Fall | GPA: 3.5     │
└──────────────────────────────────────────────┘
```

### 4. Example Queries (Sidebar)

**Location:** Left sidebar, below history

Quick-start buttons for common queries:
- "What are CS requirements?"
- "Plan my graduation"
- "Can I add a minor?"
- "Next semester courses?"

Click any button to instantly process that query.

---

## How Profile Context is Used

### In Workflow Execution

```python
# execute_workflow() function:

def execute_workflow():
    query = st.session_state.current_query
    profile = st.session_state.student_profile

    # Enhance query with profile
    enhanced_query = inject_profile_into_query(query, profile)

    # Build conversation history
    conversation_messages = [
        HumanMessage(content=msg['content']) if msg['role'] == 'user'
        else AIMessage(content=msg['content'])
        for msg in st.session_state.conversation_history
    ]

    # Pass to workflow
    initial_state = {
        "user_query": enhanced_query,  # Enhanced with profile
        "student_profile": profile,     # Full profile object
        "messages": conversation_messages,  # Chat history
        # ...
    }
```

### Profile Injection Logic

```python
def inject_profile_into_query(query: str, profile: dict) -> str:
    context_parts = []

    if profile.get('major'):
        context_parts.append(f"I'm a {major} major")

    if profile.get('current_semester'):
        context_parts.append(f"currently in {semester}")

    if profile.get('gpa'):
        context_parts.append(f"with a {gpa} GPA")

    if context_parts:
        context = ". ".join(context_parts) + ". "
        return context + query

    return query  # No profile = no enhancement
```

### Conversation History

After each successful query:
```python
# Save to history
st.session_state.conversation_history.append({
    "role": "user",
    "content": original_query
})
st.session_state.conversation_history.append({
    "role": "assistant",
    "content": final_answer
})
```

Next query uses this history for context!

---

## Usage Examples

### Example 1: Without Profile

**Setup:**
- No profile set
- No history

**Query:** "Can I add a Business minor?"

**What coordinator sees:**
```
Query: "Can I add a Business minor?"
Profile: {} (empty)
Messages: [] (empty)
```

**Response:** General information about Business minor requirements

---

### Example 2: With Profile

**Setup:**
- Major: Computer Science
- Semester: Third-Year Fall
- GPA: 3.2

**Query:** "Can I add a Business minor?"

**What coordinator sees:**
```
Query: "I'm a Computer Science major currently in Third-Year Fall with a 3.2 GPA. Can I add a Business minor?"
Profile: {
    "major": ["Computer Science"],
    "current_semester": "Third-Year Fall",
    "gpa": 3.2
}
Messages: []
```

**Response:**
- Considers CS requirements already completed
- Calculates remaining semesters (3 left)
- Checks if minor fits in remaining time
- Personalized to junior-level CS student

---

### Example 3: With Profile + History

**Setup:**
- Major: Information Systems
- Semester: First-Year Spring
- GPA: 3.8
- Previous query: "What are IS major requirements?"

**Query:** "What should I take next semester?"

**What coordinator sees:**
```
Query: "I'm an Information Systems major currently in First-Year Spring with a 3.8 GPA. What should I take next semester?"
Profile: {
    "major": ["Information Systems"],
    "current_semester": "First-Year Spring",
    "gpa": 3.8
}
Messages: [
    HumanMessage("What are IS major requirements?"),
    AIMessage("The IS major requires... [previous answer]")
]
```

**Response:**
- Knows student is IS major
- Knows they're a freshman
- Considers high GPA (can handle challenging courses)
- **References previous conversation** about IS requirements
- Recommends sophomore fall courses that follow IS sequence

---

## Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Multi-Agent Academic Advising System                    │
│  Real-Time Agent Collaboration Visualization                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Sidebar:                      Main Area:                    │
│ ┌──────────────┐             ┌────────────────────────────┐│
│ │👤 Profile    │             │ ℹ️ Using profile: CS major││
│ │              │             │                            ││
│ │Major: CS     │             │ [Query input............]  ││
│ │Semester: 2F  │             │ [🚀 Process]               ││
│ │GPA: 3.5      │             │                            ││
│ │✅ Set        │             │ 🎯 COORDINATOR             ││
│ │[Clear]       │             │ [Visual agent card]        ││
│ │              │             │                            ││
│ │💬 History    │             │ 🤖 AGENTS (2x2 grid)       ││
│ │3 exchanges   │             │ [Visual agent cards]       ││
│ │[View]        │             │                            ││
│ │[Clear]       │             │ 📝 FINAL ANSWER            ││
│ │              │             │ [Answer box]               ││
│ │💡 Examples   │             │                            ││
│ │[What are CS] │             │ Timeline & Blackboard →    ││
│ │[Plan grad]   │             │                            ││
│ │[Add minor]   │             └────────────────────────────┘│
│ └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Comparison: Before vs After

| Feature | Before | After ✅ |
|---------|--------|----------|
| Student profile | ❌ Not included | ✅ Optional sidebar |
| Profile awareness | ❌ No | ✅ Query enhancement |
| Chat history | ❌ Not tracked | ✅ Full history |
| History context | ❌ No | ✅ Used in workflow |
| Profile indicator | ❌ No | ✅ Visible badge |
| Example queries | ❌ Bottom only | ✅ Sidebar buttons |
| Personalization | ❌ Generic | ✅ Profile-based |

---

## Benefits for ACL 2026 Demo

### Demo Scenario 1: Show Optional Profile

```
1. Ask query without profile
   → Generic answer

2. Set profile (CS major, sophomore, 3.5 GPA)

3. Ask same query again
   → Personalized answer specific to CS sophomore

4. Point out difference in coordinator reasoning
```

### Demo Scenario 2: Show Conversation Context

```
1. Ask: "What are CS requirements?"
   → System explains requirements

2. Ask: "Can I handle those courses?"
   → System references previous answer
   → Uses GPA to assess difficulty

3. Point to conversation history showing context
```

### Demo Scenario 3: Show Profile Enhancement

```
1. Set profile: IS major, junior, 3.0 GPA

2. Ask: "What should I take next?"

3. Show enhanced query in timeline:
   "I'm an Information Systems major currently in
    Third-Year Fall with a 3.0 GPA. What should I
    take next?"

4. Show how coordinator used this context
```

---

## Running the Enhanced Interface

```bash
streamlit run streamlit_app_agent_view.py
```

**What you'll see:**

1. **Left sidebar** with:
   - Student Profile section
   - Conversation History
   - Example queries

2. **Main area** with:
   - Profile indicator (if set)
   - All 5 agents visible
   - Real-time collaboration
   - Final answer

3. **Right sidebar** with:
   - Event timeline
   - Blackboard state

---

## Summary

**Your question:** "Does this include chat history and student profile?"

**Answer:** ✅ **YES, now it does!**

**Added features:**
- ✅ Optional student profile (major, semester, GPA)
- ✅ Conversation history tracking
- ✅ Profile-aware query enhancement
- ✅ History context in workflow
- ✅ Visual indicators
- ✅ Clear/reset buttons
- ✅ Example queries in sidebar

**The system now:**
1. Tracks all conversations
2. Uses profile to personalize responses
3. Maintains context across queries
4. Shows profile usage transparently
5. Allows students to control their data

**Perfect for ACL 2026 demos showing how context improves multi-agent collaboration!** 🎓✨
