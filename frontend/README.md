# CommandIA frontend

React + TypeScript + Vite dashboard and public site for CommandIA.

This directory is also published as the root of the `frontend` Git branch for static hosting. On that branch, this file is the repository README.

## Run locally

```bash
npm install
npm run dev        # http://localhost:5173, /api proxied to localhost:8000
npm run build      # type-check + production build
npm run preview
```

Start the FastAPI backend from the fullstack repository root first:

```bash
py -3.10 -m uvicorn app:app --reload --port 8000
```

## API configuration

`src/services/api.ts` is the only module that talks to the backend. It uses same-origin `/api` by default, which works through the Vite proxy in development and through FastAPI when the fullstack app is served together.

Optional environment values:

```env
# Backend origin when the frontend is hosted separately.
VITE_API_URL=https://your-backend.example.com

# In-memory seed data, no backend required.
VITE_USE_MOCK=false
```

When `VITE_API_URL` is used, the backend must allow the frontend origin through `COMMANDIA_CORS_ORIGINS` and use credentials-compatible cookie settings.

## Hosting configuration

| File | Purpose |
| --- | --- |
| `vercel.json` | SPA fallback for Vercel |
| `netlify.toml` | Build settings and Node version for Netlify |
| `public/_redirects` | SPA fallback for Netlify and Cloudflare Pages |
| `public/_headers` | Security and asset caching headers |
| `.nvmrc` | Node 20 for providers that read it |

The build output is always `dist/`.

## Deploy to Vercel

1. Import the repository.
2. Select the `frontend` branch.
3. Framework preset: **Vite**.
4. Root directory: `./`.
5. Build command: `npm run build`.
6. Output directory: `dist`.
7. Environment variables:
   - `VITE_USE_MOCK=false`
   - `VITE_API_URL=https://your-backend.example.com` if the API is on another origin
8. Deploy.

## Deploy to Netlify

1. Import the repository and select the `frontend` branch.
2. Netlify reads `netlify.toml`; keep the base directory empty.
3. Set the same environment variables as above.
4. Deploy.

## Deploy to Cloudflare Pages

1. Create a Pages project and connect the repository.
2. Select the `frontend` branch.
3. Framework preset: **Vite**.
4. Build command: `npm run build`.
5. Build output directory: `dist`.
6. Set the same environment variables as above.
7. Deploy.

## API deployment note

If the backend is on another domain, set `VITE_API_URL` before building. Configure the backend with `COMMANDIA_CORS_ORIGINS` and use `COMMANDIA_COOKIE_SAMESITE=none` with `COMMANDIA_COOKIE_SECURE=True` for cross-site cookies.

For the most reliable authentication, host frontend and backend on the same site, for example `app.example.com` and `api.example.com`, or serve `frontend/dist` directly from FastAPI.

## Routes

Public: `/`, `/features`, `/how-it-works`, `/pricing`, `/faq`, `/signin`, `/signup`.

Authenticated: `/onboarding`, `/app`, `/app/inbox[/:id]`, `/app/orders[/:id]`, `/app/catalog`, `/app/rules`, `/app/ai-settings`, `/app/integrations`.

## Structure

- `src/store.tsx`: app state, auth, conversations, orders, products, settings.
- `src/pages/`: one file per area.
- `src/components/`: shared layout, inbox, icons and modal UI.
- `src/styles/`: design stylesheets.
- `src/data/seed.json`: mock data used only when `VITE_USE_MOCK=true`.
