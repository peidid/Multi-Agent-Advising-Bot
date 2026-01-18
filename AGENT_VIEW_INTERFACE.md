# Multi-Agent System Visualization Interface

**NOT a chatbot - Visual agent collaboration system**

**File:** `streamlit_app_agent_view.py`

---

## 🎯 What This Interface Does

This is a **completely different paradigm** from traditional chatbots:

✅ **All 5 agents are ALWAYS visible on screen**
✅ **Real-time state updates** - watch agents activate, think, and complete
✅ **Visual communication flow** - see information passing between agents
✅ **Live blackboard state** - monitor shared knowledge
✅ **Event timeline** - chronological system activity
✅ **NOT a chat interface** - system architecture that comes alive

---

## 🖥️ Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Multi-Agent Academic Advising System                    │
│  Real-Time Agent Collaboration Visualization                │
├─────────────────────────────────────────────────────────────┤
│  [Enter query...........................] [🚀 Process]      │
├─────────────────────────────────────────────────┬───────────┤
│                                                 │ Timeline  │
│  🎯 COORDINATOR                                 │ ────────  │
│  ┌───────────────────────────────────────────┐ │ 10:23:15  │
│  │ Intent Classifier & Coordinator           │ │ Started   │
│  │ Status: [THINKING] [ACTIVE] [COMPLETE]    │ │           │
│  │ Message: "Analyzing query..."             │ │ 10:23:16  │
│  │ [Confidence meter: ████████░░ 85%]        │ │ Activated │
│  └───────────────────────────────────────────┘ │ 3 agents  │
│                                                 │           │
│  🤖 SPECIALIZED AGENTS                          │ ─────────│
│                                                 │ State     │
│  ┌─────────────────────┐ ┌─────────────────┐  │ ────────  │
│  │ 📚 Programs & Req   │ │ 📅 Scheduling   │  │ Active: 3 │
│  │ [IDLE/ACTIVE/DONE]  │ │ [IDLE/ACTIVE]   │  │ Risks: 0  │
│  │ Confidence: 92%     │ │ Confidence: 88% │  │ Plans: 2  │
│  │ "Based on CS req.." │ │ "For Spring..." │  │           │
│  └─────────────────────┘ └─────────────────┘  │           │
│                                                 │           │
│  ┌─────────────────────┐ ┌─────────────────┐  │           │
│  │ ⚖️ Policy          │ │ 🗓️ Planning     │  │           │
│  │ [COMPLETE]          │ │ [THINKING]      │  │           │
│  │ Confidence: 85%     │ │ Confidence: 78% │  │           │
│  │ "This complies..."  │ │ "Generating..." │  │           │
│  └─────────────────────┘ └─────────────────┘  │           │
│                                                 │           │
│  📝 FINAL ANSWER                                │           │
│  ┌───────────────────────────────────────────┐ │           │
│  │ Based on all agents, here's what you     │ │           │
│  │ need: [synthesized answer]...            │ │           │
│  └───────────────────────────────────────────┘ │           │
│                                                 │           │
│  [🔄 Reset System]                              │           │
└─────────────────────────────────────────────────┴───────────┘
```

---

## 🎨 Visual States

### Agent State Colors & Animations

Each agent card changes appearance based on its state:

#### 1. **IDLE** (Gray)
```
┌─────────────────────────┐
│ 📚 Programs Agent       │
│ [IDLE]                  │
│ Waiting for activation  │
└─────────────────────────┘
```
- Gray background
- Subtle border
- No animation

#### 2. **THINKING** (Orange, Pulsing)
```
┌─────────────────────────┐
│ 📚 Programs Agent       │ ⚡ Pulsing
│ [THINKING]              │
│ Analyzing requirements  │
└─────────────────────────┘
```
- Orange gradient background
- Pulsing animation
- "Thinking" badge blinks

#### 3. **ACTIVE** (Blue, Glowing)
```
┌─────────────────────────┐
│ 📚 Programs Agent       │ 🌟 Glowing
│ [ACTIVE]                │
│ Confidence: 92%         │
│ ████████░░              │
│ "Based on CS major..."  │
└─────────────────────────┘
```
- Blue gradient background
- Glowing border effect
- Shows confidence meter
- Displays agent's message

#### 4. **COMPLETE** (Green, Checkmark)
```
┌─────────────────────────┐
│ 📚 Programs Agent   ✅  │
│ [COMPLETE]              │
│ Confidence: 92%         │
│ Full response available │
└─────────────────────────┘
```
- Green gradient background
- Soft glow
- Confidence locked in
- Checkmark indicator

---

## 🔄 How Information Flow Works

### Visual Communication Between Agents

1. **User submits query**
   - Query appears in input box
   - All agents visible but IDLE

2. **Coordinator activates** (Purple glow)
   ```
   🎯 Coordinator [THINKING]
   "Analyzing query and determining which agents to activate..."
   ```

3. **Coordinator decides** (Timeline updates)
   ```
   Timeline:
   10:23:15 🎯 Coordinator: Started analysis
   10:23:16 🎯 Coordinator: Activated 3 agents
   ```

4. **Agents activate sequentially** (Visual cascade)
   ```
   📚 Programs Agent [THINKING] → [ACTIVE] → [COMPLETE]
                                    ↓
   📅 Scheduling Agent [THINKING] → [ACTIVE] → [COMPLETE]
                                    ↓
   ⚖️ Policy Agent [THINKING] → [ACTIVE] → [COMPLETE]
   ```

5. **Blackboard updates in real-time** (Right sidebar)
   ```
   🗂️ Blackboard State
   Active Agents: 3
   Constraints: 2
   Risks: 0
   Plans: 2
   ```

6. **Coordinator synthesizes** (Purple glow returns)
   ```
   🎯 Coordinator [ACTIVE]
   "Synthesizing final answer from all agent inputs"
   ```

7. **Final answer appears** (Blue box)
   ```
   📝 Final Answer
   [Synthesized response from all agents]
   ```

---

## 🎬 Usage Example

### Scenario: "What courses should I take next semester?"

**Timeline of what user SEES:**

```
00:00 - User types query and clicks "🚀 Process"

