# Gap Analysis: Current System vs. AIED 2026 Proposal B

## Proof-Carrying Academic Advising: Constraint-Verified Plans

---

## Executive Summary

This proposal represents a **fundamental shift** from your current architecture:

| Aspect | Current System | Proposal B Requires |
|--------|---------------|---------------------|
| **Core Approach** | LLM-driven multi-agent + RAG | Constraint Solver + Verification |
| **Output** | Natural language answer | Structured proof artifact + plan |
| **Validation** | None (trust LLM) | Formal constraint checking |
| **Evaluation** | User study (planned) | Solver-checkable benchmark (offline) |
| **Clarification** | LLM decides when to ask | SAT-based minimal question computation |

The good news: **Your existing infrastructure (agents, RAG, policy data) can be repurposed** as the foundation for this new architecture.

---

## 1. CONSTRAINT REPRESENTATION GAPS

### Gap 1.1: No Formal Constraint Language

**Current State:**
- Policies stored as markdown/text documents
- RAG retrieves text, LLM interprets
- No machine-checkable representation

**What Proposal B Requires:**
```python
# Hard constraints (must hold)
class Constraint:
    type: Literal["prerequisite", "unit_limit", "gpa_requirement", "degree_requirement"]
    expression: str  # e.g., "taken(15-122) before taken(15-213)"
    source: PolicyReference  # provenance
    hard: bool  # hard vs soft

# Example constraint library
CONSTRAINTS = [
    Constraint(
        type="prerequisite",
        expression="taken(15-112) → can_take(15-122)",
        source=PolicyRef("CS_Prereqs.md", line=45),
        hard=True
    ),
    Constraint(
        type="unit_limit",
        expression="semester_units ≤ 54",
        source=PolicyRef("Overload_Policy.md", section="2.1"),
        hard=True
    ),
    Constraint(
        type="degree_requirement",
        expression="count(CS_CORE_COURSES ∩ completed) ≥ 8",
        source=PolicyRef("CS_Requirements.md"),
        hard=True
    )
]
```

**Solution: Build `constraints/` Module**

```
constraints/
├── __init__.py
├── constraint_types.py      # Pydantic models for constraints
├── constraint_library.py    # 10-20 constraint templates
├── policy_to_constraints.py # Extract constraints from policy docs
└── constraint_validator.py  # Check if constraint is well-formed
```

### Gap 1.2: No Course/Prerequisite Graph

**Current State:**
- Prerequisites mentioned in RAG documents
- No structured graph representation
- Planning Agent guesses based on LLM

**What Proposal B Requires:**
```python
# Structured prerequisite DAG
class CourseGraph:
    nodes: Dict[str, Course]  # course_code → Course
    prerequisites: Dict[str, List[str]]  # course → [prereqs]
    corequisites: Dict[str, List[str]]
    offerings: Dict[str, List[Semester]]  # when offered

    def can_take(self, course: str, completed: Set[str]) -> bool:
        prereqs = self.prerequisites.get(course, [])
        return all(p in completed for p in prereqs)

    def earliest_semester(self, course: str, completed: Set[str]) -> int:
        # BFS through dependency chain
        pass
```

**Solution: Build `data/course_graph.json`**

Extract from your existing course data into structured format:
```json
{
  "15-112": {
    "name": "Fundamentals of Programming",
    "units": 12,
    "prerequisites": [],
    "corequisites": [],
    "offerings": ["Fall", "Spring"],
    "satisfies": ["CS_CORE", "FIRST_YEAR_REQ"]
  },
  "15-122": {
    "name": "Principles of Imperative Computation",
    "units": 12,
    "prerequisites": ["15-112"],
    "offerings": ["Fall", "Spring"],
    "satisfies": ["CS_CORE"]
  }
}
```

---

## 2. SOLVER INTEGRATION GAPS

### Gap 2.1: No Constraint Solver

**Current State:**
- Planning Agent uses LLM to generate plans
- No formal feasibility checking
- No optimization

