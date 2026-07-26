# 🌐 Opening up to multiple families

**Status:** ⬜ Pending · **Priority:** Low · **Effort:** L (3+ days) · **Dependencies:** 01-alembic ✅ (done), 15-https-caddy (HTTPS mandatory before exposing auth to the internet)

## Why
Today the app serves a single family per deployment, accessed via local IP. Opening up public signup turns the project into a product that any family can use without the dev's involvement. This means hardening the surface exposed to the internet: rate limiting, anti-abuse measures, legal minimums. It's a security posture change, not just a new endpoint.

## Scope
**Includes:**
- Public signup: anyone can create their account and household in a single flow (the current register endpoint already creates its own household; exposing it without restriction)
- Basic rate limiting on auth endpoints (register, login, join)
- Email verification: decision documented below (recommended: use an external service or defer it)
- Anti-abuse limits: maximum active invitations per household, maximum members per household
- Minimal privacy page (what data is stored, where, who sees it)
- Telemetry: none, or explicit opt-in (recommended: none at first)

**Excludes:**
- Password recovery via email (depends on verification; can be a later phase)
- Social login (Google/Apple)
- Paid plans, billing, or commercial limits
- Instance admin panel (banning users, metrics)

## Proposed design

### Backend
- `slowapi` (or custom middleware) for rate limiting: e.g. 5 registrations/hour/IP, 10 logins/min/IP, limits on `/invitations`
- Business limits in configuration: `MAX_MEMBERS_PER_HOUSEHOLD`, `MAX_ACTIVE_INVITATIONS_PER_HOUSEHOLD` (reasonable values, e.g. 10 and 5)
- Email verification — **decision:** start WITHOUT mandatory verification but with the `email_verified` field in the model from the start; once activated, integrate Resend (or SES) with a `POST /auth/verify` endpoint and a soft block (reminder, not a hard blocker) initially. Rationale: adding transactional email is another infra dependency and another secret; the real anti-abuse value at the start comes from rate limiting
- `GET /legal/privacy` endpoint served as static content or a frontend page
- Tests: rate limit returns 429, invitation limits are respected, two households registered through the public flow remain isolated from each other

### Frontend
- Public signup page (today the register page may be hidden): clear copy like "create your family's household"
- Status screens for email verification (once activated)
- `/privacy` page accessible from the footer and from signup
- Readable error messages for 429 ("too many attempts, wait a few minutes")

### Infra
- HTTPS active (15) before opening up registration: auth without TLS on the internet is unacceptable
- New variables in the backend `.env`: limits, and email provider credentials if verification is activated
- Backups of the `pgdata` volume become critical (no longer just your own data): document at least one scheduled `pg_dump`
- Hosting decision: the public instance can live on the same host or on a cheap VPS; document minimum requirements

## Acceptance criteria
- [ ] A deployed public instance lets two real families register and use the app without seeing each other's data
- [ ] Rate limiting blocks a mass-registration script (429 after the limit)
- [ ] Member and invitation limits per household are enforced and return a clear error
- [ ] A privacy page exists and is accessible without login
- [ ] The whole flow runs over HTTPS with CORS restricted to the public domain

## Notes
- Bigger risk: opening auth to the internet multiplies the attack surface. Before this file, review: strength of `JWT_SECRET`, token expiration, that there are no accidentally unauthenticated endpoints, and that the AI scanner can't be abused as an OpenRouter proxy (rate limit there too).
- OpenRouter costs become third-party usage costs: consider a limit on scans per household/day, or leave the scanner as an opt-in feature with the user's own API key.
- Open decision: a public instance managed by the dev, or just "self-hostable by others"? The scope assumes a dev-managed public instance; if it were self-host only, most of this file reduces to documentation.
- Without telemetry there's no way to detect passive abuse: at minimum, logs (17-monitoreo) should be active on the public instance.
