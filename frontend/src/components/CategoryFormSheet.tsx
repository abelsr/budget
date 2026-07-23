import { useState } from "react"
import { Trash2 } from "lucide-react"
import { motion } from "motion/react"

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
  useCreateCategory,
  useDeleteCategory,
  useUpdateCategory,
} from "@/lib/queries"
import { springIndicator } from "@/lib/springs"
import type { Category } from "@/lib/types"

/** Iconos válidos: mismos nombres del mapa de CategoryIcon. */
const ICON_NAMES = [
  "shopping-cart",
  "utensils",
  "car",
  "house",
  "zap",
  "heart-pulse",
  "gamepad-2",
  "repeat",
  "banknote",
  "hand-coins",
  "wallet",
  "piggy-bank",
]

const COLOR_PRESETS = [
  "#30b0c7",
  "#ff9f0a",
  "#0a84ff",
  "#bf5af2",
  "#ffd60a",
  "#ff375f",
  "#ff6482",
  "#ac8e68",
  "#30d158",
  "#64d2ff",
  "#8e8e93",
  "#5e5ce6",
]

/**
 * Bottom sheet para crear o editar una categoría.
 * En edición el tipo no se puede cambiar y aparece el borrado en dos pasos.
 */
export function CategoryFormSheet({
  open,
  onOpenChange,
  category,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  category?: Category
}) {
  return (
    <Drawer open={open} onOpenChange={onOpenChange} showSwipeHandle>
      <DrawerContent className="mx-auto max-w-lg">
        {open && (
          <CategoryForm
            key={category?.id ?? "new"}
            category={category}
            onDone={() => onOpenChange(false)}
          />
        )}
      </DrawerContent>
    </Drawer>
  )
}

function CategoryForm({
  category,
  onDone,
}: {
  category?: Category
  onDone: () => void
}) {
  const isEditing = category !== undefined
  const createCategory = useCreateCategory()
  const updateCategory = useUpdateCategory()
  const deleteCategory = useDeleteCategory()

  const [name, setName] = useState(category?.name ?? "")
  const [type, setType] = useState<Category["type"]>(category?.type ?? "expense")
  const [icon, setIcon] = useState(category?.icon ?? ICON_NAMES[0])
  const [color, setColor] = useState(category?.color ?? COLOR_PRESETS[0])
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isPending =
    createCategory.isPending ||
    updateCategory.isPending ||
    deleteCategory.isPending
  const canSave = name.trim().length > 0 && !isPending

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
    const input = { name: name.trim(), icon, color, type }
    if (isEditing) {
      updateCategory.mutate(
        { id: category.id, name: input.name, icon, color },
        { onSuccess: onDone, onError },
      )
    } else {
      createCategory.mutate(input, { onSuccess: onDone, onError })
    }
  }

  function remove() {
    if (!category) return
    if (!confirmingDelete) {
      setConfirmingDelete(true)
      return
    }
    setError(null)
    deleteCategory.mutate(category.id, { onSuccess: onDone, onError })
  }

  return (
    <div className="flex flex-col gap-5 px-5 pb-8">
      <DrawerHeader className="p-0 pt-2">
        <DrawerTitle className="text-center text-[17px] font-semibold">
          {isEditing ? "Editar categoría" : "Nueva categoría"}
        </DrawerTitle>
      </DrawerHeader>

      {/* Preview en vivo */}
      <div className="flex items-center justify-center gap-3">
        <CategoryIcon
          icon={icon}
          color={color}
          size={24}
          className="size-12"
        />
        <span className="text-[17px] font-semibold">
          {name.trim() || "Sin nombre"}
        </span>
      </div>

      {/* Nombre */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Nombre
        </p>
        <input
          autoFocus={!isEditing}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Ej. Supermercado"
          className="w-full rounded-xl bg-secondary px-4 py-2.5 text-[15px] outline-none placeholder:text-muted-foreground"
          aria-label="Nombre de la categoría"
        />
      </div>

      {/* Tipo: en edición no se puede cambiar */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Tipo
        </p>
        <div
          className={`flex rounded-xl bg-secondary p-1 ${
            isEditing ? "opacity-50" : ""
          }`}
        >
          {(["expense", "income"] as const).map((t) => (
            <button
              key={t}
              disabled={isEditing}
              onClick={() => setType(t)}
              className="relative flex-1 rounded-lg py-2 text-[14px] font-medium"
            >
              {type === t && (
                <motion.span
                  layoutId="category-type"
                  transition={springIndicator}
                  className="absolute inset-0 rounded-lg bg-card shadow-sm"
                />
              )}
              <span
                className={`relative ${
                  type === t ? "text-foreground" : "text-muted-foreground"
                }`}
              >
                {t === "expense" ? "Gasto" : "Ingreso"}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Icono */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Icono
        </p>
        <div className="grid grid-cols-4 gap-2">
          {ICON_NAMES.map((name) => {
            const selected = icon === name
            return (
              <button
                key={name}
                onClick={() => setIcon(name)}
                aria-label={`Icono ${name}`}
                className="pressable flex items-center justify-center rounded-2xl py-2"
              >
                <CategoryIcon
                  icon={name}
                  color={color}
                  size={22}
                  className={`size-12 transition-shadow ${
                    selected ? "ring-2 ring-offset-2 ring-offset-background" : ""
                  }`}
                  style={{ ["--tw-ring-color" as string]: color }}
                />
              </button>
            )
          })}
        </div>
      </div>

      {/* Color */}
      <div>
        <p className="mb-2 text-[13px] font-medium text-muted-foreground">
          Color
        </p>
        <div className="flex flex-wrap gap-3">
          {COLOR_PRESETS.map((preset) => {
            const selected = color === preset
            return (
              <button
                key={preset}
                onClick={() => setColor(preset)}
                aria-label={`Color ${preset}`}
                className={`pressable size-9 rounded-full transition-shadow ${
                  selected ? "ring-2 ring-offset-2 ring-offset-background" : ""
                }`}
                style={{
                  backgroundColor: preset,
                  ["--tw-ring-color" as string]: preset,
                }}
              />
            )
          })}
        </div>
      </div>

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
          disabled={deleteCategory.isPending}
          className={`pressable flex h-12 items-center justify-center gap-2 rounded-2xl text-[15px] font-semibold transition-colors ${
            confirmingDelete
              ? "bg-expense text-white"
              : "bg-expense/10 text-expense"
          }`}
        >
          <Trash2 size={16} />
          {confirmingDelete
            ? "¿Seguro? Toca para confirmar"
            : "Eliminar categoría"}
        </button>
      )}
    </div>
  )
}
