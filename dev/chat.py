"""
Enhanced Interactive Chat with Real-Time Workflow Demonstration
Shows the actual multi-agent workflow including negotiation and collaboration.
Supports PARALLEL agent execution with visual feedback.
"""
# Allow running from dev/ — make the repo root importable
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress SSL warnings when SSL verification is disabled
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from multi_agent import app, coordinator, programs_agent, courses_agent, policy_agent, planning_agent, AGENT_REGISTRY, execute_single_agent
from blackboard.schema import WorkflowStep, ConflictType
from langchain_core.messages import HumanMessage, AIMessage
from config import print_model_config
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import time
from datetime import datetime
import threading

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(dev_mode=False):
    """Print welcome header."""
    print("=" * 80)
    if dev_mode:
        print("🔧 CMU-Q Academic Advising Chatbot - DEVELOPMENT MODE")
    else:
        print("🎓 CMU-Q Academic Advising Chatbot - Workflow Demonstration")
    print("=" * 80)
    print("\nThis interface shows how multiple agents collaborate in real-time.")
    print("\nYou'll see:")
    print("  • Intent classification")
    print("  • 🚀 PARALLEL agent execution (faster!)")
    print("  • Negotiation/collaboration process")
    print("  • Final human-like advisor response")
    
    if dev_mode:
        print("\n🔧 DEVELOPMENT MODE Commands:")
        print("  • @programs <query>  - Use only Programs Requirements Agent")
        print("  • @courses <query>   - Use only Course Scheduling Agent")
        print("  • @policy <query>    - Use only Policy Compliance Agent")
        print("  • @planning <query>  - Use only Academic Planning Agent")
        print("  • @all <query>       - Use all agents (bypass intent classification)")
        print("  • mode:normal        - Switch to normal mode")
    else:
        print("\n💡 Development Mode:")
        print("  • Type 'mode:dev' to enable manual agent selection")
    
    print("\n🧠 Coordination Mode:")
    print("  • LLM-Driven Coordination")
    print("    (Full LLM reasoning for dynamic workflow planning)")
    
    print("\n💬 Conversation Memory:")
    print("  • System remembers conversation history")
    print("  • You can refer to previous topics (e.g., 'it', 'that course')")
    print("  • Type 'clear' to reset conversation")
    
    print("\nType 'quit' to exit")
    print("-" * 80)
    print()
    # Show model configuration
    print_model_config()
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

