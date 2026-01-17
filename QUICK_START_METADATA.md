# Quick Start: Document Metadata Enhancements

**TL;DR**: Your agents can now see what document each piece of information comes from! This helps them cite sources and understand context better.

---

## 🚀 Quick Start (3 Steps)

### Step 1: Rebuild Indexes with Metadata

Run this command to add metadata to all your vector databases:

```bash
python rebuild_indexes_with_metadata.py
```

**What this does**:
- Adds [DOCUMENT CONTEXT] headers to all chunks
- Includes file name, type, program, courses mentioned, and summary
- Takes ~5-10 minutes

**Output**:
```
================================================================================
🔄 REBUILD VECTOR DATABASES WITH METADATA
================================================================================

⚠️  WARNING: This will DELETE and REBUILD ALL domain indexes:
   - programs
   - courses
   - policies

Do you want to proceed? (yes/no): yes

================================================================================
Starting rebuild...
================================================================================

📦 Analyzing domain: PROGRAMS
--------------------------------------------------------------------------------
   Loaded 12 JSON files with metadata
   Loaded 15 markdown files with metadata
✅ Domain 'programs' index built successfully

📦 Analyzing domain: COURSES
--------------------------------------------------------------------------------
   Loaded 2471 JSON files with metadata
✅ Domain 'courses' index built successfully

📦 Analyzing domain: POLICIES
--------------------------------------------------------------------------------
   Loaded 35 markdown files with metadata
✅ Domain 'policies' index built successfully

================================================================================
✅ Successfully rebuilt ALL domain indexes with metadata!
================================================================================
```

### Step 2: Test the System

```bash
python chat.py
```

**Try these queries**:

1. "What are the IS core requirements?"
   - Look for document source citations in response

2. "Tell me about 15-213"
   - Agent should know it's from course documentation

3. "What's the registration policy?"
   - Should cite specific policy documents

### Step 3: Verify Improvements

**What to Look For**:

✓ Agents mention document sources:
  - "According to IS_Requirements.json..."
  - "The registration policy document states..."
  
✓ Better context understanding:
  - Distinguishes between program requirements vs policies
  - Knows which program a document relates to
  
✓ More accurate answers:
  - Retrieves more relevant information
  - Less confusion between similar topics

---

## 📊 What Changed?

### Before

**Chunk Example**:
```
{
    "Name": "Technical Core - Mathematics",
    "Constraints": "Satisfy all of the courses requirements",
    "Allowed_Courses": "21-112 or 21-120 or 21-127"
}
```

❌ Agent doesn't know:
- What document this is from
- What type of information it is
- Which program it relates to

### After

**Chunk Example**:
```
[DOCUMENT CONTEXT]
File: IS_Requirements.json
Type: program_requirements
Program: Information Systems
Mentions courses: 15-110, 15-112, 15-121, 21-112, 21-120, 67-100, ...
Summary: Contains 20 requirements | Examples: Technical Core - Mathematics, ...

[DOCUMENT CONTENT]
{
    "Name": "Technical Core - Mathematics",
    "Constraints": "Satisfy all of the courses requirements",
    "Allowed_Courses": "21-112 or 21-120 or 21-127"
}
```

✅ Agent knows:
- Source: IS_Requirements.json
- Type: program_requirements
- Program: Information Systems
- Related courses

---

## 🎯 Key Benefits

### 1. Source Citations 📄
**Before**: "You need to take 15-112 and 67-100"  
**After**: "According to IS_Requirements.json, the IS Core requires 15-112 and 67-100"

### 2. Better Context 🧠
**Before**: Retrieves mixed information without knowing document types  
**After**: Knows if it's reading requirements, policies, or course descriptions

### 3. Improved Accuracy ⚡
**Before**: May confuse requirements from different programs  
**After**: Metadata shows which program each requirement belongs to

### 4. User Trust 🤝
**Before**: Users wonder "Where did this info come from?"  
**After**: Clear source attribution builds confidence

---

## 📁 What Was Changed?

### Modified Files

1. **`rag_engine_improved.py`**
   - Added metadata extraction functions
   - Enhanced document loading
   - Prepends [DOCUMENT CONTEXT] to chunks

2. **`agents/programs_agent.py`**
   - Updated prompt to use metadata
   - Instructs agent to cite sources

3. **`agents/policy_agent.py`**
   - Updated prompts for metadata usage
   - Emphasizes document citations

4. **`agents/courses_agent.py`**
   - Leverages metadata for course identification
   - Uses metadata to understand context

### New Files

5. **`generate_document_metadata.py`**
   - Analyzes documents and generates metadata report

6. **`rebuild_indexes_with_metadata.py`**
   - User-friendly rebuild script

