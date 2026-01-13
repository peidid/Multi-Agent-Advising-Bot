"""
Test script for interactive clarification feature
"""

from coordinator.clarification_handler import ClarificationHandler
from langchain_openai import ChatOpenAI
from config import get_coordinator_model, get_coordinator_temperature

# Initialize
llm = ChatOpenAI(
    model=get_coordinator_model(),
    temperature=get_coordinator_temperature()
)
handler = ClarificationHandler(llm)

# Test cases
test_cases = [
    {
        "name": "Ambiguous - No major specified",
        "query": "Do I need to take 15-122 for my degree?",
        "profile": {},
        "expected": "needs_clarification=True"
    },
    {
        "name": "Clear - Major specified in query",
        "query": "As a CS student, do I need to take 15-122?",
        "profile": {},
        "expected": "needs_clarification=False"
    },
    {
        "name": "Clear - Major in profile",
        "query": "Do I need to take 15-122?",
        "profile": {"major": "Computer Science"},
        "expected": "needs_clarification=False"
    },
    {
        "name": "Ambiguous - Multiple missing items",
        "query": "Can I graduate on time?",
        "profile": {},
        "expected": "needs_clarification=True"
    },
    {
        "name": "Clear - General course info",
        "query": "What are the prerequisites for 15-213?",
        "profile": {},
        "expected": "needs_clarification=False"
    },
]

print("=" * 80)
print("TESTING CLARIFICATION FEATURE")
print("=" * 80)

for i, test in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"Test {i}: {test['name']}")
    print(f"{'='*80}")
    print(f"Query: \"{test['query']}\"")
    print(f"Profile: {test['profile']}")
    print(f"Expected: {test['expected']}")
    
    try:
        result = handler.check_for_clarification(
            test['query'],
            [],
            test['profile']
        )
        
        print(f"\n✅ Result:")
        print(f"   Needs Clarification: {result.get('needs_clarification')}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')}")
        
        if result.get('needs_clarification'):
            print(f"   Missing Info: {result.get('missing_info', [])}")
            print(f"   Questions ({len(result.get('questions', []))}):")
            for q in result.get('questions', []):
                print(f"      • {q.get('question')}")
                print(f"        Why: {q.get('why')}")
        
        # Check if result matches expectation
        expected_needs = "True" in test['expected']
        actual_needs = result.get('needs_clarification', False)
        
        if expected_needs == actual_needs:
            print(f"\n   ✅ PASS - Matches expectation")
        else:
            print(f"\n   ❌ FAIL - Does not match expectation")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

print(f"\n{'='*80}")
print("TESTING COMPLETE")
print(f"{'='*80}")