def show_intent_classification(query, conversation_history=None, student_profile=None):
    """Show intent classification step with clarification support."""
    print_section("STEP 1: Intent Classification", "🎯")
    print(f"\n   Query: \"{query}\"")

    # Show conversation context if available
    if conversation_history and len(conversation_history) > 1:
        # Count previous turns (pairs of human + AI messages)
        num_previous_turns = (len(conversation_history) - 1) // 2
        print(f"   💭 Context: {num_previous_turns} previous turn(s) in conversation")

    print("\n   Analyzing query to determine which agents are needed...")

    # Track intent classification time
    intent_start = time.time()
    intent = coordinator.classify_intent(query, conversation_history, student_profile)
    intent_time = time.time() - intent_start
    print(f"\n   ⏱️  Intent classification took {intent_time:.2f}s")
    
    # Check if LLM-driven mode
    is_llm_driven = intent.get('mode') == 'llm_driven'
    
    # Check if clarification is needed (NEW)
    if intent.get('understanding', {}).get('requires_clarification'):
        show_clarification_needed(intent)
        clarification = get_user_clarification(intent)
        return intent, [], clarification, intent_time  # Return clarification data + timing
    
    if is_llm_driven:
        # Display LLM-driven analysis
        print(f"\n   🧠 LLM-Driven Coordination (Full Reasoning)")
        print(f"   📊 Priority: {intent.get('priority', 'high')}")
        
        if 'confidence' in intent:
            confidence = intent['confidence']
            confidence_bar = "█" * int(confidence * 10)
            print(f"   🎯 Confidence: {confidence_bar} ({confidence:.2f})")
        
        # Show understanding
        if 'understanding' in intent and intent['understanding']:
            understanding = intent['understanding']
            print(f"\n   🔍 Problem Understanding:")
            if understanding.get('student_goal'):
                print(f"      • Goal: {understanding['student_goal']}")
            if understanding.get('underlying_concern'):
                print(f"      • Concern: {understanding['underlying_concern']}")
        
        # Show goal
        if intent.get('goal'):
            print(f"\n   🎯 Coordination Goal:")
            print(f"      {intent['goal']}")
        
        print(f"\n   💭 Reasoning:")
        reasoning_lines = intent.get('reasoning', 'N/A').split('\n')
        for line in reasoning_lines[:10]:  # Show first 10 lines (increased from 5)
            if line.strip():
                print(f"      {line.strip()}")
        if len(reasoning_lines) > 10:
            print(f"      ... ({len(reasoning_lines) - 10} more lines)")
        
        # Show agent analysis
        if 'agent_analysis' in intent and intent['agent_analysis']:
            print(f"\n   🤖 Agent Analysis:")
            for agent_name, analysis in intent['agent_analysis'].items():  # Show all agents
                priority = analysis.get('priority', 'unknown')
                print(f"\n      • {agent_name}: {priority} priority")
                if analysis.get('reasoning'):
                    reasoning_text = analysis['reasoning']
                    # Show full reasoning, wrap at 120 chars
                    if len(reasoning_text) > 120:
                        print(f"        → {reasoning_text[:120]}")
                        print(f"          {reasoning_text[120:]}")
                    else:
                        print(f"        → {reasoning_text}")
    
    else:
        # Display rule-based analysis (enhanced or basic)
        print(f"\n   ✅ Intent Type: {intent.get('intent_type', 'unknown').replace('_', ' ').title()}")
        print(f"   📊 Priority: {intent.get('priority', 'medium')}")
        
        # Display confidence if available (enhanced classifier)
        if 'confidence' in intent:
            confidence = intent['confidence']
            confidence_bar = "█" * int(confidence * 10)
            print(f"   🎯 Confidence: {confidence_bar} ({confidence:.2f})")
        
        # Display extracted entities if available (enhanced classifier)
        if 'entities' in intent:
            entities = intent['entities']
            if any(entities.values()):  # If any entities found
                print(f"\n   🔍 Extracted Entities:")
                if entities.get('courses'):
                    print(f"      • Courses: {', '.join(entities['courses'])}")
                if entities.get('programs'):
                    print(f"      • Programs: {', '.join(entities['programs'])}")
                if entities.get('policies'):
                    print(f"      • Policies: {', '.join(entities['policies'])}")
                if entities.get('temporal'):
                    print(f"      • Time: {', '.join(entities['temporal'])}")
        
        print(f"\n   💭 Reasoning: {intent.get('reasoning', 'N/A')}")
        
        # Display clarification questions if needed
        if intent.get('needs_clarification'):
            print(f"\n   ⚠️  Clarification Needed:")
            for q in intent.get('clarification_questions', []):
                print(f"      • {q}")
    
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
    
    # Show decision points for LLM-driven
    if is_llm_driven and intent.get('decision_points'):
        print(f"\n   ⚙️  Decision Points:")
        for dp in intent['decision_points'][:2]:  # Show first 2
            print(f"      • After {dp.get('after_agent', 'unknown')}: {dp.get('check', '')[:60]}...")
    
    time.sleep(0.5)  # Reduced from 1s
    return intent, workflow, None, intent_time  # None = no clarification, + timing

