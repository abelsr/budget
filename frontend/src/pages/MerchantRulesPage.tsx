import { useState } from "react"
import { ArrowLeft, Plus, Tags, Trash2 } from "lucide-react"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { CategoryIcon } from "@/components/CategoryIcon"
import { ApiError } from "@/lib/api"
import { useCategories, useCreateMerchantRule, useDeleteMerchantRule, useMerchantRules } from "@/lib/queries"

/** Rules turn recurring bank-statement descriptions into useful categories. */
export function MerchantRulesPage() {
  const { data: rules = [] } = useMerchantRules()
  const { data: categories = [] } = useCategories()
  const createRule = useCreateMerchantRule()
  const deleteRule = useDeleteMerchantRule()
  const [pattern, setPattern] = useState("")
  const [categoryId, setCategoryId] = useState("")
  const activeCategories = categories.filter((category) => category.active)
  const error = createRule.error instanceof ApiError ? createRule.error.message : null

  function submit(event: React.FormEvent) {
    event.preventDefault()
    if (!pattern.trim() || !categoryId) return
    createRule.mutate({ pattern: pattern.trim(), categoryId }, {
      onSuccess: () => {
        setPattern("")
        setCategoryId("")
      },
    })
  }

  return (
    <main className="mx-auto flex w-full max-w-xl flex-col gap-5 pb-6">
      <header className="flex min-h-11 items-center gap-3 px-1">
        <Link to="/app/ajustes" aria-label="Volver a ajustes" className="pressable rounded-full p-2 text-muted-foreground"><ArrowLeft size={20} /></Link>
        <div>
          <h1 className="text-xl font-bold tracking-tight">Reglas de comercios</h1>
          <p className="text-[12px] text-muted-foreground">Clasifica automáticamente futuros CSV.</p>
        </div>
      </header>

      <form onSubmit={submit} className="space-y-3 rounded-3xl border border-border bg-card p-4 shadow-sm">
        <label className="block text-[13px] font-medium">Comercio o texto en el estado de cuenta
          <input value={pattern} onChange={(event) => setPattern(event.target.value)} placeholder="Ej. Walmart" maxLength={120} className="mt-1.5 h-11 w-full rounded-xl border border-border bg-background px-3 text-[14px] outline-none focus-visible:ring-2 focus-visible:ring-ring" />
        </label>
        <label className="block text-[13px] font-medium">Categoría
          <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="mt-1.5 h-11 w-full rounded-xl border border-border bg-background px-3 text-[14px] outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <option value="">Selecciona una categoría</option>
            {activeCategories.map((category) => <option key={category.id} value={category.id}>{category.name} ({category.type === "expense" ? "Gasto" : "Ingreso"})</option>)}
          </select>
        </label>
        {error && <p className="text-[13px] text-expense">{error}</p>}
        <Button type="submit" disabled={createRule.isPending || !pattern.trim() || !categoryId} className="pressable h-11 w-full rounded-xl"><Plus size={16} /> Añadir regla</Button>
      </form>

      <section className="overflow-hidden rounded-3xl border border-border bg-card shadow-sm">
        {rules.length === 0 ? <div className="px-5 py-10 text-center"><Tags className="mx-auto mb-3 text-muted-foreground" size={24} /><p className="text-[14px] font-medium">Aún no hay reglas</p><p className="mt-1 text-[12px] text-muted-foreground">Las descripciones coincidentes usarán la categoría que elijas.</p></div> : rules.map((rule, index) => {
          const category = categories.find((item) => item.id === rule.categoryId)
          return <div key={rule.id} className={`flex items-center gap-3 px-4 py-3 ${index ? "border-t border-border" : ""}`}>
            {category ? <CategoryIcon icon={category.icon} color={category.color} className="size-9 shrink-0" size={18} /> : <span className="flex size-9 items-center justify-center rounded-full bg-secondary">?</span>}
            <div className="min-w-0 flex-1"><p className="truncate text-[14px] font-medium">{rule.pattern}</p><p className="text-[12px] text-muted-foreground">{rule.categoryName}</p></div>
            <button type="button" aria-label={`Eliminar regla ${rule.pattern}`} onClick={() => deleteRule.mutate(rule.id)} disabled={deleteRule.isPending} className="pressable rounded-full p-2 text-expense disabled:opacity-50"><Trash2 size={16} /></button>
          </div>
        })}
      </section>
    </main>
  )
}
