# Negotiation Protocol Analysis
## Current State vs. True Negotiation Protocol

---

## 🔍 Current Implementation Status

### ✅ **What EXISTS:**

#### 1. **Basic Negotiation Infrastructure**

**File**: `coordinator/coordinator.py` → `manage_negotiation()`

```python
def manage_negotiation(self, state: BlackboardState) -> Dict[str, Any]:
    """
    Manage Proposal + Critique Protocol.
    
    Protocol:
    1. Programs Agent proposes plan
    2. Policy Agent critiques plan
    3. If conflicts, loop (max 3 iterations)
    """
```

**What it does:**
- Checks if Programs Agent has proposed a plan
- Checks if Policy Agent has critiqued
- Detects conflicts
- If conflicts found → loops back (max 3 iterations)
- If hard violations → asks user for input

**Limitations:**
- ❌ No structured negotiation rounds
- ❌ No visible negotiation history
- ❌ No explicit proposal-critique-revision cycle
- ❌ Agents don't directly respond to critiques
- ❌ More like "conflict detection + revision loop" than true negotiation

#### 2. **Critique Mechanism**

**File**: `agents/policy_agent.py` → `_critique_plan()`

```python
def _critique_plan(self, plan_option, student_profile: dict) -> AgentOutput:
    """Critique a proposed plan for policy compliance."""
```

**What it does:**
- Takes a plan from Programs Agent
- Checks against policies
- Returns structured critique with:
  - Violations (hard/soft)
  - Risks
  - Constraints
  - Policy citations

**Status**: ✅ Works, but only critiques - doesn't participate in back-and-forth

#### 3. **Critique Handling**

**File**: `agents/planning_agent.py` → `handle_critique()`

```python
def handle_critique(self, state: BlackboardState, critique: str) -> str:
    """Handle critiques from other agents."""
```

**What it does:**
- Takes a critique string
- Revises plan based on feedback
- Returns revised plan

**Status**: ⚠️ **EXISTS but NOT CALLED in workflow!**

#### 4. **Conflict Detection**

**File**: `coordinator/coordinator.py` → `detect_conflicts()`

```python
def detect_conflicts(self, state: BlackboardState) -> List[Conflict]:
    """Detect conflicts between agent outputs."""
```

**What it does:**
- Checks Policy Agent outputs for violations
- Identifies hard violations vs. high risks
- Detects trade-offs (multiple valid options)
- Returns structured `Conflict` objects

**Status**: ✅ Works well

#### 5. **Visualization**

**File**: `chat.py` → `show_negotiation()`

**What it does:**
- Shows that Programs Agent proposed
- Shows Policy Agent critique
- Displays conflicts
- Shows iteration count

**Status**: ✅ Basic visualization exists

---

## ❌ **What's MISSING: True Negotiation Protocol**

Based on your gap analysis (`ACL2026_GAP_ANALYSIS.md`), here's what's needed:

### **The Gap:**

**Current**: Simple conflict detection → revision loop → ask user

**Needed**: Structured, visible, multi-round negotiation protocol

---

## 🎯 **What a TRUE Negotiation Protocol Would Look Like**

### **Structured Negotiation Rounds**

