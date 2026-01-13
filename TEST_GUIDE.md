# 测试脚本使用指南 (Test Script Guide)

## 📋 概述 (Overview)

`test.py` 是一个自动化测试脚本，用于批量测试 AdvisingBot 系统。

### 功能特点

- ✅ 从 `in.txt` 读取测试问题（每行一个问题）
- ✅ 自动处理每个问题通过完整的多Agent系统
- ✅ 支持交互式澄清（在需要时可以在 CMD 中提供输入）
- ✅ 生成两个输出文件：
  - `out.txt`: 问题和最终答案（简洁版）
  - `out_raw.txt`: 问题和完整处理日志（详细版）
- ✅ 不修改原始 MAS 代码

## 🚀 使用方法 (Usage)

### 1. 准备测试问题

在 `in.txt` 文件中写入测试问题，每行一个：

```txt
How do I know which courses to take each semester?
Can I take more than the recommended number of courses in a semester?
What happens if I register for a course but don't meet the prerequisites?
```

### 2. 运行测试脚本

```bash
python test.py
```

### 3. 提供澄清（如果需要）

如果系统需要澄清信息（例如专业、学期等），你会在终端看到提示：

```
⚠️  CLARIFICATION NEEDED
================================================================================

The system needs additional information to provide an accurate answer.

Missing Information:
- major

Questions for Clarification:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q1: What is your major or program? (Please spell out full name)
    Why: Requirements differ significantly between programs
    Options: Computer Science (CS), Information Systems (IS), Biological Sciences (Bio), Business Administration (BA)
    Note: Please use full major name to avoid confusion (e.g., 'Biological Sciences' not 'BS')
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What is your major or program? (Please spell out full name):
```

**你需要在终端输入答案：**

```
What is your major or program? (Please spell out full name): Computer Science
```

系统会继续处理并给出答案。

### 4. 查看结果

测试完成后，查看生成的文件：

#### `out.txt` - 简洁版（仅问题和答案）

```
================================================================================
ADVISING BOT TEST RESULTS - FINAL ANSWERS ONLY
================================================================================

Question 1:
How do I know which courses to take each semester?

Answer:
Use Stellic to track your degree progress and refer to the IS Sample Plan 
for recommended course sequencing. Your advisor can also help you plan based 
on your interests and graduation goals.

--------------------------------------------------------------------------------

Question 2:
Can I take more than the recommended number of courses in a semester?

Answer:
Yes, but overloading (taking more than 54 units) requires advisor approval...
```

#### `out_raw.txt` - 详细版（完整处理日志）

```
================================================================================
QUESTION 1
================================================================================
How do I know which courses to take each semester?

================================================================================
💬 You: How do I know which courses to take each semester?
================================================================================

================================================================================
🎯 STEP 1: Intent Classification
================================================================================

   Query: "How do I know which courses to take each semester?"
   
   Analyzing query to determine which agents are needed...
   
   ✅ Intent: general_advising
   📋 Required Agents: ['programs_requirements', 'policy_compliance']
   🎯 Confidence: 0.95
   💭 Reasoning: Student asking about general course planning process...

[... 完整的处理日志 ...]
```

## 📊 输出说明 (Output Explanation)

### out.txt

- **用途**: 快速查看所有问题的答案
- **格式**: 问题 + 答案
- **适合**: 检查答案质量、用于评估

### out_raw.txt

- **用途**: 深入分析系统处理过程
- **格式**: 完整的处理日志（包括意图分类、Agent执行、协商等）
- **适合**: 调试、分析系统行为、研究

## ⚠️ 注意事项 (Important Notes)

### 1. 澄清请求

- 如果问题需要专业信息但未提供，系统会要求澄清
- 你必须在终端输入答案才能继续
- 澄清信息会在同一会话中保留（下一个问题会记住）

**建议：**在问题中直接包含必要信息以避免澄清：

```txt
# 不好 - 会触发澄清
Do I need to take 15-213?

# 好 - 不会触发澄清
I'm a CS freshman. Do I need to take 15-213?
```

### 2. 对话上下文

- 测试脚本维护对话历史
- 后续问题可以引用之前的信息
- 每次运行测试会重置历史

### 3. 性能

- 每个问题需要调用 LLM API（可能需要几秒钟）
- 如果有很多问题，测试可能需要较长时间
- 可以使用 Ctrl+C 中断测试

## 🔧 高级用法 (Advanced Usage)

### 跳过特定问题

在 `in.txt` 中用 `#` 注释掉不想测试的问题：

```txt
How do I know which courses to take each semester?
# Can I take more than the recommended number of courses?  (跳过这个)
What happens if I register for a course but don't meet prerequisites?
```

### 测试对话能力

在 `in.txt` 中使用连续的相关问题测试对话记忆：

```txt
I'm a CS freshman planning my courses
What courses should I take in my first semester?
What about my second semester?
Do I need to take 15-213?
```

第 2-4 个问题会利用第 1 个问题中提供的上下文（CS freshman）。

## 🐛 故障排除 (Troubleshooting)

### 问题：脚本卡住不动

**原因**: 可能在等待澄清输入

**解决**: 检查终端是否有提示，输入所需信息

### 问题：某些问题没有答案

**原因**: 
- 可能需要澄清但未提供
- 系统出错

**解决**: 查看 `out_raw.txt` 了解详细错误信息

### 问题：答案质量不佳

**原因**: 
- 问题表述不清
- 缺少必要上下文
- 数据库中没有相关信息

**解决**: 
1. 在问题中包含更多上下文
2. 检查 `out_raw.txt` 查看系统推理过程
3. 确认 RAG 数据库包含相关信息

## 📝 示例测试集 (Example Test Sets)

### 通用政策问题（无需澄清）

```txt
How do I enroll in a course?
What happens if I drop a course?
Can I take graduate courses as an undergraduate?
What is the minimum QPA required?
How do I declare a minor?
```

### 专业特定问题（需要提供专业）

```txt
I'm a CS junior. What courses should I take next semester?
I'm an IS sophomore. Can I graduate on time?
As a Bio student, do I need to take 15-122?
```

### 对话测试（测试上下文记忆）

```txt
I'm a CS freshman
What courses do I need to take?
What about prerequisites for these courses?
Can I take them all in one semester?
```

## ✅ 最佳实践 (Best Practices)

1. **明确指定上下文**: 在问题中包含专业、学期等信息
2. **分类组织问题**: 将相似问题放在一起方便分析
3. **先测试小集合**: 先用几个问题测试，确认工作正常
4. **保存测试集**: 为不同测试场景创建不同的 `in.txt` 文件
5. **对比结果**: 定期运行相同测试集，对比答案质量变化

## 🎯 与原始 chat.py 的区别

| 特性 | test.py | chat.py |
|------|---------|---------|
| 输入方式 | 批量读取文件 | 交互式输入 |
| 输出保存 | 自动保存到文件 | 仅终端显示 |
| 对话历史 | 跨问题保留 | 跨轮次保留 |
| 澄清处理 | 支持（终端输入） | 支持（终端输入） |
| 修改原系统 | 否 | N/A |

---

**创建日期**: January 13, 2026  
**用途**: 自动化测试 AdvisingBot  
**维护者**: 与 chat.py 保持同步
