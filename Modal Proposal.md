Based on the previous version provided, I’ve come up with the following ideas. 

To put it into one sentence, the current version is a well-structured RAG workflow (which is really impressive), and we may add dynamic role allocation, iterative negotiation, coordination protocols, and emergent collaboration, to become a full-blown dynamic multi-agent system in the research sense, featuring visible negotiation and collaborative planning.

*   **Expanded Agents & Specialized Roles**
    

Given that agents have better performance with specialized and focused task & knowledge base, we could introduce more agents (maybe 5-12 agents in total) which are responsible for a specific & focused portion respectively. (I will list some potential agents later)

**Dynamic Workflow & Orchestrated Negotiation**

Secondly, instead of a static workflow, we may try a dynamic multi-agent system, featuring an **orchestration of specialized agents** that collaborate to solve a user's problem. There will be a supervisor/orchestrator that decides what action next. For example, if a student considers taking an additional major, the orchestrator modal may call for academic apartments, registration & policy (like overload issue), and finance (for tuition) agents. If the Registration & Policy agent flags a risk, the supervisor/orchestrator dynamically routes this conversation to a different agent to solve the problem. 

Instead of a linear chain, we apply a hub-and-spoke topology managed by the coordinator. Agents do not talk to each other directly to prevent hallucination. They communicate via a Shared State (The Blackboard) managed by the Coordinator. The Coordinator decides "Communication Access." For example, If the user asks about tuition, the Coordinator grants access to the Finance Agent but keeps the Career Agent silent to save tokens and reduce noise.

After some research, I’m confident that this is doable in LangGraph.

**History/memory integration**

Storing and summarizing long-term student data. Implement more long-term memory, add access to student information (such as GPA and credits) and chat history. This could make personalized consulting more accessible and convenient for students.

**Richer Database**

For the database, I believe there is room for refinement or addition, to enhance the performance of the advising bot. I can get more data from scotty, which can be merged with the current effort. 

**Interactive Conflict resolution**

Advising is about trade-offs, not just rules. To make the process of negotiation transparent, visible, and interactive to students, the coordinator could expose the conflict through a UI widget. Instead of generating the whole answer in one go, like basic LLM, it leaves some decisions to students (user agency), and dynamically asks follow-up questions.

**AI-Replica & personalities?**

Maybe the advisor has his/her own academic/life experience that could be integrated in the advice? Or provide lived examples or historical cases, such as alumni/professor’s experience to make the advising more convincing and mimic?

Below are some ideas about the agents. We may not implement all of them, and there is room for discussion about feasibility.

Main Advisor (coordinator)

Knowledge base:

Conversational context, the shared state (blackboard) containing data retrieved by other agents

All agents’ tasks, features, & ability

General academic advising approach and knowledge (expertise and experience for professional advisors)

Task:

Intent classification & routing. Analyze user’s input and plan the workflow, decide which agents to be activated.  (for example, as an IS student wanting to take CS minor, it needs to coordinate IS, CS, and maybe uni-level registration & policy department, maybe also finance). The planning workflow may be dynamically changing over the conversation.

Access control. Decide access to the shared state and communication to prevent noise. It silents irrelevant agents

Conflict Detection. Evaluate outputs from multiple agents, and organize negotiation processes if necessary. 

Ask users follow-up questions, such as when conflicts emerge or clarification is needed.

Ensure the workload is mentally and physically healthy & sustainable

Ability:

High-level reasoning (advising-based), state management (dynamic workflow & communication access), interact with users (follow-up questions)

Long-term Memory/personalization: 

Knowledge base:

Students’ previous consulting history

Students’ academic performance records

Task:

Retrieve and summarize the students’ consulting history and academic performance data (such as GPA or credit progress), so that other agents could rapidly read and understand, to provide more custom and individualized consulting.

Ability:

Access to student information

API to Stellic/SIO for progress tracking

Academic departments (majors) Agents:

Knowledge base:

Each program’s courses, requirements, schedule, academic resources or so.

Task:

Be able to deal with major-related issue, such as course requirements for obtaining the degree, or transfer policy

Provide major-specific information, since different departments’ policies vary a lot.

Ability:

Access departments’ online resources, policies, & related information.

Course Agents:

Knowledge Base:

Each course’s basic info, credit, pre-requisite, etc.

Specific offering detail, such as if 15-122 is offered in 2026 spring, and the instructor

Task:

Answer queries regarding course information

Ability:

Access to Stellic API or ScottyLab API (if possible)

Minor Agents:

Knowledge base:

Each minor’s requirement, introduction, responsible professors etc.

Uni minor policy and how to enroll

Task:

Answer questions regarding minors at CMUQ

University-level policies Agent:

Knowledge base:

Uni-level policies regarding registration, finance, academic integrity, exam & grading  etc.

Task:

Check & guide if the solution/answers on the state follow the university policies.

Make adaption if conflicts between user intention and uni-level rules emerge.

clarify/answer query regarding uni-level policies.

Provide financial assistance & information

Event Agent:

Knowledge base:

Up-to-date activity information

Global trip, such as exchange to Pittsburg and global learning trip.

Task:

Retrieve useful information for school activities, along with access for registration

Plan for global trips, as opportunities are limited.

Ability:

API to school activity calendar

Career advice agent:

Knowledge base:

Basic knowledge about career development/job skills

Doha, and also international, job market landscape & opportunities

Updated on-campus working opportunities

Task:

Advice on career/job development issues, such as internship, CVs…

Match career/job/intern opportunities

Help to find on-campus job opportunities

Ability:

Access specialized web like handshake & linkedin

Online search for job/intern opportunities

Research Agent:

Knowledge base:

On-campus research platform/project/opportunities

Information about how to start undergraduate research

Task:

Provide instructions/guidance for undergraduate research

Match research opportunities, look for ongoing research and professors’ interests

Look for research opportunities outside the university

Ability:

Search on web for research opportunities/papers

People/faculty agents

Knowledge base:

Each faculty/stuff/position’s basic info, bio, responsibilities, experience, expertise

Task:

If needed, tell the user who to turn to

Match faculties’ academic interests with students’ for research

Ability:

Access people’s personal web, google scholar, linkedin…

This is a brainstorm proposal, so any comment, critics, or feedback are more than welcome.