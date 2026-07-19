#!/usr/bin/env python3
"""Validate or enqueue a recorded Discord watch workflow from its JSON manifest."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    limit = manifest.get("replay_limit_seconds")
    steps = manifest.get("steps")
    if not isinstance(limit, int) or limit <= 0 or not isinstance(steps, list) or not steps:
        raise ValueError("manifest needs replay_limit_seconds and at least one step")
    deadlines = [step.get("deadline_second") for step in steps]
    if any(not isinstance(value, int) for value in deadlines) or max(deadlines) > limit:
        raise ValueError("one or more step deadlines exceed replay_limit_seconds")
    if manifest.get("trigger", {}).get("channel") != "#gpu-desk":
        raise ValueError("the recorded watch trigger must use #gpu-desk")
    return manifest


def queue_payload(manifest: dict) -> dict:
    command = manifest["trigger"]["command"]
    fields = {}
    for line in command.splitlines()[1:]:
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip().lower()] = value.strip()
    item = fields.get("item", "")
    if not item:
        raise ValueError("trigger.command must include an item")
    agents = ", ".join(agent["name"] for agent in manifest.get("agents", []))
    prompt = (
        f"Monitor {item}. Target: {fields.get('target price', 'unspecified')} with "
        f"{fields.get('tolerance', 'unspecified')} tolerance; maximum wait: "
        f"{fields.get('max wait', 'unspecified')}. Scout must use the database first "
        f"and a bounded trusted-web fallback; Inspector must review the evidence; "
        f"NemoHermes must publish up to five verified Online or In-store / pickup options "
        f"through Sage in #daily. Include direct trusted links or stock-check links, omit "
        f"internal IDs, and record feedback in reviews_feedback. Agents: {agents}."
    )
    return {
        "confirmed": True,
        "name": manifest["name"],
        "prompt": prompt,
        "timezone": "CDT",
        "schedule": fields.get("schedule", "every 1 minute"),
        "requested_by": "workflow-json-runner",
        "workflow": "daily-deals",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--queue", action="store_true", help="enqueue the confirmed cron request via the local broker")
    parser.add_argument("--broker", default="http://127.0.0.1:8001", help="broker base URL")
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest)
        payload = queue_payload(manifest)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Invalid workflow manifest: {error}", file=sys.stderr)
        return 2

    summary = {
        "validated": True,
        "name": manifest["name"],
        "replay_limit_seconds": manifest["replay_limit_seconds"],
        "final_deadline_seconds": max(step["deadline_second"] for step in manifest["steps"]),
        "command": manifest["trigger"]["command"],
    }
    if not args.queue:
        print(json.dumps(summary, indent=2))
        return 0

    request = Request(
        args.broker.rstrip("/") + "/cron-requests",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            summary["broker"] = json.loads(response.read())
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"Could not queue workflow: {error}", file=sys.stderr)
        return 3
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
