"""
Streamlit Academic Advising Chatbot - Research Demo Interface

This interface demonstrates:
1. Multi-agent collaboration workflow
2. Coordinator decision-making process
3. Agent negotiations and conflict resolution
4. Blackboard state evolution
5. Interactive academic planning

Perfect for ACL 2026 demo track!
"""

import streamlit as st
from typing import Dict, List, Any
import json
from datetime import datetime
import time

# Suppress SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from multi_agent import app, coordinator, programs_agent, courses_agent, policy_agent, planning_agent
from blackboard.schema import WorkflowStep, ConflictType, AgentOutput, PlanOption
from langchain_core.messages import HumanMessage, AIMessage

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="CMU-Q Academic Advising - Multi-Agent System Demo",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    /* Main container */
    .main {
        padding: 1rem;
    }

    /* Agent cards */
    .agent-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
    }

    .agent-card-active {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.02); }
    }

    /* Blackboard state */
    .blackboard {
        background: #2d3748;
        color: #e2e8f0;
        padding: 1.5rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
    }

    /* Negotiation flow */
    .negotiation-step {
        border-left: 3px solid #48bb78;
        padding-left: 1rem;
        margin: 1rem 0;
    }

    .critique {
        border-left: 3px solid #f56565;
        padding-left: 1rem;
        margin: 1rem 0;
    }

    /* Timeline */
    .timeline-item {
        position: relative;
        padding-left: 2rem;
        padding-bottom: 1.5rem;
        border-left: 2px solid #cbd5e0;
    }

    .timeline-item::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 0;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #4299e1;
    }

    /* Plan display */
    .semester-card {
        background: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* Confidence badges */
    .confidence-high {
        background: #48bb78;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
    }

    .confidence-medium {
        background: #ed8936;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
    }

    .confidence-low {
        background: #f56565;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'workflow_log' not in st.session_state:
    st.session_state.workflow_log = []

if 'blackboard_states' not in st.session_state:
    st.session_state.blackboard_states = []

if 'student_profile' not in st.session_state:
    st.session_state.student_profile = {
        "major": ["Computer Science"],
        "minor": [],
        "current_semester": "Second-Year Fall",
        "completed_courses": [
            "15-112", "15-122", "21-120", "21-122", "21-127",
            "76-100", "76-101", "07-129", "99-101"
        ],
        "gpa": 3.5
    }

if 'show_research_panel' not in st.session_state:
    st.session_state.show_research_panel = True

if 'current_state' not in st.session_state:
    st.session_state.current_state = None

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_confidence_badge(confidence: float) -> str:
    """Return HTML badge for confidence level."""
    if confidence >= 0.8:
        return f'<span class="confidence-high">High: {confidence:.0%}</span>'
    elif confidence >= 0.6:
        return f'<span class="confidence-medium">Medium: {confidence:.0%}</span>'
    else:
        return f'<span class="confidence-low">Low: {confidence:.0%}</span>'

def format_timestamp() -> str:
    """Get formatted timestamp."""
    return datetime.now().strftime("%H:%M:%S")

def log_workflow_event(event_type: str, agent: str, description: str, data: Any = None):
    """Log a workflow event."""
    st.session_state.workflow_log.append({
        "timestamp": format_timestamp(),
        "type": event_type,
        "agent": agent,
        "description": description,
        "data": data
    })

def display_agent_card(agent_name: str, status: str, output: AgentOutput = None):
    """Display an agent card with status."""

    agent_info = {
        "programs_requirements": {
            "name": "Programs & Requirements",
            "icon": "📚",
            "role": "Degree requirements specialist"
        },
        "course_scheduling": {
            "name": "Course & Scheduling",
            "icon": "📅",
            "role": "Course information specialist"
        },
        "policy_compliance": {
            "name": "Policy & Compliance",
            "icon": "⚖️",
            "role": "University policy specialist"
        },
        "academic_planning": {
            "name": "Academic Planning",
            "icon": "🗓️",
            "role": "Multi-semester planning specialist"
        }
    }

    info = agent_info.get(agent_name, {"name": agent_name, "icon": "🤖", "role": "Agent"})

    card_class = "agent-card-active" if status == "active" else "agent-card"

    st.markdown(f"""
    <div class="{card_class}">
        <h4>{info['icon']} {info['name']}</h4>
        <p style="font-size: 0.9rem; opacity: 0.9;">{info['role']}</p>
        <p style="font-size: 0.85rem; margin-top: 0.5rem;">Status: {status.upper()}</p>
    </div>
    """, unsafe_allow_html=True)

    if output and status == "completed":
        with st.expander(f"📊 {info['name']} Output", expanded=False):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Confidence:** {get_confidence_badge(output.confidence)}", unsafe_allow_html=True)
            with col2:
                st.caption(f"{len(output.answer)} chars")

            st.markdown("**Answer:**")
            st.info(output.answer[:500] + "..." if len(output.answer) > 500 else output.answer)

            if output.plan_options:
                st.markdown("**Plan Options:**")
                for i, plan in enumerate(output.plan_options[:2], 1):
                    st.markdown(f"*Option {i}:* {len(plan.courses)} courses, {len(plan.semesters)} semesters")

            if output.risks:
                st.markdown("**Risks Identified:**")
                for risk in output.risks[:3]:
                    severity_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(risk.severity, "⚪")
                    st.caption(f"{severity_color} {risk.description}")

            if output.constraints:
                st.markdown("**Constraints:**")
                for constraint in output.constraints[:3]:
                    st.caption(f"{'🔴' if constraint.hard else '🟡'} {constraint.description}")

def display_blackboard_state(state: Dict[str, Any]):
    """Display current blackboard state."""
    st.markdown("### 📋 Blackboard State")

    # Show key state information
    cols = st.columns(4)

    with cols[0]:
        st.metric("Active Agents", len(state.get("active_agents", [])))

    with cols[1]:
        st.metric("Completed Agents", len(state.get("agent_outputs", {})))

    with cols[2]:
        st.metric("Risks", len(state.get("risks", [])))

    with cols[3]:
        st.metric("Conflicts", len(state.get("conflicts", [])))

    # Detailed state in expander
    with st.expander("🔍 Full Blackboard State (JSON)", expanded=False):
        # Filter out large message objects for display
        display_state = {
            "workflow_step": state.get("workflow_step"),
            "user_goal": state.get("user_goal"),
            "active_agents": state.get("active_agents", []),
            "next_agent": state.get("next_agent"),
            "plan_options": len(state.get("plan_options", [])),
            "risks": len(state.get("risks", [])),
            "constraints": len(state.get("constraints", [])),
            "conflicts": len(state.get("conflicts", []))
        }
        st.json(display_state)

def display_workflow_timeline():
    """Display workflow execution timeline."""
    st.markdown("### ⏱️ Workflow Timeline")

    for event in reversed(st.session_state.workflow_log[-10:]):  # Last 10 events
        event_icon = {
            "coordinator": "🎯",
            "agent_start": "▶️",
            "agent_complete": "✅",
            "negotiation": "🔄",
            "conflict": "⚠️",
            "synthesis": "🎨"
        }.get(event['type'], "•")

        st.markdown(f"""
        <div class="timeline-item">
            <strong>{event_icon} {event['timestamp']}</strong><br/>
            <span style="color: #718096;">{event['agent']}</span>: {event['description']}
        </div>
        """, unsafe_allow_html=True)

def display_negotiation_flow(state: Dict[str, Any]):
    """Display negotiation and conflict resolution process."""
    conflicts = state.get("conflicts", [])

    if not conflicts:
        return

    st.markdown("### 🔄 Negotiation & Conflict Resolution")

    for i, conflict in enumerate(conflicts, 1):
        st.markdown(f"**Conflict {i}: {conflict.conflict_type.value.upper()}**")

        st.markdown(f"""
        <div class="critique">
            <strong>Affected Agents:</strong> {', '.join(conflict.affected_agents)}<br/>
            <strong>Issue:</strong> {conflict.description}
        </div>
        """, unsafe_allow_html=True)

        if conflict.options:
            st.markdown("**Resolution Options:**")
            for j, option in enumerate(conflict.options, 1):
                st.markdown(f"{j}. {option.get('description', 'N/A')}")

def display_plan_visualization(plan_options: List[PlanOption]):
    """Display academic plans in a visual format."""
    if not plan_options:
        return

    st.markdown("### 📅 Generated Academic Plans")

    for i, plan in enumerate(plan_options, 1):
        with st.expander(f"📋 Plan Option {i} - {len(plan.semesters)} Semesters", expanded=(i == 1)):

            # Plan metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Courses", len(plan.courses))
            with col2:
                st.metric("Semesters", len(plan.semesters))
            with col3:
                st.markdown(f"**Confidence:** {get_confidence_badge(plan.confidence)}", unsafe_allow_html=True)

            # Justification
            if plan.justification:
                st.markdown("**Rationale:**")
                st.info(plan.justification)

            # Semester breakdown
            st.markdown("**Semester-by-Semester Plan:**")

            for j, semester in enumerate(plan.semesters, 1):
                term = semester.get("term", f"Semester {j}")
                courses = semester.get("courses", [])
                units = semester.get("total_units", 0)

                # Determine unit color
                unit_color = "🟢" if units <= 48 else "🟡" if units <= 54 else "🔴"

                st.markdown(f"""
                <div class="semester-card">
                    <strong>{term}</strong> {unit_color} <span style="color: #718096;">({units} units)</span><br/>
                    <span style="font-size: 0.9rem;">{', '.join(courses)}</span>
                </div>
                """, unsafe_allow_html=True)

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    st.title("🎓 CMU-Q Academic Advising System")
    st.caption("Multi-Agent Collaboration Demo for ACL 2026")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ System Control")

        # Student profile editor
        with st.expander("👤 Student Profile", expanded=False):
            st.session_state.student_profile['major'] = [st.selectbox(
                "Major",
                ["Computer Science", "Information Systems", "Business Administration", "Biology"],
                index=["Computer Science", "Information Systems", "Business Administration", "Biology"].index(
                    st.session_state.student_profile['major'][0]
                )
            )]

            st.session_state.student_profile['current_semester'] = st.selectbox(
                "Current Semester",
                ["First-Year Fall", "First-Year Spring", "Second-Year Fall", "Second-Year Spring",
                 "Third-Year Fall", "Third-Year Spring", "Fourth-Year Fall", "Fourth-Year Spring"],
                index=2
            )

            st.session_state.student_profile['gpa'] = st.slider(
                "GPA", 0.0, 4.0, 3.5, 0.1
            )

        # Research panel toggle
        st.session_state.show_research_panel = st.checkbox(
            "Show Research Analysis",
            value=st.session_state.show_research_panel
        )

        # Example queries
        st.markdown("---")
        st.subheader("💡 Example Queries")

        example_queries = {
            "Requirements": "What are the CS major requirements?",
            "Planning": "Help me plan my courses until graduation",
            "Minor": "Can I add a Business minor?",
            "Early Grad": "Can I graduate in 3.5 years?",
            "Schedule": "What courses should I take next semester?",
            "Policy": "What is the policy on course overload?"
        }

        for category, query in example_queries.items():
            if st.button(f"📌 {category}", key=f"example_{category}"):
                st.session_state['example_query'] = query

        # Clear conversation
        st.markdown("---")
        if st.button("🗑️ Clear Conversation"):
            st.session_state.conversation_history = []
            st.session_state.workflow_log = []
            st.session_state.blackboard_states = []
            st.session_state.current_state = None
            st.rerun()

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 Chat Interface",
        "🔬 Research View",
        "📊 System Analytics",
        "📚 Documentation"
    ])

    # TAB 1: Chat Interface
    with tab1:
        render_chat_interface()

    # TAB 2: Research View
    with tab2:
        render_research_view()

    # TAB 3: Analytics
    with tab3:
        render_analytics()

    # TAB 4: Documentation
    with tab4:
        render_documentation()

