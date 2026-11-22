"""Preview and import a legacy kWh statistics prefix into a V2 statistics series."""

import argparse
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit, urlunsplit

HOUR_MS = 3_600_000


def make_plan(source, target, start_ms, cutover_ms):
    """Keep the target sums fixed and align the imported prefix to its first row."""
    source = sorted(source, key=lambda row: row["start"])
    target = sorted(target, key=lambda row: row["start"])
    prefix = [row for row in source if start_ms <= row["start"] < cutover_ms]
    baseline = next((row for row in source if row["start"] == start_ms - HOUR_MS), None)
    first = next((row for row in target if row["start"] == cutover_ms), None)
    if not baseline or not first or not prefix:
        raise ValueError("Need a source baseline one hour before start and a target row at cutover.")
    if any(row["start"] < cutover_ms for row in target):
        raise ValueError("The target already contains earlier statistics. This tool will not overwrite them.")
    rows = [baseline, *prefix]
    expected = list(range(start_ms - HOUR_MS, cutover_ms, HOUR_MS))
    if [row["start"] for row in rows] != expected:
        raise ValueError("Legacy statistics have missing or duplicate hours. Resolve gaps first.")
    for row in [*rows, first]:
        for key in ("sum", "state"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not (-1e15 < value < 1e15):
                raise ValueError("Every boundary/source row needs finite sum and state values.")
    for previous, current in zip(rows, rows[1:]):
        if current["sum"] < previous["sum"] or current["state"] < previous["state"]:
            raise ValueError("Legacy counter reset or decreasing statistics require a custom migration.")
    bridge = first["state"] - rows[-1]["state"]
    if bridge < 0:
        raise ValueError("The target meter is lower than the legacy meter. Verify units and counters.")
    offset = first["sum"] - bridge - rows[-1]["sum"]
    imported = [
        {"start": datetime.fromtimestamp(row["start"] / 1000, timezone.utc).isoformat(),
         "state": row["state"], "sum": row["sum"] + offset}
        for row in rows
    ]
    return {"bridge_kwh": bridge, "offset": offset, "stats": imported,
            "legacy_production_kwh": rows[-1]["sum"] - rows[0]["sum"]}


class Connection:
    def __init__(self, url, token):
        try:
            import websocket
        except ImportError as error:
            raise RuntimeError("Install websocket-client: python -m pip install websocket-client") from error
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.query:
            raise ValueError("Use the Home Assistant base URL without credentials or query parameters.")
        endpoint = urlunsplit(("wss" if parts.scheme == "https" else "ws",
                               parts.netloc, parts.path.rstrip("/") + "/api/websocket", "", ""))
        self.socket = websocket.create_connection(endpoint, timeout=120)
        self.sequence = 0
        if json.loads(self.socket.recv()).get("type") != "auth_required":
            raise RuntimeError("Unexpected authentication response.")
        self.socket.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(self.socket.recv()).get("type") != "auth_ok":
            raise RuntimeError("Home Assistant authentication failed.")

    def call(self, command, **data):
        self.sequence += 1
        self.socket.send(json.dumps({"id": self.sequence, "type": command, **data}))
        while True:
            reply = json.loads(self.socket.recv())
            if reply.get("id") == self.sequence and reply.get("type") == "result":
                if not reply.get("success"):
                    raise RuntimeError(f"Home Assistant rejected {command}: {reply.get('error')}")
                return reply.get("result")

    def statistics(self, entities, start):
        return self.call("recorder/statistics_during_period", statistic_ids=entities,
                         start_time=start, period="hour", types=["sum", "state"])


def hour(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None or parsed.minute or parsed.second or parsed.microsecond:
        raise argparse.ArgumentTypeError("Use an exact hour with UTC offset, e.g. 2026-01-01T00:00:00+01:00")
    return parsed.astimezone(timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Home Assistant base URL")
    parser.add_argument("--source", required=True, help="Legacy statistic ID")
    parser.add_argument("--target", required=True, help="V2 Lifetime Energy statistic ID")
    parser.add_argument("--start", required=True, type=hour, help="First hour to migrate, including its production")
    parser.add_argument("--cutover", required=True, type=hour, help="First existing V2 statistics hour")
    parser.add_argument("--output", required=True, type=Path, help="New local audit/backup JSON file")
    parser.add_argument("--apply", action="store_true", help="Import after preview and confirmation")
    parser.add_argument("--confirmed-bridge-kwh", type=float,
                        help="Independently verified production in the first V2 hour")
    args = parser.parse_args()
    if args.source == args.target or args.start >= args.cutover:
        parser.error("Source and target must differ, and start must precede cutover.")
    # Create a new audit file before any network write. Never overwrite a previous backup.
    with args.output.open("x", encoding="utf-8") as audit:
        token = os.environ.get("HA_TOKEN") or getpass.getpass("Home Assistant access token: ")
        connection = Connection(args.url, token)
        try:
            # Read all existing target history so an earlier target baseline cannot be missed.
            start = "1970-01-01T00:00:00+00:00"
            entities = [args.source, args.target]
            metadata = connection.call("recorder/get_statistics_metadata", statistic_ids=entities)
            by_id = {item["statistic_id"]: item for item in metadata}
            for entity in entities:
                item = by_id.get(entity, {})
                if item.get("unit_of_measurement") != "kWh" or not item.get("has_sum"):
                    raise ValueError("Both statistics must exist, use kWh and have a cumulative sum.")
            original = connection.statistics(entities, start)
            target = original.get(args.target, [])
            plan = make_plan(original.get(args.source, []), target,
                             int(args.start.timestamp() * 1000), int(args.cutover.timestamp() * 1000))
            record = {"source": args.source, "target": args.target, "metadata": metadata,
                      "original": original, "plan": plan, "status": "preview"}
            json.dump(record, audit, indent=2)
            audit.flush()
            print(f"Prefix rows (including baseline): {len(plan['stats'])}")
            print(f"Legacy production: {plan['legacy_production_kwh']:.6f} kWh")
            print(f"First V2 hour bridge: {plan['bridge_kwh']:.6f} kWh")
            print(f"Private local audit file: {args.output}")
            if not args.apply:
                print("Preview complete. No statistics imported.")
                return
            bridge = args.confirmed_bridge_kwh
            if bridge is None or abs(bridge - plan["bridge_kwh"]) > 0.000001:
                raise ValueError("Supply the independently checked first V2 hour production with --confirmed-bridge-kwh.")
            if input("Type IMPORT to insert only the missing historical prefix: ") != "IMPORT":
                raise ValueError("Import cancelled.")
            # Re-read before writing to catch another import or a changed historical prefix.
            current = connection.statistics(entities, start)
            for entity in entities:
                cutoff = int(args.cutover.timestamp() * 1000) + HOUR_MS
                old_boundary = [row for row in original[entity] if row["start"] < cutoff]
                new_boundary = [row for row in current[entity] if row["start"] < cutoff]
                if old_boundary != new_boundary:
                    raise ValueError("Historical statistics changed during preview. Stop and review a fresh preview.")
            item = by_id[args.target]
            import_metadata = {"statistic_id": args.target, "source": item["source"],
                               "name": item.get("name"), "unit_of_measurement": "kWh",
                               "unit_class": item.get("unit_class"), "mean_type": 0, "has_sum": True}
            connection.call("recorder/import_statistics", metadata=import_metadata, stats=plan["stats"])
            expected = {int(datetime.fromisoformat(row["start"]).timestamp() * 1000): row
                        for row in plan["stats"]}
            # Import acknowledges a queued job. Wait for its rows before checking values.
            for attempt in range(30):
                verified = connection.statistics(entities, start)
                imported = {row["start"]: row for row in verified[args.target] if row["start"] in expected}
                if len(imported) == len(expected):
                    break
                time.sleep(2)
            if len(imported) != len(expected):
                raise RuntimeError("Import verification incomplete. Inspect the audit before retrying.")
            for stamp, row in expected.items():
                actual = imported[stamp]
                if any(abs(actual[key] - row[key]) > 0.000001 for key in ("sum", "state")):
                    raise RuntimeError("Imported values differ. Inspect the audit before retrying.")
            for entity in entities:
                after = {row["start"]: row for row in verified[entity]}
                for row in original[entity]:
                    if after.get(row["start"]) != row:
                        raise RuntimeError("An original row changed. Inspect the audit; do not repeat the import.")
            print("Import verified. Original source and existing target statistics match the audit.")
        finally:
            connection.socket.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        sys.exit(1)
