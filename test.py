"""
Automated Testing Script for AdvisingBot

Reads questions from in.txt and processes them through the multi-agent system.
Saves results to:
- out.txt: Questions and final answers only
- out_raw.txt: Questions and all processing information
"""

import sys
import io
from langchain_core.messages import HumanMessage, AIMessage

# Import components from chat.py
from multi_agent import app, coordinator, programs_agent, courses_agent, policy_agent
from blackboard.schema import WorkflowStep
from chat import (
    print_section, show_intent_classification, show_agent_execution,
    show_negotiation, show_final_answer, get_user_clarification,
    show_clarification_needed
)


class TeeOutput:
    """Capture stdout while still printing to console"""
    def __init__(self):
        self.terminal = sys.stdout
        self.log = io.StringIO()
    
    def write(self, message):
        self.terminal.write(message)
        self.terminal.flush()  # Ensure immediate display
        self.log.write(message)
    
    def flush(self):
        self.terminal.flush()
    
    def getvalue(self):
        return self.log.getvalue()
    
    def isatty(self):
        """Required for input() to work correctly"""
        return self.terminal.isatty()

def process_question(question: str, conversation_messages: list, student_profile: dict):
    """
    Process a single question through the multi-agent system.
    
    Returns:
        tuple: (final_answer, raw_output)
    """
    # Use TeeOutput to capture stdout while still allowing console interaction
    tee = TeeOutput()
    original_stdout = sys.stdout
    
    try:
        # Redirect stdout to TeeOutput
        sys.stdout = tee
        
        print("=" * 80)
        print(f"💬 You: {question}")
        print("=" * 80)
        
        # Add current query to conversation history
        conversation_messages.append(HumanMessage(content=question))
        
        # Prepare initial state
        initial_state = {
                "user_query": question,
                "student_profile": student_profile,
                "agent_outputs": {},
                "constraints": [],
                "risks": [],
                "plan_options": [],
                "conflicts": [],
                "open_questions": [],
                "messages": conversation_messages.copy(),
                "active_agents": [],
                "workflow_step": WorkflowStep.INITIAL,
                "iteration_count": 0,
                "next_agent": None,
                "user_goal": None
        }
        
        # Step 1: Intent classification
        conversation_history = [
            {"role": msg.type, "content": msg.content}
            for msg in initial_state.get("messages", [])
        ]
        intent, workflow, clarification = show_intent_classification(
            question, conversation_history, student_profile
        )
        
        # Handle clarification if needed (with max retry limit)
        clarification_retries = 0
        max_clarification_retries = 1
        
        while clarification and clarification_retries < max_clarification_retries:
            # Update student profile with clarification
            student_profile.update(clarification)
            initial_state["student_profile"] = student_profile
            
            # Add clarification Q&A to conversation history
            clarification_questions = intent.get('understanding', {}).get('clarification_questions', [])
            if clarification_questions:
                questions_text = "\n".join([
                    f"Q: {q.get('question', '')} (Why: {q.get('why', '')})"
                    for q in clarification_questions
                ])
                conversation_messages.append(AIMessage(content=f"I need clarification:\n{questions_text}"))
            
            # Add user's answers as Human message
            answers_text = ", ".join([f"{k}: {v}" for k, v in clarification.items()])
            conversation_messages.append(HumanMessage(content=answers_text))
            
            # Add acknowledgment as AI message
            conversation_messages.append(AIMessage(content=f"Thank you! I now understand you are: {answers_text}"))
            
            # Re-classify with updated profile
            print("\n   🔄 Re-analyzing with clarification...")
            conversation_history = [
                {"role": msg.type, "content": msg.content}
                for msg in conversation_messages
            ]
            
            # Call show_intent_classification normally (without skip_clarification)
            intent, workflow, clarification = show_intent_classification(
                question, conversation_history, student_profile
            )
            
            clarification_retries += 1
        
        # If still needs clarification after max retries, proceed anyway
        if clarification and clarification_retries >= max_clarification_retries:
            print("\n   ⚠️  Proceeding with available information...")
            workflow = intent.get('required_agents', [])
        
        initial_state["user_goal"] = intent.get("intent_type", "")
        initial_state["active_agents"] = workflow
        
        # Skip agent execution if no agents (clarification-only case)
        if not workflow:
            print("\n⚠️  Waiting for clarification before proceeding to agents.")
            return None, tee.getvalue()
        
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
        
        # Add AI response to conversation history
        conversation_messages.append(AIMessage(content=answer))
        
        # Get captured output
        captured_output = tee.getvalue()
        
        return answer, captured_output
        
    except Exception as e:
        error_msg = f"\n❌ Error processing question: {str(e)}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        # Get captured output including error
        captured_output = tee.getvalue() + error_msg
        
        return None, captured_output
    
    finally:
        # Always restore stdout
        sys.stdout = original_stdout


