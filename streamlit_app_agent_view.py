"""
Multi-Agent System Visualization Interface
NOT a chatbot - shows all agents on screen with dynamic collaboration

For ACL 2026 Demo - Research Track
"""

import streamlit as st
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import time
import urllib3
from enum import Enum
import html

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from multi_agent import app
from blackboard.schema import WorkflowStep, AgentOutput
from langchain_core.messages import HumanMessage, AIMessage

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Multi-Agent Academic Advising System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AGENT STATE ENUM
# ============================================================================

class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    ACTIVE = "active"
    COMPLETE = "complete"
    ERROR = "error"

# ============================================================================
# CSS STYLING
# ============================================================================

st.markdown("""
<style>
    /* Main container */
    .main-container {
        background: #0e1117;
        padding: 1rem;
    }

    /* Agent card - idle state */
    .agent-card {
        background: linear-gradient(135deg, #1e2530 0%, #2d3748 100%);
        border: 2px solid #4a5568;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 0.5rem;
        transition: all 0.3s ease;
        min-height: 200px;
        position: relative;
    }

    /* Agent card - active state */
    .agent-card.active {
        background: linear-gradient(135deg, #2c5282 0%, #3182ce 100%);
        border-color: #63b3ed;
        box-shadow: 0 0 20px rgba(99, 179, 237, 0.5);
        animation: pulse 2s infinite;
    }

    /* Agent card - thinking state */
    .agent-card.thinking {
        background: linear-gradient(135deg, #744210 0%, #ed8936 100%);
        border-color: #f6ad55;
        animation: pulse 1.5s infinite;
    }

    /* Agent card - complete state */
    .agent-card.complete {
        background: linear-gradient(135deg, #22543d 0%, #38a169 100%);
        border-color: #68d391;
        box-shadow: 0 0 15px rgba(104, 211, 145, 0.3);
    }

    /* Coordinator card - special styling */
    .coordinator-card {
        background: linear-gradient(135deg, #44337a 0%, #6b46c1 100%);
        border: 3px solid #9f7aea;
        border-radius: 15px;
        padding: 2rem;
        margin: 1rem;
        min-height: 220px;
        position: relative;
    }

    .coordinator-card.active {
        box-shadow: 0 0 30px rgba(159, 122, 234, 0.7);
        animation: pulse 2s infinite;
    }

    /* Pulse animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }

    /* Agent header */
    .agent-header {
        font-size: 1.2rem;
        font-weight: bold;
        color: #e2e8f0;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Agent status badge */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        text-transform: uppercase;
    }

    .status-badge.idle {
        background: #4a5568;
        color: #cbd5e0;
    }

    .status-badge.thinking {
        background: #ed8936;
        color: white;
        animation: blink 1s infinite;
    }

    .status-badge.active {
        background: #3182ce;
        color: white;
    }

    .status-badge.complete {
        background: #38a169;
        color: white;
    }

    @keyframes blink {
        0%, 50%, 100% { opacity: 1; }
        25%, 75% { opacity: 0.5; }
    }

    /* Message box inside agent */
    .agent-message {
        background: rgba(0, 0, 0, 0.3);
        border-left: 4px solid #63b3ed;
        padding: 1rem;
        margin-top: 1rem;
        border-radius: 4px;
        color: #e2e8f0;
        font-size: 0.9rem;
        max-height: 150px;
        overflow-y: auto;
    }

    /* Communication arrow */
    .comm-arrow {
        position: absolute;
        width: 0;
        height: 0;
        border-left: 10px solid transparent;
        border-right: 10px solid transparent;
        border-top: 15px solid #63b3ed;
        animation: float 2s infinite;
    }

    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    /* Blackboard state panel */
    .blackboard-panel {
        background: #1a202c;
        border: 2px solid #4a5568;
        border-radius: 8px;
        padding: 1rem;
        max-height: 600px;
        overflow-y: auto;
    }

    /* Timeline event */
    .timeline-event {
        background: rgba(74, 85, 104, 0.3);
        border-left: 3px solid #63b3ed;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 4px 4px 0;
        color: #e2e8f0;
        font-size: 0.85rem;
    }

    .timeline-event.coordinator {
        border-left-color: #9f7aea;
    }

    .timeline-event.agent {
        border-left-color: #63b3ed;
    }

    .timeline-event.negotiation {
        border-left-color: #ed8936;
    }

    /* Query input area */
    .query-container {
        background: #2d3748;
        border: 2px solid #4a5568;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    /* Final answer box */
    .final-answer {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d5a8c 100%);
        border: 2px solid #4299e1;
        border-radius: 10px;
        padding: 2rem;
        margin: 1rem 0;
        color: #e2e8f0;
    }

    /* Confidence meter */
    .confidence-meter {
        width: 100%;
        height: 8px;
        background: #4a5568;
        border-radius: 4px;
        margin-top: 0.5rem;
        overflow: hidden;
    }

    .confidence-fill {
        height: 100%;
        background: linear-gradient(90deg, #48bb78 0%, #38a169 100%);
        transition: width 0.5s ease;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'agent_states' not in st.session_state:
    st.session_state.agent_states = {
        'coordinator': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
        'programs_requirements': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
        'course_scheduling': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
        'policy_compliance': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
        'academic_planning': {'state': AgentState.IDLE, 'message': '', 'confidence': 0},
    }

if 'timeline' not in st.session_state:
    st.session_state.timeline = []

if 'blackboard_state' not in st.session_state:
    st.session_state.blackboard_state = {}

if 'final_answer' not in st.session_state:
    st.session_state.final_answer = None

if 'processing' not in st.session_state:
    st.session_state.processing = False

if 'processing_stage' not in st.session_state:
    st.session_state.processing_stage = 'idle'  # idle, coordinator_thinking, executing, updating_agents, complete

if 'workflow_result' not in st.session_state:
    st.session_state.workflow_result = None

if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'student_profile' not in st.session_state:
    st.session_state.student_profile = {
        "major": None,
        "current_semester": None,
        "completed_courses": [],
        "gpa": None
    }

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_student_profile_summary() -> str:
    """Get human-readable summary of student profile."""
    profile = st.session_state.student_profile
    parts = []

    if profile.get('major'):
        parts.append(f"Major: {profile['major'][0] if isinstance(profile['major'], list) else profile['major']}")
    if profile.get('current_semester'):
        parts.append(f"Semester: {profile['current_semester']}")
    if profile.get('gpa'):
        parts.append(f"GPA: {profile['gpa']}")

    return " | ".join(parts) if parts else "Not set"

def inject_profile_into_query(query: str, profile: dict) -> str:
    """Enhance query with profile information."""
    context_parts = []

    if profile.get('major'):
        major = profile['major'][0] if isinstance(profile['major'], list) else profile['major']
        context_parts.append(f"I'm a {major} major")

    if profile.get('current_semester'):
        context_parts.append(f"currently in {profile['current_semester']}")

    if profile.get('gpa'):
        context_parts.append(f"with a {profile['gpa']} GPA")

    if context_parts:
        context = ". ".join(context_parts) + ". "
        return context + query

    return query

def update_agent_state(agent_name: str, state: AgentState, message: str = "", confidence: float = 0):
    """Update agent state and add timeline event."""
    st.session_state.agent_states[agent_name] = {
        'state': state,
        'message': message,
        'confidence': confidence
    }

    # Add timeline event
    event_type = 'coordinator' if agent_name == 'coordinator' else 'agent'
    st.session_state.timeline.append({
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'type': event_type,
        'agent': agent_name,
        'event': f"{agent_name.replace('_', ' ').title()}: {state.value}",
        'message': message
    })

def reset_system():
    """Reset all agents to idle state."""
    st.session_state.agent_states = {
        agent: {'state': AgentState.IDLE, 'message': '', 'confidence': 0}
        for agent in st.session_state.agent_states.keys()
    }
    st.session_state.timeline = []
    st.session_state.blackboard_state = {}
    st.session_state.final_answer = None
    st.session_state.processing = False
    st.session_state.processing_stage = 'idle'
    st.session_state.workflow_result = None

def render_agent_card(agent_name: str, display_name: str, icon: str, is_coordinator: bool = False):
    """Render an individual agent card with current state."""

    agent_data = st.session_state.agent_states[agent_name]
    state = agent_data['state']
    message = agent_data['message']
    confidence = agent_data['confidence']

    # DEBUG: Print state info
    if state == AgentState.COMPLETE:
        st.caption(f"🔍 DEBUG: {agent_name} - State: {state.value}, Message exists: {bool(message)}, Length: {len(str(message)) if message else 0}")

    # Determine card class
    card_class = "coordinator-card" if is_coordinator else "agent-card"
    if state != AgentState.IDLE:
        card_class += f" {state.value}"

    # Status badge
    status_html = f'<span class="status-badge {state.value}">{state.value}</span>'

    # Render card header with status
    st.markdown(f"""
    <div class="{card_class}">
        <div class="agent-header">
            <span style="font-size: 1.5rem;">{icon}</span>
            <span>{display_name}</span>
        </div>
        {status_html}
    </div>
    """, unsafe_allow_html=True)

    # Show message content OUTSIDE the HTML card (using native Streamlit)
    if state == AgentState.COMPLETE and message:
        # Create a visible container for the message
        with st.container():
            # Show confidence bar
            if confidence > 0:
                st.progress(confidence, text=f"Confidence: {confidence:.0%}")
                st.write("")  # Spacing

            # Show message content directly in a styled container (readable text, not HTML)
            st.markdown("**Agent Response:**")
            st.info(message)  # Use info box to make it clearly visible
            st.write("")  # Add spacing below

def render_timeline():
    """Render event timeline in sidebar."""
    st.markdown("### 📊 Event Timeline")

    if not st.session_state.timeline:
        st.info("No events yet. Submit a query to start.")
        return

    # Show most recent events first
    for event in reversed(st.session_state.timeline[-20:]):  # Last 20 events
        event_class = f"timeline-event {event['type']}"
        icon = {
            'coordinator': '🎯',
            'agent': '🤖',
            'negotiation': '🔄'
        }.get(event['type'], '•')

        st.markdown(f"""
        <div class="{event_class}">
            {icon} <strong>{event['timestamp']}</strong>: {event['event']}
        </div>
        """, unsafe_allow_html=True)

def render_blackboard_state():
    """Render current blackboard state."""
    st.markdown("### 🗂️ Blackboard State")

    if not st.session_state.blackboard_state:
        st.info("Blackboard empty. Waiting for agents...")
        return

    # Show key metrics
    state = st.session_state.blackboard_state

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Agents", len(state.get('active_agents', [])))
    with col2:
        st.metric("Constraints", len(state.get('constraints', [])))

    col3, col4 = st.columns(2)
    with col3:
        st.metric("Risks", len(state.get('risks', [])))
    with col4:
        st.metric("Plans", len(state.get('plan_options', [])))

    # Show workflow step
    if state.get('workflow_step'):
        st.caption(f"**Step:** {state['workflow_step']}")

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def start_query_processing(query: str):
    """Initialize query processing."""
    st.session_state.processing = True
    st.session_state.processing_stage = 'coordinator_thinking'
    st.session_state.current_query = query

    # Reset system
    st.session_state.agent_states = {
        agent: {'state': AgentState.IDLE, 'message': '', 'confidence': 0}
        for agent in st.session_state.agent_states.keys()
    }
    st.session_state.timeline = []
    st.session_state.blackboard_state = {}
    st.session_state.final_answer = None

    # Update coordinator to thinking
    update_agent_state('coordinator', AgentState.THINKING,
                      "Analyzing query and determining which agents to activate...")

def execute_workflow():
    """Execute the actual multi-agent workflow."""
    query = st.session_state.current_query
    profile = st.session_state.student_profile

    # Enhance query with profile if available
    enhanced_query = inject_profile_into_query(query, profile)

    # Build conversation messages from history
    conversation_messages = [
        HumanMessage(content=msg['content']) if msg['role'] == 'user'
        else AIMessage(content=msg['content'])
        for msg in st.session_state.conversation_history
    ]

    # Prepare state
    initial_state = {
        "user_query": enhanced_query,
        "student_profile": profile,
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

    # EXECUTE WORKFLOW
    with st.spinner("🤖 Executing workflow..."):
        result = app.invoke(initial_state)

    # Store result
    st.session_state.workflow_result = result
    st.session_state.processing_stage = 'updating_agents'

    # Update coordinator - active
    update_agent_state('coordinator', AgentState.ACTIVE,
                      f"Activated {len(result.get('active_agents', []))} agents: {', '.join(result.get('active_agents', []))}")

def update_agent_displays():
    """Update all agent displays with results."""
    result = st.session_state.workflow_result
    agent_outputs = result.get('agent_outputs', {})

    # Update each agent to active then complete
    for agent_name, output in agent_outputs.items():
        update_agent_state(agent_name, AgentState.COMPLETE,
                          output.answer, output.confidence)

    # Update coordinator - complete
    update_agent_state('coordinator', AgentState.COMPLETE,
                      "Synthesized final answer from all agent inputs")

    # Update blackboard state
    st.session_state.blackboard_state = {
        'active_agents': result.get('active_agents', []),
        'constraints': result.get('constraints', []),
        'risks': result.get('risks', []),
        'plan_options': result.get('plan_options', []),
        'conflicts': result.get('conflicts', []),
        'workflow_step': result.get('workflow_step', WorkflowStep.COMPLETE)
    }

    # Extract final answer
    final_answer = result["messages"][-1].content if result.get("messages") else "Processing complete."
    st.session_state.final_answer = final_answer

    # Save to conversation history
    st.session_state.conversation_history.append({
        "role": "user",
        "content": st.session_state.current_query
    })
    st.session_state.conversation_history.append({
        "role": "assistant",
        "content": final_answer
    })

    # Mark as complete
    st.session_state.processing = False
    st.session_state.processing_stage = 'complete'

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    st.markdown("""
    <h1 style='text-align: center; color: #e2e8f0;'>
        🤖 Multi-Agent Academic Advising System
    </h1>
    <p style='text-align: center; color: #cbd5e0; margin-bottom: 2rem;'>
        Real-Time Agent Collaboration Visualization | ACL 2026 Demo
    </p>
    """, unsafe_allow_html=True)

    # Sidebar: Student Profile
    with st.sidebar:
        st.header("👤 Student Profile")
        st.caption("Optional - enhances personalized advice")

        # Major
        major_options = ["Not set", "Computer Science", "Information Systems", "Business Administration", "Biology"]
        selected_major = st.selectbox("Major", major_options,
                                     index=0 if not st.session_state.student_profile.get('major') else
                                     major_options.index(st.session_state.student_profile['major'][0]
                                                        if isinstance(st.session_state.student_profile.get('major'), list)
                                                        else st.session_state.student_profile.get('major', 'Not set')))

        if selected_major != "Not set":
            st.session_state.student_profile['major'] = [selected_major]
        else:
            st.session_state.student_profile['major'] = None

        # Semester
        semester_options = ["Not set", "First-Year Fall", "First-Year Spring", "Second-Year Fall",
                           "Second-Year Spring", "Third-Year Fall", "Third-Year Spring",
                           "Fourth-Year Fall", "Fourth-Year Spring"]
        selected_semester = st.selectbox("Current Semester", semester_options,
                                        index=0 if not st.session_state.student_profile.get('current_semester') else
                                        semester_options.index(st.session_state.student_profile.get('current_semester', 'Not set')))

        if selected_semester != "Not set":
            st.session_state.student_profile['current_semester'] = selected_semester
        else:
            st.session_state.student_profile['current_semester'] = None

        # GPA
        set_gpa = st.checkbox("Set GPA", value=st.session_state.student_profile.get('gpa') is not None)
        if set_gpa:
            current_gpa = st.session_state.student_profile.get('gpa')
            default_value = str(current_gpa) if current_gpa is not None else ""
            gpa_input = st.text_input("GPA (0.0-4.0)", value=default_value, placeholder="e.g., 3.5")

            if gpa_input:
                try:
                    gpa = float(gpa_input)
                    if 0.0 <= gpa <= 4.0:
                        st.session_state.student_profile['gpa'] = gpa
                    else:
                        st.error("⚠️ GPA must be between 0.0 and 4.0")
                        st.session_state.student_profile['gpa'] = None
                except ValueError:
                    st.error("⚠️ Please enter a valid number")
                    st.session_state.student_profile['gpa'] = None
            else:
                st.session_state.student_profile['gpa'] = None
        else:
            st.session_state.student_profile['gpa'] = None

        # Show profile summary
        profile_summary = get_student_profile_summary()
        if profile_summary != "Not set":
            st.success(f"✅ {profile_summary}")
        else:
            st.info("ℹ️ No profile set")

        if st.button("🗑️ Clear Profile"):
            st.session_state.student_profile = {
                "major": None,
                "current_semester": None,
                "completed_courses": [],
                "gpa": None
            }
            st.rerun()

        st.markdown("---")

        # Conversation History
        st.header("💬 Conversation History")
        if st.session_state.conversation_history:
            st.caption(f"{len(st.session_state.conversation_history) // 2} exchanges")

            with st.expander("View History", expanded=False):
                for i, msg in enumerate(st.session_state.conversation_history):
                    if msg['role'] == 'user':
                        st.markdown(f"**👤 You:** {msg['content'][:100]}...")
                    else:
                        st.markdown(f"**🤖 AI:** {msg['content'][:100]}...")
                    if i < len(st.session_state.conversation_history) - 1:
                        st.markdown("---")

            if st.button("🗑️ Clear History"):
                st.session_state.conversation_history = []
                st.rerun()
        else:
            st.info("No conversation yet")

        st.markdown("---")

        # Example Queries
        st.header("💡 Examples")
        examples = [
            "What are CS requirements?",
            "Plan my graduation",
            "Can I add a minor?",
            "Next semester courses?",
        ]

        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:15]}", disabled=st.session_state.processing):
                st.session_state.current_query = ex
                start_query_processing(ex)
                st.rerun()

    # Profile indicator in main area
    profile_summary = get_student_profile_summary()
    if profile_summary != "Not set":
        st.info(f"👤 Using profile: {profile_summary}")

    # Query input
    st.markdown('<div class="query-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([5, 1])

    with col1:
        user_query = st.text_input(
            "Enter your academic advising question:",
            placeholder="e.g., What courses should I take next semester?",
            disabled=st.session_state.processing,
            label_visibility="collapsed"
        )

    with col2:
        submit_button = st.button(
            "🚀 Process",
            disabled=st.session_state.processing,
            use_container_width=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Process query based on stage
    if submit_button and user_query and not st.session_state.processing:
        start_query_processing(user_query)
        st.rerun()

    # Continue processing based on stage
    if st.session_state.processing_stage == 'coordinator_thinking':
        # Show coordinator thinking, then move to execution
        time.sleep(0.5)  # Brief visual pause
        st.session_state.processing_stage = 'executing'
        st.rerun()

    elif st.session_state.processing_stage == 'executing':
        # Execute the workflow
        execute_workflow()
        st.rerun()

    elif st.session_state.processing_stage == 'updating_agents':
        # Update agent displays
        update_agent_displays()
        st.rerun()

    # Main layout: Agents + Sidebar
    main_col, sidebar_col = st.columns([3, 1])

    with main_col:
        # Coordinator (top center)
        st.markdown("### 🎯 Coordinator")
        render_agent_card('coordinator', 'Intent Classifier & Coordinator', '🎯', is_coordinator=True)

        st.markdown("---")
        st.markdown("### 🤖 Specialized Agents")

        # Four agents in 2x2 grid
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)

        with row1_col1:
            render_agent_card('programs_requirements', 'Programs & Requirements', '📚')

        with row1_col2:
            render_agent_card('course_scheduling', 'Course Scheduling', '📅')

        with row2_col1:
            render_agent_card('policy_compliance', 'Policy Compliance', '⚖️')

        with row2_col2:
            render_agent_card('academic_planning', 'Academic Planning', '🗓️')

        # Final answer (if available)
        if st.session_state.final_answer:
            st.markdown("---")
            st.markdown(f"""
            <div class="final-answer">
                <h3 style="color: #90cdf4; margin-top: 0;">📝 Final Answer</h3>
                <div style="margin-top: 1rem;">{st.session_state.final_answer}</div>
            </div>
            """, unsafe_allow_html=True)

        # Reset button
        if not st.session_state.processing:
            if st.button("🔄 Reset System", use_container_width=False):
                reset_system()
                st.rerun()

    with sidebar_col:
        st.markdown('<div class="blackboard-panel">', unsafe_allow_html=True)

        # Timeline
        render_timeline()

        st.markdown("---")

        # Blackboard state
        render_blackboard_state()

        st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