```python
# coordinator/negotiation_protocol.py (NOT YET IMPLEMENTED)

class NegotiationRound(BaseModel):
    """One round of negotiation"""
    round_number: int
    proposal: Proposal  # From proposing agent
    critiques: List[Critique]  # From critiquing agents
    revision: Optional[Proposal]  # Revised proposal
    resolution: Optional[Resolution]  # Final resolution
    
class Proposal(BaseModel):
    """A plan proposed by an agent"""
    agent_name: str
    plan_type: Literal["semester_plan", "degree_plan", "course_selection"]
    content: Dict[str, Any]  # Structured plan data
    justification: str
    confidence: float
    assumptions: List[str]
    policy_citations: List[str]
    
class Critique(BaseModel):
    """Critique of a proposal"""
    critic_agent: str
    target_proposal_id: str
    approval_status: Literal["approved", "rejected", "conditional"]
    violations: List[PolicyViolation]
    risks: List[Risk]
    suggested_modifications: List[str]
    confidence: float
    
class NegotiationProtocol:
    """Structured negotiation between agents"""
    
    def run_negotiation(self, state: BlackboardState, max_rounds: int = 3):
        """
        Run proposal + critique negotiation cycle
        
        Round Structure:
        1. Agent proposes plan → Blackboard
        2. Critics review → Generate critiques → Blackboard
        3. Coordinator mediates → Determines if revision needed
        4. If revision needed → Agent revises → Back to step 2
        5. If approved → Finalize plan
        """
        negotiation_history = []
        
        for round_num in range(max_rounds):
            print(f"\n🔄 Negotiation Round {round_num + 1}")
            
            # Step 1: Get proposal
            proposal = self.get_proposal(state)
            negotiation_history.append({
                "round": round_num + 1,
                "type": "proposal",
                "agent": proposal.agent_name,
                "content": proposal.content,
                "timestamp": datetime.now()
            })
            
            # Step 2: Get critiques
            critiques = []
            for critic_name in self.get_critic_agents(proposal):
                critique = self.agents[critic_name].critique_proposal(proposal, state)
                critiques.append(critique)
                negotiation_history.append({
                    "round": round_num + 1,
                    "type": "critique",
                    "agent": critic_name,
                    "approval": critique.approval_status,
                    "violations": critique.violations,
                    "timestamp": datetime.now()
                })
            
            # Step 3: Mediate
            resolution = self.mediate(proposal, critiques, state)
            
            # Step 4: Check if done
            if resolution.is_final:
                negotiation_history.append({
                    "round": round_num + 1,
                    "type": "resolution",
                    "outcome": resolution.outcome,
                    "timestamp": datetime.now()
                })
                state["negotiation_history"] = negotiation_history
                return resolution
            
            # Step 5: Revise and continue
            if resolution.needs_revision:
                revised_proposal = self.revise_proposal(proposal, critiques)
                state["agent_outputs"]["programs_requirements"].plan_options[0] = revised_proposal
                # Continue to next round
        
        # Max rounds reached
        return self.fallback_resolution(state)
```

---

## 📊 **Current Flow vs. True Negotiation Flow**

### **Current Flow (Simplified)**

```
1. Programs Agent executes → Proposes plan
   ↓
2. Policy Agent executes → Critiques plan
   ↓
3. Coordinator detects conflicts
   ↓
4. If conflicts:
   → Loop back (max 3 times)
   → OR ask user for input
   ↓
5. Synthesize answer
```

**Problems:**
- ❌ No visible negotiation rounds
- ❌ No structured proposal-critique-revision cycle
- ❌ Agents don't see each other's critiques directly
- ❌ No negotiation history tracking
- ❌ `handle_critique()` exists but isn't called

### **True Negotiation Flow (What's Needed)**

```
Round 1:
1. Programs Agent → PROPOSES plan → Blackboard
   [Visible: "📝 Programs Agent proposes: 4-year plan with CS minor"]
   
2. Policy Agent → CRITIQUES proposal → Blackboard
   [Visible: "🔍 Policy Agent critiques: Semester 3 has 60 units (violates 54-unit limit)"]
   
3. Coordinator → MEDIATES → Determines revision needed
   [Visible: "🔄 Coordinator: Revision needed - unit overload detected"]
   
4. Programs Agent → REVISES plan based on critique → Blackboard
   [Visible: "✏️ Programs Agent revises: Redistributed courses to Semester 4"]
   
Round 2:
5. Policy Agent → RE-CRITIQUES revised plan → Blackboard
   [Visible: "🔍 Policy Agent: Approved! Plan now compliant"]
   
6. Coordinator → FINALIZES → Plan approved
   [Visible: "✅ Negotiation complete: Plan approved after 2 rounds"]
```

