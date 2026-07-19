# Frontend — Industrial Brain AI

## Install

```bash
npm install
```

## Run

```bash
npm run dev
```

Open http://localhost:3000 — unauthenticated users are sent to `/login`; after sign-in the enterprise shell opens on `/dashboard`.

Set the API base URL (default `http://localhost:8000`):

```bash
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Milestone 1.8 shell

- Architecture §10 sidebar routes under `app/(app)/`
- Auth-gated layout (`AuthGate`)
- Dark/light theme (`next-themes`)
- TanStack Query + authenticated `apiClient`
- shadcn-style `Button` baseline (`components/ui`)

## Tooling

```bash
npm run lint
npm run format:check
npm run build
```
