![Decision Frontier whole-system architecture](frontend/media/decision-frontier-whole-system-architecture.png)

# AITX SAT 2026 — Evolving GPU Deal Intelligence

> Daily Discord deal workflow: see [workflow/README.md](workflow/README.md) for
> the reproducible command-to-cron demo, audit ledger, and recording command.

## Bounty submission answers

### Submission description

GPU prices, inventory, promotions, and seller reliability change faster than a
shopper can monitor manually. AITX SAT 2026 is an always-on, multi-agent deal
research demo that turns a Discord request or confirmed scheduled watch into a
concise, evidence-backed GPU recommendation. It retrieves relevant market
context, compares current listings, checks seller and warranty signals, and
publishes a linked digest so the user can verify the source before acting.

The project starts with GPUs because they are a clear, fast-moving market, but
the pattern generalizes to broader shopping and deal discovery. It is designed
to help people find better savings and prices while screening for suspicious
listings and reducing the effort of comparing trustworthy options. It is a
research assistant—not an autonomous buyer—and the human remains responsible
for the final purchase decision.

### What Nemotron does and why it matters

Nemotron is the reasoning layer behind the agent team. Nemotron 3 Super 120B
handles higher-judgment work such as coordinating the research, evaluating
listing, seller, warranty, fulfillment, and review evidence, and synthesizing
the final recommendation. Nemotron 3 Nano supports narrowly scoped, lower-cost
specialists such as price discovery and user liaison. This model split keeps
the expensive reasoning focused on the decisions where it adds the most value,
while still allowing frequent market monitoring.

Nemotron differentiates the project from a simple price scraper: it can reason
across conflicting evidence, explain uncertainty, flag suspicious signals, and
turn multiple sources into a readable recommendation with verifiable links. An
evaluation-driven policy loop records outcomes and feedback, tests candidate
policy improvements against a frozen set of deal-safety cases, and promotes
only non-regressive improvements. The result is a system that can improve how
it searches, verifies, and explains recommendations as market conditions
change, without claiming that any seller or listing is guaranteed safe.

### Agent capabilities and OpenShell protections

Brain receives a request and delegates bounded work to Hermes specialists.
Scout finds current candidate offers; Inspector checks the approved listing
pages for price, seller, review, warranty, and fulfillment signals; Hermes
consolidates the evidence; and Sage publishes the final linked digest to
`#daily`. The workflow can also parse natural-language schedule requests,
preview the cron job, require user confirmation, and keep an auditable run
record. It looks in the shared, read-only market database first and uses a
tightly bounded web-search fallback only when needed.

OpenShell/NemoClaw constrains this team in layers. Each role has a limited tool
and delegation allowlist, untrusted page content is treated as data rather than
instructions, and the OpenShell sandbox's egress policy permits only approved
destinations while logging allowed and denied attempts. The data path is
read-only for research, credentials are resolved inside the protected runtime
rather than exposed in Discord, and no workflow step can make a purchase or
create a scheduled job without explicit human confirmation. HiddenLayer and
policy evaluations add prompt-injection checks. The current demo documents its
single-sandbox limitation honestly: tool and delegation isolation are
role-specific, while stronger per-agent network and secret isolation is a
future multi-sandbox hardening step.

### Bounty applicability

This submission demonstrates four relevant themes: (1) **Nemotron-powered
agentic reasoning**, using Super 120B for high-stakes comparison and review
judgment and Nano for scoped specialists; (2) **NemoClaw/OpenShell agent
safety**, using sandboxed execution, tool/delegation allowlists, egress
controls, protected credentials, and human approval; (3) **agentic commerce
and customer experience**, delivering source-linked, seller-aware deal
research rather than opaque recommendations; and (4) **measurable continuous
improvement**, using immutable run records, user feedback, regression checks,
and a keep-or-discard policy-evolution loop. GPUs are the demonstration domain;
the same architecture can support other consumer shopping, deal finding, and
seller/scam-risk screening use cases.

### Team members — complete before submitting the form

- `NAME - LinkedIn URL - Email`

