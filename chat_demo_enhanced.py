"""
Enhanced Interactive Chat with Real-Time Workflow Demonstration
Shows the actual multi-agent workflow including negotiation and collaboration.
"""
from multi_agent import app, coordinator, programs_agent, courses_agent, policy_agent
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
    print("\nThis interface shows how multiple agents collaborate in real-time.")
    print("\nYou'll see:")
    print("  • Intent classification")
    print("  • Agent activation and execution")
    print("  • Negotiation/collaboration process")
    print("  • Final human-like advisor response")
    print("\nType 'quit' to exit")
    print("-" * 80)
    print()

def print_section(title, emoji="📋"):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(f"{emoji} {title}")
    print("=" * 80)

def print_subsection(title, emoji="  •"):
    """Print a subsection."""
    print(f"\n{emoji} {title}")
    print("-" * 80)

def format_text(text, indent="   ", width=76):
    """Format text with word wrapping."""
    words = text.split()
    lines = []
    line = indent
    for word in words:
        if len(line + word) < width:
            line += word + " "
        else:
            if line.strip():
                lines.append(line.rstrip())
            line = indent + word + " "
    if line.strip():
        lines.append(line.rstrip())
    return "\n".join(lines)

def show_intent_classification(query):
    """Show intent classification step."""
    print_section("STEP 1: Intent Classification", "🎯")
    print(f"\n   Query: \"{query}\"")
    print("\n   Analyzing query to determine which agents are needed...")
    
    intent = coordinator.classify_intent(query)
    
    print(f"\n   ✅ Intent Type: {intent.get('intent_type', 'unknown').replace('_', ' ').title()}")
    print(f"   📊 Priority: {intent.get('priority', 'medium')}")
    print(f"   💭 Reasoning: {intent.get('reasoning', 'N/A')}")
    
    required_agents = intent.get('required_agents', [])
    print(f"\n   🤖 Agents to Activate:")
    for i, agent in enumerate(required_agents, 1):
        agent_display = agent.replace('_', ' ').title()
        print(f"      {i}. {agent_display}")
    
    workflow = coordinator.plan_workflow(intent)
    print(f"\n   📋 Workflow Order:")
    for i, agent in enumerate(workflow, 1):
        agent_display = agent.replace('_', ' ').title()
        print(f"      {i}. {agent_display}")
    
    time.sleep(1)
    return intent, workflow

def show_agent_execution(agent_name, state):
    """Show agent execution."""
    agent_display = agent_name.replace('_', ' ').title()
    print_subsection(f"Executing {agent_display} Agent", "🤖")
    
    # Map agent names to instances
    agents = {
        "programs_requirements": programs_agent,
        "course_scheduling": courses_agent,
        "policy_compliance": policy_agent
    }
    
    if agent_name not in agents:
        print(f"   ⚠️  Unknown agent: {agent_name}")
        return None
    
    agent = agents[agent_name]
    print(f"   ⏳ {agent_display} is processing your query...")
    print(f"      (Retrieving domain-specific knowledge)")
    
    # Execute agent
    output = agent.execute(state)
    
    # Display output
    print(f"\n   ✅ {agent_display} completed!")
    print(f"      Confidence: {output.confidence:.2f}")
    
    if output.relevant_policies:
        print(f"      Policies Cited: {len(output.relevant_policies)}")
    
    # Show answer preview
    answer_preview = output.answer[:150] + "..." if len(output.answer) > 150 else output.answer
    print(f"\n   💭 Agent's Contribution:")
    print(format_text(answer_preview))
    
    # Show plan options if Programs agent
    if agent_name == "programs_requirements" and output.plan_options:
        print(f"\n   📋 Plan Options Proposed: {len(output.plan_options)}")
        for i, plan in enumerate(output.plan_options[:2], 1):
            courses_str = ', '.join(plan.courses[:5])
            if len(plan.courses) > 5:
                courses_str += f" (+{len(plan.courses) - 5} more)"
            print(f"      Option {i}: {courses_str}")
            print(f"         Confidence: {plan.confidence:.2f}")
    
    # Show risks
    if output.risks:
        print(f"\n   ⚠️  Risks Identified: {len(output.risks)}")
        for risk in output.risks[:2]:
            severity_icon = "🔴" if risk.severity == "high" else "🟡" if risk.severity == "medium" else "🟢"
            print(f"      {severity_icon} [{risk.severity.upper()}] {risk.description[:60]}...")
    
    # Show constraints
    if output.constraints:
        print(f"\n   🚫 Constraints Found: {len(output.constraints)}")
        for constraint in output.constraints[:2]:
            hard_icon = "🔴" if constraint.hard else "🟡"
            print(f"      {hard_icon} {'[HARD]' if constraint.hard else '[SOFT]'} {constraint.description[:60]}...")
    
    time.sleep(0.8)
    return output

