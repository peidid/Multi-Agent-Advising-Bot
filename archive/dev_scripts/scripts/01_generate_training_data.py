"""
Step 1: Generate Multi-Label Training Data for Intent Classification
====================================================================
This script reads your existing AdvisingBot data (courses, programs, policies)
and uses GPT-4o to generate diverse student questions with multi-label annotations.

Usage:
    cd AdvisingBot/
    python scripts/01_generate_training_data.py

Output:
    data/finetune/raw_questions.json

Prerequisites:
    pip install openai tqdm
    export OPENAI_API_KEY="sk-..."
"""

import os
import json
import random
import time
from pathlib import Path
from typing import Optional
from tqdm import tqdm
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

client = OpenAI()  # reads OPENAI_API_KEY from env

# Parallel processing config
MAX_WORKERS = 5  # Number of parallel API calls (adjust based on your rate limit)

# ============================================================
# CONFIGURATION - Adjust paths to match your project structure
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # AdvisingBot/
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = DATA_DIR / "finetune"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# How many files to sample per category (for context, not per-file generation)
MAX_COURSE_FILES = 30  # sample courses to show model what data looks like
MAX_PROGRAM_FILES = 20  # sample programs
MAX_POLICY_FILES = 20   # sample policies

# Questions per category (total target - will be generated in batches)
QUESTIONS_PER_CATEGORY = {
    "course": 300,    # 300 diverse course questions
    "program": 250,   # 250 diverse program questions
    "policy": 250,    # 250 diverse policy questions
    "planning": 150,  # 150 diverse planning questions
}
# Total single-agent: ~950 questions

BATCH_SIZE = 50  # Generate 50 questions per API call (fits in response limit)

MODEL = "gpt-4o"  # use best model for all generation (ensures quality + diversity)
VERBOSE = True  # Set to True to see sample questions as they're generated


# ============================================================
# SINGLE-AGENT QUESTION GENERATION
# ============================================================

