# ACL 2026 Implementation Plan
## From Current System to Publication-Ready Research

Based on gap analysis and advisor feedback

---

## Timeline Overview

**Target:** ACL 2026 Demo Track Submission (June 2026)

- **Phase 1:** Negotiation Mechanisms (Feb 2026) - 4 weeks
- **Phase 2:** Interactive Conflicts (Mar 2026) - 3 weeks  
- **Phase 3:** Evaluation Framework (Apr 2026) - 4 weeks
- **Phase 4:** Paper Writing (May-Jun 2026) - 6 weeks

**Total:** 17 weeks (achievable!)

---

## Phase 1: Structured Negotiation Protocol (Feb 2026)

### Goal
Implement visible, structured negotiation between agents

### Why This Matters
**Advisor feedback:** "To be taken seriously in a research paper, I'd define one or two specific mechanisms"

This is your **core research contribution** - without this, you just have "fancy routing."

### Week 1: Design Negotiation Protocol

**Tasks:**
1. Define negotiation data structures
2. Design proposal + critique protocol
3. Write negotiation flow diagram
4. Get advisor approval on design

**Deliverables:**
```python
# coordinator/negotiation_types.py

class Proposal(BaseModel):
    """A plan proposed by an agent"""
    agent_name: str
    plan_type: Literal["semester_plan", "degree_plan", "course_selection"]
    content: Dict[str, Any]  # Structured plan data
    justification: str
    confidence: float
    assumptions: List[str]
    policy_citations: List[PolicyCitation]
    
class Critique(BaseModel):
    """Critique of a proposal by another agent"""
    critic_agent: str
    target_proposal_id: str
    approval_status: Literal["approved", "rejected", "conditional"]
    violations: List[PolicyViolation]
    risks: List[Risk]
    suggested_modifications: List[str]
    confidence: float

class NegotiationRound(BaseModel):
    """One round of negotiation"""
    round_number: int
    proposal: Proposal
    critiques: List[Critique]
    resolution: Optional[Resolution]
    needs_user_input: bool
```

### Week 2: Implement Proposal Generation

**Tasks:**
1. Update Programs Agent to generate structured proposals
2. Add justification and confidence to proposals
3. Update blackboard to store proposals
4. Test proposal generation

**Code Changes:**
```python
# agents/programs_agent.py

def propose_plan(self, state: BlackboardState) -> Proposal:
    """
    Generate a structured plan proposal
    """
    # Analyze requirements
    requirements = self.analyze_requirements(state.student_profile)
    
    # Generate plan
    plan = self.generate_semester_plan(requirements)
    
    # Create proposal with justification
    proposal = Proposal(
        agent_name="programs_requirements",
        plan_type="semester_plan",
        content=plan,
        justification=self.explain_plan(plan, requirements),
        confidence=self.calculate_confidence(plan),
        assumptions=self.extract_assumptions(plan),
        policy_citations=self.cite_relevant_policies(plan)
    )
    
    return proposal
```

### Week 3: Implement Critique Generation

**Tasks:**
1. Update Policy Agent to critique proposals
2. Add violation detection logic
3. Add risk assessment
4. Test critique generation

**Code Changes:**
```python
# agents/policy_agent.py

def critique_proposal(self, proposal: Proposal, state: BlackboardState) -> Critique:
    """
    Critique a proposal for policy compliance
    """
    # Check for violations
    violations = self.check_policy_violations(proposal)
    
    # Assess risks
    risks = self.assess_risks(proposal)
    
    # Suggest modifications if needed
    modifications = []
    if violations:
        modifications = self.suggest_fixes(violations, proposal)
    
    # Determine approval status
    if any(v.severity == "hard" for v in violations):
        status = "rejected"
    elif risks or violations:
        status = "conditional"
    else:
        status = "approved"
    
    return Critique(
        critic_agent="policy_compliance",
        target_proposal_id=proposal.id,
        approval_status=status,
        violations=violations,
        risks=risks,
        suggested_modifications=modifications,
        confidence=0.95
    )
```

### Week 4: Implement Negotiation Coordinator

