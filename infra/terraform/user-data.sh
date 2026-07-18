#!/bin/bash
# First-boot bootstrap for the AITX agent host (Ubuntu 24.04).
# Installs Docker, clones the STABLE FORK, prepares the deploy stack, and
# schedules the July 20 backup+self-stop. Secrets (.env) are NOT baked in —
# they arrive via scp after provisioning (see infra/README.md step 4).
set -euxo pipefail
exec > /var/log/aitx-bootstrap.log 2>&1

apt-get update -q
apt-get install -y -q docker.io docker-compose-v2 git curl jq

# Clone the user's fork (more stable than upstream; public, no auth needed)
install -d -o ubuntu -g ubuntu /opt/aitx
sudo -u ubuntu git clone https://github.com/Tar-ive/AITX-SAT-2026.git /opt/aitx/repo || true
usermod -aG docker ubuntu

# Backup + self-stop script (July 20, 05:00 UTC == July 20, 00:00 CDT)
cat > /opt/aitx/backup-and-stop.sh <<'EOS'
#!/bin/bash
set -x
TS=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p /opt/aitx/backups
C=$(docker ps -a --format '{{.Names}}' | grep openshell- | head -1)
if [ -n "$C" ]; then
  docker cp "$C:/sandbox/.openclaw" "/opt/aitx/backups/openclaw-state-$TS" || true
  tar czf "/opt/aitx/backups/openclaw-state-$TS.tar.gz" -C /opt/aitx/backups "openclaw-state-$TS" && rm -rf "/opt/aitx/backups/openclaw-state-$TS"
fi
cp /opt/aitx/repo/deploy/docker-compose/.env "/opt/aitx/backups/env-$TS.bak" 2>/dev/null || true
sync
shutdown -h +2 "AITX 2-day lifetime reached; agents backed up to /opt/aitx/backups"
EOS
chmod 700 /opt/aitx/backup-and-stop.sh

cat > /etc/cron.d/aitx-selfstop <<'EOC'
0 5 20 7 * root /opt/aitx/backup-and-stop.sh
EOC

echo "bootstrap complete"
