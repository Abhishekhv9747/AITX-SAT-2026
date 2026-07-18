# External APIs, Datasets, Keys & Access Control

Companion to `unified_ecommerce_agent_architecture.md` (Saksham's six-agent
design) and `config/agents.yaml` (the enforcement). Scope: the daily GPU
price-watch MVP plus the review-audit loop.

## 1. APIs and data sources

Status verified July 18, 2026.

| Source | What for | Access | Configuration |
|---|---|---|---|
| **eBay Browse API** | Live new/used listings, price, shipping, seller data | Free developer account. Browse search uses a client-credentials **application** token. Sandbox and Production keys are separate. | `EBAY_ENV`, `EBAY_CLIENT_ID`, `EBAY_CLIENT_SECRET`, `EBAY_MARKETPLACE_ID` |
| **Best Buy Products API** | Near-real-time retail price, availability, specs, and images | Free API key; recommended second live-price source | `BESTBUY_API_KEY` |
| **Amazon Creators API** | Amazon catalog, offers, and availability | Replaced PA-API on May 15, 2026. Requires Amazon Associates, 10 qualifying sales in the previous 30 days, app registration, credentials, and partner tag. | `AMAZON_CREATORS_CREDENTIAL_ID`, `AMAZON_CREATORS_CREDENTIAL_SECRET`, `AMAZON_PARTNER_TAG` |
| **Open Icecat** | Structured manufacturer specs, MPN/GTIN matching, images | Free registration; catalog enrichment, not a dependable live-price feed | `ICECAT_USERNAME` |
| **Wikidata** | Open identifiers and sparse manufacturer/model metadata | Free SPARQL endpoint, no key; enrichment only | none |
| **Tavily / Serper** | Discovery and market news | Existing keys; treat discovered prices as unverified until a retailer API confirms them | existing keys |
| **PCPartPicker** | Human-facing comparison and compatibility links | No public API. Do not depend on its internal endpoints or scrape without permission. | none |

The existing eBay token in the root `.env` was tested successfully against
Sandbox and rejected by Production, as expected. It is useful for development
but should not be treated as permanent configuration. Store the matching
Sandbox or Production Client ID and Client Secret and mint short-lived tokens
at runtime.

For production eBay data, create or retrieve the **Production** App ID and Cert
ID under eBay Developer Account → Application Keys. A user-consent token is not
needed for Browse search; it is only needed later for APIs that access or
modify a user's own account data.

Do not use Amazon page scraping as a fallback. Amazon's program policies limit
automated extraction and use of product content. Until Creators API access is
approved, return an Amazon search/deep link without claiming a verified price.

## 2. Open datasets

| Dataset | Used for | Access |
|---|---|---|
| **Ott OpSpam v1.4** (1,600 gold-labeled deceptive/truthful reviews) | Sage benchmark (already the v0 baseline) | direct download ✓ (`benchmarks/download`) |
| **YelpChi / YelpNYC / YelpZip** (Rayana & Akoglu) | Sage metadata-aware benchmark | free for research, request form |
| **UCSD/McAuley Amazon Reviews** | product-domain transfer for Sage | direct download, no key |
| **GPTARD / ARED** (AI-generated review sets) | modern LLM-fake benchmark | per-paper release pages |
| **Our own `price-history/*.jsonl`** | Speculator's trend calls; grows daily from the 08:00 job | generated in-sandbox, committed nightly if desired |

No dependable, freely licensed GPU price-history dataset was identified.
Supabase stores our own observations from day one in `price_observations`;
Keepa is a paid alternative for Amazon history.

## 3. Supabase setup

The local project lives in `supabase/`. API credentials stay in `.env` or a
deployment secret manager—never in database rows.

```bash
supabase start
supabase db reset
supabase status
```

For a hosted project:

```bash
supabase login
supabase link --project-ref "$SUPABASE_PROJECT_REF"
supabase db push
```

The initial migration creates sources, canonical products, external
identifiers, current listings, price observations, user watchlists, and sync
runs. Row-level security permits authenticated catalog reads and restricts
watchlists to their owner; ingestion writes use the server-only service role.

## 4. Who talks to whom (enforced, not aspirational)

Delegation allowlists live in `config/agents.yaml`; Discord exposure is
decided by `scripts/wire-discord-bots.sh` bindings; egress is policed by the
OpenShell sandbox policy.

```mermaid
flowchart LR
    subgraph Discord
      U([User])
    end
    subgraph Sandbox
      B[main / Brain]
      S[scout]
      I[inspector]
      C[concierge]
      subgraph Internal only
        A[amazon]
        E[ebay]
        T[tech]
        P[speculator]
        G[sage]
      end
    end
    U <--> B & S & I & C
    B --> S & I & C & A & E & T & P & G
    S --> P
    I --> G
    A --> G
    E --> G
```

- **Discord-facing:** main, scout, inspector, concierge (own bot identities).
- **Internal only:** amazon, ebay, tech, speculator, sage — no Discord
  account, no binding; reachable solely by agent-to-agent delegation.
- **sage** is terminal: judges payloads it is handed; no network tools.

## 5. Secrets handling & isolation roadmap

**Now (single sandbox):** retail API keys enter as env vars; tool allowlists
limit which agents *use* them, and the identity layer forbids echoing
credentials into Discord. Honest limit: env and egress are sandbox-global, so
a compromised Discord-facing agent shares the blast radius.

**Next (per-trust-zone sandboxes):** split into `openclaw` (Discord-facing
team) and `retail` (amazon/ebay/tech + their keys), each with its own
OpenShell egress policy (retail: only `*.ebay.com`, `api.bestbuy.com`,
`*.amazon.com`; no Discord egress at all), talking over the gateway's
agent-to-agent channel. The deploy scaffold (`deploy/docker-compose/`) grows a
second sandbox service; on Kubernetes this becomes the Helm chart with one
sandbox per pod and NetworkPolicies mirroring the egress rules — the
retail-assistant example's `helm/` tree is the template.

## 6. The MVP loop (daily 08:00 digest)

1. User in `#gpu-desk`: `@Brain watch RTX 5090 daily` → `subscriptions.json`.
2. OpenClaw cron job (`gpu-daily-watch`, `0 8 * * *`) runs a main-agent turn:
   fan out to scout/amazon/ebay/tech → best price + links; append
   `price-history/rtx-5090.jsonl`; speculator reads history → trend.
3. One message to `#daily` (fallback `#gpu-desk`): best price, where, link,
   trend ↑/↓/→ with a one-line reason, subscriber tags.
4. Reactions on the digest feed Sage's reward loop (`benchmarks/` measures it).
