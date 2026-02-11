"""
Step 4: Fine-Tuned Multi-Label Intent Classifier
==================================================
Drop-in replacement for your existing intent_classifier_enhanced.py

This replaces the LLM prompt-based classification with a fine-tuned model
that outputs which agents are needed for each query.

Integration:
    1. Copy this file to AdvisingBot/coordinator/finetuned_classifier.py
    2. Update llm_driven_coordinator.py to use this instead of intent_classifier_enhanced.py
    3. See the integration example at the bottom of this file.

File: coordinator/finetuned_classifier.py
"""

import json
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from openai import AsyncOpenAI  # async for your FastAPI backend

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logger = logging.getLogger(__name__)

# Load the model ID from the fine-tuning job output
FINETUNE_DIR = Path(__file__).resolve().parent.parent / "data" / "finetune"

# System message MUST match what was used during fine-tuning
SYSTEM_MESSAGE = (
    "You are an intent classifier for CMU-Qatar's academic advising system. "
    "Given a student's question, determine which specialized agents are needed to answer it. "
    "Respond with ONLY a comma-separated list of the required agents from: course, program, policy, planning. "
    "Use the minimum set of agents needed. Examples:\n"
    "- 'What are the prereqs for 15-122?' → course\n"
    "- 'Can I take 15-251 while on probation?' → course, policy\n"
    "- 'Plan my remaining semesters for CS major' → program, course, planning"
)


class FineTunedClassifier:
    """
    Multi-label intent classifier using a fine-tuned GPT-4o-mini model.
    
    Replaces the prompt-based intent_classifier_enhanced.py with a faster,
    cheaper, and more accurate fine-tuned model.
    
    Output format:
    {
        "intents": ["course", "policy"],     # which categories
        "agents": ["courses_agent", "policy_agent"],  # mapped agent names
        "is_multi": True,                    # whether multiple agents needed
        "raw_output": "course, policy"       # raw model output for debugging
    }
    """
    
    # Map from classification labels → your actual agent names in the system
    # These match the agent names in coordinator/coordinator.py
    AGENT_MAPPING = {
        "course":   "course_scheduling",
        "program":  "programs_requirements",
        "policy":   "policy_compliance",
        "planning": "academic_planning",
    }
    
    VALID_LABELS = set(AGENT_MAPPING.keys())
    
    def __init__(self, model_id: Optional[str] = None):
        """
        Args:
            model_id: The fine-tuned model ID (e.g., "ft:gpt-4o-mini-2024-07-18:org::abc123")
                       If None, tries to load from data/finetune/finetune_job.json
        """
        self.client = AsyncOpenAI()
        
        if model_id:
            self.model_id = model_id
        else:
            self.model_id = self._load_model_id()
        
        logger.info(f"FineTunedClassifier initialized with model: {self.model_id}")
    
    def _load_model_id(self) -> str:
        """Load the fine-tuned model ID from the job file."""
        job_file = FINETUNE_DIR / "finetune_job.json"
        
        if not job_file.exists():
            raise FileNotFoundError(
                f"Fine-tuning job file not found at {job_file}. "
                "Either pass model_id directly or run the fine-tuning pipeline first."
            )
        
        with open(job_file) as f:
            job_info = json.load(f)
        
        model_id = job_info.get("fine_tuned_model")
        if not model_id:
            raise ValueError(
                "Fine-tuned model not ready yet. "
                "Run 'python 03_finetune.py status' to check progress."
            )
        
        return model_id
    
    async def classify(self, query: str, student_profile: Optional[dict] = None) -> dict:
        """
        Classify a student query into one or more agent categories.
        
        Args:
            query: The student's question
            student_profile: Optional student context (not used by classifier directly,
                           but available if you want to add it to the prompt later)
        
        Returns:
            dict with intents, agents, is_multi, raw_output
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    {"role": "user", "content": query}
                ],
                max_tokens=20,      # output is just labels, very short
                temperature=0,       # deterministic for classification
            )
            
            raw_output = response.choices[0].message.content.strip().lower()
            
            # Parse comma-separated labels
            labels = [l.strip() for l in raw_output.split(",")]
            labels = [l for l in labels if l in self.VALID_LABELS]
            
            # Fallback: if parsing fails or returns empty, route to all agents
            if not labels:
                logger.warning(
                    f"Classifier returned invalid output '{raw_output}' for query: {query[:50]}..."
                    " Falling back to all agents."
                )
                labels = list(self.VALID_LABELS)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_labels = []
            for l in labels:
                if l not in seen:
                    seen.add(l)
                    unique_labels.append(l)
            
            agents = [self.AGENT_MAPPING[l] for l in unique_labels]
            
            result = {
                "intents": unique_labels,
                "agents": agents,
                "is_multi": len(unique_labels) > 1,
                "raw_output": raw_output
            }
            
            logger.info(
                f"Classified: '{query[:50]}...' → {unique_labels} "
                f"(multi={result['is_multi']})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Classification failed for '{query[:50]}...': {e}")
            # Safe fallback: route to all agents
            return {
                "intents": list(self.VALID_LABELS),
                "agents": list(self.AGENT_MAPPING.values()),
                "is_multi": True,
                "raw_output": f"ERROR: {str(e)}"
            }


# ============================================================
# OPTIONAL: Hybrid Classifier with Confidence-Based Fallback
# ============================================================

class HybridClassifier:
    """
    Uses the fine-tuned model as primary, falls back to prompt-based 
    classification if the fine-tuned model seems uncertain.
    
    This is useful during the transition period while you validate 
    the fine-tuned model's accuracy.
    """
    
    def __init__(
        self, 
        finetuned_model_id: Optional[str] = None,
        fallback_model: str = "gpt-4o-mini",
        use_fallback: bool = True
    ):
        self.primary = FineTunedClassifier(model_id=finetuned_model_id)
        self.fallback_model = fallback_model
        self.use_fallback = use_fallback
        self.client = AsyncOpenAI()
    
    async def classify(self, query: str, student_profile: Optional[dict] = None) -> dict:
        """Classify with primary model, fallback if result seems off."""
        result = await self.primary.classify(query, student_profile)
        
        # If the primary model returned an error or all agents, try fallback
        if self.use_fallback and "ERROR" in result.get("raw_output", ""):
            logger.info("Primary classifier failed, using fallback...")
            return await self._fallback_classify(query)
        
        return result
    
    async def _fallback_classify(self, query: str) -> dict:
        """Prompt-based fallback classification (your original approach)."""
        fallback_prompt = f"""Classify this CMU-Qatar student query. Which agents are needed?
