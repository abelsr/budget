# 💾 Postgres and MinIO backups

**Status:** ✅ Done 2026-07-26 · **Priority:** Medium · **Effort:** S (<1 day) · **Dependencies:** None

## Why
This is self-hosted family finance software: the data lives in two Docker volumes (`pgdata` and `minio_data`). Losing those volumes — a broken disk, an accidental `docker compose down -v`, a botched server migration — means losing **everything**, with no third-party recourse. An automatic backup and a documented restore procedure are the minimum safety net.

## Scope
**Includes:**
- `scripts/backup.sh` script that generates a Postgres dump + a copy of the MinIO files with a timestamp in `./backups/`
- Simple retention (delete backups older than 30 days)
- Automation option: a cron service in compose or documentation for host cron
- Restore procedure documented in the README

**Doesn't include:**
- Encrypted backups or upload to remote destinations (S3, B2, etc.) — the user can rsync/sync the `./backups/` folder on their own
- Point-in-time recovery (WAL archiving)
- Backup of the configuration (`.env`, compose) — although it's mentioned as a recommendation

## Proposed design

### Backend
- No changes

### Frontend
- No changes

### Infra
- `scripts/backup.sh`:
  - Postgres dump: `docker compose exec -T db pg_dump -U <user> <db> | gzip > ./backups/pg-<timestamp>.sql.gz`
  - Attachments: `tar` of the `minio_data` volume (`docker run --rm -v ..._minio_data:/data -v ./backups:/backup alpine tar czf /backup/minio-<timestamp>.tar.gz -C /data .`) or `mc mirror` to a local folder — pick one and document it (prefer `tar` of the volume: zero new dependencies)
  - Retention: `find ./backups -name '*.gz' -mtime +30 -delete`
  - Variables read from the existing `.env` (Postgres credentials); fail-fast with `set -euo pipefail`
- Automation (one of the two, document both):
  - Host cron: example line `0 3 * * * /path/to/project/scripts/backup.sh`
  - Optional compose service with a cron image that runs the script (`backup` profile so it doesn't start by default)
- README: "Restoring a backup" section — bring up a clean stack, `gunzip < dump | docker compose exec -T db psql ...`, restore the tar into the MinIO volume, start it up

## Acceptance criteria
- [x] Running `scripts/backup.sh` generates the compressed Postgres dump and the MinIO archive in `./backups/` with a timestamp
- [x] Backups older than 30 days are automatically deleted when running the script
- [x] Restore tested: on a clean stack (new volumes), restoring both artifacts brings up the app with the previous data (users, accounts, transactions and attachments visible)
- [x] The README documents backup and restore step by step

## Implementation notes (2026-07-26)

- **`--clean --if-exists` was not optional.** The doc assumed a "clean stack"
  means an empty database, but `backend/entrypoint.sh` applies Alembic
  migrations on startup: by the time you restore, the schema already exists at
  head and a plain dump fails with "relation already exists". This was
  reproduced on the throwaway stack before choosing the flags.
- **The MinIO tar is streamed to stdout instead of through a bind mount.** The
  doc's `-v ./backups:/backup` is resolved by the *host* Docker daemon, so it
  silently breaks when the script itself runs inside a container — which is
  exactly what the optional `backup` compose service does. `docker run ... tar
  cz -C /data . > file` writes to whatever filesystem the script sees, so one
  code path works in both places.
- **Postgres credentials are read from the running container**
  (`docker compose exec -T db printenv POSTGRES_USER`), not from `.env`. The doc
  said `.env`, but `docker-compose.yml` sets `POSTGRES_USER`/`POSTGRES_DB`
  literally and `.env` never had them: reading `.env` would have produced a
  script that works today only by coincidence.
- **Artifacts are written as `*.part` and renamed on success.** Otherwise an
  interrupted run leaves a truncated `.gz` that looks like a valid backup and
  that the retention pass counts as one.
- **Host cron is documented as the recommended option** and the compose
  `backup` profile service as the alternative, rather than treating them as
  equivalent: the service needs the host Docker socket, writes `root`-owned
  files, and can only sleep a fixed interval instead of targeting 03:00.

## Notes
- Test the restore **before** you need it: an unverified backup is not a backup.
- A hot `pg_dump` is consistent enough for this use case (family app, low concurrency); there's no need to stop the backend.
- `./backups/` must be in `.gitignore`.
- Open decision: if a remote destination is added later, `restic` or `rclone` are good options without changing the script's structure.
