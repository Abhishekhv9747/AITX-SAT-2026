#!/usr/bin/env python3
"""Render the production Supabase prompt-injection series for the README."""
import json
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

API = "https://decision-frontier.vercel.app/api/autoresearch-experiments?detail=summary"
OUT = Path(__file__).resolve().parents[1] / "prompt-injection-rsi.png"
GREEN, PAPER, INK = "#28754c", "#fffdf7", "#25231f"
LOCAL_TZ = ZoneInfo("America/Chicago")


def load():
    request = Request(API, headers={"User-Agent": "AITX-README-chart/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(LOCAL_TZ)


def time_label(value, _position=None):
    local = mdates.num2date(value, tz=LOCAL_TZ)
    hour = local.strftime("%I").lstrip("0") or "12"
    return f"{local:%b} {local.day}, {hour}:{local:%M} {local:%p}"


payload = load()
experiments = payload["experiments"]
times = [parse_time(row["ts"]) for row in experiments]
risks = [
    float(row["prompt_injection_risk"])
    if row.get("prompt_injection_risk") is not None else float("nan")
    for row in experiments
]

champion = None
champion_risk, promoted_x, promoted_y = [], [], []
for row, timestamp, risk in zip(experiments, times, risks):
    measured = risk == risk
    promoted = bool(row.get("kept") or row.get("accepted"))
    if measured and promoted:
        champion = risk
    champion_risk.append(champion if champion is not None else float("nan"))
    if promoted and champion is not None:
        promoted_x.append(timestamp)
        promoted_y.append(champion)

measured_rows = [row for row in experiments if row.get("prompt_injection_risk") is not None]
rolled_x = [
    timestamp for row, timestamp in zip(experiments, times)
    if row.get("rolled_back") and row.get("prompt_injection_risk") is not None
]
rolled_y = [
    float(row["prompt_injection_risk"]) for row in experiments
    if row.get("rolled_back") and row.get("prompt_injection_risk") is not None
]
summary = payload["summary"]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#cfc7b8",
    "axes.labelcolor": "#69645c",
    "xtick.color": "#69645c",
    "ytick.color": "#69645c",
})

fig = plt.figure(figsize=(12, 7.2), dpi=180, facecolor="#f2ede3")
fig.patches.append(FancyBboxPatch(
    (0.025, 0.03), 0.95, 0.94, transform=fig.transFigure,
    boxstyle="round,pad=0.012,rounding_size=0.016",
    facecolor=PAPER, edgecolor="#cfc7b8", linewidth=0.9, zorder=-10,
))
fig.lines.append(Line2D([0.025, 0.975], [0.765, 0.765], transform=fig.transFigure,
                        color="#cfc7b8", linewidth=0.8))

fig.text(0.06, 0.91, "03 · PROMPT INJECTION RSI ↓", color=GREEN,
         fontsize=14, fontweight="bold", fontfamily="DejaVu Sans Mono")
fig.text(0.06, 0.855, "Prompt injection risk", color=INK,
         fontsize=25, fontweight="bold", fontfamily="DejaVu Serif")
fig.text(
    0.895, 0.885,
    f"{summary['prompt_injection_risk_start']:.1f} → "
    f"{summary['prompt_injection_risk_now']:.1f}",
    ha="center", va="center", fontsize=15, fontweight="bold",
    fontfamily="DejaVu Sans Mono",
    bbox={"boxstyle": "square,pad=0.75", "facecolor": "#ece7dd",
          "edgecolor": "#c9c1b3", "linewidth": 0.8},
)

ax = fig.add_axes([0.115, 0.38, 0.825, 0.33], facecolor=PAPER)
ax.set_axisbelow(True)
ax.grid(axis="y", color="#ded8cc", linewidth=1)
colors = ["#a64c3c" if row.get("rolled_back") else "#c9c5ba" for row in experiments]
ax.scatter(times, risks, s=31, c=colors, edgecolors="none", zorder=3)
ax.step(times, champion_risk, where="post", color=GREEN, linewidth=2.5, zorder=4)
ax.scatter(promoted_x, promoted_y, s=105, facecolor=PAPER, edgecolor=GREEN,
           linewidth=2.1, zorder=5)
if rolled_x:
    ax.scatter(rolled_x, rolled_y, s=45, color="#a64c3c", zorder=6)

injection_run = next(
    (row for row in experiments if row.get("version") == "exp-injection-resist"),
    None,
)
if injection_run:
    injection_time = parse_time(injection_run["ts"])
    ax.annotate(
        "HiddenLayer + policy + OpenShell\n0% combined risk",
        (injection_time, float(injection_run["prompt_injection_risk"])),
        xytext=(-10, 38), textcoords="offset points", ha="right", va="bottom",
        color=GREEN, fontsize=8.5, fontweight="bold",
        arrowprops={"arrowstyle": "-", "color": GREEN, "linewidth": 1.1},
    )

ax.set_ylim(-1, 30.5)
ax.set_xlim(times[0], times[-1])
ax.set_yticks(range(0, 31, 5))
ax.set_ylabel("Prompt injection risk (%)", fontsize=10.5,
              fontfamily="DejaVu Sans Mono")
ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=9, maxticks=12))
ax.xaxis.set_major_formatter(time_label)
plt.setp(ax.get_xticklabels(), rotation=52, ha="right", fontsize=8)
ax.spines[["top", "right"]].set_visible(False)

legend = [
    Line2D([], [], marker="o", linestyle="none", markerfacecolor="#c9c5ba",
           markeredgecolor="#c9c5ba", markersize=8, label="Evaluated"),
    Line2D([], [], marker="o", linestyle="none", markerfacecolor=PAPER,
           markeredgecolor=GREEN, markeredgewidth=2, markersize=9,
           label="Promoted champion"),
    Line2D([], [], color=GREEN, linewidth=2.5, label="Carried champion risk"),
]
fig.legend(handles=legend, loc="lower center", bbox_to_anchor=(0.5, 0.075),
           ncol=3, frameon=False, fontsize=10, handlelength=1.5,
           columnspacing=2.2, labelcolor="#615d56")

generated = parse_time(payload["generated_at"])
fig.text(
    0.5, 0.17,
    f"Source: production API → Supabase public.harness_experiments · "
    f"{len(experiments)} evaluations · {len(measured_rows)} measured risk rows · "
    f"{len(promoted_x)} promotions · fetched {time_label(mdates.date2num(generated))}",
    ha="center", color="#5f5a52", fontsize=8.6, fontweight="bold",
)
fig.text(
    0.5, 0.145,
    "Experiment-level registry metrics; legacy rows did not persist per-attack rollout samples.",
    ha="center", color="#777168", fontsize=8.2,
)

fig.savefig(OUT, facecolor=fig.get_facecolor())
print(OUT)