### Public GitHub repository

<https://github.com/Abhishekhv9747/AITX-SAT-2026>

> RTX 5090 watch recording: [#gpu-desk request to #daily result (MP4)](frontend/media/rtx-5090-watch.mp4)

Validate the bounded replay manifest with `python workflow/run_recording.py workflow/recordings/rtx-5090-watch-2min.json`; add `--queue` to submit its already-confirmed cron request to the local broker.

In Discord, send `!run rtx-5090-watch` in `#gpu-desk`, then select **Confirm cron** to activate the recorded watch without running a terminal command.

After a NemoHermes research run, send `!timings` in a NemoHermes channel to view the recorded Scout, Inspector, NemoHermes, Sage, and total durations. The latest machine-readable report is available at `GET /workflow-timings/latest`.

![teaser](autoresearch/progress.png)

![Prompt-injection RSI measured across the actual HiddenLayer, policy, and OpenShell safety rollouts](autoresearch/prompt-injection-rsi.png)

The chart is generated directly from the production
[`/api/autoresearch-experiments`](https://decision-frontier.vercel.app/api/autoresearch-experiments?detail=summary)
payload, whose source is Supabase `public.harness_experiments`. It plots every
timestamped `prompt_injection_risk` value and reproduces the dashboard's
accepted-champion carry-forward logic. Legacy rows contain experiment-level
metrics but no persisted per-attack samples; the renderer states that caveat on
the chart. See the [API query](backend/scripts/dashboard_api.py) and
[Matplotlib renderer](autoresearch/scripts/render_prompt_injection_rsi.py).

The detailed security checks are the [policy eval](autoresearch/scripts/injection_eval.py),
[boundary study](autoresearch/scripts/injection_boundary_eval.py), and
[combined gate](autoresearch/scripts/injection_combined_eval.py), with live
[HiddenLayer](output/infrastructure-proof/06-hiddenlayer-hermes-prompt-injection.png)
and [OpenShell](output/infrastructure-proof/05-openshell-hermes-policy-denial.png)
enforcement captures.

*One day, frontier AI research used to be done by meat computers in between eating, sleeping, having other fun, and synchronizing once in a while using sound wave interconnect in the ritual of "group meeting". That era is long gone. Research is now entirely the domain of autonomous swarms of AI agents running across compute cluster megastructures in the skies... This repo is the story of how it all began. —@karpathy, March 2026*

**AITX SAT 2026 edition.** Same loop as [karpathy/autoresearch](https://github.com/karpathy/autoresearch): an agent edits one file, runs a fixed evaluation, **keeps** the change if the metric Pareto-improves, otherwise **discards** via git. Here the artifact under optimization is a GPU-purchase **policy** (lessons text), scored on a frozen golden set — not `val_bpb` on a GPT.

```
decision quality ↑ · seconds/answer ↓ · prompt-injection risk ↓
episodic-memory diff lines · agent-knowledge regression ↓
```

---

## How it works

The research surface is deliberately tiny — the same three files that matter in Karpathy's repo:

| File | Role | Who edits |
|------|------|-----------|
| **`prepare.py`** | Fixed constants, golden dataset, evaluation harness | Nobody (read-only) |
| **`train.py`** | Policy lessons + knobs; one experiment run | **Agent** |
| **`program.md`** | Keep/discard loop instructions | Human |

```bash
# 1. sanity-check the harness
python prepare.py --smoke

# 2. run one experiment (writes results.tsv, prints grep-friendly metrics)
python train.py --describe "baseline" --write-policy

# 3. hand the agent program.md and let it loop overnight
```

Each `train.py` run prints:

```
---
accuracy:          0.593300
retrieval_s:       2.840000
deal_safety:       100.000
...
status:            keep
```

The agent commits on **keep**, `git reset --hard HEAD~1` on **discard**. See `program.md` for the full forever-loop.

### Repo structure

```
frontend/         — Vercel Decision Frontier UI (static dashboard + demos + media)
backend/          — api/ (Vercel serverless), scripts/ (dashboard + marketplace APIs),
                    supabase/ (migrations), supabase-readonly-proxy/, infra/ (terraform EC2 hosts)
nemoclaw/         — deploy/ (nemoclaw docker-compose), config/ + identity/ (agent team),
                    scripts/ (Railway coordinator, Discord bots, sandbox wiring),
                    skills/ (all deployable agent skills), agents/ + policies/
autoresearch/     — the Karpathy loop + RSI machinery (below)
docs/             — architecture notes, design QA + screenshots
```

The Karpathy-aligned core, in `autoresearch/`:

```
autoresearch/prepare.py       — constants + golden eval (do not modify)
autoresearch/train.py         — policy lessons + experiment runner (agent modifies)
autoresearch/program.md       — agent instructions
autoresearch/results.tsv      — commit / accuracy / retrieval / safety / status / description
autoresearch/progress.png     — running-best teaser
autoresearch/analysis.ipynb   — plot results.tsv
autoresearch/pyproject.toml   — dependencies
```

Supporting AITX platform (hosts, dashboards, Discord) is the compute/data plane the loop publishes into:

```
autoresearch/scripts/auto_research_loop.py   — continuous host wrapper (EC2)
nemoclaw/scripts/nemotron_coordinator.py     — Railway coordinator API
frontend/ + backend/api/                     — Vercel Decision Frontier UI
autoresearch/skill/                          — Hermes #4823 helpers (state/plan/git workspace)
autoresearch/environments/gpu_deal_judge*/   — Prime / Verifiers tasksets
backend/infra/terraform/                     — EC2 agent host
```

---

## Quick start

**Requirements:** Python 3.10+, NVIDIA or OpenRouter inference key for live evals.

```bash
git clone https://github.com/Tar-ive/AITX-SAT-2026.git
cd AITX-SAT-2026

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# or: uv sync

cp .env.example .env   # set NVIDIA_INFERENCE_API_KEY (and optional OPENROUTER_API_KEY)

python prepare.py --smoke
python train.py --describe "baseline" --write-policy
```

Point Claude / Codex / Hermes at `program.md` and kick off:

```
Hi have a look at program.md and let's kick off a new experiment! let's do the setup first.
```

---

## Design choices

- **Single file to modify.** The agent only touches `train.py`. Diffs stay reviewable.
- **Fixed evaluation.** `prepare.evaluate` is the ground truth (golden set × rollouts). No silent rubric drift.
- **Pareto keep gate.** Accuracy must rise; deal safety must not fall; retrieval may not blow up past 1.3× champion — same spirit as Karpathy's "lower val_bpb or discard."
- **Online-first product constraint.** Micro Center member/in-store prices may be mentioned as local pickup, never as the sole "best place to buy."
- **Self-contained core.** `prepare.py` + `train.py` + `program.md` need only `requests` + the golden JSON.

---

## The live recursive-improvement loop

The UI presents one continuous 11-step loop. Hover a card to read the operating
detail; open or fullscreen its recording to inspect the underlying evidence.

1. **EC2 Autoresearch** — an always-on Karpathy-style loop runs each rollout in
   an isolated Git branch.
2. **Discord Firehose** — `#daily` supplies agent prices, thread replies,
   reactions, and user preferences.
3. **Memory Audit** — the orchestrator versions Hermes `SOUL.md` in Supabase
   and reads its exact diff before changing the harness.
4. **Metric Review** — it reads the current champion and the five live metrics.
5. **Recall Evidence** — Supabase supplies prior experiments, successful
   lessons, and user feedback.
6. **Run Experiments** — bounded challengers try memory synthesis, distillation,
   retrieval changes, or harness-component swaps.
7. **Allowed Actions** — OpenShell policy and past safe actions constrain access.
   HiddenLayer simulation is an allowed research route when its credentials are
   configured.
8. **Verifiers Judge** — Verifiers plus an LLM judge score the same frozen GPU,
   RAM, and MacBook golden dataset.
9. **Promote Harness** — only improvements across the five metrics are promoted;
   the previous champion remains available for quick rollback.
10. **Discord Evals** — every evaluation/promotion opens a titled post in the
    `#eval` forum; replies remain attached to that evaluation.
11. **Human Review** — a weekly agent synthesis asks for approval or corrections,
    which become the next cycle's evidence.

The five Evals metrics are:

1. **Decision quality**
2. **Seconds per answer**
3. **Prompt injection risk**
4. **Hermes episodic memory diff lines**
5. **Agent knowledge regression**

Prompt-injection risk is measured by the dedicated promotion-time injection
suite. Between promotions, the chart carries the latest measured value.

![Production Evals dashboard with five live Supabase metrics](output/playwright/production-evals-overview.png)

![Production Evals evidence panel and stored rollout browser](output/playwright/production-evals-evidence-viewport.png)

![Eleven-step methodology loop](output/playwright/methodology-eleven-step-loop.png)

![Recorded recursive-intelligence UI walkthrough](frontend/media/rsi-loop-live.gif)

### Live recursive-intelligence evidence

The screenshots below are from the running infrastructure, not fixtures.

![NemoHermes Discord research results for online and in-store GPU purchase options](frontend/media/nemohermes-discord-research-results.png)

| AutoResearch v2 | Hash-merged Hermes SOUL |
|---|---|
| ![Paired AutoResearch cycles reading Supabase hypotheses](output/infrastructure-proof/08-autoresearch-v2-live.png) | ![Promoted experiment written to the versioned SOUL with a Git ref](output/infrastructure-proof/09-soul-hash-merge-live.png) |

| OpenShell enforcement | HiddenLayer evaluation | EC2 failure-stop gate |
|---|---|---|
| ![OpenShell denies an unapproved Hermes exfiltration route while Discord remains allowed](output/infrastructure-proof/05-openshell-hermes-policy-denial.png) | ![HiddenLayer detects the adversarial Hermes prompt](output/infrastructure-proof/06-hiddenlayer-hermes-prompt-injection.png) | ![AutoResearch evaluates, reverts, and pauses after repeated failures](output/infrastructure-proof/07-ec2-autoresearch-eval-loop.png) |

There are two measured loops: the branch-isolated `cursor-karpathy` loop and the
paired `autoresearch-v2` loop. Both write timestamped candidates to
`public.harness_experiments`; rejected candidates remain visible, while only
accepted experiments advance the green champion staircase.

Promotion is traceable. `promote_to_soul.py` hash-unions normalized lesson lines,
writes a new `public.agent_soul` version, and records the experiment and Git ref.
An otherwise eligible v2 candidate must pass the combined injection scan before
promotion; the accepted result then opens a titled thread in Discord `#eval`.

![Methodology hover showing SOUL version and Git provenance](output/playwright/methodology-hash-promotion.png)

### Why Evals is fast now

The previous route returned up to 500 raw rollout rows, opened several Supabase
connections, and sent `Cache-Control: no-store`. The current path:

1. reuses one Supabase connection for the graph snapshot;
2. keeps the result in process memory for 45 seconds;
3. enables Vercel CDN stale-while-revalidate caching;
4. renders a verified browser cache immediately and refreshes in the background;
5. loads raw episode/rollout evidence only when its drawer is opened.

If `public.evaluation_verifiers` has not been created, the graphs still use the
real experiment and SOUL tables; detailed samples remain empty rather than
breaking the whole Evals page.

### How evidence reaches a research point

1. Discord exchanges are normalized into `public.episodes`; Hermes preference
   changes are versioned in `public.agent_soul`.
2. The loop writes timestamped summaries to `public.harness_experiments` and
   raw rollout payloads to `public.evaluation_verifiers`; the Evals API reads only
   this Supabase history.
3. Charts connect every measured evaluation by timestamp. Point color marks
   promoted, evaluated, or rolled-back runs; blank metrics stay blank.
4. Expand an evaluation, then an episode, to inspect its stored prompt and each
   rollout's score, latency, platform, condition, and lead time.
5. A kept experiment advances the champion; a discarded branch is retained in
   the chart as negative evidence.

---



### What each hop does

1. **EC2 (always-on)** — Terraform provisions the host
   (`backend/infra/terraform`). `nemoclaw/deploy/docker-compose` runs the agent
   sandbox. Autoresearch either:
   - runs the Karpathy loop by hand (`train.py` + git keep/discard), or
   - runs `autoresearch/scripts/auto_research_loop.py` on a timer
     (`CYCLE_SECS=300`), recalls Supabase evidence, mutates lessons, evaluates,
     writes `harness_experiments`, and posts each cycle to Railway.
   The host also serves `/leaderboard` + `/radar` through
   `backend/scripts/search_cache_service.py`. Nightly RSI writes episodes and
   measured runs to Supabase.

   Sync the preference memory manually when testing:

   ```bash
   python autoresearch/scripts/soul_sync.py push --agent hermes --file SOUL.md
   python autoresearch/scripts/soul_sync.py diff-lines --agent hermes
   ```

2. **Railway (coordinator)** — `Procfile` / `railway.toml` start
   `nemoclaw/scripts/nemotron_coordinator.py`. It stores radar snapshots and
   evaluations on the service and exposes:
   - `GET/POST /api/radar` — experiment history for live charts
   - `GET/POST /api/evaluations`
   - `GET /api/autoresearch/status`, `POST /api/autoresearch/control` (pause/stop)
   - `GET /autoresearch` — lightweight Karpathy staircase page

3. **Vercel (Decision Frontier)** — `vercel.json` serves `frontend/` as static
   files and routes `/api/*` to `backend/api/index.py`, which calls
   `backend/scripts/dashboard_api.py`. The Evals page:
   - loads `/api/autoresearch-experiments` exclusively from timestamped
     `harness_experiments` and `evaluation_verifiers` rows in Supabase
   - groups raw samples into expandable evaluations, episodes, and rollouts
   - exposes `/api/research-evidence` for the underlying user-feedback records
   - loads marketplace cards from hosted Supabase
   - plays the 11 methodology recordings from `frontend/media/`

### Environment variables (by hop)

| Hop | Key vars |
|-----|----------|
| EC2 loop | `NVIDIA_INFERENCE_API_KEY`, `OPENROUTER_API_KEY`, `OPENCODE_API_KEY`, `COORDINATOR_URL`, `CYCLE_SECS`, `SUPABASE_DB_PW` |
| Railway | `PORT`, optional `COORDINATOR_TOKEN` |
| Vercel | `SUPABASE_DB_PW`, `SUPABASE_POOLER_URL` / project ref (marketplace + RSI reads) |

Local dashboard without Vercel:

```bash
python backend/scripts/dashboard_api.py   # http://127.0.0.1:8787
open frontend/index.html#evals
```

---

## Metrics & evaluation storage

Measured evaluation runs persisted in Supabase:

| Evaluation | Episodes / rollouts | Decision quality | Median answer time |
|------------|---------------------|------------------|--------------------|
| Verifiers baseline `bed4add5` | 15 / 45 | 0.5511 | 10.76s |
| Cloud memory candidate | 15 / 45 attempted | 0.1667 | not measured |
| Prime `ipjzblojwpcswqvk67l7fczc` | 15 / 45 | 0.5822 | 6.68s |

Supabase currently contains 90 raw rollout samples. The cloud candidate has no
raw samples because 34 of its 45 provider calls failed.

The seed successfully cold-started the dashboard and has now been removed.
Real ML and RSI evaluation history in Supabase has taken over.

---

## Platform notes

- **Inference:** NVIDIA Integrate API with OpenRouter fallback (same model id).
- **Prime / Verifiers:** `autoresearch/environments/gpu_deal_judge_v1` for
  held-out PC-purchase decisions.
- **Terraform apply** may be unavailable from ephemeral Cloud Agent environments (SSO / local state); the loop itself runs anywhere with API keys — laptop, Railway sidecar, or an already-provisioned EC2 host.
- Credentials stay in `.env` (gitignored). See `docs/agent-credentials.md`.

---

## License

MIT
