# 📴 Offline mode with sync queue

**Status:** ✅ 2026-08-05 · **Priority:** Low · **Effort:** L (3+ days) · **Dependencies:** 03-pwa ✅

## Why
The main use case is logging an expense on the spot: at the supermarket, on the street, with bad mobile data. Today, without a connection, the app simply fails and the expense gets forgotten. An offline queue makes capture reliable even when the network isn't; it's the natural next step after having an installable PWA.

## Scope
**Includes:**
- Outbox in IndexedDB: transactions created offline are saved locally with a "pending" status
- Automatic sync when back online (`online` listener + retry; Background Sync API where available)
- Persistent banner "Offline — N pending transactions" showing queue status
- Offline reading of the last data snapshot (persist the TanStack Query cache in localStorage)
- Simple conflict resolution: server-wins (transactions are append-only, collisions are rare)

**Excludes:**
- Offline editing of existing transactions (creation only)
- Syncing accounts/categories/goals (assumed stable; if missing, the upload fails and retries)
- Conflict resolution UI (not applicable with append-only + server-wins)
- Offline attachments (the scanner and attachments require network; only transaction data is queued)

## Proposed design

### Backend
- Idempotent sync endpoint: the client sends `client_id` (UUID generated on the device) with each transaction; the server stores it and rejects duplicates (unique constraint per household) to tolerate retries
- No business model changes beyond the nullable `client_id` on `transactions`
- Clear error response if the transaction references a nonexistent account/category (the client marks it as failed and reports it)

### Frontend
- Outbox in IndexedDB (`idb` or Dexie): `pending_mutations` table with `{ client_id, payload, created_at, attempts, last_error }`
- Interceptor in the mutations layer: if `navigator.onLine === false` or the POST fails due to a network error (not a 4xx), save it to the outbox and return an optimistic success
- Flush: on the `online` event, on regaining focus, and with a backup `setInterval`; each item is uploaded in order and deleted once confirmed with a 2xx
- Global banner: reads network status and the outbox count ("Offline — 3 pending transactions"); disappears once empty
- `persistQueryClient` (official TanStack Query plugin) with a localStorage persister: when opened offline, the last snapshot's data is shown with a "data from X ago" indicator
- Pending transactions appear in the feed with a "Pending upload" badge (optimistic UI from the outbox, not from the query cache)

### Infra
- No changes

## Acceptance criteria
- [x] One-time transactions entered offline are user-scoped IndexedDB entries with pending/error feed states and a global banner.
- [x] The queue flushes in order when online, focused, or on its interval; 4xx entries stay failed without blocking subsequent entries.
- [x] `clientId` has a household-scoped unique constraint and idempotent replay, including payload conflict and personal-account authorization checks.
- [x] Query snapshots persist per authenticated user and render an offline age indicator.
- [ ] Validate the airplane-mode round trip on a real installed mobile app.

## Notes
- Risk: rare service worker states combined with the outbox (e.g. SW serving an old shell with different sync logic). Test the PWA update flow together with the queue.
- `client_id` must be generated once per transaction and survive browser reloads (it lives in IndexedDB, not in memory).
- Open decision: the Background Sync API doesn't exist on Safari iOS; the `online` listener + focus fallback is sufficient for real-world use — document this.
- Don't attempt to sync attachments offline: the scanner flow is already inherently online (call to OpenRouter).
