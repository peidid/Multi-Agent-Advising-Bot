"""
Interactive Chat Interface for Multi-Agent Academic Advising System
Talk to the system like you would talk to an academic advisor.
"""
from multi_agent import app
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage
import os

def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print welcome header."""
    print("=" * 70)
    print("🎓 CMU-Q Academic Advising Chatbot")
    print("=" * 70)
    print("\nI'm your multi-agent academic advisor. I can help you with:")
    print("  • Major/minor requirements")
    print("  • Course planning and scheduling")
    print("  • Policy questions")
    print("  • Degree progress")
    print("\nType 'quit' or 'exit' to end the conversation")
    print("Type 'clear' to clear the screen")
    print("Type 'help' for more information")
    print("-" * 70)
    print()

def print_help():
    """Print help information."""
    print("\n" + "=" * 70)
    print("HELP")
    print("=" * 70)
    print("\nExample questions you can ask:")
    print("  • 'What are the IS major requirements?'")
    print("  • 'Can I add a CS minor as an IS student?'")
    print("  • 'What courses should I take next semester?'")
    print("  • 'Can I take course overload?'")
    print("  • 'What is the policy on repeating courses?'")
    print("\nCommands:")
    print("  • 'quit' or 'exit' - End conversation")
    print("  • 'clear' - Clear screen")
    print("  • 'help' - Show this help message")
    print("=" * 70 + "\n")

def format_agent_status(agent_outputs):
    """Format agent execution status for display."""
    if not agent_outputs:
        return ""
    
    status_lines = []
    for agent_name, output in agent_outputs.items():
        # Format agent name nicely
        display_name = agent_name.replace("_", " ").title()
        confidence_bar = "█" * int(output.confidence * 10)
        status_lines.append(f"  ✓ {display_name}: {confidence_bar} ({output.confidence:.1f})")
    
    return "\n".join(status_lines)

def chat():
    """Main chat loop."""
    clear_screen()
    print_header()
    
    # Conversation state (for future: maintain history)
    conversation_history = []
    
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
            
            if user_input.lower() == 'help':
                print_help()
                continue
            
            # Process query through multi-agent system
            print("\n🤔 Thinking...")
            print("   (This may take a moment as I consult multiple specialized agents)")
            
            # Prepare state
            state = {
                "user_query": user_input,
                "student_profile": {},  # TODO: Load from user profile if available
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
            
            # Run through workflow
            result = app.invoke(state)
            
            # Display result
            print("\n" + "=" * 70)
            print("📋 ADVISOR RESPONSE")
            print("=" * 70)
            
            # Show which agents were consulted
            agent_outputs = result.get("agent_outputs", {})
            if agent_outputs:
                print("\n🔍 Agents Consulted:")
                print(format_agent_status(agent_outputs))
            
            # Show final answer
            messages = result.get("messages", [])
            if messages:
                final_message = messages[-1]
                if hasattr(final_message, 'content'):
                    answer = final_message.content
                else:
                    answer = str(final_message)
                
                print("\n💡 Answer:")
                print("-" * 70)
                # Print answer with proper word wrapping
                words = answer.split()
                line = ""
                for word in words:
                    if len(line + word) < 70:
                        line += word + " "
                    else:
                        print(line)
                        line = word + " "
                if line:
                    print(line)
            
            # Show any conflicts or open questions
            conflicts = result.get("conflicts", [])
            if conflicts:
                print("\n⚠️  Conflicts Detected:")
                for conflict in conflicts:
                    print(f"   • {conflict.description}")
            
            open_questions = result.get("open_questions", [])
            if open_questions:
                print("\n❓ Follow-up Questions:")
                for question in open_questions:
                    print(f"   • {question}")
            
            print("=" * 70)
            
            # Add to conversation history
            conversation_history.append({
                "user": user_input,
                "response": answer if messages else "No response generated"
            })
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Good luck with your studies!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try rephrasing your question or type 'help' for examples.")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    chat()

