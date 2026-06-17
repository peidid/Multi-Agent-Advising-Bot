# ACL 2026 Gap Analysis: Current System vs. Vision

## Executive Summary

**Current Status:** You have a **solid foundation** - a well-implemented LLM-driven multi-agent system with dynamic coordination, RAG, and conversation memory.

**Gap:** You need to move from "dynamic routing" to **visible negotiation protocols** and **interactive conflict resolution** to have a strong research contribution for ACL 2026.

**Priority:** Focus on mechanisms (negotiation protocols, structured conflicts) over adding more agents.

---

## 1. What You Have (Current Strengths) ✅

### 1.1 Core Architecture ✅
- **LLM-Driven Coordinator** - Implemented and working
  - Dynamic workflow planning (no predefined intents)
  - Context-aware agent selection
  - Full reasoning visible to users
  
- **Multi-Agent System** - 3 specialized agents
  - Programs Requirements Agent
  - Course Scheduling Agent
  - Policy Compliance Agent
  
- **Blackboard Pattern** - Shared state implementation
  - `blackboard/schema.py` with structured types
  - AgentOutput, Constraint, Risk, PlanOption models
  - Conflict types defined
  
- **RAG Implementation** - Domain-specific knowledge bases
  - Separate vector DBs per agent
  - ~5000 documents indexed
  - ChromaDB + OpenAI embeddings

### 1.2 Recent Additions ✅
- **Conversation Memory** - Just implemented (Jan 2026)
  - Short-term memory across turns
  - Context-aware follow-ups
  - Reference resolution ("it", "that course")
  
- **Development Mode** - Testing infrastructure
  - Manual agent selection
  - Individual agent testing

### 1.3 What Works Well ✅
- Clean architecture (coordinator + agents + blackboard)
- LLM-driven coordination (research contribution identified)
- Explainability (shows reasoning process)
- Domain coverage for CMU-Q advising

---

## 2. Critical Gaps for ACL 2026 ❌

### 2.1 No Visible Negotiation Protocol ❌ **[HIGHEST PRIORITY]**

**Advisor Feedback (Section 3.2):**
> "To be taken seriously in a research paper, I'd define one or two specific mechanisms, e.g.:
> - Proposal + critique protocol
> - Confidence + citation aggregation"

**Current State:**
- Agents execute independently
- Coordinator synthesizes outputs after all agents finish
- No structured back-and-forth between agents
- No visible negotiation process

**What's Missing:**
```
Current Flow:
Query → Coordinator plans → All agents execute in parallel → Synthesize → Answer

Needed Flow:
Query → Coordinator plans → Agent 1 proposes plan
     → Agent 2 critiques (flags issues) → Coordinator mediates
     → Revised plan → Agent 3 validates → Final answer
```

**Research Value:**
This is THE core contribution. Without visible negotiation, it's just "fancy routing."

### 2.2 No Interactive Conflict Resolution ❌ **[HIGH PRIORITY]**

**Advisor Feedback (Section 5):**
> "Define 2–3 canonical conflict types... what UI widget is used... what follow-up questions you ask"

**Current State:**
- Conflicts detected but only logged
- No user interaction for trade-offs
- System makes all decisions unilaterally
- No "Plan A vs Plan B" widgets

**What's Missing:**
```python
# Current: Conflicts detected but not exposed
conflicts = coordinator.detect_conflicts(state)
# ... system decides internally

# Needed: Interactive resolution
if conflict.type == ConflictType.TRADE_OFF:
    show_ui_widget("Plan A vs Plan B")
    user_choice = get_user_input()
    workflow = coordinator.adapt_based_on_choice(user_choice)
```

**Canonical Conflict Types (from advisor):**
1. **Hard Violation** - Plan breaks policy (impossible)
2. **High Risk** - Plan possible but risky (needs user decision)
3. **Trade-offs** - Multiple valid options (user agency)

**Research Value:**
- User agency in AI systems
- Human-in-the-loop decision making
- Controlled experiments (with vs without interaction)

### 2.3 Blackboard Not Fully Structured ❌ **[MEDIUM PRIORITY]**

**Advisor Feedback (Section 3.1):**
> "Instead of 'shared state' in prose, think of a typed schema"
> "Each agent reads/writes specific fields instead of adding free-form prose"

**Current State:**
- Schema exists (`blackboard/schema.py`) with types
- But agents return mostly free-text answers
- Not fully enforced structured data flow

**What's Missing:**
```python
# Current: Agents return prose
agent_output.answer = "The student needs to take 15-213, which requires..."

# Needed: Structured fields
agent_output.structured_data = {
    "required_courses": ["15-213"],
    "prerequisites_met": True,
    "confidence": 0.92,
    "policy_citations": ["CS_Major_Requirements_v2023.pdf#p5"]
}
```

