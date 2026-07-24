# 🌐 Apertura multi-familia

**Estado:** ⬜ Pendiente · **Prioridad:** Baja · **Esfuerzo:** L (3+ días) · **Dependencias:** 01-alembic ✅ (hecho), 15-https-caddy (HTTPS obligatorio para exponer auth a internet)

## Por qué
Hoy la app sirve a una sola familia por despliegue, con acceso por IP local. Abrir el registro público convierte el proyecto en un producto que cualquier familia puede usar sin que el dev intervenga. Implica endurecer la superficie expuesta a internet: rate limiting, anti-abuso, mínimos legales. Es un cambio de postura de seguridad, no solo un endpoint nuevo.

## Alcance
**Incluye:**
- Signup público: cualquier persona crea su cuenta y su hogar en un solo flujo (el register actual ya crea hogar propio; exponerlo sin restricción)
- Rate limiting básico en endpoints de auth (register, login, join)
- Verificación de email: decisión documentada abajo (recomendado: con servicio externo o diferirla)
- Límites anti-abuso: máximo de invitaciones activas por hogar, máximo de miembros por hogar
- Página de privacidad mínima (qué datos se guardan, dónde, quién los ve)
- Telemetría: ninguna, u opt-in explícito (recomendado: ninguna al inicio)

**No incluye:**
- Recuperación de contraseña por email (depende de la verificación; puede ser fase posterior)
- Login social (Google/Apple)
- Planes de pago, billing o límites comerciales
- Panel de administración de la instancia (ban de usuarios, métricas)

## Diseño propuesto

### Backend
- `slowapi` (o middleware propio) para rate limiting: p. ej. 5 registros/hora/IP, 10 logins/min/IP, límites en `/invitations`
- Límites de negocio en configuración: `MAX_MEMBERS_PER_HOUSEHOLD`, `MAX_ACTIVE_INVITATIONS_PER_HOUSEHOLD` (valores razonables, p. ej. 10 y 5)
- Verificación de email — **decisión:** iniciar SIN verificación obligatoria pero con el campo `email_verified` en el modelo desde ya; cuando se active, integrar Resend (o SES) con un endpoint `POST /auth/verify` y bloqueo suave (recordatorio, no impedimento) al inicio. Justificación: añadir email transaccional es otra dependencia de infra y otro secreto; el valor anti-abuso real al inicio lo da el rate limiting
- Endpoint `GET /legal/privacy` servido como contenido estático o página del frontend
- Tests: rate limit devuelve 429, límites de invitaciones se respetan, dos hogares registrados por el flujo público quedan aislados

### Frontend
- Página pública de signup (hoy el registro puede estar escondido): copy claro de "crea el hogar de tu familia"
- Pantallas de estado para verificación de email (cuando se active)
- Página `/privacidad` accesible desde el footer y desde el signup
- Mensajes de error legibles para 429 ("demasiados intentos, espera unos minutos")

### Infra
- HTTPS activo (15) antes de abrir el registro: auth sin TLS en internet es inaceptable
- Variables nuevas en `.env` del backend: límites, y credenciales del proveedor de email si se activa verificación
- Backups del volumen `pgdata` pasan a ser críticos (ya no son solo datos propios): documentar al menos un `pg_dump` programado
- Decisión de hosting: la instancia pública puede vivir en el mismo host o en un VPS barato; documentar requisitos mínimos

## Criterios de aceptación
- [ ] Una instancia pública desplegada permite que dos familias reales se registren y usen la app sin ver datos de la otra
- [ ] El rate limiting bloquea un script de registros masivos (429 tras el límite)
- [ ] Los límites de miembros e invitaciones por hogar se aplican y devuelven error claro
- [ ] Existe página de privacidad accesible sin login
- [ ] Todo el flujo corre sobre HTTPS con CORS restringido al dominio público

## Notas
- Riesgo mayor: abrir auth a internet multiplica la superficie de ataque. Antes de este archivo, revisar: fuerza del `JWT_SECRET`, expiración de tokens, que no haya endpoints sin auth por descuido, y que el escáner IA no se pueda abusar como proxy de OpenRouter (rate limit también ahí).
- Los costos de OpenRouter pasan a ser por uso de terceros: considerar límite de escaneos por hogar/día o dejar el escáner como feature opt-in con API key propia del usuario.
- Decisión abierta: ¿una instancia pública gestionada por el dev, o solo "self-hosteable por otros"? El alcance asume instancia pública gestionada; si fuera solo self-host, la mayoría de este archivo se reduce a documentación.
- Sin telemetría no hay forma de detectar abuso pasivo: mínimo logs (17-monitoreo) activos en la instancia pública.
