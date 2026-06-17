"""
Quick demo: Generate a few sample questions to preview output format.
Run: python scripts/demo_generation.py
"""
import json
from openai import OpenAI

client = OpenAI()

# Demo: Generate multi-agent questions
MULTI_AGENT_DEMO = {
    "labels": ["course", "policy"],
    "description": "Questions needing both course details AND policy knowledge",
    "scenarios": [
        "Taking courses while on academic probation",
        "Prerequisite waiver policies",
        "Retaking a failed course",
    ],
}

prompt = f"""You are generating training data for a student query intent classifier at CMU-Qatar.

Generate 5 diverse questions a CMU-Qatar student might ask that require
MULTIPLE agents to answer properly. Specifically, these questions need: [course, policy]

What this combination means: {MULTI_AGENT_DEMO['description']}

Example scenarios:
{chr(10).join(f"- {s}" for s in MULTI_AGENT_DEMO['scenarios'])}

IMPORTANT:
- Questions should NATURALLY require all listed agents
- Make questions sound like real students (casual, sometimes incomplete)
- Include specific CMU-Q courses (15-122, 15-213, 67-250, etc.)

Return ONLY a valid JSON array:
[{{"question": "...", "labels": ["course", "policy"]}}]"""

print("=" * 60)
print("DEMO: Multi-Agent Question Generation")
print("=" * 60)
print(f"\nGenerating questions for: course + policy")
print("...")

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.9,
    max_tokens=2000,
    response_format={"type": "json_object"}
)

content = response.choices[0].message.content
parsed = json.loads(content)

# Handle different response formats
if isinstance(parsed, dict):
    questions = parsed.get("questions", parsed.get("data", [parsed] if "question" in parsed else []))
else:
    questions = parsed

print(f"\n✅ Generated {len(questions)} questions:\n")
for i, q in enumerate(questions, 1):
    print(f"{i}. {q['question']}")
    print(f"   Labels: {q['labels']}")
    print()

print("=" * 60)
print("This is what each entry looks like in raw_questions.json")
print("=" * 60)
print(json.dumps(questions[0], indent=2))
