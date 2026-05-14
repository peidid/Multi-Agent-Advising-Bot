# T3 Benchmark Generation Prompt — Cross-Domain Constraint Checking (50 queries)

Copy everything below the line and paste it directly into Claude Sonnet in VS Code. Make sure Claude has access to your project data folder.

---

## PROMPT START

You are helping me generate a benchmark for evaluating academic advising systems at CMU-Q. I need you to generate **exactly 50 T3 (Cross-Domain Constraint Checking) questions**.

### What makes T3 different from T1 and T2

- **T1 (Factual Lookup):** "What are the prerequisites for 15-213?" → single fact, single domain
- **T2 (Single-Domain Reasoning):** "I've completed 15-112 — can I take 15-213?" → reasoning within ONE domain (courses)
- **T3 (Cross-Domain Constraint Checking):** "I want to take 15-213 and 67-373 in Fall 2025 — is this possible given my major requirements and schedule?" → requires combining information from **2 or more domains** (courses + schedules + programs) to produce a correct answer

T3 is the first tier where a single-agent system with one RAG lookup is likely to miss something, because the answer depends on facts scattered across multiple data sources that must be **jointly** reasoned about.

### Step 0 — Understand the benchmark design

**First, read `benchmark/outline.md` carefully.** This document describes the full benchmark design, including the tier taxonomy (T1-T5), evaluation criteria, and how this tier fits into the larger picture. Understand T3's role and how it differs from T1 (single fact, single domain) and T2 (reasoning within one domain) before proceeding.

### Step 1 — Familiarize yourself with the data

Read the following data sources in my project folder (not necessarily every file, but make sure the files you select are **diverse and representative** enough to cover different majors, course departments, semesters, and policy areas):

- JSON files in `data/courses/` — course catalog with codes, names, units, prerequisites, descriptions
- Files in `data/programs/` — degree requirements for IS, CS, BA, Biological Sciences, all concentrations and minors
- Files in `data/policies/` — registration rules, unit limits, overload policy, academic standing/warning rules, grading
- Files in `data/schedules/` — semester course offerings, times, instructors for 2024-2026
- The file `benchmark_personas.json` — 64 student personas with full course histories, standings, goals, concerns

**If the folder structure is different from what's listed above, explore the `data/` directory first and tell me what you find before proceeding.**

### Step 2 — Study the personas thoroughly

**Read `benchmark_personas.json` carefully.** Almost every T3 question requires a specific student's context. Pay special attention to:
   - Students on **academic warning**: P-009 (CS, 5th year), P-013 (IS, sophomore), P-046 (CS, 5th year, entered 2016)
   - Students with **dual minors or dual concentrations**: P-042, P-044, P-045, P-025, P-028, P-035, P-056
   - Students in their **final semesters**: all seniors and 5th-year students
   - Students with **unusual entry years**: P-046 (Fall 2016), P-052 (Summer 2016), P-019 (Fall 2019)

### Step 3 — Generate 50 questions

Follow the strict rules below.

### The core principle of T3

Every T3 question MUST require information from **at least 2 different domains** to answer correctly. The answer is WRONG or INCOMPLETE if any one domain is ignored. This is the defining characteristic.

For each question, you must be able to clearly state: "Domain X provides [fact A], Domain Y provides [fact B], and only by combining A and B can you reach the correct conclusion."

### The 5 cross-domain categories (10 questions each)

**Category A — Prerequisites + Schedule (10 questions)**
Can a student take a specific course in a specific semester, considering both prerequisite satisfaction AND whether the course is actually offered?

Domain crossing: `courses` (prerequisites) × `schedules` (semester offerings/times)

Reasoning pattern: Student wants course X → check if prereqs are met (courses domain) → check if X is offered in target semester (schedules domain) → check for time conflicts with other planned courses (schedules domain).

**All 10 must reference a specific persona** (use their actual course history to determine prereq satisfaction).

Example:
```
Persona P-004 (CS junior, has taken 15-112, 15-122, 15-150, 21-127, 21-241)
Question: "I want to take 15-251 and 15-213 next semester (Spring 2026). Can I do both?"
Answer: "You can take 15-213 (prereq 15-112 ✓). However, check the schedule — 
15-251 and 15-213 may have a time conflict on [specific days/times]. 
Also, 15-251 requires 15-150 which you have completed ✓."

Domains needed: 
- courses: verify prereqs for both 15-251 and 15-213 against student's history
- schedules: check if both are offered Spring 2026 and whether times conflict
Wrong if only one domain consulted: checking only prereqs would miss the time conflict; 
checking only schedules would miss whether the student is eligible.
```

