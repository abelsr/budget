# UI/UX Reference Alignment Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align the authenticated budget interface with `docs/brand/pantallas-referencia.png` while preserving the existing API-backed workflows.

**Architecture:** Keep the current React routes and query hooks, but reshape the shared shell and dashboard into the reference information architecture. Reuse the existing transaction and scanner mutations; only change their responsive presentation so desktop and mobile reflect the supplied screens.

**Tech Stack:** React 19, TypeScript, React Router, Tailwind CSS 4, Motion, Recharts, Lucide.

---

## Chunk 1: Shared Navigation And Desktop Dashboard

### Task 1: Reference app shell

**Files:**
- Modify: `frontend/src/components/layout/AppShell.tsx`
- Modify: `frontend/src/components/AddTransactionSheet.tsx`

- [x] Replace the desktop shell with the reference sidebar: mark, six navigation entries, household switcher, and member profile area.
- [x] Add desktop-only header actions for notifications and `+ Registrar`; retain the mobile floating action.
- [x] Keep Categories routed under settings until a reports route exists; do not render dead links.
- [x] Build with `npm run build`.

### Task 2: Reference dashboard composition

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/index.css`

- [x] Recompose the dashboard into balance trend, per-account list, income-versus-expense bars, category donut, recent movements, and ticket-scanner card.
- [x] Preserve live account, summary, category, member, and transaction data from existing hooks.
- [x] Make the mobile order match the reference: greeting/title, balance, accounts, monthly flow, then bottom navigation.
- [x] Use the existing semantic tokens and responsive breakpoints; do not introduce raw component-level colors.
- [x] Build with `npm run build` and visually inspect desktop and 390px mobile.

## Chunk 2: Mobile Workflows And Settings

### Task 3: Movement list and quick-entry presentation

**Files:**
- Modify: `frontend/src/pages/TransactionsPage.tsx`
- Modify: `frontend/src/components/AddTransactionSheet.tsx`

- [x] Add the reference search and filter affordances to the movements header without claiming server-side filtering until the API supports it.
- [x] Restyle quick entry as the reference form: full-height mobile sheet, title/close control, segmented type selector, value, selectable category/account rows, date and note, pinned save button.
- [x] Retain repeat and attachment functionality as secondary fields rather than removing behavior.
- [x] Build with `npm run build`.

### Task 4: Scanner and settings presentation

**Files:**
- Modify: `frontend/src/components/TicketScanner.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [x] Present the ticket picker, camera, analysis and review flow as a full-height mobile experience while retaining the existing image/camera and API analysis behavior.
- [x] Rework Settings into the reference list structure: profile, account placeholder, household members, categories, preferences, currency, and sign-out.
- [x] Do not add unsupported profile/password mutations; make the account entry non-destructive until those endpoints are built.
- [x] Build with `npm run build`, run a browser console check, and inspect 390px mobile.

## Chunk 3: Verification

### Task 5: End-to-end visual verification

**Files:**
- No source changes expected.

- [x] Run `npm run build` and `npm run lint` from `frontend/`.
- [x] Inspect desktop at 1536px and mobile at 390px through the running Docker frontend.
- [x] Confirm no console errors on public, login, and reachable authenticated flows.
- [x] Report remaining intentional gaps: reports page and server-side movement filtering.
