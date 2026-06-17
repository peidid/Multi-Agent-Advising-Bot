# archive/ — dead code & legacy docs (NOT part of the running system)

Nothing in this folder is imported or executed by the production app
(`backend/server.py` → `multi_agent.py`) or the `frontend/`. It is kept only
for reference/history and can be deleted entirely without affecting the system.

Verified dead on 2026-06-17 via an import-closure analysis from the live
entrypoint, plus removal of the few dead-but-imported references in the live
code (see git history of this branch). See `../0_SYSTEM_REPORT.md` for the full
rationale.

## Contents

| Path | What it was | Why it's here |
|---|---|---|
| `api/` | A second, modular FastAPI backend (`api/main.py`, routers, services, 5-collection Mongo schema) + `run_api.py`, `requirements_api.txt`, `run_api.bat` | Abandoned rewrite. **Never deployed** — production is `backend/server.py`. Its DB schema diverges from the live one. |
| `dead_modules/planning/` | "Planning mode" collaborative negotiation coordinator | Feature whose UI was removed (commit `1ccf2a0`); `planning_mode` was never sent by the frontend. The live code paths that imported it were removed. |
| `dead_modules/planning_tools.py` | Prereq/plan helpers for planning mode | Superseded by validators in `course_tools.py`; no live importer. |
| `dead_modules/clarification_handler.py` | Interactive clarification handler | Instantiated by the coordinator but never invoked; the wiring was removed from `coordinator/coordinator.py`. |
| `dead_modules/intent_classifier_enhanced.py` | Prompt-based intent classifier | Superseded by `coordinator/llm_driven_coordinator.py` + `coordinator/finetuned_classifier.py`. Only referenced from a docstring. |
| `dead_modules/memory/` | `memory_manager.py`, `entity_tracker.py`, `profile_manager.py` | The old short-term-memory/profile system. Superseded by `LLMDrivenCoordinator.resolve_context()` + the Mongo profile. Only `memory/context_formatter.py` remains live at the root. |
| `dev_scripts/` | One-time ingestion + the fine-tune training pipeline (`scripts/`) + tests for dead code (`test_api.py`, `test_planning.py`) + `convert_schedules.py`, `process_*_schedules.py`, `generate_document_metadata.py`, `setup_domain_indexes.py`, `cleanup_project.py`, `verify_models.py` | One-off/offline tooling, not run by the app. NOTE: `rebuild_indexes_with_metadata.py` is **not** here — it's used by the Docker build and stays at the repo root. |
| `docs_legacy/` | ~55 historical `.md`/`.txt` files (bugfix notes, status reports, proposals, quick-starts) | Mostly stale or superseded. `0_SYSTEM_REPORT.md` (repo root) is the current authoritative document. |
| `misc/` | `Benchmark.zip` (unzipped copy lives at `../Benchmark/`), `info/`, `info - 副本/` (duplicate) | Redundant artifacts. |

## To permanently delete

```bash
git rm -r archive/
```
(History is preserved in git regardless.)
