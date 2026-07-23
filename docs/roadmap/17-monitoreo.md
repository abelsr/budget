# 📡 Monitoreo y alertas

**Estado:** ⬜ Pendiente · **Prioridad:** Baja · **Esfuerzo:** S (<1 día) · **Dependencias:** 15-https-caddy (solo si el monitoreo es externo tipo Better Stack; Uptime Kuma local no la necesita)

## Por qué
Es un sistema self-hosted usado por personas reales: si el backend muere un viernes, nadie se entera hasta que alguien intenta registrar un gasto. Además, los adjuntos crecen en el volumen de MinIO sin límite aparente y un disco lleno tumba Postgres. Un mínimo de logs estructurados y dos alertas (caída, disco) cubre el 90% de los desastres probables.

## Alcance
**Incluye:**
- Logs estructurados JSON en el backend (uvicorn + configuración de logging) con `request_id` por petición
- Healthcheck externo sobre `/health`: Uptime Kuma self-hosted (recomendado, mismo host) o Better Stack free
- Alerta de disco del host > 85% (los volúmenes de Postgres y MinIO crecen con adjuntos)
- Dashboard mínimo de uptime (el que provee la herramienta elegida)

**No incluye:**
- Métricas de aplicación (Prometheus/Grafana, APM): excesivo para esta escala
- Alertas de negocio (errores 5xx por minuto, latencia p95)
- Centralización de logs de todos los contenedores (Loki y similares)
- Monitoreo de costos de OpenRouter

## Diseño propuesto

### Backend
- Configuración de logging en JSON: formatter propio o `python-json-logger`, aplicado a uvicorn (`--log-config` o dictConfig en `main.py`)
- Middleware de `request_id`: generar UUID por request, inyectarlo en el contexto de logging y devolverlo en el header `X-Request-ID` (facilita correlacionar "el usuario dice que falló" con el log exacto)
- Verificar que `/health` existe y es ligero (sin queries pesadas); si no existe, crearlo: 200 con `{ "status": "ok" }` y chequeo básico de DB
- Nivel INFO en producción, DEBUG por variable de entorno

### Frontend
- Sin cambios

### Infra
- **Opción recomendada:** servicio `uptime-kuma` en el mismo compose (imagen `louislam/uptime-kuma`), monitor HTTP a `http://backend:8000/health` cada 60s, notificación por Telegram/Discord/email (Kuma soporta todas sin configurar SMTP propio)
- **Opción externa:** Better Stack free apuntando a `https://finanzas.dominio.com/health` (requiere 15); útil porque alerta aunque todo el host muera, no solo el backend
- Alerta de disco: script en cron del host (`df /` + webhook a Telegram/ntfy) o el propio Uptime Kuma no lo cubre — el script es lo simple y suficiente
- Documentar en README: dónde ver el dashboard de Kuma (puerto 3001, idealmente solo en LAN o tras Tailscale) y qué hacer cuando llega cada alerta

## Criterios de aceptación
- [ ] `docker compose stop backend` genera una alerta recibida en menos de 5 minutos
- [ ] Los logs del backend salen en JSON con `request_id`, método, path, status y duración
- [ ] El header `X-Request-ID` de una respuesta aparece en los logs de esa petición
- [ ] Existe alerta configurada para disco del host > 85% (probada manualmente bajando el umbral)
- [ ] El dashboard de uptime muestra historial de al menos una semana tras una semana corriendo

## Notas
- Decisión abierta: Uptime Kuma local alerta de todo menos de la muerte del host completo (si el host cae, Kuma también). Para eso está la opción externa; lo ideal es Kuma local + Better Stack free como red de seguridad, ambos son baratos de operar.
- Riesgo menor: logs JSON con datos sensibles. Asegurarse de no loggear bodies de requests (tokens, montos no son secreto de estado pero tampoco hace falta escribirlos); loggear solo metadata.
- El threshold de disco (85%) asume volúmenes en el disco raíz; si `pgdata` o MinIO viven en otro mount, apuntar el chequeo ahí.
- Referencias: https://github.com/louislam/uptime-kuma · https://betterstack.com/uptime
