"""Install the real release through Marketplace, then configure synthetic solar data."""

import asyncio
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit
import json

from homeassistant.bootstrap import async_setup_hass
from homeassistant.runner import RuntimeConfig

DOMAIN = "solaredge_v2_test"
REPOSITORY = "Cindyst1/solaredge-v2"
VERSION = "v0.6.8"


async def phase(directory, mode):
    hass = await async_setup_hass(RuntimeConfig(config_dir=directory, skip_pip=True))
    assert hass is not None
    connection = None
    try:
        await hass.async_start()
        user = await hass.auth.async_create_user("Fresh install synthetic admin", group_ids=["system-admin"])
        refresh = await hass.auth.async_create_refresh_token(user, client_id="http://localhost/")
        from migrate_statistics import Connection
        connection = await asyncio.to_thread(Connection, "http://127.0.0.1:18123",
                                              hass.auth.async_create_access_token(refresh))

        async def call(command, **kwargs):
            return await asyncio.to_thread(connection.call, command, **kwargs)

        if mode == "install":
            for attempt in range(120):
                entries = hass.config_entries.async_entries("marketplace")
                if entries and entries[0].state.value == "loaded":
                    break
                await asyncio.sleep(1)
            else:
                raise AssertionError("Marketplace did not start")
            entry = entries[0]
            hass.config_entries.async_update_entry(entry, data={**entry.data, "token": os.environ["CI_GITHUB_TOKEN"]})
            assert await hass.config_entries.async_reload(entry.entry_id)
            await call("marketplace/warning/accept")
            await call("marketplace/repositories/add", repository=REPOSITORY, category="integration")
            repositories = await call("marketplace/repositories/list")
            repository = next(repo for repo in repositories if repo["full_name"].lower() == REPOSITORY.lower())
            await call("marketplace/repository/install", repository=repository["id"], version=VERSION,
                       confirm_replace_built_in=False)
            manifest = json.loads(Path(directory, "custom_components", DOMAIN, "manifest.json").read_text())
            assert manifest["version"] == VERSION.removeprefix("v")
            info = await call("marketplace/repository/info", repository_id=repository["id"])
            assert "Deze stap is optioneel" in info["additional_info"]
            assert "Sla deze stap over" in info["additional_info"]
            assert not Path(directory, "tools", "migrate_statistics.py").exists()
            assert not hass.config_entries.async_entries(DOMAIN)
            print("PASS: real Marketplace download, optional migration instructions, no existing solar entry")
            return

        assert not hass.config_entries.async_entries(DOMAIN)
        energy = AsyncMock(return_value=100.0)
        tokens = AsyncMock(return_value={"access_token": "synthetic", "refresh_token": "synthetic",
                                        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()})
        # Only external SolarEdge API calls are mocked. HA config flow and sensor setup are real.
        with ExitStack() as stack:
            for name in ("config_flow", "__init__"):
                module = f"custom_components.{DOMAIN}" if name == "__init__" else f"custom_components.{DOMAIN}.{name}"
                stack.enter_context(patch(f"{module}.get_energy", energy))
                stack.enter_context(patch(f"{module}.get_tokens", tokens))
            for name, value in (("get_current_power", None), ("get_daily_balance", {}), ("get_site_status", None)):
                stack.enter_context(patch(f"custom_components.{DOMAIN}.{name}", AsyncMock(return_value=value)))
            flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
            assert flow["step_id"] == "user"
            assert not any("migrat" in str(key).lower() for key in flow["data_schema"].schema)
            callback = await hass.config_entries.flow.async_configure(flow["flow_id"], {
                "client_id": "00000000-0000-4000-8000-000000000001", "client_secret": "synthetic",
                "production_start": "2025-01-01", "device_inventory": False})
            assert callback["step_id"] == "callback"
            authorize = callback["description_placeholders"]["authorize_url"]
            external_id = parse_qs(urlsplit(authorize).query)["external_id"][0]
            result = await hass.config_entries.flow.async_configure(flow["flow_id"], {
                "callback": f"http://localhost:8080/oauth/callback?code=synthetic&site_id=900000001&external_id={external_id}"})
            assert result["type"] == "create_entry", result
            await hass.async_block_till_done()
            entries = hass.config_entries.async_entries(DOMAIN)
            assert len(entries) == 1
            for attempt in range(60):
                states = [state for state in hass.states.async_all("sensor")
                          if state.entity_id.endswith("lifetime_energy")]
                if states:
                    break
                await asyncio.sleep(1)
            assert len(states) == 1
            sensor = states[0]
            assert sensor.state == "100.0", sensor
            assert sensor.attributes["device_class"] == "energy"
            assert sensor.attributes["state_class"] == "total_increasing"
            assert sensor.attributes["unit_of_measurement"] == "kWh"
            await call("energy/save_prefs", energy_sources=[{"type": "solar", "stat_energy_from": sensor.entity_id,
                       "config_entry_solar_forecast": []}], device_consumption=[])
            prefs = await call("energy/get_prefs")
            assert prefs["energy_sources"][0]["stat_energy_from"] == sensor.entity_id
            energy.return_value = 102.0
            await entries[0].runtime_data.async_refresh()
            await hass.async_block_till_done()
            assert float(hass.states.get(sensor.entity_id).state) == 102.0
            assert not list(Path(directory).glob("*-private.json"))
            print("PASS: first config flow, no migration step, Lifetime Energy 100 -> 102 kWh, Energy dashboard source")
    finally:
        if connection:
            await asyncio.to_thread(connection.socket.close)
        await hass.async_stop()


if len(sys.argv) == 3:
    asyncio.run(phase(sys.argv[1], sys.argv[2]))
else:
    with tempfile.TemporaryDirectory() as directory:
        Path(directory, "configuration.yaml").write_text(
            "http:\n  server_host: 127.0.0.1\n  server_port: 18123\nrecorder:\nwebsocket_api:\nconfig:\nenergy:\n",
            encoding="utf-8")
        # Separate processes exercise the normal restart between download and first setup.
        for mode in ("install", "configure"):
            subprocess.run([sys.executable, __file__, directory, mode], check=True)
