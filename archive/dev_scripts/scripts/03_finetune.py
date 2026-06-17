"""
Step 3: Fine-Tune on OpenAI and Monitor Progress
==================================================
Uploads training data and launches a fine-tuning job on gpt-4o-mini.

Usage:
    python scripts/03_finetune.py launch    # Upload files + start job
    python scripts/03_finetune.py status    # Check job status
    python scripts/03_finetune.py test      # Test the fine-tuned model

Prerequisites:
    pip install openai
    export OPENAI_API_KEY="sk-..."
"""

import sys
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = OpenAI()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FINETUNE_DIR = PROJECT_ROOT / "data" / "finetune"
TRAIN_FILE = FINETUNE_DIR / "train.jsonl"
VAL_FILE = FINETUNE_DIR / "val.jsonl"
JOB_FILE = FINETUNE_DIR / "finetune_job.json"  # stores job metadata

# Must match the system message in 02_clean_and_split.py
SYSTEM_MESSAGE = (
    "You are an intent classifier for CMU-Qatar's academic advising system. "
    "Given a student's question, determine which specialized agents are needed to answer it. "
    "Respond with ONLY a comma-separated list of the required agents from: course, program, policy, planning. "
    "Use the minimum set of agents needed. Examples:\n"
    "- 'What are the prereqs for 15-122?' → course\n"
    "- 'Can I take 15-251 while on probation?' → course, policy\n"
    "- 'Plan my remaining semesters for CS major' → program, course, planning"
)


def launch():
    """Upload files and start fine-tuning job."""
    print("📤 Uploading training file...")
    with open(TRAIN_FILE, "rb") as f:
        train_upload = client.files.create(file=f, purpose="fine-tune")
    print(f"  Train file ID: {train_upload.id}")

    print("📤 Uploading validation file...")
    with open(VAL_FILE, "rb") as f:
        val_upload = client.files.create(file=f, purpose="fine-tune")
    print(f"  Val file ID: {val_upload.id}")
    
    # Wait for files to be processed
    print("⏳ Waiting for files to be processed...")
    for file_id in [train_upload.id, val_upload.id]:
        while True:
            file_info = client.files.retrieve(file_id)
            if file_info.status == "processed":
                break
            time.sleep(2)
    print("  Files processed ✅")
    
    print("\n🚀 Starting fine-tuning job...")
    job = client.fine_tuning.jobs.create(
        training_file=train_upload.id,
        validation_file=val_upload.id,
        model="gpt-4o-mini-2024-07-18",
        hyperparameters={
            "n_epochs": 3,              # 2-4 is typical for classification
            "batch_size": "auto",        # let OpenAI optimize
            "learning_rate_multiplier": "auto"
        },
        suffix="advisingbot-router"  # model name suffix
    )
    
    # Save job info
    job_info = {
        "job_id": job.id,
        "model": job.model,
        "status": job.status,
        "train_file_id": train_upload.id,
        "val_file_id": val_upload.id,
        "created_at": str(job.created_at),
    }
    with open(JOB_FILE, "w") as f:
        json.dump(job_info, f, indent=2)
    
    print(f"\n✅ Job created!")
    print(f"  Job ID:  {job.id}")
    print(f"  Model:   {job.model}")
    print(f"  Status:  {job.status}")
    print(f"\nRun 'python 03_finetune.py status' to monitor progress.")
    print(f"Typically takes 10-30 minutes.\n")


def status():
    """Check fine-tuning job status."""
    if not JOB_FILE.exists():
        print("❌ No job file found. Run 'launch' first.")
        return
    
    with open(JOB_FILE) as f:
        job_info = json.load(f)
    
    job = client.fine_tuning.jobs.retrieve(job_info["job_id"])
    
    print(f"Job ID:           {job.id}")
    print(f"Status:           {job.status}")
    print(f"Model:            {job.model}")
    print(f"Fine-tuned model: {job.fine_tuned_model or 'Not ready yet'}")
    
    if job.status == "succeeded":
        # Save the model ID
        job_info["fine_tuned_model"] = job.fine_tuned_model
        with open(JOB_FILE, "w") as f:
            json.dump(job_info, f, indent=2)
        print(f"\n🎉 Fine-tuning complete!")
        print(f"Model ID: {job.fine_tuned_model}")
        print(f"\nSaved to {JOB_FILE}")
        print(f"Run 'python 03_finetune.py test' to try it out.")
    
    elif job.status == "failed":
        print(f"\n❌ Fine-tuning failed!")
        print(f"Error: {job.error}")
    
    else:
        # Show recent events
        print(f"\n📊 Recent events:")
        events = client.fine_tuning.jobs.list_events(job.id, limit=10)
        for event in reversed(events.data):
            print(f"  [{event.level}] {event.message}")


