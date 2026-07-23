import type { Transition } from "motion/react"

/**
 * Presets de springs según la guía Apple Design.
 *
 * Apple piensa en "damping ratio" (overshoot) y "response" (rapidez),
 * no en duraciones fijas. En Motion, eso mapea a `bounce` + `duration`:
 *
 *  - Default UI: critically damped, sin overshoot (damping 1.0, response 0.3–0.4)
 *  - Momentum/flick: un poco de bounce, SOLO cuando el gesto trae velocidad
 *    (damping ~0.8 → bounce ~0.2)
 *  - Drawer/sheet: damping 0.8, response 0.3
 *
 * Regla de oro: las springs son interrumpibles y parten del valor actual
 * en pantalla; nunca uses keyframes/CSS transitions para gestos.
 */

/** Default: graceful, sin overshoot. Úsala en casi todo. */
export const springDefault: Transition = {
  type: "spring",
  bounce: 0,
  duration: 0.4,
}

/** Entradas de contenido (cards, listas): rápida y sin rebote. */
export const springAppear: Transition = {
  type: "spring",
  bounce: 0,
  duration: 0.35,
}

/** Sheets/drawers e interacciones con momentum: bounce ligero. */
export const springSheet: Transition = {
  type: "spring",
  bounce: 0.2,
  duration: 0.4,
}

/** Indicadores que siguen selección (tab activo, segmented control). */
export const springIndicator: Transition = {
  type: "spring",
  bounce: 0.15,
  duration: 0.35,
}
