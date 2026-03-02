# SmartView OPC – Förderbandstation

> SCADA-System für Industrie 4.0 | Siemens S7-1500 via OPC UA | Raspberry Pi 4B Edge Device

---

## Projektbeschreibung

SmartView OPC ist ein leichtgewichtiges SCADA-System (Supervisory Control and Data Acquisition), das Prozessdaten von einer **Siemens S7-1500 SPS** (IP: `192.168.6.12`) über das **OPC UA Protokoll** (IEC 62541) ausliest und auf einem modernen, responsiven **Web-Dashboard** visualisiert.

Aktuell konfiguriert für die **Förderbandstation** mit Endlagen-Erkennung und Start/Stopp/Reset-Steuerung.

Das System läuft vollständig auf einem **Raspberry Pi 4B** als Edge Device – ohne Cloud-Abhängigkeit, ohne externe Server.

### Highlights

- Live-Anzeige von Digital-Status (Endlagen-LEDs) und Steuerung (Taster-Buttons)
- Automatischer Reconnect bei Verbindungsverlust zur SPS
- Grenzwert-Alarmierung mit optischem Hinweis im Browser
- CSV-Historisierung aller Messwerte
- Aufklappbare Historietabelle im Dashboard
- Docker-Unterstützung für einfaches Deployment
- Vollständig kommentierter, gut strukturierter Code

---

## Architekturdiagramm

```
  Feldebene                Steuerung              Edge Device (RPi 4B)         Browser
 ┌──────────┐             ┌──────────────┐        ┌─────────────────────┐    ┌──────────┐
 │Endlagen- │──PROFINET──►│ Siemens      │OPC UA  │ opc_client.py       │    │          │
 │sensoren  │             │ S7-1500      │◄──────►│ app.py (Flask)      │HTTP│ Dashboard│
 │Förder-   │             │ 192.168.6.12 │        │ history.py (CSV)    │───►│ Bootstrap│
 │band      │             │ OPC UA :4840 │        │                     │    │ 5        │
 └──────────┘             └──────────────┘        │ Port :5000          │    └──────────┘
                                                  └─────────────────────┘
```

Detaillierte Architektur: [docs/SCADA.md](docs/SCADA.md)

---

## Schnellstart

```bash
# 1. Repository klonen
git clone <repo-url>
cd smartview-opc

# 2. Python-Abhängigkeiten installieren
pip install -r backend/requirements.txt

# 3. OPC UA Tags eintragen (!)
#    → backend/config.py öffnen und alle Platzhalter befüllen

# 4. Server starten
python backend/app.py

# 5. Browser öffnen
# http://localhost:5000
```

### Mit Docker (empfohlen für Raspberry Pi)

```bash
# 1. OPC UA Tags eintragen: backend/config.py anpassen

# 2. Container bauen und starten
docker compose up -d

# 3. Browser öffnen
# http://<RaspberryPi-IP>:5000

# Logs anzeigen
docker compose logs -f
```

---

## Projektstruktur

```
smartview-opc/
├── backend/
│   ├── app.py            # Flask REST API + SSE Server (Einstiegspunkt)
│   ├── opc_client.py     # OPC UA Client: Polling, Reconnect, Alarmierung
│   ├── history.py        # CSV-Historisierung der Messwerte
│   ├── config.py         # *** HIER KONFIGURATION ANPASSEN ***
│   └── requirements.txt  # Python-Abhängigkeiten
│
├── frontend/
│   ├── index.html        # Dashboard-Hauptseite
│   ├── css/
│   │   └── style.css     # Industrielles Dark-Theme
│   └── js/
│       └── app.js        # SSE-Client + Karten-Rendering
│
├── docs/
│   └── SCADA.md          # Recherche: SCADA, OPC UA, Architektur
│
├── data/                 # Wird automatisch erstellt: CSV-History
│
├── Dockerfile            # Container-Image Definition
├── docker-compose.yml    # Container-Deployment
├── .gitignore
├── CHANGELOG.md
└── README.md             # Diese Datei
```

---

## Konfiguration

Die gesamte Konfiguration befindet sich in `backend/config.py`.

### Pflichtfelder (vor erstem Start ausfüllen!)

| Einstellung          | Beschreibung                          | Aktueller Wert                      |
|---------------------|---------------------------------------|-------------------------------------|
| `OPC_UA_ENDPOINT`   | IP + Port des OPC UA Servers (S7-1500)| `opc.tcp://192.168.6.12:4840`       |
| `TAG_NODES`         | Lesbare Variablen (Endlagen)          | `endlage_eingefahren`, `endlage_ausgefahren` |
| `CONTROL_NODES`     | Steuerbare Variablen (Taster)         | `taster_start`, `schalter_stopp`, `taster_reset` |

### OPC UA Node-IDs (Förderbandstation – DB1)