def show_parallel_agent_execution(workflow, state):
    """
    Execute agents in PARALLEL and show real-time progress.
    Returns updated state with all agent outputs and execution metadata.
    """
    print_section("STEP 2: Parallel Agent Execution", "🚀")

    if not workflow:
        print("\n   ℹ️  No agents to execute.")
        return state, {}

    # Display which agents will run in parallel
    print(f"\n   ⚡ PARALLEL EXECUTION MODE")
    print(f"   {'-' * 60}")
    print(f"   Launching {len(workflow)} agents simultaneously:")
    for i, agent_name in enumerate(workflow, 1):
        agent_display = agent_name.replace('_', ' ').title()
        print(f"      {i}. {agent_display}")
    print(f"   {'-' * 60}")

    # Track execution
    execution_times = {}
    agent_outputs = {}
    completion_order = []
    all_risks = list(state.get("risks", []))
    all_constraints = list(state.get("constraints", []))
    plan_options = []

    # Start parallel execution
    print(f"\n   ⏳ All agents started at {datetime.now().strftime('%H:%M:%S')}")
    print(f"   {'=' * 60}")

    parallel_start = time.time()

    # Use ThreadPoolExecutor for parallel execution
    with ThreadPoolExecutor(max_workers=len(workflow)) as executor:
        # Submit all agents simultaneously
        future_to_agent = {
            executor.submit(execute_single_agent, agent_name, state): agent_name
            for agent_name in workflow
        }

        # Show progress as agents complete
        for future in as_completed(future_to_agent):
            agent_name, output, exec_time = future.result()
            completion_order.append(agent_name)

            if output is not None:
                agent_outputs[agent_name] = output
                execution_times[agent_name] = round(exec_time, 2)

                # Display completion
                agent_display = agent_name.replace('_', ' ').title()
                completion_num = len(completion_order)
                print(f"\n   ✅ [{completion_num}/{len(workflow)}] {agent_display} completed in {exec_time:.2f}s")
                print(f"      Confidence: {output.confidence:.2f}")

                # Show brief summary
                if output.relevant_policies:
                    print(f"      📚 Cited {len(output.relevant_policies)} policies")
                if output.risks:
                    print(f"      ⚠️  Identified {len(output.risks)} risks")
                if output.constraints:
                    print(f"      🚫 Found {len(output.constraints)} constraints")
                if output.plan_options:
                    print(f"      📋 Proposed {len(output.plan_options)} plan options")

                # Aggregate data
                all_risks.extend(output.risks)
                all_constraints.extend(output.constraints)
                if output.plan_options:
                    plan_options.extend(output.plan_options)

    parallel_total = time.time() - parallel_start
    sequential_total = sum(execution_times.values())
    speedup = sequential_total / parallel_total if parallel_total > 0 else 1.0

    # Show execution summary
    print(f"\n   {'=' * 60}")
    print(f"   🏁 PARALLEL EXECUTION COMPLETE")
    print(f"   {'=' * 60}")
    print(f"   ⏱️  Parallel Time:     {parallel_total:.2f}s (actual)")
    print(f"   ⏱️  Sequential Time:   {sequential_total:.2f}s (if run one-by-one)")
    print(f"   🚀 Speedup:           {speedup:.2f}x faster!")
    print(f"   📊 Completion Order:  {' → '.join([a.split('_')[0].title() for a in completion_order])}")

    # Build execution metadata
    execution_metadata = {
        "execution_mode": "parallel",
        "agents_executed": list(agent_outputs.keys()),
        "execution_times": execution_times,
        "total_execution_time": round(parallel_total, 2),
        "sequential_equivalent": round(sequential_total, 2),
        "parallel_speedup": round(speedup, 2),
        "completion_order": completion_order
    }

    # Update state
    state["agent_outputs"] = agent_outputs
    state["risks"] = all_risks
    state["constraints"] = all_constraints
    if plan_options:
        state["plan_options"] = plan_options
    state["execution_metadata"] = execution_metadata

    # Update phase timing
    phase_timing = state.get("phase_timing", {})
    phase_timing["parallel_agents"] = round(parallel_total, 2)
    phase_timing["parallel_agents_detail"] = execution_times
    state["phase_timing"] = phase_timing

    # Show detailed agent outputs
    print(f"\n   {'=' * 60}")
    print(f"   📋 DETAILED AGENT OUTPUTS")
    print(f"   {'=' * 60}")

    for agent_name, output in agent_outputs.items():
        show_agent_output_details(agent_name, output)

    return state, execution_metadata


def show_agent_output_details(agent_name, output):
    """Show detailed output from a single agent."""
    agent_display = agent_name.replace('_', ' ').title()
    print(f"\n   🤖 {agent_display}")
    print(f"   {'-' * 56}")

    # Show confidence
    confidence_bar = "█" * int(output.confidence * 10)
    print(f"      Confidence: {confidence_bar} ({output.confidence:.2f})")

    # Show policies cited
    if output.relevant_policies:
        print(f"\n      📚 Policies Cited: {len(output.relevant_policies)}")
        for i, policy in enumerate(output.relevant_policies[:3], 1):
            policy_short = policy[:80] + "..." if len(policy) > 80 else policy
            print(f"         {i}. {policy_short}")
        if len(output.relevant_policies) > 3:
            print(f"         ... and {len(output.relevant_policies) - 3} more")

    # Show answer preview
    answer_preview = output.answer[:500] + "..." if len(output.answer) > 500 else output.answer
    print(f"\n      💭 Contribution Preview:")
    for line in answer_preview.split('\n')[:6]:
        print(f"         {line[:75]}")

    # Show plan options if any
    if output.plan_options:
        print(f"\n      📋 Plan Options: {len(output.plan_options)}")
        for i, plan in enumerate(output.plan_options[:2], 1):
            courses_str = ', '.join(plan.courses[:5])
            if len(plan.courses) > 5:
                courses_str += f" (+{len(plan.courses) - 5} more)"
            print(f"         Option {i}: {courses_str}")

    # Show risks
    if output.risks:
        print(f"\n      ⚠️  Risks: {len(output.risks)}")
        for risk in output.risks[:2]:
            icon = "🔴" if risk.severity == "high" else "🟡"
            print(f"         {icon} [{risk.severity.upper()}] {risk.description[:60]}...")

    # Show constraints
    if output.constraints:
        print(f"\n      🚫 Constraints: {len(output.constraints)}")
        for constraint in output.constraints[:2]:
            icon = "🔴" if constraint.hard else "🟡"
            print(f"         {icon} {'[HARD]' if constraint.hard else '[SOFT]'} {constraint.description[:60]}...")