**Key Differences:**
- ✅ Visible rounds with clear structure
- ✅ Each step logged to negotiation history
- ✅ Agents explicitly respond to critiques
- ✅ Multiple back-and-forth rounds
- ✅ Negotiation state visible to user

---

## 🔧 **How to Make Negotiation Visible**

### **1. Add Negotiation History to Blackboard**

**File**: `blackboard/schema.py`

```python
class NegotiationRound(BaseModel):
    """One round of negotiation"""
    round_number: int
    proposal: Optional[Proposal] = None
    critiques: List[Critique] = Field(default_factory=list)
    revision: Optional[Proposal] = None
    resolution: Optional[str] = None
    timestamp: datetime

class BlackboardState(TypedDict):
    # ... existing fields ...
    
    # NEW: Negotiation tracking
    negotiation_history: List[NegotiationRound]
    current_negotiation_round: Optional[NegotiationRound]
    negotiation_status: Literal["none", "active", "resolved", "failed"]
```

### **2. Implement True Negotiation Protocol**

**File**: `coordinator/negotiation_protocol.py` (CREATE THIS)

```python
class NegotiationProtocol:
    """Structured negotiation protocol"""
    
    def run_negotiation(self, state: BlackboardState) -> Dict[str, Any]:
        """
        Execute Proposal + Critique + Revision protocol
        
        Returns:
            Updated state with negotiation results
        """
        max_rounds = 3
        negotiation_history = state.get("negotiation_history", [])
        
        for round_num in range(max_rounds):
            round_data = NegotiationRound(round_number=round_num + 1)
            
            # STEP 1: Get proposal
            proposal = self._get_current_proposal(state)
            if not proposal:
                break
            
            round_data.proposal = proposal
            self._log_negotiation_event(state, "proposal", proposal)
            
            # STEP 2: Get critiques
            critiques = self._get_critiques(proposal, state)
            round_data.critiques = critiques
            for critique in critiques:
                self._log_negotiation_event(state, "critique", critique)
            
            # STEP 3: Check if approved
            if all(c.approval_status == "approved" for c in critiques):
                round_data.resolution = "approved"
                negotiation_history.append(round_data)
                state["negotiation_history"] = negotiation_history
                state["negotiation_status"] = "resolved"
                return state
            
            # STEP 4: Mediate and determine revision
            mediation_result = self._mediate(proposal, critiques, state)
            
            if mediation_result.needs_revision:
                # STEP 5: Revise proposal
                revised_proposal = self._revise_proposal(
                    proposal, critiques, state
                )
                round_data.revision = revised_proposal
                self._log_negotiation_event(state, "revision", revised_proposal)
                
                # Update state with revised proposal
                state = self._update_proposal(state, revised_proposal)
            else:
                # User input needed or fallback
                round_data.resolution = mediation_result.outcome
                negotiation_history.append(round_data)
                state["negotiation_history"] = negotiation_history
                return state
            
            negotiation_history.append(round_data)
        
        # Max rounds reached
        state["negotiation_history"] = negotiation_history
        state["negotiation_status"] = "failed"
        return state
```

### **3. Call Revision Handler**

**File**: `multi_agent.py` or `coordinator/coordinator.py`

**Current**: `handle_critique()` exists but is never called

**Fix**: Call it during negotiation:

```python
# In manage_negotiation() or negotiation protocol
if conflicts and iteration < max_iterations:
    # Get critique from Policy Agent
    critique = policy_output.answer  # or structured critique
    
    # Call Planning Agent's revision handler
    revised_plan = planning_agent.handle_critique(state, critique)
    
    # Update state with revised plan
    state["agent_outputs"]["academic_planning"].plan_options[0] = revised_plan
```

### **4. Visualize Negotiation Rounds**

