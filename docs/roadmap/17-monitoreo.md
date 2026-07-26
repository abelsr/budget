# 📡 Monitoring and alerts

**Status:** ⬜ Pending · **Priority:** Low · **Effort:** S (<1 day) · **Dependencies:** 15-https-caddy (only if monitoring is external, like Better Stack; local Uptime Kuma doesn't need it)

## Why
This is a self-hosted system used by real people: if the backend dies on a Friday, nobody finds out until someone tries to log an expense. Also, attachments grow in the MinIO volume with no apparent limit, and a full disk brings Postgres down. A minimum of structured logs and two alerts (downtime, disk) covers 90% of the likely disasters.

## Scope
**Includes:**
- Structured JSON logs in the backend (uvicorn + logging configuration) with a `request_id` per request
- External healthcheck over `/health`: self-hosted Uptime Kuma (recommended, same host) or Better Stack free tier
- Host disk alert at > 85% (Postgres and MinIO volumes grow with attachments)
- Minimal uptime dashboard (whichever the chosen tool provides)

**Excludes:**
- Application metrics (Prometheus/Grafana, APM): overkill at this scale
- Business alerts (5xx errors per minute, p95 latency)
- Centralized logging across all containers (Loki and similar)
- OpenRouter cost monitoring

## Proposed design

### Backend
- JSON logging configuration: custom formatter or `python-json-logger`, applied to uvicorn (`--log-config` or dictConfig in `main.py`)
- `request_id` middleware: generate a UUID per request, inject it into the logging context, and return it in the `X-Request-ID` header (makes it easier to correlate "the user says it failed" with the exact log entry)
- Verify that `/health` exists and is lightweight (no heavy queries); if it doesn't exist, create it: 200 with `{ "status": "ok" }` and a basic DB check
- INFO level in production, DEBUG via environment variable

### Frontend
- No changes

### Infra
- **Recommended option:** an `uptime-kuma` service in the same compose (image `louislam/uptime-kuma`), HTTP monitor against `http://backend:8000/health` every 60s, notification via Telegram/Discord/email (Kuma supports all of these without needing to configure your own SMTP)
- **External option:** Better Stack free tier pointing at `https://finanzas.dominio.com/health` (requires 15); useful because it alerts even if the whole host dies, not just the backend
- Disk alert: a cron script on the host (`df /` + webhook to Telegram/ntfy), since Uptime Kuma itself doesn't cover this — the script is simple and sufficient
- Document in the README: where to view the Kuma dashboard (port 3001, ideally LAN-only or behind Tailscale) and what to do when each alert arrives

## Acceptance criteria
- [ ] `docker compose stop backend` generates an alert received within 5 minutes
- [ ] Backend logs are output in JSON with `request_id`, method, path, status, and duration
- [ ] A response's `X-Request-ID` header appears in that request's logs
- [ ] An alert is configured for host disk > 85% (tested manually by lowering the threshold)
- [ ] The uptime dashboard shows at least a week of history after running for a week

## Notes
- Open decision: local Uptime Kuma alerts on everything except the whole host dying (if the host goes down, Kuma goes down too). That's what the external option is for; ideally it's local Kuma + Better Stack free as a safety net, both are cheap to run.
- Minor risk: JSON logs with sensitive data. Make sure not to log request bodies (tokens and amounts aren't state secrets, but there's no need to write them either); log only metadata.
- The disk threshold (85%) assumes volumes are on the root disk; if `pgdata` or MinIO live on a different mount, point the check there instead.
- References: https://github.com/louislam/uptime-kuma · https://betterstack.com/uptime
