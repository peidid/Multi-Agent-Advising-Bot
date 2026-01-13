"""
Quick verification script to check that model configuration is working correctly.
"""
from coordinator.coordinator import Coordinator
from agents.programs_agent import ProgramsRequirementsAgent
from agents.courses_agent import CourseSchedulingAgent
from agents.policy_agent import PolicyComplianceAgent
from config import (
    get_coordinator_model, 
    get_agent_model,
    print_model_config
)

def verify_models():
    """Verify that all components are using the correct models."""
    print("=" * 70)
    print("Model Configuration Verification")
    print("=" * 70)
    print()
    
    # Print expected configuration
    print_model_config()
    print()
    
    # Verify Coordinator
    print("🔍 Verifying Coordinator...")
    coordinator = Coordinator()
    coordinator_model = coordinator.llm.model_name if hasattr(coordinator.llm, 'model_name') else str(coordinator.llm)
    expected_coordinator = get_coordinator_model()
    print(f"   Expected: {expected_coordinator}")
    print(f"   Actual: {coordinator_model}")
    if expected_coordinator in str(coordinator_model):
        print("   ✅ Coordinator model configured correctly")
    else:
        print("   ⚠️  Coordinator model mismatch!")
    print()
    
    # Verify Agents
    print("🔍 Verifying Agents...")
    agents = [
        ("Programs Agent", ProgramsRequirementsAgent()),
        ("Courses Agent", CourseSchedulingAgent()),
        ("Policy Agent", PolicyComplianceAgent())
    ]
    
    expected_agent = get_agent_model()
    all_correct = True
    
    for agent_name, agent in agents:
        agent_model = agent.llm.model_name if hasattr(agent.llm, 'model_name') else str(agent.llm)
        print(f"   {agent_name}:")
        print(f"      Expected: {expected_agent}")
        print(f"      Actual: {agent_model}")
        if expected_agent in str(agent_model):
            print(f"      ✅ {agent_name} model configured correctly")
        else:
            print(f"      ⚠️  {agent_name} model mismatch!")
            all_correct = False
        print()
    
    # Summary
    print("=" * 70)
    if all_correct and expected_coordinator in str(coordinator_model):
        print("✅ All models configured correctly!")
    else:
        print("⚠️  Some models may not be configured correctly. Check the output above.")
    print("=" * 70)

if __name__ == "__main__":
    verify_models()
