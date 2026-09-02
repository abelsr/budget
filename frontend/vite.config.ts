import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'budget · finanzas del hogar',
        short_name: 'budget',
        description: 'El dinero de tu hogar, en un solo lugar.',
        start_url: '/',
        display: 'standalone',
        background_color: '#eff6ff',
        theme_color: '#eff6ff',
        lang: 'es-MX',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          {
            src: 'pwa-512x512-maskable.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'maskable',
          },
        ],
      },
      workbox: {
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  build: {
    // Issue #44: separar las libs pesadas (recharts, motion, react-day-picker)
    // del chunk de la app. Con React.lazy por página, recharts solo se
    // descarga al visitar Dashboard/Reports; este chunk estable se cachea
    // entre builds mientras la app cambie.
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return
          if (id.includes("recharts")) return "recharts"
          if (id.includes("node_modules/motion")) return "motion"
          if (id.includes("react-day-picker")) return "day-picker"
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // En dev, /api → backend FastAPI local
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
      },
    },
  },
})
