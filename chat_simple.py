"""
Simple Interactive Chat Interface
A simpler version without fancy formatting.
"""
from multi_agent import app
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

def main():
    print("=" * 70)
    print("CMU-Q Academic Advising Chatbot")
    print("Type 'quit' to exit")
    print("=" * 70)
    print()
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not user_input:
            continue
        
        print("Thinking...")
        
        # Prepare state
        state = {
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
        
        # Run workflow
        result = app.invoke(state)
        
        # Display answer
        messages = result.get("messages", [])
        if messages:
            answer = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
            print("\nAdvisor:", answer)
            print()
        else:
            print("No response generated.\n")

if __name__ == "__main__":
    main()