**Research Value:**
- Interpretability
- Automatic evaluation
- Debugging and error analysis

### 2.4 No Long-Term Student Profile ❌ **[MEDIUM PRIORITY]**

**Advisor Feedback (Section 4):**
> "Decide early what lives in long-term memory: stable data (academic record, declared interests)"

**Current State:**
- Only conversation-level memory (within session)
- No persistent student profile
- No API integration with Stellic/SIO
- Student info manually entered each time

**What's Missing:**
```python
# Needed: Student Profile Agent
class StudentProfile:
    major: List[str]
    minor: List[str]
    gpa: float
    completed_courses: List[str]
    current_semester: int
    work_hours: int  # constraints
    flags: List[str]  # "probation", "overload"
    goals: List[str]  # "graduate in 4 years", "study abroad"
```

**Research Value:**
- Personalization
- Context-aware recommendations
- Privacy-aware multi-agent systems

### 2.5 No Ablation Study Design ❌ **[HIGH PRIORITY]**

**Advisor Feedback (Section 2):**
> "To be justified with experiments: Ablation study. What happens if we go with a smaller number of agents, or a larger number?"

**Advisor Feedback (Section 7):**
> "Compare conditions: Single RAG advisor, Static multi-agent, Full system"

**Current State:**
- One full system implementation
- No baseline comparisons
- No evaluation framework
- No test scenarios with gold standards

**What's Missing:**
1. **Baseline Systems:**
   - Single-agent RAG (no multi-agent)
   - Rule-based routing (no LLM coordination)
   - Static workflow (no negotiation)

2. **Test Dataset:**
   - 50-100 advising scenarios
   - Gold-standard answers from human advisors
   - Edge cases and conflicts

3. **Metrics:**
   - Correctness vs. policies
   - Safety (rate of bad advice)
   - User satisfaction
   - Token cost & latency

**Research Value:**
- Proves your approach is better
- Required for publication
- Identifies what actually helps

### 2.6 No Explicit Research Questions ❌ **[HIGH PRIORITY]**

**Advisor Feedback (Section 7):**
> "Right now you have an excellent system design brainstorm. To make it publishable, you need explicit research questions"

**Current State:**
- No formal RQs stated
- Contribution is implicit
- No clear evaluation plan

**What's Missing:**

**RQ1 (Main):** Does LLM-driven coordinator-based multi-agent advising with visible negotiation improve the quality and safety of recommendations compared to single-agent RAG?

**RQ2:** Does structured negotiation protocol (proposal + critique) lead to better conflict detection and resolution?

**RQ3:** Does interactive conflict resolution (exposing trade-offs to users) lead to better-aligned decisions?

**RQ4:** How does the number of specialized agents affect system performance? (ablation)

---

## 3. Agent Design Gap

### Current: 3 Agents
1. Programs Requirements
2. Course Scheduling
3. Policy Compliance

### Advisor's Recommendation: 5-7 Core Agents

**Advisor Feedback (Section 2):**
> "I'd suggest grouping into ~5–7 core agents, where each one has:
> - its own tools / APIs
> - a clearly non-overlapping mandate"

### Recommended Agent Structure:

| Agent | Current Status | Tools Needed | Priority |
|-------|---------------|--------------|----------|
| **1. Orchestrator** | ✅ Implemented | None (LLM-driven) | Done |
| **2. Student Profile & Memory** | ❌ Missing | Stellic API, SIO API | High |
| **3. Programs & Requirements** | ✅ Implemented | Degree checker logic | Done |
| **4. Course & Scheduling** | ✅ Implemented | Schedule DB API | Done |
| **5. Policy & Compliance** | ✅ Implemented | Policy RAG | Done |
| **6. Opportunities** | ❌ Missing | Handshake, LinkedIn | Low |
| **7. People / Routing** | ❌ Missing | Faculty directory | Low |

**Gap Analysis:**
- **Good news:** You have the 3 most critical agents (Programs, Courses, Policy)
- **Missing:** Student Profile integration (important for personalization)
- **Missing:** Opportunities & People agents (less critical for core research)

**Recommendation:**
- **Don't add more agents yet** - focus on negotiation mechanisms first
- Add Student Profile Agent if you can get API access
- Skip Opportunities/People agents unless they're needed for specific scenarios

---

## 4. Technical Implementation Gaps

### 4.1 Negotiation Implementation ❌

**What You Need to Build:**

