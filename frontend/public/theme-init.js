// Aplica el tema guardado antes del primer paint (sin flash blanco).
// Separado en un archivo para que el CSP `script-src 'self'` no necesite
// 'unsafe-inline' ni un hash que cambiaría cada build (issue #34).
try {
  var t = localStorage.getItem("ff-theme")
  var dark =
    t === "dark" ||
    ((t === null || t === "system") &&
      matchMedia("(prefers-color-scheme: dark)").matches)
  if (dark) {
    document.documentElement.classList.add("dark")
    document
      .querySelector('meta[name="theme-color"]')
      .setAttribute("content", "#070c16")
  }
} catch (e) {}
