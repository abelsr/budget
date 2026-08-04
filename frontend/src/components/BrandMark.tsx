/**
 * Marca budget. Isotipo + wordmark, una sola implementación para el sidebar,
 * el acceso y el onboarding (docs/design-guidelines.md §1).
 *
 * El isotipo ya trae su gradiente azul, así que nunca se recolorea; sobre una
 * superficie de marca se usa `onBrand`, que le pone el contenedor blanco de la
 * variante de la hoja de marca.
 */
export function BrandMark({
  size = 32,
  showWordmark = true,
  onBrand = false,
  className,
}: {
  size?: number
  showWordmark?: boolean
  onBrand?: boolean
  className?: string
}) {
  return (
    <span className={`flex items-center gap-2.5 ${className ?? ""}`}>
      <img
        src="/budget/isotipo.svg"
        alt={showWordmark ? "" : "budget"}
        aria-hidden={showWordmark || undefined}
        width={size}
        height={size}
        style={{ width: size, height: size }}
        className={`shrink-0 object-contain ${
          onBrand ? "rounded-[28%] bg-white p-1 shadow-sm" : ""
        }`}
      />
      {showWordmark && (
        <span
          className="text-[22px] leading-none font-bold tracking-[-0.03em]"
          style={{ fontSize: size * 0.68 }}
        >
          budget
        </span>
      )}
    </span>
  )
}
