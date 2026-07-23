import { useState } from "react"
import { CreditCard, Landmark, PiggyBank, Plus, Wallet } from "lucide-react"

import { AccountFormSheet } from "@/components/AccountFormSheet"
import { formatMoney } from "@/lib/format"
import { useAccounts } from "@/lib/queries"
import type { Account, AccountKind } from "@/lib/types"

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

  const [sheetOpen, setSheetOpen] = useState(false)
  const [editingAccount, setEditingAccount] = useState<Account | undefined>()

  function openCreate() {
    setEditingAccount(undefined)
    setSheetOpen(true)
  }

  function openEdit(account: Account) {
    setEditingAccount(account)
    setSheetOpen(true)
  }

  return (
    <div className="flex flex-col gap-4">
      <header className="flex items-start justify-between px-1">
        <div>
          <p className="text-[13px] font-medium text-muted-foreground">
            Total · {formatMoney(total)}
          </p>
          <h1 className="text-[34px] leading-tight font-bold tracking-tight">
            Cuentas
          </h1>
        </div>
        <button
          aria-label="Crear cuenta"
          onClick={openCreate}
          className="pressable mt-1 flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
        >
          <Plus size={20} strokeWidth={2.5} />
        </button>
      </header>

      {accounts.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-16 text-center">
          <span className="flex size-16 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
            <Wallet size={28} />
          </span>
          <p className="mt-2 text-[17px] font-semibold">Sin cuentas</p>
          <p className="text-[13px] text-muted-foreground">
            Toca + para crear la primera
          </p>
        </div>
      ) : (
        <section className="rounded-3xl bg-card shadow-sm">
          <ul className="divide-y divide-border/60 py-2">
            {accounts.map((a) => {
              const meta = kindMeta[a.kind]
              const Icon = meta.icon
              return (
                <li
                  key={a.id}
                  onClick={() => openEdit(a)}
                  className="pressable flex cursor-pointer items-center gap-3 px-4 py-3"
                >
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
                    <Icon size={20} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[15px] font-medium">{a.name}</p>
                    <p className="text-[13px] text-muted-foreground">
                      {meta.label}
                    </p>
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
      )}

      <AccountFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        account={editingAccount}
      />
    </div>
  )
}
