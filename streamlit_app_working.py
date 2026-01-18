"""
Working Streamlit App - Shows REAL Agent Outputs

FIXES:
1. Actually executes agents and shows their real outputs
2. Analytics panel appears after answer
3. Shows what each agent actually says
4. Captures real negotiation if it happens
"""

import streamlit as st
from typing import Dict, List, Any
import json
from datetime import datetime
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from multi_agent import app
from blackboard.schema import WorkflowStep, AgentOutput
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
# CSS
# ============================================================================

st.markdown("""
<style>
    .agent-output-box {
        background: #f7fafc;
        border-left: 4px solid #4299e1;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }

    .agent-header {
        color: #2d3748;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }

    .confidence-badge {
        background: #48bb78;
        color: white;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.875rem;
        display: inline-block;
    }

    .analytics-panel {
        background: #edf2f7;
        border: 2px solid #cbd5e0;
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1.5rem 0;
    }

    .timeline-event {
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-left: 3px solid #cbd5e0;
        padding-left: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'workflow_history' not in st.session_state:
    st.session_state.workflow_history = []

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

    return " | ".join(parts) if parts else "Profile not set"

def inject_profile_into_query(query: str, profile: Dict) -> str:
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

def show_agent_output_live(agent_name: str, output: AgentOutput):
    """Display what an agent actually said."""

    agent_display = agent_name.replace('_', ' ').title()

    st.markdown(f"""
    <div class="agent-output-box">
        <div class="agent-header">🤖 {agent_display}</div>
        <div class="confidence-badge">Confidence: {output.confidence:.0%}</div>
    </div>
    """, unsafe_allow_html=True)

    # Show agent's answer
    with st.expander(f"📄 {agent_display}'s Full Response", expanded=True):
        st.write(output.answer)

        if output.plan_options:
            st.write(f"**📋 Proposed {len(output.plan_options)} plan(s)**")

        if output.risks:
            st.write(f"**⚠️ Identified {len(output.risks)} risk(s):**")
            for risk in output.risks[:3]:
                st.caption(f"• {risk.description}")

        if output.constraints:
            st.write(f"**🚫 Found {len(output.constraints)} constraint(s):**")
            for constraint in output.constraints[:3]:
                st.caption(f"• {constraint.description}")

def show_analytics_panel(workflow_data: Dict):
    """Show analytics panel after answer."""

    st.markdown("---")

    with st.expander("🔬 **Research Analytics - View Complete Workflow**", expanded=False):
        st.markdown('<div class="analytics-panel">', unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs([
            "📊 Workflow Summary",
            "🤖 Agent Outputs",
            "🔄 Negotiation"
        ])

        # TAB 1: Workflow Summary
        with tab1:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Agents Activated", len(workflow_data.get('active_agents', [])))
            with col2:
                st.metric("Execution Time", f"{workflow_data.get('execution_time', 0):.1f}s")
            with col3:
                st.metric("Conflicts", len(workflow_data.get('conflicts', [])))

            st.markdown("**Timeline:**")
            for event in workflow_data.get('timeline', []):
                icon = {'coordinator': '🎯', 'agent': '🤖', 'synthesis': '✨'}.get(event['type'], '•')
                st.markdown(f"""
                <div class="timeline-event">
                    {icon} <strong>{event['timestamp']}</strong>: {event['description']}
                </div>
                """, unsafe_allow_html=True)

        # TAB 2: Agent Outputs
        with tab2:
            st.markdown("**What Each Agent Said:**")

            for agent_name, output in workflow_data.get('agent_outputs', {}).items():
                with st.expander(f"📌 {agent_name.replace('_', ' ').title()}", expanded=False):
                    st.markdown(f"**Confidence:** {output.confidence:.0%}")
                    st.markdown("**Full Answer:**")
                    st.info(output.answer)

                    if output.plan_options:
                        st.write(f"Proposed {len(output.plan_options)} plan(s)")

                    if output.risks:
                        st.write(f"**Risks ({len(output.risks)}):**")
                        for risk in output.risks:
                            st.caption(f"⚠️ {risk.description}")

        # TAB 3: Negotiation
        with tab3:
            conflicts = workflow_data.get('conflicts', [])

            if conflicts:
                for i, conflict in enumerate(conflicts, 1):
                    st.markdown(f"**Conflict {i}:**")
                    st.warning(f"{conflict.conflict_type.value}: {conflict.description}")
                    st.caption(f"Affected: {', '.join(conflict.affected_agents)}")
            else:
                st.success("✅ No conflicts - all agents agreed!")

        st.markdown('</div>', unsafe_allow_html=True)

# ============================================================================
# MAIN PROCESSING
# ============================================================================

def process_query(user_query: str):
    """Process query and show real agent outputs."""

    start_time = time.time()

    # Workflow tracking
    workflow_data = {
        'query': user_query,
        'timeline': [],
        'active_agents': [],
        'agent_outputs': {},
        'conflicts': [],
        'final_state': {},
        'execution_time': 0
    }

    # Progress container
    progress_container = st.container()

    with progress_container:
        st.markdown("### 🔄 Processing Your Query")

        # Check profile
        profile = st.session_state.student_profile
        profile_used = any([profile.get('major'), profile.get('current_semester'), profile.get('gpa')])

        if profile_used:
            enhanced_query = inject_profile_into_query(user_query, profile)
            st.info(f"📋 Using your profile: {get_student_profile_summary()}")
            workflow_data['timeline'].append({
                'type': 'coordinator',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f'Enhanced query with student profile'
            })
        else:
            enhanced_query = user_query

        # Show coordinator thinking
        with st.spinner("🎯 Coordinator analyzing query..."):
            workflow_data['timeline'].append({
                'type': 'coordinator',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': 'Coordinator classifying intent'
            })

        # Prepare state
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

        # EXECUTE THE ACTUAL WORKFLOW
        st.write("🤖 **Executing Multi-Agent Workflow...**")

        workflow_data['timeline'].append({
            'type': 'coordinator',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'description': 'Starting agent execution'
        })

        with st.spinner("⏳ Agents working..."):
            result = app.invoke(initial_state)

        # Extract what happened
        workflow_data['active_agents'] = result.get('active_agents', [])
        workflow_data['agent_outputs'] = result.get('agent_outputs', {})
        workflow_data['conflicts'] = result.get('conflicts', [])
        workflow_data['final_state'] = result

        # Show which agents ran
        st.success(f"✅ Completed! {len(workflow_data['active_agents'])} agents activated: {', '.join([a.replace('_', ' ').title() for a in workflow_data['active_agents']])}")

        workflow_data['timeline'].append({
            'type': 'agent',
            'timestamp': datetime.now().strftime("%H:%M:%S"),
            'description': f"Executed {len(workflow_data['active_agents'])} agents"
        })

        # Show each agent's output
        st.markdown("---")
        st.markdown("### 🤖 What Each Agent Said")

        for agent_name, output in workflow_data['agent_outputs'].items():
            show_agent_output_live(agent_name, output)

            workflow_data['timeline'].append({
                'type': 'agent',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f"{agent_name.replace('_', ' ').title()} completed with {output.confidence:.0%} confidence"
            })

        # Show conflicts if any
        if workflow_data['conflicts']:
            st.markdown("---")
            st.markdown("### ⚠️ Conflicts Detected")
            for conflict in workflow_data['conflicts']:
                st.warning(f"**{conflict.conflict_type.value}:** {conflict.description}")
                st.caption(f"Agents involved: {', '.join(conflict.affected_agents)}")

            workflow_data['timeline'].append({
                'type': 'negotiation',
                'timestamp': datetime.now().strftime("%H:%M:%S"),
                'description': f"Resolved {len(workflow_data['conflicts'])} conflict(s)"
            })

    workflow_data['execution_time'] = time.time() - start_time
    workflow_data['timeline'].append({
        'type': 'synthesis',
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'description': 'Synthesized final answer'
    })

    # Store for analytics
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
        st.caption("Multi-Agent System - See What Each Agent Says!")
    with col2:
        if st.button("🔄 New Session"):
            st.session_state.conversation_history = []
            st.session_state.workflow_history = []
            st.rerun()

    # Show profile status
    profile_summary = get_student_profile_summary()
    if profile_summary != "Profile not set":
        st.success(f"👤 {profile_summary}")
    else:
        st.info("👤 Profile not set (optional)")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Student Profile")
        st.caption("Optional - for personalized advice")

        # Major
        major_options = ["Not set", "Computer Science", "Information Systems", "Business Administration", "Biology"]
        selected_major = st.selectbox("Major", major_options)

        if selected_major != "Not set":
            st.session_state.student_profile['major'] = [selected_major]
        else:
            st.session_state.student_profile['major'] = None

        # Semester
        semester_options = ["Not set", "First-Year Fall", "First-Year Spring", "Second-Year Fall",
                           "Second-Year Spring", "Third-Year Fall", "Third-Year Spring",
                           "Fourth-Year Fall", "Fourth-Year Spring"]
        selected_semester = st.selectbox("Current Semester", semester_options)

        if selected_semester != "Not set":
            st.session_state.student_profile['current_semester'] = selected_semester
        else:
            st.session_state.student_profile['current_semester'] = None

        # GPA
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
        st.markdown("### 💡 Examples")

        examples = [
            "What are the CS major requirements?",
            "Help me plan my courses until graduation",
            "Can I add a Business minor?",
            "What should I take next semester?",
        ]

        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:20]}"):
                st.session_state['pending_query'] = ex
                st.rerun()

    # Display conversation
    for i, msg in enumerate(st.session_state.conversation_history):
        with st.chat_message(msg['role'], avatar="👤" if msg['role'] == 'user' else "🎓"):
            st.markdown(msg['content'])

            # Show analytics for previous responses
            if msg['role'] == 'assistant' and i < len(st.session_state.workflow_history):
                show_analytics_panel(st.session_state.workflow_history[i // 2])

    # Get input
    if 'pending_query' in st.session_state:
        user_input = st.session_state.pop('pending_query')
    else:
        user_input = st.chat_input("Ask about your academic plan...")

    if user_input:
        # Add user message
        st.session_state.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        # Process
        with st.chat_message("assistant", avatar="🎓"):
            response, result, workflow_data = process_query(user_input)

            # Show final answer
            st.markdown("---")
            st.markdown("### 📝 Final Answer")
            st.markdown(response)

            # Show plans if generated
            if result.get("plan_options"):
                st.markdown("---")
                st.markdown("### 📅 Generated Plans")

                for i, plan in enumerate(result["plan_options"][:2], 1):
                    with st.expander(f"📋 Plan {i} - {len(plan.semesters)} Semesters"):
                        st.metric("Confidence", f"{plan.confidence:.0%}")

                        if plan.justification:
                            st.info(plan.justification)

                        for j, sem in enumerate(plan.semesters, 1):
                            term = sem.get('term', f'Semester {j}')
                            courses = sem.get('courses', [])
                            units = sem.get('total_units', 0)

                            st.markdown(f"**{term}** ({units} units)")
                            st.caption(', '.join(courses))

            # Show analytics panel
            show_analytics_panel(workflow_data)

        # Add response
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()

if __name__ == "__main__":
    main()
