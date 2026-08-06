import { useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import {
  AlertTriangle,
  Check,
  ChevronDown,
  FileSpreadsheet,
  History,
  RotateCcw,
  Upload,
} from "lucide-react"
import { motion } from "motion/react"

import { ApiError } from "@/lib/api"
import { formatMoney, formatShortDate } from "@/lib/format"
import {
  useAccounts,
  useCommitImport,
  useImportBatch,
  useImportBatches,
  usePreviewImport,
  useRestoreImportBatch,
  useRevertImportBatch,
} from "@/lib/queries"
import { springAppear } from "@/lib/springs"
import type {
  ImportBatch,
  ImportDateFormat,
  ImportMapping,
  ImportPreview,
  ImportRevertConflict,
} from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, EmptyState, PageHeader } from "@/components/ui/surface"

type Step = "upload" | "review" | "result"

const dateFormats: ImportDateFormat[] = ["DD/MM/YYYY", "MM/DD/YYYY"]

function errorMessage(error: unknown) {
  return error instanceof ApiError ? error.message : "No se pudo completar la operación. Inténtalo de nuevo."
}

function duplicateLabel(reasons: string[]) {
  const labels = { household: "posible duplicado", fingerprint: "ya importado", file: "repetido en el archivo" }
  return reasons.map((reason) => labels[reason as keyof typeof labels] ?? reason).join(" · ")
}

