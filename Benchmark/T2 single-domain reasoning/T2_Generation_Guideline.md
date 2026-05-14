# T2 Benchmark Generation Prompt — Single-Domain Reasoning (50 queries)

Copy everything below the line and paste it directly into Claude Sonnet in VS Code.

---

## PROMPT START

You are helping me generate a benchmark for evaluating academic advising systems at CMU-Q. Generate **exactly 50 T2 (Single-Domain Reasoning) questions**.

### Step 0 — Read the benchmark design

**Read `benchmark/outline.md` first.** Understand T2's role:
- T1: "What are the prerequisites for 15-213?" → pure lookup
- **T2: "I've completed 15-112 — can I take 15-213?" → reasoning within ONE domain**
- T3: "Can I take 15-213 and 67-373 in Fall 2025 given my major and schedule?" → crosses domains

### Step 1 — Quick data scan (spend ≤ 3 minutes)

Do a **fast scan** — just enough to understand what exists. Do NOT read every file.

- Skim **5-10 course files** in `data/courses/` for fields (prereqs, units, names)
- Skim **2-3 program files** in `data/programs/` for requirement structures
- Skim **1-2 policy files** in `data/policies/` for key rules (unit limits, academic warning)
- Skim **1-2 schedule files** in `data/schedules/` for format
- Read **only the `persona_summaries` array** in `benchmark_personas.json` metadata — do NOT read every persona's full course list

### Step 2 — Generate all 50 questions

**IMPORTANT: Prioritize generating all 50 questions quickly. I will verify answers manually afterward.**

Use real course codes and program names where you can. If you're unsure about a specific fact (a prerequisite, a requirement detail, a policy number), **write your best guess and flag it in `needs_verification`**. Do not spend time looking things up for every question.

### Categories (10 each)

**A — Prerequisite Satisfaction (10):** "Can I take X given my courses?" All 10 reference a persona. Mix YES and NO answers.

**B — Requirement Progress (10):** "How far along am I in my major/minor?" All 10 reference a persona. Cover different majors/concentrations.

**C — Schedule Feasibility (10):** "Do courses A and B have a time conflict?" 5 with persona, 5 generic. Mix conflicts and no-conflicts.

**D — Policy Application (10):** "Does this rule apply to my situation?" Use P-009, P-013, P-046 (academic warning) for ≥3. Cover unit limits, overload, standing restrictions.

**E — Course Equivalence (10):** "Does course X count for requirement Y?" 5 with persona, 5 generic.

### Output format

JSON array. Each entry:

```json
{
  "query_id": "T2-001",
  "tier": "T2",
  "category": "A",
  "persona_id": "P-004" or null,
  "question": "I've taken 15-112 and 21-127. Can I register for 15-251?",
  "expected_answer": "No — 15-251 requires 15-150, which you haven't completed.",
  "reasoning_type": "Prerequisite chain check",
  "domain": "courses",
  "common_mistake": "Only checking one prereq instead of all",
  "needs_verification": ["Confirm 15-251 actual prereqs", "Confirm P-004 hasn't taken 15-150"]
}
```

**`needs_verification` is the most important field.** List every factual claim I need to check.

### Checklist
- 50 total, 10 per category
- All require reasoning (not just retrieval)
- Each stays within ONE domain
- ≥35 reference a persona
- `needs_verification` present on every entry
- No duplicates

**Generate all 50 now. Output only the JSON array.**

## PROMPT END