**What Proposal B Requires:**
```python
from ortools.sat.python import cp_model

class AcademicPlanSolver:
    def __init__(self, constraints: List[Constraint], courses: CourseGraph):
        self.model = cp_model.CpModel()
        self.constraints = constraints
        self.courses = courses

    def solve(self, student_state: StudentState, goal: Goal) -> SolverResult:
        # Decision variables: take[course][semester] ∈ {0, 1}
        take = {}
        for course in self.courses.nodes:
            for sem in range(8):  # 8 semesters
                take[course, sem] = self.model.NewBoolVar(f"take_{course}_{sem}")

        # Add constraints
        self._add_prerequisite_constraints(take)
        self._add_unit_limit_constraints(take)
        self._add_degree_requirement_constraints(take, goal)

        # Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        if status == cp_model.OPTIMAL:
            return SolverResult(
                feasible=True,
                plan=self._extract_plan(solver, take),
                proof=self._generate_proof(solver)
            )
        else:
            return SolverResult(
                feasible=False,
                violated_constraints=self._get_violations(),
                proof=self._generate_infeasibility_proof()
            )
```

**Solution: Build `solver/` Module**

```
solver/
├── __init__.py
├── academic_solver.py       # OR-Tools CP-SAT integration
├── constraint_encoder.py    # Convert constraints to solver format
├── plan_extractor.py        # Extract plan from solution
└── proof_generator.py       # Generate proof artifacts
```

### Gap 2.2: No Verification Layer

**Current State:**
- LLM generates plan → accepted as-is
- No check if plan actually works

**What Proposal B Requires:**
```python
class PlanVerifier:
    def verify(self, plan: Plan, student: StudentState, policies: List[Constraint]) -> VerificationResult:
        violations = []
        satisfied = []

        for constraint in policies:
            if self._check_constraint(constraint, plan, student):
                satisfied.append(ConstraintStatus(constraint, "SATISFIED"))
            else:
                violations.append(ConstraintStatus(constraint, "VIOLATED",
                                                   reason=self._explain_violation(constraint, plan)))

        return VerificationResult(
            valid=len(violations) == 0,
            satisfied_constraints=satisfied,
            violated_constraints=violations,
            assumptions=self._extract_assumptions(plan)
        )
```

---

## 3. PROOF ARTIFACT GAPS

### Gap 3.1: No Structured Proof Output

**Current State:**
- Output is natural language answer
- Citations are strings, not structured references
- No machine-readable justification

**What Proposal B Requires:**
```python
@dataclass
class ProofArtifact:
    """Machine-readable proof that plan is correct"""

    plan: StructuredPlan  # The recommended plan

    # Constraints satisfied with provenance
    satisfied_constraints: List[ConstraintProof]

    # Assumptions made (what we assumed to be true)
    assumptions: List[Assumption]

    # Trade-offs and alternatives
    alternatives: List[AlternativePlan]
    trade_offs: List[TradeOff]

    # Provenance chain
    policy_citations: List[PolicyReference]

@dataclass
class ConstraintProof:
    constraint: Constraint
    status: Literal["SATISFIED", "SATISFIED_WITH_ASSUMPTION"]
    evidence: str  # How it was satisfied
    source: PolicyReference

@dataclass
class Assumption:
    variable: str  # e.g., "student.available_fall_2026"
    assumed_value: Any
    impact: str  # What happens if assumption is wrong
```

**Solution: Build `proof/` Module**

```
proof/
├── __init__.py
├── proof_artifact.py        # Pydantic models for proofs
├── proof_generator.py       # Generate proofs from solver output
├── proof_renderer.py        # Render proof as JSON/markdown
└── provenance_tracker.py    # Track policy citations
```

---

## 4. CLARIFICATION MODULE GAPS

### Gap 4.1: LLM-Based vs SAT-Based Clarification

**Current State (clarification_handler.py):**
- LLM decides when to ask questions
- Questions based on heuristics, not formal analysis
- May ask unnecessary questions or miss critical ones

