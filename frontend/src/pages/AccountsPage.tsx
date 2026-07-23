import { CreditCard, Landmark, PiggyBank, Wallet } from "lucide-react"

import { formatMoney } from "@/lib/format"
import { useAccounts } from "@/lib/queries"
import type { AccountKind } from "@/lib/types"

const kindMeta: Record<AccountKind, { label: string; icon: typeof Wallet }> = {
  cash: { label: "Efectivo", icon: Wallet },
  debit: { label: "Débito", icon: Landmark },
  credit: { label: "Crédito", icon: CreditCard },
  savings: { label: "Ahorro", icon: PiggyBank },
}

/** Cuentas del hogar con sus saldos. */
export function AccountsPage() {
  const { data: accounts = [] } = useAccounts()
  const total = accounts.reduce((sum, a) => sum + a.balance, 0)

  return (
    <div className="flex flex-col gap-4">
      <header className="px-1">
        <p className="text-[13px] font-medium text-muted-foreground">
          Total · {formatMoney(total)}
        </p>
        <h1 className="text-[34px] leading-tight font-bold tracking-tight">
          Cuentas
        </h1>
      </header>

      <section className="rounded-3xl bg-card shadow-sm">
        <ul className="divide-y divide-border/60 py-2">
          {accounts.map((a) => {
            const meta = kindMeta[a.kind]
            const Icon = meta.icon
            return (
              <li key={a.id} className="pressable flex items-center gap-3 px-4 py-3">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                  <Icon size={20} />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[15px] font-medium">{a.name}</p>
                  <p className="text-[13px] text-muted-foreground">{meta.label}</p>
                </div>
                <span
                  className={`tnum shrink-0 text-[15px] font-semibold ${
                    a.balance < 0 ? "text-expense" : ""
                  }`}
                >
                  {formatMoney(a.balance)}
                </span>
              </li>
            )
          })}
        </ul>
      </section>

      <p className="px-2 text-center text-[13px] text-muted-foreground">
        La creación y edición de cuentas llegará con el backend.
      </p>
    </div>
  )
}