def test():
    """Test the fine-tuned model with sample queries."""
    if not JOB_FILE.exists():
        print("❌ No job file found.")
        return
    
    with open(JOB_FILE) as f:
        job_info = json.load(f)
    
    model_id = job_info.get("fine_tuned_model")
    if not model_id:
        print("❌ Fine-tuned model not ready. Run 'status' to check.")
        return
    
    # Test queries covering all combinations
    test_queries = [
        # Single agent
        "What are the prereqs for 15-122?",
        "What courses are required for the CS major?",
        "What is the academic probation policy?",
        "How many courses should I take per semester?",
        
        # Two agents
        "Can I take 15-251 next semester if I'm on academic probation?",
        "Which electives count as technical electives for the CS major?",
        "Can I still graduate on time if I add a business minor?",
        "What's the maximum course load policy and how does it affect my plan?",
        
        # Three+ agents
        "I'm on probation and want to switch from BA to CS. What courses do I need and can I graduate in time?",
        "Plan my remaining semesters to finish the IS major with a CS minor, considering I failed 15-122.",
    ]
    
    print(f"Testing model: {model_id}\n")
    print("-" * 80)
    
    for query in test_queries:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": query}
            ],
            max_tokens=20,
            temperature=0
        )
        
        result = response.choices[0].message.content.strip()
        print(f"Q: {query}")
        print(f"A: {result}")
        print()


def evaluate():
    """Run full evaluation on the validation set."""
    if not JOB_FILE.exists():
        print("❌ No job file found.")
        return
    
    with open(JOB_FILE) as f:
        job_info = json.load(f)
    
    model_id = job_info.get("fine_tuned_model")
    if not model_id:
        print("❌ Fine-tuned model not ready.")
        return
    
    if not VAL_FILE.exists():
        print("❌ Validation file not found.")
        return
    
    print(f"Evaluating model: {model_id}")
    print("Loading validation data...")
    
    val_data = []
    with open(VAL_FILE) as f:
        for line in f:
            val_data.append(json.loads(line))
    
    correct = 0
    total = len(val_data)
    errors = []
    
    print(f"Running {total} predictions...\n")
    
    for i, entry in enumerate(val_data):
        question = entry["messages"][1]["content"]
        expected = entry["messages"][2]["content"]
        
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": question}
            ],
            max_tokens=20,
            temperature=0
        )
        
        predicted = response.choices[0].message.content.strip()
        
        # Normalize for comparison: sort labels
        expected_set = set(l.strip() for l in expected.split(","))
        predicted_set = set(l.strip() for l in predicted.split(","))
        
        if expected_set == predicted_set:
            correct += 1
        else:
            errors.append({
                "question": question,
                "expected": expected,
                "predicted": predicted
            })
        
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{total} ({correct}/{i+1} correct)")
        
        time.sleep(0.1)  # rate limit
    
    accuracy = correct / total * 100
    print(f"\n{'='*60}")
    print(f"RESULTS")
    print(f"{'='*60}")
    print(f"Accuracy: {correct}/{total} = {accuracy:.1f}%")
    
    if errors:
        print(f"\nSample errors ({min(10, len(errors))} of {len(errors)}):")
        for err in errors[:10]:
            print(f"  Q: {err['question'][:70]}...")
            print(f"  Expected:  {err['expected']}")
            print(f"  Predicted: {err['predicted']}")
            print()
    
    # Save evaluation results
    eval_results = {
        "model": model_id,
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "errors": errors
    }
    eval_path = FINETUNE_DIR / "eval_results.json"
    with open(eval_path, "w") as f:
        json.dump(eval_results, f, indent=2)
    print(f"Full results saved to: {eval_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 03_finetune.py [launch|status|test|evaluate]")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "launch":
        launch()
    elif command == "status":
        status()
    elif command == "test":
        test()
    elif command == "evaluate":
        evaluate()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python 03_finetune.py [launch|status|test|evaluate]")
