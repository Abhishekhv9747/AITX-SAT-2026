#!/usr/bin/env python3
"""Autonomous promotion gate for the nightly RSI cycle.

Replaces the human --accepted decision with a statistical rule:
  PROMOTE   candidate_mean - champion_mean >= +0.01 AND the candidate's
            CI lower bound clears champion_mean - 0.01  (real, defensible gain)
  ROLLBACK  champion_mean - candidate_mean >  0.02      (regression: restore
            the champion lessons file)
  HOLD      otherwise (keep champion, keep experimenting tomorrow)

Prints the decision word on the last line (PROMOTE|ROLLBACK|HOLD) for the
shell wrapper, and appends the run to data/rsi_runs.csv via the existing
adapter so the dashboard trend line updates either way. Humans audit the
dashboard; nothing waits on them.

Usage: auto_promote.py <results.jsonl> <rsi_runs.csv> <version> <policy_change>
"""

import csv
import json
import math
import subprocess
import sys
from pathlib import Path

results_path, csv_path, version, policy_change = sys.argv[1:5]

rows = [json.loads(l) for l in open(results_path) if l.strip()]
rewards = [float(r.get("reward", 0.0)) for r in rows]
n = len(rewards)
mean = sum(rewards) / n
sd = math.sqrt(sum((x - mean) ** 2 for x in rewards) / max(n - 1, 1))
ci = 1.96 * sd / math.sqrt(n)

champion = None
if Path(csv_path).exists():
    for row in csv.DictReader(open(csv_path)):
        if row.get("accepted", "").lower() == "true":
            champion = row  # last accepted row wins
champ_mean = float(champion["decision_quality"]) if champion else -1.0

if champion is None or (mean - champ_mean >= 0.01 and (mean - ci) >= champ_mean - 0.01):
    decision = "PROMOTE"
elif champ_mean - mean > 0.02:
    decision = "ROLLBACK"
else:
    decision = "HOLD"

accepted = decision == "PROMOTE"
subprocess.run(
    [sys.executable, str(Path(__file__).parent / "verifiers_to_rsi_csv.py"),
     results_path, "--output", csv_path,
     "--run-id", version, "--version", version,
     "--policy-change", policy_change, "--teacher-model", "Nemotron",
     "--accepted", str(accepted).lower(),
     "--current", str(accepted).lower()],
    check=True,
)

print(f"candidate mean={mean:.3f} ci=±{ci:.3f} n={n} | champion={champ_mean:.3f}")
print(decision)