```python
# coordinator/negotiation_protocol.py

class NegotiationProtocol:
    """Structured negotiation between agents"""
    
    def proposal_critique_cycle(self, state: BlackboardState):
        """
        1. Programs Agent proposes a plan
        2. Policy Agent critiques it
        3. Coordinator mediates and revises
        """
        # Step 1: Proposal
        proposal = self.programs_agent.propose_plan(state)
        state.blackboard.proposals.append(proposal)
        
        # Step 2: Critique
        critique = self.policy_agent.critique_proposal(proposal, state)
        state.blackboard.critiques.append(critique)
        
        # Step 3: Mediation
        if critique.has_violations():
            resolution = self.coordinator.mediate(proposal, critique)
            if resolution.needs_user_input:
                return self.interactive_conflict_resolution(resolution)
        
        return self.finalize_plan(proposal, critique)
    
    def confidence_aggregation(self, agent_outputs):
        """
        Aggregate confidence and citations from multiple agents
        """
        weighted_answer = self.combine_by_confidence(agent_outputs)
        policy_support = self.aggregate_citations(agent_outputs)
        return weighted_answer, policy_support
```

### 4.2 Interactive Conflict UI ❌

**What You Need to Build:**

```python
# ui/conflict_widgets.py

def show_tradeoff_widget(conflict: Conflict) -> UserChoice:
    """
    Display trade-off options to user
    """
    print("\n" + "="*80)
    print("⚖️  DECISION POINT: Multiple Valid Options")
    print("="*80)
    
    for i, option in enumerate(conflict.options, 1):
        print(f"\n📋 Option {i}: {option['title']}")
        print(f"   Pros:")
        for pro in option['pros']:
            print(f"     ✅ {pro}")
        print(f"   Cons:")
        for con in option['cons']:
            print(f"     ❌ {con}")
        print(f"   Confidence: {option['confidence']:.2f}")
    
    choice = input("\nWhich option do you prefer? (1/2/skip): ")
    return UserChoice(choice)

def show_risk_warning(conflict: Conflict) -> bool:
    """
    Warn user about high-risk plan
    """
    print("\n⚠️  WARNING: High-Risk Plan Detected")
    print(f"   {conflict.description}")
    print(f"\n   Risks:")
    for risk in conflict.risks:
        print(f"     🔴 {risk.description}")
    
    confirm = input("\nDo you want to proceed anyway? (yes/no): ")
    return confirm.lower() == 'yes'
```

### 4.3 Structured Blackboard Updates ❌

**Current blackboard/schema.py is good, but needs:**

```python
# Enhance AgentOutput to require structured data
class AgentOutput(BaseModel):
    agent_name: str
    answer: str  # Free text for display
    
    # ADD: Structured data for coordination
    structured_data: Dict[str, Any]  # Agent-specific structured output
    confidence: float
    reasoning_steps: List[str]  # Show reasoning process
    relevant_policies: List[PolicyCitation]  # Not just strings
    conflicts_detected: List[Conflict]  # Each agent can flag conflicts
    
    # For Programs Agent specifically
    proposed_plans: Optional[List[PlanOption]] = None
    
    # For Policy Agent specifically
    policy_violations: Optional[List[PolicyViolation]] = None

class PolicyCitation(BaseModel):
    """Structured policy reference"""
    document: str
    section: str
    page: Optional[int]
    quote: str
    url: Optional[str]

class PolicyViolation(BaseModel):
    """Specific policy violation"""
    policy_id: str
    description: str
    severity: Literal["hard", "soft"]
    affected_plan_elements: List[str]
    suggested_fix: Optional[str]
```

---

## 5. Evaluation Gap ❌

### What You Need for ACL 2026:

**5.1 Test Scenarios (50-100 cases)**

Categories:
1. **Simple queries** (20 cases)
   - "What are prerequisites for 15-213?"
   - "When is 67-364 offered?"
   
2. **Complex multi-agent queries** (20 cases)
   - "I got a D in 15-112, do I need to retake it?"
   - "Can I add a CS minor as an IS major?"
   
3. **Conflict scenarios** (20 cases)
   - Student wants overload (policy violation)
   - Course prerequisites not met
   - Schedule conflicts
   
4. **Trade-off scenarios** (20 cases)
   - Multiple valid graduation plans
   - Study abroad vs. timely graduation
   - Harder courses vs. lighter load
   
5. **Edge cases** (20 cases)
   - Ambiguous queries
   - Missing information
   - Policy exceptions

**5.2 Gold Standard Answers**

For each scenario:
- Correct answer from human advisor
- Policy citations
- Risk flags
- Decision rationale

**5.3 Baseline Systems**

