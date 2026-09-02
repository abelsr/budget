import "fake-indexeddb/auto"

// jsdom expone `navigator.onLine = true` por defecto; se sobrescribe por test.
Object.defineProperty(window.navigator, "onLine", {
  configurable: true,
  writable: true,
  value: true,
})

// `structuredClone` y `crypto.randomUUID` ya existen en Node 24, pero lo
// dejamos explícito para que no dependa del runtime.
if (typeof globalThis.structuredClone !== "function") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ;(globalThis as any).structuredClone = (v: unknown) => JSON.parse(JSON.stringify(v))
}