SINGLE_AGENT_PROMPTS = {
    "course": """You are generating training data for a student query intent classifier at CMU-Qatar.

Given this course data, generate {n} HIGHLY DIVERSE questions a student might ask about this course.

CRITICAL: Each question MUST be different. Use these categories (at least 2 questions per category):
1. Prerequisites/corequisites: "Do I need X before taking this?", "What should I take first?"
2. Scheduling: "When is this offered?", "Is this a fall or spring course?", "What time does it meet?"
3. Workload/difficulty: "How hard is this class?", "How many hours per week?", "Is it manageable with X?"
4. Content/topics: "What will I learn?", "Does this cover X topic?", "What's the focus?"
5. Assessment: "How is grading done?", "Are there exams or projects?", "What's the homework like?"
6. Eligibility: "Can freshmen take this?", "Is this open to non-majors?", "Any restrictions?"
7. Comparison: "How does this compare to X?", "Should I take this or Y?", "Is this the right level for me?"
8. Practical: "Is this course useful for X career?", "Do employers value this?", "Will this help with Y?"

VARIETY REQUIREMENTS:
- Mix question lengths: some very short ("15-122 prereqs?"), some conversational ("Hey, I was wondering if...")
- Mix formality: casual ("yo is this class hard?") to formal ("What are the learning objectives?")
- Some should mention the course by number, others by name, others just "this course"
- NO TWO QUESTIONS should start with the same 3 words

Return ONLY a valid JSON array:
[{{"question": "...", "labels": ["course"]}}]

Course data:
{data}""",

    "program": """You are generating training data for a student query intent classifier at CMU-Qatar.

Given this degree program description, generate {n} HIGHLY DIVERSE questions about degree requirements.

CRITICAL: Each question MUST be different. Use these categories (at least 2 per category):
1. Required courses: "What courses do I need for X major?", "Is Y required?", "Core requirements?"
2. Electives: "Which electives count?", "How many free electives?", "Can I choose X as elective?"
3. Units/credits: "How many units to graduate?", "Total credits needed?", "Units for the minor?"
4. Double major/minor: "Can I double major in X and Y?", "Is adding a minor feasible?", "Overlap between majors?"
5. Progress check: "Am I on track?", "What do I still need?", "Have I satisfied the X requirement?"
6. Tracks/concentrations: "What tracks are available?", "Difference between concentrations?", "Which track for AI?"
7. Substitutions: "Can X substitute for Y?", "Are there alternatives to Z?", "Equivalent courses?"
8. Graduation: "Can I graduate early?", "What's left for me to complete?", "Minimum semesters needed?"

VARIETY REQUIREMENTS:
- Mix: short ("CS major requirements?") and long ("I'm a sophomore wondering what courses I still need...")
- Mix formality: casual ("what do I gotta take?") to formal ("Please list the requirements")
- Some specific ("15-251 for CS?"), some general ("math requirements")
- NO TWO QUESTIONS should start with the same 3 words

Return ONLY a valid JSON array:
[{{"question": "...", "labels": ["program"]}}]

Program data:
{data}""",

    "policy": """You are generating training data for a student query intent classifier at CMU-Qatar.

Given this academic policy document, generate {n} HIGHLY DIVERSE questions about policies and rules.

CRITICAL: Each question MUST be different. Use these categories (at least 2 per category):
1. Deadlines: "When is the drop deadline?", "Last day to add?", "Registration dates?"
2. GPA/Standing: "What GPA for dean's list?", "Probation threshold?", "Good standing requirements?"
3. Withdrawal: "Can I withdraw from a class?", "W on transcript impact?", "Late withdrawal policy?"
4. Overload: "Can I take more than 54 units?", "Overload approval process?", "Max units allowed?"
5. Pass/Fail: "Can I P/F this course?", "Deadline for P/F election?", "Which courses allow P/F?"
6. Probation/Recovery: "What happens if my GPA drops?", "How to get off probation?", "Academic warning?"
7. Appeals/Exceptions: "Can I appeal this?", "Exception request process?", "Who do I talk to about X?"
8. Consequences: "What if I fail?", "Retake policy?", "Academic integrity violation consequences?"

VARIETY REQUIREMENTS:
- Mix worried tone ("I'm freaking out, what if...") and calm inquiry ("Could you explain the policy on...")
- Some hypothetical ("If I were to..."), some immediate ("I need to drop NOW")
- Some reference specific situations from the policy document
- NO TWO QUESTIONS should start with the same 3 words

Return ONLY a valid JSON array:
[{{"question": "...", "labels": ["policy"]}}]

Policy data:
{data}"""
}


# ============================================================
# MULTI-AGENT QUESTION GENERATION
# ============================================================

