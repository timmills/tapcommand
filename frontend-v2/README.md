# TapCommand Frontend v2

A fresh React + TypeScript interface built with Vite, TanStack Query, Zustand, Tailwind CSS, and React Router. This
project pairs with the existing FastAPI backend to provide modern device management, discovery, and template tooling.

## Getting Started

```bash
cd frontend-v2
cp .env.example .env.local # adjust API base URL if needed
npm install
npm run dev
```

Visit `http://localhost:5174` to load the new UI while the current frontend continues to run on its original port.

## Available Scripts

- `npm run dev` – Start the Vite development server (port 5174)
- `npm run build` – Type-check and build the production bundle
- `npm run preview` – Preview the production build locally
- `npm run lint` – Lint the codebase with ESLint + TypeScript ESLint

## Architecture Notes

- **Data fetching** is handled by TanStack Query using a shared Axios instance (`src/lib/axios.ts`).
- **State** that needs to cross feature boundaries can be added to dedicated Zustand stores under `src/stores/`.
- **Styling** relies on Tailwind CSS with a lightweight semantic palette (`brand`) for primary actions.
- **Routing** is defined in `src/app/router.tsx`, with a responsive layout in `src/routes/root-layout.tsx`.
- **Firmware workflows** live inside the template detail view and call `/api/v1/templates/preview`, `/compile`, and `/download/{filename}`.

### Feature Modules

- `features/devices` – Managed device grid backed by `/api/v1/management/managed`.
- `features/devices/pages/connected-devices-page.tsx` – Venue devices derived from controller port assignments.
- `features/discovery` – Live mDNS discovery view calling `/api/v1/devices/discovery/*`.
- `features/templates` – Template catalogue sourced from `/api/v1/templates`.
- `features/settings` – Placeholder for upcoming Wi-Fi/tag/channel configuration flows.

## Next Steps

- Introduce WebSocket streaming (using `VITE_WS_BASE_URL`) for real-time status updates.
- Add Vitest + React Testing Library coverage per feature module (`*.test.tsx`).
