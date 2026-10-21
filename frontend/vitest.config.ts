import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/__tests__/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary"],
      reportsDirectory: "./coverage",
      // Solo el código de la app: sin tests, sin setup de vitest y sin las
      // declaraciones de tipos (no tienen código ejecutable que cubrir).
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/__tests__/**",
        "src/test/**",
        "src/**/*.test.{ts,tsx}",
        "src/**/*.d.ts",
      ],
      // Piso anti-regresión, no una meta. Cobertura REAL el día que se activó
      // este gate (#47): 6.52% líneas, 5.91% statements, 2.45% funciones,
      // 2.91% ramas, con 2 archivos de test sobre 74 de src. Los umbrales van
      // un punto por debajo para no fallar por ruido de un refactor, y deben
      // SUBIR por sprint a medida que se añadan tests (siguiente paso: cubrir
      // src/lib/offline.tsx y src/lib/auth.tsx, que ya tienen tests y son la
      // mayor superficie de lógica sin cubrir).
      thresholds: {
        lines: 6,
        statements: 5,
        functions: 2,
        branches: 2,
      },
    },
  },
})