# All 2-agent, 3-agent, and 4-agent combinations
# Total: 6 two-agent + 4 three-agent + 1 four-agent = 11 combinations
MULTI_AGENT_COMBOS = [
    # ==================== 2-AGENT COMBINATIONS (6 total) ====================
    {
        "labels": ["course", "policy"],
        "description": "Questions needing both course details AND policy knowledge",
        "scenarios": [
            "Taking courses while on academic probation",
            "Prerequisite waiver policies",
            "Overloading (taking more than max units)",
            "Retaking a failed course - policy + which semester offered",
            "Pass/fail vs letter grade policies for specific courses",
            "Cross-campus course policies",
            "Independent study course policies",
            "Auditing courses - rules and restrictions",
        ],
        "count": 80
    },
    {
        "labels": ["course", "planning"],
        "description": "Questions about course selection in context of semester planning",
        "scenarios": [
            "What to take next semester given current progress",
            "Course sequencing and prerequisite chains",
            "Workload balancing across semesters",
            "Summer course planning",
            "Which elective to take when",
            "Handling a course conflict between two needed courses",
            "Best time to take difficult courses",
            "Internship semester course planning",
        ],
        "count": 80
    },
    {
        "labels": ["course", "program"],
        "description": "Questions about which specific courses fulfill degree requirements",
        "scenarios": [
            "Which electives count for CS technical electives",
            "Can a specific course count for both major and minor",
            "Substitutions for required courses",
            "Double-counting courses across requirements",
            "New courses that might fulfill old requirements",
            "Which courses satisfy the math requirement",
            "Does this course count for my concentration",
        ],
        "count": 80
    },
    {
        "labels": ["program", "planning"],
        "description": "Questions about completing degree requirements over time",
        "scenarios": [
            "Can I graduate early with this major",
            "Double major feasibility and timeline",
            "Adding a minor late (junior/senior year)",
            "Switching majors and what transfers",
            "How many semesters left to complete requirements",
            "Sample 4-year plan for my major",
            "Catching up after changing major",
        ],
        "count": 80
    },
    {
        "labels": ["program", "policy"],
        "description": "Questions about degree requirements and academic policies",
        "scenarios": [
            "GPA requirements for declaring a major/minor",
            "Maximum time to complete degree requirements",
            "Transfer credit policies for degree requirements",
            "Double-counting policies between major and minor",
            "Declaring multiple majors - policy and requirements",
            "Dropping a minor - policy and implications",
            "Changing concentration within major",
        ],
        "count": 80
    },
    {
        "labels": ["policy", "planning"],
        "description": "Questions where policies constrain academic plans",
        "scenarios": [
            "Maximum units per semester policy impact on graduation",
            "Study abroad semester and credit transfer planning",
            "Leave of absence and returning timeline",
            "Probation recovery plan across semesters",
            "Dean's list / honors requirements over time",
            "Part-time enrollment policy and graduation timeline",
            "Summer course policies and planning",
        ],
        "count": 80
    },
    # ==================== 3-AGENT COMBINATIONS (4 total) ====================
    {
        "labels": ["course", "policy", "planning"],
        "description": "Complex queries needing course info, policy compliance, and scheduling",
        "scenarios": [
            "Planning next year while on probation with specific course needs",
            "Overloading next semester to make up for a withdrawal",
            "Taking graduate courses as undergrad - eligibility + planning",
            "Retaking failed courses while managing unit limits",
            "Summer overload to catch up after academic difficulty",
        ],
        "count": 60
    },
    {
        "labels": ["course", "program", "planning"],
        "description": "Degree planning with specific course details",
        "scenarios": [
            "Build a plan to finish CS major with business minor in 3 years",
            "Which remaining required courses should I take in which order",
            "Planning electives to fulfill multiple requirements simultaneously",
            "Optimal course sequence for double major",
            "Balancing core requirements and electives over semesters",
        ],
        "count": 60
    },
    {
        "labels": ["course", "program", "policy"],
        "description": "Course selection with degree and policy constraints",
        "scenarios": [
            "Can I substitute this course for a requirement given the waiver policy",
            "Double-counting policies for double majors",
            "Using AP/transfer credits to satisfy degree requirements",
            "Petition to use non-standard course for requirement",
            "Cross-listed course counting for multiple requirements",
        ],
        "count": 60
    },
    {
        "labels": ["program", "policy", "planning"],
        "description": "Degree completion with policy constraints over time",
        "scenarios": [
            "Minimum GPA required each semester to graduate on time",
            "Part-time status impact on degree completion timeline",
            "Academic recovery plan to meet graduation requirements",
            "Study abroad impact on major completion timeline",
            "Leave of absence and returning to complete degree",
        ],
        "count": 60
    },
    # ==================== 4-AGENT COMBINATION (1 total) ====================
    {
        "labels": ["course", "program", "policy", "planning"],
        "description": "The most complex queries touching all areas",
        "scenarios": [
            "I'm on probation, want to switch from BA to CS, plan my remaining semesters",
            "Full academic plan considering all requirements, policies, and course availability",
            "Recovering from academic difficulty while changing major and graduating on time",
            "Double major with study abroad while meeting all policies",
            "Transfer student catching up on requirements with unit limit constraints",
            "Senior adding minor - feasibility with course availability and graduation timeline",
        ],
        "count": 50
    },
]
# Total multi-agent: 6*80 + 4*60 + 50 = 480 + 240 + 50 = 770 questions


# ============================================================
# PLANNING-ONLY QUESTIONS (no direct data source)
# ============================================================

