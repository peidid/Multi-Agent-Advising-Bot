"""
Generate missing multi-agent questions and append to raw_questions.json
"""
import json
import time
from pathlib import Path
from openai import OpenAI

client = OpenAI()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "finetune" / "raw_questions.json"

MODEL = "gpt-4o"

# The three combinations that need more questions
MISSING_COMBOS = [
    {
        "labels": ["course", "planning"],
        "description": "Questions about course selection in context of semester planning",
        "scenarios": [
            "What to take next semester given current progress",
            "Course sequencing and prerequisite chains",
            "Workload balancing across semesters",
            "Summer course planning",
            "Which elective to take when",
            "Handling a course conflict between two needed courses",
            "Best time to take difficult courses",
            "Internship semester course planning",
            "Balancing lab courses with lecture courses",
            "When to take writing-intensive courses",
        ],
        "count": 60
    },
    {
        "labels": ["course", "policy", "program"],
        "description": "Course selection with degree and policy constraints",
        "scenarios": [
            "Can I substitute this course for a requirement given the waiver policy",
            "Double-counting policies for double majors",
            "Using AP/transfer credits to satisfy degree requirements",
            "Petition to use non-standard course for requirement",
            "Cross-listed course counting for multiple requirements",
            "Retaking a course that's required for my major",
            "Pass/fail option for a required course",
            "Taking a course at another campus to fulfill requirement",
        ],
        "count": 60
    },
    {
        "labels": ["planning", "policy", "program"],
        "description": "Degree completion with policy constraints over time",
        "scenarios": [
            "Minimum GPA required each semester to graduate on time",
            "Part-time status impact on degree completion timeline",
            "Academic recovery plan to meet graduation requirements",
            "Study abroad impact on major completion timeline",
            "Leave of absence and returning to complete degree",
            "Maximum time limit to complete degree requirements",
            "Probation while trying to complete major requirements",
            "Unit limits affecting graduation timeline",
        ],
        "count": 60
    },
]


def call_gpt(prompt: str) -> list:
    """Call GPT and parse JSON response."""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=16000,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            if not content:
                print(f"  Empty content (attempt {attempt+1}), retrying...")
                time.sleep(2)
                continue

            parsed = json.loads(content)

            if isinstance(parsed, dict):
                for key in ["questions", "data", "results", "items"]:
                    if key in parsed:
                        return parsed[key]
                if "question" in parsed:
                    return [parsed]
            elif isinstance(parsed, list):
                return parsed

            print(f"  Unexpected format, retrying...")

        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2)

    return []


def generate_for_combo(combo: dict) -> list:
    """Generate questions for a single combo."""
    labels_str = ", ".join(combo["labels"])
    scenarios_str = "\n".join(f"- {s}" for s in combo["scenarios"])
    target = combo["count"]

    all_questions = []
    batch_size = 30  # Generate in batches of 30
    num_batches = (target + batch_size - 1) // batch_size

    print(f"\n  Generating {target} questions for [{labels_str}] in {num_batches} batches...")

    for batch_num in range(num_batches):
        remaining = target - len(all_questions)
        batch_target = min(batch_size, remaining)

        if batch_target <= 0:
            break

        prompt = f"""You are generating training data for a student query intent classifier at CMU-Qatar.

Generate EXACTLY {batch_target} HIGHLY DIVERSE questions a CMU-Qatar student might ask that require
MULTIPLE agents to answer properly. Specifically, these questions need: [{labels_str}]

What this combination means: {combo['description']}

EXAMPLE scenarios (use as inspiration, but CREATE MANY NEW ONES):
{scenarios_str}

This is batch {batch_num + 1} of {num_batches} - make sure questions are unique and diverse!

CRITICAL REQUIREMENTS:
1. GO BEYOND the example scenarios - invent new realistic situations students face
2. Questions should NATURALLY require ALL listed agents (not artificially combined)
3. Mix student types: freshmen, sophomores, juniors, seniors, transfer students
4. Mix emotional tones: stressed, curious, urgent, casual, formal
5. Reference specific CMU-Q courses (15-112, 15-122, 15-213, 15-251, 67-250, 67-262, 70-122, etc.)
6. NO TWO QUESTIONS should start with the same 4 words
7. Mix question lengths: short, medium, and long conversational questions

VARIETY in question styles:
- Hypothetical: "What if I...", "If I were to..."
- Situational: "I'm currently...", "My situation is..."
- Direct: "Can I...", "Is it possible to..."
- Anxious: "I'm worried that...", "What happens if..."
- Planning: "I want to...", "I'm trying to..."

Return ONLY a valid JSON array with EXACTLY {batch_target} questions:
[{{"question": "...", "labels": {json.dumps(combo["labels"])}}}]"""

        questions = call_gpt(prompt)
        if questions:
            for q in questions:
                q["labels"] = combo["labels"]
                q["source_file"] = f"missing_{labels_str.replace(', ', '_')}"
            all_questions.extend(questions)
            print(f"    Batch {batch_num + 1}/{num_batches}: +{len(questions)} (total: {len(all_questions)})")
        else:
            print(f"    Batch {batch_num + 1}/{num_batches}: FAILED")

    return all_questions


def main():
    print("=" * 60)
    print("Generating Missing Multi-Agent Questions")
    print("=" * 60)

    # Load existing data
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        existing_data = json.load(f)

    print(f"Existing questions: {len(existing_data)}")

    # Generate missing questions
    new_questions = []
    for combo in MISSING_COMBOS:
        questions = generate_for_combo(combo)
        new_questions.extend(questions)
        print(f"  ✓ Generated {len(questions)} for {combo['labels']}")

    # Append to existing
    combined = existing_data + new_questions

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print(f"Added {len(new_questions)} new questions")
    print(f"Total questions now: {len(combined)}")
    print(f"Saved to: {OUTPUT_FILE}")

    # Show new distribution
    from collections import Counter
    label_combos = Counter(tuple(sorted(q["labels"])) for q in combined)
    print("\nUpdated label distribution:")
    for combo, count in sorted(label_combos.items(), key=lambda x: -x[1]):
        print(f"  {', '.join(combo):40s} → {count}")


if __name__ == "__main__":
    main()