def show_agent_execution(agent_name, state):
    """Show single agent execution (used in dev mode or fallback)."""
    agent_display = agent_name.replace('_', ' ').title()
    print_subsection(f"Executing {agent_display} Agent", "🤖")

    # Map agent names to instances
    agents = {
        "programs_requirements": programs_agent,
        "course_scheduling": courses_agent,
        "policy_compliance": policy_agent,
        "academic_planning": planning_agent
    }

    if agent_name not in agents:
        print(f"   ⚠️  Unknown agent: {agent_name}")
        return None

    agent = agents[agent_name]
    print(f"   ⏳ {agent_display} is processing your query...")
    print(f"      (Retrieving domain-specific knowledge)")

    # Execute agent
    start_time = time.time()
    output = agent.execute(state)
    exec_time = time.time() - start_time

    # Display output
    print(f"\n   ✅ {agent_display} completed in {exec_time:.2f}s!")
    print(f"      Confidence: {output.confidence:.2f}")
    
    if output.relevant_policies:
        print(f"\n   📚 Policies Cited: {len(output.relevant_policies)}")
        for i, policy in enumerate(output.relevant_policies[:5], 1):  # Show first 5
            if len(policy) > 100:
                print(f"      {i}. {policy[:100]}")
                print(f"         {policy[100:]}")
            else:
                print(f"      {i}. {policy}")
        if len(output.relevant_policies) > 5:
            print(f"      ... and {len(output.relevant_policies) - 5} more")
    
    # Show longer answer preview (increased to 800 chars for better debugging)
    answer_preview = output.answer[:800] + "..." if len(output.answer) > 800 else output.answer
    print(f"\n   💭 Agent's Contribution:")
    print(format_text(answer_preview))
    
    # Show total length if truncated
    if len(output.answer) > 800:
        print(f"      (Total length: {len(output.answer)} chars, showing first 800)")
    
    # Show plan options if Programs agent or Planning agent
    if (agent_name in ["programs_requirements", "academic_planning"]) and output.plan_options:
        print(f"\n   📋 Plan Options Proposed: {len(output.plan_options)}")
        for i, plan in enumerate(output.plan_options[:3], 1):  # Show 3 options instead of 2
            # For academic planning agent, show semester structure
            if agent_name == "academic_planning" and hasattr(plan, 'semesters') and plan.semesters:
                print(f"      Option {i}: {len(plan.semesters)} semesters planned")
                print(f"         Total courses: {len(plan.courses)}")
                # Show first 2-3 semesters as preview
                for j, sem in enumerate(plan.semesters[:3], 1):
                    term = sem.get('term', f'Semester {j}')
                    sem_courses = sem.get('courses', [])
                    units = sem.get('total_units', 0)
                    print(f"         • {term}: {len(sem_courses)} courses ({units} units)")
                if len(plan.semesters) > 3:
                    print(f"         ... and {len(plan.semesters) - 3} more semesters")
            else:
                # Original display for programs agent
                courses_str = ', '.join(plan.courses[:8])  # Show 8 courses instead of 5
                if len(plan.courses) > 8:
                    courses_str += f" (+{len(plan.courses) - 8} more)"
                print(f"      Option {i}: {courses_str}")

            if hasattr(plan, 'confidence'):
                print(f"         Confidence: {plan.confidence:.2f}")
            if hasattr(plan, 'justification') and plan.justification:
                # Show first 200 chars of justification
                just = plan.justification[:200]
                if len(plan.justification) > 200:
                    just += "..."
                print(f"         Rationale: {just}")
            if hasattr(plan, 'description'):
                print(f"         Description: {plan.description}")
    
    # Show risks with full description
    if output.risks:
        print(f"\n   ⚠️  Risks Identified: {len(output.risks)}")
        for i, risk in enumerate(output.risks[:4], 1):  # Show 4 risks instead of 2
            severity_icon = "🔴" if risk.severity == "high" else "🟡" if risk.severity == "medium" else "🟢"
            print(f"      {i}. {severity_icon} [{risk.severity.upper()}] {risk.description}")  # Full description
            if hasattr(risk, 'type'):
                print(f"         Type: {risk.type}")
        if len(output.risks) > 4:
            print(f"      ... and {len(output.risks) - 4} more")
    
    # Show constraints with full description
    if output.constraints:
        print(f"\n   🚫 Constraints Found: {len(output.constraints)}")
        for i, constraint in enumerate(output.constraints[:4], 1):  # Show 4 constraints instead of 2
            hard_icon = "🔴" if constraint.hard else "🟡"
            print(f"      {i}. {hard_icon} {'[HARD]' if constraint.hard else '[SOFT]'} {constraint.description}")  # Full description
            if hasattr(constraint, 'source'):
                print(f"         Source: {constraint.source}")
        if len(output.constraints) > 4:
            print(f"      ... and {len(output.constraints) - 4} more")
    
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
                    for i, constraint in enumerate(hard_constraints[:4], 1):  # Show 4 instead of 2
                        print(f"      {i}. {constraint.description}")  # Full description
                        if hasattr(constraint, 'policy_citation') and constraint.policy_citation:
                            print(f"         Policy: {constraint.policy_citation}")
                    if len(hard_constraints) > 4:
                        print(f"      ... and {len(hard_constraints) - 4} more")
                else:
                    soft_constraints = [c for c in policy_output.constraints if not c.hard]
                    if soft_constraints:
                        print(f"\n   🟡 Soft Constraints: {len(soft_constraints)}")
                        for i, constraint in enumerate(soft_constraints[:3], 1):
                            print(f"      {i}. {constraint.description}")  # Full description
            
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
            print(f"      Description: {conflict.description}")  # Full description, no truncation
            if conflict.options:
                print(f"      Options Available: {len(conflict.options)}")
        
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

