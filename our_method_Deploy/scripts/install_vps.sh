#!/usr/bin/env bash
set -euo pipefail

DEPLOY_ROOT=${PLC_DEPLOY_ROOT:-/opt/plc-generation/app}
CONDA_ROOT=${PLC_CONDA_ROOT:-/home/ubuntu/miniforge3}
ENV_NAME=${PLC_CONDA_ENV:-plc_generation}
INSTALLER=/tmp/Miniforge3-Linux-x86_64.sh

sudo apt-get update
if apt-cache show freerdp3-x11 >/dev/null 2>&1; then
  freerdp_package=freerdp3-x11
else
  freerdp_package=freerdp2-x11
fi
sudo apt-get install -y xvfb xdotool x11-utils "$freerdp_package"

if [[ ! -x "$CONDA_ROOT/bin/conda" ]]; then
  curl -fsSL --retry 4 -o "$INSTALLER" \
    https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  bash "$INSTALLER" -b -p "$CONDA_ROOT"
  rm -f "$INSTALLER"
fi

if ! "$CONDA_ROOT/bin/conda" env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
  "$CONDA_ROOT/bin/conda" create -y -n "$ENV_NAME" python=3.11 pip
fi

"$CONDA_ROOT/bin/conda" run -n "$ENV_NAME" python -m pip install --upgrade pip
"$CONDA_ROOT/bin/conda" run -n "$ENV_NAME" python -m pip install "$DEPLOY_ROOT[test]"
mkdir -p /opt/plc-generation/data/jobs
mkdir -p /opt/plc-generation/dvp-bridge/dvp-spool/{pending,results}
chmod 700 /opt/plc-generation/data /opt/plc-generation/data/jobs
chmod 700 /opt/plc-generation/dvp-bridge /opt/plc-generation/dvp-bridge/dvp-spool
printf 'Environment %s is ready at %s\n' "$ENV_NAME" "$CONDA_ROOT"
