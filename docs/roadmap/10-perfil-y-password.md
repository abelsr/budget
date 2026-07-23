# 👤 Perfil y cambio de contraseña

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna

## Por qué
Hoy el nombre del usuario y la contraseña son inmutables desde la UI. Es lo mínimo esperable de cualquier cuenta, y su ausencia obliga a tocar la DB a mano.

## Alcance
**Incluye:**
- Edición del nombre visible del usuario.
- Cambio de contraseña con verificación de la actual.

**No incluye:**
- Cambio de email (es la identidad de login; queda fuera por ahora — documentado abajo).
- Recuperación de contraseña olvidada (flujo de email).
- Foto de perfil o avatar.

## Diseño propuesto
### Backend
- `PATCH /auth/me` con `{name}` → actualiza el nombre del usuario autenticado.
  - **Decisión documentada: no incluir email.** El email es la identidad de login; cambiarlo implica re-verificación y casos borde (colisiones entre hogares). Fuera de alcance.
- `POST /auth/change-password` con `{currentPassword, newPassword}`:
  - Verifica `currentPassword`; si falla, responde `401` (o `400` con código claro) sin revelar más.
  - Valida `newPassword` con mínimo 8 caracteres.
  - Re-hashea con el mismo hasher actual.
  - **Decisión recomendada: los tokens JWT existentes siguen válidos** (stateless, sin lista de revocación). Simplicidad para self-hosted familiar; invalidar requeriría store de tokens o versioning.
### Frontend
- En Ajustes > Cuenta:
  - Editar nombre: inline o sheet simple con un campo; al guardar se refleja en sidebar/detalle.
  - "Cambiar contraseña": sheet con 3 campos (actual, nueva, confirmar nueva); validación local de coincidencia y longitud mínima; errores del servidor mostrados en el sheet (p.ej. "La contraseña actual es incorrecta"); haptic feedback al éxito.
- Invalidar/refetch de la query del usuario tras ambos cambios (patrón existente en `src/lib/queries.ts`).
### Infra
- Sin cambios.

## Criterios de aceptación
- [ ] Cambiar el nombre se refleja inmediatamente en el sidebar y en el detalle de la cuenta.
- [ ] Tras cambiar la contraseña, el login con la nueva funciona y con la vieja es rechazado.
- [ ] Contraseña actual incorrecta devuelve error claro mostrado en el sheet.
- [ ] Contraseña nueva de menos de 8 caracteres es rechazada con mensaje.
- [ ] Los tokens activos siguen funcionando tras el cambio de contraseña (no se cierra la sesión).
- [ ] Tests: PATCH nombre, cambio exitoso, contraseña actual incorrecta, validación de longitud.

## Notas
- Riesgo: ninguno relevante; son endpoints estándar sobre auth ya existente.
- Decisión abierta a futuro: si se agrega recuperación de contraseña, se necesita envío de email — hoy no hay infra de correo.
- Si más adelante se quiere invalidar sesiones al cambiar la contraseña, agregar `password_version` al usuario e incluirlo en el payload del JWT.
