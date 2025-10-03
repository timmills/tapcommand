# Frontend Rewrite Findings

## Overview
- The existing React app fails to compile under the enforced `strict` TypeScript configuration (`tsconfig.app.json:2-26`) and is conceptually stuck between the original monolith and the rewrite plans.
- Build failures stem from missing utility exports, incompatible type definitions, and partially implemented feature splits (e.g., Tag Management, channel tooling, YAML builder).
- The three `FRONTEND*.md` guides capture the intent to rebuild, but they contain conflicting directions, outdated endpoint notes, and gaps that make it hard to execute without another round of discovery.

## Plan Document Observations
- `FRONTEND_ACTION_PLAN.md`: The "Selective Salvage" path still assumes Tag Management will be removed immediately (`FRONTEND_ACTION_PLAN.md:138-176`), yet the current code keeps `src/components/TagManagementTab.tsx` alive and deeply wired (`src/App.tsx:520-628`, `src/components/TagManagementTab.tsx:1-111`). Mixing those instructions with the live code explains why props/state are half-migrated. The plan also prescribes adopting Zustand/TanStack Query/Tailwind, but none of those packages exist in `package.json`, so the project is not actually following Option A or B yet.
- `FRONTEND_RECOVERY_GUIDE.md`: Several API notes are stale. The guide still references snake_case IR endpoints (`FRONTEND_RECOVERY_GUIDE.md:44-47`, `FRONTEND_RECOVERY_GUIDE.md:313`), but the backend ships the hyphenated prefix `"/api/v1/ir-libraries"` (`backend/app/routers/ir_libraries.py:13`). It also calls for `POST /api/v1/devices/discovery/start` (`FRONTEND_RECOVERY_GUIDE.md:72`, `FRONTEND_RECOVERY_GUIDE.md:329`), whereas the backend exposes `GET /api/v1/devices/discovery/start` (`backend/app/api/devices.py:63-68`). These discrepancies line up with the fetch helpers that were never finished.
- `FRONTEND_RESTART_FEASIBILITY.md`: Confirms a fresh build is the preferred strategy, but it underestimates the amount of re-modelling required to bring channel and template workflows back online (the current channel mocks still assume POST bodies that the backend PATCH routes do not accept; see `backend/app/routers/channels.py:175-205`). The doc also leans on type definitions (`TemplateLibraryItem`, `SelectedLibrary`, etc.) that were never synchronised in code, leading to the present type conflicts.

## Current Frontend Health Snapshot
- Running `npm run build` fails with >90 TypeScript errors. Representative issues:
  - `src/App.tsx` imports helpers such as `getApiErrorMessage` that do not exist (`src/App.tsx:27-36`, `src/utils.ts:1-25`).
  - Two competing type vocabularies exist: the legacy `src/types.ts` and the newer `src/types/index.ts`. Because `App.tsx` imports `./types`, the bundler resolves to `src/types.ts`, whose shapes (`SettingsTab = 'channels' | 'templates' | 'tags'`, `TemplateLibraryItem` without `brand` fields, etc.) conflict with the newer usage (`src/types.ts:1-135`, `src/types/index.ts:1-208`). This alone triggers dozens of "property does not exist" errors across pages.
  - `useDevices.updateDevice` still references an undefined `response` after an early throw (`src/hooks/useDevices.ts:46-58`), so the file never type-checks.
  - Channel and YAML flows depend on mock data with shapes that the backend never emits (e.g., `availability` arrays and `broadcaster_network` on in-house payloads in `src/hooks/useChannels.ts:23-100`), reinforcing the mismatch noted in the recovery guides.
  - Strict unused-variable checks (`tsconfig.app.json:18-24`) flag hundreds of dormant variables left midway through the refactor.
- Runtime ergonomics suffered as the state explosion in `src/App.tsx` (1400+ LOC) continues to orchestrate every tab; the move toward modular pages (`src/pages/*.tsx`) stalled before wiring them into a shared store.

## Why a Fresh Start is Justified
- Backend contracts are stable and well-defined via FastAPI routers (`backend/app/main.py:45-102`), but the frontend currently hardcodes `http://localhost:8000` inside hooks (`src/hooks/useDevices.ts:15`, `src/hooks/useChannels.ts:6`, `src/hooks/useTags.ts:4`), preventing environment-based configuration and SSR-friendly fetch layers.
- The overlapping type systems and partial component extraction make incremental fixes riskier than building from a clean scaffold that adopts the documented patterns (React 18 + TypeScript + Vite + dedicated data layer).
- Channel management, YAML builder, and Tag Management need holistic redesigns to match the backend’s PATCH/GET endpoints (`backend/app/routers/channels.py:151-210`, `backend/app/routers/settings.py:35-125`, `backend/app/routers/templates.py:19-210`). Recreating those flows with TanStack Query/Zustand is easier than untangling the current prop drilling.

## Suggested Fresh Start Outline
1. **Archive and scaffold**: Move `frontend` to `frontend-legacy` and bootstrap a new Vite React/TS app; add dependencies `@tanstack/react-query`, `zustand`, `zod`, `react-hook-form`, and a styling baseline (Tailwind or CSS modules).
2. **Centralise API access**: Build a typed client that reflects the real routes (pay special attention to hyphenated prefixes and HTTP verbs). Generate types from the FastAPI OpenAPI schema so the frontend and backend stay aligned.
3. **State architecture**: Use TanStack Query for backend reads and mutations; reserve Zustand for cross-cutting UI state (selected device, dialog visibility). Co-locate slices per feature to avoid reviving the monolithic `App.tsx` controller.
4. **Feature sequencing**: Implement device discovery/management first, then IR sender port assignments, followed by YAML builder and template save flows, and finally channel & tag management. Ship each tab with accompanying Vitest + Testing Library coverage.
5. **Styling & UX**: Establish a design system early (button/input primitives, layout shell) and bake in loading/error/empty states per the recovery guide goals. Budget time for WebSocket/SSE integration once core pages are stable.
6. **Migration plan**: Run the new frontend on an alternate port, gate access via env flag, and backfill data migration scripts as needed (e.g., mapping legacy tag IDs).

## If Short-Term Triage Is Needed
- Restore missing helpers (or remove their usage) to get TypeScript compiling: either re-implement utility exports or rewrite `App.tsx` to use the new helper set.
- Delete/rename `src/types.ts` after migrating consumers to `src/types/index.ts` so the compiler resolves a single source of truth.
- Replace hardcoded API bases with `import.meta.env` variables and update the fetch hooks to the correct verbs and payloads.
- Relax `noUnused*` temporarily if you must ship a stopgap, but plan to re-enable once the new structure is in place.

These notes should give us a clearer path forward and a reality check against the existing plans before committing to the rewrite.
