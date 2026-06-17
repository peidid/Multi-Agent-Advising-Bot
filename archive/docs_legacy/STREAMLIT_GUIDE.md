## Streamlit Academic Advising UI - Complete Guide

**Perfect for ACL 2026 Demo Track!**

This Streamlit interface provides a **visual demonstration** of your multi-agent system's:
- Dynamic coordinator decision-making
- Agent collaboration and negotiation
- Blackboard state evolution
- Conflict resolution process
- Academic planning visualization

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_streamlit.txt
```

This installs:
- `streamlit` - Web UI framework
- `plotly` - Interactive visualizations
- `pandas` - Data handling

### 2. Run the App

```bash
streamlit run streamlit_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 🎨 UI Features

### Tab 1: 💬 Chat Interface

**Standard chat interface** with enhanced features:

- **Real-time agent status cards**
  - Shows which agents are activated
  - Displays agent confidence levels
  - Expandable output details

- **Visual plan display**
  - Semester-by-semester breakdown
  - Color-coded unit loads (green ≤48, yellow ≤54, red >54)
  - Course listings per semester

- **Student profile customization**
  - Change major, semester, GPA
  - Affects planning recommendations

**Example queries** (click to try):
- "What are the CS major requirements?"
- "Help me plan my courses until graduation"
- "Can I add a Business minor?"
- "Can I graduate in 3.5 years?"

### Tab 2: 🔬 Research View

**Perfect for ACL 2026 demos!** Shows:

#### Dynamic Workflow Visualization
- Which agents were activated
- Execution order
- Why each agent was chosen

#### Agent Collaboration Analysis
- Individual agent contributions
- Confidence scores per agent
- Risks and constraints identified

#### Blackboard State Evolution
- Slider to view state at different workflow stages
- See how state changes as agents execute
- Structured JSON view of blackboard

#### Workflow Timeline
- Chronological event log
- Agent start/complete events
- Negotiation steps
- Coordinator decisions

#### Negotiation Protocol Display
- Conflict detection details
- Proposal + Critique exchanges
- Resolution options
- Final agreed solution

### Tab 3: 📊 System Analytics

**Performance metrics:**
- Total queries processed
- Agent activation counts
- Negotiation frequency
- Average confidence scores

**Agent usage breakdown:**
- Bar chart of agent activations
- Shows which agents are used most
- Identifies collaboration patterns

**Activity log:**
- Recent workflow events
- Timestamped actions
- Event type indicators

### Tab 4: 📚 Documentation

**In-app documentation:**
- Agent descriptions and capabilities
- Coordinator explanation
- Negotiation protocol details
- Research contributions for ACL 2026
- Links to external documentation

---

## 🎯 Research Demonstration Features

### 1. **Visible Multi-Agent Collaboration**

The UI makes agent interactions **transparent**:

```
🎯 Coordinator Analysis:
   Query requires: degree requirements + course planning

🤖 Agents Activated:
   1. Programs & Requirements Agent
   2. Academic Planning Agent
   3. Policy & Compliance Agent

📋 Blackboard State:
   - Programs Agent: Identified 12 required courses
   - Planning Agent: Generated 2 plan options
   - Policy Agent: Flagged 1 overload semester

🔄 Negotiation:
   - Policy: "Semester 3 has 60 units (exceeds 54)"
   - Planning: "Redistributing 2 courses to Semester 4"
   - Policy: "Revised plan approved"
```

### 2. **Emergent Intelligent Behavior**

Watch the LLM **reason** about planning:
- No hardcoded prerequisite rules
- Infers sequencing from course descriptions
- Adapts to novel constraints dynamically

### 3. **Interactive Conflict Resolution**

When conflicts arise:
- System presents trade-offs visually
- User can see multiple resolution options
- Transparent decision-making process

### 4. **Structured Blackboard Communication**

View the **typed schema** in action:
- PlanOption objects with semesters, courses, confidence
- Risk objects with severity and descriptions
- Constraint objects with hard/soft flags
- All viewable as structured JSON

---

## 📸 Screenshots & Demo Flow

### Ideal Demo Flow for ACL 2026

**Step 1: Simple Query**
```
User: "What are the CS major requirements?"

Show:
- Single agent activated (Programs Agent)
- Quick response, high confidence
- No negotiation needed
```

**Step 2: Complex Planning Query**
```
User: "Help me plan my courses until graduation with a Business minor"

Show:
- Multiple agents activated (Programs + Planning + Courses + Policy)
- Blackboard evolving as each agent contributes
- Plans generated with semester structure
- Visual semester cards
```

**Step 3: Negotiation Example**
```
User: "Can I graduate in 3.5 years?"

Show:
- Planning agent proposes aggressive plan
- Policy agent identifies overload semesters
- Negotiation: back-and-forth revision
- Final plan with user choice presented
```

