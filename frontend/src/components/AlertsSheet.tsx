import { useState } from "react"
import { Bell, CalendarClock, CircleAlert, CreditCard, PiggyBank, Wallet } from "lucide-react"
import { useNavigate } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { useAlerts, useGenerateAlertRecurring, useReadAlerts } from "@/lib/queries"
import type { Alert, AlertKind } from "@/lib/types"

const alertVisual: Record<AlertKind, { icon: typeof Bell; tone: string }> = {
  budget_warning: { icon: CircleAlert, tone: "bg-amber-500/12 text-amber-700 dark:text-amber-300" },
  budget_exceeded: { icon: CircleAlert, tone: "bg-expense/12 text-expense" },
  recurring_overdue: { icon: CalendarClock, tone: "bg-primary/12 text-primary" },
  goal_reached: { icon: PiggyBank, tone: "bg-income/12 text-income" },
  negative_balance: { icon: Wallet, tone: "bg-expense/12 text-expense" },
  card_payment_due: { icon: CreditCard, tone: "bg-primary/12 text-primary" },
  instalment_due: { icon: CalendarClock, tone: "bg-primary/12 text-primary" },
}

function destination(kind: AlertKind) {
  if (kind === "recurring_overdue") return "/app/ajustes/recurrentes"
  if (kind === "negative_balance" || kind === "card_payment_due" || kind === "instalment_due") return "/app/cuentas"
  return "/app"
}

export function AlertsButton() {
  const [open, setOpen] = useState(false)
  const { data: alerts = [] } = useAlerts()
  const unread = alerts.filter((alert) => !alert.readAt).length
  return <>
    <button type="button" onClick={() => setOpen(true)} aria-label={unread ? `${unread} notificaciones pendientes` : "Notificaciones"} className="pressable relative flex size-8 items-center justify-center rounded-full text-muted-foreground hover:bg-secondary hover:text-foreground">
      <Bell size={18} />
      {unread > 0 && <span className="absolute right-0 top-0 flex min-w-3.5 items-center justify-center rounded-full bg-destructive px-1 text-[9px] font-bold leading-3.5 text-destructive-foreground">{unread > 9 ? "9+" : unread}</span>}
    </button>
    <AlertsSheet open={open} onOpenChange={setOpen} alerts={alerts} />
  </>
}

function AlertsSheet({ open, onOpenChange, alerts }: { open: boolean; onOpenChange: (open: boolean) => void; alerts: Alert[] }) {
  const navigate = useNavigate()
  const read = useReadAlerts()
  const generate = useGenerateAlertRecurring()
  const unread = alerts.filter((alert) => !alert.readAt)
  function visit(alert: Alert) {
    if (!alert.readAt) read.mutate(alert.id)
    onOpenChange(false)
    navigate(destination(alert.kind))
  }
  return <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle><DrawerContent className="mx-auto max-w-lg"><div className="flex max-h-[calc(100dvh-2rem)] flex-col"><DrawerHeader className="flex-row items-center justify-between text-left"><DrawerTitle>Notificaciones</DrawerTitle>{unread.length > 0 && <button type="button" onClick={() => read.mutate(undefined)} className="pressable text-[13px] font-medium text-primary">Marcar todas como leídas</button>}</DrawerHeader><div className="min-h-0 overflow-y-auto px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))]">{alerts.length === 0 ? <div className="py-12 text-center"><Bell className="mx-auto mb-3 text-muted-foreground" size={28} /><p className="text-sm font-medium">Todo al día</p><p className="mt-1 text-[13px] text-muted-foreground">Aquí aparecerán avisos importantes de tu hogar.</p></div> : <div className="space-y-2">{alerts.map((alert) => <AlertRow key={alert.id} alert={alert} onVisit={visit} onGenerate={() => generate.mutate(alert.id)} generating={generate.isPending} />)}</div>}</div></div></DrawerContent></Drawer>
}

function AlertRow({ alert, onVisit, onGenerate, generating }: { alert: Alert; onVisit: (alert: Alert) => void; onGenerate: () => void; generating: boolean }) {
  const visual = alertVisual[alert.kind]
  const Icon = visual.icon
  return <div className={`rounded-2xl border p-3 ${alert.readAt ? "opacity-60" : "bg-card"}`}><button type="button" onClick={() => onVisit(alert)} className="pressable flex w-full gap-3 text-left"><span className={`flex size-9 shrink-0 items-center justify-center rounded-full ${visual.tone}`}><Icon size={17} /></span><span className="min-w-0 flex-1"><span className="block text-[13px] font-medium leading-5">{alert.message}</span><span className="mt-0.5 block text-[11px] text-muted-foreground">{new Date(alert.createdAt).toLocaleDateString("es-MX", { day: "numeric", month: "short" })}</span></span>{!alert.readAt && <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" aria-label="No leída" />}</button>{alert.kind === "recurring_overdue" && !alert.readAt && <Button size="sm" variant="secondary" disabled={generating} onClick={onGenerate} className="pressable mt-3 h-8 rounded-lg text-xs">Generar ahora</Button>}</div>
}
