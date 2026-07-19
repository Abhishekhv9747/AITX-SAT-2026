-- Self-Harness action registry (docs/self-improving-harness.md, step 7).
-- Every harness mutation the orchestrator attempts is recorded here: which
-- action, its metric deltas, and accept/reject. Future experiments read this
-- to (a) bias search toward what worked and (b) forbid known-regressive
-- actions — the Self-Harness "no-regression" guarantee, backed by data.

create table if not exists public.harness_experiments (
    id bigint generated always as identity primary key,
    experiment_id text not null unique,
    action text not null check (action in (
        'update_episodic_memory', 'search_verifiers_hub', 'swap_harness_component',
        'distill_to_smaller_model', 'adjust_openshell_policy', 'mutate_policy')),
    hypothesis text,
    -- the 5 leaderboard metrics, candidate vs champion
    decision_quality numeric,
    seconds_per_answer numeric,
    forbidden_platform_risk numeric,   -- lower is better
    memory_diff_lines integer,          -- Hermes episodic-memory churn (5th metric)
    knowledge_regression numeric,       -- accuracy delta vs champion; <0 = regressed
    accepted boolean not null default false,
    rolled_back boolean not null default false,
    source_box text,                    -- 'cursor-karpathy' | 'main-loop' | 'nightly-tournament'
    created_at timestamptz not null default now()
);

create index if not exists harness_experiments_action_idx
    on public.harness_experiments (action, accepted, created_at desc);

alter table public.harness_experiments enable row level security;