**Tasks:**
1. Build negotiation loop in coordinator
2. Implement mediation logic
3. Add iteration limits (max 3 rounds)
4. Test full negotiation cycle

**Code Changes:**
```python
# coordinator/negotiation_protocol.py

class NegotiationProtocol:
    
    def run_negotiation(self, state: BlackboardState, max_rounds: int = 3):
        """
        Run proposal + critique negotiation cycle
        """
        for round_num in range(max_rounds):
            print(f"\n🔄 Negotiation Round {round_num + 1}")
            
            # Step 1: Agent proposes
            proposal = self.get_proposal_agent(state).propose_plan(state)
            state.negotiation_history.append({"type": "proposal", "data": proposal})
            print(f"   📝 {proposal.agent_name} proposes: {proposal.plan_type}")
            
            # Step 2: Critics review
            critiques = []
            for critic_name in self.get_critic_agents(proposal):
                critique = self.agents[critic_name].critique_proposal(proposal, state)
                critiques.append(critique)
                state.negotiation_history.append({"type": "critique", "data": critique})
                print(f"   🔍 {critic_name} critiques: {critique.approval_status}")
            
            # Step 3: Mediate
            resolution = self.mediate(proposal, critiques, state)
            
            # Step 4: Check if done
            if resolution.is_final:
                print(f"   ✅ Negotiation complete: {resolution.outcome}")
                return resolution
            
            # Step 5: Check if need user input
            if resolution.needs_user_input:
                print(f"   ⚠️  User input required")
                return resolution  # Pause for user
            
            # Step 6: Revise and continue
            print(f"   🔄 Revising based on critiques...")
        
        # Max rounds reached
        return self.fallback_resolution(state)
    
    def mediate(self, proposal: Proposal, critiques: List[Critique], state: BlackboardState):
        """
        Mediate between proposal and critiques
        """
        # Count approvals/rejections
        approved = [c for c in critiques if c.approval_status == "approved"]
        rejected = [c for c in critiques if c.approval_status == "rejected"]
        conditional = [c for c in critiques if c.approval_status == "conditional"]
        
        # Hard violations = rejected
        if rejected:
            return Resolution(
                outcome="rejected",
                reason=f"Hard policy violations: {rejected[0].violations}",
                is_final=True
            )
        
        # All approved = accept
        if len(approved) == len(critiques):
            return Resolution(
                outcome="accepted",
                plan=proposal,
                is_final=True
            )
        
        # Conditional = needs revision or user input
        if conditional:
            # Can we auto-fix?
            if self.can_auto_resolve(conditional):
                revised_proposal = self.apply_modifications(proposal, conditional)
                return Resolution(
                    outcome="revised",
                    plan=revised_proposal,
                    is_final=False  # Continue negotiation
                )
            else:
                # Need user to decide
                return Resolution(
                    outcome="needs_user_input",
                    conflicting_requirements=self.extract_conflicts(conditional),
                    options=self.generate_options(proposal, conditional),
                    is_final=False,
                    needs_user_input=True
                )
```

**Deliverable:** Working negotiation demo showing:
- Programs Agent proposes plan
- Policy Agent critiques (finds violations)
- Coordinator mediates
- Either: accept, reject, revise, or ask user

---

## Phase 2: Interactive Conflict Resolution (Mar 2026)

### Goal
Make conflicts visible and let users participate in resolution

### Why This Matters
**Advisor feedback:** "This is exactly how you can differentiate from 'just a smarter chatbot'"

### Week 5: Define Conflict Types

**Tasks:**
1. Implement 3 canonical conflict types
2. Design UI widgets for each type
3. Write interaction flows
4. Create mockups

**Canonical Conflict Types:**

