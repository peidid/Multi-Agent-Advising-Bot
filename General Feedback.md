1\. Overall: what’s strong and what to sharpen
==============================================

Strong points
-------------

*   Clear recognition that you currently have: single-agent RAG → moving to dynamic multi-agent.
    
*   Thoughtful decomposition of the advising domain (policies, majors/minors, courses, careers, research, events, people).
    
*   Explicit mention of:
    
    *   Shared state / blackboard
        
    *   Dynamic routing / coordinator
        
    *   Interactive conflict resolution
        
    *   History-based personalization
        

Those are exactly the bits that can become a research contribution if done carefully.

What needs sharpening for “research-level”
------------------------------------------

*   The number and granularity of agents (5–12) feels too big and a bit ad hoc. To be justified with experiments: Ablation study. What happens if we go with a smaller number of agents, or a larger number?
    
*   “Negotiation” and “emergent collaboration” are still conceptual; you need concrete mechanisms.
    
*   The research questions and evaluation are implicit rather than explicit.
    
*   Some agents overlap heavily and could/should be merged (maybe).
    

2\. Agent design: reduce, merge, and give each agent a _real_ superpower
========================================================================

Right now you have:

*   Main Advisor / Coordinator
    
*   Long-term Memory / Personalization
    
*   Academic Departments
    
*   Course Agents
    
*   Minor Agents
    
*   University-level Policies
    
*   Event Agent
    
*   Career Agent
    
*   Research Agent
    
*   People / Faculty Agent
    

That’s great coverage, but I would suggest **grouping** into ~5–7 _core_ agents, where each one has:

*   its own **tools / APIs**, and
    
*   a clearly **non-overlapping mandate**.
    

### **Suggested grouping**

**1\. Orchestrator / Main Advisor**

*   As you wrote: intent classification, workflow planning, conflict detection, user interaction.
    
*   I’d remove the anthropomorphic “Ensure the workload is mentally and physically healthy & sustainable” and rephrase as:
    
    *   “Manage conversation complexity, token budget, and when to stop or escalate to humans.”
        

**2\. Student Profile & Memory Agent**

*   Merge “Long-term Memory/personalization” into a single “Student Model” agent:
    
    *   APIs to Stellic / SIO.
        
    *   Summaries of academic history, goals, risk flags (e.g., probation, overloads).
        
    *   Returns a _structured_ profile (JSON-like) to the blackboard rather than free text.
        

**3\. Programs & Requirements Agent**

*   Merge:
    
    *   Academic departments agents,
        
    *   Minor agents,
        
    *   Part of university policies relevant to degree structure.
        
*   Responsibilities:
    
    *   Check progress toward degrees/minors.
        
    *   Validate whether a proposed plan satisfies requirements.
        
    *   Answer course/major/minor requirement questions.
        
*   Tools:
    
    *   RAG over catalog + program sheets.
        
    *   Structural rules / “degree checker” logic if you have it.
        

**4\. Course & Scheduling Agent**

*   Merge Course Agents + Event Agent (for _curriculum-related_ events, like when a course is offered, add/drop deadlines).
    
*   Responsibilities:
    
    *   Given a list of candidate courses, find **offerings** (semester, instructor, time conflicts).
        
    *   Surface schedule-related constraints and clashes.
        
*   Tools:
    
    *   APIs to course schedule DB.
        
    *   RAG over course descriptions.
        

**5\. Policy & Compliance / Finance Agent**

*   Merge:
    
    *   University-level policies, registration policies, and finance (maybe as sub-modes of the same agent).
        
*   Responsibilities:
    
    *   Check that any recommendation is compliant with:
        
        *   overload limits,
            
        *   repeating courses,
            
        *   probation rules,
            
        *   tuition/fees implications (if data is available).
            
*   Tools:
    
    *   RAG over official policies.
        
    *   Finances DB APIs, if accessible.
        

**6\. Opportunities Agent**

*   Merge:
    
    *   Career advice,
        
    *   Research,
        
    *   Events (global trips, exchanges, internships).
        
*   Responsibilities:
    
    *   Given a student profile + interests, retrieve:
        
        *   internships/jobs,
            
        *   research projects,
            
        *   study abroad/exchange opportunities.
            
*   Tools:
    
    *   RAG over internal opportunity listings.
        
    *   Handshake / LinkedIn / websites (where allowed).
        

**7\. People / Routing Agent (optional)**

*   Could be folded into Opportunities or Programs Agent.
    
*   Main job: map “what I want” → “who to talk to” (advisor, prof, office).
    

This consolidation makes the system:

*   more manageable,
    
*   easier to debug,
    
*   more interpretable for research ablations.
    

3\. Coordinator, blackboard, and “negotiation”: make them very concrete
=======================================================================

You propose:

*   Hub-and-spoke topology with a Coordinator.
    
*   Blackboard / shared state.
    
*   Orchestrated negotiation.
    

This is exactly the right framing. To make it research-real:

### **3.1 Shared State (Blackboard) as** _**structured**_ **data**

Instead of “shared state” in prose, think of a typed schema, e.g.:

*   student\_profile
    
    *   major(s), minor(s), GPA, completed courses, flags.
        
*   user\_goal
    
    *   e.g. "add CS minor" or "graduate in 4 years with study abroad".
        
*   constraints\[\]
    
    *   from policy (“max 60 units”), student (“I work 20h/week”), finance.
        
*   plan\_options\[\]
    
    *   candidate semester-by-semester plans.
        