/** Importación segura: se revisa localmente y el servidor vuelve a procesar el CSV al confirmar. */
export function ImportPage() {
  const navigate = useNavigate()
  const { data: accounts = [] } = useAccounts()
  const {
    data: batches = [],
    isLoading: historyLoading,
    isError: historyError,
    error: historyErrorDetail,
    refetch: retryHistory,
  } = useImportBatches()
  const previewImport = usePreviewImport()
  const commitImport = useCommitImport()
  const [step, setStep] = useState<Step>("upload")
  const [file, setFile] = useState<File | null>(null)
  const [accountId, setAccountId] = useState("")
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [mapping, setMapping] = useState<ImportMapping | null>(null)
  const [dateFormat, setDateFormat] = useState<ImportDateFormat | null>(null)
  const [selectedPositions, setSelectedPositions] = useState<Set<number>>(new Set())
  const [result, setResult] = useState<ImportBatch | null>(null)
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  async function previewFile(mappingOverride?: ImportMapping, formatOverride?: ImportDateFormat) {
    if (!file || !accountId) return
    setFormError(null)
    try {
      const response = await previewImport.mutateAsync({
        file,
        accountId,
        mapping: mappingOverride,
        dateFormat: formatOverride,
      })
      setPreview(response)
      setMapping(response.mapping)
      setDateFormat(response.dateFormat)
      setSelectedPositions(new Set(response.rows.filter((row) => row.selected).map((row) => row.sourcePosition)))
      setStep("review")
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  async function commit() {
    if (!file || !mapping || !dateFormat || selectedPositions.size === 0) return
    setFormError(null)
    try {
      const response = await commitImport.mutateAsync({
        file,
        accountId,
        mapping,
        dateFormat,
        selectedPositions: [...selectedPositions].sort((a, b) => a - b),
      })
      setResult(response.batch)
      setSelectedBatchId(response.batch.id)
      setStep("result")
    } catch (error) {
      setFormError(errorMessage(error))
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={springAppear}
      className="mx-auto flex w-full max-w-5xl flex-col gap-5 pb-6"
    >
      <PageHeader title="Importar movimientos" back={() => navigate(-1)} />

      <ol aria-label="Progreso de importación" className="grid grid-cols-3 gap-2">
        <StepIndicator number={1} label="Archivo" active={step === "upload"} complete={step !== "upload"} />
        <StepIndicator number={2} label="Revisar" active={step === "review"} complete={step === "result"} />
        <StepIndicator number={3} label="Resultado" active={step === "result"} complete={false} />
      </ol>

      {formError && <ErrorNotice message={formError} />}

      {step === "upload" && (
        <UploadStep
          accounts={accounts}
          file={file}
          accountId={accountId}
          pending={previewImport.isPending}
          onFile={setFile}
          onAccount={setAccountId}
          onPreview={() => previewFile()}
        />
      )}
      {step === "review" && preview && mapping && dateFormat && (
        <ReviewStep
          preview={preview}
          mapping={mapping}
          dateFormat={dateFormat}
          selectedPositions={selectedPositions}
          pending={previewImport.isPending || commitImport.isPending}
          onMapping={setMapping}
          onDateFormat={setDateFormat}
          onRepreview={() => previewFile(mapping, dateFormat)}
          onToggle={(position) => setSelectedPositions((current) => {
            const next = new Set(current)
            if (next.has(position)) next.delete(position)
            else next.add(position)
            return next
          })}
          onSelectAll={() => setSelectedPositions(new Set(preview.rows.map((row) => row.sourcePosition)))}
          onSelectNone={() => setSelectedPositions(new Set())}
          onCommit={commit}
          onBack={() => setStep("upload")}
        />
      )}
      {step === "result" && result && (
        <ResultStep batch={result} onNew={() => {
          setFile(null)
          setPreview(null)
          setMapping(null)
          setResult(null)
          setSelectedPositions(new Set())
          setStep("upload")
        }} />
      )}

      <ImportHistory
        batches={batches}
        loading={historyLoading}
        error={historyError ? errorMessage(historyErrorDetail) : null}
        onRetry={() => { void retryHistory() }}
        selectedBatchId={selectedBatchId}
        onSelect={setSelectedBatchId}
      />
    </motion.div>
  )
}

function StepIndicator({ number, label, active, complete }: { number: number; label: string; active: boolean; complete: boolean }) {
  return <li className={`flex items-center gap-2 rounded-xl px-2 py-2 text-[12px] font-medium ${active ? "bg-primary/10 text-primary" : "text-muted-foreground"}`}>
    <span className={`flex size-6 shrink-0 items-center justify-center rounded-full text-[11px] ${active || complete ? "bg-primary text-primary-foreground" : "bg-secondary"}`}>{complete ? <Check size={14} /> : number}</span>
    <span className="truncate">{label}</span>
  </li>
}

function UploadStep({ accounts, file, accountId, pending, onFile, onAccount, onPreview }: {
  accounts: { id: string; name: string; bank?: string | null }[]; file: File | null; accountId: string; pending: boolean
  onFile: (file: File | null) => void; onAccount: (id: string) => void; onPreview: () => void
}) {
  return <Card className="mx-auto w-full max-w-2xl p-4 sm:p-6">
    <div className="flex items-start gap-3">
      <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary"><FileSpreadsheet size={21} /></span>
      <div><h2 className="text-[17px] font-semibold">Elige el extracto</h2><p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">El archivo se envía para analizarlo en memoria. Solo las filas que confirmes se guardan. Aceptamos CSV de hasta 5 MB.</p></div>
    </div>
    <div className="mt-6 grid gap-4 sm:grid-cols-2">
      <label className="grid gap-1.5 text-[13px] font-medium">Cuenta de destino
        <select value={accountId} onChange={(event) => onAccount(event.target.value)} className="h-10 rounded-xl border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50">
          <option value="">Selecciona una cuenta</option>
          {accounts.map((account) => <option key={account.id} value={account.id}>{account.name}{account.bank ? ` · ${account.bank}` : ""}</option>)}
        </select>
      </label>
      <label className="grid gap-1.5 text-[13px] font-medium">Archivo CSV
        <input type="file" accept=".csv,text/csv" onChange={(event) => onFile(event.target.files?.[0] ?? null)} className="h-10 w-full rounded-xl border border-input bg-background px-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-secondary file:px-2 file:py-1 file:text-[12px] file:font-semibold" />
      </label>
    </div>
    {file && <p className="mt-3 rounded-xl bg-secondary px-3 py-2 text-[12px] text-muted-foreground"><strong className="text-foreground">{file.name}</strong> · {(file.size / 1024).toFixed(1)} KB</p>}
    <Button className="mt-6 h-10 w-full rounded-xl" disabled={!file || !accountId || pending} onClick={onPreview}><Upload size={16} />{pending ? "Analizando…" : "Analizar archivo"}</Button>
  </Card>
}

function ReviewStep({ preview, mapping, dateFormat, selectedPositions, pending, onMapping, onDateFormat, onRepreview, onToggle, onSelectAll, onSelectNone, onCommit, onBack }: {
  preview: ImportPreview; mapping: ImportMapping; dateFormat: ImportDateFormat; selectedPositions: Set<number>; pending: boolean
  onMapping: (mapping: ImportMapping) => void; onDateFormat: (format: ImportDateFormat) => void; onRepreview: () => void; onToggle: (position: number) => void; onSelectAll: () => void; onSelectNone: () => void; onCommit: () => void; onBack: () => void
}) {
  const updateMapping = (key: keyof ImportMapping, value: string) => onMapping({ ...mapping, [key]: value })
  const needsRepreview = mapping.date !== preview.mapping.date
    || mapping.amount !== preview.mapping.amount
    || mapping.description !== preview.mapping.description
    || dateFormat !== preview.dateFormat
  return <div className="grid gap-5 lg:grid-cols-[18rem_minmax(0,1fr)]">
    <Card className="h-fit p-4">
      <h2 className="text-[16px] font-semibold">Verifica las columnas</h2>
      <p className="mt-1 text-[12px] leading-relaxed text-muted-foreground">Si cambias el formato o una columna, analizaremos de nuevo el archivo.</p>
      <div className="mt-4 grid gap-3">
        {(["date", "amount", "description"] as const).map((key) => <label key={key} className="grid gap-1 text-[12px] font-medium capitalize">{key === "date" ? "Fecha" : key === "amount" ? "Importe" : "Descripción"}
          <select value={mapping[key]} onChange={(event) => updateMapping(key, event.target.value)} className="h-9 rounded-lg border border-input bg-background px-2 text-sm">
            {preview.headers.map((header) => <option key={header} value={header}>{header}</option>)}
          </select>
        </label>)}
        <label className="grid gap-1 text-[12px] font-medium">Formato de fecha
          <select value={dateFormat} onChange={(event) => onDateFormat(event.target.value as ImportDateFormat)} className="h-9 rounded-lg border border-input bg-background px-2 text-sm">
            {dateFormats.map((format) => <option key={format}>{format}</option>)}
          </select>
        </label>
      </div>
      <Button variant="outline" className="mt-4 w-full" disabled={pending} onClick={onRepreview}><RotateCcw size={14} />{pending ? "Actualizando…" : "Actualizar vista"}</Button>
    </Card>
    <Card className="min-w-0 overflow-hidden">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border px-4 py-3">
        <div className="mr-auto"><h2 className="text-[16px] font-semibold">Movimientos detectados</h2><p className="text-[12px] text-muted-foreground">{selectedPositions.size} de {preview.rows.length} seleccionados</p></div>
        <button type="button" onClick={onSelectAll} className="pressable text-[12px] font-semibold text-primary">Seleccionar todos</button>
        <button type="button" onClick={onSelectNone} className="pressable text-[12px] font-semibold text-primary">Ninguno</button>
      </div>
      <div className="max-h-[45dvh] overflow-auto">
        <table className="w-full min-w-[38rem] text-left text-[13px]"><thead className="sticky top-0 bg-card text-[11px] text-muted-foreground"><tr><th className="w-12 px-4 py-2"><span className="sr-only">Seleccionar</span></th><th className="py-2">Fecha</th><th className="py-2">Descripción</th><th className="px-4 py-2 text-right">Importe</th></tr></thead><tbody>
          {preview.rows.map((row) => <tr key={row.sourcePosition} className="border-t border-border align-top"><td className="px-4 py-3"><input aria-label={`Seleccionar fila ${row.sourcePosition}`} type="checkbox" checked={selectedPositions.has(row.sourcePosition)} onChange={() => onToggle(row.sourcePosition)} className="size-4 accent-primary" /></td><td className="whitespace-nowrap py-3">{formatShortDate(row.date)}</td><td className="max-w-64 py-3"><p className="truncate font-medium">{row.description || "Sin descripción"}</p>{row.duplicateReasons.length > 0 && <p className="mt-0.5 flex items-center gap-1 text-[11px] text-amber-700 dark:text-amber-400"><AlertTriangle size={12} />{duplicateLabel(row.duplicateReasons)}</p>}</td><td className={`px-4 py-3 text-right font-semibold tabular-nums ${row.amount > 0 ? "text-income" : "text-expense"}`}>{row.amount > 0 ? "+" : "−"}{formatMoney(Math.abs(row.amount))}</td></tr>)}
        </tbody></table>
      </div>
      <div className="border-t border-border p-3"><div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-between"><Button variant="secondary" onClick={onBack}>Cambiar archivo</Button><Button className="h-9" disabled={!selectedPositions.size || pending || needsRepreview} onClick={onCommit}>{pending ? "Importando…" : `Importar ${selectedPositions.size} movimientos`}</Button></div>{needsRepreview && <p role="status" className="mt-2 text-right text-[12px] text-amber-700 dark:text-amber-400">Actualiza la vista antes de confirmar los cambios de columnas o fecha.</p>}</div>
    </Card>
  </div>
}

function ResultStep({ batch, onNew }: { batch: ImportBatch; onNew: () => void }) {
  return <Card className="mx-auto w-full max-w-2xl p-5 text-center sm:p-7"><span className="mx-auto flex size-14 items-center justify-center rounded-full bg-income/15 text-income"><Check size={28} /></span><h2 className="mt-4 text-xl font-bold">Importación terminada</h2><p className="mt-1 text-[13px] text-muted-foreground">Lote <span className="font-mono text-[11px] text-foreground">{batch.id}</span></p><div className="mt-6 grid grid-cols-2 overflow-hidden rounded-2xl border border-border"><div className="border-r border-border p-4"><p className="text-2xl font-bold tabular-nums">{batch.importedCount}</p><p className="text-[12px] text-muted-foreground">importados</p></div><div className="p-4"><p className="text-2xl font-bold tabular-nums">{batch.skippedCount}</p><p className="text-[12px] text-muted-foreground">omitidos</p></div></div><div className="mt-5 flex flex-col gap-2 sm:flex-row sm:justify-center"><Button onClick={onNew}>Importar otro archivo</Button><Button variant="outline" render={<Link to={`/app/transacciones?accountId=${batch.accountId}`} />}>Ver movimientos</Button></div></Card>
}

function ImportHistory({ batches, loading, error, onRetry, selectedBatchId, onSelect }: { batches: ImportBatch[]; loading: boolean; error: string | null; onRetry: () => void; selectedBatchId: string | null; onSelect: (id: string) => void }) {
  const [open, setOpen] = useState(Boolean(selectedBatchId))
  useEffect(() => {
    if (selectedBatchId) setOpen(true)
  }, [selectedBatchId])
  const selected = selectedBatchId ?? batches[0]?.id ?? null
  return <section><button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex w-full items-center gap-2 px-1 text-left"><History size={17} /><span className="flex-1 text-[15px] font-semibold">Historial de importaciones</span><ChevronDown size={16} className={`transition-transform ${open ? "rotate-180" : ""}`} /></button>{open && (error ? <RetryNotice message={`No se pudo cargar el historial. ${error}`} onRetry={onRetry} /> : <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(16rem,0.7fr)_minmax(0,1.3fr)]"><Card className="overflow-hidden">{loading ? <p className="p-4 text-[13px] text-muted-foreground">Cargando…</p> : batches.length === 0 ? <EmptyState icon={<History size={22} />} title="Sin importaciones" hint="Los lotes confirmados aparecerán aquí." /> : batches.map((batch) => <button key={batch.id} type="button" onClick={() => onSelect(batch.id)} className={`pressable w-full border-b border-border px-4 py-3 text-left last:border-0 ${selected === batch.id ? "bg-primary/5" : ""}`}><p className="truncate text-[14px] font-semibold">{batch.sourceFilename}</p><p className="mt-0.5 text-[12px] text-muted-foreground">{new Date(batch.createdAt).toLocaleDateString("es-MX")} · {batch.importedCount} importados</p></button>)}</Card><BatchDetail batchId={selected} /></div>)}</section>
}

function BatchDetail({ batchId }: { batchId: string | null }) {
  const { data: batch, isLoading, isError, error, refetch } = useImportBatch(batchId)
  const revert = useRevertImportBatch()
  const restore = useRestoreImportBatch()
  const [confirming, setConfirming] = useState(false)
  const [conflicts, setConflicts] = useState<ImportRevertConflict[]>([])
  const [mutationError, setMutationError] = useState<string | null>(null)
  if (!batchId) return null
  if (isLoading) return <Card className="p-4 text-[13px] text-muted-foreground">Cargando lote…</Card>
  if (isError || !batch) return <RetryNotice message={`No se pudo cargar el lote. ${isError ? errorMessage(error) : "Inténtalo de nuevo."}`} onRetry={() => { void refetch() }} />
  const reverted = batch.rows.filter((row) => row.currentTransaction?.deleteReason === "import_revert").length
  const batchIdToRevert = batch.id
  function isConflict(error: unknown): error is ApiError & { detail: { conflicts: ImportRevertConflict[] } } {
    return error instanceof ApiError
      && error.status === 409
      && typeof error.detail === "object"
      && error.detail !== null
      && "conflicts" in error.detail
      && Array.isArray(error.detail.conflicts)
      && error.detail.conflicts.length > 0
      && error.detail.conflicts.every((conflict) => typeof conflict === "object" && conflict !== null
        && "rowId" in conflict && typeof conflict.rowId === "string"
        && "transactionId" in conflict && typeof conflict.transactionId === "string")
  }
  async function doRevert() { try { setConflicts([]); setMutationError(null); await revert.mutateAsync(batchIdToRevert); setConfirming(false) } catch (error) { if (isConflict(error)) setConflicts(error.detail.conflicts); else setMutationError(errorMessage(error)) } }
  async function doRestore() { try { setMutationError(null); await restore.mutateAsync(batchIdToRevert) } catch (error) { setMutationError(errorMessage(error)) } }
  return <Card className="overflow-hidden"><div className="border-b border-border p-4"><p className="text-[16px] font-semibold">{batch.sourceFilename}</p><p className="mt-1 text-[12px] text-muted-foreground">{batch.selectedCount} seleccionados · {batch.importedCount} creados · {batch.skippedCount} omitidos</p><p className="mt-1 text-[11px] text-muted-foreground">{batch.editEvents.length} eventos de edición · ID {batch.id}</p></div><div className="max-h-52 overflow-auto">{batch.rows.map((row) => <div key={row.id} className="border-b border-border px-4 py-2.5 text-[12px]"><div className="flex justify-between gap-3"><span className="truncate font-medium">{row.currentTransaction?.note ?? `Fila ${row.sourcePosition}`}</span><span className="tabular-nums">{row.currentTransaction ? formatMoney(row.currentTransaction.amount) : "Omitido"}</span></div><p className="mt-0.5 text-muted-foreground">Fila {row.sourcePosition} · {row.status}{row.editEvents.length ? ` · ${row.editEvents.length} edición(es)` : ""}</p></div>)}</div>{conflicts.length > 0 && <div role="alert" className="m-3 rounded-xl bg-expense/10 p-3 text-[12px] text-expense">No se pudo revertir: {conflicts.length} movimiento(s) cambiaron desde la importación. Revisa sus ediciones antes de intentarlo.</div>}{mutationError && <ErrorNotice message={mutationError} />}<div className="flex flex-wrap items-center gap-2 p-3">{reverted > 0 ? <Button disabled={restore.isPending} onClick={doRestore}><RotateCcw size={14} />{restore.isPending ? "Restaurando…" : `Restaurar ${reverted} movimientos`}</Button> : confirming ? <><span className="mr-auto text-[12px] text-muted-foreground">Se ocultarán {batch.importedCount} movimientos sin cambios.</span><Button variant="secondary" onClick={() => setConfirming(false)}>Cancelar</Button><Button variant="destructive" disabled={revert.isPending} onClick={doRevert}>{revert.isPending ? "Revirtiendo…" : "Confirmar reversión"}</Button></> : <Button variant="destructive" onClick={() => setConfirming(true)}><RotateCcw size={14} />Revertir lote</Button>}</div></Card>
}

function ErrorNotice({ message }: { message: string }) { return <div role="alert" className="flex items-center gap-2 rounded-2xl border border-expense/25 bg-expense/10 px-4 py-3 text-[13px] text-expense"><AlertTriangle size={16} /><span>{message}</span></div> }
function RetryNotice({ message, onRetry }: { message: string; onRetry: () => void }) { return <Card className="mt-3 p-4"><ErrorNotice message={message} /><Button variant="outline" className="mt-3" onClick={onRetry}>Reintentar</Button></Card> }