| Variable               | Node-ID                                              | Typ     |
|------------------------|------------------------------------------------------|---------|
| Endlage Eingefahren    | `ns=3;s="DB1"."xEndlage_Ausschiebezyl_Eingefahren"` | Bool    |
| Endlage Ausgefahren    | `ns=3;s="DB1"."xEndlage_Ausschiebezyl_Ausgefahren"` | Bool    |
| Taster Start           | `ns=3;s="DB1"."xTaster_Start"`                      | Bool    |
| Schalter Stopp         | `ns=3;s="DB1"."xSchalter_Stopp"`                    | Bool    |
| Taster Reset           | `ns=3;s="DB1"."xTaster_Reset"`                      | Bool    |

Node-IDs können mit **UaExpert** oder im TIA Portal unter *OPC UA → Serverübersicht* ermittelt werden.

### Weitere Einstellungen

| Einstellung          | Beschreibung                     | Standard |
|---------------------|----------------------------------|----------|
| `POLL_INTERVAL_MS`  | Abtastrate in Millisekunden      | `1000`   |
| `FLASK_PORT`        | Webserver-Port                   | `5000`   |
| `HISTORY_ENABLED`   | CSV-Logging ein/aus              | `True`   |
| `HISTORY_INTERVAL_S`| CSV-Schreibintervall in Sekunden | `60`     |

---

## API-Dokumentation

| Endpunkt                        | Methode | Beschreibung                             |
|---------------------------------|---------|------------------------------------------|
| `/`                             | GET     | Dashboard (HTML)                         |
| `/api/data`                     | GET     | Alle Tag-Werte + Steuerungs-Zustände     |
| `/api/tags/<name>`              | GET     | Einzelner Tagwert (JSON)                 |
| `/api/alerts`                   | GET     | Aktive Alarme (JSON)                     |
| `/api/history/<tag_name>`       | GET     | Historische Werte eines Tags (JSON)      |
| `/api/config`                   | GET     | Tag- und Steuerungs-Konfiguration        |
| `/api/control/<ctrl_name>`      | POST    | Steuerung schalten (`{"value": true}`)   |

### Beispielaufruf

```bash
# Alle aktuellen Werte abrufen
curl http://localhost:5000/api/data

# Endlage-Status abfragen
curl http://localhost:5000/api/tags/endlage_eingefahren

# Start-Taster aktivieren
curl -X POST -H "Content-Type: application/json" \
     -d '{"value": true}' http://localhost:5000/api/control/taster_start

# Historie der Endlage abrufen
curl http://localhost:5000/api/history/endlage_eingefahren
```

---

## Setup auf dem Raspberry Pi 4B

### Voraussetzungen

- Raspberry Pi 4B mit Raspberry Pi OS (64-bit empfohlen)
- Python 3.9 oder höher
- Netzwerkverbindung zur Siemens S7-1500 (gleiches Subnetz: `192.168.6.x`)

### Installation ohne Docker

```bash
# Python-Pakete installieren
pip3 install -r backend/requirements.txt

# Konfiguration anpassen
nano backend/config.py

# Server starten
python3 backend/app.py
```

### Autostart mit systemd (empfohlen)

```bash
sudo nano /etc/systemd/system/smartview.service
```

```ini
[Unit]
Description=SmartView OPC SCADA Server
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/smartview-opc
ExecStart=/usr/bin/python3 backend/app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable smartview
sudo systemctl start smartview
sudo systemctl status smartview
```

---

## Features

### Förderbandstation (v2.0)

- [x] OPC UA Client mit 2 Digitalwerten (Endlage Eingefahren/Ausgefahren)
- [x] OPC UA Client mit 3 Steuerungen (Start, Stopp, Reset)
- [x] REST API: `GET /api/data`, `POST /api/control/<name>`
- [x] Webseite mit Live-Endlagen-LEDs und Steuerungs-Buttons
- [x] Aufklappbare Historietabelle (letzte 50 Statusänderungen)
- [x] Demo-Modus für Entwicklung ohne SPS
- [x] README + Architekturdiagramm

### Bonus (implementiert)

- [x] **Alarmierung**: Grenzwertüberschreitung → blinkendes Alarm-Banner
- [x] **CSV-History**: Alle Messwerte werden periodisch in `data/history.csv` gespeichert
- [x] **Docker**: Dockerfile + docker-compose.yml vorhanden
- [x] **In-Memory-Historie**: Aufklappbare Tabelle im Dashboard

---

## Screenshots

Das Dashboard zeigt:
1. **Navbar**: Projektname + Verbindungsstatus (grün/rot) + DEMO-Badge
2. **Endlagen-Status**: LED-Indikatoren für Eingefahren/Ausgefahren (AKTIV/INAKTIV)
3. **Steuerung**: Start (grün), Stopp (rot), Reset (gelb) Buttons
4. **Historie**: Aufklappbare Tabelle der letzten Statusänderungen
5. **Alarm-Banner**: Blinkt rot bei Grenzwertüberschreitung

---

## Team & Lizenz

Entwickelt im Rahmen des Projekts **SmartView OPC** (SFE / Industrie 4.0 Modul)

Lizenz: [MIT](https://opensource.org/licenses/MIT)
