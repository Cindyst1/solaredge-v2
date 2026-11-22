"""Run the migration CLI against a disposable, real Home Assistant Recorder."""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile

from homeassistant.bootstrap import async_setup_hass
from homeassistant.runner import RuntimeConfig
from homeassistant.components.recorder import get_instance


async def main():
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "configuration.yaml").write_text(
            "http:\n  server_host: 127.0.0.1\n  server_port: 18123\n"
            "recorder:\nwebsocket_api:\nconfig:\n", encoding="utf-8")
        hass = await async_setup_hass(RuntimeConfig(config_dir=directory, skip_pip=True))
        assert hass is not None, "Home Assistant bootstrap failed"
        try:
            await hass.async_start()
            user = await hass.auth.async_create_user("Synthetic test admin", group_ids=["system-admin"])
            refresh = await hass.auth.async_create_refresh_token(user)
            token = hass.auth.async_create_access_token(refresh)
            # Import the CLI only after HA has started. All calls run in executor threads.
            from migrate_statistics import Connection
            connection = await asyncio.to_thread(Connection, "http://127.0.0.1:18123", token)

            async def call(command, **kwargs):
                return await asyncio.to_thread(connection.call, command, **kwargs)

            source = "sensor.synthetic_legacy_energy"
            target = "sensor.synthetic_v2_energy"
            base = datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp()

            def stats(values):
                return [{"start": datetime.fromtimestamp(base + hour * 3600, timezone.utc).isoformat(),
                         "state": state, "sum": total} for hour, state, total in values]

            async def seed(entity, values):
                await call("recorder/import_statistics", metadata={"statistic_id": entity,
                           "source": "recorder", "name": entity, "unit_of_measurement": "kWh",
                           "unit_class": "energy", "mean_type": 0, "has_sum": True}, stats=stats(values))
                await get_instance(hass).async_block_till_done()

            await seed(source, [(0, 100, 10), (1, 102, 12), (2, 105, 15)])
            await seed(target, [(3, 106, 0), (4, 108, 2)])

            async def snapshot():
                return await call("recorder/statistics_during_period", start_time="2025-01-01T00:00:00+00:00",
                                  statistic_ids=[source, target], period="hour", types=["state", "sum"])

            before = await snapshot()
            script = str(Path(__file__).with_name("migrate_statistics.py"))

            async def run(name, *extra):
                process = await asyncio.create_subprocess_exec(
                    sys.executable, script, "--url", "http://127.0.0.1:18123", "--source", source,
                    "--target", target, "--start", "2025-01-01T01:00:00+00:00",
                    "--cutover", "2025-01-01T03:00:00+00:00", "--output", f"{directory}/{name}.json",
                    *extra, env={**os.environ, "HA_TOKEN": token}, stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
                stdout, stderr = await process.communicate(b"IMPORT\n")
                print(stdout.decode(), stderr.decode())
                return process.returncode

            assert await run("preview") == 0
            assert await snapshot() == before, "Preview wrote statistics"
            assert await run("apply", "--apply", "--confirmed-bridge-kwh", "1") == 0
            after = await snapshot()
            assert after[source] == before[source], "Legacy rows changed"
            assert after[target][-2:] == before[target], "Existing V2 rows changed"
            assert [row["sum"] for row in after[target]] == [-6, -4, -1, 0, 2]
            assert [after[target][i]["sum"] - after[target][i-1]["sum"] for i in range(1, 5)] == [2, 3, 1, 2]
            assert after[target][-1]["sum"] - after[target][0]["sum"] == 8, "Double-counted production"
            assert await run("repeat", "--apply", "--confirmed-bridge-kwh", "1") != 0
            assert await snapshot() == after, "Repeated import changed statistics"
            await asyncio.to_thread(connection.socket.close)
            print("PASS: preview, real import, 8 kWh total, preserved readings, repeated-import guard")
        finally:
            await hass.async_stop()


asyncio.run(main())