def render_chat_interface():
    """Render the main chat interface."""

    # Display conversation history
    for msg in st.session_state.conversation_history:
        if msg['role'] == 'user':
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg['content'])
        else:
            with st.chat_message("assistant", avatar="🎓"):
                st.markdown(msg['content'])

    # Chat input
    if 'example_query' in st.session_state:
        user_input = st.session_state.pop('example_query')
    else:
        user_input = st.chat_input("Ask me anything about your academic plan...")

    if user_input:
        # Add user message
        st.session_state.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Process with multi-agent system
        with st.chat_message("assistant", avatar="🎓"):
            with st.spinner("🤔 Analyzing your query..."):
                response, final_state = process_query(user_input)

            st.markdown(response)

            # Store state
            st.session_state.current_state = final_state
            st.session_state.blackboard_states.append(final_state)

        # Add assistant response
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()

def process_query(user_query: str) -> tuple[str, Dict]:
    """Process query through multi-agent system with visual feedback."""

    # Create placeholder for live updates
    status_placeholder = st.empty()
    agents_placeholder = st.empty()
    blackboard_placeholder = st.empty()

    # Log start
    log_workflow_event("coordinator", "Coordinator", "Analyzing query intent")

    # Prepare messages
    conversation_messages = [
        HumanMessage(content=msg['content']) if msg['role'] == 'user'
        else AIMessage(content=msg['content'])
        for msg in st.session_state.conversation_history
    ]

    # Initial state
    initial_state = {
        "user_query": user_query,
        "student_profile": st.session_state.student_profile,
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "plan_options": [],
        "conflicts": [],
        "open_questions": [],
        "messages": conversation_messages,
        "active_agents": [],
        "workflow_step": WorkflowStep.INITIAL,
        "iteration_count": 0,
        "next_agent": None,
        "user_goal": None
    }

    # Step 1: Intent classification
    with status_placeholder.container():
        st.info("🎯 **Step 1:** Coordinator classifying intent...")

    time.sleep(0.5)

    # Step 2: Execute workflow
    result = app.invoke(initial_state)

    # Display activated agents
    active_agents = result.get("active_agents", [])

    with agents_placeholder.container():
        st.success(f"🤖 **Agents Activated:** {len(active_agents)}")

        cols = st.columns(len(active_agents) if active_agents else 1)
        for i, agent_name in enumerate(active_agents):
            with cols[i]:
                output = result.get("agent_outputs", {}).get(agent_name)
                display_agent_card(agent_name, "completed", output)

    # Display blackboard
    with blackboard_placeholder.container():
        display_blackboard_state(result)

    # Log completion
    log_workflow_event("synthesis", "Coordinator", "Synthesized final answer")

    # Extract final answer
    final_answer = result["messages"][-1].content if result.get("messages") else "I'm sorry, I couldn't process that."

    # Display plan if generated
    plan_options = result.get("plan_options", [])
    if plan_options:
        display_plan_visualization(plan_options)

    # Display conflicts/negotiation if any
    if result.get("conflicts"):
        display_negotiation_flow(result)

    return final_answer, result

