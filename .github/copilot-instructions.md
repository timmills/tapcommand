<!-- Copilot instructions for the TapCommand repo: concise, actionable, and repository-specific. -->

# TapCommand — Copilot instructions (concise)

Purpose: help an AI coding agent be immediately productive in this repository. Keep suggestions precise, minimal-risk, and evidence-based (only change files referenced below unless asked).

Key pointers (do these first)
- Read `backend/app/main.py` to understand startup lifecycle: DB creation, discovery, health, queue processor, schedule processor, and cleanup services start at app lifespan.
- Use `backend/run.sh` or `backend/run.sh` pattern to launch backend; canonical dev command: `cd backend && source ../venv/bin/activate && python -m uvicorn app.main:app --reload` (also in `CLAUDE.md`, `AGENTS.md`).
- The active frontend is `frontend-v2/` (not `frontend/`). Use `cd frontend-v2 && npm install && npm run dev`.

Architecture & boundaries (short)
- Backend: FastAPI app in `backend/app/` (routers under `api/` and `routers/`, services under `services/`, models under `models/`). Key entry: `backend/app/main.py`.
- Command routing: unified command queue (`backend/app/models/command_queue.py`, service `backend/app/services/command_queue.py`, processor `backend/app/services/queue_processor.py`). Prefer changing queue logic only when you update both service and processor.
- Device types: IR controllers (`ir-*`), Network TVs (`nw-*`), Audio controllers (`audio-*`). Discovery and capability fetch for ESPHome devices occurs via mDNS and `esphome_manager` (see `services/esphome_client.py`).
- ESPHome firmware lives in `esphome/` and is compiled with ESPHome CLI (available in the venv).

Important developer workflows
- Bootstrap backend: `./backend/run.sh` (creates venv, pip installs, runs uvicorn). For iterative dev use `uvicorn --reload` command above.
- Database: SQLite at `backend/tapcommand.db`. Tables created programmatically by `backend/app/db/database.py::create_tables()` on startup — there is no active Alembic migration workflow for runtime schema (some migration scripts exist in `backend/migrations/`).
- Run discovery probe: `cd backend && source ../venv/bin/activate && python test_discovery.py`.
- Inspect command queue: `GET /api/commands/queue/metrics` or query SQLite (`sqlite3 backend/tapcommand.db`).

Project-specific conventions (must follow)
- Hostname prefixes drive routing: `ir-` = ESPHome IR controllers, `nw-` = network TVs, `audio-`/`plm-` = audio controllers. Discovery, adoption, and router selection branch on these prefixes.
- Frontend/Backend param naming: frontend uses `box` for IR ports; backend uses `port`. Translate when touching API or esphome client code (see `services/esphome_client.py`).
- Async-first: device comms are async (aioesphomeapi, httpx). Prefer async functions for I/O. Use `SessionLocal()` for DB sessions and always close them (try/finally).
- Queue semantics: commands have `command_class` (immediate/interactive/bulk/system). Only interactive/immediate should bypass the queue for low-latency operations.
- Logging and non-throwing APIs: most device APIs log errors and return success flags instead of raising—mirror this pattern for backward compatibility.

Integration points & dependencies to be careful about
- ESPHome: uses `aioesphomeapi` and in-repo `esphome/` YAMLs. Capability discovery uses `report_capabilities` service; changes to capability format require DB field updates (`device.capabilities`).
- Network TV libraries: `pywebostv`, `samsungctl`, `hisensetv` etc. Tests should mock network calls (see `backend/tests/` guidance in `AGENTS.md`).
- AES70 audio: `aes70py` is installed from a wheel URL; be mindful when updating versions.

Quick examples to copy/paste (use these when editing code)
- Enqueue a command (use `CommandQueueService.enqueue`):
  - File: `backend/app/services/command_queue.py`
  - Example: enqueue a channel change: call `await CommandQueueService.enqueue(db, hostname, 'channel', 'interactive', port=1, channel='60')`.
- Fetch capabilities after discovery (pattern in `main.py`): schedule async task with `asyncio.run_coroutine_threadsafe(fetch_caps(), _main_loop)` when inside a sync mDNS callback.
- Mark command completed/failed: use `CommandQueueService.mark_completed(db, id, True, exec_ms)` and `CommandQueueService.mark_failed(db, id, "error", retry=True)` to keep history and port status consistent.

What not to do
- Don't change DB table names or columns without updating `create_tables()` and migration scripts in `backend/migrations/`.
- Don't assume synchronous device access—mixing sync calls into discovery callbacks must schedule into the main loop (see `_main_loop` usage in `main.py`).

Files worth reading before large changes
- `backend/app/main.py` (startup, lifespan, discovery callback pattern)
- `backend/app/services/command_queue.py` and `backend/app/services/queue_processor.py` (queue contract)
- `backend/app/services/esphome_client.py` (ESPHome service naming/box->port translation)
- `backend/app/core/config.py` (env and DB path conventions)
- `esphome/esp_multi_report.yaml` (capabilities contract)

If you make changes
- Run: `cd backend && source ../venv/bin/activate && python -m uvicorn app.main:app --reload` and exercise `/docs` for API shape.
- Run discovery probe and a queue metric check; ensure no unhandled exceptions in logs. Tail `journalctl -u tapcommand-backend.service -f` if using systemd.

Questions to ask the maintainer when unsure
- Should a change affect historical command semantics (queue ordering, retry/backoff)? If yes, require QA on devices.
- Is a schema change allowed in deployed venues? Prefer additive, backward-compatible changes or migration scripts in `backend/migrations/`.

End of file — ask for clarification if any integration points (ESPHome capability schema, network TV executor interfaces, AES70 mapping) are unclear.
