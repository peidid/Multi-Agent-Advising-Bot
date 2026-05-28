"""
Coordinator / Orchestrator

Key Responsibilities:
- Intent classification & routing
- Workflow planning (dynamic)
- Conflict detection
- Negotiation management
- Answer synthesis
"""
from typing import Dict, List, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from blackboard.schema import (
    BlackboardState, Conflict, ConflictType, WorkflowStep, AgentOutput
)
import json
import re
import sys
import os

# Add parent directory to path to import config
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
from config import (
    get_coordinator_model, get_coordinator_temperature, get_openai_base_url,
    get_coordinator_eval_model, get_coordinator_eval_temperature,
    get_triage_model, get_triage_temperature
)

# Import LLM-driven coordinator
from coordinator.llm_driven_coordinator import LLMDrivenCoordinator
from coordinator.clarification_handler import ClarificationHandler

# Context formatter for passing context to agents (lightweight, no processing)
try:
    from memory.context_formatter import build_agent_context, format_conversation_context
    CONTEXT_FORMATTER_AVAILABLE = True
except ImportError:
    CONTEXT_FORMATTER_AVAILABLE = False

# Course validation tools for plan checking
try:
    from course_tools import (
        check_prereqs_satisfied,
        check_courses_conflict,
        validate_semester_plan,
        validate_full_plan
    )
    VALIDATION_TOOLS_AVAILABLE = True
except ImportError:
    VALIDATION_TOOLS_AVAILABLE = False
    print("Warning: course_tools validation not available")

# Fine-tuned classifier (fast routing)
try:
    from coordinator.finetuned_classifier import FineTunedClassifier
    FINETUNED_AVAILABLE = True
except ImportError:
    FINETUNED_AVAILABLE = False

# Config: Set to True to use fast fine-tuned classifier instead of LLM reasoning
USE_FINETUNED_CLASSIFIER = True


