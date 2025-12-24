"""
Interactive Chat Interface with Workflow Demonstration
Shows the complete multi-agent workflow including negotiation and collaboration.
"""
from multi_agent import app
from blackboard.schema import WorkflowStep, ConflictType
from langchain_core.messages import HumanMessage
import os
import time

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print welcome header."""
    print("=" * 80)
    print("🎓 CMU-Q Academic Advising Chatbot - Workflow Demonstration")
    print("=" * 80)
    print("\nThis interface shows how multiple agents collaborate to answer your questions.")
    print("\nYou'll see:")
    print("  • Intent classification by Coordinator")
    print("  • Which agents are activated")
    print("  • Each agent's contribution")
    print("  • Negotiation/collaboration process")
    print("  • Final synthesized answer")
    print("\nType 'quit' or 'exit' to end")
    print("-" * 80)
    print()

def print_step(step_num, title, delay=0.5):
    """Print a workflow step header."""
    print("\n" + "=" * 80)
    print(f"STEP {step_num}: {title}")
    print("=" * 80)
    time.sleep(delay)

def print_agent_output(agent_name, output, show_details=True):
    """Print an agent's output in a formatted way."""
    display_name = agent_name.replace("_", " ").title()
    
    print(f"\n🤖 {display_name} Agent:")
    print("-" * 80)
    
    if show_details:
        print(f"   Confidence: {output.confidence:.2f}")
        if output.relevant_policies:
            print(f"   Policies Cited: {', '.join(output.relevant_policies[:3])}")
        if output.risks:
            print(f"   Risks Identified: {len(output.risks)}")
        if output.constraints:
            print(f"   Constraints Found: {len(output.constraints)}")
        if output.plan_options:
            print(f"   Plan Options Proposed: {len(output.plan_options)}")
    
    print(f"\n   💭 Agent's Response:")
    print("   " + "-" * 76)
    # Word wrap the answer
    words = output.answer.split()
    line = "   "
    for word in words:
        if len(line + word) < 78:
            line += word + " "
        else:
            print(line)
            line = "   " + word + " "
    if line.strip():
        print(line)
    
    # Show plan options if any
    if output.plan_options:
        print(f"\n   📋 Proposed Plan(s):")
        for i, plan in enumerate(output.plan_options[:2], 1):  # Show max 2 plans
            print(f"\n   Plan Option {i}:")
            print(f"      Courses: {', '.join(plan.courses[:5])}{'...' if len(plan.courses) > 5 else ''}")
            print(f"      Confidence: {plan.confidence:.2f}")
            print(f"      Justification: {plan.justification[:100]}...")
    
    # Show risks if any
    if output.risks:
        print(f"\n   ⚠️  Risks Identified:")
        for risk in output.risks[:3]:  # Show max 3 risks
            severity_emoji = "🔴" if risk.severity == "high" else "🟡" if risk.severity == "medium" else "🟢"
            print(f"      {severity_emoji} [{risk.severity.upper()}] {risk.description[:80]}...")
    
    # Show constraints if any
    if output.constraints:
        print(f"\n   🚫 Constraints:")
        for constraint in output.constraints[:3]:  # Show max 3 constraints
            hard_emoji = "🔴" if constraint.hard else "🟡"
            print(f"      {hard_emoji} {'[HARD]' if constraint.hard else '[SOFT]'} {constraint.description[:80]}...")
    
    print()

def print_conflict(conflict):
    """Print conflict information."""
    conflict_emoji = {
        ConflictType.HARD_VIOLATION: "🔴",
        ConflictType.HIGH_RISK: "🟡",
        ConflictType.TRADE_OFF: "🟢"
    }
    emoji = conflict_emoji.get(conflict.conflict_type, "⚠️")
    
    print(f"\n   {emoji} Conflict Type: {conflict.conflict_type.value.replace('_', ' ').title()}")
    print(f"   Affected Agents: {', '.join(conflict.affected_agents)}")
    print(f"   Description: {conflict.description}")
    if conflict.options:
        print(f"   Resolution Options: {len(conflict.options)}")

