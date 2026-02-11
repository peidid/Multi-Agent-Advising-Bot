"""
Fix labels for questions from line 948 onwards in raw_questions.json.
Does NOT modify anything before line 948 (which was manually corrected).

Agent roles:
- course: Course details (prereqs, content, schedule, workload, assessments, instructors)
- program: Degree/major/minor requirements (what courses needed, credits, tracks)
- policy: University policies (overload, pass/fail, probation, deadlines, withdrawal, GPA rules)
- planning: Multi-semester planning, graduation timeline, workload balancing, course sequencing
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "data" / "finetune" / "raw_questions.json"

# Keywords/patterns that indicate each agent
COURSE_PATTERNS = [
    r"prereq", r"prerequisite", r"coreq", r"anti-req",
    r"workload", r"difficult", r"hard", r"easy", r"tough",
    r"content", r"topic", r"cover", r"learn",
    r"exam", r"project", r"homework", r"assignment", r"grading curve",
    r"instructor", r"professor", r"teaching style", r"lecture",
    r"offered", r"schedule", r"time", r"morning", r"afternoon",
    r"lab", r"recitation", r"textbook", r"syllabus",
    r"class size", r"group work", r"peer",
]

PROGRAM_PATTERNS = [
    r"major", r"minor", r"requirement", r"degree",
    r"elective.*count", r"fulfill", r"satisfy",
    r"core course", r"concentration", r"track",
    r"double major", r"double count", r"substitut",
    r"credit.*toward", r"count.*toward",
    r"cs major", r"is major", r"business major", r"biology",
    r"graduate.*requirement", r"unit.*graduat",
]

POLICY_PATTERNS = [
    r"policy", r"policies",
    r"overload", r"unit limit", r"max.*unit",
    r"pass/fail", r"pass fail", r"p/f", r"pass/no pass",
    r"probation", r"academic standing", r"good standing",
    r"withdrawal", r"withdraw", r"drop.*deadline", r"add.*deadline",
    r"dean'?s list", r"gpa.*require", r"minimum gpa",
    r"retake", r"repeat.*course", r"fail.*retake",
    r"transfer credit", r"credit transfer",
    r"full.?time", r"part.?time",
    r"visa", r"international student.*enroll",
    r"audit", r"auditing",
    r"academic integrity", r"plagiarism", r"cheating",
    r"leave of absence", r"scholarship",
    r"appeal", r"petition", r"exception",
    r"registration", r"enroll.*deadline",
    r"voucher",
]

PLANNING_PATTERNS = [
    r"plan.*semester", r"semester plan", r"next semester",
    r"graduate on time", r"graduation timeline",
    r"workload.*balanc", r"balance.*workload",
    r"course sequence", r"what.*take.*after", r"what.*next",
    r"study abroad", r"internship.*semester",
    r"summer course", r"when.*take", r"best time.*take",
    r"early graduation", r"graduate early",
    r"4.?year plan", r"four.?year",
]


def classify_question(question: str, current_labels: list) -> list:
    """
    Determine the correct labels for a question based on its content.
    """
    q_lower = question.lower()
    new_labels = set()

    # Check for course-related content
    is_course = False
    for pattern in COURSE_PATTERNS:
        if re.search(pattern, q_lower):
            is_course = True
            break
    # Also check if it mentions specific course numbers prominently asking about the course itself
    if re.search(r"\b(15-\d{3}|67-\d{3}|70-\d{3}|73-\d{3}|76-\d{3}|21-\d{3}|98-\d{3})\b", q_lower):
        # It mentions a course, but what about it?
        if any(kw in q_lower for kw in ["about", "detail", "content", "prereq", "workload", "hard", "easy", "offer", "schedule"]):
            is_course = True

    # Check for program-related content
    is_program = False
    for pattern in PROGRAM_PATTERNS:
        if re.search(pattern, q_lower):
            is_program = True
            break
    # Specific program keywords
    if any(kw in q_lower for kw in ["cs major", "is major", "business major", "biology major", "minor in", "double major"]):
        is_program = True
    if "requirement" in q_lower and ("major" in q_lower or "minor" in q_lower or "degree" in q_lower):
        is_program = True

    # Check for policy-related content
    is_policy = False
    for pattern in POLICY_PATTERNS:
        if re.search(pattern, q_lower):
            is_policy = True
            break

    # Check for planning-related content
    is_planning = False
    for pattern in PLANNING_PATTERNS:
        if re.search(pattern, q_lower):
            is_planning = True
            break
    # Also planning if asking about timing/sequencing
    if any(kw in q_lower for kw in ["should i take", "when should", "next semester", "plan my", "planning my"]):
        is_planning = True

    # Build label set
    if is_course:
        new_labels.add("course")
    if is_program:
        new_labels.add("program")
    if is_policy:
        new_labels.add("policy")
    if is_planning:
        new_labels.add("planning")

    # If nothing detected, use heuristics based on question content
    if not new_labels:
        # Default heuristics
        if "?" in question or question.lower().startswith(("what", "how", "when", "can", "is", "are", "do", "does")):
            # Try to infer from context
            if any(kw in q_lower for kw in ["course", "class", "15-", "67-", "70-", "73-", "76-", "21-"]):
                new_labels.add("course")
            elif any(kw in q_lower for kw in ["major", "minor", "program", "degree"]):
                new_labels.add("program")
            elif any(kw in q_lower for kw in ["policy", "rule", "allow", "permit"]):
                new_labels.add("policy")
            else:
                # Keep original if can't determine
                return current_labels

    # If still empty, keep original
    if not new_labels:
        return current_labels

    return sorted(list(new_labels))


def fix_specific_questions(data: list, start_idx: int) -> list:
    """
    Apply manual fixes for commonly mislabeled question types.
    """
    for i in range(start_idx, len(data)):
        q = data[i]["question"].lower()
        labels = data[i]["labels"]

        # Fix specific misclassifications

        # "Can I use pass/fail for courses in X minor?" -> policy, program
        if "pass/fail" in q and ("minor" in q or "major" in q):
            data[i]["labels"] = sorted(["policy", "program"])
            continue

        # Dean's list questions -> policy only (not course or program)
        if "dean" in q and "list" in q:
            if "course" in labels or "program" in labels:
                new_labels = ["policy"]
                if "plan" in q or "semester" in q:
                    new_labels.append("planning")
                data[i]["labels"] = sorted(new_labels)
            continue

        # Overload questions -> policy
        if "overload" in q and "course" in labels and "policy" not in labels:
            data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # "What do I gotta take to fulfill X requirements" -> program
        if ("fulfill" in q or "satisfy" in q or "requirement" in q) and "course" in labels:
            data[i]["labels"] = sorted(list(set(labels) | {"program"}))
            continue

        # Visa/international student enrollment questions -> policy
        if ("visa" in q or "international student" in q) and ("enroll" in q or "unit" in q or "course" in q):
            if "policy" not in labels:
                data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # "Can I audit X?" -> policy (auditing is policy)
        if "audit" in q and "policy" not in labels:
            new_labels = list(set(labels) | {"policy"})
            if "course" not in new_labels and re.search(r"\d{2}-\d{3}", q):
                new_labels.append("course")
            data[i]["labels"] = sorted(new_labels)
            continue

        # "switch major" questions -> program, policy (and maybe planning)
        if "switch" in q and "major" in q:
            new_labels = {"program", "policy"}
            if "plan" in q or "semester" in q or "when" in q:
                new_labels.add("planning")
            data[i]["labels"] = sorted(list(new_labels))
            continue

        # Probation + course questions -> policy, course
        if "probation" in q:
            new_labels = set(labels)
            new_labels.add("policy")
            if re.search(r"\d{2}-\d{3}", q):
                new_labels.add("course")
            data[i]["labels"] = sorted(list(new_labels))
            continue

        # "QPA policy" or "GPA policy" -> policy
        if ("qpa" in q or "gpa" in q) and ("policy" in q or "require" in q):
            if "policy" not in labels:
                data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # Questions about prerequisites for courses -> course (not program/planning)
        if "prerequisite" in q and re.search(r"\d{2}-\d{3}", q):
            if labels == ["program"] or labels == ["planning"]:
                data[i]["labels"] = ["course"]
            continue

        # "CS/IS program offerings" -> program
        if "program" in q and "offering" in q:
            data[i]["labels"] = ["program"]
            continue

        # "Is X a tough course" -> course
        if any(kw in q for kw in ["tough", "hard", "easy", "difficult"]) and re.search(r"\d{2}-\d{3}", q):
            if labels == ["program"]:
                data[i]["labels"] = ["course"]
            continue

        # "What if I can't take X this semester" -> course, planning
        if "what if" in q and "take" in q and "semester" in q:
            new_labels = set(labels) - {"program"}
            new_labels.add("course")
            new_labels.add("planning")
            data[i]["labels"] = sorted(list(new_labels))
            continue

        # "When should I take X for Y major/program" -> course, program, planning
        if "when" in q and "take" in q and ("major" in q or "program" in q):
            data[i]["labels"] = sorted(["course", "program", "planning"])
            continue

        # Pure planning questions mislabeled
        if labels == ["course"] and any(kw in q for kw in ["next semester", "plan my", "planning", "graduate on time"]):
            data[i]["labels"] = ["planning"]
            if re.search(r"\d{2}-\d{3}", q):
                data[i]["labels"] = sorted(["course", "planning"])
            continue

        # "Elective options for X minor/major" -> program
        if "elective" in q and ("minor" in q or "major" in q):
            if labels == ["course"]:
                data[i]["labels"] = ["program"]
            elif "course" in labels and "program" not in labels:
                data[i]["labels"] = sorted(list(set(labels) | {"program"}))
            continue

        # "Does X count towards Y requirement" -> course, program
        if "count" in q and ("requirement" in q or "major" in q or "minor" in q or "elective" in q):
            new_labels = {"program"}
            if re.search(r"\d{2}-\d{3}", q):
                new_labels.add("course")
            data[i]["labels"] = sorted(list(new_labels))
            continue

        # "How does X fit into curriculum/program" -> course, program
        if ("fit" in q or "integrate" in q) and ("curriculum" in q or "program" in q or "major" in q):
            new_labels = {"program"}
            if re.search(r"\d{2}-\d{3}", q):
                new_labels.add("course")
            data[i]["labels"] = sorted(list(new_labels))
            continue

        # Withdrawal questions -> policy
        if "withdraw" in q and "policy" not in labels:
            data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # "Full-time status" -> policy
        if "full-time" in q or "full time" in q:
            if "policy" not in labels:
                data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # Transfer credit questions -> policy
        if "transfer" in q and ("credit" in q or "student" in q):
            if "policy" not in labels:
                data[i]["labels"] = sorted(list(set(labels) | {"policy"}))
            continue

        # "Taking X and Y together" -> course, planning
        if ("together" in q or "same semester" in q or "simultaneously" in q) and re.search(r"\d{2}-\d{3}", q):
            new_labels = {"course", "planning"}
            data[i]["labels"] = sorted(list(new_labels))
            continue

    return data


def main():
    print("Loading raw_questions.json...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total questions: {len(data)}")

    # Find which index corresponds to line 948
    # Each question entry is about 7 lines in JSON, so line 948 / 7 ≈ 135
    # But let's be safe and find the entry that has source_file containing batch_course_2 at the right position

    # Actually, the user said from line 948. Let's count characters/lines more carefully.
    # The easiest approach: load as text, find the line, then map to index

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Line 948 is at index 947 (0-indexed)
    # Find which question entry this corresponds to
    # We'll parse up to that line to count how many complete entries

    text_up_to_948 = "".join(lines[:947])
    # Count how many complete question entries by counting '"question":'
    entries_before = text_up_to_948.count('"question":')

    print(f"Questions before line 948: {entries_before}")
    print(f"Will fix labels for questions from index {entries_before} onwards")

    # First, apply rule-based classification
    changes_made = 0
    for i in range(entries_before, len(data)):
        old_labels = data[i]["labels"].copy()
        new_labels = classify_question(data[i]["question"], old_labels)
        if sorted(new_labels) != sorted(old_labels):
            data[i]["labels"] = new_labels
            changes_made += 1

    print(f"Classification-based changes: {changes_made}")

    # Then apply specific fixes for known patterns
    data = fix_specific_questions(data, entries_before)

    # Save the fixed data
    with open(INPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nSaved fixed labels to {INPUT_FILE}")

    # Print distribution
    from collections import Counter
    label_combos = Counter(tuple(sorted(q["labels"])) for q in data)
    print("\nUpdated label distribution:")
    for combo, count in sorted(label_combos.items(), key=lambda x: -x[1]):
        print(f"  {', '.join(combo):45s} → {count}")


if __name__ == "__main__":
    main()
