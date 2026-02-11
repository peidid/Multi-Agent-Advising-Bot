"""
Step 2: Clean, Deduplicate, Balance, and Split Training Data
=============================================================
Takes the raw generated questions and prepares them for fine-tuning.

Usage:
    python scripts/02_clean_and_split.py

Input:  data/finetune/raw_questions.json
Output: data/finetune/train.jsonl
        data/finetune/val.jsonl
        data/finetune/stats.json
"""

import json
import random
import hashlib
from pathlib import Path
from collections import Counter

# ============================================================
# CONFIGURATION
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
FINETUNE_DIR = PROJECT_ROOT / "data" / "finetune"

INPUT_FILE = FINETUNE_DIR / "raw_questions.json"
TRAIN_FILE = FINETUNE_DIR / "train.jsonl"
VAL_FILE = FINETUNE_DIR / "val.jsonl"
STATS_FILE = FINETUNE_DIR / "stats.json"

TRAIN_RATIO = 0.85  # 85% train, 15% validation
MIN_QUESTION_LENGTH = 10  # characters
SIMILARITY_THRESHOLD = 0.85  # for dedup (simple approach)

VALID_LABELS = {"course", "program", "policy", "planning"}

# The system message used during fine-tuning AND inference (must match exactly)
SYSTEM_MESSAGE = (
    "You are an intent classifier for CMU-Qatar's academic advising system. "
    "Given a student's question, determine which specialized agents are needed to answer it. "
    "Respond with ONLY a comma-separated list of the required agents from: course, program, policy, planning. "
    "Use the minimum set of agents needed. Examples:\n"
    "- 'What are the prereqs for 15-122?' → course\n"
    "- 'Can I take 15-251 while on probation?' → course, policy\n"
    "- 'Plan my remaining semesters for CS major' → program, course, planning"
)


# ============================================================
# CLEANING
# ============================================================

def normalize_question(q: str) -> str:
    """Normalize a question for deduplication."""
    return q.lower().strip().rstrip("?").strip()


def question_hash(q: str) -> str:
    """Create a hash for fast exact-match dedup."""
    return hashlib.md5(normalize_question(q).encode()).hexdigest()


def is_valid_question(item: dict) -> bool:
    """Validate a single question entry."""
    if not isinstance(item, dict):
        return False
    if "question" not in item or "labels" not in item:
        return False
    if not isinstance(item["question"], str):
        return False
    if len(item["question"].strip()) < MIN_QUESTION_LENGTH:
        return False
    if not isinstance(item["labels"], list):
        return False
    # All labels must be valid
    if not all(l in VALID_LABELS for l in item["labels"]):
        return False
    if len(item["labels"]) == 0:
        return False
    return True


def clean_labels(labels: list) -> list:
    """Sort and deduplicate labels for consistency."""
    return sorted(set(l.strip().lower() for l in labels if l.strip().lower() in VALID_LABELS))


def deduplicate(data: list[dict]) -> list[dict]:
    """Remove duplicate and near-duplicate questions."""
    seen_hashes = set()
    seen_normalized = set()
    unique = []
    
    for item in data:
        h = question_hash(item["question"])
        norm = normalize_question(item["question"])
        
        # Exact match dedup
        if h in seen_hashes:
            continue
        
        # Near-duplicate: check if normalized form was seen
        # (catches "What are prereqs for 15-122?" vs "what are prereqs for 15-122")
        if norm in seen_normalized:
            continue
        
        seen_hashes.add(h)
        seen_normalized.add(norm)
        unique.append(item)
    
    return unique


# ============================================================
# FORMAT FOR OPENAI FINE-TUNING
# ============================================================

def to_finetune_entry(item: dict) -> dict:
    """
    Convert a question to OpenAI fine-tuning format.
    
    The assistant response is a comma-separated list of agent labels.
    This is what the fine-tuned model will learn to output.
    """
    labels_str = ", ".join(item["labels"])
    
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MESSAGE},
            {"role": "user", "content": item["question"]},
            {"role": "assistant", "content": labels_str}
        ]
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("Step 2: Clean, Deduplicate, and Split")
    print("=" * 60)
    
    # Load raw data
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        print("Run 01_generate_training_data.py first.")
        return
    
    with open(INPUT_FILE, encoding="utf-8") as f:
        raw_data = json.load(f)
    
    print(f"\nRaw data loaded: {len(raw_data)} questions")
    
    # --- Clean ---
    cleaned = []
    invalid_count = 0
    for item in raw_data:
        if not is_valid_question(item):
            invalid_count += 1
            continue
        item["labels"] = clean_labels(item["labels"])
        if item["labels"]:  # might be empty after cleaning
            cleaned.append(item)
        else:
            invalid_count += 1
    
    print(f"After validation: {len(cleaned)} valid, {invalid_count} removed")
    
    # --- Deduplicate ---
    unique = deduplicate(cleaned)
    print(f"After dedup:      {len(unique)} unique questions")
    
    # --- Check distribution ---
    label_combos = Counter(tuple(item["labels"]) for item in unique)
    print("\nLabel distribution:")
    for combo, count in sorted(label_combos.items(), key=lambda x: -x[1]):
        print(f"  {', '.join(combo):45s} → {count:4d}")
    
    # Also count individual label frequency
    individual_labels = Counter()
    for item in unique:
        for label in item["labels"]:
            individual_labels[label] += 1
    
    print("\nIndividual label frequency (a label can appear in multiple combos):")
    for label, count in individual_labels.most_common():
        print(f"  {label:15s} → {count:4d}")
    
    # --- Shuffle and Split ---
    random.seed(42)  # reproducible
    random.shuffle(unique)
    
    split_idx = int(len(unique) * TRAIN_RATIO)
    train_data = unique[:split_idx]
    val_data = unique[split_idx:]
    
    print(f"\nSplit: {len(train_data)} train / {len(val_data)} validation")
    
    # --- Write JSONL files ---
    def write_jsonl(data: list[dict], path: Path):
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                entry = to_finetune_entry(item)
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    write_jsonl(train_data, TRAIN_FILE)
    write_jsonl(val_data, VAL_FILE)
    
    print(f"\n✅ Written:")
    print(f"  Train: {TRAIN_FILE}")
    print(f"  Val:   {VAL_FILE}")
    
    # --- Save stats ---
    stats = {
        "raw_count": len(raw_data),
        "cleaned_count": len(cleaned),
        "unique_count": len(unique),
        "train_count": len(train_data),
        "val_count": len(val_data),
        "label_distribution": {", ".join(k): v for k, v in label_combos.items()},
        "individual_label_frequency": dict(individual_labels),
        "system_message": SYSTEM_MESSAGE,
    }
    
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    
    print(f"  Stats: {STATS_FILE}")
    
    # --- Show sample entries ---
    print("\n--- Sample training entries ---")
    for item in random.sample(train_data, min(5, len(train_data))):
        labels_str = ", ".join(item["labels"])
        print(f"  Q: {item['question'][:80]}...")
        print(f"  A: {labels_str}")
        print()


if __name__ == "__main__":
    main()
