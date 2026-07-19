# Self-Improving Harness — vision, gap analysis, and what's feasible

The 11-step flow you described is a real, research-backed architecture. It maps
onto three 2026 works:

- **Self-Harness** (Shanghai AI Lab, arXiv [2606.09498](https://arxiv.org/html/2606.09498v1)):
  an LLM agent improves *its own harness* from behavioral failure evidence, via
  a three-stage loop — **failure mining → harness proposal → regression
  testing** — held-out pass rates rose 40.5%→61.9%. This is exactly your steps
  5–9 (run experiments on the harness, keep only regression-free gains).
- **Darwin Gödel Machine** (Sakana AI, arXiv [2505.22954](https://arxiv.org/pdf/2505.22954)):
  a system that rewrites its own code and *empirically validates each change*
  against a benchmark (SWE-bench 20%→50%). This is your step 8–9 (validate,
  promote with rollback) — DGM's key idea is "empirical evidence, not proof,"
  which is precisely our frozen-benchmark gate.
- **Verifiers Environments Hub** (Prime Intellect): 2,500+ community RL
  environments, `prime env install owner/name`. This is your step 7 action
  "search the hub for exercises similar to what we need."
- Background: Lilian Weng, *Harness Engineering for Self-Improvement*
  ([lilianweng.github.io](https://lilianweng.github.io/posts/2026-07-04-harness/)).

**So the vision is not sci-fi — it's the current frontier, and we already have
most of the substrate.** Here's exactly where each step stands.

## Gap analysis (where we are vs. the 11 steps)

| # | Step | Status | What exists | Gap to close |
|---|------|--------|-------------|--------------|
| 1 | Karpathy autoresearch on EC2, rollouts in git branches | ✅ **done** | Cursor loop on the t3.small box; systemd; experiments as git branches | — |
| 2 | Live firehose from #daily (prices, 👍, thread prefs) | 🟡 partial | nightly episodic distillation of transcripts | reactions + thread-reply preferences not yet extracted as signal; it's nightly, not live |
| 3 | Orchestrator evaluates current episodic memory | 🟡 partial | nightly tournament treats episodic memory as one strategy | orchestrator doesn't *inspect* the memory diff explicitly |
| 4 | Reads eval metrics | ✅ done | loop scores every candidate | — |
| 5 | Experiments conditioned on Supabase "what worked" | 🟡 partial | `episodes`, `rsi_runs` tables exist | experiments don't yet read prior-winner history to bias search |
| 6 | **5 leaderboard metrics** | 🟡 4 of 5 | decision-quality, seconds/answer, forbidden-platform risk, knowledge-regression | **missing: Hermes episodic-memory diff lines** (implemented below) |
| 7 | Action space (Supabase-gated, OpenShell-gated, simulate ideas) | 🔴 mostly missing | OpenShell policies gate egress | the *action registry* (distill / update-memory / hub-search / swap-component) isn't formalized — this is the Self-Harness core |
| 8 | Evaluate with verifiers + LLM-judge on golden set | ✅ mostly | `gpu_deal_judge` env, rubric, golden dataset | rubric is rule-based; an LLM-judge reward func is a small add |
| 9 | Promote with quick rollback | ✅ done | statistical gate + auto-rollback (`auto_promote.py`) | extend from policy to harness-components |
| 10 | Notify in #eval, human-digestible | 🟡 partial | posts to #daily | dedicated #eval channel + digest format (implemented below) |
| 11 | Weekly human review by agent | ✅ done | Sunday synthesis in `nightly_master_cycle.py` | — |

**Headline: ~6 of 11 done, 4 partial, 1 (the harness action-space) is the real
frontier.** We are much closer than a from-scratch build.

## The action space (step 7) — the Self-Harness core, designed

The orchestrator's "allowed actions" become a **registry**, each action a
harness mutation that can be simulated → evaluated → promoted/rolled-back:

| Action | What it mutates | Feasible now? |
|---|---|---|
| `update_episodic_memory` | the lessons/MEMORY.md the agents load | ✅ yes (the loop already does this) |
| `search_verifiers_hub` | pull a similar env from the Hub as a new eval | 🟡 needs `prime` CLI + network policy |
| `swap_harness_component` | replace a rubric/tool/prompt module with a GitHub-recommended one | 🟡 sandboxed diff + regression test (Self-Harness §3) |
| `distill_to_smaller_model` | teach a nano agent from Super via memory (Railway) | 🟡 needs a distillation run |
| `adjust_openshell_policy` | widen/narrow an agent's egress | 🔴 security-sensitive; human-gated |

**Gating (your step 7):** an action is allowed iff (a) a past experiment in
Supabase didn't mark it regressive, (b) the OpenShell policy permits the egress
it needs, and (c) it passes the regression test on the frozen golden set before
promotion. This is exactly Self-Harness's "no-regression" guarantee plus DGM's
"empirical validation."

## What I'm implementing now (the feasible, high-value gaps)

1. **5th metric — episodic-memory diff lines** (completes your named 5). Every
   evaluation records how many lines the episodic memory changed vs. the
   champion: a direct measure of *how much the agent learned*. Added to the
   loop and the radar (5 axes).
2. **#eval channel digest** (step 10). A dedicated, human-readable eval post:
   the 5 metrics, before→after, the winning action, and a rollback button-style
   note — separate from the noisy #daily.
3. **Action registry scaffold + Supabase `harness_experiments` table** (step 7):
   records every attempted action, its metric deltas, and accept/reject, so
   future experiments read "what worked" (step 5) and the gate can forbid
   known-regressive actions.

## What stays research/roadmap (honest)

- **Live firehose** (step 2): moving from nightly to streaming needs a Discord
  gateway listener on reactions/threads — feasible but a separate build.
- **Hub-search & component-swap as live actions** (step 7): these are the
  Self-Harness/DGM frontier; we scaffold the registry now and wire the riskier
  actions behind human approval.
- **Distillation** (step 7): the teacher→student path is scaffolded
  (`export_teacher_dataset.py`); a real fine-tune needs a GPU box.

## How we evaluate all of it (step 8, unchanged discipline)

Frozen golden dataset + verifiers rubric + (new) an LLM-as-judge reward func,
memory-ON vs memory-OFF, McNemar p<0.05 for any promotion claim. Every harness
mutation is judged the same honest way a policy change is.
