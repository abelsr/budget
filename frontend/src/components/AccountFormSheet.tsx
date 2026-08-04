import { useState } from "react"
import { CreditCard, Landmark, PiggyBank, Wallet } from "lucide-react"

import { AccountCard } from "@/components/AccountCard"
import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { ApiError } from "@/lib/api"
import { BANK_SUGGESTIONS } from "@/lib/brands"
import {
  useCreateAccount,
  useDeleteAccount,
  useUpdateAccount,
} from "@/lib/queries"
import type { Account, AccountKind, CardBrand } from "@/lib/types"

const kindOptions: { kind: AccountKind; label: string; icon: typeof Wallet }[] = [
  { kind: "cash", label: "Efectivo", icon: Wallet },
  { kind: "debit", label: "Débito", icon: Landmark },
  { kind: "credit", label: "Crédito", icon: CreditCard },
  { kind: "savings", label: "Ahorro", icon: PiggyBank },
]

const brandOptions: { value: CardBrand; label: string }[] = [
  { value: "visa", label: "Visa" },
  { value: "mastercard", label: "Mastercard" },
  { value: "amex", label: "Amex" },
  { value: "other", label: "Otra" },
]

interface AccountFormSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Si viene, el sheet edita esa cuenta; si no, crea una nueva. */
  account?: Account
}

/** Bottom sheet para crear o editar una cuenta del hogar. */
export function AccountFormSheet({
  open,
  onOpenChange,
  account,
}: AccountFormSheetProps) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <AccountForm account={account} onDone={() => onOpenChange(false)} />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function AccountForm({
  account,
  onDone,
}: {
  account?: Account
  onDone: () => void
}) {
  const createAccount = useCreateAccount()
  const updateAccount = useUpdateAccount()
  const deleteAccount = useDeleteAccount()

  const [name, setName] = useState(account?.name ?? "")
  const [kind, setKind] = useState<AccountKind>(account?.kind ?? "cash")
  const [balanceText, setBalanceText] = useState(
    account ? String(account.openingBalance) : "0",
  )
  const [bank, setBank] = useState(account?.bank ?? "")
  const [cardBrand, setCardBrand] = useState<CardBrand | "">(
    account?.cardBrand ?? "",
  )
  const [lastFour, setLastFour] = useState(account?.lastFour ?? "")
  const [confirmingDelete, setConfirmingDelete] = useState(false)

  const openingBalance = Number(balanceText.replace(",", ".")) || 0
  const lastFourValid = lastFour === "" || /^\d{4}$/.test(lastFour)
  const isPending =
    createAccount.isPending ||
    updateAccount.isPending ||
    deleteAccount.isPending
  const canSave = name.trim().length > 0 && lastFourValid && !isPending

  const error =
    createAccount.error ?? updateAccount.error ?? deleteAccount.error
  const errorMessage =
    error instanceof ApiError
      ? error.message
      : error
        ? "Ocurrió un error inesperado"
        : null

  function save() {
    if (!canSave) return
    const input = {
      name: name.trim(),
      kind,
      openingBalance,
      bank: bank.trim() || null,
      cardBrand: cardBrand || null,
      lastFour: lastFour || null,
    }
    if (account) {
      updateAccount.mutate({ id: account.id, ...input }, { onSuccess: onDone })
    } else {
      createAccount.mutate(input, { onSuccess: onDone })
    }
  }

  /** Eliminación en dos pasos: el primer toque pide confirmación inline. */
  function remove() {
    if (!account || isPending) return
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    deleteAccount.mutate(account.id, {
      onSuccess: onDone,
      onError: () => setConfirmingDelete(false),
    })
  }

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          {account ? "Editar cuenta" : "Nueva cuenta"}
        </DrawerTitle>
      </DrawerHeader>

      {/* Nombre */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Nombre
        </p>
        <input
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ej. Cuenta nómina"
          className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
          aria-label="Nombre de la cuenta"
        />
      </div>

      {/* Tipo */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Tipo
        </p>
        <div className="grid grid-cols-2 gap-2">
          {kindOptions.map(({ kind: k, label, icon: Icon }) => {
            const selected = kind === k
            return (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`pressable flex items-center gap-2 rounded-xl px-4 py-2.5 text-[14px] font-medium transition-colors ${
                  selected
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                }`}
              >
                <Icon size={18} />
                {label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Saldo inicial */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Saldo inicial
        </p>
        <input
          inputMode="decimal"
          value={balanceText}
          onChange={(e) =>
            setBalanceText(e.target.value.replace(/[^0-9.,-]/g, ""))
          }
          className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none"
          aria-label="Saldo inicial"
        />
      </div>

      {/* Datos de tarjeta (opcional) — activan el widget tipo wallet */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Datos de tarjeta <span className="font-normal">(opcional)</span>
        </p>
        <div className="flex flex-col gap-2">
          <input
            list="bank-suggestions"
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            placeholder="Banco (ej. BBVA)"
            className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
            aria-label="Banco"
          />
          <datalist id="bank-suggestions">
            {BANK_SUGGESTIONS.map((b) => (
              <option key={b} value={b} />
            ))}
          </datalist>
          <div className="flex gap-2">
            <input
              inputMode="numeric"
              maxLength={4}
              value={lastFour}
              onChange={(e) =>
                setLastFour(e.target.value.replace(/\D/g, "").slice(0, 4))
              }
              placeholder="Últimos 4 dígitos"
              className="tnum w-36 rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
              aria-label="Últimos 4 dígitos de la tarjeta"
            />
            <div className="flex flex-1 gap-1.5">
              {brandOptions.map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setCardBrand(value)}
                  className={`pressable flex-1 rounded-xl px-2 py-2.5 text-[12px] font-medium transition-colors ${
                    cardBrand === value
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary text-secondary-foreground"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {lastFour !== "" && !lastFourValid && (
            <p className="text-[12px] text-expense">Deben ser 4 dígitos.</p>
          )}
        </div>
      </div>

      {/* Vista previa del widget tipo wallet */}
      {lastFour !== "" && (
        <div>
          <p className="mb-2 text-[13px] font-medium text-muted-foreground">
            Vista previa
          </p>
          <AccountCard
            account={{
              id: account?.id ?? "preview",
              householdId: account?.householdId ?? "",
              name: name.trim() || "Nombre de la cuenta",
              kind,
              openingBalance,
              balance: openingBalance,
              bank: bank.trim() || null,
              cardBrand: cardBrand || null,
              lastFour,
            }}
          />
        </div>
      )}

      {errorMessage && (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">
          {errorMessage}
        </p>
      )}

      <Button
        size="lg"
        disabled={!canSave}
        onClick={save}
        className="pressable h-12 rounded-2xl text-[16px] font-semibold"
      >
        Guardar
      </Button>

      {account && (
        <button
          type="button"
          onClick={remove}
          disabled={isPending}
          className={`pressable h-12 rounded-2xl text-[15px] font-semibold text-expense transition-colors ${
            confirmingDelete ? "bg-expense/10" : ""
          }`}
        >
          {confirmingDelete ? "¿Seguro? Toca para confirmar" : "Eliminar cuenta"}
        </button>
      )}
    </div>
  )
}
