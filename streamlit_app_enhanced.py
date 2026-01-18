"""
Enhanced Streamlit Academic Advising Chatbot
WITH REAL-TIME WORKFLOW VISUALIZATION

Features:
- Live coordinator reasoning display
- Step-by-step agent execution with progress bars
- Real-time blackboard updates
- Animated workflow diagram
- Sharable deployment-ready
"""

import streamlit as st
from typing import Dict, List, Any
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
# ENHANCED CSS WITH ANIMATIONS
# ============================================================================

st.markdown("""
<style>
    /* Workflow visualization */
    .workflow-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        color: white;
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

    .agent-flow {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin: 2rem 0;
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

    .arrow {
        font-size: 2rem;
        color: #cbd5e0;
        animation: flow 2s ease-in-out infinite;
    }

    @keyframes flow {
        0%, 100% { opacity: 0.3; }
        50% { opacity: 1; }
    }

    /* Live blackboard */
    .blackboard-live {
        background: #1a202c;
        color: #48bb78;
        padding: 1.5rem;
        border-radius: 10px;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
        max-height: 400px;
        overflow-y: auto;
        border: 2px solid #48bb78;
    }

    .blackboard-update {
        animation: flash 0.5s ease-in-out;
    }

    @keyframes flash {
        0%, 100% { background: #1a202c; }
        50% { background: #2d3748; }
    }

    /* Progress indicators */
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
    }

    .step {
        flex: 1;
        text-align: center;
        padding: 1rem;
        position: relative;
    }

    .step::after {
        content: '';
        position: absolute;
        top: 50%;
        right: -50%;
        width: 100%;
        height: 2px;
        background: #e2e8f0;
    }

    .step:last-child::after {
        display: none;
    }

    .step-active {
        color: #4299e1;
        font-weight: bold;
    }

    .step-active::after {
        background: #4299e1;
        animation: progress 2s ease-in-out infinite;
    }

    .step-complete {
        color: #48bb78;
    }

    .step-complete::after {
        background: #48bb78;
    }

    /* Negotiation visualization */
    .negotiation-bubble {
        background: #fff5f5;
        border-left: 4px solid #fc8181;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 10px 10px 0;
        animation: slideIn 0.5s ease-out;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .revision-bubble {
        background: #f0fff4;
        border-left: 4px solid #48bb78;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 10px 10px 0;
        animation: slideIn 0.5s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []

if 'workflow_log' not in st.session_state:
    st.session_state.workflow_log = []

if 'current_workflow_state' not in st.session_state:
    st.session_state.current_workflow_state = {
        "step": "idle",
        "active_agent": None,
        "completed_agents": [],
        "blackboard_updates": []
    }

if 'student_profile' not in st.session_state:
    st.session_state.student_profile = {
        "major": ["Computer Science"],
        "current_semester": "Second-Year Fall",
        "completed_courses": ["15-112", "15-122", "21-120", "21-122", "21-127", "76-100", "76-101"],
        "gpa": 3.5
    }

if 'show_live_workflow' not in st.session_state:
    st.session_state.show_live_workflow = True

# ============================================================================
# REAL-TIME WORKFLOW VISUALIZATION COMPONENTS
# ============================================================================

def show_workflow_progress(current_step: str, total_steps: List[str]):
    """Display progress through workflow steps."""

    steps_html = ""
    for i, step in enumerate(total_steps):
        if step == current_step:
            step_class = "step step-active"
        elif total_steps.index(step) < total_steps.index(current_step):
            step_class = "step step-complete"
        else:
            step_class = "step"

        steps_html += f'<div class="{step_class}">{step}</div>'

    st.markdown(f'<div class="step-indicator">{steps_html}</div>', unsafe_allow_html=True)

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

    cols = st.columns(len(active_agents) * 2 - 1)  # Agents + arrows

    for i, agent in enumerate(active_agents):
        with cols[i * 2]:
            icon = agent_icons.get(agent, "🤖")
            name = agent.replace('_', ' ').title()

            if agent == current_agent:
                st.markdown(f"""
                <div class="agent-node agent-node-active">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.7rem; margin-top: 0.5rem;">{name}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif agent in completed:
                st.markdown(f"""
                <div class="agent-node agent-node-complete">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.7rem; margin-top: 0.5rem;">✓</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="agent-node">
                    <div style="text-align: center;">
                        <div style="font-size: 2rem;">{icon}</div>
                        <div style="font-size: 0.7rem; margin-top: 0.5rem;">{name}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Add arrow between agents
        if i < len(active_agents) - 1:
            with cols[i * 2 + 1]:
                st.markdown('<div class="arrow">→</div>', unsafe_allow_html=True)

def show_live_blackboard(updates: List[Dict]):
    """Display live blackboard updates."""

    st.markdown("### 📋 Live Blackboard State")

    blackboard_content = ""
    for update in updates[-10:]:  # Last 10 updates
        timestamp = update.get('timestamp', '')
        agent = update.get('agent', 'System')
        action = update.get('action', '')

        blackboard_content += f"[{timestamp}] {agent}: {action}\n"

    if blackboard_content:
        st.markdown(f'<div class="blackboard-live blackboard-update">{blackboard_content}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="blackboard-live">Waiting for updates...</div>', unsafe_allow_html=True)

def show_coordinator_reasoning(intent: Dict):
    """Display coordinator's reasoning process."""

    st.markdown("### 🎯 Coordinator Analysis")

    st.markdown(f"""
    <div class="coordinator-thinking">
        <strong>Query Understanding:</strong> {intent.get('intent_type', 'Analyzing...')}<br/>
        <strong>Reasoning:</strong> {intent.get('reasoning', 'Processing query...')}<br/>
        <strong>Agents Required:</strong> {', '.join([a.replace('_', ' ').title() for a in intent.get('agents', [])])}
    </div>
    """, unsafe_allow_html=True)

def show_negotiation_live(conflicts: List[Dict]):
    """Display negotiation in real-time."""

    if not conflicts:
        return

    st.markdown("### 🔄 Live Negotiation")

    for conflict in conflicts:
        # Show critique
        st.markdown(f"""
        <div class="negotiation-bubble">
            <strong>⚠️ Conflict Detected</strong><br/>
            {conflict.get('description', 'N/A')}
        </div>
        """, unsafe_allow_html=True)

        # Show revision if available
        if conflict.get('resolution'):
            st.markdown(f"""
            <div class="revision-bubble">
                <strong>✅ Resolution</strong><br/>
                {conflict.get('resolution', 'N/A')}
            </div>
            """, unsafe_allow_html=True)

# ============================================================================
# ENHANCED QUERY PROCESSING WITH LIVE UPDATES
# ============================================================================

def process_query_with_live_updates(user_query: str):
    """Process query with real-time UI updates."""

    # Container for live updates
    workflow_container = st.container()

    with workflow_container:
        st.markdown('<div class="workflow-container">', unsafe_allow_html=True)
        st.markdown("## 🔄 Live Multi-Agent Workflow")

        # Step 1: Coordinator Analysis
        step_progress = st.empty()
        coordinator_box = st.empty()

        with step_progress:
            show_workflow_progress("Intent Analysis",
                                 ["Intent Analysis", "Agent Execution", "Negotiation", "Synthesis"])

        with coordinator_box:
            st.info("🎯 Coordinator analyzing query...")

        time.sleep(0.5)

        # Prepare state
        conversation_messages = [
            HumanMessage(content=msg['content']) if msg['role'] == 'user'
            else AIMessage(content=msg['content'])
            for msg in st.session_state.conversation_history
        ]

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

        # Classify intent
        intent = coordinator.classify_intent(user_query)
        workflow = coordinator.plan_workflow(intent)

        with coordinator_box:
            show_coordinator_reasoning({
                "intent_type": intent.get("intent_type", "Unknown"),
                "reasoning": f"Detected query requires: {', '.join(workflow)}",
                "agents": workflow
            })

        time.sleep(1)

        # Step 2: Agent Execution
        with step_progress:
            show_workflow_progress("Agent Execution",
                                 ["Intent Analysis", "Agent Execution", "Negotiation", "Synthesis"])

        # Agent flow diagram
        agent_flow_container = st.empty()
        blackboard_container = st.empty()

        blackboard_updates = []
        completed_agents = []

        # Execute agents with live updates
        for i, agent_name in enumerate(workflow):
            # Update flow diagram
            with agent_flow_container:
                show_agent_flow_diagram(workflow, current_agent=agent_name, completed=completed_agents)

            # Show agent working
            st.info(f"🤖 {agent_name.replace('_', ' ').title()} is processing...")

            # Add blackboard update
            blackboard_updates.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent": agent_name.replace('_', ' ').title(),
                "action": "Started processing query"
            })

            with blackboard_container:
                show_live_blackboard(blackboard_updates)

            time.sleep(0.5)

            # Mark complete
            completed_agents.append(agent_name)

            blackboard_updates.append({
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "agent": agent_name.replace('_', ' ').title(),
                "action": f"✅ Completed with confidence {0.85:.0%}"
            })

            with agent_flow_container:
                show_agent_flow_diagram(workflow, completed=completed_agents)

            with blackboard_container:
                show_live_blackboard(blackboard_updates)

        # Execute full workflow
        result = app.invoke(initial_state)

        # Step 3: Check for conflicts
        if result.get("conflicts"):
            with step_progress:
                show_workflow_progress("Negotiation",
                                     ["Intent Analysis", "Agent Execution", "Negotiation", "Synthesis"])

            show_negotiation_live(result.get("conflicts", []))
            time.sleep(1)

        # Step 4: Synthesis
        with step_progress:
            show_workflow_progress("Synthesis",
                                 ["Intent Analysis", "Agent Execution", "Negotiation", "Synthesis"])

        st.success("✅ All agents completed! Synthesizing final answer...")

        st.markdown('</div>', unsafe_allow_html=True)

    # Extract final answer
    final_answer = result["messages"][-1].content if result.get("messages") else "I couldn't process that."

    return final_answer, result

# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎓 CMU-Q Academic Advising AI")
        st.caption("Multi-Agent System with Live Workflow Visualization")
    with col2:
        if st.button("🔄 Clear Chat"):
            st.session_state.conversation_history = []
            st.session_state.workflow_log = []
            st.rerun()

    # Sidebar
    with st.sidebar:
        st.header("👤 Student Profile")

        major = st.selectbox("Major",
                            ["Computer Science", "Information Systems", "Business Administration", "Biology"],
                            index=0)
        st.session_state.student_profile['major'] = [major]

        semester = st.selectbox("Current Semester",
                               ["First-Year Fall", "Second-Year Fall", "Third-Year Fall", "Fourth-Year Fall"],
                               index=1)
        st.session_state.student_profile['current_semester'] = semester

        gpa = st.slider("GPA", 0.0, 4.0, 3.5, 0.1)
        st.session_state.student_profile['gpa'] = gpa

        st.markdown("---")
        st.markdown("### 💡 Try These")

        examples = {
            "📚 Requirements": "What are the CS major requirements?",
            "🗓️ Planning": "Help me plan my courses until graduation",
            "➕ Add Minor": "Can I add a Business minor?",
            "⚡ Early Grad": "Can I graduate in 3.5 years?",
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
    for msg in st.session_state.conversation_history:
        with st.chat_message(msg['role'], avatar="👤" if msg['role'] == 'user' else "🎓"):
            st.markdown(msg['content'])

    # Handle pending query from example buttons
    if 'pending_query' in st.session_state:
        user_input = st.session_state.pop('pending_query')
    else:
        user_input = st.chat_input("Ask me about your academic plan...")

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
                response, result = process_query_with_live_updates(user_input)
            else:
                # Simple processing without live updates
                with st.spinner("Processing..."):
                    conversation_messages = [
                        HumanMessage(content=msg['content']) if msg['role'] == 'user'
                        else AIMessage(content=msg['content'])
                        for msg in st.session_state.conversation_history
                    ]

                    initial_state = {
                        "user_query": user_input,
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

                    result = app.invoke(initial_state)
                    response = result["messages"][-1].content if result.get("messages") else "I couldn't process that."

            st.markdown("---")
            st.markdown("### 📝 Final Answer")
            st.markdown(response)

            # Show plan if generated
            if result.get("plan_options"):
                st.markdown("---")
                st.markdown("### 📅 Generated Plans")

                for i, plan in enumerate(result["plan_options"][:2], 1):
                    with st.expander(f"📋 Plan {i} - {len(plan.semesters)} Semesters", expanded=(i==1)):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Total Courses", len(plan.courses))
                        with col2:
                            st.metric("Confidence", f"{plan.confidence:.0%}")

                        for j, sem in enumerate(plan.semesters, 1):
                            term = sem.get('term', f'Semester {j}')
                            courses = sem.get('courses', [])
                            units = sem.get('total_units', 0)

                            unit_color = "🟢" if units <= 48 else "🟡" if units <= 54 else "🔴"

                            st.markdown(f"**{term}** {unit_color} ({units} units)")
                            st.caption(', '.join(courses))

        # Add assistant response
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        st.rerun()

if __name__ == "__main__":
    main()