PLANNING_PROMPT = """Generate {n} diverse questions a CMU-Qatar student might ask that require 
ONLY academic planning advice (semester scheduling, workload management, course sequencing).

These should NOT be about specific course details, degree requirements, or policies - 
just general planning and scheduling questions.

Examples:
- "How many courses should I take per semester?"
- "Is it better to front-load hard courses or spread them out?"
- "What's a good course load for someone who also works part-time?"
- "Should I take summer courses or use it for internships?"
- "How do I balance technical and non-technical courses?"

Make questions natural - how real students would ask them.

Return ONLY a valid JSON array:
[{{"question": "...", "labels": ["planning"]}}]"""


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def call_gpt(prompt: str, model: str = None, max_retries: int = 3, max_tokens: int = 16000) -> Optional[list]:
    """Call GPT and parse JSON response with retry logic."""
    if model is None:
        model = MODEL
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=max_tokens,
                response_format={"type": "json_object"}
            )

            # Check if response has content
            if not response.choices:
                print(f"  Empty response (attempt {attempt+1}), retrying...")
                time.sleep(2)
                continue

            content = response.choices[0].message.content
            if not content:
                print(f"  Empty content (attempt {attempt+1}), retrying...")
                time.sleep(2)
                continue

            content = content.strip()
            if not content:
                print(f"  Whitespace-only content (attempt {attempt+1}), retrying...")
                time.sleep(2)
                continue

            parsed = json.loads(content)

            # Handle both {"questions": [...]} and [...] formats
            if isinstance(parsed, dict):
                # Look for the array in common keys
                for key in ["questions", "data", "results", "items"]:
                    if key in parsed:
                        return parsed[key]
                # If dict has question/labels structure, wrap in list
                if "question" in parsed:
                    return [parsed]
            elif isinstance(parsed, list):
                return parsed

            print(f"  Warning: Unexpected format, retrying... (keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)})")

        except json.JSONDecodeError as e:
            print(f"  JSON parse error (attempt {attempt+1}): {e}")
            # Log first 200 chars of content for debugging
            try:
                if content:
                    print(f"    Content preview: {content[:200]}...")
            except NameError:
                pass
            time.sleep(2)
        except Exception as e:
            print(f"  API error (attempt {attempt+1}): {e}")
            time.sleep(5)

    return None


def load_course_files(data_dir: Path, max_files: int) -> list[tuple[str, str]]:
    """Load course JSON files. Returns list of (filename, content)."""
    courses_dir = data_dir / "courses"
    if not courses_dir.exists():
        print(f"Warning: {courses_dir} not found")
        return []
    
    all_files = list(courses_dir.rglob("*.json"))
    sampled = random.sample(all_files, min(max_files, len(all_files)))
    
    results = []
    for f in sampled:
        try:
            content = f.read_text(encoding="utf-8")
            # Truncate very long files to save tokens
            if len(content) > 5000:
                content = content[:5000] + "\n... (truncated)"
            results.append((f.name, content))
        except Exception as e:
            print(f"  Error reading {f}: {e}")
    
    return results


def load_program_files(data_dir: Path) -> list[tuple[str, str]]:
    """Load program files (MD and JSON)."""
    programs_dir = data_dir / "programs"
    if not programs_dir.exists():
        print(f"Warning: {programs_dir} not found")
        return []
    
    results = []
    for f in programs_dir.rglob("*"):
        if f.suffix in (".md", ".json") and f.is_file():
            try:
                content = f.read_text(encoding="utf-8")
                if len(content) > 6000:
                    content = content[:6000] + "\n... (truncated)"
                results.append((f.name, content))
            except Exception as e:
                print(f"  Error reading {f}: {e}")
    
    return results


def load_policy_files(data_dir: Path) -> list[tuple[str, str]]:
    """Load policy markdown files."""
    policies_dir = data_dir / "policies"
    if not policies_dir.exists():
        print(f"Warning: {policies_dir} not found")
        return []
    
    results = []
    for f in policies_dir.rglob("*.md"):
        try:
            content = f.read_text(encoding="utf-8")
            if len(content) > 6000:
                content = content[:6000] + "\n... (truncated)"
            results.append((f.name, content))
        except Exception as e:
            print(f"  Error reading {f}: {e}")
    
    return results


# ============================================================
# MAIN GENERATION PIPELINE (BATCH GENERATION FOR DIVERSITY)
# ============================================================

