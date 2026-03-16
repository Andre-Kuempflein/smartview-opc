# Changelog – SmartView OPC

Alle wichtigen Änderungen werden in dieser Datei dokumentiert.
Format: [Semantic Versioning](https://semver.org/)

---

## [2.0.1] – 2026-03-16 – DB2 Migration

### Geändert
- **Node-IDs**: Alle OPC UA Node-IDs von `DB1` auf `DB2` umgestellt
  - Grund: DB2 wurde ohne "Optimierter Bausteinzugriff" angelegt (erforderlich für OPC UA Zugriff)
  - Betrifft: `config.py` → `TAG_NODES` und `CONTROL_NODES`

---

## [2.0.0] – 2026-03-02 – Förderbandstation

### Geändert
- **SPS-Konfiguration**: Neuer OPC UA Endpoint `opc.tcp://192.168.6.12:4840` (S7-1500)
- **TAG_NODES**: Druckluft-Analogwert entfernt → 2 digitale Endlagen-Status aus DB1
  - `endlage_eingefahren` (`ns=3;s="DB1"."xEndlage_Ausschiebezyl_Eingefahren"`)
  - `endlage_ausgefahren` (`ns=3;s="DB1"."xEndlage_Ausschiebezyl_Ausgefahren"`)
- **CONTROL_NODES**: 4 Zylinder-Steuerungen entfernt → 3 Taster aus DB1
  - `taster_start` (`ns=3;s="DB1"."xTaster_Start"`)
  - `schalter_stopp` (`ns=3;s="DB1"."xSchalter_Stopp"`)
  - `taster_reset` (`ns=3;s="DB1"."xTaster_Reset"`)
- **Frontend**: Komplettes Redesign des Dashboards
  - Endlagen-Status als LED-Indikatoren (AKTIV/INAKTIV mit Glow-Effekt)
  - Start (grün), Stopp (rot), Reset (gelb) Buttons mit farbigen Icons
  - Seitentitel: „Förderbandstation" statt „Prozessdaten Dashboard"

### Hinzugefügt
- **Historietabelle**: Aufklappbare Sektion im Dashboard (Bootstrap Collapse)
  - Zeigt letzte 50 Endlagen-Statusänderungen mit Zeitstempel
  - Auto-Refresh alle 5 Sekunden wenn geöffnet
  - Button wechselt zwischen „Anzeigen" / „Ausblenden"
- **Digital-Tag-Support**: `updateDigitalCard()` in `app.js` für Bool-Werte
- **Demo-Simulation**: `_read_demo_values()` simuliert Bool-Endlagen statt Druckluft-Sinus

### Behoben
- `/api/config` Endpunkt: `cfg["unit"]` → `cfg.get("unit", "")` für digitale Tags ohne Einheit
- Tag-Initialisierung: `unit`-Feld ist jetzt optional in `opc_client.py`

---

## [1.0.0] – 2025-02-13 – Erstveröffentlichung

### Hinzugefügt
- OPC UA Client (`opc_client.py`) mit Polling (1-Sekunden-Takt)
  - Liest 3 Analogwerte: Kesseltemperatur (°C), Leitungsdruck (bar), Füllstand (%)
  - Liest 3 Digitalwerte: Pumpe 1 Lauf, Ventil 1 Auf, Störung Anlage
  - Automatischer Reconnect bei Verbindungsverlust (5-Sekunden-Pause)
  - Thread-sichere Datenspeicherung (Lock-basiert)
  - Alarmprüfung bei Grenzwertüberschreitung (analog + digital)

- Flask REST API (`app.py`)
  - `GET /api/tags` – alle aktuellen Tagwerte als JSON
  - `GET /api/tags/<name>` – einzelner Tagwert als JSON
  - `GET /api/status` – Verbindungsstatus (connected / disconnected)
  - `GET /api/alarms` – aktive Alarme als JSON-Array
  - `GET /api/history?count=N` – historische Werte aus CSV
  - `GET /api/stream` – SSE Live-Datenstrom (text/event-stream)
  - CORS-Header für Entwicklung

- CSV-Historisierung (`history.py`)
  - Schreibt alle 60 Sekunden einen Datensatz in `data/history.csv`
  - Erstellt Datei + Ordner automatisch beim ersten Start
  - Konfigurierbar: Intervall, Pfad, Ein/Aus-Schalter

- Zentralisierte Konfiguration (`config.py`)
  - OPC UA Server-URL (Platzhalter für S7-1516)
  - Tag-Definitionen mit Node-IDs (Platzhalter)
  - Metadaten: Label, Einheit, Min/Max-Bereich, Alarmgrenzen
  - Alle Pflichtfelder klar als Platzhalter gekennzeichnet

- Web-Dashboard (`frontend/`)
  - Responsives Bootstrap-5-Layout (Dark-Theme)
  - SSE-basierte Live-Updates (kein Browser-Reload nötig)
  - Analogwert-Karten mit Fortschrittsbalken + Farbkodierung
  - Digitalwert-Karten mit EIN/AUS-Indikator
  - Blinkendes Alarm-Banner bei Grenzwertüberschreitung
  - Verlauf-Tabelle (letzten N Messwerte)
  - Verbindungsstatus-Badge in Navbar

- Docker-Unterstützung
  - `Dockerfile` (Python 3.11-slim, gunicorn)
  - `docker-compose.yml` mit Volume-Mount für CSV-History

- Dokumentation
  - `README.md` mit Quickstart, Setup, API-Referenz, Feature-Liste
  - `docs/SCADA.md` mit Architekturdiagramm, OPC UA Erklärung, Datenfluss
  - Vollständige Code-Kommentierung (Deutsch)

### Technischer Stack
- Python 3.9+, Flask 3.0.3, opcua 0.98.13, gunicorn 22.0.0
- HTML5, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript
- Raspberry Pi 4B als Edge Device
- Siemens S7-1516 mit OPC UA Server

---

## [Geplant] – Zukünftige Versionen

### v1.1.0 (geplant)
- [ ] OPC UA Subscription statt Polling (geringere Netzwerklast)
- [ ] SQLite-Datenbank als Alternative zu CSV
- [ ] Alarm-E-Mail-Benachrichtigung (SMTP)
- [ ] Authentifizierung (Login-Seite, Session)

### v1.2.0 (geplant)
- [ ] MQTT-Export für Cloud-Integration (AWS IoT, Azure IoT Hub)
- [ ] Grafana-Integration (InfluxDB als Datasource)
- [ ] Mehrsprachigkeit (DE/EN)