You need to implement:

1. **Baseline 1: Single-Agent RAG**
   - One large knowledge base
   - No specialization
   - No negotiation

2. **Baseline 2: Rule-Based Multi-Agent**
   - Fixed routing rules
   - No LLM coordination
   - No negotiation

3. **Baseline 3: Static Multi-Agent**
   - LLM coordination
   - But no negotiation
   - No interactive conflict resolution

4. **Your System: Full Dynamic System**
   - LLM coordination
   - Structured negotiation
   - Interactive conflict resolution

**5.4 Metrics**

**Automatic Metrics:**
- **Correctness:** % of recommendations matching gold standard
- **Safety:** % of responses with no policy violations
- **Completeness:** % of relevant policies cited
- **Efficiency:** Token cost, latency

**Human Evaluation:**
- **Quality:** 1-5 rating by human advisors
- **Clarity:** How well-explained is the answer?
- **Trust:** Would you trust this advice?
- **Satisfaction:** Would you use this system?

**Compare across conditions:**
- Single-agent vs. multi-agent
- Rule-based vs. LLM-driven
- With vs. without negotiation
- With vs. without interactive conflict resolution

---

## 6. Priority Roadmap for ACL 2026

### Phase 1: Mechanisms (Feb 2026) - **CRITICAL**

**Goal:** Implement negotiation protocols

**Tasks:**
1. ✅ Implement Proposal + Critique protocol
   - Programs Agent proposes plan
   - Policy Agent critiques
   - Coordinator mediates
   
2. ✅ Implement Confidence Aggregation
   - Each agent returns confidence + citations
   - Coordinator resolves conflicts by confidence/citations
   
3. ✅ Make outputs more structured
   - Enforce structured data in AgentOutput
   - Policy violations as structured objects
   - Plans with pros/cons

**Deliverable:** Working negotiation demo

### Phase 2: Interactive Conflicts (Mar 2026) - **HIGH PRIORITY**

**Goal:** User agency in conflict resolution

**Tasks:**
1. ✅ Implement 3 canonical conflict types
   - Hard violation (block and explain)
   - High risk (warn and confirm)
   - Trade-off (show options and let user choose)
   
2. ✅ Build UI widgets
   - Plan comparison widget
   - Risk warning dialog
   - Clarification questions
   
3. ✅ Update coordinator to expose conflicts

**Deliverable:** Interactive conflict resolution demo

### Phase 3: Evaluation Framework (Apr 2026) - **CRITICAL**

**Goal:** Prove your approach works

**Tasks:**
1. ✅ Create test dataset (50 scenarios)
   - Collect from real advising sessions
   - Get gold standards from advisors
   
2. ✅ Implement baseline systems
   - Single-agent RAG
   - Rule-based routing
   - Static multi-agent
   
3. ✅ Run ablation studies
   - Compare all conditions
   - Measure all metrics
   
4. ✅ Human evaluation study
   - Recruit advisors as raters
   - Compare system outputs

**Deliverable:** Full evaluation results

### Phase 4: Student Profile (May 2026) - **OPTIONAL**

**Goal:** Personalization (if time allows)

**Tasks:**
1. ⚠️ Get API access to Stellic/SIO
2. ⚠️ Implement Student Profile Agent
3. ⚠️ Show personalization improves results

**Deliverable:** Personalized advising demo

### Phase 5: Paper Writing (May-Jun 2026) - **CRITICAL**

**Goal:** ACL 2026 submission

**Tasks:**
1. ✅ Write paper with clear RQs
2. ✅ Present evaluation results
3. ✅ Prepare demo video
4. ✅ Submit to ACL 2026 Demo Track

---

## 7. What NOT to Do (Avoid Scope Creep)

### ❌ Don't Add More Agents Yet

Your advisor is clear:
> "The number and granularity of agents (5–12) feels too big and a bit ad hoc"

**Current 3 agents are enough** for core research contribution. Focus on:
- How they negotiate (mechanisms)
- Not how many you have (coverage)

### ❌ Don't Build Career/Research/Events Agents

These are "nice to have" but not critical for research contribution:
- Career Agent
- Research Agent  
- Events Agent
- People/Faculty Agent

**Why skip?**
- No APIs available (Handshake, LinkedIn access is hard)
- Adds complexity without research value
- Your core contribution is negotiation, not coverage

**When to add?**
- After paper acceptance
- As product features
- Not for research evaluation

### ❌ Don't Build AI-Replica/Personalities Yet

Your advisor warns:
> "I'd be quite cautious here, especially for real people"

**Problems:**
- Privacy concerns
- Consent needed
- Hard to evaluate
- Not core contribution

