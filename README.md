# SmartView OPC – Prozessdaten im Griff

> SCADA-System für Industrie 4.0 | Siemens S7-1516 via OPC UA | Raspberry Pi 4B Edge Device

---

## Projektbeschreibung

SmartView OPC ist ein leichtgewichtiges SCADA-System (Supervisory Control and Data Acquisition), das Prozessdaten von einer **Siemens S7-1516 SPS** über das **OPC UA Protokoll** (IEC 62541) ausliest und auf einem modernen, responsiven **Web-Dashboard** visualisiert.

Das System läuft vollständig auf einem **Raspberry Pi 4B** als Edge Device – ohne Cloud-Abhängigkeit, ohne externe Server.

### Highlights

- Live-Anzeige von Analog- und Digitalwerten über SSE (Server-Sent Events)
- Automatischer Reconnect bei Verbindungsverlust zur SPS
- Grenzwert-Alarmierung mit optischem Hinweis im Browser
- CSV-Historisierung aller Messwerte
- Docker-Unterstützung für einfaches Deployment
- Vollständig kommentierter, gut strukturierter Code

---

## Architekturdiagramm

```
  Feldebene                Steuerung              Edge Device (RPi 4B)         Browser
 ┌──────────┐             ┌──────────────┐        ┌─────────────────────┐    ┌──────────┐
 │ Sensoren │──PROFINET──►│ Siemens      │OPC UA  │ opc_client.py       │    │          │
 │ Aktoren  │             │ S7-1516      │◄──────►│ app.py (Flask)      │SSE │ Dashboard│
 │          │             │              │        │ history.py (CSV)    │───►│ Bootstrap│
 └──────────┘             │ OPC UA :4840 │        │                     │    │ 5        │
                          └──────────────┘        │ Port :5000          │    └──────────┘
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

| Einstellung       | Beschreibung                          | Standard                      |
|------------------|---------------------------------------|-------------------------------|
| `OPC_SERVER_URL` | IP + Port des OPC UA Servers (S7-1516)| `opc.tcp://192.168.0.1:4840`  |
| `OPC_TAGS`       | Node-IDs der SPS-Variablen            | Beispiel-Node-IDs (Platzhalter)|

### OPC UA Node-IDs für Siemens S7-1516

Format: `ns=3;s="Datenbaustein"."Variablenname"`

Beispiel: `ns=3;s="DB_Prozess"."Temperatur_Kessel"`

Node-IDs können mit **Siemens UaExpert** oder im TIA Portal unter *OPC UA → Serverübersicht* ermittelt werden.

### Weitere Einstellungen

| Einstellung          | Beschreibung                     | Standard |
|---------------------|----------------------------------|----------|
| `POLL_INTERVAL_MS`  | Abtastrate in Millisekunden      | `1000`   |
| `FLASK_PORT`        | Webserver-Port                   | `5000`   |
| `HISTORY_ENABLED`   | CSV-Logging ein/aus              | `True`   |
| `HISTORY_INTERVAL_S`| CSV-Schreibintervall in Sekunden | `60`     |

---

## API-Dokumentation

| Endpunkt                 | Methode | Beschreibung                             |
|--------------------------|---------|------------------------------------------|
| `/`                      | GET     | Dashboard (HTML)                         |
| `/api/tags`              | GET     | Alle aktuellen Tagwerte (JSON)           |
| `/api/tags/<name>`       | GET     | Einzelner Tagwert (JSON)                 |
| `/api/status`            | GET     | OPC UA Verbindungsstatus (JSON)          |
| `/api/alarms`            | GET     | Aktive Alarme (JSON)                     |
| `/api/history?count=N`   | GET     | Letzte N Historieeinträge (JSON)         |
| `/api/stream`            | GET     | SSE Live-Datenstrom (text/event-stream)  |

### Beispielaufruf

```bash
# Alle aktuellen Werte abrufen
curl http://localhost:5000/api/tags

# Einzelnen Wert abfragen
curl http://localhost:5000/api/tags/temperatur_kessel

# Letzte 50 Historieeinträge
curl http://localhost:5000/api/history?count=50
```

---

## Setup auf dem Raspberry Pi 4B

### Voraussetzungen

- Raspberry Pi 4B mit Raspberry Pi OS (64-bit empfohlen)
- Python 3.9 oder höher
- Netzwerkverbindung zur Siemens S7-1516 (gleiches Subnetz oder geroutet)

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

### Pflicht (implementiert)

- [x] OPC UA Client mit 3 Analogwerten (Temperatur, Druck, Füllstand)
- [x] OPC UA Client mit 3 Digitalwerten (Pumpe, Ventil, Störung)
- [x] REST API: `GET /api/tags` und `GET /api/tags/<name>`
- [x] Webseite mit Live-Anzeige aller Werte
- [x] README + Architekturdiagramm

### Bonus (implementiert)

- [x] **SSE statt Polling** (+5 Punkte): `/api/stream` sendet Updates per Server-Sent Events
- [x] **Alarmierung** (+1 Punkt): Grenzwertüberschreitung → blinkendes Alarm-Banner
- [x] **CSV-History** (+2 Punkte): Alle Messwerte werden minütlich in `data/history.csv` gespeichert
- [x] **Docker** (+6 Punkte): Dockerfile + docker-compose.yml vorhanden

---

## Screenshots

Das Dashboard zeigt:
1. **Navbar**: Projektname + Verbindungsstatus (grün/rot)
2. **Alarm-Banner**: Blinkt rot bei Grenzwertüberschreitung
3. **Analogwert-Karten**: Wert + Einheit + Fortschrittsbalken (farbkodiert)
4. **Digitalwert-Karten**: EIN/AUS mit grünem/grauem Icon
5. **Verlauf**: Tabellarische Darstellung der letzten Messwerte

---

## Team & Lizenz

Entwickelt im Rahmen des Projekts **SmartView OPC** (SFE / Industrie 4.0 Modul)

Lizenz: [MIT](https://opensource.org/licenses/MIT)
