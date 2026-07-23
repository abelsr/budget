# 📴 Modo offline con cola de sincronización

**Estado:** ⬜ Pendiente · **Prioridad:** Baja · **Esfuerzo:** L (3+ días) · **Dependencias:** 03-pwa (service worker ya instalado)

## Por qué
El caso de uso principal es registrar un gasto en el momento: en el súper, en la calle, con datos móviles malos. Hoy, sin conexión, la app simplemente falla y el gasto se olvida. Una cola offline convierte la captura en confiable aunque la red no lo sea; es el siguiente paso natural después de tener la PWA instalable.

## Alcance
**Incluye:**
- Outbox en IndexedDB: movimientos creados sin conexión se guardan localmente con estado "pendiente"
- Sincronización automática al volver online (listener `online` + reintento; Background Sync API donde esté disponible)
- Banner persistente "Sin conexión — N movimientos pendientes" con estado de la cola
- Lectura offline del último snapshot de datos (persistir el cache de TanStack Query en localStorage)
- Resolución de conflictos simple: server-wins (los movimientos son append-only, colisiones raras)

**No incluye:**
- Edición offline de movimientos existentes (solo creación)
- Sincronización de cuentas/categorías/metas (se asumen estables; si faltan, la subida falla y reintenta)
- Conflict resolution UI (no aplica con append-only + server-wins)
- Attachments offline (el escáner y los adjuntos requieren red; se encolan solo los datos del movimiento)

## Diseño propuesto

### Backend
- Endpoint de sync idempotente: el cliente envía `client_id` (UUID generado en el dispositivo) en cada movimiento; el servidor lo guarda y rechaza duplicados (constraint único por household) para tolerar reintentos
- Sin cambios en modelos de negocio más allá del `client_id` nullable en `transactions`
- Respuesta de error clara si el movimiento referencia una cuenta/categoría inexistente (el cliente lo marca como fallido y lo reporta)

### Frontend
- Outbox en IndexedDB (`idb` o Dexie): tabla `pending_mutations` con `{ client_id, payload, created_at, attempts, last_error }`
- Interceptor en el layer de mutaciones: si `navigator.onLine === false` o el POST falla por red (no por 4xx), guardar en outbox y devolver éxito optimista
- Flush: al evento `online`, al recuperar foco, y con `setInterval` de respaldo; cada item se sube en orden y se borra al confirmar 2xx
- Banner global: lee el estado de la red y el conteo del outbox ("Sin conexión — 3 movimientos pendientes"); desaparece al vaciarse
- `persistQueryClient` (plugin oficial de TanStack Query) con persister de localStorage: al abrir sin red, se muestran los datos del último snapshot con indicador de "datos de hace X"
- Los movimientos pendientes se muestran en el feed con badge "Pendiente de subir" (optimistic UI desde el outbox, no del cache de queries)

### Infra
- Sin cambios

## Criterios de aceptación
- [ ] Modo avión → registrar un gasto → aparece en el feed con badge "Pendiente" y el banner cuenta 1
- [ ] Al volver la conexión, el gasto se sube solo, el badge desaparece y el banner se vacía sin intervención del usuario
- [ ] Un reintento (doble flush, recarga a mitad de sync) no duplica movimientos en el servidor
- [ ] Sin conexión, al abrir la app se ven los datos del último snapshot con indicador de antigüedad
- [ ] Un movimiento que falla con 4xx se marca como error y no bloquea el resto de la cola

## Notas
- Riesgo: estados raros del service worker combinados con el outbox (p. ej. SW sirviendo shell viejo con lógica de sync distinta). Probar el flujo de actualización de la PWA junto con la cola.
- `client_id` debe generarse una vez por movimiento y sobrevivir recargas del navegador (vive en IndexedDB, no en memoria).
- Decisión abierta: Background Sync API no existe en Safari iOS; el fallback de listener `online` + foco es suficiente para el uso real, documentarlo.
- No intentar sincronizar attachments offline: el flujo del escáner ya es inherentemente online (llamada a OpenRouter).
