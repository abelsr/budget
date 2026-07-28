# Design guidelines — budget

> The design system of record for the app. Tokens live in
> `frontend/src/index.css`; this document explains **what each token means and
> when to use it**, so a new screen can be built without inventing values.
>
> Last updated: 2026-07-27 · Supersedes the *Design language* section of
> [plan.md](plan.md), which now links here.

## 0. What changed and why

The app shipped with an **iOS system palette** (`#007aff`, `#f2f2f7`) while the
brand identity is a **blue-first mark** (`#2563EB`). Two blues in one product is
a bug, not a style. This revision:

- keeps every **interaction** principle from the Apple Design language
  (springs, translucent materials, pointer-down feedback, interruptibility) —
  they are about *behaviour* and were never the problem;
- replaces the **colour** layer with the brand system, so the isotipo, the
  splash, the CTA and the primary chart series are literally the same blue;
- adds the layer that did not exist: a **validated data-visualisation
  palette**, because a finance app is mostly charts and category colours were
  being hand-picked;
- restates the dashboard as an **information hierarchy** (four questions in
  order) rather than a bag of cards.

**Non-goals.** No new component library, no rounded-everything restyle, no
motion changes. `springs.ts` stands as-is.

---

## 1. Brand foundation

From the brand sheet ([`brand/imagen-de-marca.png`](brand/imagen-de-marca.png)):

| Role | Hex | Use |
|---|---|---|
| Azul principal | `#2563EB` | primary actions, active state, series slot 1 |
| Azul oscuro | `#1D4ED8` | pressed/hover of primary, gradient end |
| Azul claro | `#93C5FD` | on-blue accents, decorative strokes over blue surfaces |
| Fondo | `#EFF6FF` | light-mode page plane |
| Texto | `#0F172A` | light-mode primary ink |

The isotipo (a "b" whose counter holds a bar chart) means *growth, control,
clarity*. Two consequences for the UI:

1. **Blue is the app's voice, not its decoration.** Blue marks what the user can
   act on and what the product is confident about. It is never used for a
   surface just to look branded.
2. **Bars and charts are brand assets.** Chart quality is brand quality — hence
   §4 is a hard spec, not a suggestion.

Logo usage: isotipo alone at ≤32px (nav, favicon, avatars), isólogo elsewhere.
Clear space around the mark = 25% of its width. Never re-colour the mark, never
place the blue-gradient version on a blue surface (use the white-outline
variant from the brand sheet).

---

## 2. Semantic colour tokens

Never write a hex in a component. Components consume the semantic layer; only
`index.css` knows hexes.

### Light (page plane `#EFF6FF`, card `#FFFFFF`)

| Token | Hex | Contrast | Meaning |
|---|---|---|---|
| `--background` | `#EFF6FF` | — | page plane, tinted so white cards read as raised |
| `--card` | `#FFFFFF` | — | any content surface |
| `--foreground` | `#0F172A` | 17.9:1 on card | primary ink |
| `--muted-foreground` | `#5A6B85` | 5.4:1 card / 5.0:1 page | labels, metadata, axis text |
| `--secondary` | `#DCE7FA` | — | chips, inputs, progress tracks |
| `--border` | `rgba(15,23,42,.10)` | — | hairlines only, never a container outline |
| `--primary` | `#2563EB` | 5.2:1 | primary action, active nav, link |
| `--primary-strong` | `#1D4ED8` | 6.7:1 | pressed/hover, gradient end |
| `--primary-soft` | `#DBEAFE` | — | tinted wash behind primary content |
| `--income` | `#15803D` | 5.0:1 | money in |
| `--expense` | `#DC2626` | 4.8:1 | money out, over budget |
| `--warning` | `#B45309` | 5.0:1 | 75–99% of a budget |

### Dark (page plane `#070C16`, card `#121A2B`)

Dark is a **selected** set of steps, not an inversion. The plane is deep navy
rather than pure black so translucent materials have something to blur.