**What Proposal B Requires:**
```python
class MinimalClarificationComputer:
    """Compute minimal questions needed to determine feasibility"""

    def compute_needed_clarifications(self,
                                      student: StudentState,
                                      goal: Goal,
                                      constraints: List[Constraint]) -> List[Question]:
        # Find variables that are UNKNOWN but affect feasibility
        unknown_vars = self._find_unknown_variables(student)

        # For each unknown, check if it affects feasibility
        critical_unknowns = []
        for var in unknown_vars:
            # Check: Is the problem feasible with var=True? var=False?
            feasible_if_true = self.solver.check_sat(constraints, {var: True})
            feasible_if_false = self.solver.check_sat(constraints, {var: False})

            if feasible_if_true != feasible_if_false:
                # This variable determines feasibility!
                critical_unknowns.append(var)

        # Generate minimal question set
        return self._generate_questions(critical_unknowns)
```

**Solution: Modify Clarification Logic**

Replace LLM-based clarification with solver-based:
```python
# Instead of:
clarification_check = self.clarification_handler.check_for_clarification(query, ...)

# Do:
clarification_check = self.solver.compute_minimal_clarifications(student_state, goal)
```

---

## 5. BENCHMARK GAPS (Most Critical for Publishability)

### Gap 5.1: No AdvisingBench Dataset

**Current State:**
- No systematic test cases
- No ground truth
- Evaluation requires user study

**What Proposal B Requires:**
```python
# Scenario structure
@dataclass
class AdvisingScenario:
    id: str
    description: str

    # Inputs
    student_state: StudentState
    goal: Goal
    preferences: Optional[Preferences]

    # Ground truth (solver-generated)
    ground_truth: GroundTruth

@dataclass
class GroundTruth:
    feasibility: Literal["FEASIBLE", "INFEASIBLE", "UNDER_SPECIFIED"]

    # If feasible
    valid_plans: List[Plan]  # Set of correct plans

    # If infeasible
    violated_constraints: List[Constraint]  # Minimal violation set

    # If under-specified
    required_clarifications: List[str]  # Variables needed

# Scenario families (from outline)
SCENARIO_FAMILIES = [
    "adding_minor_with_prereqs",
    "switching_majors_credit_transfer",
    "overload_request",
    "accelerate_graduation",
    "retake_policy_gpa",
    "intentionally_infeasible",
    "missing_information_clarification"
]
```

**Solution: Build `benchmark/` Module**

```
benchmark/
├── __init__.py
├── scenario_generator.py    # Generate synthetic scenarios
├── ground_truth_solver.py   # Compute ground truth via solver
├── scenarios/
│   ├── adding_minor.json    # 50 scenarios
│   ├── switching_major.json # 50 scenarios
│   └── ...
├── evaluator.py             # Compute metrics
└── metrics.py               # Define metrics
```

### Gap 5.2: No Automated Metrics

**Current State:**
- No evaluation code
- Would need manual inspection

**What Proposal B Requires:**
```python
class AdvisingMetrics:
    def feasibility_rate(self, predictions: List[PlanResult], ground_truth: List[GroundTruth]) -> float:
        """% of plans that are actually feasible"""
        correct = sum(1 for p, gt in zip(predictions, ground_truth)
                      if self.solver.verify(p.plan) == gt.feasibility)
        return correct / len(predictions)

    def violation_explanation_accuracy(self, predictions, ground_truth) -> float:
        """For infeasible cases, did system cite correct violated constraints?"""
        pass

    def clarification_efficiency(self, predictions, ground_truth) -> float:
        """How many questions until feasible output?"""
        pass

    def provenance_coverage(self, predictions) -> float:
        """% of constraints with provenance attached"""
        pass
```

---

## 6. ARCHITECTURE TRANSFORMATION

### Current Architecture vs. Proposal B Architecture

