# ✉️ Invitaciones end-to-end

**Estado:** ✅ Implementado (2026-07-24, falta verificación manual en navegador) · **Prioridad:** Alta · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna

## Por qué
Es una app de finanzas **familiares**, pero hoy no hay forma de sumar miembros desde la UI: el botón "Invitar miembro" en Ajustes está deshabilitado con el texto "Próximamente". Sin embargo la API (`POST /households/me/invitations`) y la pantalla de unirse (`/login?invite=TOKEN`) ya existen y funcionan. Falta solo conectar los puntos en el frontend.

## Alcance
**Incluye:**
- Habilitar el botón "Invitar miembro" en Ajustes > Hogar
- Mostrar el link de invitación completo con botones de copiar y compartir
- Indicar la expiración del link (7 días)

**No incluye:**
- Revocar invitaciones activas
- Roles/permisos por miembro (todos son iguales hoy)
- Envío del link por email (self-hosted sin SMTP; el usuario comparte el link por su canal)

## Diseño propuesto

### Backend
- Sin cambios obligatorios: `POST /households/me/invitations` ya crea la invitación y devuelve el token
- *(Opcional)* `GET /households/me/invitations` para listar invitaciones activas (útil para mostrar "links pendientes" en la UI). Si se implementa, marcar expiradas y usadas en la respuesta

### Frontend
- Ajustes > Hogar: habilitar el botón "Invitar miembro" (quitar estado deshabilitado y texto "Próximamente")
- Al hacer click: llamar `POST /households/me/invitations`, construir el link completo `https://<host>/login?invite=<TOKEN>` usando `window.location.origin`
- Mostrar el link en un campo de solo lectura con:
  - Botón **Copiar** (`navigator.clipboard.writeText`) con feedback visual ("Copiado")
  - Botón **Compartir** si `navigator.share` existe (móvil); ocultarlo si no
- Mostrar texto de expiración: "Válido por 7 días"
- Verificar que el flujo existente de `/login?invite=TOKEN` (modo "Unirse") sigue funcionando sin cambios

### Infra
- Sin cambios

## Criterios de aceptación

> Código completo; los 5 criterios son de recorrido manual y quedan por
> confirmar con el stack levantado.

- [ ] Desde Ajustes > Hogar se puede generar un link de invitación con un click
- [ ] El link se copia al portapapeles y, en móvil, se puede compartir por el sheet nativo
- [ ] Abriendo el link en una ventana de incógnito se puede registrar un segundo usuario
- [ ] Ajustes > Hogar muestra los 2 miembros tras el registro
- [ ] Reusar un link ya consumido muestra un error claro al usuario

## Qué se implementó (2026-07-24)

Solo frontend; el backend (`POST /households/me/invitations`, `POST /auth/join`)
ya estaba completo y con tests.

- `frontend/src/lib/queries.ts`: tipo `Invitation` + hook `useCreateInvitation`.
- `frontend/src/lib/clipboard.ts`: `copyText()` con fallback a
  `document.execCommand('copy')` para HTTP plano por IP (sin contexto seguro).
- `frontend/src/components/InviteSheet.tsx`: bottom sheet que genera el link al
  abrirse, lo muestra en un campo de solo lectura (select-all al enfocar),
  botones **Copiar** (feedback "Copiado" 2s), **Compartir** (solo si existe
  `navigator.share`) y **Generar otro link**; texto de expiración con la fecha
  real derivada de `expiresAt`; skeleton mientras carga y mensaje de error.
- `frontend/src/pages/SettingsPage.tsx`: botón "Invitar miembro" habilitado
  (se quitó `disabled` y "Próximamente") abriendo el sheet.

**Verificado:** `tsc -b && vite build` limpio, `oxlint` sin nuevos warnings, los
37 tests de pytest siguen pasando.
**Pendiente:** recorrido manual en navegador (generar link → incógnito →
registrar segundo usuario → ver 2 miembros → reusar link consumido).

## Notas
- El registro vía invitación ya existe en el login (modo "Unirse" leyendo `?invite=TOKEN`); esta tarea es mayormente UI.
- Riesgo menor: `navigator.clipboard` requiere contexto seguro (HTTPS o localhost); en HTTP plano por IP puede fallar. Prever fallback con `document.execCommand('copy')` o selección manual del campo.
- Esta funcionalidad se reutiliza en el paso 3 del wizard de onboarding (ver `05-onboarding.md`).
