# 🔒 HTTPS with Caddy

**Status:** ⬜ Pending · **Priority:** High · **Effort:** S (<1 day) · **Dependencies:** None (unblocks 03-pwa in production and 14-multi-familia)

## Why
Current access is over a local IP on plain HTTP: JWT credentials and financial data travel unencrypted, and service workers (PWA) require a secure context. Also, any future opening to the internet (multi-family, external monitoring) requires TLS. This is the infrastructure piece with the best effort/impact ratio in the whole roadmap.

## Scope
**Includes:**
- Caddy as a reverse proxy in front of the compose stack with automatic Let's Encrypt certificates
- 80→443 redirect and security headers (HSTS, X-Content-Type-Options, etc.)
- Documented alternative route for LAN use without a public domain: Tailscale (HTTPS on the tailnet) or mkcert (local CA)
- Harden secrets: `JWT_SECRET` of at least 32 random bytes
- Update backend CORS to the real domain

**Excludes:**
- Proxy-level authentication (Caddy/basic-auth in front of the app)
- Automatic secret rotation or management with Vault/similar
- Internal certificates between compose services (the internal Docker network stays on HTTP)

## Proposed design

### Backend
- `settings.cors_origins`: from the current value to the real domain (`https://finanzas.dominio.com`)
- Validate at startup that `JWT_SECRET` has >= 32 bytes; fail loudly if not (better to crash than run insecurely)
- Generate the new secret: `openssl rand -hex 32` → `.env` (invalidates existing tokens, acceptable: users re-login)

### Frontend
- No code changes; verify the build doesn't assume `http://` anywhere (nginx's `/api` proxy makes it agnostic)

### Infra
- `caddy` service in `docker-compose.yml` with the `caddy:2` image, ports 80/443 published, `caddy_data` and `caddy_config` volumes (certificate persistence)
- Minimal `Caddyfile`:
  ```
  finanzas.dominio.com {
      reverse_proxy frontend:80
      encode zstd gzip
      header {
          Strict-Transport-Security "max-age=31536000; includeSubDomains"
          X-Content-Type-Options "nosniff"
          X-Frame-Options "DENY"
          Referrer-Policy "strict-origin-when-cross-origin"
      }
  }
  ```
  (the `/api` proxy is already handled by the frontend's nginx; Caddy only points to the frontend)
- DNS: an A record for the domain pointing to the host; ports 80/443 open on the router/firewall
- LAN route documented in the README: option A) Tailscale on the host + `tailscale cert` for HTTPS at `https://host.tailnet.ts.net`; option B) mkcert with the CA installed on the family's devices; both avoid exposing anything to the internet
- Document in the README: the full flow with a real domain and the LAN flow, and how to verify automatic renewal

## Acceptance criteria
- [ ] `https://finanzas.dominio.com` loads with a valid lock icon (real Let's Encrypt certificate)
- [ ] `http://` redirects to `https://` (301)
- [ ] The app works the same over HTTPS: login, AI scanner, and attachment upload/download included
- [ ] Security headers are present (verifiable with securityheaders.com or curl)
- [ ] The backend only starts with a `JWT_SECRET` >= 32 bytes and rejects a weak one
- [ ] README documents both the domain route and the LAN route (Tailscale/mkcert)

## Notes
- Let's Encrypt requires the domain to resolve to the host and port 80 to be reachable for the HTTP-01 challenge; if the host is behind CGNAT (common with residential ISPs), the LAN route with Tailscale is the only viable one — document this clearly to avoid frustrating the user.
- Risk: forgetting to persist `caddy_data` and hitting Let's Encrypt's rate limit on every container restart. The volume is mandatory, not optional.
- Changing `JWT_SECRET` invalidates all active sessions: do it only once and let users (the family) know they'll need to re-login.
- Reference: https://caddyserver.com/docs/quick-starts/reverse-proxy
