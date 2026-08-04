import { CreditCard } from "lucide-react"

import { BrandMedallion } from "@/components/BrandMedallion"
import { BRAND_LOGOS } from "@/lib/brand-logos.generated"
import { getBrand, matchBrand } from "@/lib/brands"
import { formatMoney } from "@/lib/format"
import type { Account, CardBrand } from "@/lib/types"

/**
 * Widget de cuenta tipo wallet (iOS/Android). Se usa cuando la cuenta tiene
 * definidos `bank` y/o `lastFour` (docs/roadmap/18-features-y-uiux-propuestas.md B1).
 *
 * Gradiente oscuro derivado del color de la marca del banco (o neutro si no se
 * reconoce), texto blanco, número enmascarado con los últimos 4 dígitos, chip y
 * emisor de la tarjeta. Solo se muestran los últimos 4 dígitos, nunca el
 * número completo.
 */

const CARD_BRAND_LOGO: Partial<Record<CardBrand, string>> = {
  visa: "visa",
  mastercard: "mastercard",
  amex: "american-express",
}

/** Oscurece (factor < 1) o aclara (factor > 1) un hex RGB multiplicando canales. */
function shade(hex: string, factor: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return hex
  const n = parseInt(m[1], 16)
  const clamp = (c: number) => Math.min(255, Math.round(c))
  const r = clamp(((n >> 16) & 255) * factor)
  const g = clamp(((n >> 8) & 255) * factor)
  const b = clamp((n & 255) * factor)
  return `#${((1 << 24) | (r << 16) | (g << 8) | b).toString(16).slice(1)}`
}

export function AccountCard({
  account,
  onClick,
  className,
}: {
  account: Account
  onClick?: () => void
  className?: string
}) {
  const bank = matchBrand(account.bank ?? "")
  const brandLogo = account.cardBrand
    ? CARD_BRAND_LOGO[account.cardBrand]
    : undefined
  const brandPath = brandLogo ? getBrand(brandLogo) : undefined
  const logo = brandPath?.logo ? BRAND_LOGOS[brandPath.logo] : undefined
  const base = bank?.color ?? "#334155"
  const gradient = `linear-gradient(135deg, ${shade(base, 1.25)}, ${shade(
    base,
    0.55,
  )})`

  const label = `${account.name} · ${formatMoney(account.balance)}`

  const content = (
    <>
      <div
        className="pointer-events-none absolute -top-12 -right-10 size-32 rounded-full bg-white/10 blur-2xl"
        aria-hidden="true"
      />
      <div className="relative flex flex-col gap-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2.5">
            {bank ? (
              <BrandMedallion brand={bank} size={16} className="size-8 shrink-0 bg-white/15 text-white" />
            ) : (
              <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-white/15 text-white">
                <CreditCard size={15} aria-hidden="true" />
              </span>
            )}
            <p className="truncate text-[13px] font-semibold text-white/90">
              {account.bank || account.name}
            </p>
          </div>
          {logo?.kind === "path" ? (
            <svg
              viewBox="0 0 24 24"
              width={34}
              height={24}
              className="shrink-0 text-white"
              aria-label={brandPath?.name ?? "Tarjeta"}
              role="img"
            >
              <path d={logo.d} fill="currentColor" />
            </svg>
          ) : (
            <span
              className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white/70"
              aria-hidden="true"
            >
              {account.cardBrand ?? "card"}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between">
          {/* Chip EMV decorativo */}
          <span
            className="flex h-7 w-9 items-center justify-center rounded-md bg-gradient-to-br from-amber-100 to-amber-300"
            aria-hidden="true"
          >
            <span className="h-3.5 w-6 rounded-[3px] border border-amber-600/40 bg-amber-200/60" />
          </span>
        </div>

        <p className="tnum text-[19px] font-semibold tracking-[0.12em] text-white">
          ••••&ensp;••••&ensp;••••&ensp;{account.lastFour}
        </p>

        <div className="flex items-end justify-between gap-3">
          <p className="min-w-0 truncate text-[14px] font-medium text-white/90">
            {account.name}
          </p>
          <p className="tnum shrink-0 text-[16px] font-bold text-white">
            {formatMoney(account.balance)}
          </p>
        </div>
      </div>
    </>
  )

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        aria-label={label}
        className={`pressable relative overflow-hidden rounded-3xl p-5 text-left shadow-lg ${className ?? ""}`}
        style={{ background: gradient }}
      >
        {content}
      </button>
    )
  }

  return (
    <div
      className={`relative overflow-hidden rounded-3xl p-5 shadow-lg ${className ?? ""}`}
      style={{ background: gradient }}
    >
      {content}
    </div>
  )
}