```python
# coordinator/conflicts.py

class ConflictType(str, Enum):
    HARD_VIOLATION = "hard_violation"  # Plan impossible (block)
    HIGH_RISK = "high_risk"            # Plan risky (warn + confirm)
    TRADE_OFF = "trade_off"            # Multiple options (let user choose)

class ConflictWidget:
    """Base class for conflict UI"""
    
    def show_hard_violation(self, conflict):
        """
        Block the plan and explain why
        """
        print("\n" + "="*80)
        print("🚫 PLAN BLOCKED: Policy Violation")
        print("="*80)
        print(f"\n{conflict.description}")
        print(f"\nViolated Policy:")
        for v in conflict.violations:
            print(f"  • {v.policy_id}: {v.description}")
            print(f"    Citation: {v.citation}")
        print(f"\nWhat this means:")
        print(f"  {conflict.explanation}")
        print(f"\nSuggested alternatives:")
        for alt in conflict.alternatives:
            print(f"  • {alt}")
    
    def show_high_risk_warning(self, conflict):
        """
        Warn about risks and get confirmation
        """
        print("\n" + "="*80)
        print("⚠️  HIGH-RISK PLAN DETECTED")
        print("="*80)
        print(f"\n{conflict.description}")
        print(f"\nIdentified Risks:")
        for r in conflict.risks:
            severity_icon = "🔴" if r.severity == "high" else "🟡"
            print(f"  {severity_icon} {r.description}")
            print(f"     Impact: {r.impact}")
        print(f"\nPolicy Guidance:")
        for p in conflict.policy_guidance:
            print(f"  • {p}")
        
        choice = input("\n⚠️  Do you want to proceed despite these risks? (yes/no): ")
        return choice.lower() == 'yes'
    
    def show_tradeoff_options(self, conflict):
        """
        Show multiple valid options and let user choose
        """
        print("\n" + "="*80)
        print("⚖️  DECISION POINT: Multiple Valid Paths")
        print("="*80)
        print(f"\n{conflict.description}")
        
        for i, option in enumerate(conflict.options, 1):
            print(f"\n{'='*40}")
            print(f"Option {i}: {option.title}")
            print(f"{'='*40}")
            
            print(f"\n✅ Advantages:")
            for pro in option.pros:
                print(f"   • {pro}")
            
            print(f"\n❌ Disadvantages:")
            for con in option.cons:
                print(f"   • {con}")
            
            print(f"\n📊 Metrics:")
            print(f"   Time to graduate: {option.semesters_to_graduate} semesters")
            print(f"   Difficulty: {option.difficulty}/5")
            print(f"   Workload: {option.workload} units/semester avg")
            print(f"   Confidence: {option.confidence:.1%}")
        
        while True:
            choice = input(f"\nWhich option do you prefer? (1-{len(conflict.options)}/skip): ")
            if choice in [str(i) for i in range(1, len(conflict.options)+1)] or choice == 'skip':
                return choice
            print("Invalid choice, please try again.")
```

### Week 6: Implement Conflict Detection

**Tasks:**
1. Add conflict detection in negotiation
2. Classify conflicts by type
3. Extract conflict details
4. Test detection logic

**Code Changes:**
```python
# coordinator/conflict_detection.py

class ConflictDetector:
    
    def detect_conflicts(self, proposal: Proposal, critiques: List[Critique]) -> List[Conflict]:
        """
        Detect and classify conflicts from negotiation
        """
        conflicts = []
        
        # Hard violations
        hard_violations = [v for c in critiques for v in c.violations if v.severity == "hard"]
        if hard_violations:
            conflicts.append(Conflict(
                type=ConflictType.HARD_VIOLATION,
                description="Plan violates university policies",
                violations=hard_violations,
                alternatives=self.generate_alternatives(proposal, hard_violations)
            ))
        
        # High risks
        high_risks = [r for c in critiques for r in c.risks if r.severity == "high"]
        if high_risks:
            conflicts.append(Conflict(
                type=ConflictType.HIGH_RISK,
                description="Plan is possible but carries significant risks",
                risks=high_risks,
                policy_guidance=self.get_policy_guidance(high_risks)
            ))
        
        # Trade-offs (multiple valid modifications suggested)
        if len([c for c in critiques if c.suggested_modifications]) >= 2:
            options = self.generate_tradeoff_options(proposal, critiques)
            conflicts.append(Conflict(
                type=ConflictType.TRADE_OFF,
                description="Multiple valid paths forward",
                options=options
            ))
        
        return conflicts
```

### Week 7: Integrate Interactive Resolution

**Tasks:**
1. Add conflict widgets to chat interface
2. Handle user input during negotiation
3. Resume negotiation after user input
4. Test full interactive flow

