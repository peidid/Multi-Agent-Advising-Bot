# Multi-Agent Academic Advising Bot (CMU-Qatar)

A multi-agent academic advising chatbot for Carnegie Mellon University–Qatar.
A coordinator LLM routes each student question to specialized domain agents
(Programs & Requirements, Course Scheduling, Policy Compliance, Academic
Planning) that run in parallel, each retrieving from its own RAG index and
writing into a shared blackboard; the coordinator evaluates their outputs and
synthesizes the final answer, streaming progress to the UI in real time.

> **Deep dive:** [`0_SYSTEM_REPORT.md`](0_SYSTEM_REPORT.md) is the authoritative,
> code-verified technical report (architecture, the live request path traced
> hop-by-hop, data model, models/prompts, known issues). Read it before making
> substantial changes.

---

## Project structure (live system)

```
.
├── multi_agent.py            # LangGraph engine: coordinator → parallel_agents → synthesize
├── config.py                 # model + endpoint configuration (single source of truth)
├── rag_engine_improved.py    # Chroma retrievers, 5 domain indexes (DOMAIN_PATHS)
├── course_tools.py           # structured course/schedule lookups + plan validators
├── course_name_mapping.py    # course-code / major helpers
├── rebuild_indexes_with_metadata.py   # (re)builds chroma_db_* from data/ — used by Docker build
│
├── coordinator/              # triage, intent classification, agent selection, evaluation, synthesis
│   ├── coordinator.py            #   main Coordinator (gpt-4o-mini triage, gpt-4-turbo plan/synth, gpt-5.2 eval)
│   ├── llm_driven_coordinator.py #   LLM agent-selection + short-term memory (resolve_context)
│   └── finetuned_classifier.py   #   optional fine-tuned router
├── agents/                   # base_agent + 4 domain agents (programs, courses, policy, planning)
├── blackboard/schema.py      # shared BlackboardState + AgentOutput/Risk/Constraint/PlanOption
├── memory/context_formatter.py  # formats profile + history into agent prompts
├── streaming/                # SSE event types + callback queue
├── baselines/runners.py      # ablation systems (single-agent, CoT, one-shot, opaque)
│
├── backend/                  # ★ PRODUCTION API (FastAPI + MongoDB + JWT) — server.py, database.py
├── frontend/                 # ★ PRODUCTION UI (Next.js 14)
│
├── data/                     # knowledge base (courses, schedules, policies, programs, planning)
├── chroma_db_*/              # prebuilt vector indexes (one per domain)
├── Benchmark/                # T1–T5 evaluation task suite
│
├── dev/                      # local dev/demo tools (CLI + Streamlit) — see dev/README.md
└── archive/                  # dead code & legacy docs, NOT run — see archive/README.md
```

## Running it

### 1. Backend (production API)
```bash
pip install -r requirements.txt
# configure backend/.env  (copy from backend/.env.example):
#   MONGODB_URI, MONGODB_DATABASE, OPENAI_API_KEY, JWT_SECRET_KEY,
#   ALLOWED_ORIGINS, (optional) OPENAI_API_BASE, PORT
python rebuild_indexes_with_metadata.py     # build chroma_db_* (first run only)
uvicorn backend.server:app --host 0.0.0.0 --port 8000
```

### 2. Frontend
```bash
cd frontend
npm install
# set NEXT_PUBLIC_API_URL (defaults to http://localhost:8000)
npm run dev        # http://localhost:3000
```

### 3. Dev tools (no web stack / no DB needed)
```bash
python dev/chat.py                       # terminal REPL against the engine
streamlit run dev/streamlit_app.py       # research visualization UI
```

### Deployment
Railway via `Dockerfile` (`railway.json` → Dockerfile). The container builds the
indexes and runs `uvicorn server:app` from `/app/backend`. `Procfile` runs the
equivalent `uvicorn backend.server:app`.

## Models (`config.py`)

| Role | Model |
|---|---|
| Triage (greeting/general/academic) | `gpt-4o-mini` |
| Coordinator routing + synthesis | `gpt-4-turbo` |
| Domain agents + output evaluation | `gpt-5.2` |
| Embeddings | OpenAI embeddings |

> ⚠️ `gpt-5.2` in `config.py` is a placeholder id with no fallback — confirm it
> resolves at your OpenAI endpoint, or every academic query will fail. See
> `0_SYSTEM_REPORT.md` §6.

## Ablation systems (research)

The backend exposes `GET /api/systems`; the frontend's selector picks one per
request via the `system` field of `POST /api/chat/stream`:
`multi_agent` (full), `multi_agent_opaque`, `single_agent`, `single_agent_cot`,
`one_shot`. Defined in `baselines/runners.py` + `backend/server.py`.