def show_clarification_needed(intent):
    """Display clarification request to user."""
    clarification_info = intent.get('understanding', {})
    questions = clarification_info.get('clarification_questions', [])
    reasoning = clarification_info.get('clarification_reasoning', '')
    missing = clarification_info.get('missing_information', [])
    
    print("\n" + "=" * 80)
    print("❓ CLARIFICATION NEEDED")
    print("=" * 80)
    
    print(f"\n   🤔 Why I need to ask:")
    print(f"      {reasoning}")
    
    if missing:
        print(f"\n   📋 Missing information: {', '.join(missing)}")
    
    print(f"\n   💡 To give you an accurate answer, I need to know:")

def get_user_clarification(intent):
    """Get clarification from user interactively."""
    clarification_info = intent.get('understanding', {})
    questions = clarification_info.get('clarification_questions', [])
    
    if not questions:
        return None
    
    print("\n" + "-" * 80)
    
    responses = {}
    for i, q in enumerate(questions, 1):
        print(f"\n   {i}. {q.get('question', 'Please provide information')}")
        if q.get('why'):
            print(f"      → {q.get('why')}")
        
        if q.get('note'):
            print(f"      ⚠️  {q.get('note')}")
        
        if q.get('options'):
            print(f"      Options: {', '.join(q.get('options'))}")
        
        answer = input(f"\n      Your answer: ").strip()
        
        if answer:
            q_type = q.get('type', f'question_{i}')
            
            # Normalize ambiguous answers
            if q_type == 'major':
                answer = normalize_major_name(answer)
            
            responses[q_type] = answer
    
    print("\n   ✅ Thank you! Now I can provide an accurate answer.")
    print("=" * 80)
    
    return responses