**Code Changes:**
```python
# chat.py - add conflict handling

def handle_conflict(conflict: Conflict) -> Resolution:
    """
    Show conflict to user and get their input
    """
    widget = ConflictWidget()
    
    if conflict.type == ConflictType.HARD_VIOLATION:
        widget.show_hard_violation(conflict)
        # No choice - blocked
        return Resolution(outcome="rejected", reason="Policy violation")
    
    elif conflict.type == ConflictType.HIGH_RISK:
        proceed = widget.show_high_risk_warning(conflict)
        if proceed:
            return Resolution(outcome="accepted_with_risks", risks=conflict.risks)
        else:
            return Resolution(outcome="rejected", reason="User declined risks")
    
    elif conflict.type == ConflictType.TRADE_OFF:
        choice = widget.show_tradeoff_options(conflict)
        if choice == 'skip':
            return Resolution(outcome="deferred", reason="User wants to think")
        else:
            option_idx = int(choice) - 1
            return Resolution(
                outcome="accepted",
                chosen_option=conflict.options[option_idx]
            )
```

**Deliverable:** Interactive conflict demo showing:
- Hard violation blocked with explanation
- High risk warned with confirmation
- Trade-off presented with user choice

---

## Phase 3: Evaluation Framework (Apr 2026)

### Goal
Prove your approach works better than baselines

### Why This Matters
**Advisor feedback:** "To make it publishable, you need explicit research questions and evaluation plan"

### Week 8: Create Test Dataset

**Tasks:**
1. Collect 50 real advising scenarios
2. Get gold-standard answers from advisors
3. Categorize scenarios
4. Document ground truth

**Scenario Categories:**

```
1. Simple Queries (10 scenarios)
   - "What are prerequisites for 15-213?"
   - "When is 67-364 offered?"
   - "What courses satisfy Gen Ed requirement?"

2. Complex Multi-Agent (10 scenarios)
   - "I got a D in 15-112, do I need to retake?"
   - "Can I add CS minor as IS major?"
   - "I want to study abroad, how does it affect graduation?"

3. Conflict Scenarios (10 scenarios)
   - "I want to take 6 courses next semester" (overload)
   - "Can I take 15-213 without 15-122?" (prerequisite)
   - "I need to graduate in 3 years" (accelerated)

4. Trade-off Scenarios (10 scenarios)
   - "Should I take harder courses or maintain GPA?"
   - "Study abroad vs. internship?"
   - "Double major vs. graduate early?"

5. Edge Cases (10 scenarios)
   - Ambiguous queries
   - Missing information
   - Policy exceptions
   - Transfer credit issues
```

**Gold Standard Format:**
```json
{
  "scenario_id": "complex_001",
  "category": "complex_multi_agent",
  "query": "I probably will get a D in 15-112 this semester. As a CS student, do I need to retake it next semester?",
  "student_context": {
    "major": "Computer Science",
    "current_semester": 3,
    "gpa": 3.2,
    "completed_courses": ["15-110", "15-112"]
  },
  "gold_answer": {
    "decision": "Yes, you need to retake 15-112",
    "reasoning": "CS major requires C or better in core courses. 15-112 is a core course.",
    "policy_citations": [
      "CS_Major_Requirements.pdf#page5: 'Core courses require C or better'",
      "University_Grading_Policy.pdf#page3: 'D is passing university-wide but may not satisfy major requirements'"
    ],
    "required_agents": ["policy_compliance", "programs_requirements"],
    "risks": ["Delayed graduation", "May affect course sequencing"],
    "alternatives": ["Retake in Spring", "Retake in Summer"]
  },
  "evaluator": "Dr. Smith (Academic Advisor)",
  "date": "2026-04-01"
}
```

### Week 9: Implement Baseline Systems

**Tasks:**
1. Build Single-Agent RAG baseline
2. Build Rule-Based Multi-Agent baseline
3. Build Static Multi-Agent baseline
4. Test all systems on dataset

