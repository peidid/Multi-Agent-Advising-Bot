# Streamlit UI - Quick Start

**Goal:** Beautiful visual interface for your ACL 2026 multi-agent system demo!

---

## 🚀 Run in 3 Steps

### 1. Install Streamlit

```bash
pip install -r requirements_streamlit.txt
```

### 2. Launch the App

```bash
streamlit run streamlit_app.py
```

### 3. Open Browser

App automatically opens at: `http://localhost:8501`

---

## 🎯 What You'll See

### 4 Tabs:

1. **💬 Chat Interface**
   - Ask questions naturally
   - See agent cards activate in real-time
   - Visual semester-by-semester plans
   - Color-coded workload indicators

2. **🔬 Research View** (Perfect for ACL demos!)
   - Agent collaboration breakdown
   - Blackboard state evolution
   - Workflow timeline
   - Negotiation protocol visualization

3. **📊 System Analytics**
   - Performance metrics
   - Agent usage charts
   - Activity logs

4. **📚 Documentation**
   - In-app help
   - Research contributions
   - System architecture

---

## 💡 Try These Queries

**Click the sidebar examples or type:**

- "What are the CS major requirements?"
- "Help me plan my courses until graduation"
- "Can I add a Business minor?"
- "Can I graduate in 3.5 years?"

---

## 🎬 For ACL 2026 Demos

### Show This Flow:

1. **Simple query** → See single agent activate
2. **Planning query** → Watch multiple agents collaborate
3. **Switch to Research tab** → Point out:
   - Dynamic workflow (LLM decides which agents)
   - Blackboard communication (structured state)
   - Negotiation protocol (Proposal + Critique)
   - Timeline (chronological events)

### Key Talking Points:

✅ "No hardcoded rules - LLM coordinator decides workflow dynamically"
✅ "Agents communicate via structured blackboard (see JSON)"
✅ "Negotiation: Planning proposes → Policy critiques → Planning revises"
✅ "Emergent behavior: LLM infers prerequisites without explicit rules"

---

## 🎨 UI Features Highlights

### Agent Cards
- **Green pulse** = currently active
- **Expandable** to see full output
- Shows confidence, risks, constraints

### Plan Visualization
- **Green dots** = normal workload (≤48 units)
- **Yellow dots** = heavy load (49-54 units)
- **Red dots** = overload (>54 units, needs approval)

### Blackboard State
- **Slider** to view evolution
- **JSON view** for structured data
- See state grow as agents contribute

### Timeline
- Chronological workflow events
- Color-coded event types
- Timestamped actions

---

## 🔧 Customization

### Change Student Profile
Sidebar → Student Profile → Adjust major, semester, GPA

### Toggle Research Panel
Sidebar → "Show Research Analysis" checkbox

### Clear History
Sidebar → "Clear Conversation" button

---

## 📸 Screenshot Tips

For your paper/presentation:

1. **Agent Activation**: Chat tab during multi-agent query
2. **Blackboard Evolution**: Research tab with state slider
3. **Negotiation**: Research tab showing conflict resolution
4. **Plan Display**: Chat tab with semester cards
5. **Timeline**: Research tab with event log

---

## 🐛 Common Issues

**Port already in use:**
```bash
streamlit run streamlit_app.py --server.port 8502
```

**App won't start:**
```bash
# Check dependencies
pip install streamlit plotly pandas
```

**Slow performance:**
- Clear conversation history
- Restart Streamlit (Ctrl+C, then rerun)

---

## 📚 More Info

- **Complete Guide**: `STREAMLIT_GUIDE.md`
- **Planning Features**: `PLANNING_GUIDE.md`
- **System Docs**: `README.md`

---

## ✅ That's It!

```bash
streamlit run streamlit_app.py
```

Then ask: **"Help me plan my courses until graduation"**

Watch the magic happen! 🎓✨
