# 💾 Backups de Postgres y MinIO

**Estado:** ⬜ Pendiente · **Prioridad:** Media · **Esfuerzo:** S (<1 día) · **Dependencias:** Ninguna

## Por qué
Son finanzas familiares self-hosted: los datos viven en dos volúmenes Docker (`pgdata` y `minio_data`). Perder esos volúmenes —disco roto, `docker compose down -v` accidental, migración de servidor mal hecha— es perder **todo**, sin recursos a terceros. Un backup automático y un restore documentado son la red de seguridad mínima.

## Alcance
**Incluye:**
- Script `scripts/backup.sh` que genera dump de Postgres + copia de los archivos de MinIO con timestamp en `./backups/`
- Retención simple (borrar backups con más de 30 días)
- Opción de automatización: servicio con cron en compose o documentación para cron del host
- Procedimiento de restore documentado en el README

**No incluye:**
- Backups cifrados ni subida a destinos remotos (S3, B2, etc.) — el usuario puede rsync/sync la carpeta `./backups/` por su cuenta
- Point-in-time recovery (WAL archiving)
- Backup de la configuración (`.env`, compose) — aunque se menciona como recomendación

## Diseño propuesto

### Backend
- Sin cambios

### Frontend
- Sin cambios

### Infra
- `scripts/backup.sh`:
  - Dump de Postgres: `docker compose exec -T db pg_dump -U <user> <db> | gzip > ./backups/pg-<timestamp>.sql.gz`
  - Attachments: `tar` del volumen `minio_data` (`docker run --rm -v ..._minio_data:/data -v ./backups:/backup alpine tar czf /backup/minio-<timestamp>.tar.gz -C /data .`) o `mc mirror` a una carpeta local — elegir uno y documentarlo (preferir `tar` del volumen: cero dependencias nuevas)
  - Retención: `find ./backups -name '*.gz' -mtime +30 -delete`
  - Variables leídas del `.env` existente (credenciales de Postgres); fail-fast con `set -euo pipefail`
- Automatización (una de las dos, documentar ambas):
  - Cron del host: línea de ejemplo `0 3 * * * /ruta/al/proyecto/scripts/backup.sh`
  - Servicio opcional en compose con una imagen de cron que ejecute el script (perfil `backup` para no arrancarlo por defecto)
- README: sección "Restaurar un backup" — levantar stack limpio, `gunzip < dump | docker compose exec -T db psql ...`, restaurar el tar en el volumen de MinIO, arrancar

## Criterios de aceptación
- [ ] Correr `scripts/backup.sh` genera el dump comprimido de Postgres y el archivo de MinIO en `./backups/` con timestamp
- [ ] Los backups con más de 30 días se eliminan automáticamente al correr el script
- [ ] Restore probado: en un stack limpio (volúmenes nuevos), restaurar ambos artefactos levanta la app con los datos anteriores (usuarios, cuentas, transacciones y attachments visibles)
- [ ] El README documenta backup y restore paso a paso

## Notas
- Probar el restore **antes** de necesitarlo: un backup no verificado no es un backup.
- `pg_dump` en caliente es consistente para este caso de uso (app familiar, baja concurrencia); no hace falta detener el backend.
- `./backups/` debe estar en `.gitignore`.
- Decisión abierta: si más adelante se agrega destino remoto, `restic` o `rclone` son buenas opciones sin cambiar la estructura del script.
