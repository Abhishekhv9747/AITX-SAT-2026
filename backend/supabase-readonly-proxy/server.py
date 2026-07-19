import json
import os
import re
import threading
import http.client
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import discord
import psycopg

MAX_ROWS = 100
FORBIDDEN = re.compile(r"\b(insert|update|delete|merge|create|alter|drop|truncate|grant|revoke|copy|call|do|execute|set|reset|begin|commit|rollback|vacuum|analyze|watchlists)\b", re.I)
JOB_NAME = re.compile(r"[a-z0-9][a-z0-9-]{2,63}\Z")
REQUEST_LOCK = threading.Lock()
REQUESTS_PATH = Path(os.environ.get("CRON_BROKER_STATE_PATH", "/data/cron_requests.json"))
CDT_UTC_OFFSET_HOURS = 5
PUBLISH_TARGETS = {
    "/publish": ("DISCORD_DAILY_CHANNEL_ID", "DISCORD_SAGE_BOT_TOKEN", "[Sage daily update]"),
}


def parse_time(value):
    match = re.fullmatch(r"(0?[1-9]|1[0-2])(?::([0-5][0-9]))?\s*(am|pm)", value)
    if match:
        hour = int(match.group(1)) % 12
        if match.group(3) == "pm":
            hour += 12
        return hour, int(match.group(2) or 0)
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", value)
    if match:
        return int(match.group(1)), int(match.group(2))
    raise ValueError("time must look like '9am', '9:30 pm', or '21:30'")


def cdt_to_utc(hour, minute):
    """Convert a CDT wall-clock time to the UTC-only Hermes scheduler."""
    total_minutes = hour * 60 + minute + CDT_UTC_OFFSET_HOURS * 60
    return (total_minutes // 60) % 24, total_minutes % 60, total_minutes // (24 * 60)


def format_time(hour, minute):
    return f"{hour:02d}:{minute:02d}"


def parse_schedule(text):
    value = " ".join(str(text).strip().lower().split())
    days = {"monday": "1", "tuesday": "2", "wednesday": "3", "thursday": "4", "friday": "5", "saturday": "6", "sunday": "0"}
    if match := re.fullmatch(r"every (\d{1,3}) minutes?", value):
        minutes = int(match.group(1))
        if 1 <= minutes <= 59:
            return {"cron": f"*/{minutes} * * * *", "description": f"every {minutes} minutes"}
    elif match := re.fullmatch(r"every (\d{1,2}) hours?", value):
        hours = int(match.group(1))
        if 1 <= hours <= 23:
            return {"cron": f"0 */{hours} * * *", "description": f"every {hours} hours"}
    elif match := re.fullmatch(r"daily at (.+)", value):
        hour, minute = parse_time(match.group(1))
        utc_hour, utc_minute, _ = cdt_to_utc(hour, minute)
        return {
            "cron": f"{utc_minute} {utc_hour} * * *",
            "description": f"daily at {format_time(hour, minute)} CDT ({format_time(utc_hour, utc_minute)} UTC)",
        }
    elif match := re.fullmatch(r"weekdays at (.+)", value):
        hour, minute = parse_time(match.group(1))
        utc_hour, utc_minute, day_offset = cdt_to_utc(hour, minute)
        utc_days = "1-5" if day_offset == 0 else "2-6"
        return {
            "cron": f"{utc_minute} {utc_hour} * * {utc_days}",
            "description": f"weekdays at {format_time(hour, minute)} CDT ({format_time(utc_hour, utc_minute)} UTC)",
        }
    elif match := re.fullmatch(r"weekly on (" + "|".join(days) + r") at (.+)", value):
        day, raw_time = match.groups()
        hour, minute = parse_time(raw_time)
        utc_hour, utc_minute, day_offset = cdt_to_utc(hour, minute)
        utc_day = (int(days[day]) + day_offset) % 7
        return {
            "cron": f"{utc_minute} {utc_hour} * * {utc_day}",
            "description": f"every {day} at {format_time(hour, minute)} CDT ({format_time(utc_hour, utc_minute)} UTC)",
        }
    elif match := re.fullmatch(r"monthly on day (\d{1,2}) at (.+)", value):
        day, raw_time = match.groups()
        if 1 <= int(day) <= 31:
            hour, minute = parse_time(raw_time)
            utc_hour, utc_minute, day_offset = cdt_to_utc(hour, minute)
            if day_offset:
                raise ValueError("monthly schedules after 6:59pm CDT cannot be converted safely; choose an earlier CDT time")
            return {
                "cron": f"{utc_minute} {utc_hour} {int(day)} * *",
                "description": f"monthly on day {day} at {format_time(hour, minute)} CDT ({format_time(utc_hour, utc_minute)} UTC)",
            }
    raise ValueError("supported schedules: every 15 minutes; every 2 hours; daily at 9am; weekdays at 17:30; weekly on monday at 9am; monthly on day 1 at 08:00 (all clock times are CDT)")


def load_requests():
    if not REQUESTS_PATH.exists():
        return []
    return json.loads(REQUESTS_PATH.read_text())


def save_requests(requests):
    REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = REQUESTS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(requests, indent=2))
    temporary.replace(REQUESTS_PATH)