| Token | Hex | Contrast on card |
|---|---|---|
| `--background` | `#070C16` | — |
| `--card` | `#121A2B` | — |
| `--foreground` | `#E7EDF8` | 14.8:1 |
| `--muted-foreground` | `#94A3B8` | 6.8:1 |
| `--secondary` | `#1E293B` | — |
| `--border` | `rgba(148,163,184,.18)` | — |
| `--primary` | `#5B8DEF` | 5.4:1 |
| `--primary-strong` | `#7BA5F5` | — |
| `--primary-soft` | `rgba(91,141,239,.16)` | — |
| `--income` | `#34D399` | 9.0:1 |
| `--expense` | `#FB7185` | 6.5:1 |
| `--warning` | `#FBBF24` | 10.4:1 |

Filled primary buttons keep `#2563EB` with white text in **both** modes (5.2:1);
`--primary` is the *ink/tint* token and lightens in dark so text and icons stay
legible.

### Rules

- **Money colour is semantic, never decorative.** Green = income, red =
  expense/over-budget, amber = approaching a limit. Nothing else may wear them.
- **Sign before colour.** Every coloured amount also carries `+`/`−` and a
  label, so colour is never the only channel (WCAG 1.4.1).
- Negative account balances are `--expense`; a positive balance is plain ink,
  not green. Green is for *flow*, not for *state*.
- `--primary` never colours body text. Links and actions only.

---

## 3. Typography

**Geist Variable**, self-hosted (`@fontsource-variable/geist`, already a
dependency — no CDN, works offline in the PWA), falling back to the system
stack. It matches the geometric grotesque of the wordmark; the previous
`-apple-system` stack rendered as three different products on three platforms.

| Role | Size / line | Weight | Tracking |
|---|---|---|---|
| Hero figure (total balance) | 40–56px | 700 | −0.03em |
| Screen title | 34px / 1.1 | 700 | −0.02em |
| Card title | 17px | 600 | −0.01em |
| Body | 15px | 400–500 | 0 |
| Row label | 14px | 500 | 0 |
| Caption / metadata | 13px | 400–500 | 0 |
| Micro (axis, badges) | 11–12px | 500–600 | +0.01em |

- **Tracking tightens as size grows.** Never positive tracking above 13px.
- **All amounts get `.tnum`** (tabular figures) so columns align — except the
  hero figure, which is standalone and uses proportional figures.
- Never centre a paragraph longer than one line. Amount columns are always
  right-aligned; labels always left.

---

## 4. Data visualisation

Category colours are user-editable, so the app must ship a **validated
palette** as the default and as the picker. Derived with the
`dataviz` skill's validator: 8 hues, brand blue in slot 1, ordering chosen by
enumerating every permutation and keeping only those that clear both CVD gates
in both modes.

| Slot | Hue | Light | Dark |
|---|---|---|---|
| 1 | blue (brand) | `#2563EB` | `#5B8DEF` |
| 2 | orange | `#EA580C` | `#E06A33` |
| 3 | teal | `#0D9488` | `#2AA79B` |
| 4 | amber | `#B77C05` | `#B98B22` |
| 5 | pink | `#DB2777` | `#DE5A93` |
| 6 | olive | `#4D7C0F` | `#74992F` |
| 7 | violet | `#7C3AED` | `#9B7BF0` |
| 8 | brown | `#9A5B26` | `#B4763B` |

**Validation results** (OKLab ΔE ×100, Machado–Oliveira–Fernandes 2009 @ 1.0):

| Check | Light (on `#FFFFFF`) | Dark (on `#121A2B`) |
|---|---|---|
| Lightness band | PASS | PASS |
| Chroma floor | PASS | PASS |
| Adjacent CVD ΔE (≥8) | **10.3** | **10.5** |
| Normal-vision ΔE (≥15) | **19.6** | **18.2** |
| Contrast vs surface (≥3:1) | PASS | PASS |

Re-run after any change — do not eyeball it:

```bash
node <dataviz-skill>/scripts/validate_palette.js \
  "#2563EB,#EA580C,#0D9488,#B77C05,#DB2777,#4D7C0F,#7C3AED,#9A5B26" \
  --mode light --surface "#FFFFFF"
node <dataviz-skill>/scripts/validate_palette.js \
  "#5B8DEF,#E06A33,#2AA79B,#B98B22,#DE5A93,#74992F,#9B7BF0,#B4763B" \
  --mode dark --surface "#121A2B"
```

### Rules

