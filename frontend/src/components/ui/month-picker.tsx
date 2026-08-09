import { useState } from "react"
import { CalendarDays, ChevronLeft, ChevronRight } from "lucide-react"

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

/** Compact, app-owned month picker. Avoids the browser calendar in planning flows. */
export function MonthPicker({ value, onChange, label }: { value: string; onChange: (value: string) => void; label: string }) {
  const [open, setOpen] = useState(false)
  const [year, setYear] = useState(() => Number(value.slice(0, 4)))
  const [selectedYear, selectedMonth] = value.split("-").map(Number)
  const formatted = new Intl.DateTimeFormat("es-MX", { month: "long", year: "numeric" }).format(new Date(`${value}-01T12:00:00`))

  function choose(month: number) {
    onChange(`${year}-${String(month).padStart(2, "0")}`)
    setOpen(false)
  }

  return <div className="relative shrink-0">
    <button type="button" onClick={() => { setYear(selectedYear); setOpen((current) => !current) }} aria-haspopup="dialog" aria-expanded={open} aria-label={label} className="pressable flex min-h-10 items-center gap-2 rounded-xl bg-secondary px-3 text-[13px] font-medium capitalize text-secondary-foreground"><CalendarDays size={16} /><span>{formatted}</span></button>
    {open && <div role="dialog" aria-label="Seleccionar mes" className="absolute right-0 z-50 mt-2 w-72 rounded-2xl border border-border bg-card p-3 shadow-xl"><div className="mb-3 flex items-center justify-between"><button type="button" onClick={() => setYear((current) => current - 1)} aria-label="Año anterior" className="pressable rounded-lg p-2 text-muted-foreground"><ChevronLeft size={17} /></button><p className="text-[15px] font-semibold">{year}</p><button type="button" onClick={() => setYear((current) => current + 1)} aria-label="Año siguiente" className="pressable rounded-lg p-2 text-muted-foreground"><ChevronRight size={17} /></button></div><div className="grid grid-cols-3 gap-1">{MONTHS.map((month, index) => { const selected = year === selectedYear && index + 1 === selectedMonth; return <button key={month} type="button" onClick={() => choose(index + 1)} aria-pressed={selected} className={`pressable rounded-xl py-2.5 text-[13px] font-medium ${selected ? "bg-primary text-primary-foreground" : "text-secondary-foreground hover:bg-secondary"}`}>{month}</button> })}</div></div>}
  </div>
}