Respond with ONLY a comma-separated list from: course, program, policy, planning

Query: {query}"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.fallback_model,
                messages=[
                    {"role": "system", "content": "You are an intent classifier."},
                    {"role": "user", "content": fallback_prompt}
                ],
                max_tokens=20,
                temperature=0
            )
            
            raw = response.choices[0].message.content.strip().lower()
            labels = [l.strip() for l in raw.split(",") if l.strip() in FineTunedClassifier.VALID_LABELS]
            
            if not labels:
                labels = list(FineTunedClassifier.VALID_LABELS)
            
            agents = [FineTunedClassifier.AGENT_MAPPING[l] for l in labels]
            
            return {
                "intents": labels,
                "agents": agents,
                "is_multi": len(labels) > 1,
                "raw_output": raw,
                "used_fallback": True
            }
        except Exception as e:
            logger.error(f"Fallback classification also failed: {e}")
            return {
                "intents": list(FineTunedClassifier.VALID_LABELS),
                "agents": list(FineTunedClassifier.AGENT_MAPPING.values()),
                "is_multi": True,
                "raw_output": f"FALLBACK_ERROR: {e}",
                "used_fallback": True
            }


# ============================================================
# INTEGRATION EXAMPLE
# ============================================================
"""
How to integrate into your existing coordinator/llm_driven_coordinator.py:

BEFORE (prompt-based):
------
    from coordinator.intent_classifier_enhanced import IntentClassifier
    
    class LLMDrivenCoordinator:
        def __init__(self):
            self.classifier = IntentClassifier()
        
        async def handle_query(self, query, profile):
            intent = await self.classifier.classify(query)
            agents_to_run = self._get_agents(intent)
            ...

AFTER (fine-tuned):
------
    from coordinator.finetuned_classifier import FineTunedClassifier
    # or: from coordinator.finetuned_classifier import HybridClassifier
    
    class LLMDrivenCoordinator:
        def __init__(self):
            # Option A: Fine-tuned only (after validation)
            self.classifier = FineTunedClassifier()
            
            # Option B: Hybrid (during transition)
            # self.classifier = HybridClassifier(use_fallback=True)
        
        async def handle_query(self, query, profile):
            result = await self.classifier.classify(query, profile)
            
            # result["agents"] gives you the list directly:
            # e.g., ["courses_agent", "policy_agent"]
            agents_to_run = result["agents"]
            is_multi = result["is_multi"]
            
            # Run agents (your existing parallel execution logic)
            if is_multi:
                # Run selected agents in parallel
                agent_outputs = await asyncio.gather(*[
                    self.run_agent(name, query, profile)
                    for name in agents_to_run
                ])
            else:
                # Single agent
                agent_outputs = [
                    await self.run_agent(agents_to_run[0], query, profile)
                ]
            
            # Continue with your existing synthesis logic...
            ...
"""