7. **`METADATA_ENHANCEMENTS.md`**
   - Complete technical documentation

8. **`QUICK_START_METADATA.md`**
   - This quick start guide

---

## 🔧 Advanced Usage

### Rebuild Specific Domain Only

```bash
# Only rebuild programs
python rebuild_indexes_with_metadata.py --domain programs

# Only rebuild courses
python rebuild_indexes_with_metadata.py --domain courses

# Only rebuild policies
python rebuild_indexes_with_metadata.py --domain policies
```

### Skip Confirmation Prompt

```bash
python rebuild_indexes_with_metadata.py --force
```

### Analyze Documents Without Rebuilding

```bash
python generate_document_metadata.py
```

This generates `document_metadata_analysis.json` with metadata for all documents.

---

## ❓ FAQ

### Q: Do I need to rebuild every time I add a document?

**A**: Only if you want the new document to have metadata. Otherwise, it will work but without the enhanced context.

### Q: Will this affect existing queries?

**A**: No! Existing queries will work the same, but with better answers due to metadata.

### Q: How much time does rebuilding take?

**A**: 
- **Programs domain**: ~1-2 minutes
- **Courses domain**: ~3-5 minutes (2500+ files)
- **Policies domain**: ~1 minute
- **Total**: ~5-10 minutes

### Q: Can I see the metadata in action?

**A**: Yes! Add debug print in agent code:
```python
context = self.retrieve_context(query)
print("RETRIEVED CONTEXT:", context)
```

You'll see the [DOCUMENT CONTEXT] headers.

### Q: What if rebuild fails?

**A**: Common issues and solutions:

1. **SSL/Connection Error**: Already handled with `verify=False` in code
2. **Timeout Error**: Already increased to 180 seconds
3. **List metadata error**: Already fixed - courses stored as comma-separated strings
4. **Missing API key**: Check `.env` file has `OPENAI_API_KEY=your_key`
5. **No documents**: Ensure `data/` folder exists with JSON/MD files

---

## 🎓 Examples

### Example 1: Requirements Query

**Query**: "What math courses do IS students need?"

**Agent Response (with metadata)**:
```
According to IS_Requirements.json, Information Systems students must 
complete one of the following math courses for the Technical Core - Mathematics 
requirement:

- 21-112 (Calculus I)
- 21-120 (Differential and Integral Calculus)
- 21-127 (Concepts of Mathematics)
- 21-240 (Matrix Algebra with Applications)
- 80-210 (Logic and Mathematical Inquiry)

This is documented in the IS program requirements under "Technical Core - Mathematics".
```

Note: Agent cites **IS_Requirements.json** and **requirement name**!

### Example 2: Policy Query

**Query**: "How do I add a course after the deadline?"

**Agent Response (with metadata)**:
```
Based on the Course Adds, Drops, and Withdrawals policy document, late course 
additions require:

1. Instructor permission
2. Academic advisor approval
3. Submission through the late add/drop form

Deadlines are outlined in the Academic Calendar (CMUQ-2025-2026-Academic-Calendar). 
Late adds may not be possible after the second week of classes.
```

Note: Agent cites **specific policy documents**!

### Example 3: Course Query

**Query**: "What are the prerequisites for 15-213?"

**Agent Response (with metadata)**:
```
According to the course documentation for 15-213 (Introduction to Computer Systems):

Prerequisites: 15-112 or 15-122

This course builds on programming fundamentals from either:
- 15-112: Fundamentals of Programming and Computer Science, OR
- 15-122: Principles of Imperative Computation

You must complete one of these courses before taking 15-213.
```

Note: Agent references **course documentation** and provides context!

---

## ✅ Success Checklist

After implementing metadata enhancements, verify:

- [ ] Ran `rebuild_indexes_with_metadata.py` successfully
- [ ] Tested with sample queries in `chat.py`
- [ ] Agents mention document sources in responses
- [ ] Retrieved chunks include [DOCUMENT CONTEXT] headers
- [ ] No errors or degraded performance
- [ ] Response quality improved (subjective check)

---

## 📚 More Information

- **Complete Technical Guide**: See `METADATA_ENHANCEMENTS.md`
- **Code Changes**: Review `rag_engine_improved.py`
- **Agent Updates**: Check agent files in `agents/` folder

---

## 🎉 You're All Set!

Your agents now have enhanced understanding of their knowledge base. They can:

✓ Cite specific documents  
✓ Understand document types  
✓ Identify program associations  
✓ Provide more accurate answers  
✓ Build user trust with source attribution

**Enjoy your improved advising bot!** 🚀

---

**Created**: January 14, 2026  
**Status**: ✅ Ready to Use
