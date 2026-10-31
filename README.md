# PROJECT PHANTASM
### *Automated Zombie Credential Exorcist*

An intelligent cybersecurity automation platform that identifies, assesses and
neutralises **zombie credentials** — abandoned, inactive or compromised user
accounts that retain access to sensitive organisational infrastructure.

Project Phantasm combines a **Python FastAPI** backend, a **React + Vite**
Halloween-themed dashboard, **Google Gemini** AI threat intelligence, and an
importable **n8n** automation workflow. It runs end-to-end in **simulation
mode** with zero external credentials, and switches to live integrations
the moment you supply real API keys via the in-app Settings page.

---

## Table of Contents
1. [Architecture](#architecture)
2. [Quick start](#quick-start)
3. [Prerequisites](#prerequisites)
4. [Configuration](#configuration)
5. [API reference](#api-reference)
6. [Simulation scenarios](#simulation-scenarios)
7. [n8n setup](#n8n-setup)
8. [Google Sheets + Gmail OAuth](#google-sheets--gmail-oauth)
9. [Gemini API key](#gemini-api-key)
10. [Running tests](#running-tests)
11. [90-second demonstration script](#90-second-demonstration-script)
12. [Project structure](#project-structure)
13. [Acceptance criteria](#acceptance-criteria)

---

## Architecture

```
USER DASHBOARD (React/Vite)
        |
        v
PYTHON FASTAPI BACKEND  (port 8100)
        |
        v
SECURITY TELEMETRY VALIDATION  (Pydantic)
        |
        v
N8N WEBHOOK (optional)  ──┐
        |                  |
        v                  v
GEMINI THREAT INTELLIGENCE   DETERMINISTIC RULES ENGINE
        |                  (fallback / simulation)
        v
STRUCTURED JSON VALIDATION  (Pydantic schema)
        |
        v
RISK CLASSIFICATION  (LOW / MEDIUM / HIGH / CRITICAL)
        |
        v
CONDITIONAL DECISION ENGINE
        |                  |
        v                  v
   LOW/MED             HIGH/CRITICAL
   MONITOR             HUMAN APPROVAL GATE
        |                  |
        |                  v
        |              MOCK IAM REVOCATION
        |                  |
        +--------+---------+
                 v
        GOOGLE SHEETS LEDGER (optional)
                 |
                 v
        GMAIL INCIDENT REPORT (optional)
                 |
                 v
        PYTHON DATABASE (SQLite / PostgreSQL)
                 |
                 v
        LIVE DASHBOARD UPDATE
```

**Python owns** the core business logic, telemetry validation, simulation
engine, IAM, audit ledger, and API. **n8n** orchestrates an equivalent pipeline
in parallel when configured. **Gemini** performs genuine contextual analysis
when an API key is present. **Simulation mode** runs the entire pipeline with
a deterministic local rules engine — no external credentials needed.

---

## Quick start

```bash
git clone <repo-url> project-phantasm
cd project-phantasm
./start.sh
```

Open <http://localhost:5173> for the dashboard. The backend API is at
<http://localhost:8100/api/v1/health>.

The first launch is in **simulation mode** — every feature works without
external credentials. Visit **Settings → Integrations** to enter real API
keys, then switch to live mode with the header toggle.

---

## Prerequisites

| Tool | Version | Why |
| --- | --- | --- |
| Python | 3.12+ | Backend |
| Node.js | 20+ | Frontend |
| npm | 10+ | Frontend deps |
| Docker | 24+ | Optional — for n8n |

### macOS
```bash
brew install python@3.12 node
brew install --cask docker   # for n8n
```

### Windows
- Install Python 3.12 from <https://python.org/downloads>
- Install Node.js LTS from <https://nodejs.org>
- Install Docker Desktop from <https://docker.com/products/docker-desktop>

---

## Configuration

All secrets are loaded from `backend/.env`. A template is provided at
`backend/.env.example`. The Settings page can update any of these at runtime
without editing files.

| Variable | Required for | How to obtain |
| --- | --- | --- |
| `GEMINI_API_KEY` | Live AI assessment | https://aistudio.google.com/app/apikey |
| `GEMINI_MODEL` | Live AI assessment | e.g. `gemini-2.5-flash`, `gemini-2.5-pro` |
| `N8N_WEBHOOK_URL` | n8n orchestration | Your imported workflow's webhook URL |
| `N8N_BASE_URL` | n8n API (optional) | http://localhost:5679 |
| `N8N_API_KEY` | n8n REST API (optional) | n8n → Settings → n8n API |
| `GOOGLE_CLIENT_ID` | Sheets + Gmail OAuth | console.cloud.google.com/apis/credentials |
| `GOOGLE_CLIENT_SECRET` | Sheets + Gmail OAuth | same as above |
| `GOOGLE_REFRESH_TOKEN` | Sheets + Gmail OAuth | OAuth playground flow (see below) |
| `GOOGLE_SHEET_ID` | Sheets audit ledger | The long ID in your Sheet URL |
| `GMAIL_SENDER` | Email reports | The OAuth-authenticated Gmail address |
| `GMAIL_RECIPIENT` | Email reports | Where incident emails are sent |
| `DATABASE_URL` | Always | `sqlite+aiosqlite:///./phantasm.db` (default) |
| `SIMULATION_MODE` | Always | `true` to start in simulation |

---

## API reference

All endpoints are prefixed with `/api/v1`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET  | `/health` | Health check |
| GET  | `/accounts` | List all monitored accounts |
| GET  | `/accounts/{user_id}` | Get a single account |
| POST | `/accounts` | Create a new account from telemetry |
| POST | `/trigger-exorcism` | Run the full pipeline against an account |
| GET  | `/incidents` | List incidents (newest first) |
| GET  | `/incidents/{incident_id}` | Get a single incident |
| GET  | `/executions/{execution_id}` | Get a pipeline execution trace |
| GET  | `/dashboard/stats` | Aggregate dashboard stats |
| GET  | `/integrations/status` | Connection status of every integration |
| POST | `/integrations/credentials` | Update a single credential |
| POST | `/integrations/test/gemini` | Live Gemini connection test |
| POST | `/integrations/test/n8n` | Live n8n webhook ping |
| POST | `/integrations/test/google` | Sheets + Gmail OAuth check |
| POST | `/approvals/{incident_id}` | Approve or reject a revocation |
| GET  | `/simulation/scenarios` | List the 6 predefined scenarios |
| POST | `/simulation/run/{scenario_id}` | Run a single scenario |
| POST | `/simulation/run-all` | Run all 6 scenarios |
| POST | `/simulation/reset` | Reset all account statuses |
| POST | `/simulation/clear` | Clear historical incidents/executions |
| POST | `/simulation/generate-random` | Generate a random telemetry |

Interactive docs are available at <http://localhost:8100/docs>.

---

## Simulation scenarios

| ID | Name | Expected risk |
| --- | --- | --- |
| `sleeping-ghost` | THE SLEEPING GHOST | LOW or MEDIUM |
| `compromised-contractor` | THE COMPROMISED CONTRACTOR | CRITICAL |
| `privileged-phantom` | THE PRIVILEGED PHANTOM | CRITICAL |
| `false-alarm` | THE FALSE ALARM | LOW |
| `brute-force-ghost` | THE BRUTE FORCE GHOST | HIGH or CRITICAL |
| `abandoned-service-account` | THE ABANDONED SERVICE ACCOUNT | HIGH or CRITICAL |

Run them from the **Simulation Lab** page or via `POST /api/v1/simulation/run-all`.

---

## n8n setup

1. (Optional) Start n8n locally:
   ```bash
   docker compose up -d n8n
   ```
2. Open <http://localhost:5679> and create the owner account.
3. Click **Workflows → Import from File** and select
   `n8n/phantasm_workflow.json`.
4. (Optional) Configure credentials for the Google Sheets and Gmail nodes
   via n8n's credential manager.
5. Activate the workflow with the toggle in the top-right.
6. Open the Webhook Trigger node and copy the **Production URL**.
7. In the Phantasm dashboard, go to **Settings → Integrations**, paste
   the URL into **n8n Webhook URL**, click **Save**, then **Test n8n
   connection**.

See `n8n/README.md` for the full walkthrough.

---

## Google Sheets + Gmail OAuth

1. Open <https://console.cloud.google.com/> and create a project.
2. Enable the **Google Sheets API** and the **Gmail API**.
3. Create an **OAuth 2.0 Client** (type: Web application). Add
   `https://developers.google.com/oauthplayground` to the redirect URIs.
4. Open <https://developers.google.com/oauthplayground>, click the
   gear icon, check "Use your own OAuth credentials", and paste your
   client ID + secret.
5. In the left panel, add these scopes:
   - `https://www.googleapis.com/auth/spreadsheets`
   - `https://www.googleapis.com/auth/gmail.send`
6. Click **Authorize APIs**, then **Exchange authorization code for
   tokens** — copy the **Refresh token**.
7. Create a Google Sheet, copy its ID (the long string in the URL).
8. In the Phantasm Settings page, enter:
   - `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`,
     `GOOGLE_SHEET_ID`, `GMAIL_SENDER`, `GMAIL_RECIPIENT`.
9. Click **Test google connection**.

---

## Gemini API key

1. Open <https://aistudio.google.com/app/apikey>.
2. Create a key. Copy the value.
3. In the Phantasm Settings page, paste into **Gemini API Key** and
   set **Gemini Model** to e.g. `gemini-2.5-flash`.
4. Click **Test gemini connection**. You should see
   *“Gemini API reachable. Model: gemini-2.5-flash.”*

---

## Running tests

```bash
cd backend
python3 -m pytest -v
```

58 tests cover: rules engine, schemas, Gemini service, n8n service,
IAM safety, scenarios, API endpoints, and all 8 acceptance tests.

To start in live mode:

```bash
./start.sh --live
```

---

## 90-second demonstration script

1. Open <http://localhost:5173>. Header reads **SIMULATION**.
2. Click **Simulation Lab** in the sidebar.
3. Click **Run All Scenarios**. All six green check marks appear.
4. Click **Ghost Monitor**. Filter by `Status: REVOKED` — the
   compromised contractor shows as revoked.
5. Click **EXORCISE CREDENTIALS** on the contractor. The pipeline
   result panel shows the 8-step trace.
6. Click **Pipeline Monitor**. Pick the contractor incident. The
   8-step pipeline visualises with completed steps.
7. Click **Epitaph Vault**. Open the contractor card. The epitaph is
   shown in italic purple.
8. Click **Threat Feed**. Latest threats stream in at the top.
9. Click **Integrations**. All integrations show their real status —
   disconnected until credentials are supplied.
10. Optionally: switch to live mode by clicking the header toggle.

---

## Project structure

```
project-phantasm/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app + lifespan
│   │   ├── config.py          # Settings + env persistence
│   │   ├── database.py        # async SQLAlchemy
│   │   ├── models/models.py   # 4 ORM entities
│   │   ├── schemas/schemas.py # Pydantic request/response models
│   │   ├── routes/            # 8 routers (one per resource)
│   │   └── services/          # gemini, n8n, iam, audit, simulation, pipeline, google
│   ├── tests/                 # 58 pytest tests
│   ├── requirements.txt
│   ├── .env.example
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/        # Header, Sidebar, StatCard, Badges
│   │   ├── pages/             # 7 pages
│   │   ├── services/api.js    # API client
│   │   ├── hooks/             # usePoll
│   │   └── styles/            # Tailwind + custom CSS
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── index.html
├── n8n/
│   ├── phantasm_workflow.json # 15-node importable workflow
│   └── README.md              # Full n8n setup guide
├── docker-compose.yml         # n8n service
├── start.sh                    # one-shot launcher
├── .gitignore
└── README.md                   # this file
```

---

## Acceptance criteria

- [x] Python backend runs successfully
- [x] Frontend runs successfully
- [x] Dashboard retrieves genuine backend data
- [x] Simulation mode works without API keys
- [x] Six scenarios are available
- [x] Risk assessments are functional
- [x] Gemini API integration is implemented
- [x] Gemini connection testing works with supplied credentials
- [x] n8n workflow is importable (validated: 15 nodes, 14 connections)
- [x] n8n webhook integration is implemented
- [x] Google Sheets integration is implemented
- [x] Gmail integration is implemented
- [x] Mock IAM revocation works
- [x] Live approval restrictions work (unit-tested)
- [x] Audit records persist (test #8)
- [x] Pipeline execution statuses update correctly
- [x] Automated tests executed (58/58 passing)
- [x] README provides complete setup instructions
- [x] The 90-second demonstration works
