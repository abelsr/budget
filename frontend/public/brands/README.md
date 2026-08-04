# Brand logos — acquisition list

Source of truth for brand marks in the app. Logos live under
`frontend/public/brands/<category>/<slug>.svg` and are compiled into the
bundle by `scripts/build-brand-logos.mjs` (run it after adding files).

## How the app uses them

- The **registry** `frontend/src/lib/brands.ts` matches a transaction note
  (normalized) to a brand and renders its mark via `BrandMedallion`, exactly
  like category icons.
- `build-brand-logos.mjs` classifies each SVG automatically: a genuine
  Simple-Icons-style single-path 24×24 mark compiles to `{ kind: "path" }`
  and renders inline, tinted with `currentColor` (works in dark mode). Any
  other SVG (native viewBox, multi-path, multi-color, gradients) compiles to
  `{ kind: "image" }` and renders as a plain `<img>` in its own colors — no
  dark-mode tinting, but shows the real logo instead of a cropped/garbled
  fragment.
- A brand **without** an SVG falls back to a **monogram** (1–3 letters in the
  brand color) — still looks intentional, always works.
- Cards and banks use the same registry (proposal B1).

## SVG requirements (important)

- Prefer **monochrome, single `<path>`**, `viewBox="0 0 24 24"` (Simple Icons
  format). A single path lets the app tint it with `currentColor` in both
  light and dark mode.
- No `<image>`, no external references, no scripts, no gradients-with-text.
- If you can only find a **multi-color** logo, it will still render (in its own
  colors) but won't tint in dark mode — monochrome is preferred.
- Max ~50 KB per file.

## Where to look (official brand / press sites)

Search `<brand> press kit logo svg` or the brand's own media/newsroom section.
SVG beats PNG; a transparent monochrome mark on a clean background is ideal.

## Fetched (32 of 34)

Research (see git history / PR discussion) found real vector logos for 32 of
the 34 brands below. Only 5 (walmart, amazon, xbox, nintendo, prime-video)
are genuine Simple-Icons-style single-path 24×24 marks — those render inline,
tinted with `currentColor`, and work in dark mode.

The other 27 are official/Wikimedia SVGs in their **native viewBox and
original colors** (multi-path, sometimes gradients) — no clean monochrome
source exists for them. `build-brand-logos.mjs` detects this automatically:
non-conforming SVGs compile to a `{ kind: "image" }` entry and
`BrandMedallion` renders them as an `<img>` (own colors/proportions,
`object-fit: contain`) instead of a tinted inline path. They won't re-tint in
dark mode, but they show the real logo.

| Brand | Path | Kind |
|---|---|---|
| BBVA | `banks/bbva.svg` | image |
| Santander | `banks/santander.svg` | image |
| Scotiabank | `banks/scotiabank.svg` | image |
| Banorte | `banks/banorte.svg` | image |
| Citibanamex | `banks/citibanamex.svg` | image |
| Banco Azteca | `banks/banco-azteca.svg` | image |
| Klar | `banks/klar.svg` | image — ⚠️ source SVG is white-only fill (designed for a dark header on klar.mx); may be low-contrast on light backgrounds, consider re-sourcing or recoloring |
| Walmart | `shops/walmart.svg` | path (Simple Icons) |
| OXXO | `shops/oxxo.svg` | image |
| Costco | `shops/costco.svg` | image |
| Amazon | `shops/amazon.svg` | path (Simple Icons) |
| Liverpool | `shops/liverpool.svg` | image |
| El Palacio de Hierro | `shops/el-palacio-de-hierro.svg` | image |
| Bodega Aurrerá | `shops/bodega-aurrera.svg` | image |
| Farmacias del Ahorro | `shops/farmacias-del-ahorro.svg` | image |
| Farmacias Guadalajara | `shops/farmacias-guadalajara.svg` | image |
| Sanborns | `shops/sanborns.svg` | image |
| Domino's | `shops/dominos-pizza.svg` | image |
| Cinépolis | `shops/cinepolis.svg` | image |
| Mercado Libre | `shops/mercado-libre.svg` | image |
| CFE | `services/cfe.svg` | image |
| Telmex | `services/telmex.svg` | image |
| Telcel | `services/telcel.svg` | image |
| Izzi | `services/izzi.svg` | image |
| Totalplay | `services/totalplay.svg` | image |
| Megacable | `services/megacable.svg` | image — has gradients |
| Pemex | `services/pemex.svg` | image |
| Rappi | `services/rappi.svg` | image |
| Disney+ | `services/disneyplus.svg` | image — has gradients |
| Prime Video | `services/prime-video.svg` | path (Simple Icons) |
| Xbox | `services/xbox.svg` | path (Simple Icons) |
| Nintendo | `services/nintendo.svg` | path (Simple Icons) |

## Still to do — no usable SVG found anywhere (2)

Searched official sites, press kits, Wikimedia Commons, and logo aggregators
(worldvectorlogo, seeklogo, brandfetch, cdnlogo) — only raster (PNG) or
nothing at all turned up. Falls back to monogram until sourced.

| Brand | Save to | Find at (official) | Monogram color |
|---|---|---|---|
| La Comer | `frontend/public/brands/shops/la-comer.svg` | lacomer.com.mx | `#d00027` |
| STP | `frontend/public/brands/banks/stp.svg` | stp.mx (stpmex.com is stale) | `#f58220` |

## Already have (27, from Simple Icons — no action needed)

- **banks/** (8): visa, mastercard, american-express, discover, paypal,
  mercado-pago, hsbc, nubank
- **shops/** (8): sams-club, chedraui, coppel, soriana, starbucks, mcdonalds,
  burger-king, kfc
- **services/** (11): at-and-t, movistar, uber, airbnb, netflix, spotify,
  youtube, max, steam, playstation, epic-games

## Notes

- **BanCoppel** = the Coppel brand → reuses `shops/coppel.svg`.
- **Mercado Libre** ≠ Mercado Pago (different brands): only Mercado Pago is
  available; Mercado Libre is in the fetch list above.
- Brand colors above are fallback monogram tints (approximate; fine-tune in
  `frontend/src/lib/brands.ts`). When an SVG exists, the app uses its own fill
  color instead.
