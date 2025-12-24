from agents.programs_agent import ProgramsRequirementsAgent
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

agent = ProgramsRequirementsAgent()
state = {
    "user_query": "What are IS requirements?",
    "student_profile": {},
    "agent_outputs": {},
    "constraints": [],
    "risks": [],
    "plan_options": [],
    "conflicts": [],
    "open_questions": [],
    "messages": [HumanMessage(content="test")],
    "active_agents": [],
    "workflow_step": WorkflowStep.INITIAL,
    "iteration_count": 0,
    "next_agent": None,
    "user_goal": None
}

output = agent.execute(state)
print(f"Works, Answer: {output.answer[:100]}...")

from coordinator.coordinator import Coordinator

coordinator = Coordinator()
intent = coordinator.classify_intent("Can I add CS minor?")
print(f"✅ Coordinator works! Intent: {intent['intent_type']}")
print(f"   Required agents: {intent['required_agents']}")


from multi_agent import app
from blackboard.schema import WorkflowStep
from langchain_core.messages import HumanMessage

state = {
    "user_query": "What are IS major requirements?",
    "student_profile": {},
    "agent_outputs": {},
    "constraints": [],
    "risks": [],
    "plan_options": [],
    "conflicts": [],
    "open_questions": [],
    "messages": [HumanMessage(content="What are IS major requirements?")],
    "active_agents": [],
    "workflow_step": WorkflowStep.INITIAL,
    "iteration_count": 0,
    "next_agent": None,
    "user_goal": None
}

result = app.invoke(state)
print("✅ Full workflow works!")
print(f"Answer: {result['messages'][-1].content[:200]}...")