**Baseline 1: Single-Agent RAG**
```python
# evaluation/baselines/single_agent_rag.py

class SingleAgentRAG:
    """
    Baseline: One agent with all knowledge
    """
    def __init__(self):
        # Merge all knowledge bases
        self.knowledge_base = self.merge_all_domains()
        self.llm = ChatOpenAI(model="gpt-4o")
    
    def answer(self, query: str) -> str:
        # Retrieve from combined knowledge base
        docs = self.knowledge_base.similarity_search(query, k=10)
        
        # Generate answer with all context
        prompt = f"Answer this advising question:\n{query}\n\nContext:\n{docs}"
        return self.llm.invoke(prompt)
```

**Baseline 2: Rule-Based Multi-Agent**
```python
# evaluation/baselines/rule_based.py

class RuleBasedRouter:
    """
    Baseline: Fixed routing rules (no LLM)
    """
    def route(self, query: str) -> List[str]:
        query_lower = query.lower()
        
        # Simple keyword matching
        agents = []
        if any(kw in query_lower for kw in ["prerequisite", "course", "offering"]):
            agents.append("course_scheduling")
        if any(kw in query_lower for kw in ["major", "minor", "requirement", "graduate"]):
            agents.append("programs_requirements")
        if any(kw in query_lower for kw in ["policy", "overload", "retake", "grade"]):
            agents.append("policy_compliance")
        
        return agents if agents else ["programs_requirements"]  # Default
```

**Baseline 3: Static Multi-Agent**
```python
# evaluation/baselines/static_multi_agent.py

class StaticMultiAgent:
    """
    Baseline: Multi-agent with LLM routing but no negotiation
    """
    def process(self, query: str) -> str:
        # LLM classifies intent
        intent = self.coordinator.classify_intent(query)
        
        # Execute agents in parallel (no negotiation)
        outputs = {}
        for agent_name in intent['required_agents']:
            outputs[agent_name] = self.agents[agent_name].execute(query)
        
        # Simple concatenation (no mediation)
        return self.concatenate_outputs(outputs)
```

### Week 10: Run Evaluation

**Tasks:**
1. Run all systems on test dataset
2. Collect automatic metrics
3. Collect human ratings
4. Analyze results

**Automatic Metrics:**
```python
# evaluation/metrics.py

def evaluate_correctness(system_answer: str, gold_answer: dict) -> float:
    """
    Compare system answer to gold standard
    """
    # Check if decision matches
    decision_match = check_decision_match(system_answer, gold_answer['decision'])
    
    # Check if key reasoning points covered
    reasoning_coverage = check_reasoning_coverage(
        system_answer, 
        gold_answer['reasoning']
    )
    
    # Check if policies cited
    policy_citation_recall = check_policy_citations(
        system_answer,
        gold_answer['policy_citations']
    )
    
    return (decision_match * 0.5 + 
            reasoning_coverage * 0.3 + 
            policy_citation_recall * 0.2)

def evaluate_safety(system_answer: str, gold_answer: dict) -> bool:
    """
    Check if answer violates any policies
    """
    # Extract recommendations
    recommendations = extract_recommendations(system_answer)
    
    # Check each against policies
    for rec in recommendations:
        if violates_policy(rec):
            return False  # Unsafe
    
    return True  # Safe
```

**Human Evaluation Protocol:**
```python
# evaluation/human_eval.py

# Show advisors system outputs (blinded)
# Ask them to rate on 1-5 scale:

RATING_CRITERIA = {
    "correctness": "Is the advice factually correct?",
    "completeness": "Does it cover all relevant aspects?",
    "clarity": "Is the explanation clear and well-organized?",
    "safety": "Would you trust this advice for a real student?",
    "helpfulness": "Would this help the student make a decision?"
}

# For each scenario:
# - Show query + student context
# - Show system output (blinded - don't reveal which system)
# - Ask advisor to rate on each criterion
# - Collect qualitative feedback
```

### Week 11: Analysis and Ablation

**Tasks:**
1. Compare systems statistically
2. Run ablation studies
3. Analyze failure cases
4. Document findings