```
CURRENT ARCHITECTURE:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Query     │ ──► │ Coordinator │ ──► │   Agents    │
└─────────────┘     │  (LLM-based)│     │ (RAG + LLM) │
                    └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────────────────────┐
                    │      Natural Language       │
                    │          Answer             │
                    └─────────────────────────────┘


PROPOSAL B ARCHITECTURE:
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Query     │ ──► │   Parser    │ ──► │  Student    │
│             │     │ (LLM-based) │     │   State     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          ▼                          │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │           CONSTRAINT LAYER                   │   │
                    │  │  ┌───────────┐  ┌───────────┐  ┌──────────┐ │   │
                    │  │  │Prereq DAG │  │Unit Limits│  │Degree Req│ │   │
                    │  │  └───────────┘  └───────────┘  └──────────┘ │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                          │                          │
                    │                          ▼                          │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │              SOLVER (OR-Tools)               │   │
                    │  │   • Plan generation                          │   │
                    │  │   • Feasibility checking                     │   │
                    │  │   • Minimal clarification computation        │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                          │                          │
                    │                          ▼                          │
                    │  ┌─────────────────────────────────────────────┐   │
                    │  │              VERIFIER                        │   │
                    │  │   • Check all constraints                    │   │
                    │  │   • Generate proof artifact                  │   │
                    │  └─────────────────────────────────────────────┘   │
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               ▼
                    ┌─────────────────────────────────────────────────────┐
                    │                 PROOF ARTIFACT                       │
                    │  • Verified plan (structured)                        │
                    │  • Constraints satisfied + provenance                │
                    │  • Assumptions                                       │
                    │  • Trade-offs and alternatives                       │
                    └─────────────────────────────────────────────────────┘
                                               │
                                               ▼
                    ┌─────────────────────────────────────────────────────┐
                    │              EXPLANATION GENERATOR                   │
                    │           (LLM for natural language)                 │
                    └─────────────────────────────────────────────────────┘
```

---

## 7. IMPLEMENTATION ROADMAP

### Phase 1: Constraint Foundation (Week 1-2)

**Files to Create:**

```
constraints/
├── __init__.py
├── models.py                # Constraint, StudentState, Goal models
├── course_graph.py          # Prerequisite DAG
├── constraint_library.py    # 15-20 constraint templates
└── policy_extractor.py      # (Optional) LLM extracts constraints
```

**Tasks:**
1. Define Pydantic models for constraints, student state, goals
2. Build course graph from existing course data
3. Create constraint templates for:
   - Prerequisites (10 templates)
   - Unit limits (3 templates)
   - Degree requirements (5 templates)
   - GPA requirements (2 templates)

### Phase 2: Solver Integration (Week 2-3)

**Files to Create:**

```
solver/
├── __init__.py
├── academic_solver.py       # Main solver class
├── encoder.py               # Constraint → solver variables
├── decoder.py               # Solution → Plan
└── clarification_solver.py  # Minimal clarification computation
```

**Tasks:**
1. Install OR-Tools: `pip install ortools`
2. Implement constraint encoding for each type
3. Implement plan extraction from solution
4. Implement minimal clarification computation

### Phase 3: Verification & Proof (Week 3-4)

**Files to Create:**

```
proof/
├── __init__.py
├── verifier.py              # Plan verification
├── proof_artifact.py        # Proof data structures
├── proof_generator.py       # Generate proofs
└── proof_renderer.py        # Render as JSON/markdown
```

**Tasks:**
1. Implement verification logic
2. Define proof artifact schema
3. Generate provenance links to policies
4. Render proofs for human inspection

### Phase 4: Benchmark (Week 4-5)

**Files to Create:**

```
benchmark/
├── __init__.py
├── scenario_generator.py
├── ground_truth.py
├── evaluator.py
├── metrics.py
└── scenarios/
    ├── adding_minor_50.json
    ├── switching_major_50.json
    ├── overload_50.json
    ├── accelerate_graduation_50.json
    ├── retake_gpa_50.json
    ├── infeasible_50.json
    └── clarification_50.json
```

**Tasks:**
1. Generate 50 scenarios per family (350 total)
2. Compute ground truth for each scenario
3. Implement evaluation metrics
4. Run baselines and full system

### Phase 5: Baselines & Experiments (Week 5-6)

**Baselines to Implement:**
1. **RAG-only:** Your current system (answer with citations, no verifier)
2. **LLM Planner:** Planning Agent alone (no solver)
3. **LLM + Verifier:** LLM proposes, solver verifies only (no repair)
4. **Full System:** LLM proposes, solver verifies, repairs, proof output

---

## 8. REUSABLE COMPONENTS FROM CURRENT SYSTEM