def normalize_major_name(answer: str) -> str:
    """
    Normalize major name to full official name.
    
    Handles common abbreviations and variations.
    """
    answer_lower = answer.lower().strip()
    
    # Common abbreviations
    mapping = {
        'cs': 'Computer Science',
        'computer science': 'Computer Science',
        'is': 'Information Systems',
        'information systems': 'Information Systems',
        'info systems': 'Information Systems',
        'bio': 'Biological Sciences',
        'biology': 'Biological Sciences',
        'biological sciences': 'Biological Sciences',
        'bs': 'Biological Sciences',  # Assuming BS = Biological Sciences in biology context
        'ba': 'Business Administration',
        'business': 'Business Administration',
        'business administration': 'Business Administration',
    }
    
    if answer_lower in mapping:
        return mapping[answer_lower]
    
    # Return original if no mapping found
    return answer

def show_final_answer(state, answer):
    """Show the final synthesized answer with details."""
    print_section("STEP 4: Final Answer Synthesis", "💬")
    
    agent_outputs = state.get("agent_outputs", {})
    
    print("\n   🧠 Coordinator is synthesizing final answer...")
    print("      • Combining insights from all agents")
    print("      • Resolving any remaining conflicts")
    print("      • Formatting for student readability")
    print("      • Adding policy citations")
    
    print(f"\n   {'='*76}")
    print(f"   📊 AGENT CONTRIBUTIONS SUMMARY")
    print(f"   {'='*76}")
    
    print("\n   Agents Consulted:")
    total_policies = 0
    total_risks = 0
    total_constraints = 0
    
    for agent_name in agent_outputs.keys():
        output = agent_outputs[agent_name]
        agent_display = agent_name.replace('_', ' ').title()
        confidence_bar = "█" * int(output.confidence * 10)
        print(f"\n      🤖 {agent_display}")
        print(f"         Confidence: {confidence_bar} ({output.confidence:.2f})")
        print(f"         Policies Cited: {len(output.relevant_policies)}")
        print(f"         Risks Identified: {len(output.risks)}")
        print(f"         Constraints: {len(output.constraints)}")
        
        total_policies += len(output.relevant_policies)
        total_risks += len(output.risks)
        total_constraints += len(output.constraints)
    
    print(f"\n   📈 Overall Statistics:")
    print(f"      • Total Agents: {len(agent_outputs)}")
    print(f"      • Total Policies: {total_policies}")
    print(f"      • Total Risks: {total_risks}")
    print(f"      • Total Constraints: {total_constraints}")
    
    print("\n" + "=" * 80)
    print("💡 FINAL ADVISOR RESPONSE")
    print("=" * 80)
    print()
    
    # Display answer with markdown formatting preserved
    # The answer is already formatted by the LLM with markdown
    print(answer)
    print()
    
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
    dev_mode = False
    print_header(dev_mode)
    
    # Initialize conversation memory (persistent across queries)
    conversation_messages = []
    
    # Initialize student profile (persistent across queries)
    student_profile = {}
    
    while True:
        try:
            # Get user input
            prompt = "💬 You: " if not dev_mode else "🔧 Dev: "
            user_input = input(f"\n{prompt}").strip()
            
            if not user_input:
                continue
            
            # Handle mode switching
            if user_input.lower() == 'mode:dev':
                dev_mode = True
                clear_screen()
                print_header(dev_mode)
                print("\n✅ Development mode enabled! You can now manually select agents.")
                continue
            
            if user_input.lower() == 'mode:normal':
                dev_mode = False
                clear_screen()
                print_header(dev_mode)
                print("\n✅ Normal mode enabled! Intent classification will run automatically.")
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye! Good luck with your studies!")
                break
            
            if user_input.lower() == 'clear':
                clear_screen()
                print_header(dev_mode)
                # Also clear conversation history
                conversation_messages = []
                print("🧹 Conversation history cleared.\n")
                continue
            
            # Start timing (exclude clarification interaction time)
            processing_start_time = time.time()
            
            # Handle manual agent selection in dev mode
            manual_agents = None
            actual_query = user_input
            
            if dev_mode:
                if user_input.startswith('@programs '):
                    manual_agents = ['programs_requirements']
                    actual_query = user_input[10:].strip()
                    print(f"\n🔧 Manual agent selection: Programs Requirements Agent")
                elif user_input.startswith('@courses '):
                    manual_agents = ['course_scheduling']
                    actual_query = user_input[9:].strip()
                    print(f"\n🔧 Manual agent selection: Course Scheduling Agent")
                elif user_input.startswith('@policy '):
                    manual_agents = ['policy_compliance']
                    actual_query = user_input[8:].strip()
                    print(f"\n🔧 Manual agent selection: Policy Compliance Agent")
                elif user_input.startswith('@planning '):
                    manual_agents = ['academic_planning']
                    actual_query = user_input[10:].strip()
                    print(f"\n🔧 Manual agent selection: Academic Planning Agent")
                elif user_input.startswith('@all '):
                    manual_agents = ['programs_requirements', 'course_scheduling', 'policy_compliance', 'academic_planning']
                    actual_query = user_input[5:].strip()
                    print(f"\n🔧 Manual agent selection: All Agents")
                
                if not actual_query:
                    print("⚠️  Please provide a query after the agent selector.")
                    continue
            
            # Add current query to conversation history
            conversation_messages.append(HumanMessage(content=actual_query))
            
            # Prepare initial state (with full conversation history)
            initial_state = {
                "user_query": actual_query,
                "student_profile": student_profile,  # Use persistent profile
                "agent_outputs": {},
                "constraints": [],
                "risks": [],
                "plan_options": [],
                "conflicts": [],
                "open_questions": [],
                "messages": conversation_messages.copy(),  # Full conversation history
                "active_agents": [],
                "workflow_step": WorkflowStep.INITIAL,
                "iteration_count": 0,
                "next_agent": None,
                "user_goal": None,
                "execution_metadata": None,  # Will be populated by parallel execution
                "phase_timing": {}  # Will track timing for each phase
            }
            
            # Step 1: Intent classification (skip if manual agents selected)
            if manual_agents:
                print(f"\n   Query: \"{actual_query}\"")
                print(f"   🔧 Skipping intent classification (manual mode)")
                workflow = manual_agents
                initial_state["user_goal"] = "manual_selection"
            else:
                # Pass conversation history to classifier
                conversation_history = [
                    {"role": msg.type, "content": msg.content}
                    for msg in initial_state.get("messages", [])
                ]
                intent, workflow, clarification, intent_time = show_intent_classification(
                    actual_query, conversation_history, student_profile
                )
                initial_state["phase_timing"]["intent_classification"] = intent_time
                
                # Handle clarification if needed (with max retry limit)
                clarification_retries = 0
                max_clarification_retries = 1  # Only allow ONE round of clarification
                
                while clarification and clarification_retries < max_clarification_retries:
                    # Pause timing during clarification (user interaction time)
                    clarification_pause_start = time.time()
                    
                    # Update student profile with clarification
                    student_profile.update(clarification)
                    initial_state["student_profile"] = student_profile
                    
                    # Add clarification Q&A to conversation history (FIXED)
                    # 1. Add the clarification questions as AI message
                    clarification_questions = intent.get('understanding', {}).get('clarification_questions', [])
                    if clarification_questions:
                        questions_text = "\n".join([
                            f"Q: {q.get('question', '')} (Why: {q.get('why', '')})"
                            for q in clarification_questions
                        ])
                        conversation_messages.append(AIMessage(content=f"I need clarification:\n{questions_text}"))
                    
                    # 2. Add the user's answers as Human message
                    answers_text = ", ".join([f"{k}: {v}" for k, v in clarification.items()])
                    conversation_messages.append(HumanMessage(content=answers_text))
                    
                    # 3. Add acknowledgment as AI message
                    conversation_messages.append(AIMessage(content=f"Thank you! I now understand you are: {answers_text}"))
                    
                    # Resume timing after clarification
                    clarification_pause_duration = time.time() - clarification_pause_start
                    processing_start_time += clarification_pause_duration  # Adjust start time to exclude clarification
                    
                    # Re-classify with updated profile and FULL conversation history
                    print("\n   🔄 Re-analyzing with clarification...")
                    conversation_history = [
                        {"role": msg.type, "content": msg.content}
                        for msg in conversation_messages
                    ]
                    intent, workflow, clarification, intent_time = show_intent_classification(
                        actual_query, conversation_history, student_profile
                    )
                    initial_state["phase_timing"]["intent_classification"] = intent_time

                    clarification_retries += 1
                
                # If still needs clarification after max retries, proceed anyway
                if clarification and clarification_retries >= max_clarification_retries:
                    print("\n   ⚠️  Proceeding with available information...")
                    workflow = intent.get('required_agents', [])
                    
                    # If still no workflow after max retries, use general knowledge
                    if not workflow:
                        print("\n   ℹ️  No specific agents identified. Using general knowledge to respond.")
                
                initial_state["user_goal"] = intent.get("intent_type", "")
            
            initial_state["active_agents"] = workflow
            
            # If no workflow, skip agent execution and go to synthesis
            if not workflow:
                print("\n   ℹ️  No specific agents needed. Using general knowledge to respond.")
                # Skip agent execution and negotiation, go directly to answer synthesis
            else:
                # Step 2: Execute agents (PARALLEL or sequential based on mode)
                if dev_mode and manual_agents and len(manual_agents) == 1:
                    # Single agent in dev mode - use sequential execution
                    print_section("STEP 2: Agent Execution (Single Agent)", "🤖")
                    for agent_name in workflow:
                        output = show_agent_execution(agent_name, initial_state)
                        if output:
                            agent_outputs = initial_state.get("agent_outputs", {})
                            agent_outputs[agent_name] = output
                            initial_state["agent_outputs"] = agent_outputs

                            if agent_name == "programs_requirements" and output.plan_options:
                                initial_state["plan_options"] = output.plan_options

                            initial_state["risks"] = initial_state.get("risks", []) + output.risks
                            initial_state["constraints"] = initial_state.get("constraints", []) + output.constraints
                else:
                    # Multiple agents - use PARALLEL execution
                    initial_state, exec_metadata = show_parallel_agent_execution(workflow, initial_state)

                # Step 3: Show negotiation
                conflicts = show_negotiation(initial_state)
                initial_state["conflicts"] = conflicts
            
            # Step 4: Synthesize and show final answer
            synthesis_start = time.time()
            answer = coordinator.synthesize_answer(initial_state)
            synthesis_time = time.time() - synthesis_start
            initial_state["phase_timing"]["synthesis"] = round(synthesis_time, 2)

            # Calculate total phase timing
            phase_timing = initial_state.get("phase_timing", {})
            phase_timing["total"] = round(sum(v for k, v in phase_timing.items() if isinstance(v, (int, float)) and k != "total"), 2)

            show_final_answer(initial_state, answer)
            
            # Calculate and display processing time
            processing_end_time = time.time()
            total_processing_time = processing_end_time - processing_start_time

            print("\n" + "=" * 80)
            print(f"⏱️  PROCESSING TIME & PERFORMANCE")
            print("=" * 80)
            print(f"\n   Total Processing Time: {total_processing_time:.2f} seconds")
            print(f"   (Excludes user clarification interaction time)")

            # Show phase timing breakdown
            phase_timing = initial_state.get("phase_timing", {})
            if phase_timing:
                print(f"\n   📊 PHASE TIMING BREAKDOWN:")
                if "intent_classification" in phase_timing:
                    print(f"      • Intent Classification: {phase_timing['intent_classification']:.2f}s")
                if "parallel_agents" in phase_timing:
                    print(f"      • Parallel Agents:       {phase_timing['parallel_agents']:.2f}s")
                if "synthesis" in phase_timing:
                    print(f"      • Synthesis:             {phase_timing['synthesis']:.2f}s")

            # Show parallel execution details if available
            exec_metadata = initial_state.get("execution_metadata")
            if exec_metadata and exec_metadata.get("execution_mode") == "parallel":
                print(f"\n   🚀 PARALLEL EXECUTION STATS:")
                print(f"      • Agents Run:        {len(exec_metadata.get('agents_executed', []))}")
                print(f"      • Parallel Time:     {exec_metadata.get('total_execution_time', 0):.2f}s")
                print(f"      • Sequential Equiv:  {exec_metadata.get('sequential_equivalent', 0):.2f}s")
                speedup = exec_metadata.get('parallel_speedup', 1.0)
                if speedup > 1.5:
                    print(f"      • Speedup Factor:    {speedup:.2f}x 🔥")
                else:
                    print(f"      • Speedup Factor:    {speedup:.2f}x")
                time_saved = exec_metadata.get('sequential_equivalent', 0) - exec_metadata.get('total_execution_time', 0)
                if time_saved > 0:
                    print(f"      • Time Saved:        {time_saved:.2f}s")

            # Break down if time is significant
            if total_processing_time > 60:
                minutes = int(total_processing_time // 60)
                seconds = total_processing_time % 60
                print(f"\n   = {minutes} minute(s) and {seconds:.2f} seconds")

            # Performance indicator
            if total_processing_time < 30:
                print(f"\n   ✅ Fast response")
            elif total_processing_time < 60:
                print(f"\n   ⚠️  Moderate response time")
            else:
                print(f"\n   🐌 Slow response - consider using faster model")

            print("\n" + "=" * 80)
            
            # Add AI response to conversation history
            conversation_messages.append(AIMessage(content=answer))
            
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

