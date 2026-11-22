# SolarEdge V2

[Nederlands](README.md)

SolarEdge V2 is a community integration that replaces the legacy SolarEdge connection. It reads solar data through the SolarEdge Monitoring API V2. A fresh install creates a separate integration entry. Legacy history is not migrated automatically.

**Verified in Home Assistant: Lifetime Energy.** This cumulative kWh counter uses SITE_DATA and works as a solar production source in the Energy dashboard. Daily, monthly and yearly production and quarter-hour power depend on the available cloud data. See the sensor table for additional permissions and local sources.

## Transfer legacy history with the standalone migration tool

To bring production history from your legacy SolarEdge sensor into V2, use the [migration tool and English instructions](https://github.com/Cindyst1/solaredge-v2/blob/main/tools/README.md#english).

**This is a separate Python script that you run manually.** Installing or updating through Marketplace or HACS does not start a migration. The integration does not run the script automatically. Find it in the `tools` directory on GitHub.

The tool previews the changes and requires confirmation before importing. It supports a continuous prefix of legacy hourly kWh statistics and checks for overlap and a matching bridge hour. It has been tested against a separate Home Assistant installation with synthetic data. Create a full backup, read the prerequisites, and verify production totals afterwards. It migrates long-term Energy dashboard statistics, not raw History readings.

## 1. Installation

### Home Assistant 2026.11 and later: Marketplace

1. As an administrator, open **Settings → Marketplace** and accept the first-use warning to enable installations.
2. Search for **SolarEdge V2**. If it does not appear, select **Add from link** and enter `https://github.com/Cindyst1/solaredge-v2`. Connect GitHub if prompted. If asked for a type, choose **Integration**.
3. Open **SolarEdge V2**, select **Install**, and restart Home Assistant when prompted.

See the [Marketplace guide](https://www.home-assistant.io/integrations/marketplace/#custom-repositories).

### Home Assistant 2026.10 and earlier: HACS

1. Open **HACS → ⋮ → Custom repositories**. Add `https://github.com/Cindyst1/solaredge-v2` as an **Integration**.
2. Open **SolarEdge V2**, select **Download**, and restart Home Assistant.

See the [HACS guide](https://www.hacs.xyz/docs/faq/custom_repositories/).

After a first installation, go to **Settings → Devices & services → Add integration** and search for **SolarEdge V2**. Updates use the existing integration entry.

## 2. Connect your SolarEdge site

1. In the [SolarEdge Developer Platform](https://developer.solaredge.com/), create a **Monitoring API** app with **Site Access** and the **SITE_DATA** scope.
2. Register `http://localhost:8080/oauth/callback` as an allowed redirect URL. Save your **Client ID** and **Client Secret**.
3. In Home Assistant, enter your Client ID, Client Secret, and the date your system first generated power (`YYYY-MM-DD`).
4. Open the sign-in link shown by Home Assistant on the same device. Select your SolarEdge site and approve access.
5. Copy the full `localhost` URL from the browser address bar into the masked field in Home Assistant. The browser may show a connection error. The URL contains the temporary authorization code Home Assistant needs.

The integration requests access for one month and refreshes the access token during that period. Sign in again when Home Assistant prompts you. Keep your Client Secret and the full callback URL private.

## Which sensors report values?

| Sensors | Source and requirements |
| --- | --- |
| **Lifetime Energy** | Cumulative solar production in kWh via **SITE_DATA**. Use this sensor for solar production in the Energy dashboard. |
| **Energy Today**, **Produced Energy Today**, **Energy This Month**, **Energy This Year** | Production for the relevant period via **SITE_DATA**. Both daily sensors report the same production. |
| **Current Power**, **Solar Power Flow** | Solar power in W. The cloud provides a 15-minute reading up to two hours old. You can also select an existing local power sensor. |
| **Last Reported Site Power** | Latest available cloud reading for site power within an eleven-hour lookup window. The reading's timestamp is available in `sample_at`. |
| **Site Status**, **Imported Energy Today**, **Exported Energy Today**, **Consumed Energy Today**, **Self Consumed Energy Today** | Optional cloud data. These sensors report values when SolarEdge makes the data available for your site and permissions. |
| **Grid Power Flow**, **Grid Flow Direction** | From a selected local grid power sensor such as a P1 meter, or from the cloud if Advanced Monitoring provides power flows. |
| **Home Consumption Power Flow**, **Battery Power Flow**, **Battery Flow Direction** | Require power flows from Advanced Monitoring. SolarEdge can deny access to this data separately. |
| **Meters**, **Inverters**, and registration status per device | Enable device discovery and authorize **DEVICE_DATA**. The inventory depends on what SolarEdge returns for your site. |
| **Power (15-minute average)** per inverter | Requires an inverter that SolarEdge reports as active and access to its power data. Inventory access alone may be insufficient. |
| **Sensors**, **Gateways**, **Batteries**, **Storage Level** | These entities have no data source. |

Optional sensors can show **Unknown** when the source is missing or SolarEdge denies access. The integration requests **Lifetime Energy** and site power every 15 minutes, including with device discovery enabled. It updates the other daily totals and inventory less often. The cloud reading timestamp may differ from the time Home Assistant updates the sensor.

### Enable device discovery or add a local source

- **Inverters and meters.** Allow **DEVICE_DATA** in your SolarEdge app. Open **⋮ → Reconfigure** for the integration, enable inverter and meter discovery, and authorize the same site again.
- **Grid power.** Open **Configure** and select an existing sensor, such as your P1 meter, under **Local grid power**. Positive values mean import and negative values mean export. This supplies grid power and direction. Daily energy totals come from SolarEdge.
- **Solar power.** Under **Local solar power**, you can select an existing Home Assistant sensor in W or kW. The integration reads that entity. For a cloud-only setup, leave both local fields blank.

## Energy dashboard

1. Find **Lifetime Energy** under **Settings → Devices & services → Entities** and compare it with the lifetime production shown in SolarEdge.
2. Open **Settings → Dashboards → Energy** and select **Lifetime Energy** under **Solar panels**.
3. Use one production source per period for the same panels to avoid double counting. If you are switching from an existing sensor and want to keep its production history in the Energy dashboard, plan the statistics migration first. This integration does not automatically migrate the old Home Assistant sensor's history. The lifetime counter includes production since the date you entered.

The **Self-consumed solar energy** card also needs a **grid export energy counter in kWh**, for example from a P1 reader or another compatible grid meter. In the Energy dashboard, add that counter under **Electricity grid → Return to grid**. The **Local grid power** option provides power in W and does not replace the kWh counter. **Lifetime Energy** is sufficient for displaying solar production alone.

## Bringing over history from the legacy integration

A standalone [migration tool with preview](https://github.com/Cindyst1/solaredge-v2/blob/main/tools/README.md#english) is available for a continuous legacy series. Read the prerequisites and test against a restored copy first. This is a separate Python script to run manually.

The first Lifetime Energy value is a meter reading. Home Assistant does not reconstruct historical daily production from it. Renaming an entity does not automatically merge two existing histories either.

1. Create a full Home Assistant backup including the Recorder database. Record the old and new entity IDs, the last valid legacy reading and the first valid V2 reading, including timezone and units.
2. Compare both counters with SolarEdge. Establish the cutover time and check which intervals already exist. The difference between two lifetime counters alone cannot establish the production on individual days.
3. A continuous V2 series requires a separate Recorder statistics migration. It must combine legacy long-term statistics up to the cutover with V2 statistics afterwards. The cumulative statistics sum must remain continuous at the boundary. Simply copying meter readings or importing an interval twice can create artificial production.
4. Fill missing intervals only with verified SolarEdge production for those intervals. Check units, local day boundaries, daylight saving time and overlap with existing records.
5. Compare daily, monthly and yearly totals before and after migration. Then use one continuous production source for these panels in the Energy dashboard. Keep the original data and backup until verification is complete.

The integration does not import history automatically. The standalone tool supports only the continuous prefix described above. The appropriate migration depends on the existing data and Home Assistant version. Migrating long-term Energy dashboard statistics does not automatically move every raw reading in the History view. Seek assistance with the Recorder migration when needed and work from a backup.

## Install manually

Copy `custom_components/solaredge_v2_test` from the [GitHub release](https://github.com/Cindyst1/solaredge-v2/releases/latest) into `/config/custom_components/`. Restart Home Assistant, add **SolarEdge V2**, and follow the steps under **Connect your SolarEdge site**.
