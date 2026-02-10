# Web UI

React 18 single-page application served via Nginx reverse proxy on port **8080**. Provides a dark-themed dashboard for managing incidents, viewing alerts, on-call schedules, notifications, and AI-powered root-cause suggestions. Nginx also acts as the API gateway, proxying requests to all backend microservices.

<p align="center">
  <img src="images/CriticalIncident.webp" alt="Incident Dashboard" width="700"/>
</p>

## Tech Stack

| Category | Technology |
| :--- | :--- |
| Framework | React 18.3 + Vite 7.3 (ESM) |
| Routing | react-router-dom 6.22 |
| Data Fetching | @tanstack/react-query 5.90 + axios 1.6 |
| Styling | Tailwind CSS 4.1 (dark theme) |
| UI Primitives | Radix UI (dialog, select, tabs, tooltip, switch, popover, etc.) |
| Icons | lucide-react |
| Charts | recharts 3.7 |
| Utilities | date-fns 3.6, clsx, tailwind-merge, class-variance-authority |

## Pages / Routes

| Route | Page | Description |
| :--- | :--- | :--- |
| `/login` | Login | Credential login (demo: `admin`/`admin`), session stored in `sessionStorage` |
| `/` | Dashboard | Real-time overview — stat cards, recent incidents, recent alerts, service health |
| `/incidents` | Incidents | Filterable, paginated incident list with inline Acknowledge / Resolve actions |
| `/incidents/:id` | IncidentDetail | Full detail view — AI suggestions panel, notes/timeline, linked alerts, metrics |
| `/alerts` | Alerts | Filterable alert list with correlation status badges |
| `/analytics` | Analytics | Charts: severity/status pie, incidents-by-service bar, KPI cards (MTTA/MTTR) |
| `/oncall` | OnCall | Current on-call per team, rotation schedules, on-call metrics |
| `/notifications` | Notifications | Searchable notification feed with channel icons and delivery status |
| `*` | NotFound | 404 page |

All routes except `/login` are protected via the `useAuth` hook.

## API Integration

The frontend communicates with backend services through Nginx proxy paths:

| Proxy Path | Upstream Service | Key Endpoints |
| :--- | :--- | :--- |
| `/api/alert-ingestion/` | alert-ingestion:8001 | `GET /alerts`, `GET /metrics` |
| `/api/incident-management/` | incident-management:8002 | `GET/PATCH /incidents`, `GET /incidents/analytics` |
| `/api/oncall-service/` | oncall-service:8003 | `GET /schedules`, `GET /oncall/current` |
| `/api/notification-service/` | notification-service:8004 | `GET /notifications` |
| `/api/ai-analysis/` | ai-analysis:8005 | `GET /suggestions`, `POST /analyze`, `GET /knowledge-base` |
| `/ws/` | incident-management:8002 | WebSocket for live incident updates |

Data auto-refreshes every 15–30 seconds via React Query.

## Nginx Configuration

Nginx listens on port 8080 and serves three roles:

1. **SPA host** — serves the Vite-built static assets with `try_files` fallback to `index.html`
2. **API gateway** — reverse-proxies `/api/{service}/` to the corresponding backend container
3. **Health endpoint** — `/health` returns `{"status":"healthy","service":"web-ui","version":"1.0.0"}` for Docker health checks

WebSocket support is configured for `/ws/` with 86400s timeouts.

## Docker Build

Multi-stage Dockerfile:

1. **Stage 1 (builder)** — `node:20-alpine`: `npm ci` → `npm run build` (Vite production build)
2. **Stage 2 (runtime)** — `nginx:1.25-alpine`: copies custom `nginx.conf` + built assets, removes setuid/setgid binaries for security, runs as non-root `nginx` user

Exposes port **8080**. Health check: `wget --spider http://localhost:8080/`.

## Key Features

| Feature | Description |
| :--- | :--- |
| **Dark Theme** | Full dark mode with zinc/slate palette, shimmer loading states |
| **Live Dashboard** | Open/acknowledged/resolved counts, MTTA/MTTR gauges, service health |
| **Incident Lifecycle** | List → detail → acknowledge → resolve, with notes timeline |
| **AI Suggestions** | Per-incident AI suggestions panel (root cause, solution, confidence, source) |
| **Alert Correlation** | Correlation status badges, noise-reduction percentage from Prometheus metrics |
| **On-Call Display** | Current primary/secondary per team, rotation schedules table |
| **Analytics Charts** | Severity/status pie charts, incidents-by-service bar, KPI cards |
| **Notifications Feed** | Channel icons (email/slack/webhook/sms) with delivery status |
| **Authentication** | Session-based login with protected routes |

## Component Architecture

```text
App.jsx
├── Sidebar            Fixed 240px left nav with "ExpertMind" branding
├── ProtectedRoute     Auth guard (useAuth hook + sessionStorage)
├── pages/
│   ├── Dashboard      Stat cards, recent incidents/alerts, service health
│   ├── Incidents      Filter bar, paginated table, bulk actions
│   ├── IncidentDetail AI panel, notes, linked alerts, timeline
│   ├── Alerts         Filter bar, correlation badges
│   ├── Analytics      Recharts visualizations, KPI cards
│   ├── OnCall         On-call cards, schedules table
│   └── Notifications  Search + filter, notification feed
├── components/ui/     shadcn/ui primitives (badge, button, card, table, etc.)
├── services/api.js    All backend API calls via axios
├── hooks/useAuth.js   Auth context provider
└── utils/formatters.js  Date/severity/status formatting helpers
```

## Screenshots

<p align="center">
  <img src="images/analytic.webp" alt="Analytics Dashboard" width="700"/>
</p>

<p align="center">
  <img src="images/OnCall.webp" alt="On-Call Schedule" width="700"/>
</p>
