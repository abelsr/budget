/** Barra de progreso semáforo: verde <75%, ámbar <100%, rojo ≥100%. */
export function BudgetBar({ percentage }: { percentage: number }) {
  const pct = Math.max(0, Math.min(percentage, 100))
  const color =
    percentage >= 100 ? "bg-expense" : percentage >= 75 ? "bg-warning" : "bg-income"

  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
      <div
        className={`h-full rounded-full transition-all ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
