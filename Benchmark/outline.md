**The "when and why multi-agent" framing is the real contribution.** This is the most interesting and timely research question in the message. The field is genuinely confused right now about whether multi-agent architectures are worth the complexity. A well-designed empirical study that says "here's the boundary — single-agent handles X, multi-agent is necessary for Y, and here's why" would be cited. That's a finding people actually need.

**Your peer's intuition matches reality.** The observation that single-agent is faster and often more accurate on straightforward tasks, but multi-agent helps on complex planning and cross-domain reasoning — this is almost certainly what the ablation will show. The key is that *documenting this precisely with evidence* is the contribution, not the system itself. The system becomes the vehicle for the finding.

**The benchmark idea has legs.** ACL values reusable resources. A well-constructed benchmark of academic advising queries stratified by complexity — from simple lookups to adversarial multi-constraint planning problems — is something other researchers could build on. Combined with the ablation results showing where each system configuration breaks down, this is a dual contribution: benchmark + empirical findings.

## Where I'd Push Back or Refine

**Don't try to claim all three contributions equally.** The messages list iterative refinement, proposal-critique, transparency, the benchmark, AND the "when do we need multi-agent" analysis. That's too many things for a demo paper, and individually most are modest. I'd pick a clear primary narrative:

> *Primary:* Empirical analysis of when multi-agent is necessary vs. overkill, using academic advising as a testbed with a new difficulty-stratified benchmark.
> *Secondary:* The system and its design (proposal-critique, iterative refinement) as the experimental apparatus.
> *Tertiary:* Transparency findings from the user study.

This reframes the paper from "look at our system" to "here's what we learned by building and rigorously testing this system." That's a much stronger pitch for ACL.

**The benchmark needs careful design to be credible.** Using student course data for context is the right instinct, but a few things matter:

- You need a **clear taxonomy of difficulty levels** with principled criteria, not just "easy/medium/hard." Something like: T1 (single-fact lookup), T2 (single-domain reasoning), T3 (cross-domain constraint checking), T4 (multi-step planning with constraints), T5 (adversarial/impossible cases with conflicting requirements). Then show the ablation results broken down by tier — that's the money table.
- **Gold-standard answers are essential.** AI-generated questions evaluated by AI is circular. For the benchmark to be taken seriously, advisors need to write or validate both the questions and reference answers, at least for the complex tiers.
- **Size matters.** 150 queries is okay for a system evaluation, but thin for a benchmark contribution. If the benchmark is a headline contribution, aim for 200-300+ with good coverage across tiers.

**The "single agent is enough" finding needs to be presented carefully.** There's a risk that reviewers read the paper and conclude "so the multi-agent system is unnecessary for most cases... why did you build it?" The narrative needs to be: "We built the full system, discovered through rigorous ablation that complexity is only justified for specific query types, and here's a precise characterization of *which* types and *why*." Frame it as insight, not as undermining your own system.

**Human evaluation is non-negotiable for this framing.** If the claim is "multi-agent catches errors that single-agent misses on complex planning," you need advisors confirming that those catches are real and meaningful, not just the system's own GPT-5.2 saying so. Even 3-4 advisors evaluating 50 complex queries each would be sufficient.

## My Honest Assessment of This Direction

This reframing moves the paper from "solid engineering, questionable novelty" to "empirical contribution the community needs." The combination of:

1. A difficulty-stratified benchmark with advisor-validated gold standards
2. Clean ablation results showing where each component adds value
3. A clear "here's the boundary between single-agent and multi-agent" finding

...is a genuinely publishable package. The benchmark gives it lasting value, the ablation gives it rigor, and the finding gives it relevance.



This is a substantial question — let me think through this carefully and give you a concrete, actionable plan.

## Benchmark Design: The Big Picture

The benchmark needs three things to be competitive at ACL: a **principled taxonomy**, **realistic contextualized queries**, and **rigorous evaluation criteria**. Let me walk through each.

## 1. Query Taxonomy

You need clearly defined tiers where each tier adds complexity. Here's what I'd propose:

**T1 — Factual Lookup** (easiest)
Single-fact retrieval with an unambiguous answer. Examples: "What are the prerequisites for 15-213?", "How many units is 67-272?", "When is 67-373 offered in Fall 2025?"

**T2 — Single-Domain Reasoning**
Requires inference within one domain, not just retrieval. Examples: "Can a student who hasn't taken 15-112 register for 15-213?", "Does 67-272 count toward the IS core?"