**Ablation Studies:**
```
1. Effect of LLM Coordination
   - Rule-based routing vs. LLM-driven
   - Measure: Agent selection accuracy, answer quality
   
2. Effect of Negotiation
   - Static multi-agent vs. with negotiation
   - Measure: Policy violation rate, risk detection
   
3. Effect of Interactive Resolution
   - System decides vs. user decides on conflicts
   - Measure: User satisfaction, decision alignment
   
4. Effect of Number of Agents
   - 1 agent vs. 3 agents vs. 5 agents
   - Measure: Answer quality, efficiency (tokens/latency)
```

**Deliverable:** Complete evaluation results showing:
- Your system outperforms baselines
- Negotiation reduces policy violations
- Interactive resolution improves satisfaction
- Statistical significance tests

---

## Phase 4: Paper Writing (May-Jun 2026)

### Goal
Write and submit ACL 2026 Demo Track paper

### Week 12-13: Paper Draft

**Paper Structure:**

```
Title: "Structured Negotiation in Multi-Agent Academic Advising: 
        LLM-Driven Coordination with Interactive Conflict Resolution"

Abstract (150 words)
- Problem: Academic advising is complex, multi-faceted
- Gap: Existing systems use single agents or simple routing
- Solution: Multi-agent with structured negotiation + interactive conflicts
- Results: X% better correctness, Y% fewer violations, Z% higher satisfaction

1. Introduction
   - Academic advising challenges
   - Multi-agent systems for complex domains
   - Our contribution: negotiation mechanisms
   
2. Related Work
   - Multi-agent systems
   - LLM-based coordination
   - Academic advising systems
   
3. System Architecture
   - Overview (coordinator + agents + blackboard)
   - LLM-driven coordinator
   - Structured negotiation protocol
   - Interactive conflict resolution
   
4. Negotiation Mechanisms
   - Proposal + critique protocol (Algorithm 1)
   - Conflict classification (3 types)
   - Mediation strategies
   
5. Evaluation
   - Research questions
   - Test dataset (50 scenarios)
   - Baseline systems
   - Metrics
   - Results
     - RQ1: Multi-agent > single-agent
     - RQ2: Negotiation > static
     - RQ3: Interactive > automatic
   - Ablation studies
   
6. Demo System
   - User interface
   - Example scenarios
   - Visible negotiation
   - Interactive widgets
   
7. Discussion
   - Insights
   - Limitations
   - Future work
   
8. Conclusion

References
```

### Week 14: Demo Video

**Tasks:**
1. Record system demo (3-5 minutes)
2. Show key features
3. Highlight research contributions
4. Edit and polish

**Demo Script:**
```
[0:00-0:30] Introduction
- "Academic advising is complex..."
- "We present a multi-agent system with structured negotiation"

[0:30-1:30] System Overview
- Architecture diagram
- 3 specialized agents
- LLM-driven coordinator
- Blackboard pattern

[1:30-3:00] Negotiation Demo
- Show real query: "Can I add CS minor?"
- Programs Agent proposes plan
- Policy Agent critiques (finds overload issue)
- Coordinator mediates
- User presented with options

[3:00-4:00] Interactive Conflict
- Show trade-off scenario
- User chooses between options
- System adapts workflow
- Final answer with citations

[4:00-4:30] Results Highlight
- Graph showing improvement over baselines
- Key statistics

[4:30-5:00] Conclusion
- Research contributions
- Future work
```

### Week 15-16: Revisions

**Tasks:**
1. Get advisor feedback on draft
2. Revise paper
3. Polish demo video
4. Prepare supplementary materials

### Week 17: Submission

**Tasks:**
1. Final proofread
2. Format according to ACL guidelines
3. Submit paper + demo video
4. Submit code repository

**Deliverable:** ACL 2026 Demo Track submission!

---

## Research Questions (Final Version)

**RQ1 (Main):** Does multi-agent coordination with structured negotiation improve the quality and safety of academic advising recommendations compared to single-agent systems?

**Hypothesis:** Multi-agent with negotiation will have:
- Higher correctness (>15% improvement)
- Lower policy violation rate (<5% violations vs. 15% for baseline)
- Higher safety ratings from advisors

**RQ2:** Does the proposal-critique negotiation protocol improve conflict detection and resolution compared to static multi-agent systems?

**Hypothesis:** Negotiation will detect:
- 2x more conflicts
- 3x more policy violations before they reach the user
- Higher confidence in final recommendations