**Category B — Program Requirements + Course Availability (10 questions)**
Which remaining requirements can a student actually fulfill in a given semester, considering what's offered?

Domain crossing: `programs` (degree/minor/concentration requirements) × `schedules` (what's offered when)

Reasoning pattern: Student needs courses [X, Y, Z] for their program → which of those are offered in the target semester? → are any NOT offered, creating a bottleneck?

**All 10 must reference a specific persona.**

Example:
```
Persona P-015 (IS junior, Data Science concentration, Tech Entrepreneurship minor)
Question: "Which of my remaining DS concentration courses are available in Spring 2026?"
Answer: "Your DS concentration still requires [A, B, C]. Of these, A and B are offered 
Spring 2026 but C is only offered in Fall semesters. You should plan to take C in Fall 2026."

Domains needed:
- programs: what DS concentration courses does P-015 still need
- schedules: which of those are offered in Spring 2026
```

**Category C — Policy + Student Situation (10 questions)**
Does a policy constraint affect what a specific student can do, given their academic record and current plans?

Domain crossing: `policies` (rules about unit limits, overload, academic warning) × `courses` (unit counts of planned courses) and/or `programs` (student's program status)

Reasoning pattern: Student wants to do X → policy says rule Y applies to students in condition Z → is this student in condition Z? → what are the consequences?

**Prioritize personas on academic warning (P-009, P-013, P-046) — use each at least once.** Also include scenarios involving overload requests, unit limit calculations, and registration restrictions.

Example:
```
Persona P-009 (CS, 5th year, academic warning)
Question: "I need to take 5 courses next semester to graduate on time. Is that allowed?"
Answer: "Taking 5 courses would total approximately [X] units. However, you are on 
academic warning, which limits you to [Y] units per semester per [policy name]. 
You would need to either get an exception or spread courses across more semesters."

Domains needed:
- courses: calculate total units for the 5 specific courses
- policies: academic warning unit cap rule
Wrong if only one domain consulted: knowing the unit cap but not the specific 
course units can't determine if the limit is exceeded; knowing the courses 
but not the policy can't identify the restriction.
```

**Category D — Multi-Requirement Interaction (10 questions)**
How do requirements from different parts of a student's program interact — major requirements, minor requirements, concentration requirements, and general education?

Domain crossing: `programs` (multiple requirement sets) × `courses` (course details, double-counting rules)

Reasoning pattern: Student is pursuing major + minor (or + concentration) → a course satisfies requirement in program A → does it also count for program B? → what does policy say about double-counting?

**All 10 must reference personas with declared minors or multiple concentrations.** Good candidates: P-003, P-005, P-007, P-014, P-025, P-028, P-035, P-042, P-044, P-045, P-053, P-056.

Example:
```
Persona P-025 (BA junior, dual concentration Finance + BAT, Economics minor)
Question: "Can 73-102 count toward both my Finance concentration and my Economics minor?"
Answer: "73-102 [course name] is listed as [required/elective] for the Finance 
concentration and also appears in the Economics minor requirements. However, 
[policy on double-counting states X]. Therefore [yes/no with explanation]."

Domains needed:
- programs (Finance concentration requirements)
- programs (Economics minor requirements) 
- policies (double-counting rules)
```

**Category E — Graduation Feasibility Check (10 questions)**
Can a specific student graduate by their target date, considering remaining requirements, course availability, and policy constraints?

Domain crossing: `programs` (remaining requirements) × `schedules` (course availability) × `policies` (unit limits per semester)

This is the most complex T3 category — it often touches 3 domains. But unlike T4 (which asks "plan my semesters"), T3-E asks a **yes/no feasibility question**: "Is it even possible?"

**All 10 must reference a specific persona.** Prioritize seniors, 5th-year students, and students with concerns about graduating on time: P-007, P-009, P-010, P-019, P-022, P-029, P-038, P-040, P-046, P-052.

Example:
```
Persona P-046 (CS, 5th year, entered Fall 2016, academic warning, Math minor)
Question: "Can I complete all remaining CS requirements and my Math minor by Spring 2026?"
Answer: "You have [X] remaining CS requirements and [Y] remaining Math minor courses. 
Given that you can take at most [Z] units per semester (academic warning cap), 
and [course A] is only offered in Fall, completing everything by Spring 2026 
is [feasible/not feasible]. Specifically, [explanation of bottleneck]."

Domains needed:
- programs: remaining CS + Math minor requirements
- schedules: when remaining courses are offered
- policies: academic warning unit cap
```

### Output format

Return a single JSON array. Each entry must follow this exact schema:

```json
{
  "query_id": "T3-001",
  "tier": "T3",
  "category": "A",
  "persona_id": "P-004",
  "question": "I want to take 15-251 and 15-213 together in Spring 2026. Is that possible for me?",
  "answer": "You have completed the prerequisites for both courses (15-150 and 21-127 for 15-251; 15-112 for 15-213). Both are offered in Spring 2026. However, 15-251 is scheduled MWF 10:30-11:20 and 15-213 is MWF 10:30-11:20 — they have a direct time conflict. You cannot take both in Spring 2026.",
  "domains_required": ["courses", "schedules"],
  "domain_contributions": {
    "courses": "Prerequisite verification for both courses against student's history",
    "schedules": "Semester offering confirmation and time conflict detection"
  },
  "key_facts": [
    "15-251 requires 15-150 and 21-127 (both completed by P-004)",
    "15-213 requires 15-112 (completed by P-004)",
    "Both offered Spring 2026",
    "Time conflict: both MWF 10:30-11:20"
  ],
  "wrong_if_single_domain": "Checking only prerequisites would approve this combination; checking only schedules would miss whether the student is eligible. Both domains are necessary for a correct answer.",
  "common_mistake": "Approving the combination after verifying prerequisites without checking schedule conflicts",
  "reasoning_chain": [
    "Step 1: Check if P-004 has prereqs for 15-251 → Yes (15-150 ✓, 21-127 ✓)",
    "Step 2: Check if P-004 has prereqs for 15-213 → Yes (15-112 ✓)",
    "Step 3: Check if both offered Spring 2026 → Yes",
    "Step 4: Check for time conflicts → CONFLICT detected",
    "Conclusion: Not possible due to time conflict"
  ]
}
```

### Quality checklist (verify before outputting)

- [ ] All 50 questions genuinely require 2+ domains — test this by asking "could I answer this correctly with only one domain?" If yes, it's NOT a T3 question, demote it to T2.
- [ ] Every fact in every answer is traceable to a specific data file. No invented prerequisites, schedules, requirements, or policies.
- [ ] All persona references accurately reflect the persona's actual course history from `benchmark_personas.json`. Double-check completed courses before claiming a prerequisite is or isn't met.
- [ ] `wrong_if_single_domain` clearly explains WHY consulting only one domain produces an incorrect or incomplete answer.
- [ ] 10 questions per category (A through E)
- [ ] At least 45 of 50 questions reference a specific persona
- [ ] P-009, P-013, and P-046 (academic warning students) each appear in at least 2 questions
- [ ] Students with dual minors/concentrations appear in Category D questions
- [ ] Seniors and 5th-year students appear in Category E questions
- [ ] `common_mistake` identifies a plausible error — something a less sophisticated system would actually get wrong
- [ ] No duplicate or trivially similar questions
- [ ] Answers are complete and specific (not vague — cite exact course codes, unit counts, times, policy names)

### Important warnings

1. **Do NOT generate questions where the cross-domain aspect is trivial.** Bad example: "What are the prereqs for 15-213 and when is it offered?" — this is just two T1 questions stapled together. Good T3 questions have domains that **interact**: the answer from one domain changes the meaning or applicability of the answer from another domain.

2. **Do NOT invent any facts.** Every course code, prerequisite, schedule, requirement, and policy must come from the actual data files. If you cannot verify a fact, do not include it in a question or answer.

3. **The `wrong_if_single_domain` field is the most important quality check.** If you cannot write a convincing explanation of why a single domain produces the wrong answer, the question is not truly cross-domain and should be replaced.

**Generate the 50 T3 questions now. Output only the JSON array, no other text.**

## PROMPT END