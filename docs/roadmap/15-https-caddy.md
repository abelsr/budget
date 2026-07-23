# 🔒 HTTPS con Caddy

**Estado:** ⬜ Pendiente · **Prioridad:** Alta · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna (desbloquea 03-pwa en producción y 14-multi-familia)

## Por qué
El acceso actual es por IP local en HTTP plano: credenciales JWT y datos financieros viajan sin cifrar, y los service workers (PWA) exigen contexto seguro. Además, cualquier apertura futura a internet (multi-familia, monitoreo externo) requiere TLS. Es la pieza de infraestructura con mejor relación esfuerzo/impacto de todo el roadmap.

## Alcance
**Incluye:**
- Caddy como reverse proxy delante del compose con certificados automáticos de Let's Encrypt
- Redirección 80→443 y headers de seguridad (HSTS, X-Content-Type-Options, etc.)
- Ruta alternativa documentada para uso LAN sin dominio público: Tailscale (HTTPS en la tailnet) o mkcert (CA local)
- Endurecer secretos: `JWT_SECRET` de al menos 32 bytes aleatorios
- Actualizar CORS del backend al dominio real

**No incluye:**
- Autenticación a nivel de proxy (Caddy/basic-auth delante de la app)
- Rotación automática de secretos ni gestión con Vault/similares
- Certificados internos entre servicios del compose (la red Docker interna sigue en HTTP)

## Diseño propuesto

### Backend
- `settings.cors_origins`: del valor actual al dominio real (`https://finanzas.dominio.com`)
- Validar al arranque que `JWT_SECRET` tiene >= 32 bytes; fallar ruidosamente si no (mejor caerse que correr inseguro)
- Generar el secreto nuevo: `openssl rand -hex 32` → `.env` (invalida los tokens existentes, aceptable: los usuarios re-login)

### Frontend
- Sin cambios de código; verificar que el build no asume `http://` en ningún lado (el proxy `/api` de nginx lo hace agnóstico)

### Infra
- Servicio `caddy` en `docker-compose.yml` con imagen `caddy:2`, puertos 80/443 publicados, volúmenes `caddy_data` y `caddy_config` (persistencia de certificados)
- `Caddyfile` mínimo:
  ```
  finanzas.dominio.com {
      reverse_proxy frontend:80
      encode zstd gzip
      header {
          Strict-Transport-Security "max-age=31536000; includeSubDomains"
          X-Content-Type-Options "nosniff"
          X-Frame-Options "DENY"
          Referrer-Policy "strict-origin-when-cross-origin"
      }
  }
  ```
  (el proxy `/api` ya lo maneja nginx del frontend; Caddy solo apunta al frontend)
- DNS: registro A del dominio apuntando al host; puertos 80/443 abiertos en el router/firewall
- Ruta LAN documentada en README: opción A) Tailscale en el host + `tailscale cert` para HTTPS en `https://host.tailnet.ts.net`; opción B) mkcert con CA instalada en los dispositivos de la familia; ambas evitan exponer nada a internet
- Documentar en README: flujo completo con dominio propio y flujo LAN, y cómo verificar la renovación automática

## Criterios de aceptación
- [ ] `https://finanzas.dominio.com` carga con candado válido (certificado Let's Encrypt real)
- [ ] `http://` redirige a `https://` (301)
- [ ] La app funciona igual sobre HTTPS: login, escáner IA y subida/descarga de adjuntos incluidos
- [ ] Los headers de seguridad están presentes (verificable con securityheaders.com o curl)
- [ ] El backend arranca solo con `JWT_SECRET` >= 32 bytes y rechaza uno débil
- [ ] README documenta la ruta con dominio y la ruta LAN (Tailscale/mkcert)

## Notas
- Let's Encrypt exige que el dominio resuelva al host y que el puerto 80 sea alcanzable para el challenge HTTP-01; si el host está tras CGNAT (común en ISPs residenciales), la ruta LAN con Tailscale es la única viable — documentarlo claramente para no frustrar al usuario.
- Riesgo: olvidar persistir `caddy_data` y pegarle al rate limit de Let's Encrypt en cada reinicio del contenedor. El volumen es obligatorio, no opcional.
- Cambiar `JWT_SECRET` invalida todas las sesiones activas: hacerlo una sola vez y avisar a los usuarios (la familia) de que tendrán que re-login.
- Referencia: https://caddyserver.com/docs/quick-starts/reverse-proxy
