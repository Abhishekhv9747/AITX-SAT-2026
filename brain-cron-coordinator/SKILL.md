---
name: brain-cron-coordinator
description: Brain-only confirmation workflow for scheduling Hermes jobs from Discord.
---

# Cron requests from Discord

When a user says `cron create` (or otherwise asks to schedule a recurring
task), Brain coordinates the request but never runs `cron`, `hermes cron`, or
any scheduler command itself.

1. Extract a supported schedule, a short lowercase-hyphenated job name, and a
   self-contained task prompt. Interpret all clock times as **CDT** (UTC-5).
   The broker converts them to the UTC-only Hermes scheduler; do not ask the
   user to calculate UTC.
   Supported schedules are:
   `every 15 minutes`, `every 2 hours`, `daily at 9am`, `weekdays at 17:30`,
   `weekly on monday at 9am`, and `monthly on day 1 at 08:00`.
2. Use timezone `CDT`. Ask the broker to parse the schedule and show the user
   the CDT schedule, its UTC execution expression, and the
   intended `#daily` Sage delivery:

```bash
curl -sS -X POST http://host.openshell.internal:8001/cron-parse -H 'Content-Type: application/json' -d '{"schedule":"<schedule>"}'
```
3. Ask the same Discord user for an explicit confirmation such as `confirm
   cron`. Do not submit, modify, or create anything until that confirmation is
   present in the same conversation.
4. Only after confirmation, submit the request to Hermes. Use the requester’s
   Discord identity as the final argument:

```bash
python3 /sandbox/.openclaw/workspace/skills/brain-cron-coordinator/queue_cron.py "<schedule>" "CDT" "<job-name>" "<task prompt>" "<requester-id>"
```

5. Tell the user that Hermes has been asked to create the job and that Sage
   will publish each completed job result in `#daily`. Do not claim that the
   job is active until Hermes reports it created.

Never include secrets, tokens, connection strings, or private Discord content
in the job name or prompt. A rejection or missing confirmation means no job.