**Step 4: Research View**
```
Switch to Research tab

Show:
- Workflow timeline with all events
- Agent collaboration breakdown
- Blackboard state slider (show evolution)
- Negotiation protocol visualization
```

---

## 🎬 Customization Guide

### Adding Custom Visualizations

#### 1. **Agent Interaction Graph**

Add to `render_research_view()`:

```python
import plotly.graph_objects as go

def show_agent_graph(state):
    """Show agent interaction as network graph."""

    # Create nodes for each agent
    agents = state.get("active_agents", [])

    # Create edges based on blackboard reads/writes
    # (coordinator → agent → blackboard → other agents)

    fig = go.Figure(data=[go.Sankey(
        node = dict(
          label = ["Coordinator"] + agents + ["Blackboard"],
          color = "blue"
        ),
        link = dict(
          source = [0, 0, 1, 2],  # indices
          target = [1, 2, 3, 3],
          value = [1, 1, 1, 1]
      ))])

    st.plotly_chart(fig)
```

#### 2. **Confidence Timeline**

Track confidence over conversation:

```python
def show_confidence_timeline():
    """Show how confidence evolves."""

    confidences = []
    for state in st.session_state.blackboard_states:
        for agent, output in state.get("agent_outputs", {}).items():
            confidences.append({
                "query": len(confidences) + 1,
                "agent": agent,
                "confidence": output.confidence
            })

    df = pd.DataFrame(confidences)
    st.line_chart(df.pivot(index="query", columns="agent", values="confidence"))
```

#### 3. **Semester Workload Visualization**

For planning agent output:

```python
def visualize_workload(plan: PlanOption):
    """Visualize semester workload distribution."""

    semesters = [s['term'] for s in plan.semesters]
    units = [s['total_units'] for s in plan.semesters]

    fig = go.Figure(data=[
        go.Bar(x=semesters, y=units, marker_color='lightblue')
    ])

    # Add threshold lines
    fig.add_hline(y=48, line_dash="dash", line_color="green",
                  annotation_text="Normal Load")
    fig.add_hline(y=54, line_dash="dash", line_color="orange",
                  annotation_text="Maximum Allowed")

    st.plotly_chart(fig)
```

### Styling Customizations

Edit the CSS in `st.markdown()` section:

```python
# Change agent card colors
.agent-card {
    background: linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 100%);
}

# Change active animation
@keyframes pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(66, 153, 225, 0.7); }
    50% { transform: scale(1.05); box-shadow: 0 0 0 10px rgba(66, 153, 225, 0); }
}
```

### Adding New Tabs

```python
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "💬 Chat",
    "🔬 Research",
    "📊 Analytics",
    "📚 Docs",
    "🎥 Demo Mode"  # NEW
])

with tab5:
    render_demo_mode()
```

---

## 🔧 Configuration Options

### Session State Variables

Control app behavior via `st.session_state`:

```python
# In sidebar:
if st.checkbox("Auto-expand agent outputs"):
    st.session_state.auto_expand = True

if st.checkbox("Show detailed blackboard"):
    st.session_state.show_blackboard = True

# Animation speed
animation_speed = st.slider("Animation Speed", 0.1, 2.0, 0.5)
st.session_state.animation_delay = animation_speed
```

### Logging Levels

Add to sidebar for debugging:

```python
log_level = st.selectbox("Log Level", ["INFO", "DEBUG", "VERBOSE"])

if log_level == "VERBOSE":
    # Show all LLM prompts and responses
    st.session_state.verbose = True
```

---

## 🎓 ACL 2026 Demo Tips

### Before the Demo

1. **Prepare example queries** that showcase:
   - Simple single-agent queries
   - Complex multi-agent collaboration
   - Negotiation scenarios
   - Planning with constraints

2. **Seed the conversation**:
   ```python
   # Add to streamlit_app.py
   if 'demo_mode' in st.query_params:
       st.session_state.conversation_history = [
           {"role": "user", "content": "What are CS requirements?"},
           {"role": "assistant", "content": "..."},
           # Pre-populate with good examples
       ]
   ```

3. **Take screenshots** for paper:
   - Agent activation sequence
   - Blackboard state evolution
   - Negotiation visualization
   - Plan display

### During the Demo

**Script:**

1. **Start simple**: "What are the CS major requirements?"
   - Point out single agent activation
   - Show confidence score
   - Quick response time

2. **Show collaboration**: "Help me plan my courses until graduation"
   - Watch multiple agents activate
   - Point to timeline as it updates
   - Show blackboard state growing

