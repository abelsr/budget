# 📱 PWA instalable

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** M (1-3 días) · **Dependencias:** Ninguna

## Por qué
La decisión de producto es "PWA instalable con shell offline" y el uso principal es móvil: registrar un gasto desde el teléfono en el momento. Hoy no hay `manifest` ni service worker, así que no se puede instalar ni abrir sin el chrome del navegador. Es la diferencia entre "una web" y "una app" para el usuario final.

## Alcance
**Incluye:**
- Web app manifest con nombre, iconos y colores del tema
- Service worker con precache del shell (HTML/JS/CSS/assets)
- Iconos de la app (192/512, maskable) generados desde el logo Wallet
- `apple-touch-icon` y meta tags para iOS

**No incluye:**
- Cache de datos de la API (las llamadas `/api` son online-first, NO se cachean)
- Cola offline de transacciones para sincronizar después (fase futura)
- Push notifications

## Diseño propuesto

### Backend
- Sin cambios

### Frontend
- Agregar `vite-plugin-pwa` a la app React+Vite+TS
- Manifest: nombre "Finanzas Familiares", `short_name`, `display: standalone`, `start_url: /`, `background_color` y `theme_color` sincronizados con el modo oscuro de la app (revisar cómo se define hoy el theme para no duplicar el color)
- Iconos: generar 192x192 y 512x512 (incluyendo variante `maskable` con padding seguro) a partir del logo Wallet existente; agregar `apple-touch-icon` (180x180) en `index.html`
- Service worker: precache del shell (assets del build); estrategia **network-only/online-first para `/api/*`** — si la red falla, la UI muestra mensaje de error, no datos viejos cacheados
- Registrar el SW y manejar actualizaciones (prompt o auto-update; decidir, preferible auto-update con recarga silenciosa para una app familiar)

### Infra
- Verificar que nginx (frontend) sirve el `manifest.webmanifest` y el SW con los headers correctos (el SW debe servirse con `Cache-Control: no-cache` para que las actualizaciones lleguen)
- Confirmar que el build de Docker del frontend incluye los archivos generados por `vite-plugin-pwa`

## Criterios de aceptación
- [ ] En Android/Chrome aparece el prompt de instalación y la app se instala con ícono propio
- [ ] En iOS se puede "Agregar a pantalla de inicio" con el ícono correcto
- [ ] La app instalada abre en modo standalone (sin barra del navegador)
- [ ] Sin conexión, el shell carga (UI visible) aunque los datos fallen con un mensaje claro
- [ ] Las llamadas a `/api` nunca devuelven datos cacheados viejos
- [ ] El chequeo PWA de Lighthouse pasa

## Notas
- HTTPS: los SW exigen contexto seguro; en self-hosted por IP+HTTP la instalación puede no estar disponible. Documentar que se recomienda HTTPS (reverse proxy / Tailscale / etc.).
- Riesgo: un SW mal configurado puede dejar clientes "atrapados" en una versión vieja del frontend. Probar el flujo de actualización antes de darlo por cerrado.
- Referencia: https://vite-pwa-org.netlify.app/
