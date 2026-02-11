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
from config import get_coordinator_model, get_coordinator_temperature, get_openai_base_url

# Import LLM-driven coordinator
from coordinator.llm_driven_coordinator import LLMDrivenCoordinator
from coordinator.clarification_handler import ClarificationHandler

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
        try:
            # === FAST PATH: Use fine-tuned classifier ===
            if self.finetuned_classifier:
                import asyncio
                # Run async classifier synchronously
                # Use asyncio.run() which creates a new event loop for the current thread
                # This works correctly even when called from a background thread
                result = asyncio.run(
                    self.finetuned_classifier.classify(query, student_profile)
                )

                return {
                    "intent_type": "finetuned_classified",
                    "required_agents": result["agents"],
                    "confidence": 0.95,  # Fine-tuned model is well-calibrated
                    "reasoning": f"Fine-tuned classifier: {result['raw_output']}",
                    "priority": "high",
                    "intents": result["intents"],
                    "is_multi_agent": result["is_multi"],
                    "mode": "finetuned"
                }

            # === SLOW PATH: Full LLM reasoning ===
            # Normal workflow planning
            plan = self.llm_coordinator.understand_and_plan(
                query,
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
                "mode": "llm_driven"
            }
            
            return result
            
        except Exception as e:
            print(f"⚠️  LLM-driven coordinator error: {e}")
            import traceback
            traceback.print_exc()
            # Return a minimal fallback
            return {
                "intent_type": "general",
                "required_agents": ["programs_requirements"],
                "confidence": 0.5,
                "reasoning": f"Error in LLM coordination: {str(e)}",
                "priority": "medium",
                "mode": "fallback"
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
        
        # Combine agent outputs
        agent_summaries = []
        for agent_name, output in agent_outputs.items():
            agent_summaries.append(f"""
{agent_name.upper()}:
Answer: {output.answer}
Confidence: {output.confidence}
Policies: {', '.join(output.relevant_policies)}
Risks: {len(output.risks)}
""")
        
        conflicts_text = ""
        if conflicts:
            conflicts_text = "\nConflicts Detected:\n"
            for conflict in conflicts:
                conflicts_text += f"- {conflict.conflict_type.value}: {conflict.description}\n"
        
        prompt = f"""You are an academic advisor helping a student. Synthesize information from specialized agents into a clear, well-formatted answer.

User Query: {user_query}

Agent Outputs:
{chr(10).join(agent_summaries)}
{conflicts_text}

CRITICAL: Below is a form of structure you could follow. you can adapt as needed, as long as it help students to understand what you're saying effectively

## 📌 Direct Answer (Quick Summary)
[Give a clear, direct answer to the student's question. This should immediately tell them what they need to know.]

### Key Points
• [Most critical information first]
• [What the student MUST know]
• [Clear, actionable points]

### Detailed Explanation
[Now provide the full context, reasoning, and background]

### What You Should Do / Next Steps
[Clear action items, numbered list]

FORMATTING REQUIREMENTS:
1. better to include a summary/directn answer at the top
2. Use **bold** for critical information (deadlines, requirements, warnings)
3. Use bullet points (•) for easy scanning
4. Avoid useless & redundant words.
5. Use ⚠️ for warnings, ✅ for recommendations
6. Only include policy references if relevant
8. Don't hallucinate policies - only use information from agents
9. Use friendly, conversational tone

Remember: Students want the answer FIRST, details SECOND. Make it easy to scan quickly.
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

