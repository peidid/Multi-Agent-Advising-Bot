# T1 Benchmark Generation Prompt — Factual Lookup (50 queries)


---

## PROMPT START

You are helping me generate a benchmark for evaluating academic advising systems at CMU-Q. I need you to generate **exactly 100 T1 (Factual Lookup) questions** — questions that have a single, unambiguous factual answer retrievable from the data.

### Your task

1. **Read the following data sources in my project folder** before generating anything (not necessarily every file, but makesure the files selected are diverse and representitive enough):
   - JSON files in `data/courses/` — course catalog with codes, names, units, prerequisites, descriptions
   - files in `data/programs/` — degree requirements for IS, CS, BA, Biological Sciences
   - files in `data/policies/` — registration rules, unit limits, academic standing, grading
   - files in `data/schedules/` — semester course offerings, times, instructors for 2024-2026
   - The file `benchmark_personas.json` (I will provide or it is in the project root)

   **If the folder structure is different, explore the `data/` directory first and tell me what you find before proceeding.**

2. **Generate 100 questions** following the strict rules below.

### Rules

- Every question must have **exactly one correct, unambiguous answer** that can be found directly in the data files you just read.
- Every answer must include the **exact data source** (which file and which field) where the answer is found.
- **Do NOT invent, assume, or hallucinate any facts.** If you cannot find a piece of information in the data, do not generate a question about it.
- Questions should sound **natural** — like a real student asking an advisor. Vary phrasing: some formal, some casual, some indirect.
- Each question should be answerable from **a single domain** (courses OR programs OR policies OR schedules — not a combination).

  - **Category A — Course Info (20):** Questions about course names, units, descriptions. E.g., "How many units is 15-213?"
  - **Category B — Prerequisites (10):** Questions about what courses are prerequisites for a given course. E.g., "What do I need to take before 67-373?"
  - **Category C — Schedule/Offering (20):** Questions about when a course is offered, what time, who teaches it. E.g., "Is 15-251 offered in Spring 2026?"
  - **Category D — Program Requirements (30):** Questions about what courses are required for a specific major, minor, or concentration. E.g., "What are the core courses for the IS major?"
  - **Category E — Policy (20):** Questions about university rules — unit limits, overload rules, grading policies, registration deadlines. E.g., "What is the maximum number of units I can take per semester?"

### Persona grounding

- **20 of the 50 questions** should reference a specific persona from `benchmark_personas.json`. Use their persona_id (e.g., P-001) and write the question as if that student is asking it. The answer should still be a single fact, but the question is phrased from their perspective.
  - Example: For P-003 (CS sophomore with BA minor): "I'm trying to plan my schedule — is 67-250 offered in Spring 2026?"
- **30 of the 50 questions** should be generic (no persona needed). Any student could ask these.

### Output format

Return a single JSON array. Each entry must follow this exact schema:

```json
{
  "query_id": "T1-001",
  "tier": "T1",
  "category": "A",
  "persona_id": "P-003" or null,
  "question": "How many units is 15-213?",
  "answer": "12 units",
  "source_file": "data/courses/15-213.json",
  "source_field": "units",
  "domain": "courses",
  "verification_note": "Directly stated in course JSON file"
}
```

### Quality checklist (verify before outputting)

- [ ] All 50 questions have answers that exist verbatim in the data files
- [ ] No question requires combining information from multiple domains
- [ ] No question requires reasoning or inference — just retrieval
- [ ] 10 questions per category (A through E)
- [ ] 20 questions have persona_id, 30 have null
- [ ] Phrasing is varied and natural (not all "What is..." or "How many...")
- [ ] No duplicate questions or trivially similar questions
- [ ] All course codes referenced actually exist in the data
- [ ] All semesters referenced actually exist in the schedule data

**Generate the 50 T1 questions now. Output only the JSON array, no other text.**

## PROMPT END