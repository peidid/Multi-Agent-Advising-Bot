# dev/ — local developer & demo tools

These are **not** part of the production app (that's `backend/` + `frontend/`),
but they are live, working tools that drive the same multi-agent engine
(`multi_agent.py`). They each add the repo root to `sys.path` so they can be run
from anywhere.

| File | What it does | Run from repo root |
|---|---|---|
| `chat.py` | Terminal REPL that runs the full LangGraph workflow and prints coordinator routing + per-agent output. Fastest way to exercise the engine without the web stack or a database. | `python dev/chat.py` |
| `streamlit_app.py` | Streamlit research UI that visualizes all agents and the blackboard for demos. | `streamlit run dev/streamlit_app.py` |
| `requirements_streamlit.txt` | Extra deps for the Streamlit UI. | `pip install -r dev/requirements_streamlit.txt` |

Both need the same OpenAI configuration as the backend (`OPENAI_API_KEY`, and
optionally `OPENAI_API_BASE`) and the prebuilt `chroma_db_*` indexes at the repo
root. They do **not** require MongoDB.
