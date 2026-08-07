import { useEffect, useState } from "react"
import { AlertTriangle, CheckCircle2, Landmark } from "lucide-react"

import { formatMoney } from "@/lib/format"
import type { Account } from "@/lib/types"
import {
  useCompleteReconciliation,
  useCreateReconciliation,
  useReconciliation,
  useToggleReconciliation,
} from "@/lib/queries"
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"

export function ReconciliationSheet({ account, open, onOpenChange }: { account: Account; open: boolean; onOpenChange: (open: boolean) => void }) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [statementDate, setStatementDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [statementBalance, setStatementBalance] = useState("")
  const create = useCreateReconciliation()
  const detail = useReconciliation(account.id, sessionId)
  const toggle = useToggleReconciliation()
  const complete = useCompleteReconciliation()
  const session = detail.data

  useEffect(() => {
    if (!open) {
      setSessionId(null)
      setStatementBalance("")
    }
  }, [open])

  const start = async () => {
    const created = await create.mutateAsync({ accountId: account.id, statementDate, statementBalance: Number(statementBalance) })
    setSessionId(created.id)
  }
  const refresh = () => detail.refetch()
  const toggleRow = async (transactionId: string, reconciled: boolean) => {
    await toggle.mutateAsync({ transactionId, reconciled })
    await refresh()
  }
  const finish = async () => {
    if (!sessionId) return
    await complete.mutateAsync({ accountId: account.id, id: sessionId })
    await refresh()
  }

  return <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
    <DrawerContent>
      <DrawerHeader>
        <DrawerTitle>Conciliar {account.name}</DrawerTitle>
        <DrawerDescription>{session ? "Marca los movimientos que aparecen en tu estado de cuenta." : "Compara tu saldo registrado con el cierre de tu estado de cuenta."}</DrawerDescription>
      </DrawerHeader>
      {!session ? <div className="space-y-4 overflow-y-auto px-4 py-5">
        <div className="rounded-2xl border border-primary/15 bg-primary-soft p-4">
          <Landmark size={18} className="mb-2 text-primary" />
          <p className="text-sm font-medium">Saldo registrado: {formatMoney(account.balance)}</p>
          <p className="mt-1 text-xs text-muted-foreground">Usa el saldo de cierre y la fecha exacta de tu estado de cuenta.</p>
        </div>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">Fecha de cierre<input type="date" value={statementDate} onChange={(event) => setStatementDate(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground" /></label>
        <label className="flex flex-col gap-1.5 text-xs font-medium text-muted-foreground">Saldo de cierre<input inputMode="decimal" type="number" step="0.01" value={statementBalance} onChange={(event) => setStatementBalance(event.target.value)} placeholder="0.00" className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground" /></label>
      </div> : <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {session.status === "stale" && <div className="mb-3 flex gap-2 rounded-xl border border-warning/30 bg-warning/10 p-3 text-xs text-warning"><AlertTriangle size={16} className="shrink-0" />Esta conciliación cambió después de cerrarse. Revisa los movimientos antes de confiar en ella.</div>}
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-border bg-border text-center">
          <div className="bg-card p-3"><p className="text-[10px] font-medium uppercase text-muted-foreground">Conciliado</p><p className="tnum mt-1 text-sm font-semibold">{formatMoney(session.reconciledBalance)}</p></div>
          <div className="bg-card p-3"><p className="text-[10px] font-medium uppercase text-muted-foreground">Diferencia</p><p className={`tnum mt-1 text-sm font-semibold ${session.difference === 0 ? "text-income" : "text-destructive"}`}>{formatMoney(session.difference)}</p></div>
        </div>
        <p className="mt-4 text-xs text-muted-foreground">Estado de cuenta: {formatMoney(session.statementBalance)} al {session.statementDate}</p>
        <ul className="mt-2 divide-y divide-border rounded-2xl border border-border">
          {session.transactions.map((transaction) => <li key={transaction.id} className="flex items-center gap-3 px-3 py-3"><input type="checkbox" checked={transaction.reconciliationStatus === "reconciled"} disabled={session.status !== "open" || toggle.isPending} onChange={(event) => toggleRow(transaction.id, event.target.checked)} className="size-4 accent-primary" aria-label={`Conciliar ${transaction.note ?? "movimiento"}`} /><div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{transaction.note || "Movimiento"}</p><p className="text-xs text-muted-foreground">{transaction.date}</p></div><span className={`tnum text-sm font-semibold ${transaction.type === "income" || transaction.type === "transfer" ? "text-income" : ""}`}>{transaction.type === "expense" ? "−" : "+"}{formatMoney(transaction.amount)}</span></li>)}
        </ul>
      </div>}
      <DrawerFooter>
        {!session ? <button type="button" onClick={start} disabled={!statementDate || !statementBalance || create.isPending} className="pressable h-11 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-50">{create.isPending ? "Iniciando..." : "Iniciar conciliación"}</button> : session.status === "open" ? <button type="button" onClick={finish} disabled={session.difference !== 0 || complete.isPending} className="pressable flex h-11 items-center justify-center gap-2 rounded-xl bg-primary px-4 text-sm font-semibold text-primary-foreground disabled:opacity-50"><CheckCircle2 size={17} />Completar conciliación</button> : <button type="button" onClick={() => onOpenChange(false)} className="pressable h-11 rounded-xl bg-secondary px-4 text-sm font-semibold">Cerrar</button>}
      </DrawerFooter>
    </DrawerContent>
  </Drawer>
}
