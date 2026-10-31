# CommandIA frontend (React + TypeScript + Vite)

Working frontend for the CommandIA design: public website, demo authentication, onboarding and the dashboard
(Overview, Smart Inbox with Human Takeover, Orders, Product Catalog, Business Rules, AI Settings, Integrations).

## Run
```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production build
npm run preview
```

## Structure
- `src/services/api.ts` is the only place that talks to a backend. Without `VITE_API_URL` it serves in-memory mock data
  (`src/data/seed.json`). With `VITE_API_URL=http://localhost:8000` it calls the FastAPI backend with `fetch`.
  The route paths in that file are proposals and have not been verified against the backend: adjust them there only.
- `src/store.tsx` holds app state (auth, conversations, orders, products, global AI, Instagram) and calls the service layer.
- `src/pages/` one file per area, `src/components/` shared UI (Inbox thread, layout shell, icons, modal).
- `src/styles/app.css` is the design stylesheet carried over from the approved prototype (brand colors, Poppins, spacing).

## Routes
Public: `/`, `/features`, `/how-it-works`, `/pricing`, `/faq`, `/signin`, `/signup`.
Authenticated: `/onboarding`, `/app`, `/app/inbox[/:id]`, `/app/orders[/:id]`, `/app/catalog`, `/app/rules`, `/app/ai-settings`, `/app/integrations`.

## Still simulated
Authentication (token kept in localStorage), Instagram connection, billing/pricing, order creation, and the
"Simulate a failure" switch in the takeover dialog (mock layer only). Nothing here is production-ready security.
