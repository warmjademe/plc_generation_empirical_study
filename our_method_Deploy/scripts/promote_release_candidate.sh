#!/usr/bin/env bash
set -Eeuo pipefail

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
  printf 'run as root\n' >&2
  exit 77
fi

staging_root=${1:-/home/ubuntu/plc-deploy-rc}
deploy_root=/opt/plc-generation
app_root=$deploy_root/app
config_root=$deploy_root/config
data_root=$deploy_root/data
python=/home/ubuntu/miniforge3/envs/plc_generation/bin/python
stamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_root=$deploy_root/releases/app-pre-$stamp
failed_root=$deploy_root/releases/app-failed-$stamp
promoted=false
rollback_armed=false

rollback() {
  code=$?
  if $promoted || ! $rollback_armed; then
    exit "$code"
  fi
  printf 'promotion failed; restoring %s\n' "$backup_root" >&2
  systemctl stop plc-generation-proxy.service plc-generation.service \
    plc-generation-worker.service 2>/dev/null || true
  [[ ! -d "$app_root" ]] || mv "$app_root" "$failed_root"
  if [[ -d "$backup_root" ]]; then
    mv "$backup_root" "$app_root"
    chown -R ubuntu:ubuntu "$app_root"
    sudo -u ubuntu "$python" -m pip install -q "$app_root" || true
  fi
  systemctl start plc-generation-postgres.service plc-generation-worker.service \
    plc-generation.service plc-generation-proxy.service 2>/dev/null || true
  exit "$code"
}
trap rollback ERR

[[ -f "$staging_root/pyproject.toml" ]]
[[ -x "$python" ]]
set -a
. "$config_root/service.env"
. "$config_root/providers.env"
. "$config_root/dvp-validator.env"
set +a
export PLC_PROJECT_ROOT="$staging_root"
export PYTHONPATH="$staging_root/src"

# All code, deterministic validators and production security settings are
# checked before the currently serving application is stopped.
sudo -u ubuntu -E "$python" -m compileall -q "$staging_root/src" "$staging_root/scripts"
sudo -u ubuntu -E "$python" -m pytest -q "$staging_root/tests" \
  --basetemp "$data_root/release-pytest-$stamp"
sudo -u ubuntu -E "$python" "$staging_root/scripts/preflight.py"
PLC_ENVIRONMENT=production sudo -u ubuntu -E "$python" -c \
  'from plc_deploy.settings import Settings; Settings.load()'
if [[ -x "$app_root/scripts/check_active_jobs.py" ]]; then
  safe=$($python "$app_root/scripts/check_active_jobs.py" | $python -c \
    'import json,sys; print(str(json.load(sys.stdin).get("safe_to_restart", False)).lower())')
  [[ "$safe" == true ]] || { printf 'active PLC jobs prevent deployment\n' >&2; exit 75; }
fi

systemctl stop plc-generation-proxy.service plc-generation.service \
  plc-generation-worker.service 2>/dev/null || true
install -d -m 0750 "$deploy_root/releases"
if [[ -d "$app_root" ]]; then
  mv "$app_root" "$backup_root"
  rollback_armed=true
fi
cp -a "$staging_root" "$app_root"
chown -R ubuntu:ubuntu "$app_root"
find "$app_root/scripts" -maxdepth 1 -type f -name '*.py' -exec chmod 0755 {} +
find "$app_root/scripts" -maxdepth 1 -type f -name '*.sh' -exec chmod 0755 {} +
chmod 0755 "$app_root/deploy/start-kemei-win11-instance.sh"

sudo -u ubuntu "$python" -m pip install -q "$app_root"

install -d -m 0700 "$data_root/postgres"
if [[ ! -f "$config_root/postgres.env" ]]; then
  database_password=$(openssl rand -hex 24)
  umask 077
  {
    printf 'POSTGRES_USER=plc_generation\n'
    printf 'POSTGRES_PASSWORD=%s\n' "$database_password"
    printf 'POSTGRES_DB=plc_generation\n'
  } >"$config_root/postgres.env"
else
  database_password=$(sed -n 's/^POSTGRES_PASSWORD=//p' "$config_root/postgres.env")
fi
[[ "$database_password" =~ ^[0-9a-f]{48}$ ]]
database_url="postgresql://plc_generation:${database_password}@127.0.0.1:5433/plc_generation"

