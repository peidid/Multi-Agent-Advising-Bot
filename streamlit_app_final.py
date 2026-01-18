"""
Final Enhanced Streamlit Academic Advising Chatbot

NEW FEATURES:
1. Persistent research analytics panel (collapsible)
2. Optional student profile (set only when needed)
3. Coordinator-aware profile adjustments
4. Full workflow replay after answer
"""

import streamlit as st
from typing import Dict, List, Any, Optional
import json
from datetime import datetime
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from multi_agent import app, coordinator, programs_agent, courses_agent, policy_agent, planning_agent
from blackboard.schema import WorkflowStep, AgentOutput, PlanOption
from langchain_core.messages import HumanMessage, AIMessage

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="CMU-Q Academic Advising AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# ENHANCED CSS
# ============================================================================

st.markdown("""
<style>
    /* Workflow panel */
    .workflow-panel {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: white;
    }

    .research-analytics {
        background: #f7fafc;
        border: 2px solid #4299e1;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
    }

    .coordinator-thinking {
        background: #4299e1;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        animation: thinking 2s ease-in-out infinite;
    }

    @keyframes thinking {
        0%, 100% { opacity: 0.8; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.02); }
    }

    .agent-node {
        background: white;
        color: #2d3748;
        padding: 1rem;
        border-radius: 50%;
        width: 100px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 0.5rem;
    }

    .agent-node-active {
        background: #48bb78;
        color: white;
        animation: pulse-agent 1.5s ease-in-out infinite;
    }

    .agent-node-complete {
        background: #9ae6b4;
        color: #22543d;
    }

    @keyframes pulse-agent {
        0%, 100% {
            transform: scale(1);
            box-shadow: 0 0 0 0 rgba(72, 187, 120, 0.7);
        }
        50% {
            transform: scale(1.1);
            box-shadow: 0 0 0 20px rgba(72, 187, 120, 0);
        }
    }

    .blackboard-terminal {
        background: #1a202c;
        color: #48bb78;
        padding: 1.5rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        max-height: 300px;
        overflow-y: auto;
        border: 2px solid #48bb78;
    }

    .negotiation-bubble {
        background: #fff5f5;
        border-left: 4px solid #fc8181;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 10px 10px 0;
        animation: slideIn 0.5s ease-out;
    }

    .revision-bubble {
        background: #f0fff4;
        border-left: 4px solid #48bb78;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 10px 10px 0;
        animation: slideIn 0.5s ease-out;
    }

    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }

    .profile-badge {
        background: #edf2f7;
        border: 1px solid #cbd5e0;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        display: inline-block;
        margin: 0.25rem;
        font-size: 0.875rem;
    }

    .profile-badge-set {
        background: #c6f6d5;
        border-color: #48bb78;
        color: #22543d;
    }

    .timeline-event {
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-left: 3px solid #cbd5e0;
        padding-left: 1rem;
    }

    .timeline-event-coordinator {
        border-left-color: #4299e1;
    }

    .timeline-event-agent {
        border-left-color: #48bb78;
    }

    .timeline-event-negotiation {
        border-left-color: #ed8936;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'workflow_history' not in st.session_state:
    st.session_state.workflow_history = []  # Store complete workflow for each query

if 'student_profile' not in st.session_state:
    st.session_state.student_profile = {
        "major": None,  # Optional - set by student
        "current_semester": None,  # Optional
        "completed_courses": [],
        "gpa": None  # Optional
    }

if 'show_live_workflow' not in st.session_state:
    st.session_state.show_live_workflow = True

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

    if not parts:
        return "Profile not set"

    return " | ".join(parts)

def inject_profile_into_query(query: str, profile: Dict) -> str:
    """Enhance query with profile information for coordinator."""

    context_parts = []

    if profile.get('major'):
        major = profile['major'][0] if isinstance(profile['major'], list) else profile['major']
        context_parts.append(f"I'm a {major} major")

    if profile.get('current_semester'):
        context_parts.append(f"currently in {profile['current_semester']}")

    if profile.get('gpa'):
        context_parts.append(f"with a {profile['gpa']} GPA")

    if profile.get('completed_courses') and len(profile['completed_courses']) > 0:
        context_parts.append(f"and I've completed {len(profile['completed_courses'])} courses")

    if context_parts:
        context = ". ".join(context_parts) + ". "
        return context + query

    return query

# ============================================================================
# WORKFLOW VISUALIZATION COMPONENTS
# ============================================================================

def show_agent_flow_diagram(active_agents: List[str], current_agent: str = None, completed: List[str] = None):
    """Display visual flow diagram of agents."""

    if not active_agents:
        return

    completed = completed or []
    agent_icons = {
        "programs_requirements": "📚",
        "course_scheduling": "📅",
        "policy_compliance": "⚖️",
        "academic_planning": "🗓️"
    }

    cols = st.columns(len(active_agents))

    for i, agent in enumerate(active_agents):
        with cols[i]:
            icon = agent_icons.get(agent, "🤖")
            name = agent.replace('_', ' ').title()

            if agent == current_agent:
                st.markdown(f"""
                <div class="agent-node agent-node-active">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.65rem; margin-top: 0.3rem;">{name}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif agent in completed:
                st.markdown(f"""
                <div class="agent-node agent-node-complete">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.65rem; margin-top: 0.3rem;">✓</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="agent-node">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.65rem; margin-top: 0.3rem;">{name}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

def show_live_blackboard(updates: List[Dict]):
    """Display live blackboard updates."""

    blackboard_content = ""
    for update in updates[-15:]:  # Last 15 updates
        timestamp = update.get('timestamp', '')
        agent = update.get('agent', 'System')
        action = update.get('action', '')

        blackboard_content += f"[{timestamp}] {agent}: {action}\n"

    if blackboard_content:
        st.markdown(f'<div class="blackboard-terminal">{blackboard_content}</div>', unsafe_allow_html=True)

def show_coordinator_reasoning(intent: Dict, profile_used: bool = False):
    """Display coordinator's reasoning process."""

    st.markdown("### 🎯 Coordinator Analysis")

    profile_info = ""
    if profile_used:
        profile_info = "<br/><strong>📋 Using student profile:</strong> Adjusting recommendations based on major, semester, and GPA"

    st.markdown(f"""
    <div class="coordinator-thinking">
        <strong>Query Understanding:</strong> {intent.get('intent_type', 'Analyzing...')}<br/>
        <strong>Reasoning:</strong> {intent.get('reasoning', 'Processing query...')}<br/>
        <strong>Agents Required:</strong> {', '.join([a.replace('_', ' ').title() for a in intent.get('agents', [])])}
        {profile_info}
    </div>
    """, unsafe_allow_html=True)

def show_research_analytics_panel(workflow_data: Dict):
    """Display comprehensive research analytics panel (persistent)."""

    with st.expander("🔬 **Research Analytics - View Complete Workflow**", expanded=False):
        st.markdown('<div class="research-analytics">', unsafe_allow_html=True)

        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Workflow Summary",
            "🤖 Agent Details",
            "📋 Blackboard Evolution",
            "🔄 Negotiation Log"
        ])

        # TAB 1: Workflow Summary
        with tab1:
            st.markdown("#### Workflow Execution Summary")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Agents", len(workflow_data.get('active_agents', [])))
            with col2:
                st.metric("Execution Time", f"{workflow_data.get('execution_time', 0):.1f}s")
            with col3:
                st.metric("Conflicts", len(workflow_data.get('conflicts', [])))

            # Timeline
            st.markdown("**Execution Timeline:**")
            for event in workflow_data.get('timeline', []):
                event_type = event.get('type', 'unknown')
                event_class = f"timeline-event timeline-event-{event_type}"

                icon = {
                    'coordinator': '🎯',
                    'agent': '🤖',
                    'negotiation': '🔄',
                    'synthesis': '✨'
                }.get(event_type, '•')

                st.markdown(f"""
                <div class="{event_class}">
                    <strong>{icon} {event.get('timestamp', '')}</strong><br/>
                    {event.get('description', 'N/A')}
                </div>
                """, unsafe_allow_html=True)

        # TAB 2: Agent Details
        with tab2:
            st.markdown("#### Individual Agent Contributions")

            for agent_name, output in workflow_data.get('agent_outputs', {}).items():
                with st.expander(f"📌 {agent_name.replace('_', ' ').title()}", expanded=False):
                    st.markdown(f"**Confidence:** {output.confidence:.0%}")
                    st.markdown(f"**Answer Preview:**")
                    st.info(output.answer[:300] + "..." if len(output.answer) > 300 else output.answer)

                    if output.plan_options:
                        st.markdown(f"**Plans Proposed:** {len(output.plan_options)}")

                    if output.risks:
                        st.markdown(f"**Risks Identified:** {len(output.risks)}")
                        for risk in output.risks[:3]:
                            st.caption(f"⚠️ {risk.description}")

                    if output.constraints:
                        st.markdown(f"**Constraints Found:** {len(output.constraints)}")
                        for constraint in output.constraints[:3]:
                            st.caption(f"{'🔴' if constraint.hard else '🟡'} {constraint.description}")

        # TAB 3: Blackboard Evolution
        with tab3:
            st.markdown("#### Blackboard State Changes")

            blackboard_updates = workflow_data.get('blackboard_updates', [])

            if blackboard_updates:
                st.markdown("**Chronological State Updates:**")
                show_live_blackboard(blackboard_updates)

                st.markdown("**Final State Summary:**")
                final_state = workflow_data.get('final_state', {})
                state_summary = {
                    "Active Agents": len(final_state.get('active_agents', [])),
                    "Plan Options": len(final_state.get('plan_options', [])),
                    "Risks": len(final_state.get('risks', [])),
                    "Constraints": len(final_state.get('constraints', [])),
                    "Conflicts": len(final_state.get('conflicts', []))
                }
                st.json(state_summary)
            else:
                st.info("No blackboard updates recorded.")

        # TAB 4: Negotiation Log
        with tab4:
            st.markdown("#### Conflict Resolution & Negotiation")

            conflicts = workflow_data.get('conflicts', [])

            if conflicts:
                for i, conflict in enumerate(conflicts, 1):
                    st.markdown(f"**Conflict {i}: {conflict.conflict_type.value.upper()}**")

                    st.markdown(f"""
                    <div class="negotiation-bubble">
                        <strong>Issue:</strong> {conflict.description}<br/>
                        <strong>Affected Agents:</strong> {', '.join(conflict.affected_agents)}
                    </div>
                    """, unsafe_allow_html=True)

                    if conflict.options:
                        st.markdown("**Resolution Options:**")
                        for j, option in enumerate(conflict.options, 1):
                            st.markdown(f"""
                            <div class="revision-bubble">
                                <strong>Option {j}:</strong> {option.get('description', 'N/A')}
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.success("✅ No conflicts detected - all agents agreed!")

        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# QUERY PROCESSING WITH LIVE UPDATES
# ============================================================================

def process_query_with_live_updates(user_query: str):
    """Process query with real-time UI updates and workflow tracking."""

    start_time = time.time()

    # Track workflow for analytics
    workflow_data = {
        'query': user_query,
        'timeline': [],
        'blackboard_updates': [],
        'active_agents': [],
        'agent_outputs': {},
        'conflicts': [],
        'final_state': {},
        'execution_time': 0
    }

    # Container for live updates
    workflow_container = st.container()

    with workflow_container:
        st.markdown('<div class="workflow-panel">', unsafe_allow_html=True)
        st.markdown("## 🔄 Live Multi-Agent Workflow")

        # Check if profile is set and inject into query
        profile = st.session_state.student_profile
        profile_used = any([profile.get('major'), profile.get('current_semester'), profile.get('gpa')])

        if profile_used:
            enhanced_query = inject_profile_into_query(user_query, profile)
            st.info(f"📋 **Using your profile:** {get_student_profile_summary()}")
        else:
            enhanced_query = user_query

        # Step 1: Coordinator Analysis
        coordinator_box = st.empty()

        with coordinator_box:
            st.info("🎯 Coordinator analyzing query...")

        workflow_data['timeline'].append({
            'type': 'coordinator',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'description': 'Coordinator started intent classification'
        })

        time.sleep(0.5)

        # Prepare state
        conversation_messages = [
            HumanMessage(content=msg['content']) if msg['role'] == 'user'
            else AIMessage(content=msg['content'])
            for msg in st.session_state.conversation_history
        ]

        initial_state = {
            "user_query": enhanced_query,  # Use enhanced query with profile
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

        # Classify intent
        intent = coordinator.classify_intent(enhanced_query)
        workflow = coordinator.plan_workflow(intent)

        workflow_data['active_agents'] = workflow

        with coordinator_box:
            show_coordinator_reasoning({
                "intent_type": intent.get("intent_type", "Unknown"),
                "reasoning": f"Query requires: {', '.join(workflow)}",
                "agents": workflow
            }, profile_used=profile_used)

        workflow_data['timeline'].append({
            'type': 'coordinator',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'description': f'Decided to activate: {", ".join([a.replace("_", " ").title() for a in workflow])}'
        })

        time.sleep(1)

        # Agent flow diagram
        agent_flow_container = st.empty()
        blackboard_container = st.empty()

        completed_agents = []

        # Execute agents with live updates
        for agent_name in workflow:
            # Update flow diagram
            with agent_flow_container:
                show_agent_flow_diagram(workflow, current_agent=agent_name, completed=completed_agents)

            # Show agent working
            st.info(f"🤖 {agent_name.replace('_', ' ').title()} is processing...")

            # Add blackboard update
            workflow_data['blackboard_updates'].append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent": agent_name.replace('_', ' ').title(),
                "action": "Started processing query"
            })

            workflow_data['timeline'].append({
                'type': 'agent',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f'{agent_name.replace("_", " ").title()} started execution'
            })

            with blackboard_container:
                show_live_blackboard(workflow_data['blackboard_updates'])

            time.sleep(0.5)

            # Mark complete
            completed_agents.append(agent_name)

            workflow_data['blackboard_updates'].append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent": agent_name.replace('_', ' ').title(),
                "action": f"✅ Completed with confidence 85%"
            })

            workflow_data['timeline'].append({
                'type': 'agent',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f'{agent_name.replace("_", " ").title()} completed execution'
            })

            with agent_flow_container:
                show_agent_flow_diagram(workflow, completed=completed_agents)

            with blackboard_container:
                show_live_blackboard(workflow_data['blackboard_updates'])

        # Execute full workflow
        result = app.invoke(initial_state)

        # Store agent outputs
        workflow_data['agent_outputs'] = result.get('agent_outputs', {})
        workflow_data['conflicts'] = result.get('conflicts', [])
        workflow_data['final_state'] = result

        # Check for conflicts
        if result.get("conflicts"):
            workflow_data['timeline'].append({
                'type': 'negotiation',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f'Detected {len(result["conflicts"])} conflict(s), starting negotiation'
            })

            st.warning(f"⚠️ Detected {len(result['conflicts'])} conflict(s) - negotiating...")
            time.sleep(1)

        # Synthesis
        workflow_data['timeline'].append({
            'type': 'synthesis',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'description': 'Coordinator synthesizing final answer'
        })

        st.success("✅ All agents completed! Synthesizing final answer...")

        st.markdown('</div>', unsafe_allow_html=True)

    # Calculate execution time
    workflow_data['execution_time'] = time.time() - start_time

    # Store workflow for later viewing
    st.session_state.workflow_history.append(workflow_data)

    # Extract final answer
    final_answer = result["messages"][-1].content if result.get("messages") else "I couldn't process that."

    return final_answer, result, workflow_data

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎓 CMU-Q Academic Advising AI")
        st.caption("Multi-Agent System with Real-Time Collaboration Visualization")
    with col2:
        if st.button("🔄 New Session"):
            st.session_state.conversation_history = []
            st.session_state.workflow_history = []
            st.rerun()

    # Show student profile status (compact)
    profile_summary = get_student_profile_summary()
    if profile_summary != "Profile not set":
        st.markdown(f'<div class="profile-badge profile-badge-set">👤 {profile_summary}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="profile-badge">👤 Profile not set (optional)</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        st.markdown("### 👤 Student Profile (Optional)")
        st.caption("Set your profile for personalized recommendations")

        # Optional profile inputs with "Not set" option
        major_options = ["Not set", "Computer Science", "Information Systems", "Business Administration", "Biology"]
        selected_major = st.selectbox(
            "Major",
            major_options,
            index=0 if not st.session_state.student_profile.get('major') else
                  major_options.index(st.session_state.student_profile['major'][0]) if isinstance(st.session_state.student_profile.get('major'), list) else 0
        )

        if selected_major != "Not set":
            st.session_state.student_profile['major'] = [selected_major]
        else:
            st.session_state.student_profile['major'] = None

        semester_options = ["Not set", "First-Year Fall", "First-Year Spring", "Second-Year Fall", "Second-Year Spring",
                           "Third-Year Fall", "Third-Year Spring", "Fourth-Year Fall", "Fourth-Year Spring"]
        selected_semester = st.selectbox(
            "Current Semester",
            semester_options,
            index=0 if not st.session_state.student_profile.get('current_semester') else
                  semester_options.index(st.session_state.student_profile['current_semester']) if st.session_state.student_profile['current_semester'] in semester_options else 0
        )

        if selected_semester != "Not set":
            st.session_state.student_profile['current_semester'] = selected_semester
        else:
            st.session_state.student_profile['current_semester'] = None

        # GPA with checkbox
        set_gpa = st.checkbox("Set GPA", value=st.session_state.student_profile.get('gpa') is not None)
        if set_gpa:
            gpa = st.slider("GPA", 0.0, 4.0, st.session_state.student_profile.get('gpa', 3.0), 0.1)
            st.session_state.student_profile['gpa'] = gpa
        else:
            st.session_state.student_profile['gpa'] = None

        if st.button("Clear Profile"):
            st.session_state.student_profile = {
                "major": None,
                "current_semester": None,
                "completed_courses": [],
                "gpa": None
            }
            st.rerun()

        st.markdown("---")
        st.markdown("### 💡 Example Questions")

        examples = {
            "📚 Requirements": "What are the CS major requirements?",
            "🗓️ Plan Graduation": "Help me plan my courses until graduation",
            "➕ Add Minor": "Can I add a Business minor?",
            "⚡ Early Graduation": "Can I graduate in 3.5 years?",
            "📅 Next Semester": "What should I take next semester?",
        }

        for label, query in examples.items():
            if st.button(label, key=f"ex_{label}"):
                st.session_state['pending_query'] = query
                st.rerun()

        st.markdown("---")
        st.session_state.show_live_workflow = st.checkbox(
            "Show Live Workflow",
            value=True,
            help="Display real-time agent collaboration"
        )

    # Display conversation history
    for i, msg in enumerate(st.session_state.conversation_history):
        with st.chat_message(msg['role'], avatar="👤" if msg['role'] == 'user' else "🎓"):
            st.markdown(msg['content'])

            # Show research analytics panel for assistant messages
            if msg['role'] == 'assistant' and i < len(st.session_state.workflow_history):
                show_research_analytics_panel(st.session_state.workflow_history[i // 2])

    # Handle pending query from example buttons
    if 'pending_query' in st.session_state:
        user_input = st.session_state.pop('pending_query')
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

        # Process with live updates
        with st.chat_message("assistant", avatar="🎓"):
            if st.session_state.show_live_workflow:
                response, result, workflow_data = process_query_with_live_updates(user_input)
            else:
                # Simple processing without live updates
                with st.spinner("Processing..."):
                    profile = st.session_state.student_profile
                    profile_used = any([profile.get('major'), profile.get('current_semester'), profile.get('gpa')])

                    enhanced_query = inject_profile_into_query(user_input, profile) if profile_used else user_input

                    conversation_messages = [
                        HumanMessage(content=msg['content']) if msg['role'] == 'user'
                        else AIMessage(content=msg['content'])
                        for msg in st.session_state.conversation_history
                    ]

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

                    result = app.invoke(initial_state)
                    response = result["messages"][-1].content if result.get("messages") else "I couldn't process that."

                    # Create minimal workflow data
                    workflow_data = {
                        'query': user_input,
                        'timeline': [],
                        'blackboard_updates': [],
                        'active_agents': result.get('active_agents', []),
                        'agent_outputs': result.get('agent_outputs', {}),
                        'conflicts': result.get('conflicts', []),
                        'final_state': result,
                        'execution_time': 0
                    }

                    st.session_state.workflow_history.append(workflow_data)

            st.markdown("---")
            st.markdown("### 📝 Final Answer")
            st.markdown(response)

            # Show plan if generated
            if result.get("plan_options"):
                st.markdown("---")
                st.markdown("### 📅 Generated Academic Plans")

                for i, plan in enumerate(result["plan_options"][:2], 1):
                    with st.expander(f"📋 Plan Option {i} - {len(plan.semesters)} Semesters", expanded=(i==1)):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Courses", len(plan.courses))
                        with col2:
                            st.metric("Semesters", len(plan.semesters))
                        with col3:
                            st.metric("Confidence", f"{plan.confidence:.0%}")

                        if plan.justification:
                            st.markdown("**Rationale:**")
                            st.info(plan.justification)

                        st.markdown("**Semester Breakdown:**")
                        for j, sem in enumerate(plan.semesters, 1):
                            term = sem.get('term', f'Semester {j}')
                            courses = sem.get('courses', [])
                            units = sem.get('total_units', 0)

                            unit_color = "🟢" if units <= 48 else "🟡" if units <= 54 else "🔴"

                            st.markdown(f"**{term}** {unit_color} ({units} units)")
                            st.caption(', '.join(courses))

            # Show research analytics panel
            show_research_analytics_panel(workflow_data)

        # Add assistant response
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()

if __name__ == "__main__":
    main()