def generate_batch(category: str, n_questions: int, sample_data: str) -> list[dict]:
    """Generate questions for a category using multiple API calls for better results."""
    all_questions = []

    # Calculate number of batches needed
    num_batches = (n_questions + BATCH_SIZE - 1) // BATCH_SIZE  # ceiling division
    questions_per_batch = BATCH_SIZE

    print(f"  Generating {n_questions} {category} questions in {num_batches} batches...")

    # Track previously generated questions to ensure diversity across batches
    previous_starters = set()

    for batch_num in range(num_batches):
        # Calculate how many questions for this batch
        remaining = n_questions - len(all_questions)
        batch_target = min(questions_per_batch, remaining)

        if batch_target <= 0:
            break

        # Build exclusion list from previous batches (sample to avoid prompt bloat)
        exclusion_examples = ""
        if previous_starters:
            sample_starters = list(previous_starters)[:30]
            exclusion_examples = f"""
AVOID these question starters (already generated):
{chr(10).join(f'- "{s}..."' for s in sample_starters)}
"""

        prompt = f"""You are generating training data for a student query intent classifier at CMU-Qatar.

Generate EXACTLY {batch_target} HIGHLY DIVERSE questions about {category.upper()}.
This is batch {batch_num + 1} of {num_batches} - make these different from typical questions!

SAMPLE DATA (for context):
{sample_data[:6000]}
{exclusion_examples}
CRITICAL DIVERSITY REQUIREMENTS:
1. NO TWO QUESTIONS should start with the same 4 words
2. Mix question lengths:
   - Very short (3-6 words): "15-122 prereqs?", "CS major requirements?"
   - Medium (7-15 words): "What are the prerequisites for taking 15-213?"
   - Long/conversational (16+ words): "Hey, I'm a sophomore and I was wondering if I could..."

3. Mix formality levels:
   - Casual/slang: "yo is this class hard?", "what do I gotta take?"
   - Normal: "What are the prerequisites?", "Can I take this course?"
   - Formal: "I would like to inquire about the requirements for..."

4. Mix emotional tones:
   - Neutral: "What courses are required?"
   - Curious: "I was wondering...", "Out of curiosity..."
   - Stressed: "I'm freaking out...", "URGENT:", "I'm panicking..."
   - Excited: "I really want to take...", "I'm excited about..."

5. Mix question types:
   - Direct questions: "What is..?", "How many...?", "When...?"
   - Yes/No questions: "Can I...?", "Is it possible...?", "Do I need...?"
   - Hypothetical: "What if I...?", "If I were to..."
   - Requests: "Tell me about...", "I need to know...", "Help me understand..."

6. Reference specific CMU-Q entities:
   - Courses: 15-112, 15-122, 15-213, 15-251, 15-150, 67-250, 67-262, 70-122, 73-102, 76-101, 21-127
   - Programs: CS, IS, Business, Biology, various minors
   - Policies: probation, overload, pass/fail, withdrawal, dean's list

7. Mix student perspectives:
   - Freshman: "As an incoming student...", "I'm new here..."
   - Sophomore/Junior: "I'm halfway through...", "Planning my next year..."
   - Senior: "I need to graduate...", "Final semester..."
   - Transfer: "I'm transferring from...", "My credits from..."
   - International: "As an international student...", "Visa requirements..."

Return ONLY a valid JSON array with {batch_target} questions:
[{{"question": "...", "labels": ["{category}"]}}]

IMPORTANT: Generate EXACTLY {batch_target} unique, diverse questions. Quality and diversity matter!"""

        questions = call_gpt(prompt)

        if questions:
            # Add metadata and track starters for diversity
            for q in questions:
                q["labels"] = [category]
                q["source_file"] = f"batch_{category}_{batch_num}"
                # Track first 4 words for diversity across batches
                words = q.get("question", "").split()[:4]
                if words:
                    previous_starters.add(" ".join(words))

            all_questions.extend(questions)
            print(f"    Batch {batch_num + 1}/{num_batches}: +{len(questions)} questions (total: {len(all_questions)})")
        else:
            print(f"    Batch {batch_num + 1}/{num_batches}: FAILED - retrying...")
            # Retry this batch once
            questions = call_gpt(prompt)
            if questions:
                for q in questions:
                    q["labels"] = [category]
                    q["source_file"] = f"batch_{category}_{batch_num}_retry"
                all_questions.extend(questions)
                print(f"    Batch {batch_num + 1}/{num_batches} (retry): +{len(questions)} questions")

    print(f"  ✓ Generated {len(all_questions)}/{n_questions} {category} questions")

    if VERBOSE and len(all_questions) >= 5:
        print(f"    Samples:")
        indices = [0, len(all_questions)//4, len(all_questions)//2, 3*len(all_questions)//4, -1]
        for i in indices:
            if i < len(all_questions):
                print(f"      - \"{all_questions[i].get('question', '')[:70]}...\"")

    return all_questions


def generate_single_agent_data() -> list[dict]:
    """Generate single-agent questions using batch generation for diversity."""
    all_questions = []

    # --- COURSES ---
    print("\n📚 Generating COURSE questions...")
    course_files = load_course_files(DATA_DIR, MAX_COURSE_FILES)
    course_sample = "\n\n".join([f"=== {name} ===\n{content[:1500]}" for name, content in course_files[:15]])
    questions = generate_batch("course", QUESTIONS_PER_CATEGORY["course"], course_sample)
    all_questions.extend(questions)

    # --- PROGRAMS ---
    print("\n🎓 Generating PROGRAM questions...")
    program_files = load_program_files(DATA_DIR)
    program_sample = "\n\n".join([f"=== {name} ===\n{content[:2000]}" for name, content in program_files[:10]])
    questions = generate_batch("program", QUESTIONS_PER_CATEGORY["program"], program_sample)
    all_questions.extend(questions)

    # --- POLICIES ---
    print("\n📋 Generating POLICY questions...")
    policy_files = load_policy_files(DATA_DIR)
    policy_sample = "\n\n".join([f"=== {name} ===\n{content[:2000]}" for name, content in policy_files[:10]])
    questions = generate_batch("policy", QUESTIONS_PER_CATEGORY["policy"], policy_sample)
    all_questions.extend(questions)

    # --- PLANNING ---
    print("\n📅 Generating PLANNING questions...")
    planning_context = """
    Planning questions are about:
    - Semester scheduling and course sequencing
    - Workload balancing across semesters
    - Graduation timeline planning
    - Summer courses vs regular semesters
    - Internship timing and course load
    - Study abroad planning
    - When to take difficult vs easy courses
    """
    questions = generate_batch("planning", QUESTIONS_PER_CATEGORY["planning"], planning_context)
    all_questions.extend(questions)

    return all_questions


def generate_multi_agent_data() -> list[dict]:
    """Generate multi-agent combination questions."""
    all_questions = []

    print("\n🔗 Generating MULTI-AGENT questions...")
    total_expected = sum(c["count"] for c in MULTI_AGENT_COMBOS)
    print(f"  Target: {total_expected} questions across {len(MULTI_AGENT_COMBOS)} label combinations")

    for combo in tqdm(MULTI_AGENT_COMBOS, desc="  Combos"):
        labels_str = ", ".join(combo["labels"])
        scenarios_str = "\n".join(f"- {s}" for s in combo["scenarios"])
        target_count = combo["count"]

        # For larger combos (>50), use batching
        if target_count > BATCH_SIZE:
            combo_questions = generate_multi_agent_batch(combo)
        else:
            prompt = f"""You are generating training data for a student query intent classifier at CMU-Qatar.

Generate EXACTLY {target_count} HIGHLY DIVERSE questions a CMU-Qatar student might ask that require
MULTIPLE agents to answer properly. Specifically, these questions need: [{labels_str}]

What this combination means: {combo['description']}

EXAMPLE scenarios (use as inspiration, but CREATE MANY NEW ONES):
{scenarios_str}

CRITICAL REQUIREMENTS:
1. GO BEYOND the example scenarios - invent new realistic situations students face
2. Questions should NATURALLY require all listed agents (not artificially combined)
3. Mix student types: freshmen, sophomores, juniors, seniors, transfer students, international students
4. Mix emotional tones: stressed ("I'm panicking..."), curious ("I was wondering..."), urgent ("I need to know NOW")
5. Mix complexity: simple multi-agent and complex multi-agent queries
6. Reference specific CMU-Q courses (15-122, 15-213, 15-251, 67-250, 67-262, 70-122, 73-102, etc.)
7. Include real student concerns: internships, study abroad, double majors, minors, graduation timing
8. NO TWO QUESTIONS should start with the same 4 words

VARIETY in question styles:
- Hypothetical: "What if I...", "If I were to..."
- Situational: "I'm currently...", "My situation is..."
- Direct: "Can I...", "Is it possible to..."
- Anxious: "I'm worried that...", "What happens if..."
- Planning: "I want to...", "I'm trying to..."

Return ONLY a valid JSON array with EXACTLY {target_count} questions:
[{{"question": "...", "labels": {json.dumps(combo["labels"])}}}]"""

            combo_questions = call_gpt(prompt)

        if combo_questions:
            for q in combo_questions:
                q["labels"] = combo["labels"]  # enforce correct labels
                q["source_file"] = f"multi_{'_'.join(combo['labels'])}"
            all_questions.extend(combo_questions)
            if VERBOSE:
                labels_str = "+".join(combo["labels"])
                tqdm.write(f"    ✓ [{labels_str}] {len(combo_questions)}/{target_count} questions")
                if combo_questions:
                    tqdm.write(f"      Example: \"{combo_questions[0].get('question', '')[:70]}...\"")
        else:
            tqdm.write(f"    ✗ [{labels_str}] FAILED to generate questions")

    print(f"  ✓ Total multi-agent questions: {len(all_questions)}/{total_expected}")
    return all_questions


def generate_multi_agent_batch(combo: dict) -> list[dict]:
    """Generate multi-agent questions in batches for large counts."""
    all_questions = []
    target_count = combo["count"]
    labels_str = ", ".join(combo["labels"])
    scenarios_str = "\n".join(f"- {s}" for s in combo["scenarios"])

    num_batches = (target_count + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(num_batches):
        remaining = target_count - len(all_questions)
        batch_target = min(BATCH_SIZE, remaining)

        if batch_target <= 0:
            break

        prompt = f"""You are generating training data for a student query intent classifier at CMU-Qatar.

Generate EXACTLY {batch_target} HIGHLY DIVERSE questions a CMU-Qatar student might ask that require
MULTIPLE agents to answer properly. Specifically, these questions need: [{labels_str}]

What this combination means: {combo['description']}

EXAMPLE scenarios (use as inspiration, but CREATE MANY NEW ONES):
{scenarios_str}

This is batch {batch_num + 1} of {num_batches} - make sure questions are unique!

CRITICAL REQUIREMENTS:
1. GO BEYOND the example scenarios - invent new realistic situations
2. Questions should NATURALLY require all listed agents
3. Mix student types, emotional tones, and complexity levels
4. Reference specific CMU-Q courses (15-122, 15-213, 15-251, 67-250, etc.)
5. NO TWO QUESTIONS should start with the same 4 words

Return ONLY a valid JSON array with EXACTLY {batch_target} questions:
[{{"question": "...", "labels": {json.dumps(combo["labels"])}}}]"""

        questions = call_gpt(prompt)
        if questions:
            all_questions.extend(questions)

    return all_questions


def main():
    print("=" * 60)
    print("AdvisingBot Fine-Tuning Data Generator")
    print("=" * 60)
    
    # Check data directory
    if not DATA_DIR.exists():
        print(f"\n⚠️  Data directory not found at {DATA_DIR}")
        print("Please run this script from the AdvisingBot project root,")
        print("or adjust PROJECT_ROOT in the configuration section.")
        return
    
    # Generate all data
    single_data = generate_single_agent_data()
    multi_data = generate_multi_agent_data()
    
    all_data = single_data + multi_data
    
    # Save raw data
    output_path = OUTPUT_DIR / "raw_questions.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    # Print statistics
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    print(f"Total questions: {len(all_data)}")
    print(f"Single-agent:    {len(single_data)}")
    print(f"Multi-agent:     {len(multi_data)}")
    print(f"\nSaved to: {output_path}")
    
    # Label distribution
    from collections import Counter
    label_combos = Counter(tuple(sorted(q["labels"])) for q in all_data)
    print("\nLabel distribution:")
    for combo, count in sorted(label_combos.items(), key=lambda x: -x[1]):
        print(f"  {', '.join(combo):40s} → {count}")


if __name__ == "__main__":
    main()
