import { Link } from "react-router-dom"
import { ChevronLeft } from "lucide-react"

/**
 * Primitivas del sistema de diseño (docs/design-guidelines.md §5 y §7).
 *
 * Existen para que ninguna pantalla vuelva a escribir a mano una superficie,
 * un encabezado o un área táctil: el sistema vive aquí, no en copias.
 */

/** Superficie de contenido: radio, hairline y la única elevación de tarjeta. */
export const CARD = "rounded-3xl border border-border bg-card shadow-sm"

/** Área táctil de 44px sin agrandar el control (§9). */
export const TAP_TARGET =
  "relative before:absolute before:top-1/2 before:left-1/2 before:size-11 before:-translate-x-1/2 before:-translate-y-1/2 before:content-['']"

export function Card({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return <section className={`${CARD} ${className ?? ""}`}>{children}</section>
}

/**
 * Encabezado de pantalla: eyebrow opcional, título de 34px y una sola acción.
 * `back` lo convierte en pantalla de segundo nivel.
 */
export function PageHeader({
  title,
  eyebrow,
  back,
  action,
}: {
  title: string
  eyebrow?: React.ReactNode
  back?: string | (() => void)
  action?: React.ReactNode
}) {
  const backButton =
    typeof back === "string" ? (
      <Link
        to={back}
        aria-label="Volver"
        className={`pressable flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground ${TAP_TARGET}`}
      >
        <ChevronLeft size={20} />
      </Link>
    ) : back ? (
      <button
        onClick={back}
        aria-label="Volver"
        className={`pressable flex size-9 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground ${TAP_TARGET}`}
      >
        <ChevronLeft size={20} />
      </button>
    ) : null

  return (
    <header className="flex items-center gap-3 px-1">
      {backButton}
      <div className="min-w-0 flex-1">
        {eyebrow && (
          <p className="text-[13px] font-medium text-muted-foreground">{eyebrow}</p>
        )}
        <h1 className="truncate text-[34px] leading-tight font-bold tracking-[-0.02em]">
          {title}
        </h1>
      </div>
      {action}
    </header>
  )
}

/** Botón redondo de acción en encabezados y tarjetas. */
export function IconButton({
  label,
  onClick,
  variant = "secondary",
  children,
}: {
  label: string
  onClick: () => void
  variant?: "primary" | "secondary"
  children: React.ReactNode
}) {
  const tone =
    variant === "primary"
      ? "bg-primary text-primary-foreground"
      : "bg-secondary text-secondary-foreground"
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className={`pressable flex size-9 shrink-0 items-center justify-center rounded-full ${tone} ${TAP_TARGET}`}
    >
      {children}
    </button>
  )
}

/** Título de grupo sobre una tarjeta-lista. */
export function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-1.5 px-4 text-[13px] font-medium text-muted-foreground">
      {children}
    </h2>
  )
}

/** Vacío: una frase y, si existe, la acción que lo resuelve (§7). */
export function EmptyState({
  icon,
  title,
  hint,
  action,
}: {
  icon: React.ReactNode
  title: string
  hint: string
  action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <span className="flex size-14 items-center justify-center rounded-full bg-secondary text-muted-foreground">
        {icon}
      </span>
      <p className="mt-1 text-[16px] font-semibold">{title}</p>
      <p className="max-w-[38ch] text-[13px] leading-relaxed text-muted-foreground">
        {hint}
      </p>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

/** Interruptor del sistema: 44×44 táctil aunque mida 44×24. */
export function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: () => void
  label: string
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={(e) => {
        e.stopPropagation()
        onChange()
      }}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors before:absolute before:inset-x-0 before:top-1/2 before:h-11 before:-translate-y-1/2 before:content-[''] ${
        checked ? "bg-primary" : "bg-muted"
      }`}
    >
      <span
        className={`absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition-transform ${
          checked ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  )
}
