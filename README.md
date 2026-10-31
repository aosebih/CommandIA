# CommandIA

**Conversational commerce for Algerian businesses.**

CommandIA is an AI-powered assistant for social-commerce teams. It helps businesses handle customer conversations in Algerian Darija, Franco-Arabic, French, and English, collect order information, and keep order workflows organized.

The repository contains a FastAPI backend and AI service, a React dashboard prototype, and a Streamlit demo. The dashboard currently runs on mock data by default; see [Current limitations](#current-limitations) before using it with real customers.

## What it does

- Understands informal, multilingual customer messages.
- Guides a conversation from product inquiry to order confirmation.
- Extracts and validates customer, delivery, and order details using Pydantic schemas.
- Integrates with Meta webhooks for Instagram and Facebook messaging.
- Can persist orders and conversation data with Supabase when configured.
- Provides a React merchant dashboard prototype and a standalone Streamlit demo.

## Repository map

```text
.
├── ai/                      # Gemini integration, prompts, schemas, state and language logic
├── backend/                 # FastAPI app, webhook handling, stores and database helpers
│   └── migrations/           # SQL migrations
├── commandia-frontend/      # React + TypeScript + Vite dashboard
│   └── src/
│       ├── components/       # Shared interface components
│       ├── pages/            # Dashboard and public pages
│       ├── services/         # Frontend API / mock-data service
│       └── styles/           # Application styles
├── streamlit_sandbox/       # Standalone interactive demo
├── tests/                   # Automated Python test suite and golden data
├── app.py                   # Vercel entrypoint for the FastAPI application
├── Dockerfile               # Container build for the API service
├── requirements.txt         # Python runtime dependencies
├── requirements-dev.txt     # Python test dependencies
└── vercel.json              # Vercel service configuration
```

For AI-specific implementation notes, see [README_AI.md](README_AI.md). The frontend has its own [setup notes](commandia-frontend/README.md).

## Architecture

```text
Instagram / Facebook
        │ Meta webhook
        ▼
FastAPI service ───────► AI service (Gemini + Pydantic)
        │                         │
        ├── Conversation / order processing
        ├── Supabase persistence (optional)
        └── HTTP API ◄────────────┘
                │
                ▼
      React merchant dashboard
      (mock data by default)
```

The API is implemented in `backend/app.py`; `app.py` at the repository root exports the FastAPI application for Vercel.

## Getting started

### Prerequisites

- Python 3.10 or newer
- Node.js and npm for the React dashboard
- A Gemini API key to use live AI responses

### 1. Configure the Python service

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies and create your local environment file:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

```powershell
Copy-Item .env.example .env
```

Set at least `GEMINI_API_KEY` in `.env` for AI-powered conversations. The service can start without it, but AI processing will not be available. Meta and Supabase settings are optional for local development; configure them to enable their respective integrations.

### 2. Run the API

```bash
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Useful local endpoints:

| Endpoint | Method | Purpose |
| --- | --- | --- |
| `/healthz` | `GET` | Service and AI readiness |
| `/webhook` | `GET` | Meta webhook verification |
| `/webhook` | `POST` | Incoming Meta messaging events |
| `/chat` | `POST` | Protected development chat endpoint |
| `/api/orders` | `GET` | Dashboard order data |
| `/api/products` | `GET` | Dashboard product data |
| `/api/settings` | `GET` | Dashboard settings |

The `/chat` and `/api/*` endpoints require the `X-API-Key` header; set `COMMANDIA_API_KEY` on the server and send the matching key from a trusted client. The current React API layer does not attach this key, so its live backend mode is not ready to use as-is. Do not expose a server API key in browser code; use a properly authenticated server-side integration instead. The Meta webhook also requires the corresponding verification token and app secret for production use.

### 3. Run the dashboard

In another terminal:

```powershell
Set-Location commandia-frontend
npm ci
npm run dev
```

The dashboard is served by Vite, usually at `http://localhost:5173`. To create and preview a production build:

```bash
npm run build
npm run preview
```

By default, the dashboard uses local mock data. Setting `VITE_API_URL` switches its service layer to HTTP requests; the frontend API routes are currently proposals and are not all implemented by the backend. See [Current limitations](#current-limitations).

### Optional: Streamlit demo

The standalone simulator has its own dependencies:

```bash
python -m pip install -r streamlit_sandbox/requirements.txt
python -m streamlit run streamlit_sandbox/app.py
```

### Optional: Docker

Build and run the API container from the repository root:

```bash
docker build -t commandia-api .
docker run --rm -p 8000:8000 --env-file .env commandia-api
```

## Testing

Run the automated Python suite from the repository root:

```bash
pytest -q
```

The automated tests use the project’s test configuration and are intended for local validation. The following scripts are separate manual tools:

```bash
python -m backend.demo       # Interactive terminal conversation
python -m backend.test_ai    # Live AI check; requires a valid Gemini API key
python -m backend.emulator   # Signed Meta webhook emulator
```

## Configuration

Copy `.env.example` to `.env`; never commit real credentials. Main settings include:

| Variable group | Purpose |
| --- | --- |
| `GEMINI_*`, `MAX_RETRIES`, `RETRY_*` | AI provider, model selection, and retry behavior |
| `META_VERIFY_TOKEN`, `META_APP_SECRET`, `META_ACCESS_TOKEN` | Meta webhook verification and messaging |
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_*_TABLE` | Optional database persistence |
| `COMMANDIA_API_KEY` | Protects the development `/chat` endpoint |
| `DASHBOARD_ORIGIN`, `HOST`, `PORT` | API service and CORS configuration |
| `VITE_API_URL` | Optional frontend API base URL |

See [`.env.example`](.env.example) for the full list and setup comments.

## Deployment

The repository includes a `Dockerfile` for the FastAPI service and a `vercel.json` describing the API and frontend services. The frontend service root is `commandia-frontend`; the Python service uses the repository root and the root-level `app.py` entrypoint.

Before deploying, configure required secrets in the hosting provider rather than committing them. Set the production Meta callback URL, webhook verification token, app secret, access token, and allowed dashboard origin as appropriate. Supabase is optional and should use credentials with only the permissions the service needs.

## Current limitations

- The React dashboard defaults to seeded in-memory data. Authentication, billing, and several workflows are simulated.
- Frontend API paths are marked as proposed in `commandia-frontend/src/services/api.ts`; verify and align them with the backend before enabling `VITE_API_URL` in production.
- Live AI responses require a valid Gemini API key.
- Meta messaging and Supabase persistence require their respective credentials and provider-side setup.
- The Streamlit simulator is a separate demo application, not the production dashboard.

Do not treat the mock dashboard authentication as production security. Review authentication, authorization, data handling, and provider configuration before exposing the application to customers.

## Contributing

Contributions are welcome. For a useful change, include a concise description, note any configuration or migration impact, and run the relevant checks before opening a pull request.
