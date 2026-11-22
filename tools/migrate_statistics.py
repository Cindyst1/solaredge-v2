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


def choose_hours(source, target, start=None, cutover=None):
    """Propose the first target hour and the full available legacy prefix."""
    if not source or not target:
        raise ValueError("Both sensors need existing hourly statistics before a transition can be proposed.")
    first_source = min(row["start"] for row in source)
    first_target = min(row["start"] for row in target)
    start_ms = int(start.timestamp() * 1000) if start else first_source + HOUR_MS
    cutover_ms = int(cutover.timestamp() * 1000) if cutover else first_target
    if start_ms >= cutover_ms:
        raise ValueError("No earlier legacy prefix is available. The target may already contain migrated history.")
    if cutover_ms != first_target:
        raise ValueError("Cutover must be the first existing V2 statistics hour.")
    return start_ms, cutover_ms


def make_plan(source, target, start_ms, cutover_ms):
    """Start the imported baseline at zero and carry its production into V2 sums."""
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
    offset = -rows[0]["sum"]
    target_adjustment = rows[-1]["sum"] + offset + bridge - first["sum"]
    overlap = next((row for row in source if row["start"] == cutover_ms), None)
    bridge_verified = bool(
        overlap and isinstance(overlap.get("state"), (int, float))
        and isinstance(overlap.get("sum"), (int, float))
        and abs(overlap["state"] - first["state"]) < 0.000001
        and abs(overlap["sum"] - rows[-1]["sum"] - bridge) < 0.000001
    )
    imported = [
        {"start": datetime.fromtimestamp(row["start"] / 1000, timezone.utc).isoformat(),
         "state": row["state"], "sum": row["sum"] + offset}
        for row in rows
    ]
    return {"bridge_kwh": bridge, "bridge_verified": bridge_verified,
            "offset": offset, "target_sum_adjustment": target_adjustment, "stats": imported,
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
                         start_time=start, period="hour", types=["sum", "state"], units={"energy": "kWh"})


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
    parser.add_argument("--start", type=hour, help="Override the proposed first legacy hour to migrate")
    parser.add_argument("--cutover", type=hour, help="Explicit first V2 statistics hour (normally detected)")
    parser.add_argument("--output", required=True, type=Path, help="New local audit/backup JSON file")
    parser.add_argument("--apply", action="store_true", help="Import after preview and confirmation")
    parser.add_argument("--confirmed-bridge-kwh", type=float,
                        help="Independently verified production in the first V2 hour")
    args = parser.parse_args()
    if args.source == args.target:
        parser.error("Source and target must differ.")
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
                if item.get("statistics_unit_of_measurement") != "kWh" or not item.get("has_sum"):
                    raise ValueError("Both statistics must exist, use kWh and have a cumulative sum.")
            original = connection.statistics(entities, start)
            target = original.get(args.target, [])
            try:
                start_ms, cutover_ms = choose_hours(original.get(args.source, []), target, args.start, args.cutover)
                cutover = datetime.fromtimestamp(cutover_ms / 1000, timezone.utc)
                print(f"Proposed import start (UTC): {datetime.fromtimestamp(start_ms / 1000, timezone.utc).isoformat()}")
                print(f"Proposed first V2 hour / cutover (UTC): {cutover.isoformat()}")
                plan = make_plan(original.get(args.source, []), target, start_ms, cutover_ms)
            except ValueError as error:
                json.dump({"source": args.source, "target": args.target, "original": original,
                           "status": "needs_review", "reason": str(error)}, audit, indent=2)
                raise
            record = {"source": args.source, "target": args.target, "metadata": metadata,
                      "original": original, "plan": plan, "status": "preview"}
            json.dump(record, audit, indent=2)
            audit.flush()
            print(f"Prefix rows (including baseline): {len(plan['stats'])}")
            print(f"Legacy production: {plan['legacy_production_kwh']:.6f} kWh")
            print(f"First V2 hour bridge: {plan['bridge_kwh']:.6f} kWh")
            print(f"Bridge verified against matching legacy hour: {plan['bridge_verified']}")
            print(f"V2 statistics sum offset (meter readings stay fixed): {plan['target_sum_adjustment']:.6f} kWh")
            print(f"Private local audit file: {args.output}")
            if not args.apply:
                print("Preview complete. No statistics imported.")
                return
            bridge = args.confirmed_bridge_kwh
            if bridge is not None and (not (-1e15 < bridge < 1e15) or abs(bridge - plan["bridge_kwh"]) > 0.000001):
                raise ValueError("Confirmed bridge differs from the proposal.")
            if bridge is None and not plan["bridge_verified"]:
                raise ValueError("Supply the independently checked first V2 hour production with --confirmed-bridge-kwh.")
            if input("Type IMPORT to insert only the missing historical prefix: ") != "IMPORT":
                raise ValueError("Import cancelled.")
            # Re-read before writing to catch another import or a changed historical prefix.
            current = connection.statistics(entities, start)
            for entity in entities:
                cutoff = cutover_ms + HOUR_MS
                old_boundary = [row for row in original[entity] if row["start"] < cutoff]
                new_boundary = [row for row in current[entity] if row["start"] < cutoff]
                if old_boundary != new_boundary:
                    raise ValueError("Historical statistics changed during preview. Stop and review a fresh preview.")
            item = by_id[args.target]
            adjustment = plan["target_sum_adjustment"]
            if abs(adjustment) > 0.000001:
                connection.call("recorder/adjust_sum_statistics", statistic_id=args.target,
                                start_time=cutover.isoformat(), adjustment=adjustment,
                                adjustment_unit_of_measurement="kWh")
                for attempt in range(30):
                    shifted = connection.statistics([args.target], cutover.isoformat())[args.target]
                    if abs(shifted[0]["sum"] - target[0]["sum"] - adjustment) < 0.000001:
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError("Target sum adjustment pending. Inspect audit before retrying.")
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
                    expected_row = dict(row)
                    if entity == args.target:
                        expected_row["sum"] += adjustment
                    actual = after.get(row["start"])
                    if actual is None or actual["state"] != expected_row["state"] or abs(actual["sum"] - expected_row["sum"]) > 0.000001:
                        raise RuntimeError("An original row changed. Inspect the audit; do not repeat the import.")
            print("Import verified. Source rows and target readings preserved; target sums include the planned offset.")
        finally:
            connection.socket.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        sys.exit(1)
