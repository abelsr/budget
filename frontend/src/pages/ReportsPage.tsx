import { useState } from "react"
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { BarChart3, Download } from "lucide-react"

import { Card, EmptyState, PageHeader } from "@/components/ui/surface"
import { formatMoney, formatMoneyCompact, toISODate } from "@/lib/format"
import { seriesColor } from "@/lib/chart-colors"
import { useCategories, useRangeSummary } from "@/lib/queries"
import { useTheme } from "@/lib/theme"
import { apiFetchBlob } from "@/lib/api"

function defaultFrom() {
  const date = new Date()
  date.setMonth(date.getMonth() - 5, 1)
  return toISODate(date)
}

export function ReportsPage() {
  const [from, setFrom] = useState(defaultFrom)
  const [to, setTo] = useState(() => toISODate(new Date()))
  const [exportError, setExportError] = useState<string | null>(null)
  const [exporting, setExporting] = useState<string | null>(null)
  const { data: summary } = useRangeSummary(from, to)
  const { data: categories = [] } = useCategories()
  const { isDark } = useTheme()
  const monthly = summary?.monthly ?? []
  const expenses = summary?.byCategory ?? []
  const totalIncome = monthly.reduce((total, month) => total + month.income, 0)
  const totalExpense = monthly.reduce((total, month) => total + month.expense, 0)
  const categoryData = expenses.map((row) => {
    const category = categories.find((item) => item.id === row.categoryId)
    return { ...row, name: category?.name ?? "Categoría eliminada", color: seriesColor(category?.color ?? "#94a3b8", isDark) }
  })

  async function exportReport(format: "csv" | "xlsx" | "docx" | "pdf") {
    setExportError(null)
    setExporting(format)
    try {
      const blob = await apiFetchBlob(`/reports/export?format=${format}&from=${encodeURIComponent(from)}&to=${encodeURIComponent(to)}`)
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `reporte-${from}-a-${to}.${format}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch (error) {
      setExportError(error instanceof Error ? error.message : "No se pudo exportar el reporte.")
    } finally {
      setExporting(null)
    }
  }

  return <div className="flex max-w-5xl flex-col gap-4">
    <PageHeader title="Reportes" eyebrow="Analiza la evolución de tu hogar" />
    <Card className="p-3">
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-[11px] font-medium text-muted-foreground">Desde<input type="date" value={from} max={to} onChange={(event) => setFrom(event.target.value)} className="h-9 rounded-lg border border-input bg-background px-2 text-[12px] text-foreground outline-none focus:ring-2 focus:ring-ring/30" /></label>
        <label className="flex flex-col gap-1 text-[11px] font-medium text-muted-foreground">Hasta<input type="date" value={to} min={from} onChange={(event) => setTo(event.target.value)} className="h-9 rounded-lg border border-input bg-background px-2 text-[12px] text-foreground outline-none focus:ring-2 focus:ring-ring/30" /></label>
        <fieldset className="flex flex-wrap gap-1" aria-label="Exportar reporte">
          <legend className="sr-only">Exportar reporte</legend>
          {(["csv", "xlsx", "docx", "pdf"] as const).map((format) => <button key={format} type="button" onClick={() => void exportReport(format)} disabled={exporting !== null} className="inline-flex h-9 items-center gap-1 rounded-lg border border-input px-2 text-[11px] font-medium uppercase text-foreground hover:bg-muted disabled:cursor-not-allowed disabled:opacity-60"><Download size={13} aria-hidden="true" />{exporting === format ? "Exportando" : format}</button>)}
        </fieldset>
      </div>
      {exportError && <p className="mt-2 text-[12px] text-expense" role="alert">No se pudo exportar el reporte: {exportError}</p>}
    </Card>
    {monthly.length === 0 ? <Card><EmptyState icon={<BarChart3 size={26} />} title="Aún no hay datos para este periodo" hint="Elige otro rango o registra movimientos para ver tendencias y categorías." /></Card> : <>
      <div className="grid gap-3 sm:grid-cols-3">
        <Metric label="Ingresos" value={totalIncome} tone="text-income" />
        <Metric label="Gastos" value={totalExpense} tone="text-expense" />
        <Metric label="Balance neto" value={totalIncome - totalExpense} tone={totalIncome >= totalExpense ? "text-income" : "text-expense"} />
      </div>
      <Card className="p-4"><h2 className="text-[13px] font-semibold">Ingresos y gastos por mes</h2><div className="mt-4 h-64" role="img" aria-label="Barras mensuales de ingresos y gastos"><ResponsiveContainer width="100%" height="100%"><BarChart data={monthly} margin={{ top: 8, right: 0, left: -18, bottom: 0 }}><XAxis dataKey="month" tickFormatter={monthName} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} /><YAxis tickFormatter={formatMoneyCompact} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} width={52} /><Tooltip content={<MoneyTooltip />} /><Bar dataKey="income" name="Ingresos" fill="var(--income)" radius={[3, 3, 0, 0]} /><Bar dataKey="expense" name="Gastos" fill="var(--expense)" radius={[3, 3, 0, 0]} /></BarChart></ResponsiveContainer></div><div className="mt-2 flex justify-center gap-4 text-[11px] text-muted-foreground"><span><i className="mr-1 inline-block size-2 rounded-sm bg-income" />Ingresos</span><span><i className="mr-1 inline-block size-2 rounded-sm bg-expense" />Gastos</span></div></Card>
      <Card className="p-4"><h2 className="text-[13px] font-semibold">Gastos por categoría</h2>{categoryData.length === 0 ? <p className="py-10 text-center text-[13px] text-muted-foreground">No hay gastos en este periodo.</p> : <div className="mt-4 h-64"><ResponsiveContainer width="100%" height="100%"><BarChart data={categoryData} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}><XAxis type="number" hide /><YAxis type="category" dataKey="name" width={100} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "var(--muted-foreground)" }} /><Tooltip content={<MoneyTooltip />} /><Bar dataKey="total" name="Gastos" radius={[0, 3, 3, 0]}>{categoryData.map((row) => <Cell key={row.categoryId} fill={row.color} />)}</Bar></BarChart></ResponsiveContainer></div>}</Card>
    </>}
  </div>
}

function Metric({ label, value, tone }: { label: string; value: number; tone: string }) { return <Card className="p-4"><p className="text-[11px] font-medium text-muted-foreground">{label}</p><p className={`tnum mt-1 text-[20px] font-bold ${tone}`}>{formatMoney(value)}</p></Card> }
function monthName(month: string) { return new Intl.DateTimeFormat("es-MX", { month: "short", year: "2-digit" }).format(new Date(`${month}-01T12:00:00`)) }
function MoneyTooltip({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number }[]; label?: string }) { if (!active || !payload?.length) return null; return <div className="rounded-lg border border-border bg-card px-2.5 py-2 text-[11px] shadow-sm"><p className="mb-1 font-medium text-muted-foreground">{label && (label.includes("-") ? monthName(label) : label)}</p>{payload.map((row) => <p key={row.name} className="tnum">{row.name}: <span className="font-semibold">{formatMoney(row.value)}</span></p>)}</div> }
