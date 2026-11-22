# Lifetime Energy statistics migration

[Nederlands](#nederlands) · [English](#english)

## Nederlands

**Optionele stap voor bestaande gebruikers van de oude SolarEdge-integratie.** Gebruik dit hulpmiddel om die opgeslagen opbrengsthistorie naar V2 over te zetten. Zonder oude historie, of als je die niet wilt overzetten, sla je deze stap over. V2 kan dan direct nieuwe gegevens registreren.

Dit afzonderlijke Python-hulpmiddel importeert een gecontroleerde reeks oude **kWh-uurstatistieken** vóór de eerste V2-statistiek. Het is bedoeld voor Home Assistant 2026.11 en nieuwer. Het wijzigt geen dashboardinstellingen en kopieert geen ruwe Geschiedenis-metingen. Een back-up van de volledige Recorder-database blijft nodig naast het lokale JSON-controlebestand.

Het hulpmiddel stelt automatisch het eerste opgeslagen V2-uur als overgangsuur voor. De beschikbare oude reeks begint één uur na de oudste oude statistiek, die als baseline wordt meegenomen. Bij ontbrekende uren of een al gemigreerde V2-reeks stopt het en schrijft het de reden naar het controlebestand.

Het script vereist doorlopende oude uurgegevens, een cumulatieve teller zonder reset en een nieuwe V2-reeks zonder eerdere statistieken. Er moet een oude statistiek aanwezig zijn voor het uur direct vóór het begin van de import en voor het uur direct vóór de eerste V2-statistiek. Bij ontbrekende perioden, verschillende tellers of een reeds uitgevoerde migratie stopt het script. Het hulpmiddel haalt geen ontbrekende opbrengsten bij SolarEdge op.

### Script downloaden en openen

Open de [repository](https://github.com/Cindyst1/solaredge-v2), kies **Code → Download ZIP** en pak het bestand uit. Open een terminal in de uitgepakte hoofdmap, waarin de map `tools` staat. Je voert de opdrachten op een computer met Python uit. Die computer moet je Home Assistant kunnen bereiken.

### Voorbereiden en controleren

1. Maak een volledige Home Assistant-back-up inclusief Recorder. Voer het hulpmiddel eerst uit tegen een herstelde testkopie. De import is getest tegen een geïsoleerde Home Assistant 2026.11.1 met een eigen Recorder-database en verzonnen gegevens. Daarbij zijn het dag- en jaartotaal van 8 kWh, het behoud van meterstanden, een geweigerd onjuist overgangstotaal en bescherming tegen opnieuw importeren gecontroleerd.
2. Installeer Python 3.11 of nieuwer en `websocket-client` met `python -m pip install websocket-client`.
3. Open in Home Assistant je gebruikersprofiel, ga naar **Beveiliging** en maak bij **Langlevende toegangstokens** een token aan voor deze migratie. Je account moet beheerder zijn. Gebruik dit token tijdelijk en verwijder het na afloop. Het script vraagt dit afgeschermd, of leest `HA_TOKEN` uit de omgeving. Gebruik HTTPS voor toegang buiten je vertrouwde lokale netwerk.
4. Zoek de entiteit-ID van de oude Lifetime Energy-sensor en die van V2 onder **Instellingen → Apparaten en diensten → Entiteiten**. Voor deze sensoren zijn dat ook de statistiek-ID's. Het script bepaalt de uren en toont het voorstel in UTC. Controleer de voorgestelde periode voordat je importeert.
5. Start een voorvertoning met je eigen waarden. De onderstaande namen zijn voorbeelden.

```sh
python tools/migrate_statistics.py --url http://homeassistant.local:8123 --source sensor.legacy_lifetime_energy --target sensor.solaredge_v2_test_lifetime_energy --output preview-private.json
```

Controleer de voorgestelde uren en productie. Voor import gebruik je dezelfde opdracht met een **nieuwe** bestandsnaam en `--apply`. Typ `IMPORT` wanneer het script daarom vraagt. Als de oude statistiek in het eerste V2-uur dezelfde tellerstand toont en de uurproductie bevestigt, wordt de overgang automatisch gecontroleerd. Anders vraagt het hulpmiddel om een onafhankelijk gecontroleerde opbrengst via `--confirmed-bridge-kwh WAARDE`. Bij een langere datakloof kan het hulpmiddel de ontbrekende opbrengst niet zelf over dagen verdelen. De opties `--start` en `--cutover` blijven beschikbaar voor expliciete controle.

Het script importeert alleen de ontbrekende oude reeks en een baseline-uur. De geïmporteerde reeks begint met een statistiekbaseline van nul. De bestaande V2-statistieksommen worden met één constante verschoven om oude productie en het overgangsuur mee te nemen. De V2-tellerstanden en de productieverschillen tussen bestaande V2-uren blijven behouden. Deze verschuiving wordt vooraf getoond en in het controlebestand vastgelegd. Het controleert na import de toegevoegde rijen en vergelijkt alle bestaande bron- en doelrijen met de vooraf gelezen gegevens. Voer tijdens de migratie geen andere statistiekencorrecties of imports uit.

Bij een fout na het versturen van de import moet je eerst het resultaat en het controlebestand onderzoeken. De import kan al verwerkt zijn. Een volgende uitvoering stopt zodra eerdere doelstatistieken bestaan. Vergelijk dag-, maand- en jaartotalen met SolarEdge en kies pas na die controle één V2-productiebron in het Energiedashboard. Bewaar de oude bron en back-up. Verwijder het tijdelijke toegangstoken na afloop.

**De JSON-controlebestanden bevatten jouw meterstanden en historie. Bewaar ze privé en upload ze niet naar GitHub of een issue.** De broncode in deze map bevat uitsluitend algemene code en synthetische testgegevens.

## English

**Optional step for existing users of the legacy SolarEdge integration.** Use this tool to transfer its stored production history to V2. If you have no legacy history, or do not want to transfer it, skip this step. V2 can start recording new data directly.

This standalone Python tool imports a checked prefix of legacy **hourly kWh statistics** before the first V2 statistics row. It targets Home Assistant 2026.11 and later. It does not configure dashboards or copy raw History readings. Create a full Recorder database backup in addition to the local JSON audit file.

The tool proposes the first stored V2 hour as the cutover automatically. The legacy import begins one hour after the oldest legacy statistic, which serves as the baseline. Missing hours or an already migrated target stop the proposal and record a reason in the audit file.

It requires continuous legacy hourly records, a cumulative meter without resets, and a V2 series without earlier statistics. A legacy baseline must exist for the hour before the import start and the hour before the first V2 statistics row. Gaps, incompatible counters or a previous migration cause the tool to stop. The tool does not fetch missing production from SolarEdge.

### Download and open the script

Open the [repository](https://github.com/Cindyst1/solaredge-v2), select **Code → Download ZIP**, and extract it. Open a terminal in the extracted repository root, which contains the `tools` directory. Run these commands on a computer with Python and network access to Home Assistant.

### Preparation and preview

1. Create a full Home Assistant backup including Recorder. Run against a restored test copy first. Live import has been tested against isolated Home Assistant 2026.11.1 and its own Recorder database with synthetic data. Checks cover an 8 kWh daily and yearly total, preserved meter readings, rejection of incorrect bridge production, and repeated-import protection.
2. Install Python 3.11 or later and `websocket-client` with `python -m pip install websocket-client`.
3. In Home Assistant, open your user profile, go to **Security**, and create a **Long-lived access token** for this migration. Use an administrator account. Use the token temporarily and revoke it afterwards. The script prompts without echo or reads `HA_TOKEN` from the environment. Use HTTPS outside your trusted local network.
4. Find the legacy and V2 Lifetime Energy entity IDs under **Settings → Devices & services → Entities**. For these sensors they are also the statistic IDs. The tool detects the hours and displays its proposal in UTC. Review the proposed period before importing.
5. Run this preview command with your own values. The example IDs are placeholders.

```sh
python tools/migrate_statistics.py --url http://homeassistant.local:8123 --source sensor.legacy_lifetime_energy --target sensor.solaredge_v2_test_lifetime_energy --output preview-private.json
```

Review the proposed hours and production. To import, repeat the command with a **new** output filename and `--apply`. Type `IMPORT` when prompted. The bridge is verified automatically if the legacy statistic at the first V2 hour matches its counter and confirms the hourly production. Otherwise supply independently verified production with `--confirmed-bridge-kwh VALUE`. The tool cannot allocate missing production across a longer gap automatically. Optional `--start` and `--cutover` arguments remain available for explicit control.

Only the missing legacy prefix and one baseline hour are imported. The imported series starts at a zero statistics baseline. Existing V2 statistics sums receive one constant offset to include legacy production and the bridge hour. V2 meter readings and production differences between existing V2 hours are preserved. The offset is shown in the preview and recorded in the audit file. After import the script checks inserted values and compares all original source and target rows with its initial snapshot. Avoid concurrent statistics corrections or imports.

If an error occurs after sending the import, inspect the audit and database before retrying. The import may already have completed. A subsequent run stops when earlier target statistics exist. Verify daily, monthly and yearly production against SolarEdge before selecting one continuous V2 source in the Energy dashboard. Keep the original source and backup, then revoke the temporary token.

**The JSON audit files contain your meter readings and history. Keep them private and never attach them to GitHub or an issue.** This directory contains generic code and synthetic test fixtures only.

## Reproducible integration test

The manual GitHub Actions workflow runs tools/test_live_recorder.py inside the official Home Assistant 2026.11.1 container. Its temporary configuration and database contain synthetic data only and are removed after the test. [Passing run](https://github.com/Cindyst1/solaredge-v2/actions/runs/45082294778).

## First installation without legacy history / Eerste installatie zonder oude historie

Een aparte Home Assistant 2026.11.1-test met een lege database downloadt release 0.6.8 via de echte Marketplace, herstart de testomgeving en doorloopt de eerste configuratie zonder migratiestap. De test controleert Lifetime Energy van 100 naar 102 kWh en selectie als zonnebron in het Energiedashboard. Alleen de externe SolarEdge-login en API-antwoorden zijn gesimuleerd. De persoonlijke installatie wordt niet gebruikt. [Geslaagde test](https://github.com/Cindyst1/solaredge-v2/actions/runs/45083064022).

A separate Home Assistant 2026.11.1 test with an empty database downloads release 0.6.8 through the real Marketplace, restarts the test environment, and completes first-time configuration without migration. It checks Lifetime Energy from 100 to 102 kWh and selection as an Energy dashboard solar source. Only the external SolarEdge login and API responses are simulated. No personal installation is used. [Passing test](https://github.com/Cindyst1/solaredge-v2/actions/runs/45083064022).
