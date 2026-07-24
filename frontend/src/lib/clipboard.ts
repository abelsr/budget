/**
 * Copiado al portapapeles con fallback.
 *
 * `navigator.clipboard` solo existe en contextos seguros (HTTPS o localhost).
 * El stack self-hosted se usa por IP local en HTTP plano (celular en la misma
 * red), así que ahí hay que caer al viejo `document.execCommand('copy')`.
 */
export async function copyText(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // contexto no seguro o permiso denegado: seguimos al fallback
    }
  }

  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.setAttribute("readonly", "")
  // Fuera de pantalla pero enfocable (position:fixed evita scroll salto)
  textarea.style.position = "fixed"
  textarea.style.opacity = "0"
  textarea.style.pointerEvents = "none"
  document.body.appendChild(textarea)
  try {
    textarea.select()
    textarea.setSelectionRange(0, text.length)
    return document.execCommand("copy")
  } catch {
    return false
  } finally {
    document.body.removeChild(textarea)
  }
}
