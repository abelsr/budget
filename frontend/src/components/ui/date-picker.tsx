import { useState } from "react"
import { CalendarDays } from "lucide-react"
import { DayPicker } from "react-day-picker"
import "react-day-picker/style.css"

function parseIso(value: string) { return value ? new Date(`${value}T12:00:00`) : undefined }
function isoDate(value: Date) { return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}` }

/** App-owned calendar with locale-aware labels and no browser-native chrome. */
export function DatePicker({ value, onChange, label, min, max, disabled = false }: { value: string; onChange: (value: string) => void; label: string; min?: string; max?: string; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const selected = parseIso(value)
  return <div className="relative">
    <button type="button" onClick={() => setOpen((current) => !current)} disabled={disabled} aria-haspopup="dialog" aria-expanded={open} aria-label={label} className="pressable flex h-11 w-full items-center justify-between rounded-xl bg-secondary px-4 text-left text-[15px] text-secondary-foreground disabled:opacity-50"><span className={selected ? "capitalize" : "text-muted-foreground"}>{selected ? new Intl.DateTimeFormat("es-MX", { day: "numeric", month: "long", year: "numeric" }).format(selected) : "Selecciona una fecha"}</span><CalendarDays size={18} className="text-muted-foreground" /></button>
    {open && <div role="dialog" aria-label={label} className="absolute left-0 z-50 mt-2 w-[min(21rem,calc(100vw-2.5rem))] rounded-2xl border border-border bg-card p-3 shadow-xl"><DayPicker mode="single" selected={selected} onSelect={(day) => { if (day) { onChange(isoDate(day)); setOpen(false) } }} disabled={[...(min ? [{ before: parseIso(min)! }] : []), ...(max ? [{ after: parseIso(max)! }] : [])]} weekStartsOn={0} classNames={{ months: "w-full", month: "w-full", caption_label: "text-[14px] font-semibold capitalize", nav: "absolute inset-x-0 flex items-center justify-between", button_previous: "pressable rounded-lg p-1.5 text-muted-foreground hover:bg-secondary", button_next: "pressable rounded-lg p-1.5 text-muted-foreground hover:bg-secondary", month_grid: "mt-2 w-full border-collapse", weekdays: "text-[11px] text-muted-foreground", weekday: "h-8 font-medium", week: "h-9", day: "p-0 text-center", day_button: "pressable size-9 rounded-full text-[13px] font-medium hover:bg-secondary", selected: "[&_button]:bg-primary [&_button]:text-primary-foreground [&_button:hover]:bg-primary", today: "[&_button]:text-primary", outside: "[&_button]:text-muted-foreground/40", disabled: "[&_button]:cursor-not-allowed [&_button]:text-muted-foreground/30" }} /></div>}
  </div>
}