def render_research_view():
    """Render the research analysis view."""

    st.markdown("## 🔬 Research Analysis - Multi-Agent Collaboration")

    if not st.session_state.current_state:
        st.info("👈 Ask a question in the Chat tab to see the multi-agent workflow!")
        return

    state = st.session_state.current_state

    # Research contribution highlights
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🎯 Dynamic Workflow")
        st.markdown("""
        **Research Contribution:** LLM-driven coordinator dynamically determines
        which agents to activate based on query analysis.
        """)

        st.markdown("**Activated Agents:**")
        for agent in state.get("active_agents", []):
            st.markdown(f"- ✅ {agent.replace('_', ' ').title()}")

        st.markdown("**Execution Order:**")
        for i, agent in enumerate(state.get("active_agents", []), 1):
            st.markdown(f"{i}. {agent.replace('_', ' ').title()}")

    with col2:
        st.markdown("### 🔄 Agent Collaboration")
        st.markdown("""
        **Research Contribution:** Agents communicate through structured blackboard,
        enabling automatic conflict detection and negotiation.
        """)

        agent_outputs = state.get("agent_outputs", {})
        if agent_outputs:
            st.markdown("**Agent Contributions:**")
            for agent_name, output in agent_outputs.items():
                st.markdown(f"""
                - **{agent_name.replace('_', ' ').title()}**
                  - Confidence: {output.confidence:.2%}
                  - Risks: {len(output.risks)}
                  - Constraints: {len(output.constraints)}
                """)

    # Blackboard evolution
    st.markdown("### 📋 Blackboard State Evolution")

    if len(st.session_state.blackboard_states) > 1:
        state_index = st.slider(
            "View state at different stages",
            0,
            len(st.session_state.blackboard_states) - 1,
            len(st.session_state.blackboard_states) - 1
        )
        selected_state = st.session_state.blackboard_states[state_index]
        display_blackboard_state(selected_state)
    else:
        display_blackboard_state(state)

    # Workflow timeline
    display_workflow_timeline()

    # Negotiation analysis
    if state.get("conflicts"):
        st.markdown("### 🤝 Negotiation Protocol")
        st.markdown("""
        **Research Contribution:** Proposal + Critique mechanism where agents
        negotiate to resolve conflicts.
        """)
        display_negotiation_flow(state)

