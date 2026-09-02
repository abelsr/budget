#!/usr/bin/env bash
#
# Restore de prueba (issue #47): "el backup sin restore testeado no es backup".
#
# Toma el último dump pg-*.sql.gz, lo restaura en un Postgres SCRATCH
# efímero (un contenedor postgres:17-alpine que se destruye al salir) y
# compara el número de filas de las tablas principales contra la base en
# vivo. Si el dump estuviera corrupto o truncado, la restauración fallaría o
# los counts no cuadrarían.
#
# No toca la base en vivo ni los volúmenes: todo ocurre en un contenedor
# scratch con su propia base `restore_check`.
#
# Uso:
#   scripts/verify-restore.sh
#
# Cron (mensual, ej. el día 1 a las 4, tras el backup nocturno):
#   0 4 1 * * /path/to/budget/scripts/verify-restore.sh >> /path/to/budget/backups/verify-restore.log 2>&1
#
# Env vars:
#   BACKUP_DIR   donde viven los dumps (default: <project>/backups)
#   PG_IMAGE     imagen para el scratch (default: postgres:17-alpine)
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
PG_IMAGE="${PG_IMAGE:-postgres:17-alpine}"

log() { printf '%s  %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "docker not found in PATH"

# Tablas que deben existir y cuadrar entre el live y el restore. Son el
# núcleo del dato del hogar; si una no coincide, el dump no es fiel.
TABLES="households users accounts transactions transaction_splits categories budgets recurring_rules savings_goals instalment_plans reconciliation_sessions import_batches import_rows"

# El último dump, por nombre (el timestamp en el nombre ordena cronológico).
DUMP="$(ls -1 "$BACKUP_DIR"/pg-*.sql.gz 2>/dev/null | sort | tail -1 || true)"
[ -n "$DUMP" ] || die "no hay ningún pg-*.sql.gz en $BACKUP_DIR (ejecuta backup.sh primero)"
log "verificando restauración de $(basename "$DUMP")"

# Credenciales de la base en vivo (para comparar counts), leídas del
# contenedor como en backup.sh.
PG_USER="$(docker compose exec -T db printenv POSTGRES_USER 2>/dev/null || true)"
PG_DB="$(docker compose exec -T db printenv POSTGRES_DB 2>/dev/null || true)"

# Counts por tabla en la base en vivo (una consulta por tabla).
live_counts() {
  local table
  for table in $TABLES; do
    n="$(docker compose exec -T db psql -U "$PG_USER" -d "$PG_DB" -At \
          -c "SELECT count(*) FROM $table" 2>/dev/null || echo "?")"
    printf '%s\t%s\n' "$table" "$n"
  done
}

# Scratches: contenedor efímero. `trap` lo destruye aunque algo falle.
SCRATCH_ID=""
cleanup() {
  [ -n "$SCRATCH_ID" ] && docker rm -f "$SCRATCH_ID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

SCRATCH_ID="$(docker create "$PG_IMAGE" \
  -e POSTGRES_USER=chk -e POSTGRES_PASSWORD=chk -e POSTGRES_DB=restore_check)"
docker start "$SCRATCH_ID" >/dev/null
log "esperando a que el Postgres scratch esté listo"
for _ in $(seq 1 30); do
  if docker exec "$SCRATCH_ID" pg_isready -U chk >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$SCRATCH_ID" pg_isready -U chk >/dev/null 2>&1 \
  || die "el Postgres scratch no estuvo a tiempo (30s)"

# Copia el dump al contenedor y lo restaura. El dump ya lleva --clean
# --if-exists, así que restaura en la base vacía sin conflictos.
docker cp "$DUMP" "$SCRATCH_ID:/tmp/dump.sql.gz"
docker exec "$SCRATCH_ID" gunzip -c /tmp/dump.sql.gz \
  | docker exec -i "$SCRATCH_ID" psql -U chk -d restore_check -v ON_ERROR_STOP=1 >/dev/null \
  || die "la restauración del dump falló (corrupto o truncado)"
log "dump restaurado en el scratch"

# Counts por tabla en el scratch.
scratch_counts() {
  local table
  for table in $TABLES; do
    n="$(docker exec "$SCRATCH_ID" psql -U chk -d restore_check -At \
          -c "SELECT count(*) FROM $table" 2>/dev/null || echo "?")"
    printf '%s\t%s\n' "$table" "$n"
  done
}

if [ -n "$PG_USER" ] && [ -n "$PG_DB" ]; then
  # La base en vivo está arriba: comparación real.
  log "comparando counts live vs restore"
  live="$(live_counts)"
  scratch="$(scratch_counts)"
  if [ "$live" != "$scratch" ]; then
    diff <(echo "$live") <(echo "$scratch") | sed 's/^/    /' || true
    die "los counts del restore no coinciden con la base en vivo"
  fi
  log "los counts coinciden: restore fiel"
else
  # Sin base en vivo (p. ej. CI): solo verificamos que la restauración no
  # falló y que las tablas existen con algún dato.
  log "sin base en vivo para comparar; verificando que el restore no está vacío"
  scratch="$(scratch_counts)"
  empty="$(echo "$scratch" | awk -F'\t' '$2==0' | cut -f1)"
  [ -z "$empty" ] || die "tablas vacías tras el restore: $empty"
  log "restore no vacío (verificación sin base en vivo)"
fi

log "restore de prueba OK: $(basename "$DUMP")"
