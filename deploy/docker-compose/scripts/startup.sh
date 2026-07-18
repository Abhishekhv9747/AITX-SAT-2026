#!/usr/bin/env bash
# Workspace entrypoint: install NemoClaw, onboard the agent team, inject the
# repo identity layer, then follow logs. Idempotent across container restarts.
set -euo pipefail

echo "[startup] installing prerequisites"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl git ca-certificates docker.io >/dev/null

export PATH="$HOME/.local/bin:$PATH"

if ! command -v nemoclaw >/dev/null 2>&1; then
  echo "[startup] installing NemoClaw"
  curl -fsSL https://www.nvidia.com/nemoclaw.sh -o /tmp/nemoclaw-installer.sh
  bash /tmp/nemoclaw-installer.sh --non-interactive --yes-i-accept-third-party-software
fi

echo "[startup] onboarding sandbox '$NEMOCLAW_SANDBOX_NAME' with agent team"
nemoclaw onboard --agents /deploy/config/agents.yaml || {
  echo "[startup] onboard failed; retrying with --resume"
  nemoclaw onboard --resume
}

echo "[startup] injecting identity layer"
C=$(docker ps --format '{{.Names}}' | grep "openshell-${NEMOCLAW_SANDBOX_NAME}" | head -1)
if [ -n "$C" ]; then
  WS=/sandbox/.openclaw/workspace
  docker exec "$C" sh -c "[ -f $WS/AGENTS.md.stock ] || cp $WS/AGENTS.md $WS/AGENTS.md.stock"
  docker cp /deploy/identity/AGENTS.team.md "$C:/tmp/AGENTS.team.md"
  docker exec "$C" sh -c "
    awk '/<!-- BEGIN AITX-TEAM-PROTOCOL/{skip=1} !skip{print} /<!-- END AITX-TEAM-PROTOCOL/{skip=0}' \
      $WS/AGENTS.md > /tmp/AGENTS.base.md
    cat /tmp/AGENTS.base.md /tmp/AGENTS.team.md > $WS/AGENTS.md
    rm /tmp/AGENTS.base.md /tmp/AGENTS.team.md"
  echo "[startup] identity injected into $C"
else
  echo "[startup] WARNING: sandbox container not found; identity not injected"
fi

echo "[startup] ready — following sandbox logs"
exec nemoclaw "$NEMOCLAW_SANDBOX_NAME" logs --follow