def run_tests():
    """Run tests from in.txt and save results."""
    print("=" * 80)
    print("🧪 AUTOMATED TESTING MODE")
    print("=" * 80)
    print("\nReading questions from in.txt...")
    
    # Read questions
    try:
        with open("in.txt", "r", encoding="utf-8") as f:
            questions = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("❌ Error: in.txt not found!")
        return
    
    print(f"✅ Found {len(questions)} questions to process\n")
    
    # Initialize conversation state
    conversation_messages = []
    student_profile = {}
    
    # Results storage
    results = []  # For out.txt (Q&A only)
    raw_outputs = []  # For out_raw.txt (full processing info)
    
    # Process each question
    for i, question in enumerate(questions, 1):
        print(f"\n{'=' * 80}")
        print(f"Processing Question {i}/{len(questions)}")
        print(f"{'=' * 80}")
        print(f"Q: {question}\n")
        
        answer, raw_output = process_question(question, conversation_messages, student_profile)
        
        if answer:
            print(f"\n✅ Answer: {answer[:100]}..." if len(answer) > 100 else f"\n✅ Answer: {answer}")
            
            # Store for out.txt
            results.append({
                'question': question,
                'answer': answer
            })
        else:
            print(f"\n⚠️  No answer generated (may need clarification)")
            
            # Store empty answer
            results.append({
                'question': question,
                'answer': "[No answer generated - clarification needed]"
            })
        
        # Store for out_raw.txt
        raw_outputs.append({
            'question': question,
            'raw_output': raw_output
        })
        
        print(f"\n{'=' * 80}\n")
    
    # Write out.txt (Q&A only)
    print("Writing results to out.txt...")
    with open("out.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("ADVISING BOT TEST RESULTS - FINAL ANSWERS ONLY\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"Question {i}:\n")
            f.write(f"{result['question']}\n\n")
            f.write(f"Answer:\n")
            f.write(f"{result['answer']}\n")
            f.write("\n" + "-" * 80 + "\n\n")
    
    print("✅ out.txt written")
    
    # Write out_raw.txt (full processing info)
    print("Writing detailed logs to out_raw.txt...")
    with open("out_raw.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("ADVISING BOT TEST RESULTS - FULL PROCESSING LOGS\n")
        f.write("=" * 80 + "\n\n")
        
        for i, result in enumerate(raw_outputs, 1):
            f.write(f"\n{'=' * 80}\n")
            f.write(f"QUESTION {i}\n")
            f.write(f"{'=' * 80}\n")
            f.write(f"{result['question']}\n\n")
            f.write(result['raw_output'])
            f.write(f"\n{'=' * 80}\n\n")
    
    print("✅ out_raw.txt written")
    
    # Summary
    print("\n" + "=" * 80)
    print("🎉 TESTING COMPLETE")
    print("=" * 80)
    print(f"\nProcessed: {len(questions)} questions")
    print(f"Successful: {sum(1 for r in results if r['answer'] and '[No answer' not in r['answer'])}")
    print(f"\nResults saved to:")
    print(f"  - out.txt (final answers only)")
    print(f"  - out_raw.txt (full processing logs)")
    print("\n")


if __name__ == "__main__":
    try:
        run_tests()
    except KeyboardInterrupt:
        print("\n\n👋 Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
