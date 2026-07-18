#!/usr/bin/env bash
# Fully autonomous nightly RSI cycle (EC2 host cron, 05:30 UTC — right after
# the 05:00 memory distillation). No human in the loop:
#   1. snapshot tonight's lessons out of the sandbox
#   2. vf-eval rollouts with lessons injected (memory ON)
#   3. auto_promote.py decides: PROMOTE / HOLD / ROLLBACK
#   4. PROMOTE  -> tonight's lessons become the champion snapshot
#      ROLLBACK -> champion lessons restored into the sandbox (bad night undone)
#   5. trend CSV updated either way; full audit trail in /opt/aitx/rsi-cycles.log
set -uo pipefail
exec >> /opt/aitx/rsi-cycles.log 2>&1
echo "=== RSI cycle $(date -u +%FT%TZ) ==="

REPO=/opt/aitx/repo
cd "$REPO"
set -a; . deploy/docker-compose/.env; set +a
export OPENAI_API_KEY="${NVIDIA_INFERENCE_API_KEY:?}"
export GOLDEN_DATASET="$REPO/scripts/golden_dataset.json"
export PATH="/root/.local/bin:$PATH"

C=$(docker ps --format '{{.Names}}' | grep openshell- | head -1)
[ -n "$C" ] || { echo "no sandbox running; abort"; exit 1; }

mkdir -p /opt/aitx/memory
VERSION="auto-$(date -u +%Y%m%d)"
LESSONS=/opt/aitx/memory/lessons-$VERSION.md
CHAMPION=/opt/aitx/memory/champion-lessons.md

docker cp "$C:/sandbox/.openclaw/workspace/MEMORY.md" "$LESSONS" 2>/dev/null || echo "" > "$LESSONS"
echo "lessons snapshot: $LESSONS ($(wc -l < "$LESSONS") lines)"

cd "$REPO/environments/gpu_deal_judge"
uv run --with verifiers --with . vf-eval gpu-deal-judge \
  -m "nvidia/nemotron-3-super-120b-a12b" \
  -b "https://integrate.api.nvidia.com/v1" -k OPENAI_API_KEY \
  -n 15 -r 3 -s --env-args "{\"memory_file\": \"$LESSONS\"}" || { echo "eval failed"; exit 1; }

RESULTS=$(ls -t "$PWD"/outputs/evals/*/*/results.jsonl | head -1)
cd "$REPO"
DECISION=$(python3 scripts/auto_promote.py "$RESULTS" data/rsi_runs.csv \
  "$VERSION" "Nightly lessons $(date -u +%F) (auto)" | tee /dev/stderr | tail -1)

case "$DECISION" in
  PROMOTE)
    cp "$LESSONS" "$CHAMPION"
    echo "PROMOTED: tonight's lessons are the new champion." ;;
  ROLLBACK)
    if [ -s "$CHAMPION" ]; then
      docker cp "$CHAMPION" "$C:/sandbox/.openclaw/workspace/MEMORY.md"
      echo "ROLLED BACK: champion lessons restored into the sandbox."
    else
      echo "ROLLBACK requested but no champion snapshot exists; holding."
    fi ;;
  HOLD)
    echo "HOLD: champion unchanged; lessons stay for another night of data." ;;
esac
echo "trend row appended to data/rsi_runs.csv (decision: $DECISION)"
