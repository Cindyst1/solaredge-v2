# SolarEdge V2

[English](README_EN.md)

SolarEdge V2 is een community-integratie die de oude SolarEdge-koppeling vervangt. Ze leest zonnegegevens uit via de SolarEdge Monitoring API V2. Bij een eerste installatie wordt een aparte koppeling aangemaakt. Historie uit de oude koppeling wordt niet automatisch overgenomen.

**Bevestigd in Home Assistant: Lifetime Energy.** Deze cumulatieve kWh-teller werkt met SITE_DATA als zonneproductiebron in het Energiedashboard. Dag-, maand- en jaaropbrengst en kwartiervermogen hangen af van de beschikbare cloudgegevens. Zie de sensortabel voor extra machtigingen en lokale bronnen.

## Oude historie overzetten met het aparte migratiehulpmiddel

**Deze stap is optioneel.** Gebruik het migratiehulpmiddel als je de oude SolarEdge-integratie gebruikte en de opgeslagen opbrengsthistorie naar V2 wilt overzetten. Heb je geen oude SolarEdge-historie, of wil je die niet overzetten? Sla deze stap over en ga verder met de gewone V2-installatie.

Wil je de opbrengsthistorie van je oude SolarEdge-sensor meenemen naar V2? Gebruik het [migratiehulpmiddel en de Nederlandse handleiding](https://github.com/Cindyst1/solaredge-v2/blob/main/tools/README.md#nederlands).

**Dit is een los Python-script dat je zelf apart uitvoert.** Installeren of bijwerken via Marketplace of HACS start geen migratie. Het script wordt niet automatisch uitgevoerd door de integratie. Het is beschikbaar op GitHub in de map `tools`.

Het hulpmiddel bepaalt het overgangsuur automatisch uit de opgeslagen statistieken, toont eerst een voorstel en vereist een bevestiging voor de import. Bij ontbrekende uren of onvoldoende bewijs voor de overgang stopt het of vraagt het om extra controle. Het ondersteunt een doorlopende reeks oude kWh-uurstatistieken en controleert op overlap en een passend overgangsuur. Het is getest met een afzonderlijke Home Assistant-installatie en synthetische gegevens. Maak een volledige back-up, lees de voorwaarden en controleer na afloop de opbrengsttotalen. Het hulpmiddel neemt langetermijnstatistieken voor het Energiedashboard over; het kopieert geen ruwe Geschiedenis-metingen.

### Eerste installatie zonder oude historie getest

Installatie via de echte Marketplace is getest op een aparte Home Assistant 2026.11.1 met een lege database. Na de herstart is de eerste configuratie afgerond en Lifetime Energy als zonnebron in het Energiedashboard geselecteerd. De testsensor steeg van 100 naar 102 kWh. De externe SolarEdge-login en API-antwoorden waren gesimuleerd. [Bekijk de geslaagde test](https://github.com/Cindyst1/solaredge-v2/actions/runs/45083064022).

**Heb je geen historie uit de oude SolarEdge-integratie? Dan kun je de migratie overslaan en direct installeren.** Home Assistant gaat vanaf de installatie nieuwe metingen opslaan. De levenslange tellerstand maakt op zichzelf geen historische dagmetingen aan.

## 1. Installeren

### Home Assistant 2026.11 en nieuwer: Marketplace

1. Ga als beheerder naar **Instellingen → Marketplace** en bevestig bij het eerste gebruik de melding om installaties toe te staan.
2. Zoek naar **SolarEdge V2**. Staat de integratie er niet bij? Kies **Toevoegen via link** en voer `https://github.com/Cindyst1/solaredge-v2` in. Verbind GitHub als Marketplace daarom vraagt. Kies indien nodig **Integratie** als type.
3. Open **SolarEdge V2**, kies **Installeren** en herstart Home Assistant wanneer daarom wordt gevraagd.

Zie de [Marketplace-handleiding](https://www.home-assistant.io/integrations/marketplace/#custom-repositories).

### Home Assistant 2026.10 en ouder: HACS

1. Open **HACS → ⋮ → Aangepaste repositories**. Voeg `https://github.com/Cindyst1/solaredge-v2` toe als **Integratie**.
2. Open **SolarEdge V2**, kies **Downloaden** en herstart Home Assistant.

Zie de [HACS-handleiding](https://www.hacs.xyz/docs/faq/custom_repositories/).

Ga na een eerste installatie naar **Instellingen → Apparaten en diensten → Integratie toevoegen** en zoek **SolarEdge V2**. Bij een update blijft de bestaande koppeling in gebruik.

## 2. Koppel je SolarEdge-installatie

1. Maak in het [SolarEdge Developer Platform](https://developer.solaredge.com/) een **Monitoring API**-app aan met toegangstype **Site Access** en scope **SITE_DATA**.
2. Registreer `http://localhost:8080/oauth/callback` als toegestane redirect-URL. Bewaar je **Client ID** en **Client Secret**.
3. Vul in Home Assistant je Client ID, Client Secret en de eerste productiedatum van je installatie in (`JJJJ-MM-DD`).
4. Open op hetzelfde apparaat de aanmeldlink die Home Assistant toont. Kies je SolarEdge-installatie en geef toestemming.
5. Kopieer de volledige `localhost`-URL uit de adresbalk naar het afgeschermde veld in Home Assistant. De browser kan op die URL een verbindingsfout tonen. De URL bevat de tijdelijke aanmeldcode die Home Assistant nodig heeft.

De integratie vraagt toestemming voor één maand en vernieuwt het toegangstoken tijdens die periode. Doorloop de aanmelding opnieuw als Home Assistant daarom vraagt. Houd je Client Secret en de volledige callback-URL privé.

## Welke sensoren leveren een waarde?

| Sensoren | Bron en vereisten |
| --- | --- |
| **Lifetime Energy** | Cumulatieve zonneopbrengst in kWh via **SITE_DATA**. Gebruik deze sensor voor zonneproductie in het Energiedashboard. |
| **Energy Today**, **Produced Energy Today**, **Energy This Month**, **Energy This Year** | Opbrengst over de betreffende periode via **SITE_DATA**. De twee dagsensoren tonen dezelfde productie. |
| **Current Power**, **Solar Power Flow** | Zonnevermogen in W. De cloud levert een kwartierwaarde die maximaal twee uur oud mag zijn. Je kunt ook een bestaande lokale vermogenssensor kiezen. |
| **Last Reported Site Power** | Laatst beschikbare cloudwaarde voor het installatievermogen binnen het zoekvenster van elf uur. Het meettijdstip staat in `sample_at`. |
| **Site Status**, **Imported Energy Today**, **Exported Energy Today**, **Consumed Energy Today**, **Self Consumed Energy Today** | Optionele cloudgegevens. De sensoren krijgen een waarde als SolarEdge die voor je installatie en toegang levert. |
| **Grid Power Flow**, **Grid Flow Direction** | Via een gekozen lokale netvermogenssensor, zoals P1, of via de cloud als Advanced Monitoring energiestromen levert. |
| **Home Consumption Power Flow**, **Battery Power Flow**, **Battery Flow Direction** | Vereisen energiestromen via Advanced Monitoring. SolarEdge kan toegang tot dit onderdeel afzonderlijk weigeren. |
| **Meters**, **Inverters**, registratiestatus per apparaat | Schakel apparaatdetectie in en autoriseer ook **DEVICE_DATA**. De inventaris is afhankelijk van wat SolarEdge voor je site teruggeeft. |
| **Power (15-minute average)** per omvormer | Vereist een omvormer die SolarEdge als actief rapporteert en toegang tot diens vermogensgegevens. Inventaristoegang alleen kan onvoldoende zijn. |
| **Sensors**, **Gateways**, **Batteries**, **Storage Level** | Deze entiteiten hebben nog geen databron. |

Een optionele sensor kan **Onbekend** tonen als de bron ontbreekt of SolarEdge toegang weigert. **Lifetime Energy** en het installatievermogen worden elke 15 minuten opgevraagd, ook met apparaatdetectie. De overige dagtotalen en inventaris worden minder vaak bijgewerkt. De tijd van de laatste cloudmeting kan afwijken van het moment waarop Home Assistant de sensor bijwerkt.

### Apparaatdetectie of een lokale bron toevoegen

- **Omvormers en meters.** Sta **DEVICE_DATA** toe in je SolarEdge-app. Open bij de integratie **⋮ → Opnieuw configureren**, vink **Omvormers en meters zoeken** aan en autoriseer dezelfde installatie opnieuw.
- **Netvermogen.** Open **Configureren** en kies bij **Lokaal netvermogen** een bestaande sensor zoals je P1-meter. Positief betekent afname en negatief betekent teruglevering. Deze keuze levert netvermogen en netrichting. De energiedagtotalen komen via SolarEdge.
- **Zonnevermogen.** Kies bij **Lokaal zonnevermogen** eventueel een bestaande Home Assistant-sensor in W of kW. De integratie leest de gekozen entiteit uit. Voor een installatie die uitsluitend de cloud gebruikt, kun je beide lokale velden leeg laten.

## Energiedashboard

1. Zoek **Lifetime Energy** in **Instellingen → Apparaten en diensten → Entiteiten** en vergelijk de tellerstand met de levenslange opbrengst in SolarEdge.
2. Open **Instellingen → Dashboards → Energie** en selecteer **Lifetime Energy** onder **Zonnepanelen**.
3. Gebruik voor dezelfde zonnepanelen één productiebron per periode om dubbeltelling te voorkomen. Als je overstapt van een bestaande sensor en de oude opbrengst in het Energiedashboard wilt behouden, plan dan eerst de overgang van de statistieken. Deze integratie neemt de historie van de oude Home Assistant-sensor niet automatisch over. De levenslange tellerstand bevat wel de opbrengst sinds de opgegeven productiestart.

Voor de kaart **Zelf verbruikte zonne-energie** heeft Home Assistant ook een teller voor **teruggeleverde energie in kWh** nodig, bijvoorbeeld van een P1-meter of een andere geschikte netmeter. Voeg die teller in het Energiedashboard toe bij **Elektriciteitsnet → Teruglevering aan het net**. De optie **Lokaal netvermogen** geeft vermogen in W en vervangt deze kWh-teller niet. Voor alleen de weergave van zonneproductie volstaat **Lifetime Energy**.

## Historie van de oude koppeling meenemen

Voor een doorlopende oude reeks is een afzonderlijk [migratiehulpmiddel met voorvertoning](https://github.com/Cindyst1/solaredge-v2/blob/main/tools/README.md#nederlands) beschikbaar. Lees eerst de voorwaarden en test op een herstelde kopie. Dit is een los Python-script dat je handmatig uitvoert.

De eerste Lifetime Energy-waarde is een tellerstand. Home Assistant maakt daaruit geen historische dagopbrengsten. Ook het hernoemen van een sensor voegt twee bestaande geschiedenissen niet automatisch samen.

1. Maak een volledige Home Assistant-back-up met de Recorder-database. Noteer de oude en nieuwe entiteit-ID, de laatste geldige oude meting en de eerste geldige V2-meting, inclusief tijdzone en eenheid.
2. Vergelijk beide tellers met SolarEdge. Bepaal het omschakelmoment en controleer welke tijdvakken al aanwezig zijn. Het verschil tussen twee levensduurtellers is op zichzelf onvoldoende om de opbrengst over afzonderlijke dagen te verdelen.
3. Voor één doorlopende V2-reeks is een afzonderlijke Recorder-statistiekenmigratie nodig. Die moet oude langetermijnstatistieken tot het omschakelmoment samenvoegen met de V2-statistieken daarna. De cumulatieve statistiek ('sum') moet bij de overgang aansluiten. Een losse kopie van tellerstanden of een dubbele import kan een kunstmatige opbrengst veroorzaken.
4. Vul eventuele ontbrekende perioden alleen aan met gecontroleerde SolarEdge-opbrengsten voor die perioden. Controleer eenheden, lokale daggrenzen, zomer- en wintertijd en overlap met bestaande gegevens.
5. Vergelijk dag-, maand- en jaartotalen vóór en na de migratie. Gebruik in het Energiedashboard vervolgens één doorlopende productiebron voor deze zonnepanelen. Bewaar de oorspronkelijke gegevens en de back-up totdat de controle klaar is.

De integratie importeert geen historie automatisch. Het afzonderlijke hulpmiddel ondersteunt alleen de hierboven beschreven aaneengesloten reeks. De juiste migratie hangt af van de aanwezige gegevens en je Home Assistant-versie. Een migratie van langetermijnstatistieken voor het Energiedashboard neemt niet vanzelf alle ruwe metingen in de Geschiedenis-weergave mee. Laat bij twijfel de Recorder-migratie begeleiden en werk vanuit een back-up.

## Handmatig installeren

Kopieer `custom_components/solaredge_v2_test` uit de [GitHub-release](https://github.com/Cindyst1/solaredge-v2/releases/latest) naar `/config/custom_components/`. Herstart Home Assistant, voeg **SolarEdge V2** toe en volg de stappen onder **Koppel je SolarEdge-installatie**.