**Better approach (later):**
- Advisory styles (risk-averse vs. ambitious)
- Aggregated patterns (not individuals)

### ❌ Don't Try to Integrate Everything

**Focus on core research:**
- LLM-driven coordination
- Structured negotiation
- Interactive conflict resolution

**Leave for later:**
- Full university system integration
- Production deployment
- Real-time schedule APIs

---

## 8. Research Contribution Summary

### Current Contribution (Good but Not Enough):

"We built a multi-agent academic advising system with LLM-driven coordination"

**Problem:** Lots of people are building multi-agent systems with LLMs.

### Needed Contribution (Research-Level):

"We demonstrate that **structured negotiation protocols** and **interactive conflict resolution** in multi-agent systems lead to higher-quality, safer, and more user-aligned academic advising recommendations compared to single-agent and rule-based approaches."

**Why this is strong:**
1. **Novel mechanism:** Proposal + critique protocol
2. **User agency:** Interactive trade-off resolution
3. **Evaluation:** Shows improvement over baselines
4. **Domain:** Safety-critical (academic advising)

### Paper Title (Suggested):

"Structured Negotiation in Multi-Agent Academic Advising: LLM-Driven Coordination with Interactive Conflict Resolution"

or

"Beyond Routing: Visible Negotiation Protocols for Safe Multi-Agent Academic Advising"

---

## 9. Key Takeaways

### ✅ What You've Done Well:
1. Strong technical foundation (LLM-driven, RAG, blackboard)
2. Clean architecture (easy to extend)
3. Domain expertise (CMU-Q advising)
4. Already thinking about research contribution

### ❌ What's Missing for ACL 2026:
1. **Visible negotiation mechanisms** (proposal + critique)
2. **Interactive conflict resolution** (user agency)
3. **Evaluation framework** (baselines + metrics)
4. **Explicit research questions**
5. **Test dataset** with gold standards

### 🎯 Focus Areas (Priority Order):
1. **Negotiation protocols** (Feb) - CRITICAL
2. **Interactive conflicts** (Mar) - HIGH
3. **Evaluation framework** (Apr) - CRITICAL
4. **Paper writing** (May-Jun) - CRITICAL
5. Student profile (May) - OPTIONAL

### 💡 Strategic Advice:

**From your advisor:**
> "To be taken seriously in a research paper, I'd define one or two specific mechanisms"

**Don't:**
- Add more agents
- Try to cover everything
- Build AI personas yet

**Do:**
- Focus on negotiation mechanisms
- Make conflicts visible and interactive
- Prove it works with evaluation
- Write clear research questions

---

## 10. Next Immediate Steps (This Week)

1. **Define Research Questions** (1 day)
   - Write explicit RQ1, RQ2, RQ3
   - Get advisor feedback

2. **Design Negotiation Protocol** (2 days)
   - Sketch proposal + critique flow
   - Define data structures
   - Write pseudocode

3. **Design Conflict Types** (1 day)
   - 3 canonical types
   - UI widget mockups
   - User interaction flows

4. **Create Test Scenarios** (1 day)
   - 10 starter scenarios
   - Get gold standards from advisors

5. **Update Roadmap** (1 day)
   - Weekly milestones
   - Deliverables
   - Paper deadline

---

## Conclusion

**Gap Assessment:**

| Component | Status | Gap | Priority |
|-----------|--------|-----|----------|
| LLM Coordination | ✅ Done | None | - |
| Multi-Agent Architecture | ✅ Done | None | - |
| RAG Implementation | ✅ Done | None | - |
| Conversation Memory | ✅ Done | None | - |
| **Negotiation Protocol** | ❌ Missing | **LARGE** | **CRITICAL** |
| **Interactive Conflicts** | ❌ Missing | **LARGE** | **HIGH** |
| **Evaluation Framework** | ❌ Missing | **LARGE** | **CRITICAL** |
| Structured Blackboard | ⚠️ Partial | Medium | Medium |
| Student Profile | ❌ Missing | Medium | Optional |
| More Agents | ❌ Missing | Small | Low |

**Overall Assessment:**

You have **60% of the system** built (architecture, core agents, coordination).

You need **40% more** for a strong ACL 2026 paper:
- Negotiation mechanisms (20%)
- Evaluation framework (15%)
- Interactive conflicts (5%)

**Timeline:** **Achievable by June 2026** if you focus on mechanisms over features.

**Recommendation:** Follow the 4-phase roadmap above, prioritizing negotiation → evaluation → paper writing.

---

**You're on the right track! Focus on making the negotiation visible and measurable.** 🚀
