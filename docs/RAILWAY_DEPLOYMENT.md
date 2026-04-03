# Railway Deployment + Keap OAuth Setup

## 1) Create Keap OAuth app
1. In Keap developer console, create an OAuth app.
2. Set redirect URI to your Railway public URL callback endpoint, e.g.:
   - `https://<your-service>.up.railway.app/oauth/callback`
3. Capture:
   - `KEAP_CLIENT_ID`
   - `KEAP_CLIENT_SECRET`

## 2) Configure Railway environment variables
Set these in Railway service variables:

- `KEAP_CLIENT_ID`
- `KEAP_CLIENT_SECRET`
- `KEAP_OAUTH_REDIRECT_URI`
- `KEAP_ACCESS_TOKEN` (optional initially; populated after first code exchange)
- `KEAP_REFRESH_TOKEN` (optional initially; populated after first code exchange)
- `MCP_TRANSPORT=streamable-http`
- `MCP_PATH=/mcp`

## 3) Deploy
Railway will use:

```bash
python run.py --host 0.0.0.0 --port ${PORT:-5000} --transport streamable-http --path /mcp
```

Health checks:
- `/` returns 200 JSON health payload (used by Railway default health check).
- `/health` returns 200 lightweight status.

## 4) Fully automatic connect flow (ChatGPT/Claude compatible)
Expose and use this URL for the connector login step:

- `https://<your-service>.up.railway.app/oauth/connect`

Flow:
1. User clicks **Connect** in ChatGPT/Claude.
2. Connector opens `/oauth/connect`.
3. Server redirects to Keap OAuth consent.
4. Keap redirects back to `/oauth/callback`.
5. Server exchanges code for tokens and stores them in `KEAP_OAUTH_TOKEN_FILE` (default: `keap_oauth_tokens.json`).

> Important: attach a Railway persistent volume if you want token storage to survive restarts/deploys.

## 5) Automatic refresh
When Keap returns `401`, the server attempts refresh token flow automatically using configured OAuth variables.
