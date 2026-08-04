import { useTheme } from "@/lib/theme"
import { seriesColor } from "@/lib/chart-colors"
import { BRAND_LOGOS } from "@/lib/brand-logos.generated"
import type { Brand } from "@/lib/brands"

/**
 * Medallón circular de marca (bancos, comercios, servicios). Mismo patrón
 * visual que CategoryIcon: círculo con el color de la marca al 12% de fondo y
 * la marca coloreada encima.
 *
 * Si la marca tiene logo (path SVG de Simple Icons, 24×24) se dibuja inlined y
 * se tinta con currentColor; si no, cae al monograma (nunca bloquea la fila).
 * El color base lo da el fill del SVG cuando existe, si no el de la marca.
 */
export function BrandMedallion({
  brand,
  size = 20,
  className,
}: {
  brand: Brand
  size?: number
  className?: string
}) {
  const { isDark } = useTheme()
  const logo = brand.logo ? BRAND_LOGOS[brand.logo] : undefined
  const tint = seriesColor(logo?.kind === "path" ? logo.color : brand.color, isDark)

  return (
    <span
      className={`flex items-center justify-center rounded-full ${className ?? ""}`}
      style={{ backgroundColor: `${tint}22`, color: tint }}
      aria-label={brand.name}
      role="img"
    >
      {logo?.kind === "path" ? (
        <svg
          viewBox="0 0 24 24"
          width={size}
          height={size}
          fill="currentColor"
          aria-hidden="true"
          focusable="false"
        >
          <path d={logo.d} />
        </svg>
      ) : logo?.kind === "image" ? (
        <img
          src={`/brands/${logo.path}`}
          width={size}
          height={size}
          style={{ objectFit: "contain" }}
          alt=""
          aria-hidden="true"
        />
      ) : (
        <span
          className="font-bold uppercase tracking-tight"
          style={{
            fontSize: size * (brand.monogram.length >= 3 ? 0.55 : 0.78),
            lineHeight: 1,
          }}
        >
          {brand.monogram}
        </span>
      )}
    </span>
  )
}
