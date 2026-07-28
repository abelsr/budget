import {
  Banknote,
  Car,
  Gamepad2,
  HandCoins,
  HeartPulse,
  House,
  PiggyBank,
  Repeat,
  ShoppingCart,
  Utensils,
  Wallet,
  Zap,
  type LucideIcon,
} from "lucide-react"

import { seriesColor } from "@/lib/chart-colors"
import { useTheme } from "@/lib/theme"

const iconMap: Record<string, LucideIcon> = {
  "shopping-cart": ShoppingCart,
  utensils: Utensils,
  car: Car,
  house: House,
  zap: Zap,
  "heart-pulse": HeartPulse,
  "gamepad-2": Gamepad2,
  repeat: Repeat,
  banknote: Banknote,
  "hand-coins": HandCoins,
  wallet: Wallet,
  "piggy-bank": PiggyBank,
}

export function CategoryIcon({
  icon,
  color,
  size = 20,
  className,
  style,
}: {
  icon: string
  color: string
  size?: number
  className?: string
  style?: React.CSSProperties
}) {
  const Icon = iconMap[icon] ?? Wallet
  const { isDark } = useTheme()
  // El color guardado es el paso claro; en oscuro se usa su gemelo (§4 de la guía)
  const tint = seriesColor(color, isDark)
  return (
    <span
      className={`flex items-center justify-center rounded-full ${className ?? ""}`}
      style={{ backgroundColor: `${tint}22`, color: tint, ...style }}
    >
      <Icon size={size} strokeWidth={2.2} />
    </span>
  )
}