class Coordinator:
    """Main orchestrator for multi-agent system."""
    
    def __init__(self):
        """
        Initialize LLM-driven coordinator.
        
        Uses full LLM reasoning for coordination:
        - No predefined intent types
        - Dynamic workflow planning
        - Adaptive coordination based on context
        """
        # Use more powerful model for coordinator (complex reasoning tasks)
        model = get_coordinator_model()
        temperature = get_coordinator_temperature()
        base_url = get_openai_base_url()

        # Configure HTTP client with SSL verification disabled and longer timeout
        import httpx
        http_client = httpx.Client(verify=False, timeout=180.0)  # 3 minutes

        # Build ChatOpenAI with optional proxy support
        llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "http_client": http_client,
            "request_timeout": 180.0
        }
        if base_url:
            llm_kwargs["base_url"] = base_url

        self.llm = ChatOpenAI(**llm_kwargs)
        self.available_agents = [
            "programs_requirements",
            "course_scheduling",
            "policy_compliance",
            "academic_planning"
        ]
        
        # Initialize LLM-driven coordinator
        self.llm_coordinator = LLMDrivenCoordinator(self.llm)
        
        # Initialize clarification handler with longer timeout
        # Clarification checks can take longer due to complex prompts
        clarification_http_client = httpx.Client(verify=False, timeout=180.0)  # 3 minutes
        clarification_llm_kwargs = {
            "model": model,
            "temperature": temperature,
            "http_client": clarification_http_client,
            "request_timeout": 180.0
        }
        if base_url:
            clarification_llm_kwargs["base_url"] = base_url
        clarification_llm = ChatOpenAI(**clarification_llm_kwargs)
        self.clarification_handler = ClarificationHandler(clarification_llm)

        # Initialize TRIAGE LLM — small/fast model for the top-of-pipeline
        # "is this only a greeting?" check. Single binary call per turn.
        # Must be fast — accuracy matters less because false negatives just
        # fall through to the full pipeline (no harm).
        triage_model = get_triage_model()
        triage_temperature = get_triage_temperature()
        triage_http_client = httpx.Client(verify=False, timeout=30.0)
        triage_llm_kwargs = {
            "model": triage_model,
            "temperature": triage_temperature,
            "http_client": triage_http_client,
            "request_timeout": 30.0,
            "max_tokens": 200,  # JSON-only output, cap to keep latency tight
        }
        if base_url:
            triage_llm_kwargs["base_url"] = base_url
        self.triage_llm = ChatOpenAI(**triage_llm_kwargs)
        print(f"✅ Triage LLM: {triage_model} (greeting short-circuit)")

        # Initialize evaluation LLM - uses GPT-5.2 for best quality evaluation
        # This LLM evaluates agent outputs and provides semantic feedback
        eval_model = get_coordinator_eval_model()
        eval_temperature = get_coordinator_eval_temperature()
        eval_http_client = httpx.Client(verify=False, timeout=180.0)
        eval_llm_kwargs = {
            "model": eval_model,
            "temperature": eval_temperature,
            "http_client": eval_http_client,
            "request_timeout": 180.0
        }
        if base_url:
            eval_llm_kwargs["base_url"] = base_url
        self.eval_llm = ChatOpenAI(**eval_llm_kwargs)
        print(f"✅ Coordinator Evaluation LLM: {eval_model}")
        print("   • Holistic output evaluation")
        print("   • Semantic feedback generation")

        # Initialize fine-tuned classifier if available and enabled
        self.finetuned_classifier = None
        if USE_FINETUNED_CLASSIFIER and FINETUNED_AVAILABLE:
            try:
                self.finetuned_classifier = FineTunedClassifier()
                print("✅ Using Fine-Tuned Intent Classifier")
                print(f"   • Model: {self.finetuned_classifier.model_id}")
                print("   • Fast routing (~100ms vs ~5s)")
                print("   • Lower cost per query")
            except Exception as e:
                print(f"⚠️  Fine-tuned classifier not available: {e}")
                print("   Falling back to LLM-driven coordination")
                self.finetuned_classifier = None

        if not self.finetuned_classifier:
            print("✅ Using LLM-Driven Coordinator")
            print("   • Full LLM reasoning for workflow planning")
            print("   • Dynamic agent coordination")
            print("   • Context-aware decision making")
            print("   • Interactive clarification support")

        # Context formatting available
        if CONTEXT_FORMATTER_AVAILABLE:
            print("✅ Context Formatter enabled")
            print("   • Conversation context passed to agents")
            print("   • Student profile included in prompts")
    
    # ------------------------------------------------------------------
    # TOP-LAYER TRIAGE: binary greeting short-circuit
    # ------------------------------------------------------------------
    # Default friendly reply used when the LLM marks a query as a greeting
    # but doesn't produce a usable `reply`. Kept simple and on-topic.
    _DEFAULT_GREETING_REPLY = (
        "Hi! I'm your CMU-Q academic advisor. Ask me about courses, "
        "program requirements, university policies, or semester planning, "
        "and I'll help you out."
    )

    def triage_greeting(self, query: str) -> Dict[str, Any]:
        """
        Fast binary check: is this query ONLY a greeting / social pleasantry,
        with no academic question or task?

        Single small-model LLM call (~150-300ms). Used at the very top of the
        workflow to short-circuit the full pipeline for messages like "hi",
        "thanks", "bye" — avoiding ~20-40 s of agent calls + evaluation rounds.

        Returns:
            {"is_greeting": bool, "reply": str}
            - is_greeting=True  → caller should respond with `reply` and skip
              the resolver, classifier, agents, and synthesis.
            - is_greeting=False → caller should run the full pipeline.

        Failure mode: on any error (LLM timeout, parse failure, etc.) returns
        is_greeting=False so the full pipeline still runs. False negatives are
        free; we never block legitimate academic queries.
        """
        q = (query or "").strip()
        if not q:
            # Empty query — treat as greeting with a gentle prompt.
            return {"is_greeting": True, "reply": self._DEFAULT_GREETING_REPLY}

        # Hard length guard: if the query is long, it's almost certainly not
        # a pure greeting. Skip the LLM call entirely. (Cheap optimization
        # that doesn't change classification semantics — long messages get
        # classified the same way they would have, but instantly.)
        if len(q) > 200:
            return {"is_greeting": False, "reply": ""}

        prompt = f"""You are a fast triage step for an academic advising assistant at CMU-Q.

DECIDE: Is the following user message ONLY a greeting, thank-you, farewell, or
purely social pleasantry — with NO academic question, NO course/program/policy
request, NO planning request, and NO task?

EXAMPLES that ARE greetings (is_greeting=true):
- "hi" / "hello" / "hey" / "yo"
- "thanks!" / "thank you" / "thx"
- "bye" / "goodbye" / "see you"
- "how are you?" / "good morning"
- "ok" / "got it" / "cool"

EXAMPLES that are NOT greetings (is_greeting=false):
- "hi, what is 67-250?"          (greeting + question)
- "thanks, and what about 15-122?" (acknowledgment + follow-up)
- "what can you help me with?"   (meta question — needs a real answer)
- "what's the weather?"          (off-topic but not a greeting — let pipeline handle)
- Anything mentioning a course code, program, professor, policy, or planning request
- Anything ending in a question mark with academic content

When is_greeting=true, write a brief friendly `reply` (1-2 sentences) that
acknowledges the student and invites them to ask an academic question.
When is_greeting=false, leave `reply` empty.

USER MESSAGE: "{q}"

Respond with JSON ONLY:
{{"is_greeting": true, "reply": "..."}}
or
{{"is_greeting": false, "reply": ""}}"""

        try:
            response = self.triage_llm.invoke([SystemMessage(content=prompt)])
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if not json_match:
                # Couldn't parse — fall through to full pipeline.
                return {"is_greeting": False, "reply": ""}
            data = json.loads(json_match.group())
            is_greeting = bool(data.get("is_greeting", False))
            reply = (data.get("reply") or "").strip()
            if is_greeting and not reply:
                reply = self._DEFAULT_GREETING_REPLY
            return {"is_greeting": is_greeting, "reply": reply}
        except Exception as e:
            # Any failure → fall through to full pipeline (never block users).
            print(f"⚠️  triage_greeting failed (falling through): {e}")
            return {"is_greeting": False, "reply": ""}

    def classify_intent(self, query: str, conversation_history: List[Dict] = None,
                       student_profile: Dict = None) -> Dict[str, Any]:
        """
        Classify user intent and determine which agents to route to.

        Uses fine-tuned classifier if available (fast, ~100ms), otherwise
        falls back to full LLM reasoning (slower, ~5s but more detailed).

        Args:
            query: User's query
            conversation_history: Previous conversation messages (optional)
            student_profile: Student information (optional)

        Returns:
            Intent dictionary with agents, confidence, reasoning, etc.
        """
        # Build context string for agents (no processing, just formatting)
        context_text = ""
        if CONTEXT_FORMATTER_AVAILABLE:
            try:
                context_text = build_agent_context(
                    conversation_history or [],
                    student_profile or {}
                )
            except Exception as e:
                print(f"⚠️  Context formatting error: {e}")

        # =====================================================================
        # SHORT-TERM MEMORY: resolve pronouns / references BEFORE routing.
        # The resolver does nothing (no LLM call) on first turn — see
        # LLMDrivenCoordinator.resolve_context.
        # The resolved query is then used for routing so the fast-path
        # classifier sees a self-contained question, not "will it be offered?".
        # =====================================================================
        try:
            resolved_context = self.llm_coordinator.resolve_context(
                query,
                conversation_history or [],
                student_profile or {}
            )
        except Exception as e:
            print(f"⚠️  resolve_context failed, falling back to raw query: {e}")
            resolved_context = {
                "resolved_query": query,
                "focus_entities": {"courses": [], "programs": [],
                                   "semesters": [], "professors": []},
                "topic_continuity": "new_topic",
                "prior_facts_summary": "",
                "unresolved_references": [],
                "needs_clarification": False,
                "confidence": 0.0,
            }

        # Effective query used for routing & downstream LLM planning.
        # If the resolver expanded references, use the expansion; otherwise keep raw.
        resolved_query = resolved_context.get("resolved_query") or query
        routing_query = resolved_query if resolved_query.strip() else query

        try:
            # === FAST PATH: Use fine-tuned classifier ===
            if self.finetuned_classifier:
                import asyncio
                # Run async classifier synchronously
                # Use asyncio.run() which creates a new event loop for the current thread
                # This works correctly even when called from a background thread
                # NOTE: routing_query (resolved) is sent so the classifier sees
                # "Will 67-250 be offered Fall 2026?" instead of "Will it be offered?"
                result = asyncio.run(
                    self.finetuned_classifier.classify(routing_query, student_profile)
                )

                return {
                    "intent_type": "finetuned_classified",
                    "required_agents": result["agents"],
                    "confidence": 0.95,  # Fine-tuned model is well-calibrated
                    "reasoning": f"Fine-tuned classifier: {result['raw_output']}",
                    "priority": "high",
                    "intents": result["intents"],
                    "is_multi_agent": result["is_multi"],
                    "mode": "finetuned",
                    "context_text": context_text,  # Pass context to agents
                    "resolved_context": resolved_context,  # Short-term memory
                }

            # === SLOW PATH: Full LLM reasoning ===
            # Routing uses the resolved query so the LLM planner sees a self-
            # contained question. History is still passed for richer reasoning.
            plan = self.llm_coordinator.understand_and_plan(
                routing_query,
                conversation_history or [],
                student_profile or {}
            )

            # Convert WorkflowPlan to intent dictionary format for compatibility
            result = {
                "intent_type": "llm_planned",
                "required_agents": plan.agents,
                "confidence": plan.full_analysis.get('confidence', 0.9) if hasattr(plan, 'full_analysis') else 0.9,
                "reasoning": plan.reasoning,
                "priority": "high",
                # LLM-driven specific fields
                "goal": plan.goal,
                "execution_order": plan.execution_order,
                "parallel_stages": plan.parallel_stages,
                "decision_points": plan.decision_points,
                "expected_challenges": plan.expected_challenges,
                "success_criteria": plan.success_criteria,
                "understanding": plan.full_analysis.get('understanding', {}) if hasattr(plan, 'full_analysis') else {},
                "agent_analysis": plan.full_analysis.get('agent_analysis', {}) if hasattr(plan, 'full_analysis') else {},
                "agent_tasks": plan.agent_tasks or {},  # Specific task instructions for each agent
                "mode": "llm_driven",
                "context_text": context_text,  # Pass context to agents
                "resolved_context": resolved_context,  # Short-term memory
            }

            return result

        except Exception as e:
            print(f"⚠️  LLM-driven coordinator error: {e}")
            import traceback
            traceback.print_exc()
            # Return a minimal fallback — still includes resolved_context so
            # agents get whatever memory we managed to compute.
            return {
                "intent_type": "general",
                "required_agents": ["programs_requirements"],
                "confidence": 0.5,
                "reasoning": f"Error in LLM coordination: {str(e)}",
                "priority": "medium",
                "mode": "fallback",
                "resolved_context": resolved_context,
            }
    
    def plan_workflow(self, intent: Dict[str, Any]) -> List[str]:
        """
        Plan the workflow: which agents to call in what order.
        """
        required_agents = intent.get("required_agents", [])
        intent_type = intent.get("intent_type", "general")
        
        # Dynamic workflow planning
        if intent_type == "course_info":
            # Course information queries should go directly to course_scheduling agent
            if "course_scheduling" in required_agents:
                return ["course_scheduling"]
            # Fallback if course_scheduling not in required_agents but intent is course_info
            return ["course_scheduling"]
        elif intent_type == "validate_plan" or intent_type == "plan_semester":
            # Full workflow: propose → check schedule → check compliance
            workflow = []
            if "programs_requirements" in required_agents:
                workflow.append("programs_requirements")
            if "course_scheduling" in required_agents:
                workflow.append("course_scheduling")
            if "policy_compliance" in required_agents:
                workflow.append("policy_compliance")
            return workflow
        elif intent_type == "add_minor":
            return [a for a in required_agents if a in ["programs_requirements", "policy_compliance"]]
        else:
            return required_agents
    
    def detect_conflicts(self, state: BlackboardState) -> List[Conflict]:
        """
        Detect conflicts between agent outputs.
        """
        agent_outputs = state.get("agent_outputs", {})
        conflicts = []
        
        # Check Policy agent for violations
        policy_output = agent_outputs.get("policy_compliance")
        if policy_output:
            hard_constraints = [c for c in policy_output.constraints if c.hard]
            high_risks = [r for r in policy_output.risks if r.severity == "high"]
            
            if hard_constraints:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HARD_VIOLATION,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"Plan violates policies: {[c.description for c in hard_constraints]}",
                    options=[]
                ))
            
            if high_risks:
                conflicts.append(Conflict(
                    conflict_type=ConflictType.HIGH_RISK,
                    affected_agents=["programs_requirements", "policy_compliance"],
                    description=f"High-risk plan: {[r.description for r in high_risks]}",
                    options=[]
                ))
        
        # Check for trade-offs
        plan_options = state.get("plan_options", [])
        if len(plan_options) > 1:
            conflicts.append(Conflict(
                conflict_type=ConflictType.TRADE_OFF,
                affected_agents=["programs_requirements"],
                description="Multiple valid plan options available",
                options=[{"plan": p.dict() if hasattr(p, 'dict') else p} for p in plan_options]
            ))
        
        return conflicts
    
    def synthesize_answer(self, state: BlackboardState) -> str:
        """Synthesize final answer from all agent outputs."""
        agent_outputs = state.get("agent_outputs", {})
        user_query = state.get("user_query", "")
        conflicts = state.get("conflicts", [])

        # Combine agent outputs with FULL content
        agent_summaries = []
        for agent_name, output in agent_outputs.items():
            agent_summaries.append(f"""
=== {agent_name.upper()} ===
{output.answer}

[Confidence: {output.confidence}, Policies: {', '.join(output.relevant_policies)}, Risks: {len(output.risks)}]
""")

        conflicts_text = ""
        if conflicts:
            conflicts_text = "\nConflicts Detected:\n"
            for conflict in conflicts:
                conflicts_text += f"- {conflict.conflict_type.value}: {conflict.description}\n"

        prompt = f"""You are an academic advisor helping a student. Synthesize information from specialized agents into a clear, helpful answer.

USER QUERY: {user_query}

AGENT OUTPUTS (Use these as your primary source):
{chr(10).join(agent_summaries)}
{conflicts_text}

YOUR TASK:
Create a response that DIRECTLY addresses what the student asked for. The format should match the query type:

**For planning/schedule queries** (e.g., "give me a 4-year plan", "sample curriculum"):
- Present the ACTUAL semester-by-semester plan with specific course codes
- Use clear semester headers (Fall 2025, Spring 2026, etc.)
- Include unit counts per semester
- Add brief notes about prerequisites or sequencing
- Highlight any flexibility or alternatives

**For course questions** (e.g., "what courses do I need", "prerequisites for X"):
- List specific courses with codes and names
- Show prerequisite chains if relevant
- Include when courses are offered

**For requirement questions** (e.g., "what are the IS requirements"):
- List requirements clearly by category
- Specify how many units/courses needed
- Note any important rules or restrictions

**For policy/procedure questions**:
- Give the direct answer first
- Include relevant deadlines or conditions
- Cite specific policies if applicable

**For validation queries** (e.g., "can I do X", "does this plan work"):
- Give a clear yes/no/maybe answer first
- Explain the reasoning
- Note any conditions or alternatives

FORMATTING RULES:
1. **Match the format to what the student needs** - don't force a rigid template
2. For detailed plans, use markdown tables or clear headings for each semester
3. Use **bold** for critical info, ⚠️ for warnings, ✅ for recommendations
4. Be specific - use actual course codes and numbers from the agent outputs
5. If agents provided multiple plans/options, present the BEST one clearly (mention alternatives briefly)
6. Don't add generic "next steps" unless truly needed
7. Keep it scannable - students should find what they need quickly
8. DON'T hallucinate - only use information from agent outputs

If the student asked for a PLAN, your response should BE a plan, not a summary about planning.
"""

        response = self.llm.invoke([SystemMessage(content=prompt)])
        return response.content
    
    def manage_negotiation(self, state: BlackboardState) -> Dict[str, Any]:
        """
        Manage Proposal + Critique Protocol.
        
        Protocol:
        1. Programs Agent proposes plan
        2. Policy Agent critiques plan
        3. If conflicts, loop (max 3 iterations)
        """
        iteration = state.get("iteration_count", 0)
        max_iterations = 3
        
        agent_outputs = state.get("agent_outputs", {})
        
        # Step 1: Check if Programs agent has proposed
        if "programs_requirements" not in agent_outputs:
            return {
                "next_agent": "programs_requirements",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 2: Check if Policy agent has critiqued
        if "policy_compliance" not in agent_outputs:
            return {
                "next_agent": "policy_compliance",
                "workflow_step": WorkflowStep.AGENT_EXECUTION
            }
        
        # Step 3: Detect conflicts
        conflicts = self.detect_conflicts(state)
        
        if conflicts:
            has_hard_violation = any(c.conflict_type == ConflictType.HARD_VIOLATION for c in conflicts)
            
            if iteration >= max_iterations:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["The proposed plan has conflicts. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT
                }
            
            if has_hard_violation:
                return {
                    "conflicts": conflicts,
                    "open_questions": ["This plan violates university policies. Would you like to modify it?"],
                    "workflow_step": WorkflowStep.USER_INPUT,
                    "iteration_count": iteration + 1
                }
            else:
                # Soft conflicts - try to resolve
                return {
                    "conflicts": conflicts,
                    "workflow_step": WorkflowStep.NEGOTIATION,
                    "next_agent": "programs_requirements",
                    "iteration_count": iteration + 1
                }
        
        # No conflicts - ready to synthesize
        return {
            "workflow_step": WorkflowStep.SYNTHESIS
        }

    def build_context_for_agents(
        self,
        conversation_history: List[Dict] = None,
        student_profile: Dict = None
    ) -> str:
        """
        Build context string to pass to agents.

        Args:
            conversation_history: Recent conversation messages
            student_profile: Student profile data

        Returns:
            Formatted context string for agent prompts
        """
        if CONTEXT_FORMATTER_AVAILABLE:
            return build_agent_context(
                conversation_history or [],
                student_profile or {}
            )
        return ""

    def evaluate_outputs_for_sufficiency(
        self,
        user_query: str,
        agent_outputs: Dict[str, Any],
        current_round: int = 1,
        student_profile: Dict = None
    ) -> Dict[str, Any]:
        """
        Evaluate if agent outputs sufficiently answer the user's query.
        Uses GPT-5.2 for most accurate evaluation and provides semantic feedback.

        This is called by multi_agent.py BEFORE synthesis to decide if
        we need more information from agents (up to 3 rounds max).

        Args:
            user_query: The original user question
            agent_outputs: Dict of agent_name -> AgentOutput
            current_round: Current evaluation round (1-3)
            student_profile: Student profile dict with completed_courses for validation

        Returns:
            {
                "sufficient": bool,  # True if ready to synthesize
                "quality_score": int,  # 0-100 overall quality score
                "agents_to_rerun": [],  # List of agent names to re-run
                "agent_feedback": {  # Per-agent semantic feedback
                    "agent_name": {
                        "score": int,  # 0-100 for this agent
                        "strengths": ["..."],
                        "gaps": ["..."],
                        "guidance": "Specific guidance for re-retrieval"
                    }
                },
                "reasoning": str,  # Overall explanation
                "missing_info": []  # What information is missing
            }
        """
        if not agent_outputs:
            return {
                "sufficient": False,
                "quality_score": 0,
                "agents_to_rerun": self.available_agents[:2],
                "agent_feedback": {},
                "reasoning": "No agent outputs received",
                "missing_info": ["No information gathered yet"]
            }

        # Build detailed summary of all agent outputs
        outputs_summary = []
        for agent_name, output in agent_outputs.items():
            # Handle both AgentOutput objects and dicts
            if hasattr(output, 'answer'):
                answer = output.answer
                confidence = output.confidence
                policies = output.relevant_policies if hasattr(output, 'relevant_policies') else []
                risks = output.risks if hasattr(output, 'risks') else []
            else:
                answer = output.get('answer', str(output))
                confidence = output.get('confidence', 0.5)
                policies = output.get('relevant_policies', [])
                risks = output.get('risks', [])

            # Include full answer for better evaluation
            outputs_summary.append(f"""
=== Agent: {agent_name} ===
Full Answer:
{answer}

Self-reported confidence: {confidence}
Policies cited: {', '.join(policies) if policies else 'None'}
Risks identified: {len(risks) if isinstance(risks, list) else 0}
""")

        # =====================================================================
        # PLAN VALIDATION (if planning agent is involved)
        # =====================================================================
        plan_validation_section = ""
        if VALIDATION_TOOLS_AVAILABLE and "academic_planning" in agent_outputs:
            planning_output = agent_outputs["academic_planning"]
            planning_answer = planning_output.answer if hasattr(planning_output, 'answer') else str(planning_output)

            # Extract courses from the planning output
            all_courses = re.findall(r'\d{2}-\d{3}', planning_answer)

            if all_courses:
                # Try to parse semester structure from the output
                plan_issues = []

                # Extract semesters with their courses
                # Look for patterns like "Fall 2025:" or "Semester 1 (Fall 2025):"
                semester_pattern = r'(?:Semester \d+\s*\()?([A-Za-z]+\s+\d{4})\)?:?\s*([^S\n]*(?:\n(?!\s*Semester|\s*[A-Z][a-z]+\s+\d{4})[^\n]*)*)'
                semester_matches = re.findall(semester_pattern, planning_answer, re.IGNORECASE)

                parsed_plan = []
                for semester_name, courses_text in semester_matches:
                    semester_courses = re.findall(r'\d{2}-\d{3}', courses_text)
                    if semester_courses:
                        parsed_plan.append({
                            "semester": semester_name.strip(),
                            "courses": semester_courses
                        })

                # Get completed courses from student profile (moved outside if block to fix UnboundLocalError)
                completed_courses = []
                if student_profile:
                    completed_courses = student_profile.get("completed_courses", [])

                # Validate the parsed plan
                if parsed_plan:
                    validation_result = validate_full_plan(parsed_plan, completed_courses)

                    if not validation_result["valid"]:
                        for sem_result in validation_result["semester_results"]:
                            # Report prereq violations
                            for violation in sem_result.get("prereq_violations", []):
                                plan_issues.append(
                                    f"⚠️ PREREQ VIOLATION in {sem_result['semester']}: "
                                    f"{violation['course']} requires {', '.join(violation['missing'])}"
                                )

                            # Report schedule conflicts
                            for conflict in sem_result.get("schedule_conflicts", []):
                                plan_issues.append(
                                    f"⚠️ SCHEDULE CONFLICT in {sem_result['semester']}: "
                                    f"{', '.join(conflict['courses'])} have overlapping times"
                                )

                if plan_issues:
                    plan_validation_section = f"""

=== AUTOMATED PLAN VALIDATION ===
The following issues were detected in the proposed academic plan:

{chr(10).join(plan_issues)}

IMPORTANT: These are REAL violations detected by the system. The plan MUST be revised to fix these issues before being considered valid.
"""
                else:
                    # Check individual courses for prereqs as a sanity check
                    # Use completed courses from student profile
                    prereq_warnings = []
                    for course in all_courses[:10]:  # Check first 10 courses
                        prereq_check = check_prereqs_satisfied(course, completed_courses)
                        if prereq_check.get("has_prereqs") and not prereq_check.get("satisfied"):
                            prereq_warnings.append(
                                f"  - {course} requires: {', '.join(prereq_check.get('required_courses', []))}"
                            )

                    if prereq_warnings:
                        plan_validation_section = f"""

=== AUTOMATED PLAN VALIDATION ===
Note: The following courses have prerequisites that should be verified:
{chr(10).join(prereq_warnings[:5])}

The plan should ensure prerequisites are completed in earlier semesters.
"""

        prompt = f"""You are a senior academic advisor coordinator using GPT-5.2. Your task is to evaluate agent responses and provide actionable feedback.

USER QUERY: {user_query}

AGENT OUTPUTS (Round {current_round}/3):
{''.join(outputs_summary)}
{plan_validation_section}
EVALUATION TASK:
1. Evaluate the OVERALL quality of these combined outputs for answering the student's question
2. Provide a QUALITY SCORE (0-100) based on completeness, accuracy, and relevance
3. For EACH agent, provide specific feedback including strengths, gaps, and guidance
4. Decide if we need more information (only if score < 75 AND clear gaps exist)

SCORING GUIDELINES:
- 90-100: Excellent - comprehensive, specific, well-cited answers
- 75-89: Good - addresses the question well, minor gaps acceptable
- 60-74: Fair - some useful info but notable gaps or vagueness
- Below 60: Insufficient - major gaps, vague, or doesn't address the question

IMPORTANT:
- Be judicious - students need timely responses
- Only request re-runs if there are CLEAR, ACTIONABLE gaps
- If score >= 75, mark as sufficient even if not perfect
- Maximum 3 rounds total (currently round {current_round})
- Provide SPECIFIC guidance for agents to re-run (what to search for, what details needed)
- If AUTOMATED PLAN VALIDATION shows violations, the plan is NOT sufficient - request academic_planning to fix issues
- Prerequisite violations and schedule conflicts are CRITICAL issues that must be resolved

Respond in JSON format:
{{
    "sufficient": true/false,
    "quality_score": 85,
    "reasoning": "Overall evaluation explanation",
    "agents_to_rerun": ["agent_name1"],
    "agent_feedback": {{
        "programs_requirements": {{
            "score": 90,
            "strengths": ["Correctly identified major requirements", "Cited specific policies"],
            "gaps": [],
            "guidance": ""
        }},
        "course_scheduling": {{
            "score": 65,
            "strengths": ["Listed available courses"],
            "gaps": ["Missing prerequisite information", "No schedule details"],
            "guidance": "Search for prerequisites and course schedules for Fall 2024"
        }}
    }},
    "missing_info": ["Prerequisite chain for 15-213", "Course availability for Spring"]
}}

Available agents: {self.available_agents}
Respond ONLY with valid JSON."""

        try:
            # Use the evaluation LLM (GPT-5.2) for best quality
            response = self.eval_llm.invoke([SystemMessage(content=prompt)])

            # Parse JSON response
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # Validate agents_to_rerun
                valid_agents = [a for a in result.get("agents_to_rerun", [])
                               if a in self.available_agents]
                result["agents_to_rerun"] = valid_agents

                # Ensure quality_score exists
                if "quality_score" not in result:
                    result["quality_score"] = 75 if result.get("sufficient") else 50

                # Ensure agent_feedback exists
                if "agent_feedback" not in result:
                    result["agent_feedback"] = {}

                return result
            else:
                # If can't parse, assume sufficient to avoid infinite loops
                return {
                    "sufficient": True,
                    "quality_score": 70,
                    "agents_to_rerun": [],
                    "agent_feedback": {},
                    "reasoning": "Could not parse evaluation response, proceeding with synthesis",
                    "missing_info": []
                }

        except Exception as e:
            print(f"⚠️  Coordinator evaluation error: {e}")
            # On error, proceed with synthesis to avoid blocking
            return {
                "sufficient": True,
                "quality_score": 70,
                "agents_to_rerun": [],
                "agent_feedback": {},
                "reasoning": f"Evaluation error: {str(e)}, proceeding with synthesis",
                "missing_info": []
            }