def render_analytics():
    """Render system analytics."""

    st.markdown("## 📊 System Analytics")

    if not st.session_state.workflow_log:
        st.info("No analytics available yet. Start chatting to see system performance!")
        return

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Queries", len([e for e in st.session_state.workflow_log if e['type'] == 'coordinator']))

    with col2:
        st.metric("Agent Activations", len([e for e in st.session_state.workflow_log if e['type'] == 'agent_complete']))

    with col3:
        st.metric("Negotiations", len([e for e in st.session_state.workflow_log if e['type'] == 'negotiation']))

    with col4:
        avg_confidence = 0.85  # Placeholder
        st.metric("Avg Confidence", f"{avg_confidence:.0%}")

    # Agent usage breakdown
    st.markdown("### 🤖 Agent Usage")

    agent_counts = {}
    for event in st.session_state.workflow_log:
        if event['type'] == 'agent_complete':
            agent = event['agent']
            agent_counts[agent] = agent_counts.get(agent, 0) + 1

    if agent_counts:
        import pandas as pd
        df = pd.DataFrame([
            {"Agent": k.replace('_', ' ').title(), "Activations": v}
            for k, v in agent_counts.items()
        ])
        st.bar_chart(df.set_index("Agent"))

    # Recent workflow log
    st.markdown("### 📜 Recent Activity Log")

    for event in reversed(st.session_state.workflow_log[-20:]):
        event_type_icon = {
            "coordinator": "🎯",
            "agent_start": "▶️",
            "agent_complete": "✅",
            "negotiation": "🔄",
            "conflict": "⚠️",
            "synthesis": "🎨"
        }.get(event['type'], "•")

        st.markdown(f"""
        `{event['timestamp']}` {event_type_icon} **{event['agent']}**: {event['description']}
        """)