def validate_request(payload):
    if payload.get("confirmed") is not True:
        raise ValueError("Brain may submit a request only after explicit user confirmation.")
    name = str(payload.get("name", "")).strip().lower()
    prompt = str(payload.get("prompt", "")).strip()
    timezone = str(payload.get("timezone", "")).strip().upper()
    if not JOB_NAME.fullmatch(name):
        raise ValueError("job name must be 3-64 lowercase letters, digits, or hyphens")
    if not 8 <= len(prompt) <= 1500:
        raise ValueError("task prompt must be between 8 and 1500 characters")
    if timezone != "CDT":
        raise ValueError("use timezone CDT; the broker converts CDT (UTC-5) to the UTC-only Hermes scheduler")
    return name, prompt, timezone, parse_schedule(payload.get("schedule", ""))


def read_query(sql):
    statement = sql.strip().rstrip(";").strip()
    if not statement.lower().startswith(("select ", "with ")) or ";" in statement or FORBIDDEN.search(statement):
        raise ValueError("Only SELECT queries to shared marketplace tables are allowed.")
    with psycopg.connect(os.environ["SUPABASE_AGENT_READONLY_CONNECTION_STRING"]) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION READ ONLY")
            cursor.execute("SET LOCAL statement_timeout = '10s'")
            cursor.execute(statement)
            columns = [column.name for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchmany(MAX_ROWS)]


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, response):
        body = json.dumps(response, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/cron-requests/next":
            with REQUEST_LOCK:
                requests = load_requests()
                request = next((item for item in requests if item["status"] == "pending"), None)
                if request is None:
                    self.reply(204, {})
                    return
                request["status"] = "claimed"
                request["claim_token"] = uuid4().hex
                save_requests(requests)
            self.reply(200, request)
            return
        self.send_error(404)

    def do_POST(self):
        if self.path not in {"/query", "/cron-parse", "/cron-requests", *PUBLISH_TARGETS} and not re.fullmatch(r"/cron-requests/[0-9a-f]+/complete", self.path):
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(size))
            if self.path == "/query":
                result = read_query(payload["sql"])
                response = {"rows": result}
            elif self.path == "/cron-parse":
                response = parse_schedule(payload.get("schedule", ""))
            elif self.path == "/cron-requests":
                name, prompt, timezone, schedule = validate_request(payload)
                request = {
                    "id": uuid4().hex,
                    "status": "pending",
                    "name": name,
                    "prompt": prompt,
                    "timezone": timezone,
                    "schedule": schedule,
                    "requested_by": str(payload.get("requested_by", "discord-user"))[:120],
                }
                with REQUEST_LOCK:
                    requests = load_requests()
                    if any(item["name"] == name and item["status"] in {"pending", "claimed", "created"} for item in requests):
                        raise ValueError("an active cron request already uses this job name")
                    requests.append(request)
                    save_requests(requests)
                response = {"queued": True, "id": request["id"], **schedule}
            elif self.path.endswith("/complete"):
                request_id = self.path.split("/")[2]
                with REQUEST_LOCK:
                    requests = load_requests()
                    request = next((item for item in requests if item["id"] == request_id), None)
                    if request is None or request["status"] != "claimed" or payload.get("claim_token") != request.get("claim_token"):
                        raise ValueError("invalid or expired cron request claim")
                    request["status"] = "created" if payload.get("success") else "failed"
                    request["result"] = str(payload.get("result", ""))[:1000]
                    request.pop("claim_token", None)
                    save_requests(requests)
                response = {"updated": True}
            elif self.path in PUBLISH_TARGETS:
                content = str(payload.get("content", "")).strip()
                if not content:
                    raise ValueError("A cron-output message is required.")
                content = content[:1900]
                channel_key, token_key, prefix = PUBLISH_TARGETS[self.path]
                channel_keys = (channel_key,) if isinstance(channel_key, str) else channel_key
                channel_id = next((os.environ.get(key) for key in channel_keys if os.environ.get(key)), None)
                bot_token = os.environ.get(token_key)
                if not channel_id or not bot_token:
                    raise ValueError(f"{self.path} is not configured; set one of {', '.join(channel_keys)} and {token_key}")
                discord_connection = http.client.HTTPSConnection("discord.com", timeout=15)
                discord_connection.request(
                    "POST",
                    f"/api/v10/channels/{channel_id}/messages",
                    body=json.dumps({"content": f"{prefix}\n{content}"}),
                    headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
                )
                discord_response = discord_connection.getresponse()
                if not 200 <= discord_response.status < 300:
                    raise RuntimeError(f"Discord rejected the post ({discord_response.status})")
                discord_response.read()
                discord_connection.close()
                response = {"published": True}
            self.reply(200, response)
        except Exception as error:
            self.reply(400, {"error": str(error)})

    def log_message(self, *_):
        pass


class SageClient(discord.Client):
    async def on_ready(self):
        print(f"Sage connected as {self.user}; guild_count={len(self.guilds)}", flush=True)
        channel_id = int(os.environ["DISCORD_DAILY_CHANNEL_ID"])
        for guild in self.guilds:
            member = guild.me
            channel = guild.get_channel(channel_id)
            if member is None:
                print(f"Sage diagnostics: guild={guild.id}; member cache unavailable", flush=True)
            elif channel is None:
                print(f"Sage diagnostics: guild={guild.id}; daily channel not visible to Sage", flush=True)
            else:
                permissions = channel.permissions_for(member)
                print(
                    f"Sage diagnostics: daily_view={permissions.view_channel}; "
                    f"daily_send={permissions.send_messages}; roles={[role.name for role in member.roles]}",
                    flush=True,
                )


def run_sage_gateway():
    SageClient(intents=discord.Intents.none()).run(
        os.environ["DISCORD_SAGE_BOT_TOKEN"], log_handler=None
    )


threading.Thread(target=run_sage_gateway, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", 8001), Handler).serve_forever()