service_tmp=$(mktemp "$config_root/service.env.XXXXXX")
grep -vE '^(PLC_DATABASE_URL|PLC_ENVIRONMENT|PLC_RUN_BACKGROUND_JOBS|PLC_WORKERS|PLC_DVP_SPOOL_ROOTS)=' \
  "$config_root/service.env" >"$service_tmp"
{
  printf 'PLC_DATABASE_URL=%s\n' "$database_url"
  printf 'PLC_ENVIRONMENT=production\n'
  printf 'PLC_WORKERS=2\n'
  printf 'PLC_DVP_SPOOL_ROOTS=/opt/plc-generation/dvp-bridge-01/dvp-spool,/opt/plc-generation/dvp-bridge-02/dvp-spool,/opt/plc-generation/dvp-bridge-03/dvp-spool,/opt/plc-generation/dvp-bridge-04/dvp-spool\n'
} >>"$service_tmp"
chown --reference="$config_root/service.env" "$service_tmp"
chmod 0600 "$service_tmp"
mv "$service_tmp" "$config_root/service.env"
chmod 0600 "$config_root/postgres.env"

install -m 0644 "$app_root/deploy/plc-generation-postgres.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-generation-worker.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-generation.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-generation-proxy.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-dvp-bridge@.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-dvp-canary@.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-dvp-canary@.timer" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-generation.Caddyfile" /etc/caddy/plc-generation.Caddyfile
install -m 0644 "$app_root/deploy/plc-generation-backup.service" /etc/systemd/system/
install -m 0644 "$app_root/deploy/plc-generation-backup.timer" /etc/systemd/system/
install -d -m 0700 /opt/plc-generation/backups
systemctl daemon-reload
systemctl enable --now plc-generation-postgres.service

ready=false
stable_checks=0
for _ in $(seq 1 80); do
  if docker exec plc-generation-postgres pg_isready -U plc_generation -d plc_generation >/dev/null 2>&1; then
    stable_checks=$((stable_checks + 1))
    if (( stable_checks >= 3 )); then
      ready=true
      break
    fi
  else
    stable_checks=0
  fi
  sleep 0.25
done
$ready

if [[ -f "$data_root/service.db" ]]; then
  PLC_DATABASE_URL="$database_url" sudo -u ubuntu -E "$python" \
    "$app_root/scripts/migrate_sqlite_to_postgres.py" \
    --sqlite "$data_root/service.db" --apply >/var/tmp/plc-database-migration-$stamp.log
  chmod 0600 /var/tmp/plc-database-migration-$stamp.log
fi

# Validation VMs are deliberately not restarted by an ordinary Web release.
# Bridge/Windows changes use rolling_restart_validation_pool.sh in a separate
# maintenance window so at least three validation nodes remain available.
systemctl is-active --quiet plc-dvp-bridge@01.service
systemctl is-active --quiet plc-dvp-bridge@02.service
systemctl is-active --quiet plc-dvp-bridge@03.service
systemctl is-active --quiet plc-dvp-bridge@04.service
systemctl enable --now plc-generation-worker.service plc-generation.service
systemctl restart plc-generation-proxy.service
systemctl disable --now plc-dvp-canary.timer plc-dvp-canary.service \
  plc-dvp-bridge.service 2>/dev/null || true
systemctl enable --now plc-dvp-canary@01.timer plc-dvp-canary@02.timer \
  plc-dvp-canary@03.timer plc-dvp-canary@04.timer
systemctl enable --now plc-generation-backup.timer
systemctl start plc-generation-backup.service

systemctl is-active --quiet plc-generation-postgres.service
systemctl is-active --quiet plc-generation-worker.service
systemctl is-active --quiet plc-generation.service
curl --fail --silent --show-error --max-time 15 http://127.0.0.1:18081/health >/dev/null
curl --fail --silent --show-error --max-time 15 \
  --cacert /etc/company-ai/certs/ai.fuxtagent.com.fullchain.pem \
  https://ai.fuxtagent.com:18080/health >/dev/null
PLC_ENVIRONMENT=production "$python" "$app_root/scripts/release_gate.py" \
  --report "$data_root/release-gate-$stamp.json"
promoted=true
trap - ERR
printf 'release promoted; rollback copy: %s\n' "$backup_root"
