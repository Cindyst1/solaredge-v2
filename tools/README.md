# Lifetime Energy statistics migration

[Nederlands](#nederlands) · [English](#english)

## Nederlands

Dit afzonderlijke Python-hulpmiddel importeert een gecontroleerde reeks oude **kWh-uurstatistieken** vóór de eerste V2-statistiek. Het is bedoeld voor Home Assistant 2026.11 en nieuwer. Het wijzigt geen dashboardinstellingen en kopieert geen ruwe Geschiedenis-metingen. Een back-up van de volledige Recorder-database blijft nodig naast het lokale JSON-controlebestand.

Het kiezen van het overgangsuur vereist inzicht in de opgeslagen uurstatistieken. Vraag hulp als je dat uur niet met zekerheid kunt bepalen.

Het script vereist doorlopende oude uurgegevens, een cumulatieve teller zonder reset en een nieuwe V2-reeks zonder eerdere statistieken. Er moet een oude statistiek aanwezig zijn voor het uur direct vóór het begin van de import en voor het uur direct vóór de eerste V2-statistiek. Bij ontbrekende perioden, verschillende tellers of een reeds uitgevoerde migratie stopt het script. Het hulpmiddel haalt geen ontbrekende opbrengsten bij SolarEdge op.

### Script downloaden en openen

Open de [repository](https://github.com/Cindyst1/solaredge-v2), kies **Code → Download ZIP** en pak het bestand uit. Open een terminal in de uitgepakte hoofdmap, waarin de map `tools` staat. Je voert de opdrachten op een computer met Python uit. Die computer moet je Home Assistant kunnen bereiken.

### Voorbereiden en controleren

1. Maak een volledige Home Assistant-back-up inclusief Recorder. Voer het hulpmiddel eerst uit tegen een herstelde testkopie. De import is getest tegen een geïsoleerde Home Assistant 2026.11.1 met een eigen Recorder-database en verzonnen gegevens. Daarbij zijn het dag- en jaartotaal van 8 kWh, het behoud van meterstanden, een geweigerd onjuist overgangstotaal en bescherming tegen opnieuw importeren gecontroleerd.
2. Installeer Python 3.11 of nieuwer en `websocket-client` met `python -m pip install websocket-client`.
3. Open in Home Assistant je gebruikersprofiel, ga naar **Beveiliging** en maak bij **Langlevende toegangstokens** een token aan voor deze migratie. Je account moet beheerder zijn. Gebruik dit token tijdelijk en verwijder het na afloop. Het script vraagt dit afgeschermd, of leest `HA_TOKEN` uit de omgeving. Gebruik HTTPS voor toegang buiten je vertrouwde lokale netwerk.
4. Zoek de entiteit-ID van de oude Lifetime Energy-sensor en die van V2 onder **Ontwikkelaarstools → Statussen**. Voor deze sensoren zijn dat ook de statistiek-ID's. Bepaal vervolgens het eerste te importeren uur en het eerste bestaande V2-uur. Geef een expliciete UTC-offset mee. Controleer onafhankelijk, bijvoorbeeld in SolarEdge, de opbrengst binnen dat eerste V2-uur. Een tellerafstand door een langere datakloof kan niet aan één uur worden toegeschreven.
5. Start een voorvertoning met je eigen waarden. De onderstaande namen en datums zijn voorbeelden.

```sh
python tools/migrate_statistics.py --url http://homeassistant.local:8123 --source sensor.legacy_lifetime_energy --target sensor.solaredge_v2_test_lifetime_energy --start 2026-01-01T00:00:00+01:00 --cutover 2026-02-01T00:00:00+01:00 --output preview-private.json
```

Controleer de getoonde productie en het overgangsuur. Voor de echte import gebruik je dezelfde opdracht met een **nieuwe** bestandsnaam, plus `--apply --confirmed-bridge-kwh WAARDE`. Vervang `WAARDE` door de onafhankelijk gecontroleerde opbrengst van het eerste V2-uur. Typ daarna `IMPORT` wanneer het script daarom vraagt.

Het script importeert alleen de ontbrekende oude reeks en een baseline-uur. De geïmporteerde reeks begint met een statistiekbaseline van nul. De bestaande V2-statistieksommen worden met één constante verschoven om oude productie en het overgangsuur mee te nemen. De V2-tellerstanden en de productieverschillen tussen bestaande V2-uren blijven behouden. Deze verschuiving wordt vooraf getoond en in het controlebestand vastgelegd. Het controleert na import de toegevoegde rijen en vergelijkt alle bestaande bron- en doelrijen met de vooraf gelezen gegevens. Voer tijdens de migratie geen andere statistiekencorrecties of imports uit.

Bij een fout na het versturen van de import moet je eerst het resultaat en het controlebestand onderzoeken. De import kan al verwerkt zijn. Een volgende uitvoering stopt zodra eerdere doelstatistieken bestaan. Vergelijk dag-, maand- en jaartotalen met SolarEdge en kies pas na die controle één V2-productiebron in het Energiedashboard. Bewaar de oude bron en back-up. Verwijder het tijdelijke toegangstoken na afloop.

**De JSON-controlebestanden bevatten jouw meterstanden en historie. Bewaar ze privé en upload ze niet naar GitHub of een issue.** De broncode in deze map bevat uitsluitend algemene code en synthetische testgegevens.

## English

This standalone Python tool imports a checked prefix of legacy **hourly kWh statistics** before the first V2 statistics row. It targets Home Assistant 2026.11 and later. It does not configure dashboards or copy raw History readings. Create a full Recorder database backup in addition to the local JSON audit file.

Choosing the cutover hour requires understanding the stored hourly statistics. Ask for assistance if you cannot establish that hour reliably.

It requires continuous legacy hourly records, a cumulative meter without resets, and a V2 series without earlier statistics. A legacy baseline must exist for the hour before the import start and the hour before the first V2 statistics row. Gaps, incompatible counters or a previous migration cause the tool to stop. The tool does not fetch missing production from SolarEdge.

### Download and open the script

Open the [repository](https://github.com/Cindyst1/solaredge-v2), select **Code → Download ZIP**, and extract it. Open a terminal in the extracted repository root, which contains the `tools` directory. Run these commands on a computer with Python and network access to Home Assistant.

### Preparation and preview

1. Create a full Home Assistant backup including Recorder. Run against a restored test copy first. Live import has been tested against isolated Home Assistant 2026.11.1 and its own Recorder database with synthetic data. Checks cover an 8 kWh daily and yearly total, preserved meter readings, rejection of incorrect bridge production, and repeated-import protection.
2. Install Python 3.11 or later and `websocket-client` with `python -m pip install websocket-client`.
3. In Home Assistant, open your user profile, go to **Security**, and create a **Long-lived access token** for this migration. Use an administrator account. Use the token temporarily and revoke it afterwards. The script prompts without echo or reads `HA_TOKEN` from the environment. Use HTTPS outside your trusted local network.
4. Find the legacy and V2 Lifetime Energy entity IDs under **Developer tools → States**. For these sensors the entity IDs are also the statistic IDs. Then identify the first hour to import, and the first existing V2 hour. Include an explicit UTC offset. Independently verify production within that first V2 hour, for example in SolarEdge. A counter difference across a longer data gap cannot be assigned to a single hour.
5. Run this preview command with your own values. The example IDs and dates are placeholders.

```sh
python tools/migrate_statistics.py --url http://homeassistant.local:8123 --source sensor.legacy_lifetime_energy --target sensor.solaredge_v2_test_lifetime_energy --start 2026-01-01T00:00:00+01:00 --cutover 2026-02-01T00:00:00+01:00 --output preview-private.json
```

Check the preview and bridge production. To import, use the same command with a **new** output filename and add `--apply --confirmed-bridge-kwh VALUE`, replacing `VALUE` with independently verified first-hour production. Type `IMPORT` when prompted.

Only the missing legacy prefix and one baseline hour are imported. The imported series starts at a zero statistics baseline. Existing V2 statistics sums receive one constant offset to include legacy production and the bridge hour. V2 meter readings and production differences between existing V2 hours are preserved. The offset is shown in the preview and recorded in the audit file. After import the script checks inserted values and compares all original source and target rows with its initial snapshot. Avoid concurrent statistics corrections or imports.

If an error occurs after sending the import, inspect the audit and database before retrying. The import may already have completed. A subsequent run stops when earlier target statistics exist. Verify daily, monthly and yearly production against SolarEdge before selecting one continuous V2 source in the Energy dashboard. Keep the original source and backup, then revoke the temporary token.

**The JSON audit files contain your meter readings and history. Keep them private and never attach them to GitHub or an issue.** This directory contains generic code and synthetic test fixtures only.

## Reproducible integration test

The manual GitHub Actions workflow runs tools/test_live_recorder.py inside the official Home Assistant 2026.11.1 container. Its temporary configuration and database contain synthetic data only and are removed after the test. [Passing run](https://github.com/Cindyst1/solaredge-v2/actions/runs/45081048609).