def render_documentation():
    """Render documentation tab."""

    st.markdown("## 📚 System Documentation")

    st.markdown("""
    ### 🎯 About This System

    This is a **multi-agent academic advising system** designed for CMU-Qatar undergraduates.
    The system demonstrates advanced multi-agent collaboration techniques for the ACL 2026 demo track.

    ### 🤖 Agents

    #### 1. **Programs & Requirements Agent** 📚
    - Validates major/minor requirements
    - Checks degree progress
    - Proposes course plans

    #### 2. **Course & Scheduling Agent** 📅
    - Provides course information
    - Checks prerequisites
    - Identifies time conflicts

    #### 3. **Policy & Compliance Agent** ⚖️
    - Ensures policy compliance
    - Validates unit limits
    - Checks registration rules

    #### 4. **Academic Planning Agent** 🗓️ (NEW!)
    - Generates semester-by-semester plans
    - Balances workload
    - Integrates minors
    - Adapts to constraints

    ### 🎯 Coordinator

    The **LLM-driven coordinator**:
    - Analyzes user queries
    - Dynamically determines which agents to activate
    - Manages agent execution order
    - Detects conflicts between agent outputs
    - Triggers negotiation when needed
    - Synthesizes final answers

    ### 🔄 Negotiation Protocol

    When conflicts are detected:
    1. **Proposal**: Agent A proposes a plan
    2. **Critique**: Agent B identifies issues
    3. **Revision**: Agent A revises based on feedback
    4. **Approval**: Agent B approves or continues negotiation

    ### 📋 Blackboard Pattern

    Agents communicate through a **structured blackboard**:
    - No direct agent-to-agent communication
    - All interactions via shared state
    - Typed schema ensures interpretability
    - Enables automatic conflict detection

    ### 🔬 Research Contributions (ACL 2026)

    1. **Dynamic Multi-Agent Collaboration**: LLM-based orchestration
    2. **Negotiation Protocol**: Proposal + Critique mechanism
    3. **Emergent Behavior**: No hardcoded rules, LLM reasoning
    4. **Structured Communication**: Typed blackboard schema
    5. **Interactive Conflict Resolution**: User involvement in trade-offs

    ### 📖 Documentation Files

    - `PLANNING_GUIDE.md` - Complete planning agent guide
    - `PLANNING_IMPLEMENTATION_SUMMARY.md` - Quick reference
    - `INTEGRATION_VERIFIED.md` - Integration checklist
    - `README.md` - Main system documentation
    """)

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == "__main__":
    main()
