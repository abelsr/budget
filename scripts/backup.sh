#!/usr/bin/env bash
#
# Backup of the two Docker volumes that hold every piece of household data:
#
#   pgdata     -> backups/pg-<timestamp>.sql.gz      (compressed pg_dump)
#   minio_data -> backups/minio-<timestamp>.tar.gz   (tar of the raw volume)
#
# This script runs ON THE HOST (not inside a container): it drives the Docker
# CLI (`docker compose exec` for the pg_dump, `docker run` for the MinIO
# archive) and writes the artifacts to the host filesystem. It needs the
# `docker` CLI with the compose plugin in PATH and the `db` service running.
#
# Usage:
#   scripts/backup.sh
#
# Cron (see "Backups" in the root README.md for the full setup):
#   0 3 * * * /path/to/budget/scripts/backup.sh >> /path/to/budget/backups/backup.log 2>&1
#
# Environment overrides:
#   BACKUP_DIR       destination directory (default: <project>/backups)
#   RETENTION_DAYS   delete *.gz older than this many days (default: 30)
#   MINIO_VOLUME     Docker volume name (default: <project name>_minio_data)
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

cd "$PROJECT_ROOT"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

# Artifacts are written as *.part and renamed only after the producing command
# succeeds, so an interrupted run can never leave a truncated file that looks
# like a usable backup (or that the retention pass would count as one).
# Scoped to this run's timestamp: a wider glob would delete the in-progress
# artifact of a concurrent run (cron firing during a manual one).
cleanup() { rm -f "$BACKUP_DIR"/*"$TIMESTAMP"*.part 2>/dev/null || true; }
trap cleanup EXIT

command -v docker >/dev/null 2>&1 || die "docker not found in PATH"
docker compose version >/dev/null 2>&1 || die "the docker compose plugin is not available"

mkdir -p "$BACKUP_DIR"

docker compose ps --status running --services | grep -qx db \
  || die "the 'db' service is not running (start it with: docker compose up -d db)"

# The credentials are read from the running container rather than from .env
# because docker-compose.yml sets POSTGRES_USER/POSTGRES_DB literally. Reading
# them from anywhere else could silently diverge from what the database uses.
PG_USER="$(docker compose exec -T db printenv POSTGRES_USER)"
PG_DB="$(docker compose exec -T db printenv POSTGRES_DB)"

PROJECT_NAME="${COMPOSE_PROJECT_NAME:-$(basename "$PROJECT_ROOT")}"
MINIO_VOLUME="${MINIO_VOLUME:-${PROJECT_NAME}_minio_data}"
docker volume inspect "$MINIO_VOLUME" >/dev/null 2>&1 \
  || die "the Docker volume '$MINIO_VOLUME' does not exist (override it with MINIO_VOLUME=...)"

PG_FILE="$BACKUP_DIR/pg-$TIMESTAMP.sql.gz"
MINIO_FILE="$BACKUP_DIR/minio-$TIMESTAMP.tar.gz"

# --clean --if-exists makes the dump restorable onto a database that already
# has the schema, which is the normal case here: the backend applies Alembic
# migrations on startup, so a freshly created stack is not an empty database.
log "dumping Postgres database '$PG_DB' as user '$PG_USER'"
docker compose exec -T db pg_dump -U "$PG_USER" -d "$PG_DB" --clean --if-exists \
  | gzip > "$PG_FILE.part"
mv "$PG_FILE.part" "$PG_FILE"

# Un dump que no se puede leer no es un backup: `gzip -t` verifica la
# integridad de la compresión antes de declarar el artefacto usable (issue #47).
gzip -t "$PG_FILE" || die "pg dump failed gzip integrity check: $(basename "$PG_FILE")"

# The tar is streamed to stdout instead of being written through a bind mount.
# A `-v $BACKUP_DIR:/backup` mount is resolved by the *host* Docker daemon, so
# it silently breaks when the script itself runs inside a container. Redirecting
# stdout always writes to the filesystem the script sees, which is the host.
log "archiving MinIO volume '$MINIO_VOLUME'"
docker run --rm -v "$MINIO_VOLUME":/data:ro alpine tar cz -C /data . > "$MINIO_FILE.part"
mv "$MINIO_FILE.part" "$MINIO_FILE"

# `tar -tzf` lista el archivo sin descomprimirlo: si el tar.gz estuviera
# truncado o corrupto, esto falla y el artefacto no se cuenta como backup.
tar -tzf "$MINIO_FILE" >/dev/null || die "minio archive failed tar integrity check: $(basename "$MINIO_FILE")"

log "wrote $(basename "$PG_FILE") ($(du -h "$PG_FILE" | cut -f1)) and $(basename "$MINIO_FILE") ($(du -h "$MINIO_FILE" | cut -f1))"

# ---------- Copia off-site (issue #47) ----------
# El README pide una copia fuera de la máquina; todo lo anterior es on-site y
# se pierde junto con el disco. OFFSITE_DIR, si se define, recibe una copia
# de cada artefacto verificado (ej.: montaje NFS/rsync/rclone, otra partición,
# o un bucket local). Es opcional y no bloquea el backup si falla: el log lo
# deja marcado y el exit code se conserva para que el monitor lo vea.
if [ -n "${OFFSITE_DIR:-}" ]; then
  if ! command -v rsync >/dev/null 2>&1; then
    log "WARN: OFFSITE_DIR set but rsync not found; skipping off-site copy"
  else
    log "copying artifacts off-site to $OFFSITE_DIR"
    if rsync -a "$PG_FILE" "$MINIO_FILE" "$OFFSITE_DIR/"; then
      log "off-site copy complete"
    else
      log "WARN: off-site copy FAILED (rsync); on-site backups are still valid"
    fi
  fi
fi

# *.part is swept too: one that old is a leftover from a run that died before
# its own trap could fire, and nothing else would ever remove it.
log "applying retention: removing *.gz older than $RETENTION_DAYS days"
removed="$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name '*.gz' -o -name '*.part' \) -mtime +"$RETENTION_DAYS" -print -delete | wc -l)"
log "retention removed $removed file(s); $(find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.gz' | wc -l) remain"

log "backup complete"
