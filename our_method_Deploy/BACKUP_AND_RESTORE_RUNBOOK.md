# Backup and restore runbook

The daily timer creates a PostgreSQL custom-format dump and a compressed copy
of the append-only job evidence under `/opt/plc-generation/backups`.  A backup
is renamed out of its hidden partial directory only after SHA-256, `pg_restore
--list`, and `tar --list` all pass.  Provider credentials and service secrets
are intentionally excluded.

Before restoring, stop `plc-generation.service` and
`plc-generation-worker.service`, copy the selected backup to separate storage,
and verify it with `scripts/backup_production.py --verify <backup-directory>`.
Restore the database into a newly created empty database with `pg_restore`,
extract `evidence.tar.gz` into a new data directory, verify ownership, then
start the worker and Web service.  Run `scripts/preflight.py`, inspect `/ready`,
and download one historical artifact before reopening the proxy.  Never
restore over the only live database or delete the prior data directory until
the application-level checks pass.

The non-destructive drill command is `scripts/restore_drill.py --backup
<backup-directory> --report <report.json>`.  It restores into a randomly named
temporary database, extracts evidence into a temporary directory, checks job
counts, and removes both temporary targets in a `finally` block.  It never
modifies the live database or evidence directory.
