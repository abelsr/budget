import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { ChevronLeft, Plus } from "lucide-react"
import { motion } from "motion/react"

import { CategoryIcon } from "@/components/CategoryIcon"
import { CategoryFormSheet } from "@/components/CategoryFormSheet"
import { useCategories, useUpdateCategory } from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import type { Category } from "@/lib/types"

/**
 * Gestión de categorías del hogar: crear, editar, activar/desactivar.
 * Estilo lista iOS, agrupadas por tipo (Gastos / Ingresos).
 */
export function CategoriesPage() {
  const navigate = useNavigate()
  const { data: categories = [] } = useCategories()
  const updateCategory = useUpdateCategory()

  const [sheetOpen, setSheetOpen] = useState(false)
  const [editing, setEditing] = useState<Category | undefined>(undefined)

  const expenses = useMemo(
    () => categories.filter((c) => c.type === "expense"),
    [categories],
  )
  const incomes = useMemo(
    () => categories.filter((c) => c.type === "income"),
    [categories],
  )

  function openCreate() {
    setEditing(undefined)
    setSheetOpen(true)
  }

  function openEdit(category: Category) {
    setEditing(category)
    setSheetOpen(true)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="flex max-w-2xl flex-col gap-5"
    >
      <header className="flex items-center gap-2 px-1">
        <button
          onClick={() => navigate(-1)}
          aria-label="Volver"
          className="pressable flex size-9 items-center justify-center rounded-full bg-secondary text-secondary-foreground"
        >
          <ChevronLeft size={20} />
        </button>
        <h1 className="flex-1 text-[34px] leading-tight font-bold tracking-tight">
          Categorías
        </h1>
        <button
          onClick={openCreate}
          aria-label="Nueva categoría"
          className="pressable flex size-9 items-center justify-center rounded-full bg-primary text-primary-foreground"
        >
          <Plus size={20} strokeWidth={2.5} />
        </button>
      </header>

      <CategorySection
        title="Gastos"
        categories={expenses}
        onEdit={openEdit}
        onToggle={(c) =>
          updateCategory.mutate({ id: c.id, active: !c.active })
        }
      />
      <CategorySection
        title="Ingresos"
        categories={incomes}
        onEdit={openEdit}
        onToggle={(c) =>
          updateCategory.mutate({ id: c.id, active: !c.active })
        }
      />

      <CategoryFormSheet
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        category={editing}
      />
    </motion.div>
  )
}

function CategorySection({
  title,
  categories,
  onEdit,
  onToggle,
}: {
  title: string
  categories: Category[]
  onEdit: (category: Category) => void
  onToggle: (category: Category) => void
}) {
  return (
    <section>
      <h2 className="mb-1.5 px-4 text-[13px] font-medium text-muted-foreground">
        {title}
      </h2>
      <div className="overflow-hidden rounded-3xl bg-card shadow-sm">
        {categories.length === 0 ? (
          <p className="px-4 py-3.5 text-[13px] text-muted-foreground">
            Sin categorías
          </p>
        ) : (
          categories.map((c, i) => (
            <div
              key={c.id}
              onClick={() => onEdit(c)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault()
                  onEdit(c)
                }
              }}
              className={`pressable flex w-full cursor-pointer items-center gap-3 px-4 py-3 text-left ${
                i > 0 ? "border-t border-border/60" : ""
              } ${c.active ? "" : "opacity-50"}`}
            >
              <CategoryIcon
                icon={c.icon}
                color={c.color}
                size={20}
                className="size-10"
              />
              <p className="flex-1 text-[15px] font-medium">{c.name}</p>
              <button
                role="switch"
                aria-checked={c.active}
                aria-label={`${c.active ? "Desactivar" : "Activar"} ${c.name}`}
                onClick={(e) => {
                  e.stopPropagation()
                  onToggle(c)
                }}
                className={`relative h-6 w-11 shrink-0 rounded-full transition-colors ${
                  c.active ? "bg-primary" : "bg-muted"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 size-5 rounded-full bg-white shadow transition-transform ${
                    c.active ? "translate-x-5" : "translate-x-0"
                  }`}
                />
              </button>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