00:01 - Coordinator card lights up ORANGE (thinking)
        Message: "Analyzing query..."
        Timeline: "🎯 10:23:15: Coordinator started"

00:02 - Coordinator turns BLUE (active)
        Message: "Activated 3 agents: Programs, Scheduling, Policy"
        Timeline: "🎯 10:23:16: Activated 3 agents"

00:03 - Programs Agent card lights up ORANGE (thinking)
        Timeline: "🤖 10:23:17: Programs Agent started"

00:04 - Programs Agent turns BLUE (active)
        Message: "Based on CS major requirements, you need..."
        Confidence: 92%
        Timeline: "🤖 10:23:19: Programs Agent completed with 92% confidence"

00:05 - Scheduling Agent card lights up ORANGE (thinking)
        Timeline: "🤖 10:23:20: Scheduling Agent started"

00:06 - Scheduling Agent turns BLUE (active)
        Message: "For Spring 2026, available courses include..."
        Confidence: 88%
        Timeline: "🤖 10:23:22: Scheduling Agent completed with 88% confidence"

00:07 - Policy Agent card lights up ORANGE (thinking)
        Timeline: "🤖 10:23:23: Policy Agent started"

00:08 - Policy Agent turns BLUE (active)
        Message: "This selection complies with all policies..."
        Confidence: 85%
        Timeline: "🤖 10:23:25: Policy Agent completed with 85% confidence"

00:09 - All agent cards turn GREEN (complete) ✅
        Blackboard State updates:
        - Active Agents: 3
        - Constraints: 2
        - Risks: 0

00:10 - Coordinator turns GREEN (complete)
        Message: "Synthesized final answer from all agent inputs"

