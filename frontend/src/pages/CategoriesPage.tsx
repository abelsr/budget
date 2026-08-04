import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Plus } from "lucide-react"
import { motion } from "motion/react"

import { CategoryIcon } from "@/components/CategoryIcon"
import { CategoryFormSheet } from "@/components/CategoryFormSheet"
import { useCategories, useUpdateCategory } from "@/lib/queries"
import { IconButton, PageHeader, SectionTitle, Toggle } from "@/components/ui/surface"
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
      <PageHeader
        title="Categorías"
        back={() => navigate(-1)}
        action={
          <IconButton label="Nueva categoría" variant="primary" onClick={openCreate}>
            <Plus size={20} strokeWidth={2.5} />
          </IconButton>
        }
      />

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
      <SectionTitle>{title}</SectionTitle>
      <div className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
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
                i > 0 ? "border-t border-border" : ""
              } ${c.active ? "" : "opacity-50"}`}
            >
              <CategoryIcon
                icon={c.icon}
                color={c.color}
                size={20}
                className="size-10"
              />
              <p className="flex-1 text-[15px] font-medium">{c.name}</p>
              <Toggle
                checked={c.active}
                onChange={() => onToggle(c)}
                label={`${c.active ? "Desactivar" : "Activar"} ${c.name}`}
              />
            </div>
          ))
        )}
      </div>
    </section>
  )
}
