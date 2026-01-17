"""
Test script for Academic Planning Agent

Tests the multi-semester course planning functionality.
"""

from multi_agent import app
from langchain_core.messages import HumanMessage
from blackboard.schema import WorkflowStep

def test_planning_query(query: str, profile: dict = None):
    """Test a planning query."""

    if profile is None:
        profile = {
            "major": ["Computer Science"],
            "current_semester": "Second-Year Fall",
            "completed_courses": [
                "15-112", "15-122", "21-120", "21-122", "21-127",
                "76-100", "76-101", "07-129", "99-101"
            ],
            "gpa": 3.5
        }

    initial_state = {
        "user_query": query,
        "student_profile": profile,
        "agent_outputs": {},
        "constraints": [],
        "risks": [],
        "plan_options": [],
        "conflicts": [],
        "open_questions": [],
        "messages": [HumanMessage(content=query)],
        "active_agents": [],
        "workflow_step": WorkflowStep.INITIAL,
        "iteration_count": 0,
        "next_agent": None,
        "user_goal": None
    }

    print("=" * 80)
    print("TESTING ACADEMIC PLANNING")
    print("=" * 80)
    print(f"\nQuery: {query}")
    print(f"Student Profile: {profile.get('major')} - {profile.get('current_semester')}")
    print(f"Completed: {len(profile.get('completed_courses', []))} courses")
    print("\n" + "=" * 80)
    print("RUNNING MULTI-AGENT SYSTEM...")
    print("=" * 80 + "\n")

    result = app.invoke(initial_state)

    print("\n" + "=" * 80)
    print("FINAL ANSWER:")
    print("=" * 80)
    print(result["messages"][-1].content)

    # Show which agents were activated
    print("\n" + "=" * 80)
    print("AGENTS ACTIVATED:")
    print("=" * 80)
    for agent_name in result.get("agent_outputs", {}).keys():
        print(f"  ✓ {agent_name}")

    # Show plan options if any
    if result.get("plan_options"):
        print("\n" + "=" * 80)
        print("PLAN OPTIONS GENERATED:")
        print("=" * 80)
        for i, plan in enumerate(result.get("plan_options", []), 1):
            print(f"\nPlan {i}:")
            print(f"  Description: {plan.description}")
            print(f"  Courses: {', '.join(plan.courses[:10])}...")

    # Show risks if any
    if result.get("risks"):
        print("\n" + "=" * 80)
        print("IDENTIFIED RISKS:")
        print("=" * 80)
        for risk in result.get("risks", []):
            print(f"  ⚠ {risk.description} (severity: {risk.severity})")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")

    return result


if __name__ == "__main__":
    # Test 1: Basic semester planning
    print("\n\n" + "🔬 TEST 1: Plan remaining semesters to graduation" + "\n")
    test_planning_query(
        "Can you help me plan what courses to take each semester until graduation?"
    )

    # Test 2: Planning with minor
    print("\n\n" + "🔬 TEST 2: Planning with Business minor" + "\n")
    test_planning_query(
        "I want to add a Business Administration minor. Can you create a semester-by-semester plan that includes it?"
    )

    # Test 3: Accelerated graduation
    print("\n\n" + "🔬 TEST 3: Accelerated graduation plan" + "\n")
    test_planning_query(
        "I want to graduate in 3.5 years instead of 4. Can you make a plan for that?"
    )

    # Test 4: Starting freshman
    print("\n\n" + "🔬 TEST 4: Complete 4-year plan for new student" + "\n")
    test_planning_query(
        "I'm a new IS student. What courses should I take each semester for the next 4 years?",
        profile={
            "major": ["Information Systems"],
            "current_semester": "First-Year Fall",
            "completed_courses": [],
            "gpa": None
        }
    )