*   risks\[\]
    
    *   “overload risk”, “time conflict”, “GPA below threshold”.
        
*   policy\_citations\[\]
    
    *   each risk or decision has links to policy sections.
        
*   open\_questions\[\]
    
    *   clarifications the system needs from the student.
        

Each agent reads/writes _specific fields_ instead of adding free-form prose. That’s gold for:

*   interpretability,
    
*   automatic evaluation,
    
*   debugging.
    

### **3.2 Negotiation: from buzzword to mechanism**

You talk about “iterative negotiation” and “emergent collaboration”. To be taken seriously in a research paper, I’d define one or two specific mechanisms, e.g.:

*   **Proposal + critique protocol**:
    
    *   Step 1: Programs Agent proposes a plan with a justification.
        
    *   Step 2: Policy & Compliance Agent critiques it: flags violations, proposes edits.
        
    *   Step 3: Coordinator synthesizes a revised plan and either:
        
        *   returns to the user, or
            
        *   loops once more if conflicts remain.
            
*   **Confidence + citation aggregation**:
    
    *   Each agent returns:
        
        *   answer, confidence, relevant\_policies.
            
    *   Coordinator resolves conflicts by:
        
        *   preferring higher-confidence answers with stronger policy support,
            
        *   or asking the user to decide between trade-offs.
            

That’s what “negotiation” then means in your system: a defined interaction protocol, not just “they talk”.

4\. History / memory & privacy
==============================

Your “History/memory integration” idea is excellent and very natural for advising.

Two comments:

1.  **Scope:** Decide early what lives in long-term memory:
    
    *   stable data: academic record, declared interests, constraints (work hours, family obligations),
        
    *   episodic: previous advising conversations, key decisions.
        
2.  **Privacy & policy:** Long-term student data is sensitive. You’ll want:
    
    *   explicit **access policies** (some agents should see only aggregates),
        
    *   a clear **audit trail** (who read what, when),
        
    *   possibly a research angle around _“privacy-aware” multi-agent advising_.
        

5\. Interactive conflict resolution & UI
========================================

This part is _very_ promising:

“Instead of generating the whole answer in one go… it leaves some decisions to students (user agency), and dynamically asks follow-up questions.”

This is exactly how you can:

*   differentiate from “just a smarter chatbot,” and
    
*   design controlled experiments.
    

Suggestions:

*   Define 2–3 **canonical conflict types**:
    
    *   Plan is possible but high-risk.
        
    *   Plan breaks a hard policy (impossible).
        
    *   Plan is possible but has trade-offs (e.g., harder courses vs lighter load).
        
*   For each conflict type, define:
    
    *   how it is represented on the blackboard,
        
    *   what UI widget is used (e.g. “Plan A vs Plan B” with pros/cons),
        
    *   what follow-up questions you ask the student.
        

This gives you a clean evaluation axis: _with_ vs _without_ interactive conflict widgets.

6\. AI-Replica & personalities: powerful but delicate
=====================================================

“Maybe the advisor has his/her own academic/life experience that could be integrated…”

I’d be quite cautious here, especially for real people.

Possibly safer / more robust variants:

*   **Advising styles**, not clones:
    
    *   “structured/planner style”, “exploratory/what-if style”, “risk-averse vs ambitious” advisor modes.
        
*   **Aggregated alumni patterns**, not individual stories:
    
    *   “Students like you (IS, GPA ~3.5, interest in data science) historically followed these paths…”
        
*   If you ever use real advisors’ or alumni’s stories, they should be:
    
    *   anonymized,
        
    *   consented,
        
    *   framed as _examples_, not prescriptive.
        

This can still be a research angle: _how personas / advisory styles influence student trust and decisions_.

7\. Turning this into a research project (not just a cool system)
=================================================================

Right now you have an excellent system design brainstorm. To make it publishable, you need explicit **research questions** and **evaluation plan**. For example:

**Possible main RQ:**

RQ1: Does dynamic, coordinator-based multi-agent advising improve the _quality and safety_ of advising recommendations compared to a single-agent RAG advisor?

**Secondary RQs:**

*   RQ2: Does history-aware personalization improve perceived usefulness and trust?
    
*   RQ3: Does interactive conflict resolution (user-facing trade-offs) lead to better-aligned decisions?
    

**Evaluation ideas:**

*   Scenario-based evaluation with:
    
    *   gold-standard plans from human advisors,
        
    *   human raters (advisors) judging the quality, accuracy, and safety of system recommendations.
        
*   Compare conditions:
    
    *   Single RAG advisor.
        
    *   Static multi-agent (no negotiation, simple routing).
        
    *   Full system (dynamic routing + negotiation + memory + conflict UI).
        
*   Metrics:
    
    *   correctness vs policies,
        
    *   rate of unsafe / clearly bad advice,
        
    *   user satisfaction and perceived clarity,
        
    *   token cost and latency.
        

8\. Minor wording / framing suggestions
=======================================

A few small tweaks to your text that make it sound more precise:

*   Instead of “maybe 5–12 agents,” say: “We propose a small set (5–7) of specialized agents, each with distinct tools and domain-specific RAG indexes.”
    
*   For the Main Advisor: “Ensures the interaction remains within acceptable cognitive and operational load (e.g., limits complexity, escalates to a human advisor when needed)” instead of “mentally and physically healthy.”
    
*   For the Memory Agent: “Summarizes the student’s academic history and prior advising conversations into a concise, structured profile that downstream agents can use for personalized recommendations.”