def simulate_workflow(state):
    """Simulate and display the workflow step by step."""
    step = 1
    
    # Step 1: Intent Classification
    print_step(step, "Intent Classification by Coordinator", delay=0.3)
    from coordinator.coordinator import Coordinator
    coordinator = Coordinator()
    
    user_query = state.get("user_query", "")
    intent = coordinator.classify_intent(user_query)
    
    print(f"\n📝 User Query: \"{user_query}\"")
    print(f"\n🎯 Intent Classified: {intent.get('intent_type', 'unknown')}")
    print(f"   Priority: {intent.get('priority', 'medium')}")
    print(f"   Reasoning: {intent.get('reasoning', 'N/A')}")
    
    workflow = coordinator.plan_workflow(intent)
    print(f"\n📋 Workflow Planned:")
    for i, agent in enumerate(workflow, 1):
        print(f"   {i}. {agent.replace('_', ' ').title()} Agent")
    
    state["active_agents"] = workflow
    state["workflow_step"] = WorkflowStep.AGENT_EXECUTION
    state["next_agent"] = workflow[0] if workflow else None
    state["user_goal"] = intent.get("intent_type", "")
    
    time.sleep(1)
    
    # Step 2: Agent Execution
    step += 1
    print_step(step, "Agent Execution & Collaboration", delay=0.3)
    
    from agents.programs_agent import ProgramsRequirementsAgent
    from agents.courses_agent import CourseSchedulingAgent
    from agents.policy_agent import PolicyComplianceAgent
    
    agents = {
        "programs_requirements": ProgramsRequirementsAgent(),
        "course_scheduling": CourseSchedulingAgent(),
        "policy_compliance": PolicyComplianceAgent()
    }
    
    # Execute agents in workflow order
    for agent_name in workflow:
        if agent_name in agents:
            print(f"\n⏳ Executing {agent_name.replace('_', ' ').title()} Agent...")
            agent = agents[agent_name]
            output = agent.execute(state)
            
            # Update state
            agent_outputs = state.get("agent_outputs", {})
            agent_outputs[agent_name] = output
            state["agent_outputs"] = agent_outputs
            
            # Update plan options if Programs agent proposed plans
            if agent_name == "programs_requirements" and output.plan_options:
                state["plan_options"] = output.plan_options
            
            # Update risks and constraints
            state["risks"] = state.get("risks", []) + output.risks
            state["constraints"] = state.get("constraints", []) + output.constraints
            
            # Show agent output
            print_agent_output(agent_name, output)
            time.sleep(0.5)
    
    # Step 3: Conflict Detection & Negotiation
    step += 1
    print_step(step, "Conflict Detection & Negotiation", delay=0.3)
    
    conflicts = coordinator.detect_conflicts(state)
    
    if conflicts:
        print(f"\n🔍 Conflicts Detected: {len(conflicts)}")
        for conflict in conflicts:
            print_conflict(conflict)
        
        # Show negotiation process
        print(f"\n🔄 Negotiation Process:")
        print("   Coordinator is managing Proposal + Critique protocol...")
        
        iteration = state.get("iteration_count", 0)
        max_iterations = 3
        
        if iteration < max_iterations:
            print(f"   Iteration {iteration + 1}/{max_iterations}")
            
            # Check if we need Policy agent to critique
            if "programs_requirements" in state["agent_outputs"] and "policy_compliance" not in state["agent_outputs"]:
                programs_output = state["agent_outputs"]["programs_requirements"]
                if programs_output.plan_options:
                    print("   → Policy Agent critiquing proposed plan...")
                    policy_agent = agents["policy_compliance"]
                    policy_output = policy_agent.execute(state)
                    
                    agent_outputs = state.get("agent_outputs", {})
                    agent_outputs["policy_compliance"] = policy_output
                    state["agent_outputs"] = agent_outputs
                    state["risks"] = state.get("risks", []) + policy_output.risks
                    state["constraints"] = state.get("constraints", []) + policy_output.constraints
                    
                    print_agent_output("policy_compliance", policy_output)
                    
                    # Re-detect conflicts after critique
                    conflicts = coordinator.detect_conflicts(state)
                    if conflicts:
                        print(f"\n   ⚠️  Conflicts remain after critique:")
                        for conflict in conflicts:
                            print_conflict(conflict)
        else:
            print("   Maximum iterations reached. Asking user for input.")
    else:
        print("\n✅ No conflicts detected. All agents agree!")
    
    state["conflicts"] = conflicts
    time.sleep(1)
    
    # Step 4: Answer Synthesis
    step += 1
    print_step(step, "Answer Synthesis by Coordinator", delay=0.3)
    
    print("\n🧠 Coordinator synthesizing final answer from all agent contributions...")
    print("   Combining insights from:")
    for agent_name in state["agent_outputs"].keys():
        print(f"      • {agent_name.replace('_', ' ').title()} Agent")
    
    answer = coordinator.synthesize_answer(state)
    
    print("\n" + "=" * 80)
    print("💬 FINAL ADVISOR RESPONSE")
    print("=" * 80)
    print()
    
    # Format final answer nicely
    words = answer.split()
    line = ""
    for word in words:
        if len(line + word) < 78:
            line += word + " "
        else:
            print(line)
            line = word + " "
    if line:
        print(line)
    
    print("\n" + "=" * 80)
    
    return answer

def chat():
    """Main chat loop with workflow demonstration."""
    clear_screen()
    print_header()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Good luck with your studies!")
                break
            
            if user_input.lower() == 'clear':
                clear_screen()
                print_header()
                continue
            
            # Prepare state
            state = {
                "user_query": user_input,
                "student_profile": {},  # TODO: Can be customized
                "agent_outputs": {},
                "constraints": [],
                "risks": [],
                "plan_options": [],
                "conflicts": [],
                "open_questions": [],
                "messages": [HumanMessage(content=user_input)],
                "active_agents": [],
                "workflow_step": WorkflowStep.INITIAL,
                "iteration_count": 0,
                "next_agent": None,
                "user_goal": None
            }
            
            # Simulate and show workflow
            answer = simulate_workflow(state)
            
            # Optionally run through actual workflow to verify
            # result = app.invoke(state)
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Good luck with your studies!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\nPlease try again or type 'quit' to exit.")

if __name__ == "__main__":
    chat()

