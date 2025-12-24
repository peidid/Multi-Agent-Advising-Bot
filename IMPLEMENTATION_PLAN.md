# Implementation Plan: Multi-Agent Academic Advising Chatbot for CMU-Qatar
## ACL 2026 Demo Track

---

## Table of Contents
1. [Overview & Prerequisites](#overview--prerequisites)
2. [Phase 1: Foundation & Learning (Weeks 1-4)](#phase-1-foundation--learning-weeks-1-4)
3. [Phase 2: Core Infrastructure (Weeks 5-8)](#phase-2-core-infrastructure-weeks-5-8)
4. [Phase 3: Agent Development (Weeks 9-14)](#phase-3-agent-development-weeks-9-14)
5. [Phase 4: Coordination & Negotiation (Weeks 15-18)](#phase-4-coordination--negotiation-weeks-15-18)
6. [Phase 5: UI & Interaction (Weeks 19-22)](#phase-5-ui--interaction-weeks-19-22)
7. [Phase 6: Evaluation & Refinement (Weeks 23-26)](#phase-6-evaluation--refinement-weeks-23-26)
8. [Phase 7: Demo Preparation (Weeks 27-30)](#phase-7-demo-preparation-weeks-27-30)
9. [Resources & Learning Path](#resources--learning-path)

---

## Overview & Prerequisites

### Project Goal
Build a dynamic multi-agent academic advising chatbot that:
- Routes queries to specialized agents via a coordinator
- Uses structured blackboard/shared state for agent communication
- Implements negotiation protocols for conflict resolution
- Provides interactive UI for user agency in decision-making
- Personalizes advice using student history and academic records

### Key Research Contributions
1. **Dynamic Multi-Agent Orchestration**: Hub-and-spoke topology with coordinator
2. **Structured Blackboard**: Typed schema for agent communication
3. **Negotiation Mechanisms**: Proposal + critique protocol
4. **Interactive Conflict Resolution**: User-facing trade-offs and follow-up questions
5. **History-Aware Personalization**: Long-term memory integration

### Technology Stack
- **Framework**: LangGraph (for multi-agent orchestration)
- **LLM**: OpenAI GPT-4 or Claude (via API)
- **Vector DB**: ChromaDB or Pinecone (for RAG)
- **Backend**: Python (FastAPI or Flask)
- **Frontend**: React or Streamlit (for demo UI)
- **Database**: PostgreSQL or SQLite (for structured data)
- **APIs**: Stellic, SIO (for student data)

---

## Phase 1: Foundation & Learning (Weeks 1-4)

### Week 1: Python & LLM Basics
**Goals**: Set up development environment and learn fundamentals

**Tasks**:
1. **Python Setup**
   - Install Python 3.10+
   - Set up virtual environment
   - Learn basic Python: classes, functions, async/await
   - Practice with JSON, dictionaries, data structures

2. **LLM API Basics**
   - Sign up for OpenAI API (or Anthropic Claude)
   - Learn to make API calls
   - Practice prompt engineering
   - Build a simple chatbot (single-turn)

**Deliverables**:
- Working Python environment
- Simple script that calls LLM API
- Basic understanding of prompts and responses

**Learning Resources**:
- Python tutorial: https://docs.python.org/3/tutorial/
- OpenAI API docs: https://platform.openai.com/docs
- LangChain quickstart: https://python.langchain.com/docs/get_started/introduction

### Week 2: RAG (Retrieval-Augmented Generation)
**Goals**: Understand and implement basic RAG

**Tasks**:
1. **Vector Databases**
   - Install ChromaDB or Pinecone
   - Learn embeddings (OpenAI embeddings API)
   - Create a simple vector store
   - Practice similarity search

2. **Basic RAG Pipeline**
   - Load documents (start with a few markdown files from `info/`)
   - Chunk documents
   - Create embeddings and store in vector DB
   - Build retrieval function
   - Combine retrieval + LLM generation

**Deliverables**:
- Working RAG system that answers questions from CMU-Q documents
- Understanding of embeddings and similarity search

**Learning Resources**:
- LangChain RAG tutorial: https://python.langchain.com/docs/use_cases/question_answering/
- ChromaDB docs: https://docs.trychroma.com/

### Week 3: LangGraph Introduction
**Goals**: Learn LangGraph for multi-agent systems

**Tasks**:
1. **LangGraph Basics**
   - Install LangGraph
   - Understand state graphs
   - Build a simple 2-agent system
   - Learn state management

2. **Simple Multi-Agent Example**
   - Create two agents: one for course info, one for policy
   - Implement basic routing logic
   - Test agent communication

**Deliverables**:
- Working LangGraph state graph
- Simple 2-agent system with routing

**Learning Resources**:
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- LangGraph tutorial: https://langchain-ai.github.io/langgraph/tutorials/

### Week 4: Data Preparation
**Goals**: Organize and structure knowledge base

**Tasks**:
1. **Document Organization**
   - Review all documents in `info/` directory
   - Categorize by domain (programs, courses, policies, etc.)
   - Clean and structure markdown files
   - Create metadata for each document

2. **Knowledge Base Setup**
   - Create separate vector stores for each domain:
     - Programs & Requirements
     - Courses & Scheduling
     - Policies & Compliance
     - Opportunities (career/research/events)
   - Test retrieval from each store

**Deliverables**:
- Organized knowledge base
- Multiple vector stores ready for agents
- Document categorization complete

---

## Phase 2: Core Infrastructure (Weeks 5-8)

### Week 5: Structured Blackboard Design
**Goals**: Design and implement typed shared state schema

**Tasks**:
1. **Schema Design**
   - Define Pydantic models for blackboard:
     ```python
     class StudentProfile(BaseModel):
         major: List[str]
         minor: List[str]
         gpa: float
         completed_courses: List[str]
         flags: List[str]  # e.g., "probation", "overload"
     
     class UserGoal(BaseModel):
         description: str
         type: str  # "add_minor", "plan_semester", etc.
     
     class Constraint(BaseModel):
         source: str  # "policy", "student", "finance"
         description: str
         hard: bool  # hard vs soft constraint
     
     class PlanOption(BaseModel):
         semesters: List[Dict]
         risks: List[str]
         policy_citations: List[str]
     
     class BlackboardState(BaseModel):
         student_profile: Optional[StudentProfile]
         user_goal: Optional[UserGoal]
         constraints: List[Constraint]
         plan_options: List[PlanOption]
         risks: List[str]
         open_questions: List[str]
         agent_outputs: Dict[str, Any]
     ```

2. **Blackboard Implementation**
   - Create BlackboardState class
   - Implement read/write methods
   - Add validation logic
   - Test state updates

**Deliverables**:
- Typed blackboard schema
- Working state management system

### Week 6: Coordinator/Orchestrator Agent
**Goals**: Build the main coordinator that routes queries

**Tasks**:
1. **Intent Classification**
   - Create intent classifier using LLM
   - Define intent categories:
     - "program_requirements"
     - "course_scheduling"
     - "policy_check"
     - "opportunities"
     - "personalized_advice"
   - Test classification accuracy

2. **Routing Logic**
   - Implement agent selection logic
   - Create LangGraph nodes for each agent
   - Build coordinator node that decides next agent
   - Implement access control (which agents can read/write what)

3. **Basic Workflow**
   - Create simple LangGraph workflow:
     ```
     Start → Coordinator → Agent1 → Coordinator → Agent2 → Coordinator → End
     ```
   - Test with sample queries

**Deliverables**:
- Working coordinator agent
- Basic routing system
- LangGraph workflow skeleton

**Learning Resources**:
- LangGraph multi-agent tutorial: https://langchain-ai.github.io/langgraph/tutorials/multi-agent/

### Week 7: Student Profile & Memory Agent
**Goals**: Implement personalization agent

**Tasks**:
1. **Data Access**
   - Research Stellic/SIO API access (or use mock data initially)
   - Create student profile data structure
   - Implement profile retrieval function

2. **Memory Agent**
   - Build agent that:
     - Retrieves student academic history
     - Summarizes previous conversations
     - Creates structured profile for blackboard
   - Test profile generation

3. **Integration**
   - Connect memory agent to coordinator
   - Test personalization in workflow

**Deliverables**:
- Student Profile agent
- Profile retrieval system
- Integration with coordinator

### Week 8: Database & API Setup
**Goals**: Set up backend infrastructure

**Tasks**:
1. **Database Setup**
   - Install PostgreSQL or SQLite
   - Design schema for:
     - Student profiles
     - Conversation history
     - Agent interactions (for debugging)
   - Create database models

2. **API Framework**
   - Set up FastAPI or Flask
   - Create basic endpoints:
     - POST /chat (main chat endpoint)
     - GET /student/{id}/profile
     - GET /conversation/{id}/history
   - Test API locally

**Deliverables**:
- Database schema
- Basic API endpoints
- Backend infrastructure ready

---

## Phase 3: Agent Development (Weeks 9-14)

### Week 9-10: Programs & Requirements Agent
**Goals**: Build agent for major/minor requirements

**Tasks**:
1. **Knowledge Base**
   - Create RAG index for:
     - Major requirements (Biological Science, Business, CS, IS)
     - Minor requirements
     - Program policies
   - Test retrieval accuracy

2. **Agent Implementation**
   - Build agent that:
     - Answers requirement questions
     - Validates proposed plans against requirements
     - Checks progress toward degree
   - Implement as LangGraph node

3. **Testing**
   - Test with sample queries:
     - "What are the requirements for CS major?"
     - "Can I add a CS minor as an IS student?"
     - "Am I on track to graduate?"

**Deliverables**:
- Programs & Requirements Agent
- Working RAG index
- Test cases passing

### Week 11: Course & Scheduling Agent
**Goals**: Build agent for course information and scheduling

**Tasks**:
1. **Course Data**
   - Parse course JSON files from `info/Academic & Studies/Courses/`
   - Create course database/index
   - Extract: prerequisites, credits, descriptions

2. **Scheduling Logic**
   - Build agent that:
     - Finds course offerings (semester, instructor)
     - Checks prerequisites
     - Identifies schedule conflicts
     - Suggests course sequences
   - Integrate with course schedule APIs if available

3. **Integration**
   - Connect to coordinator
   - Test scheduling queries

**Deliverables**:
- Course & Scheduling Agent
- Course database
- Scheduling logic working

### Week 12: Policy & Compliance Agent
**Goals**: Build agent for university policies

**Tasks**:
1. **Policy Knowledge Base**
   - Create RAG index for:
     - Registration policies
     - Academic integrity
     - Exam & grading policies
     - Financial policies
   - Structure policy documents

2. **Compliance Checking**
   - Build agent that:
     - Checks plan compliance with policies
     - Flags violations (overload, probation, etc.)
     - Provides policy citations
   - Implement validation logic

3. **Testing**
   - Test with scenarios:
     - Overload detection
     - Probation rules
     - Course repeat policies

**Deliverables**:
- Policy & Compliance Agent
- Policy knowledge base
- Compliance checking working

### Week 13: Opportunities Agent
**Goals**: Build agent for career/research/events

**Tasks**:
1. **Knowledge Base**
   - Create RAG index for:
     - Career development resources
     - Research opportunities (SURA, QSIURP, etc.)
     - Events and global trips
     - On-campus jobs

2. **Agent Implementation**
   - Build agent that:
     - Matches opportunities to student profile
     - Answers questions about opportunities
     - Provides registration information
   - Consider web search integration (Handshake, LinkedIn)

3. **Integration**
   - Connect to coordinator
   - Test opportunity queries

**Deliverables**:
- Opportunities Agent
- Opportunity knowledge base
- Matching logic working

### Week 14: People/Routing Agent (Optional)
**Goals**: Build agent for routing to human advisors

**Tasks**:
1. **Faculty/Staff Database**
   - Create index of:
     - Faculty members
     - Academic advisors
     - Department contacts
   - Include: roles, expertise, contact info

2. **Routing Logic**
   - Build agent that:
     - Identifies when human help is needed
     - Recommends appropriate person/office
     - Provides contact information

**Deliverables**:
- People/Routing Agent (if implemented)
- Faculty database

---

## Phase 4: Coordination & Negotiation (Weeks 15-18)

### Week 15: Enhanced Coordinator
**Goals**: Improve coordinator with better planning

**Tasks**:
1. **Workflow Planning**
   - Implement dynamic workflow planning:
     - Coordinator analyzes query
     - Plans sequence of agents needed
     - Adjusts plan based on intermediate results
   - Test with complex queries

2. **Access Control**
   - Implement fine-grained access control:
     - Which agents can read which blackboard fields
     - Which agents can write to which fields
   - Prevent unauthorized access

**Deliverables**:
- Enhanced coordinator
- Dynamic planning working
- Access control implemented

### Week 16: Negotiation Protocol - Proposal + Critique
**Goals**: Implement negotiation mechanism

**Tasks**:
1. **Proposal Mechanism**
   - Programs Agent proposes plan
   - Plan written to blackboard with:
     - Justification
     - Confidence score
     - Policy citations

2. **Critique Mechanism**
   - Policy Agent critiques proposal:
     - Flags violations
     - Suggests edits
     - Provides alternative options
   - Write critique to blackboard

3. **Synthesis**
   - Coordinator synthesizes:
     - Revised plan
     - Conflict resolution
     - Trade-offs identified
   - Implement iteration loop (max 2-3 rounds)

**Deliverables**:
- Proposal + Critique protocol
- Negotiation mechanism working
- Test with conflicting scenarios

### Week 17: Conflict Detection & Resolution
**Goals**: Implement conflict detection logic

**Tasks**:
1. **Conflict Types**
   - Define canonical conflict types:
     - Hard policy violation (impossible)
     - High-risk plan (possible but risky)
     - Trade-off conflicts (multiple valid options)
   - Create conflict detection logic

2. **Conflict Representation**
   - Structure conflicts on blackboard:
     - Conflict type
     - Affected agents
     - Options/alternatives
     - Recommendations

3. **Resolution Strategies**
   - Implement resolution logic:
     - Automatic resolution (when possible)
     - User intervention (when needed)
   - Test conflict scenarios

**Deliverables**:
- Conflict detection system
- Conflict types defined
- Resolution logic working

### Week 18: Integration & Testing
**Goals**: Integrate all components and test end-to-end

**Tasks**:
1. **End-to-End Testing**
   - Test complex scenarios:
     - "I want to add CS minor as IS student"
     - "Can I study abroad and still graduate on time?"
     - "What courses should I take next semester?"
   - Debug issues

2. **Performance Optimization**
   - Optimize token usage
   - Reduce latency
   - Improve caching

**Deliverables**:
- Fully integrated system
- End-to-end tests passing
- Performance benchmarks

---

## Phase 5: UI & Interaction (Weeks 19-22)

### Week 19: Basic Chat Interface
**Goals**: Build simple chat UI

**Tasks**:
1. **Frontend Setup**
   - Choose: Streamlit (easier) or React (more flexible)
   - Set up basic chat interface
   - Connect to backend API
   - Display messages and responses

2. **Basic Features**
   - Chat history
   - User input
   - Response display
   - Loading indicators

**Deliverables**:
- Working chat interface
- Basic UI functional

**Learning Resources**:
- Streamlit: https://docs.streamlit.io/
- React: https://react.dev/learn

### Week 20: Interactive Conflict Widgets
**Goals**: Build UI for conflict resolution

**Tasks**:
1. **Conflict UI Components**
   - Build widgets for:
     - Plan comparison (Plan A vs Plan B)
     - Risk indicators
     - Policy citations
     - Trade-off visualization

2. **User Interaction**
   - Implement:
     - User selection between options
     - Follow-up question prompts
     - Clarification requests
   - Test user flow

**Deliverables**:
- Conflict resolution UI
- Interactive widgets working
- User testing complete

### Week 21: Visualization & Transparency
**Goals**: Show system reasoning to users

**Tasks**:
1. **Agent Activity Display**
   - Show which agents are active
   - Display agent outputs (optional debug mode)
   - Show blackboard state (for transparency)

2. **Plan Visualization**
   - Visualize semester-by-semester plans
   - Show progress toward degree
   - Display constraints and risks

**Deliverables**:
- Visualization components
- Transparency features
- User-friendly displays

### Week 22: UI Polish & UX
**Goals**: Improve user experience

**Tasks**:
1. **UX Improvements**
   - Improve styling
   - Add animations
   - Better error handling
   - Responsive design

2. **Accessibility**
   - Ensure accessibility
   - Test with users
   - Gather feedback

**Deliverables**:
- Polished UI
- Good UX
- User feedback incorporated

---

## Phase 6: Evaluation & Refinement (Weeks 23-26)

### Week 23: Evaluation Framework
**Goals**: Set up evaluation system

**Tasks**:
1. **Test Scenarios**
   - Create test scenarios:
     - Simple queries (single agent)
     - Complex queries (multiple agents)
     - Conflict scenarios
     - Edge cases
   - Create gold-standard answers

2. **Metrics**
   - Define metrics:
     - Correctness (vs policies)
     - Safety (no bad advice)
     - User satisfaction
     - Token cost
     - Latency
   - Implement evaluation scripts

**Deliverables**:
- Test scenario suite
- Evaluation framework
- Metrics defined

### Week 24: Ablation Studies
**Goals**: Compare different system configurations

**Tasks**:
1. **Baseline Comparisons**
   - Implement baselines:
     - Single-agent RAG
     - Static multi-agent (no negotiation)
     - Full system (with negotiation)
   - Run comparisons

2. **Ablation Studies**
   - Test:
     - Different numbers of agents
     - With/without memory
     - With/without negotiation
     - With/without conflict UI
   - Analyze results

**Deliverables**:
- Ablation study results
- Performance comparisons
- Analysis complete

### Week 25: Human Evaluation
**Goals**: Get feedback from real users

**Tasks**:
1. **User Study Design**
   - Design user study:
     - Recruit CMU-Q students/advisors
     - Create evaluation tasks
     - Prepare questionnaires
   - Get IRB approval if needed

2. **Conduct Study**
   - Run user study
   - Collect feedback
   - Analyze results

**Deliverables**:
- User study complete
- Feedback collected
- Results analyzed

### Week 26: Refinement Based on Feedback
**Goals**: Improve system based on evaluation

**Tasks**:
1. **Fix Issues**
   - Address bugs found
   - Improve accuracy
   - Fix UX issues

2. **Optimization**
   - Further optimize performance
   - Reduce costs
   - Improve response quality

**Deliverables**:
- Refined system
- Issues fixed
- Performance improved

---

## Phase 7: Demo Preparation (Weeks 27-30)

### Week 27: Demo Scenarios
**Goals**: Prepare compelling demo scenarios

**Tasks**:
1. **Scenario Selection**
   - Choose 3-5 best scenarios:
     - Showcase multi-agent coordination
     - Demonstrate negotiation
     - Highlight conflict resolution
     - Show personalization
   - Prepare scripts

2. **Demo Data**
   - Create demo student profiles
   - Prepare sample conversations
   - Test demo flow

**Deliverables**:
- Demo scenarios ready
- Demo data prepared
- Scripts written

### Week 28: Documentation
**Goals**: Write documentation

**Tasks**:
1. **Technical Documentation**
   - System architecture
   - API documentation
   - Agent descriptions
   - Setup instructions

2. **User Documentation**
   - User guide
   - Demo instructions
   - FAQ

**Deliverables**:
- Complete documentation
- User guide ready

### Week 29: Video & Presentation
**Goals**: Create demo video and presentation

**Tasks**:
1. **Demo Video**
   - Record demo scenarios
   - Edit video (5-10 minutes)
   - Add narration

2. **Presentation**
   - Create slides
   - Highlight research contributions
   - Prepare for ACL demo track

**Deliverables**:
- Demo video
- Presentation slides
- Ready for submission

### Week 30: Final Testing & Submission
**Goals**: Final checks and submission

**Tasks**:
1. **Final Testing**
   - Comprehensive testing
   - Fix any last-minute issues
   - Performance check

2. **Submission**
   - Prepare submission package:
     - Code repository
     - Documentation
     - Demo video
     - Paper (if required)
   - Submit to ACL 2026

**Deliverables**:
- System ready
- Submission complete
- Ready for review

---

## Resources & Learning Path

### Essential Learning Resources

1. **Python**
   - Official Python Tutorial: https://docs.python.org/3/tutorial/
   - Real Python: https://realpython.com/

2. **LLMs & APIs**
   - OpenAI API Docs: https://platform.openai.com/docs
   - Anthropic Claude API: https://docs.anthropic.com/
   - Prompt Engineering Guide: https://www.promptingguide.ai/

3. **LangChain & LangGraph**
   - LangChain Docs: https://python.langchain.com/
   - LangGraph Docs: https://langchain-ai.github.io/langgraph/
   - LangGraph Tutorials: https://langchain-ai.github.io/langgraph/tutorials/

4. **RAG & Vector Databases**
   - ChromaDB: https://docs.trychroma.com/
   - Pinecone: https://www.pinecone.io/learn/
   - LangChain RAG: https://python.langchain.com/docs/use_cases/question_answering/

5. **Multi-Agent Systems**
   - LangGraph Multi-Agent: https://langchain-ai.github.io/langgraph/tutorials/multi-agent/
   - Research Papers (read after basics):
     - "AutoGen" by Microsoft
     - "CrewAI" framework
     - Multi-agent system surveys

6. **Web Development**
   - FastAPI: https://fastapi.tiangolo.com/
   - Streamlit: https://docs.streamlit.io/
   - React: https://react.dev/learn

### Key Concepts to Master

1. **State Management**: Understanding how agents share state
2. **Orchestration**: How coordinator routes and manages agents
3. **RAG**: Retrieval-augmented generation for knowledge bases
4. **Prompt Engineering**: Writing effective prompts for agents
5. **API Design**: Building RESTful APIs
6. **Evaluation**: Designing experiments and metrics

### Weekly Time Commitment

- **Weeks 1-4**: 15-20 hours/week (learning phase)
- **Weeks 5-14**: 20-25 hours/week (development phase)
- **Weeks 15-22**: 20-25 hours/week (integration phase)
- **Weeks 23-30**: 15-20 hours/week (evaluation & demo)

### Getting Help

1. **Documentation**: Always check official docs first
2. **Stack Overflow**: For specific technical issues
3. **LangChain Discord**: Community support
4. **CMU-Q Faculty**: Your advisors and professors
5. **GitHub Issues**: For framework-specific problems

---

## Important Notes

### Research Ethics
- **Privacy**: Handle student data carefully
- **IRB Approval**: May need for user studies
- **Consent**: Get consent for using real student data
- **Anonymization**: Anonymize any real examples

### Technical Considerations
- **API Costs**: Monitor LLM API usage (can get expensive)
- **Rate Limits**: Be aware of API rate limits
- **Error Handling**: Robust error handling is crucial
- **Testing**: Test thoroughly at each phase

### Research Contributions
Remember to emphasize:
1. **Dynamic Multi-Agent Orchestration** (not just static routing)
2. **Structured Blackboard** (typed schema, not free text)
3. **Negotiation Protocols** (concrete mechanisms)
4. **Interactive Conflict Resolution** (user agency)
5. **Evaluation** (ablation studies, comparisons)

### Success Criteria
- System works end-to-end
- Demonstrates research contributions
- Handles complex advising scenarios
- Provides safe, accurate advice
- Good user experience
- Ready for ACL demo track

---

## Quick Start Checklist

- [ ] Week 1: Python environment + LLM API working
- [ ] Week 2: Basic RAG system working
- [ ] Week 3: Simple LangGraph multi-agent working
- [ ] Week 4: Knowledge base organized
- [ ] Week 8: Backend API working
- [ ] Week 14: All agents implemented
- [ ] Week 18: Full system integrated
- [ ] Week 22: UI complete
- [ ] Week 26: Evaluation done
- [ ] Week 30: Ready for submission

---

Good luck with your implementation! Start with Phase 1 and take it step by step. Don't hesitate to adjust timelines based on your learning pace.