**T3 — Cross-Domain Constraint Checking**
Requires combining information from multiple domains (courses + policies, programs + schedules). Examples: "If I take 67-272 and 67-373 together in Fall 2025, will I have a time conflict and does this satisfy any IS requirements?", "Can a student on academic probation take 21 units next semester?"

**T4 — Personalized Multi-Step Planning**
Requires reasoning about a specific student's situation across multiple semesters with constraints. This is where student course-history data becomes essential. Examples: "Given my completed courses, plan my remaining 3 semesters to finish the IS major with a CS minor while staying under 54 units per semester."

**T5 — Adversarial / Edge Cases**
Deliberately hard: conflicting constraints, impossible-to-satisfy requirements, ambiguous policies, tradeoffs with no clean answer. Examples: "I need to take 15-213 and 67-373 next semester to graduate on time, but 15-213 is a prerequisite for 67-373. What are my options?", "I want to add a CS minor but I'm a senior with 2 semesters left — is it possible, and if not, what's the closest I can get?"

**Target distribution:** Roughly 40-50 T1/T2 queries, 50-60 T3 queries, 60-80 T4 queries, 30-40 T5 queries. Total: 200-250. Weight heavily toward T3-T5 because that's where the interesting findings are, but you need T1/T2 to show the baseline comparison (single-agent handles these fine).

## 2. How to Use Student Course-History Data

This is your biggest asset. Here's a concrete pipeline:

**Step 1: Create Student Personas**

Take real course-history data and create anonymized student profiles. Each profile captures:

```json
{
  "id": "S-047",
  "major": "Information Systems",
  "minor": null,
  "year": "Junior",
  "semesters_remaining": 3,
  "courses_completed": ["15-112", "67-250", "36-200", "67-262", ...],
  "courses_in_progress": ["67-272"],
  "gpa": 3.4,
  "units_completed": 142,
  "flags": ["considering CS minor"]
}
```

Aim for 20-30 diverse personas covering different majors, years, edge cases (students behind schedule, students wanting to add minors late, students on probation, transfer students with unusual credit).

**Step 2: Generate Query-Persona Pairs**

This is the critical step. You have three methods, and you should use all three:

**Method A — Advisor-authored queries (highest quality, lowest volume).** Sit down with 2-3 academic advisors. Show them each persona and ask: "What are the hardest advising questions this student might ask? What are the questions where you'd need to carefully check multiple things before answering?" Advisors know the tricky edge cases from experience. Target 40-60 queries this way, focused on T3-T5.

**Method B — Student-sourced queries (high ecological validity).** If you can survey actual students: "What's the most confusing advising question you've had?" or mine past advising appointment records (anonymized). This gives you realistic T1-T3 queries.

**Method C — Systematic generation with adversarial design (highest volume).** Use the student profiles + curriculum data to programmatically identify constraint conflicts, then craft queries around them. For example:

```
For each student persona:
  1. Find courses they still need for graduation
  2. Check which of those have prerequisite chains they haven't started
  3. Check for semester-availability gaps (needed course not offered when they need it)
  4. Check for potential time conflicts in required courses
  5. Check if their unit count per remaining semester would exceed policy limits
  → Each tension point becomes a T4/T5 query
```

You can use an LLM to help draft the natural-language queries from these tension points, but **an advisor must validate every query and its reference answer**. The LLM helps with volume; humans ensure quality.

**Step 3: Construct Adversarial Cases Deliberately**

For T5, you want cases that are genuinely hard, not just complex. Some patterns:

- **Impossible constraints:** Student needs courses A and B next semester, but A is a prereq for B. No clean solution exists — the system should recognize this and present tradeoffs.
- **Policy conflicts:** Student wants to overload to graduate on time, but is on academic warning which prohibits overloading.
- **Ambiguous requirements:** A course satisfies requirements in two different programs — how should it be counted? What does the policy actually say?
- **Missing information:** Student asks about a course that exists but isn't scheduled for the relevant semester. System should identify this gap rather than hallucinate a schedule.
- **Cascading dependencies:** Dropping one course this semester delays a prerequisite chain that pushes graduation back two semesters, not just one. The system should trace this full chain.

## 3. Reference Answers and Evaluation Criteria

This is where most benchmarks fail. You need:

**Gold-standard reference answers for every query.** Written or validated by advisors. For T1-T2, these are straightforward factual answers. For T3-T5, the reference answer should include:

```
{
  "query_id": "T4-023",
  "persona": "S-047",
  "reference_answer": "...",
  "key_facts": [
    "15-213 is prerequisite for 15-251",
    "67-373 is only offered in Spring",
    "Student cannot exceed 54 units in any semester"
  ],
  "required_reasoning": [
    "Must recognize prerequisite chain 15-112 → 15-213 → 15-251",
    "Must check schedule availability across 3 semesters",
    "Must verify unit totals per semester"
  ],
  "known_traps": [
    "15-251 cannot be taken same semester as 15-213",
    "Suggesting 67-373 in Fall is incorrect (not offered)"
  ],
  "acceptable_alternatives": ["..."],
  "difficulty_justification": "Cross-domain: requires courses + programs + policy"
}
```

The **key_facts**, **required_reasoning**, and **known_traps** fields are what make this benchmark special. They enable both automated and human evaluation with clear criteria.

## 4. Evaluation Protocol

You need a **two-tier evaluation**:

**Tier 1 — Automated Evaluation (all queries, all systems)**

Use GPT-4 (not GPT-5.2, to avoid self-evaluation bias if your agents use 5.2) as a judge with the reference answer. Provide the query, persona, system response, and the structured reference answer. Ask the judge to score on:

- **Factual accuracy** (0-5): Are all stated facts correct per the reference?
- **Completeness** (0-5): Are all key_facts and required_reasoning present?
- **Trap avoidance** (0-5): Did the system fall into any known_traps?
- **Coherence** (0-5): Is the answer well-organized and actionable?

Use a different model from your system's to avoid the circularity problem. Also consider using Claude as a second judge and reporting inter-judge agreement — this strengthens credibility.

**Tier 2 — Human/Advisor Evaluation (subset, focused on T3-T5)**

This is non-negotiable for a competitive benchmark. Here's a practical design:

- Select 60-80 queries from T3-T5
- For each query, show the advisor the student persona + query + system response (blinded — they don't know which system produced it)
- Advisors evaluate on:
  - **Correctness:** Would following this advice lead to a good outcome? (Yes / Mostly / Partially / No)
  - **Safety:** Does this advice contain any errors that could harm the student's academic progress? (Critical error / Minor error / No error)
  - **Completeness:** Does this address everything the student needs to know? (Complete / Missing minor details / Missing major considerations)
  - **Actionability:** Could the student act on this advice without further clarification? (Yes / Needs clarification / No)

**Sample size and logistics:** 3-4 advisors, each evaluating outputs from all 5 systems on the same 60-80 queries. That's 300-400 evaluations per advisor — a lot, but feasible if spread over 1-2 weeks. Pay them or give them co-authorship credit. Report inter-annotator agreement (Krippendorff's alpha or Fleiss' kappa).

**Critical design choice: blinding.** Advisors should NOT know which system produced which response. Randomize the presentation order. This prevents bias toward or against the multi-agent system.

## 5. What Makes This ACL-Competitive

The benchmark is competitive if it has:

- **A principled taxonomy** that other researchers can apply to their own domains (not just CMU-Q specific)
- **Realistic, persona-grounded queries** that go beyond generic FAQ-style questions
- **Structured reference answers** that enable reproducible evaluation
- **Both automated and human evaluation** with inter-annotator agreement
- **A clear finding** about where system complexity is justified

The thing that elevates this from "a dataset" to "a contribution" is the analysis. The money table in the paper looks something like:

| | T1 | T2 | T3 | T4 | T5 | Overall |
|---|---|---|---|---|---|---|
| S3 (Single) | 91 | 85 | 72 | 54 | 38 | 68 |
| S4 (Single+CoT) | 93 | 88 | 78 | 61 | 45 | 73 |
| S2 (One-shot MA) | 92 | 87 | 83 | 74 | 58 | 79 |
| S1 (Full MA) | 93 | 89 | 87 | 82 | 71 | 84 |
| S0 (Full+Transparent) | 93 | 89 | 87 | 82 | 71 | 84 |

*(These numbers are illustrative, not predictions.)*

If the results show something like this pattern — convergence at T1-T2, divergence at T4-T5 — that's a clear, citable finding. The narrative becomes: "Multi-agent complexity is unjustified for simple queries but provides meaningful gains on constrained planning tasks, primarily because [specific mechanism X catches errors that single-agent misses]."

## Summary

The benchmark's competitive edge comes from three things: persona-grounded queries derived from real student data (not generic), structured reference answers with explicit reasoning requirements and known traps, and a dual evaluation (automated + blinded human) that lets you make credible claims. Combined with the ablation ladder your peer already built, this gives the paper both a reusable resource and empirical findings about when multi-agent complexity is justified. That's a paper worth publishing.

