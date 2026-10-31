# CommandIA

CommandIA is a conversational commerce workspace for Algerian e-commerce shops. It combines a FastAPI backend, a Gemini-powered order assistant, and a React dashboard.

## Repository layout

The repository uses a single `main` branch. The FastAPI backend is at the repository root and the React app is in `frontend/`.

When hosting only the frontend, configure the hosting provider with `frontend` as the project root directory.

## Features

- Email/password accounts with HttpOnly cookie sessions.
- Seeded conversations, orders, products, business rules and AI settings.
- Human takeover and AI resume per conversation.
- Product catalog and order status management with JSON persistence.
- Instagram connect/disconnect and global AI switches.
- Gemini replies and order extraction when `GEMINI_API_KEY` is configured.
- Deterministic offline replies when Gemini is unavailable.
- FastAPI can serve the production React build directly.
- Meta webhook and a protected `/chat` development endpoint.

## Requirements

- Python 3.10+
- Node.js 18+ and npm
- Optional: Gemini API key for real AI replies

## Local setup

```powershell
py -3.10 -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
npm --prefix frontend install
```

Edit `.env` and set `GEMINI_API_KEY` for real AI. The app also runs with local fallback replies when no key is configured.

Demo account:

```text
Email: demo@commandia.dz
Password: demo1234
```

## Development

Start the backend from the repository root:

```powershell
py -3.10 -m uvicorn app:app --reload --port 8000
```

Start the React dev server in a second terminal:

```powershell
npm --prefix frontend run dev
```

Open http://localhost:5173. Vite proxies `/api` to `http://localhost:8000`.

## Production-style fullstack run

```powershell
npm --prefix frontend run build
py -3.10 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

FastAPI serves `frontend/dist` at http://localhost:8000, including client-side routes.

## Frontend hosting

The frontend is in `frontend/` on `main` and is configured for static hosting.

### Vercel

1. Push the repository to GitHub, GitLab or Bitbucket.
2. In Vercel, choose **Add New > Project** and import the repository.
3. Select the `main` branch.
4. Set **Root Directory** to `frontend`.
5. Use framework preset **Vite**, build command `npm run build`, output directory `dist`.
6. Add environment variables:
   - `VITE_USE_MOCK=false`
   - `VITE_API_URL=https://your-backend.example.com` only if the API is on another origin
7. Deploy.

`frontend/vercel.json` adds the SPA fallback so routes such as `/features` and `/app/inbox` work on refresh.

### Netlify

1. Import the repository and select the `main` branch.
2. Set **Base directory** to `frontend`.
3. Netlify reads `frontend/netlify.toml`; build command is `npm run build` and publish directory is `dist`.
4. Set `VITE_USE_MOCK=false` and, when needed, `VITE_API_URL=https://your-backend.example.com`.
5. Deploy.

### Cloudflare Pages

1. Create a Pages project and connect the repository.
2. Select the `main` branch.
3. Set **Root directory** to `frontend`.
4. Framework preset: **Vite**.
5. Build command: `npm run build`.
6. Build output directory: `dist`.
7. Set `VITE_USE_MOCK=false` and, when needed, `VITE_API_URL=https://your-backend.example.com`.
8. Deploy.

`frontend/public/_redirects` provides the SPA fallback for Netlify and Cloudflare Pages. `frontend/public/_headers` adds basic security and asset-cache headers.

### Backend configuration for a separately hosted frontend

On the backend, allow the hosted origin and enable cross-origin cookies:

```env
COMMANDIA_CORS_ORIGINS=https://your-frontend.example.com
COMMANDIA_COOKIE_SECURE=True
COMMANDIA_COOKIE_SAMESITE=none
```

Use `COMMANDIA_COOKIE_SAMESITE=lax` only when frontend and backend share the same site, such as `app.example.com` and `api.example.com`.

For the most reliable login cookies, use custom domains under the same registrable domain or proxy `/api` from the frontend host to the backend. Avoid relying on cross-site third-party cookies because some browsers block them.

### Simplest deployment

If you do not need a separate frontend host, deploy `main` as one service, run `npm --prefix frontend run build`, and let FastAPI serve `frontend/dist`. Authentication then stays same-origin and no CORS or cross-site cookie configuration is needed.

## Data and reset

Workspace state is stored in `data/state.json`; initial data comes from `data/seed.json`. Delete `data/state.json` and restart the backend to reset the demo workspace.

Never commit `.env`, `data/state.json`, `frontend/node_modules` or `frontend/dist`.

## Tests

```powershell
py -3.10 -m pytest -q
npm --prefix frontend run build
```

The Python suite is offline and stubs Gemini.

## Project layout

```text
app.py                 FastAPI entrypoint, Meta webhook, static frontend
api_routes.py          /api routes used by the React app
auth.py                PBKDF2 passwords and signed session cookies
local_store.py         Atomic JSON persistence and seed loading
local_ai.py            Offline fallback replies
ai_brain.py            Gemini extraction pipeline and state machine
ai_service.py          Conversation service wrapper
schemas.py             Pydantic order contracts
wilayas.py             Algerian wilaya validation
order_store.py         Optional Supabase order persistence
data/seed.json         Initial demo workspace
docs/                  Product requirements and roadmap
frontend/              React + TypeScript + Vite app
tests/                 Offline backend and API tests
```

## API

Authentication:

- `POST /api/auth/sign-up`
- `POST /api/auth/sign-in`
- `POST /api/auth/sign-out`
- `GET /api/auth/me`

Workspace:

- `GET /api/conversations`
- `PATCH /api/conversations/{id}/mode`
- `POST /api/conversations/{id}/messages`
- `GET /api/orders`
- `PATCH /api/orders/{id}/status`
- `GET /api/products`
- `POST /api/products`
- `PUT /api/products/{id}`
- `GET /api/settings`
- `PATCH /api/settings/ai`
- `POST /api/integrations/instagram/connect`
- `POST /api/integrations/instagram/disconnect`
- `GET /api/rules`
- `PUT /api/rules`

AI and Meta:

- `GET /healthz`
- `GET /webhook`
- `POST /webhook`
- `POST /chat`

## Security note

This is a local prototype. Local accounts, JSON persistence and demo cookies are suitable for development and demonstrations, not a public multi-tenant production system. Set a private `COMMANDIA_SESSION_SECRET`, enable secure cookies behind HTTPS, and replace the JSON store with a real database before handling real customer data.
