# Repository Guidelines

## Project Structure & Module Organization
- `backend/app` contains the FastAPI service: `api` exposes routes, `services` handles discovery and IR orchestration, `models` defines SQLAlchemy tables, and `db` manages the SQLite link.
- `backend/run.sh` provisions the local virtualenv and starts Uvicorn; use it for reproducible setup.
- `frontend/` holds the Vite + React TypeScript UI, with entrypoints in `src/main.tsx` and `src/App.tsx` and shared assets under `src/assets`.
- `esphome/`, `esp_foxtel/`, and `esp_multi/` store firmware references; `esphome/esp_multi_report.yaml` is the production profile clone that exposes the `report_capabilities` service used during adoption.

## Build, Test, and Development Commands
- Backend (live reload): `cd backend && source ../venv/bin/activate && python -m uvicorn app.main:app --reload`.
- One-shot bootstrap: `cd backend && ./run.sh` to create the venv, install requirements, and launch the API.
- Discovery probe: `cd backend && source ../venv/bin/activate && python test_discovery.py` for a 30-second mDNS sweep.
- Frontend dev server: `cd frontend && npm install && npm run dev`; production check with `npm run build && npm run preview`.
- Linting: `cd frontend && npm run lint`; add a Python formatter/linter (e.g., `ruff`, `black`) when touching backend code.

## Coding Style & Naming Conventions
- Python follows PEP 8 with 4-space indents, type hints, and docstrings summarizing async workflows.
- React/TypeScript uses 2-space indents, `PascalCase` component files, and `camelCase` hooks/utilities; colocate feature styles with their component.
- Keep API paths snake_case and align ORM class names with table names to avoid migration surprises.

## Testing Guidelines
- Prefer `pytest` cases under `backend/tests/` for new logic; mock network clients so tests stay deterministic.
- Use `test_discovery.py` for manual validation only—promote mature scenarios into automated tests.
- For frontend changes, add Vitest + React Testing Library specs named `ComponentName.test.tsx` alongside the component.

## Commit & Pull Request Guidelines
- Commits use short, imperative summaries with expressive emojis (e.g., `✨ Add IR port reassignment endpoint`); continue the pattern for clarity.
- Keep commits scoped to one functional change, even if both backend and frontend are involved.
- PRs should describe intent, list validation commands, add UI screenshots or API samples, and link roadmap items or issues.

## Security & Configuration Tips
- Secrets load through `backend/app/core/config.py`; override values in an untracked `.env`, and never commit venue credentials or ESPHome keys.
- Sanitize logs that include device properties, and rotate ESPHome API keys whenever firmware bundles change hands.
