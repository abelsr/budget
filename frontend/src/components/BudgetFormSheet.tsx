import { useState } from "react"
import { Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Drawer,
  DrawerContent,
  DrawerHeader,
  DrawerTitle,
} from "@/components/ui/drawer"
import { CategoryIcon } from "@/components/CategoryIcon"
import { ApiError } from "@/lib/api"
import {
  useBudgets,
  useCategories,
  useCreateBudget,
  useDeleteBudget,
  useUpdateBudget,
} from "@/lib/queries"
import type { Budget } from "@/lib/types"

/**
 * Bottom sheet para crear o editar un límite de presupuesto.
 * En edición la categoría no se puede cambiar; en creación solo se listan
 * categorías de gasto que todavía no tienen un límite en ese periodo.
 */
export function BudgetFormSheet({
  open,
  onOpenChange,
  budget,
  defaultMonth,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  budget?: Budget
  /** YYYY-MM mostrado por la tarjeta desde la que se abre el formulario. */
  defaultMonth?: string
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <BudgetForm
            key={budget?.id ?? "new"}
            budget={budget}
            defaultMonth={defaultMonth}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function BudgetForm({
  budget,
  defaultMonth,
  onDone,
}: {
  budget?: Budget
  defaultMonth?: string
  onDone: () => void
}) {
  const isEditing = budget !== undefined
  const { data: categories = [] } = useCategories()
  const { data: budgets = [] } = useBudgets()
  const createBudget = useCreateBudget()
  const updateBudget = useUpdateBudget()
  const deleteBudget = useDeleteBudget()

  const initialMonth = budget?.month?.slice(0, 7) ?? defaultMonth ?? currentMonth()
  const [month, setMonth] = useState(initialMonth)
  const [isDefault, setIsDefault] = useState(budget?.month === null && budget !== undefined)
  const scopedBudgets = new Set(
    budgets
      .filter((item) => (isDefault ? item.month === null : item.month?.slice(0, 7) === month))
      .map((item) => item.categoryId),
  )
  const availableCategories = categories.filter(
    (c) => c.type === "expense" && (isEditing || !scopedBudgets.has(c.id)),
  )

  const [categoryId, setCategoryId] = useState(
    budget?.categoryId ?? availableCategories[0]?.id ?? "",
  )
  const [amount, setAmount] = useState(budget ? String(budget.amount) : "")
  const [rollover, setRollover] = useState(budget?.rollover ?? false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPending =
    createBudget.isPending || updateBudget.isPending || deleteBudget.isPending
  const parsedAmount = Number(amount)
  const selectedCategoryIsAvailable = isEditing || availableCategories.some((c) => c.id === categoryId)
  const canSave =
    categoryId !== "" && selectedCategoryIsAvailable && parsedAmount > 0 && !isPending && !Number.isNaN(parsedAmount)

  function onError(err: unknown) {
    setError(
      err instanceof ApiError
        ? err.message
        : "Ocurrió un error. Intenta de nuevo.",
    )
  }

  function save() {
    if (!canSave) return
    setError(null)
    if (isEditing) {
      updateBudget.mutate(
        { id: budget.id, amount: parsedAmount, rollover },
        { onSuccess: onDone, onError },
      )
    } else {
      createBudget.mutate(
        { categoryId, amount: parsedAmount, month: isDefault ? null : `${month}-01`, rollover },
        { onSuccess: onDone, onError },
      )
    }
  }

  function remove() {
    if (!budget) return
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    setError(null)
    deleteBudget.mutate(budget.id, { onSuccess: onDone, onError })
  }

  const selectedCategory = categories.find((c) => c.id === categoryId)

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          {isEditing ? "Editar presupuesto" : "Nuevo presupuesto"}
        </DrawerTitle>
      </DrawerHeader>

      {/* Preview en vivo */}
      {selectedCategory && (
        <div className="flex items-center justify-center gap-3">
          <CategoryIcon
            icon={selectedCategory.icon}
            color={selectedCategory.color}
            size={24}
            className="size-12"
          />
          <span className="text-[17px] font-semibold">{selectedCategory.name}</span>
        </div>
      )}

      {/* Categoría: en edición no se puede cambiar */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Categoría
        </p>
        {isEditing ? (
          <p className="rounded-xl bg-secondary px-4 py-2.5 text-[15px] opacity-50">
            {selectedCategory?.name ?? "—"}
          </p>
        ) : availableCategories.length === 0 ? (
          <p className="rounded-xl bg-secondary px-4 py-2.5 text-[13px] text-muted-foreground">
            Todas las categorías de gasto ya tienen un límite.
          </p>
        ) : (
          <div className="flex gap-2 overflow-x-auto pb-1">
            {availableCategories.map((c) => (
              <button
                key={c.id}
                onClick={() => setCategoryId(c.id)}
                className={`pressable shrink-0 rounded-full px-4 py-1.5 text-[13px] font-medium transition-colors ${
                  categoryId === c.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-secondary-foreground"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {!isEditing && (
        <div>
          <p className="mb-2 text-[13px] font-medium text-muted-foreground">Periodo</p>
          <input
            type="month"
            value={month}
            disabled={isDefault}
            onChange={(event) => setMonth(event.target.value)}
            className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none disabled:opacity-50"
            aria-label="Mes del presupuesto"
          />
          <label className="mt-2 flex cursor-pointer items-center gap-2 text-[12px] text-muted-foreground">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(event) => setIsDefault(event.target.checked)}
            />
            Usar como límite predeterminado para meses sin presupuesto
          </label>
        </div>
      )}

      {/* Monto */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Límite mensual
        </p>
        <input
          autoFocus={!isEditing}
          inputMode="decimal"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="0.00"
          className="tnum w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
          aria-label="Límite mensual"
        />
      </div>

      <label className="flex cursor-pointer items-start gap-3 rounded-xl bg-secondary px-4 py-3 text-[13px]">
        <input
          type="checkbox"
          checked={rollover}
          onChange={(event) => setRollover(event.target.checked)}
          className="mt-0.5"
        />
        <span>
          <span className="block font-medium">Arrastrar sobrante al mes siguiente</span>
          <span className="mt-0.5 block text-[11px] text-muted-foreground">El saldo sin gastar de este mes se suma a la disponibilidad del siguiente.</span>
        </span>
      </label>

      {error && (
        <p className="rounded-xl bg-expense/10 px-3 py-2 text-[13px] text-expense">
          {error}
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

      {isEditing && (
        <button
          onClick={remove}
          disabled={deleteBudget.isPending}
          className={`pressable flex h-12 items-center justify-center gap-2 rounded-2xl text-[15px] font-semibold transition-colors ${
            confirmingDelete
              ? "bg-expense text-white"
              : "bg-expense/10 text-expense"
          }`}
        >
          <Trash2 size={16} />
          {confirmingDelete
            ? "¿Seguro? Toca para confirmar"
            : "Eliminar presupuesto"}
        </button>
      )}
    </div>
  )
}

function currentMonth() {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`
}