- **Assign slots in fixed order, never cycled.** A 9th category is not a
  generated hue: it reuses a slot in the picker, and in the donut everything
  past the top 6 folds into a single grey **"Otros (n)"** segment, so the
  legend can list every drawn series.
- **Colour follows the category, not its rank.** Changing the month must not
  repaint a category. Slots are assigned by stable category order, never by
  amount.
- **One hex is stored per category** (the light step). In dark mode the app
  maps documented hexes to their dark twin via a lookup, and clamps any custom
  colour into the dark lightness band (`lib/chart-colors.ts`). This keeps the
  documented steps *selected* rather than algorithmically flipped.
- **Status colours are reserved.** `--income` / `--warning` / `--expense` never
  appear as a category series, and always ship with an icon or a label.
  Category olive (`#4D7C0F`) and income green (`#15803D`) may co-occur — the
  `+`/`−` and the label carry the distinction, never the hue.
- **Legend always present for ≥2 series**; ≤4 series are also direct-labelled.
- **Marks:** 2px lines, 2px surface gap between adjacent fills, 4–6px rounded
  data-ends, gridlines at `--border` and no heavier, no gradient fills under
  data (the hero card's decorative curve is not data and is exempt).
- **Every chart is hoverable.** Donut and bars: per-mark tooltip. Area/line:
  crosshair + tooltip. Tooltips use `--card` + hairline + shadow-md, never a
  black box.
- **Never a dual y-axis.** Two measures of different scale → two charts or
  index both to a common base.
- Empty state is a sentence, never a zeroed chart.

---

## 5. Space, radius, elevation

- **4px grid.** Gaps: 8 (inside a row), 12 (between rows), 16 (mobile card
  padding / between cards), 24 (desktop card padding / between cards), 32
  (section).
- **Radius scales with the surface**: `--radius` = 1rem base → chips/inputs
  `xl` (0.75rem), cards `3xl` (2.2rem), sheets `4xl`, pills `full`. A small
  element never has a larger radius than the surface holding it.
- **Elevation is a hierarchy of three, not a shadow palette:**
  - flat — the page plane; nothing floats without reason;
  - `shadow-sm` + hairline — every card;
  - `shadow-lg` — only things that overlay content (sheets, FAB, tooltips,
    the hero card).
- **Never both a heavy border and a shadow.** The hairline is what separates a
  white card from a white background in `prefers-reduced-transparency`.

---

## 6. Materials and motion

Unchanged from the Apple Design language, restated for completeness:

- Bars and sheets use `.material-bar` (blur 20px, saturate 180%) with content
  scrolling underneath. `prefers-reduced-transparency` → solid `--card`.
- Springs only, from `lib/springs.ts` (`springDefault`, `springAppear`,
  `springSheet`, `springIndicator`). No CSS durations for gestures.
- Feedback lands on **pointer-down** (`.pressable`, scale .97), never on click.
- Animations are interruptible and start from the current on-screen value.
- Enter and exit along the same path; sheets anchor to their origin.
- `prefers-reduced-motion` → cross-fade, no transform.
- **New:** charts animate on first mount only. A data refresh updates in place —
  a re-animating donut reads as "something happened".

---

## 7. Component rules

**Card.** `rounded-3xl bg-card shadow-sm` + hairline. Title 17/600 on the left,
one optional text action on the right (`--primary`, 13/500). Never two actions
in a card header — the second one belongs in the row or in a sheet.

**List row.** 44px minimum hit target. Leading 40px icon medallion tinted with
the entity's colour at 12% opacity, label + metadata stacked, trailing amount
right-aligned with `.tnum`. The whole row is the target, not the label.

**Button.** Primary = filled `#2563EB` / white, pill, `.pressable`. Secondary =
`--secondary` fill with `--foreground` ink. Tertiary = text in `--primary`.
Destructive = text in `--expense`, and destructive actions confirm in two
steps (already the pattern in the delete flows).

**Chip.** `--secondary` fill, 12/500, pill, used for filters and inline facts
(account balances in the hero). Selected chip = `--primary-soft` + `--primary`
ink, never a border swap.

**Budget bar.** 8px track (`--secondary`), rounded-full, fill green → amber at
75% → red at 100%, with the percentage stated in text next to it. The colour is
redundant with the number, deliberately.

**Empty state.** One sentence in `--muted-foreground` plus the action that
resolves it. No illustrations, no "no data" chrome.

**Skeletons, not spinners** for content that has a known shape.

---

## 8. Dashboard specification

The dashboard answers four questions, in this order. Anything that does not
answer one of them does not belong on it.

| # | Question | Component |
|---|---|---|
| 1 | *How much do we have?* | Hero balance + per-account chips |
| 2 | *How is the month going?* | Flow card: income vs expense, net, savings rate, daily pace chart |
| 3 | *Where is it going?* | Donut by category + budgets with traffic lights |
| 4 | *What just happened?* | Recent movements |

### Layout

```
mobile (1 col)                desktop ≥1024px (12 col)
┌────────────────────┐        ┌────────────────┬───────────┐
│ hero balance       │        │ hero balance   │ flow card │  1
├────────────────────┤        │  (7 col)       │  (5 col)  │
│ flow card          │        ├────────────────┴───────────┤
├────────────────────┤        │ pace chart (12 col)        │  2
│ pace chart         │        ├────────────────┬───────────┤
├────────────────────┤        │ recent (7 col) │ donut     │  3
│ scanner CTA        │        │ accounts       │ budgets   │
├────────────────────┤        │                │ scanner   │
│ donut              │        └────────────────┴───────────┘
├────────────────────┤
│ budgets            │        Mobile order is by urgency;
├────────────────────┤        desktop keeps analysis in the
│ recent             │        right rail so the left column
└────────────────────┘        stays a single reading path.
```

The accounts card is desktop-only: on mobile the hero's chips already list
every account, and repeating them costs a screenful.

### Rules specific to this screen

- **One hero figure per screen.** The total balance is the only number above
  32px. Competing hero numbers destroy the hierarchy — this is why income and
  expense moved into a shared flow card instead of two equal-weight tiles.
- The hero card is the **only** brand-blue surface on the dashboard. It carries
  the gradient (`#2563EB → #1D4ED8`) and the decorative curve; everything else
  is a white/navy card. Two blue surfaces on one screen and neither reads as
  the anchor.
- **Income and expense are a comparison, not two facts.** They share one
  proportional bar so the reader sees the ratio before reading either number,
  and the net result is stated in words ("Ahorraste $X · Y% de tus ingresos").
- The pace chart is **cumulative expense for the current month**, derived from
  the transaction window the client already has. No month-over-month
  comparison is drawn, because the client cannot guarantee a full previous
  month in that window — a chart that is sometimes truncated is worse than one
  that is honestly scoped.
- Budgets appear **only** when the household has defined at least one;
  otherwise a one-line empty state offers to create one.
- Recent movements: 6 rows, then "Ver todos". No dates on the row — the list
  is short and recent by definition, and the extra metadata truncates the
  merchant name at 390px.
- Nothing on the dashboard is a dead end: every card either links to its full
  screen or opens the sheet that edits it.

---

## 9. Accessibility checklist

Ship-blocking. Check every screen against this list:

- [ ] Body text ≥4.5:1, large text and marks ≥3:1, in **both** modes.
- [ ] No information carried by colour alone (sign, icon or label as well).
- [ ] Hit targets ≥44×44px.
- [ ] Every interactive element is reachable by keyboard with a visible
      `--ring` focus state; list rows that act as buttons have `role="button"`
      and handle Enter/Space.
- [ ] Icon-only controls have `aria-label`.
- [ ] `prefers-reduced-motion` and `prefers-reduced-transparency` respected.
- [ ] Charts have a text equivalent (the legend with values counts).
- [ ] Layout survives 200% text zoom and a 320px-wide viewport.

---

## 10. Changing the system

1. **Adding a colour is the last resort.** First check whether an existing
   semantic token means what you mean.
2. A new token is added to `index.css` in **both** modes, with its measured
   contrast recorded in §2.
3. Any change to the categorical palette re-runs the validator (§4) and
   updates the results table. A FAIL is not shippable.
4. Components import tokens, never hexes. A hex in a `.tsx` file is a bug —
   the only exception is a colour that comes from the database (a category's
   own colour).
5. When this document and the code disagree, the code is wrong.