| Current Component | Reuse For |
|-------------------|-----------|
| RAG engines (courses, policies, programs) | Policy extraction, natural language generation |
| `blackboard/schema.py` | Extend with constraint types |
| `planning_tools.py` | Course data loading |
| Course JSON data | Build course graph |
| Policy markdown files | Constraint extraction source |
| `clarification_handler.py` | Fallback for LLM-based clarification |
| Streamlit UI | Demo visualization of proofs |

---

## 9. KEY DIFFERENCES TABLE

| Aspect | Current (Multi-Agent) | Proposal B (Constraint-Verified) |
|--------|----------------------|----------------------------------|
| **Core Innovation** | Agent negotiation | Solver verification + proofs |
| **Evaluation** | User study required | Offline benchmark (no users) |
| **Correctness** | LLM says it's correct | Solver proves it's correct |
| **Output Format** | Natural language | Structured proof + NL explanation |
| **Clarification** | LLM heuristics | SAT-based minimal questions |
| **Publishability** | Harder (need users) | Easier (automated metrics) |
| **Research Contribution** | Coordination protocols | Verified planning + benchmark |

---

## 10. CONCRETE NEXT STEPS

### This Week:
1. **Install OR-Tools** and run a simple course scheduling example
2. **Create `data/course_graph.json`** from your existing course data
3. **Define 5 constraint templates** (prereqs, unit limits, degree reqs)

### Week 2:
1. **Implement basic solver** that can generate a feasible 8-semester plan
2. **Implement verifier** that checks if plan satisfies constraints

### Week 3:
1. **Implement proof artifact generation**
2. **Generate 100 benchmark scenarios**
3. **Compute ground truth for scenarios**

### Week 4:
1. **Run baselines on benchmark**
2. **Compute metrics**
3. **Start paper writing**

---

## 11. SUMMARY

**Proposal B is fundamentally different** from your current system:

| You Have | You Need |
|----------|----------|
| LLM-driven coordination | Solver-based planning |
| RAG for policy retrieval | Constraints as formal language |
| Natural language output | Structured proof artifacts |
| User study for evaluation | Solver-checkable benchmark |

**The transformation path:**
1. **Keep your RAG infrastructure** for policy extraction and NL generation
2. **Add a constraint layer** on top of your policy documents
3. **Add a solver** (OR-Tools) for plan generation and verification
4. **Add proof generation** for explainability
5. **Build benchmark** for offline evaluation

This approach is **more publishable** because:
- No IRB needed (no real students)
- Automated evaluation (reproducible)
- Formal correctness claims (verifiable)
- Novel contribution (proof-carrying advising)

---

## 12. PAPER OUTLINE REFERENCE

Based on the provided outline:

### Title Options:
- "Proof-Carrying Academic Advising: Constraint-Verified Plans with Minimal Clarification"
- "From Policy QA to Verified Plan Synthesis for Academic Advising"
- "AdvisingBench: Solver-Checked Evaluation for Academic Advisor Agents"

### Key Sections:
1. **Introduction**: Advising = constraint satisfaction + preferences, not just QA
2. **Background**: RAG bots vs CP approaches vs our hybrid
3. **Task Definition**: Inputs (S, P, G, U) → Outputs (Plan, Questions, Proof)
4. **System**: Constraint layer + Solver + Verifier + Clarification + Proof generator
5. **AdvisingBench**: 350 scenarios, 7 families, solver-generated ground truth
6. **Experiments**: 4 baselines, 2 ablations, automated metrics
7. **Discussion**: What improves and what doesn't
8. **Limitations**: Institutional variability, constraint coverage, fairness

### Minimum Viable Implementation:
- 10-20 constraint templates
- OR-Tools CP-SAT backend
- 100-500 generated scenarios
- Proof artifact wrapper

---

**Document Version:** 1.0
**Last Updated:** January 19, 2026
**Related Files:**
- `ACL2026_GAP_ANALYSIS.md` (Multi-agent proposal)
- `ACL2026_RESEARCH_ROADMAP.md` (Multi-agent roadmap)
- `RESEARCH_DOCUMENTATION.md` (Current system docs)