def show_negotiation(state):
    """Show negotiation/collaboration process."""
    print_section("STEP 3: Collaboration & Negotiation", "🔄")
    
    agent_outputs = state.get("agent_outputs", {})
    
    # Check if Programs agent proposed a plan
    programs_output = agent_outputs.get("programs_requirements")
    has_proposal = programs_output and programs_output.plan_options
    
    if has_proposal:
        print("\n   📝 Programs Agent has proposed a plan.")
        print("   🔍 Policy Agent is critiquing the proposal...")
        print("      (Checking compliance with university policies)")
        
        # Policy agent critiques
        if "policy_compliance" not in agent_outputs:
            policy_output = policy_agent.execute(state)
            agent_outputs["policy_compliance"] = policy_output
            state["agent_outputs"] = agent_outputs
            
            print(f"\n   ✅ Policy Agent critique completed!")
            
            if policy_output.constraints:
                hard_constraints = [c for c in policy_output.constraints if c.hard]
                if hard_constraints:
                    print(f"\n   🔴 Hard Violations Found: {len(hard_constraints)}")
                    for constraint in hard_constraints[:2]:
                        print(f"      • {constraint.description[:70]}...")
                else:
                    soft_constraints = [c for c in policy_output.constraints if not c.hard]
                    if soft_constraints:
                        print(f"\n   🟡 Soft Constraints: {len(soft_constraints)}")
            
            if policy_output.risks:
                high_risks = [r for r in policy_output.risks if r.severity == "high"]
                if high_risks:
                    print(f"\n   ⚠️  High Risks Identified: {len(high_risks)}")
                    for risk in high_risks[:2]:
                        print(f"      • {risk.description[:70]}...")
    
    # Detect conflicts
    conflicts = coordinator.detect_conflicts(state)
    
    if conflicts:
        print(f"\n   ⚠️  Conflicts Detected: {len(conflicts)}")
        for i, conflict in enumerate(conflicts, 1):
            conflict_type = conflict.conflict_type.value.replace('_', ' ').title()
            icon = "🔴" if conflict.conflict_type == ConflictType.HARD_VIOLATION else "🟡" if conflict.conflict_type == ConflictType.HIGH_RISK else "🟢"
            print(f"\n   {icon} Conflict {i}: {conflict_type}")
            print(f"      Affected Agents: {', '.join(conflict.affected_agents)}")
            print(f"      Issue: {conflict.description[:70]}...")
        
        iteration = state.get("iteration_count", 0)
        if iteration < 3:
            print(f"\n   🔄 Negotiation Iteration {iteration + 1}/3")
            print("      Agents are working to resolve conflicts...")
        else:
            print("\n   ⚠️  Maximum iterations reached.")
            print("      User input may be needed to resolve conflicts.")
    else:
        print("\n   ✅ No conflicts detected!")
        print("      All agents agree on the recommendation.")
    
    time.sleep(1)
    return conflicts

def show_final_answer(state, answer):
    """Show the final synthesized answer."""
    print_section("STEP 4: Final Advisor Response", "💬")
    
    agent_outputs = state.get("agent_outputs", {})
    
    print("\n   🧠 Synthesizing answer from all agent contributions...")
    print("\n   Agents consulted:")
    for agent_name in agent_outputs.keys():
        output = agent_outputs[agent_name]
        agent_display = agent_name.replace('_', ' ').title()
        confidence_bar = "█" * int(output.confidence * 10)
        print(f"      • {agent_display}: {confidence_bar} ({output.confidence:.2f})")
    
    print("\n" + "=" * 80)
    print("💡 ADVISOR'S ANSWER")
    print("=" * 80)
    print()
    
    # Format and display answer
    formatted_answer = format_text(answer, indent="")
    print(formatted_answer)
    
    # Show any open questions
    open_questions = state.get("open_questions", [])
    if open_questions:
        print("\n" + "-" * 80)
        print("❓ Follow-up Questions:")
        for question in open_questions:
            print(f"   • {question}")
    
    print("\n" + "=" * 80)

def chat():
    """Main chat loop with enhanced workflow demonstration."""
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
            
            # Prepare initial state
            initial_state = {
                "user_query": user_input,
                "student_profile": {},
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
            
            # Step 1: Show intent classification
            intent, workflow = show_intent_classification(user_input)
            initial_state["active_agents"] = workflow
            initial_state["user_goal"] = intent.get("intent_type", "")
            
            # Step 2: Show agent execution
            print_section("STEP 2: Agent Execution", "🤖")
            
            # Execute agents in workflow order
            for agent_name in workflow:
                output = show_agent_execution(agent_name, initial_state)
                if output:
                    agent_outputs = initial_state.get("agent_outputs", {})
                    agent_outputs[agent_name] = output
                    initial_state["agent_outputs"] = agent_outputs
                    
                    # Update plan options if Programs agent
                    if agent_name == "programs_requirements" and output.plan_options:
                        initial_state["plan_options"] = output.plan_options
                    
                    # Update risks and constraints
                    initial_state["risks"] = initial_state.get("risks", []) + output.risks
                    initial_state["constraints"] = initial_state.get("constraints", []) + output.constraints
            
            # Step 3: Show negotiation
            conflicts = show_negotiation(initial_state)
            initial_state["conflicts"] = conflicts
            
            # Step 4: Synthesize and show final answer
            answer = coordinator.synthesize_answer(initial_state)
            show_final_answer(initial_state, answer)
            
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

