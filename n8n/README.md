# Project Phantasm — n8n Workflow

This folder contains the importable n8n automation workflow for the Project
Phantasm zombie credential exorcist pipeline.

## Files

| File | Purpose |
| --- | --- |
| `phantasm_workflow.json` | Importable n8n workflow (15 nodes, 14 connections) |

## Pipeline overview

```
Webhook Trigger
   ↓
Payload Validation
   ↓
Data Preparation
   ↓
Gemini API Request (HTTP Request with retry)
   ↓
Gemini Response Parsing
   ↓
Threat Score Validation
   ↓
Risk Classification
   ↓
Conditional Branching (switch on category)
   ├── CRITICAL / HIGH → Human Approval Handling → Mock IAM Revocation
   └── MEDIUM / LOW   → Monitor Account
   ↓
Google Sheets Audit Logging
   ↓
Gmail Incident Notification
   ↓
Workflow Completion Response (returns JSON to caller)
```

An `Error Handling` node is wired so any pipeline failure is captured and
returned to the caller instead of dropping silently.

## 1. Install n8n locally (Docker)

```bash
docker volume create n8n_data
docker run -d --name n8n \
  -p 5679:5679 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_HOST=localhost \
  -e N8N_PORT=5679 \
  -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL=http://localhost:5679/ \
  docker.n8n.io/n8nio/n8n
```

Open <http://localhost:5679> and create your owner account on first launch.

Or use the bundled `docker-compose.yml` in the project root:

```bash
cd project-phantasm
docker compose up -d n8n
```

## 2. Import the workflow

1. In n8n, click **Workflows → Import from File**.
2. Select `phantasm_workflow.json` from this folder.
3. The workflow opens with all 15 nodes correctly wired.

## 4. Configure Gemini credentials

The `Gemini API Request` node uses two environment variables:

```bash
export GEMINI_API_KEY="YOUR_KEY"
export GEMINI_MODEL="gemini-2.5-flash"
```

Restart n8n after setting them (`docker restart n8n`).

Alternatively, replace the URL expression in the Gemini node with a static
key and use n8n's HTTP Request auth:

```text
URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
Query param: key = <YOUR_GEMINI_API_KEY>
```

## 5. Configure Google Sheets

1. Open <https://console.cloud.google.com/apis/credentials> and create an
   OAuth 2.0 Client ID (type: Web application).
2. Enable the **Google Sheets API** under APIs & Services.
3. Add `https://app.n8n.cloud/oauth/callback` (or your local n8n callback
   URL) to the authorised redirect URIs.
4. In n8n → **Credentials → Add credential → Google Sheets OAuth2 API**.
5. Paste the client ID and secret, complete the consent flow.
6. Create a new spreadsheet, copy its ID (the long string in the URL).
7. Open the imported `Google Sheets Audit Logging` node and select the
   credential. Set `Document ID` to your sheet ID.

## 6. Configure Gmail

1. In the same Google Cloud project, enable the **Gmail API**.
2. Add the Gmail scope `https://www.googleapis.com/auth/gmail.send` to the
   same OAuth client used for Sheets.
3. In n8n → **Credentials → Add credential → Gmail OAuth2 API**. Select the
   same OAuth client. Complete the consent flow.
4. Open the imported `Gmail Incident Notification` node and select the
   credential.
5. Set environment variables for the recipient:

   ```bash
   export GMAIL_SENDER="phantasm@your-domain.com"
   export GMAIL_RECIPIENT="security-team@your-domain.com"
   ```

## 7. Activate the workflow

1. In the n8n UI, click the **Active** toggle in the top-right corner.
2. Open the `Webhook Trigger` node. The **Production URL** is shown there,
   e.g. `http://localhost:5679/webhook/phantasm-exorcism`.
3. Copy that URL into the Python application via the **Settings →
   Integrations** page, or set `N8N_WEBHOOK_URL` in `backend/.env`.

## 8. Test the integration

From the Phantasm frontend:

1. Open **Settings → Integrations**.
2. Click **Test n8n connection**. You should see *“n8n webhook
   reachable”*.
3. Trigger any simulation scenario. The pipeline monitor will show
   *n8n notified* at the AUDIT_LEDGER step, and the executed workflow will
   appear in the n8n **Executions** view.

If the test fails with HTTP 404, the workflow is not yet **Active** or the
webhook path does not match `N8N_WEBHOOK_URL`. Re-check both and retry.

## Webhook payload schema

```jsonc
{
  "incident_id": "uuid",
  "user_id": "uuid",
  "telemetry": { "email": "...", "role": "...", "account_type": "...",
                 "last_active_days": 114, "accessed_resources": ["..."],
                 "failed_login_attempts": 14, "location_anomaly": true,
                 "privilege_level": "elevated" },
  "assessment": { "threat_score": 92, "risk_category": "CRITICAL",
                  "reasoning": "...", "risk_factors": ["..."],
                  "recommended_action": "REQUIRE_REVOCATION_APPROVAL",
                  "epitaph_summary": "...",
                  "assessment_source": "rules_engine|gemini",
                  "simulation_mode": true },
  "timestamp": "ISO-8601"
}
```

The response is:

```jsonc
{
  "incident_id": "...",
  "status": "completed",
  "classification": { "score": 92, "category": "CRITICAL", "recommended_action": "..." },
  "iam_action":    { "action": "REVOKED|PENDING_APPROVAL|FLAGGED|MONITORED", "timestamp": "..." },
  "timestamp": "..."
}
```
