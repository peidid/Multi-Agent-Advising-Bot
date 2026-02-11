# AdvisingBot: Multi-Label Fine-Tuning Pipeline

## Overview

This pipeline replaces the **prompt-based intent classifier** in your coordinator with a **fine-tuned GPT-4o-mini model** that does multi-label classification — meaning it outputs exactly which agents are needed for each query (e.g., `course, policy` instead of just `multi`).

## Why Multi-Label Instead of Single-Label?

| Approach | Output for "Can I retake 15-122 while on probation?" | Agents Activated |
|----------|------------------------------------------------------|-----------------|
| Single-label (`multi`) | `multi` | All 4 agents (wasteful) |
| **Multi-label** | `course, policy` | Only 2 agents (precise) |

Multi-label routing skips unnecessary agents → **faster responses + lower cost**.

---

## Pipeline Steps

### Prerequisites
```bash
pip install openai tqdm
export OPENAI_API_KEY="sk-..."
```

### Step 1: Generate Training Data
```bash
cd AdvisingBot/
python scripts/01_generate_training_data.py
```

**What it does:**
- Reads your existing `data/courses/`, `data/programs/`, `data/policies/` files
  - ~2500 course JSON files (samples 150 by default)
  - ~55 program files (MD + JSON)
  - ~32 policy MD files
- Sends each file to GPT-4o to generate diverse student questions
- Generates multi-agent combination questions for all label pairs
- Outputs → `data/finetune/raw_questions.json`

**Expected output:** ~2000-3000 questions across all label combinations.

**Cost estimate:** ~$5-15 in API calls (one-time).

**Time:** ~30-60 minutes depending on how many course files you process.

### Step 2: Clean and Split
```bash
python scripts/02_clean_and_split.py
```

**What it does:**
- Validates all questions (removes malformed entries)
- Deduplicates exact and near-duplicate questions
- Shuffles and splits into 85% train / 15% validation
- Formats into OpenAI fine-tuning JSONL format
- Outputs → `data/finetune/train.jsonl`, `data/finetune/val.jsonl`

### Step 3: Fine-Tune
```bash
# Launch the fine-tuning job
python scripts/03_finetune.py launch

# Check status (run periodically)
python scripts/03_finetune.py status

# Test with sample queries
python scripts/03_finetune.py test

# Run full evaluation on validation set
python scripts/03_finetune.py evaluate
```

**Time:** 10-30 minutes for fine-tuning to complete.

**Cost:** ~$1-5 depending on dataset size (GPT-4o-mini fine-tuning is cheap).

### Step 4: Integrate
```bash
# Copy the classifier to your project
cp scripts/04_finetuned_classifier.py AdvisingBot/coordinator/finetuned_classifier.py
```

Then update `coordinator/llm_driven_coordinator.py`:

```python
# BEFORE
from coordinator.intent_classifier_enhanced import IntentClassifier

# AFTER
from coordinator.finetuned_classifier import FineTunedClassifier
# or for a safe transition:
from coordinator.finetuned_classifier import HybridClassifier
```

---

## File Placement in Your Project

```
AdvisingBot/
├── scripts/                              # NEW - pipeline scripts
│   ├── 01_generate_training_data.py      # → Run once to generate data
│   ├── 02_clean_and_split.py             # → Run once to prepare data  
│   └── 03_finetune.py                    # → Run once to train model
├── coordinator/
│   ├── coordinator.py                    # Existing (no change)
│   ├── llm_driven_coordinator.py         # Update import (see Step 4)
│   ├── intent_classifier_enhanced.py     # Keep as fallback
│   └── finetuned_classifier.py           # NEW - from 04_finetuned_classifier.py
├── data/
│   ├── courses/                          # Existing (read by Step 1)
│   ├── programs/                         # Existing (read by Step 1)
│   ├── policies/                         # Existing (read by Step 1)
│   └── finetune/                         # NEW - generated data
│       ├── raw_questions.json            # Generated questions
│       ├── train.jsonl                   # Training data
│       ├── val.jsonl                     # Validation data
│       ├── finetune_job.json             # Job metadata + model ID
│       ├── stats.json                    # Data statistics
│       └── eval_results.json             # Evaluation results
```

---

## Expected Performance Gains

| Metric | Before (prompt-based) | After (fine-tuned) |
|--------|----------------------|-------------------|
| Classification latency | ~1-2 seconds | ~200-400ms |
| Cost per query | ~$0.01-0.03 | ~$0.0003 |
| Prompt tokens used | ~500-1000 | ~80 |
| Agent precision | Routes to all or one | Routes to exact set needed |
| Overall response time | Reduced by skipping unnecessary agents |

---

## Troubleshooting

**Q: What if accuracy is low (<85%)?**
- Generate more training data (increase `QUESTIONS_PER_SOURCE` and `MAX_COURSE_FILES`)
- Check for label noise in the generated data (manually review `raw_questions.json`)
- Increase `n_epochs` to 4-5 in the fine-tuning config
- Use the `HybridClassifier` to catch errors

**Q: What if the model always returns all agents?**
- Likely not enough single-agent examples in training data
- Check label distribution in `stats.json` — ensure single-agent examples are the majority

**Q: Can I retrain when data changes?**
- Yes, just rerun Steps 1-3. Course catalogs change per semester, so retrain each semester.
- Keep the old model running while the new one trains (zero downtime).

**Q: What about the coordinator's other functions (workflow planning, synthesis)?**
- This ONLY replaces intent classification. The coordinator's LLM-driven workflow planning,
  agent execution, and answer synthesis remain unchanged.

**Q: What are the agent name mappings?**
- The classifier outputs labels: `course`, `program`, `policy`, `planning`
- These are mapped to your actual agent names in `coordinator.py`:
  - `course` → `course_scheduling`
  - `program` → `programs_requirements`
  - `policy` → `policy_compliance`
  - `planning` → `academic_planning`