**File**: `chat.py` or `streamlit_app_agent_view.py`

```python
def show_negotiation_rounds(state):
    """Display full negotiation history"""
    history = state.get("negotiation_history", [])
    
    if not history:
        print("   No negotiation occurred.")
        return
    
    print("\n   📋 Negotiation History:")
    for round_data in history:
        print(f"\n   🔄 Round {round_data.round_number}:")
        
        if round_data.proposal:
            print(f"      📝 {round_data.proposal.agent_name} PROPOSES:")
            print(f"         {round_data.proposal.justification[:100]}...")
        
        for critique in round_data.critiques:
            status_icon = "✅" if critique.approval_status == "approved" else "❌"
            print(f"      {status_icon} {critique.critic_agent} CRITIQUES:")
            print(f"         Status: {critique.approval_status}")
            if critique.violations:
                print(f"         Violations: {len(critique.violations)}")
            if critique.suggested_modifications:
                print(f"         Suggestions: {critique.suggested_modifications[0]}")
        
        if round_data.revision:
            print(f"      ✏️ REVISED based on critiques")
        
        if round_data.resolution:
            print(f"      ✅ Resolution: {round_data.resolution}")
```

---

## 📝 **Summary: Current vs. Ideal**

| Aspect | Current Implementation | True Negotiation Protocol |
|--------|----------------------|-------------------------|
| **Structure** | Simple loop | Structured rounds |
| **Visibility** | Basic conflict display | Full negotiation history |
| **Protocol** | Implicit | Explicit Proposal-Critique-Revision |
| **Agent Response** | ❌ `handle_critique()` not called | ✅ Agents respond to critiques |
| **History** | ❌ No tracking | ✅ Complete negotiation log |
| **Rounds** | Max 3 iterations | Visible rounds with status |
| **Mediation** | Basic conflict check | Structured mediation logic |

---

## 🎯 **Recommendation**

### **For ACL 2026 Demo:**

You need to implement a **TRUE visible negotiation protocol** to have a strong research contribution.

**Priority Actions:**

1. ✅ **Create `coordinator/negotiation_protocol.py`**
   - Implement structured negotiation rounds
   - Track negotiation history
   - Make rounds visible

2. ✅ **Update `blackboard/schema.py`**
   - Add `NegotiationRound` model
   - Add `negotiation_history` to state

3. ✅ **Fix `handle_critique()` integration**
   - Actually call it during negotiation
   - Make agents respond to critiques

4. ✅ **Enhance visualization**
   - Show negotiation rounds clearly
   - Display proposal → critique → revision flow

5. ✅ **Test with real scenarios**
   - "Can I graduate in 3.5 years?" (triggers overload conflict)
   - "Add CS minor" (triggers prerequisite conflicts)
   - Show visible negotiation resolving conflicts

---

## 🔗 **Related Files**

- **Current Implementation**: `coordinator/coordinator.py` (line 313)
- **Critique Logic**: `agents/policy_agent.py` (line 47)
- **Revision Handler**: `agents/planning_agent.py` (line 314) ⚠️ Not called!
- **Visualization**: `chat.py` (line 323)
- **Gap Analysis**: `ACL2026_GAP_ANALYSIS.md` (line 56)
- **Implementation Plan**: `ACL2026_IMPLEMENTATION_PLAN.md` (line 21)

---

## ✅ **Bottom Line**

**Current State**: 
- Basic conflict detection ✅
- Simple revision loop ✅
- Critique mechanism ✅
- **BUT**: No true structured negotiation protocol ❌

**What's Needed**:
- Visible negotiation rounds
- Structured Proposal-Critique-Revision cycle
- Negotiation history tracking
- Agents explicitly responding to critiques
- Clear visualization of negotiation process

**This is your core research contribution** - without visible negotiation, it's just "fancy routing" rather than a novel multi-agent interaction mechanism! 🎯