3. **Demonstrate negotiation**: "Can I graduate in 3.5 years?"
   - Planning agent proposes aggressive plan
   - Policy agent critiques (overload)
   - Show revision process
   - Explain Proposal + Critique protocol

4. **Highlight research**: Switch to Research View
   - "This shows our dynamic workflow planning"
   - "Notice how agents communicate via blackboard"
   - "The LLM coordinator decides which agents to activate"

5. **Show plan visualization**:
   - "Here's the semester-by-semester plan"
   - Point to color-coded workload
   - "System automatically balanced units"

### Questions to Anticipate

**Q: How do agents communicate?**
A: *Switch to Research View, show Blackboard State* - "Through this structured blackboard. No direct agent-to-agent messaging."

**Q: What if agents disagree?**
A: *Use negotiation example* - "The coordinator detects conflicts and triggers negotiation. Let me show you..."

**Q: Is this hardcoded?**
A: *Show timeline* - "No hardcoded rules. The LLM coordinator dynamically decides workflow. See how execution order varies by query?"

**Q: How accurate is planning?**
A: *Show confidence scores* - "Each agent reports confidence. System can flag uncertainties. The planning agent shows 85% confidence here because it's making assumptions about future course availability."

---

## 📊 Performance Optimization

### Caching

Add Streamlit caching for expensive operations:

```python
@st.cache_data
def load_program_requirements(program: str):
    """Cache program requirements."""
    # Your loading logic
    pass

@st.cache_resource
def get_llm_instance():
    """Cache LLM initialization."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model="gpt-4o")
```

### Async Processing

For long-running queries, use async:

```python
import asyncio

async def process_query_async(query: str):
    """Process query asynchronously."""
    # Your processing logic
    pass

# In Streamlit:
with st.spinner("Processing..."):
    response = asyncio.run(process_query_async(user_query))
```

### Progressive Display

Update UI as agents complete:

```python
# Create placeholders
agent_placeholders = {
    agent: st.empty()
    for agent in ["programs", "courses", "policy", "planning"]
}

# Update as each completes
for agent in active_agents:
    with agent_placeholders[agent]:
        st.success(f"✅ {agent} completed")
        # Show output
```

---

## 🐛 Troubleshooting

### Issue: Streamlit won't start

```bash
# Check if port is in use
netstat -ano | findstr :8501

# Use different port
streamlit run streamlit_app.py --server.port 8502
```

### Issue: App is slow

- Enable caching (see Performance section)
- Reduce conversation history display limit
- Use `st.empty()` and `.container()` strategically

### Issue: State not persisting

```python
# Always initialize in session_state
if 'my_var' not in st.session_state:
    st.session_state.my_var = default_value
```

### Issue: UI not updating

- Check for `st.rerun()` calls
- Ensure state modifications trigger re-renders
- Use `st.empty()` for dynamic content

---

## 📦 Deployment Options

### Option 1: Streamlit Cloud (Free)

1. Push to GitHub
2. Go to streamlit.io/cloud
3. Connect repository
4. Deploy!

**Environment setup:**
- Add `.env` secrets in Streamlit Cloud dashboard
- Set `OPENAI_API_KEY` in secrets

### Option 2: Local Demo

```bash
# Run on local network (for demos)
streamlit run streamlit_app.py --server.address 0.0.0.0
```

### Option 3: Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.10

WORKDIR /app

COPY requirements.txt requirements_streamlit.txt ./
RUN pip install -r requirements.txt -r requirements_streamlit.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0"]
```

---

## 🎬 Video Recording Tips

For paper/demo videos:

1. **Screen resolution**: 1920x1080 (16:9)
2. **Zoom level**: 100% (readable text)
3. **Browser**: Chrome (best Streamlit support)
4. **Hide browser chrome**: F11 fullscreen mode
5. **Cursor highlighting**: Use tool like ScreenBrush

**Recommended tools:**
- OBS Studio (free screen recording)
- Camtasia (professional editing)
- Loom (quick demos with narration)

---

## 📖 Additional Resources

- **Streamlit Docs**: https://docs.streamlit.io
- **Plotly Docs**: https://plotly.com/python/
- **Your Project Docs**:
  - `PLANNING_GUIDE.md`
  - `PLANNING_IMPLEMENTATION_SUMMARY.md`
  - `README.md`

---

## ✅ Summary

You now have a **production-ready Streamlit UI** that:

✅ Visualizes multi-agent collaboration in real-time
✅ Shows blackboard state evolution
✅ Displays negotiation and conflict resolution
✅ Presents academic plans beautifully
✅ Provides research analysis views
✅ Perfect for ACL 2026 demo track

**To run:**
```bash
pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

Then ask: *"Help me plan my courses until graduation"* 🎓