00:11 - Final Answer box appears with synthesized response
```

**Total duration: ~11 seconds with full visualization**

---

## 🌟 Key Features

### 1. Always-Visible Agent System

**NOT like a chatbot where you only see messages.**

Instead:
- All 5 agents are ALWAYS on screen
- You watch them activate, think, work, complete
- Like monitoring a team of experts collaborating

### 2. Real-Time State Visualization

Each agent shows:
- **Current state** (idle/thinking/active/complete)
- **Confidence score** (visual meter)
- **Message preview** (what the agent is saying)
- **Visual effects** (colors, animations, glows)

### 3. Communication Transparency

You see:
- **When** each agent starts working (timeline)
- **What** each agent says (message in card)
- **How confident** they are (percentage + meter)
- **Blackboard updates** (shared state changes)

### 4. Event Timeline

Chronological log of everything:
```
🎯 10:23:15: Coordinator: Analyzing query
🎯 10:23:16: Coordinator: Activated 3 agents
🤖 10:23:17: Programs Agent: Started
🤖 10:23:19: Programs Agent: Completed with 92% confidence
🤖 10:23:20: Scheduling Agent: Started
🤖 10:23:22: Scheduling Agent: Completed with 88% confidence
🔄 10:23:23: Negotiation: Policy critiqued Planning
✨ 10:23:25: Coordinator: Synthesized final answer
```

### 5. Blackboard State Monitor

Live metrics:
- Active Agents count
- Constraints found
- Risks identified
- Plans generated
- Current workflow step

---

## 🎯 Perfect for ACL 2026 Demo

### Why This Interface Works for Research Demo

✅ **Shows the system architecture** - Not hidden behind chat UI
✅ **Demonstrates dynamic collaboration** - Watch agents work together
✅ **Visualizes negotiation** - See conflicts arise and resolve
✅ **Highlights emergent behavior** - Coordinator decisions visible
✅ **Educational** - Audience learns how multi-agent systems work
✅ **Transparent** - Every decision and communication is visible

### Demo Script for ACL Presentation

**Presenter:**
> "This is NOT a chatbot. This is a multi-agent collaboration system where you can SEE all 5 agents working together in real-time."

[Submit query: "Can I add a Business minor?"]

> "Watch as the coordinator analyzes the query..."
> [Coordinator lights up orange]

> "...and decides to activate 3 agents"
> [Timeline shows activation]

> "Now the Programs Agent analyzes degree requirements..."
> [Programs card lights up, shows confidence]

> "...the Scheduling Agent checks course availability..."
> [Scheduling card activates]

> "...and the Policy Agent verifies compliance"
> [Policy card activates]

> "Notice how each agent contributes with different confidence levels. The blackboard on the right shows the shared state updating in real-time."

> "Finally, the coordinator synthesizes all inputs into a coherent answer."
> [Final answer appears]

---

## 🚀 Running the Interface

```bash
streamlit run streamlit_app_agent_view.py
```

---

## 📊 Comparison: Chat vs Agent View

| Aspect | Chat Interface | **Agent View Interface** |
|--------|---------------|--------------------------|
| Agent visibility | Hidden | ✅ **Always visible** |
| State transparency | Text only | ✅ **Visual states** |
| Collaboration | Described | ✅ **Shown in real-time** |
| Communication flow | Implied | ✅ **Animated transitions** |
| System architecture | Hidden | ✅ **Front and center** |
| Research value | Low | ✅ **High - shows process** |
| Educational value | Low | ✅ **High - see how it works** |
| Demo impact | Moderate | ✅ **High - visually compelling** |

---

## 🎨 Customization Options

### Change Update Speed

In `process_query_with_visualization()`:

```python
time.sleep(0.5)  # Pause between state updates
```

Adjust for:
- **Faster demos**: `time.sleep(0.2)`
- **Slower explanation**: `time.sleep(1.0)`
- **No delay**: Remove sleep calls

### Add More Visual Effects

```python
# Add arrow animations between agents
# Add message "flying" between cards
# Add sound effects (optional)
```

---

## ✅ What Makes This Different

**Traditional chatbot:**
```
User: "What courses should I take?"
Bot: "I recommend taking 15-213, 15-251..."
```
*User has NO IDEA how the answer was generated*

**This agent view interface:**
```
User sees:
1. Coordinator thinking → "I need Programs, Scheduling, Policy agents"
2. Programs Agent → "CS requirements include..." [92% confidence]
3. Scheduling Agent → "Spring courses available..." [88% confidence]
4. Policy Agent → "This complies with..." [85% confidence]
5. Coordinator → "Synthesizing all inputs..."
6. Final Answer → "Based on all agents, I recommend..."
```
*User SEES the entire multi-agent collaboration process*

---

## 🎓 For ACL 2026 Reviewers

When reviewers access your demo, they will:

1. **Immediately see** all 5 agents on screen
2. **Submit a query** and watch the system come alive
3. **Observe** the coordinator making decisions
4. **Watch** agents activate, think, and complete tasks
5. **See** confidence scores and messages
6. **Track** the entire process in the timeline
7. **Understand** how the multi-agent system works

**No explanation needed - the interface itself demonstrates the research contribution.**

---

## 🔧 Technical Implementation

### Agent State Management

```python
st.session_state.agent_states = {
    'coordinator': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
    'programs_requirements': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
    'course_scheduling': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
    'policy_compliance': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
    'academic_planning': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
}
```

### Real-Time Updates

```python
def update_agent_state(agent_name: str, state: AgentState, message: str = "", confidence: float = 0):
    st.session_state.agent_states[agent_name] = {
        'state': state,
        'message': message,
        'confidence': confidence
    }
    st.rerun()  # Triggers immediate UI update
```

### Visual Rendering

```python
def render_agent_card(agent_name: str, display_name: str, icon: str, is_coordinator: bool = False):
    # Determines card class based on state
    # Renders HTML with appropriate styling
    # Shows confidence meter, message, status badge
```

---

## 🎯 Summary

This interface **shows the multi-agent system as a system**, not as a chatbot:

✅ All agents always visible
✅ Real-time state updates
✅ Visual collaboration flow
✅ Transparent decision-making
✅ Perfect for research demos
✅ Educational and compelling

**Run it now:**
```bash
streamlit run streamlit_app_agent_view.py
```

**Your multi-agent system is now VISIBLE!** 🚀🤖