**RQ3:** Does interactive conflict resolution (exposing trade-offs to users) lead to better-aligned decisions compared to system-only decision making?

**Hypothesis:** Interactive resolution will result in:
- Higher user satisfaction (+20%)
- Better perceived clarity (+25%)
- More trust in recommendations (+15%)

**RQ4 (Ablation):** How does the number of specialized agents affect system performance and efficiency?

**Hypothesis:** 3-5 specialized agents will optimize:
- Answer quality (vs. 1 agent)
- Efficiency (vs. 7+ agents)
- Diminishing returns beyond 5 agents

---

## Success Metrics

### Paper Acceptance
- ✅ Clear research contribution
- ✅ Novel mechanisms
- ✅ Strong evaluation
- ✅ Working demo

### System Quality
- ✅ >85% correctness on test set
- ✅ <5% policy violation rate
- ✅ >4.0/5.0 advisor ratings
- ✅ <2s response time

### Research Impact
- ✅ Publishable in ACL 2026
- ✅ Replicable (code released)
- ✅ Generalizable to other domains
- ✅ Clear next steps for research

---

## Risk Mitigation

### Risk 1: Timeline Slippage
**Mitigation:**
- Weekly check-ins with advisor
- Focus on core features (negotiation > additional agents)
- Have fallback if Phase 4 gets tight

### Risk 2: Evaluation Too Weak
**Mitigation:**
- Start collecting scenarios early
- Recruit advisors as raters early
- Have automated metrics as backup

### Risk 3: Baselines Too Strong
**Mitigation:**
- Ensure baselines are fair but not strawmen
- Document why multi-agent is needed
- Show qualitative benefits even if quantitative is small

### Risk 4: Demo Not Working
**Mitigation:**
- Test continuously
- Have recorded backup video
- Practice demo multiple times

---

## Resources Needed

### Technical
- ✅ OpenAI API access (have)
- ✅ LangChain/LangGraph (have)
- ⚠️ More compute for evaluation (may need)
- ⚠️ Stellic API access (nice to have)

### Human
- ✅ Advisor feedback (have)
- ⚠️ Need 3-5 human raters for evaluation
- ⚠️ Need students for pilot testing

### Data
- ✅ Current CMU-Q policies (have)
- ⚠️ Need real advising scenarios (collect)
- ⚠️ Need gold-standard answers (get from advisors)

---

## Deliverables Timeline

| Date | Deliverable | Status |
|------|-------------|--------|
| Feb 7 | Negotiation protocol design | 📝 To do |
| Feb 14 | Proposal generation working | 📝 To do |
| Feb 21 | Critique generation working | 📝 To do |
| Feb 28 | Full negotiation demo | 📝 To do |
| Mar 7 | Conflict types defined | 📝 To do |
| Mar 14 | Conflict detection working | 📝 To do |
| Mar 21 | Interactive resolution demo | 📝 To do |
| Apr 4 | Test dataset complete (50 scenarios) | 📝 To do |
| Apr 11 | Baseline systems implemented | 📝 To do |
| Apr 18 | Evaluation complete | 📝 To do |
| Apr 25 | Analysis and ablation done | 📝 To do |
| May 9 | Paper draft complete | 📝 To do |
| May 16 | Demo video complete | 📝 To do |
| May 30 | Revisions complete | 📝 To do |
| Jun 6 | Final submission | 📝 To do |

---

## Next Actions (This Week!)

1. **Schedule advisor meeting** to review gap analysis and get approval on plan

2. **Start designing negotiation protocol**
   - Sketch data structures
   - Draw interaction diagram
   - Write pseudocode

3. **Begin collecting test scenarios**
   - Talk to advisors
   - Collect 5-10 real cases
   - Document gold standards

4. **Update project documentation**
   - Add research questions to README
   - Create NEGOTIATION_DESIGN.md
   - Update roadmap

5. **Set up weekly check-ins**
   - Progress tracking
   - Blocker resolution
   - Timeline adjustments

---

**You have a clear path to ACL 2026! Focus on negotiation mechanisms first, then evaluation. You can do this!** 🚀
