# SCADA-Dokumentation – SmartView OPC

## Was ist SCADA?

**SCADA** steht für **Supervisory Control and Data Acquisition** (Überwachung, Steuerung und Datenerfassung).
Es handelt sich um eine Klasse von Softwaresystemen, die in der Automatisierungstechnik eingesetzt werden,
um Maschinen, Anlagen und Prozesse zu überwachen und zu steuern.

Typische Einsatzgebiete:
- Fertigungsanlagen (Automotive, Chemie, Lebensmittel)
- Energieversorgung (Strom, Gas, Wasser)
- Gebäudeautomation
- Wasseraufbereitung / Kläranlagen

---

## Systemarchitektur von SmartView OPC

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Feldbusebene (Field Level)                   │
│                                                                     │
│   Sensoren                  Aktoren               Messtechnik       │
│   (Endlagen, Magazin,       (Förderband,           (IO-Link ⚠️)     │
│    Lichtschranke)            Zylinder)                              │
│        │                        │                      │            │
│        └────────────────────────┼──────────────────────┘            │
│                                 │ PROFINET                          │
└─────────────────────────────────┼───────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Steuerungsebene (Control Level)                   │
│                                                                      │
│              ┌──────────────────────────────┐                       │
│              │    Siemens S7-1500 (SPS)     │                       │
│              │                              │                       │
│              │  - Verarbeitet Sensordaten   │                       │
│              │  - Steuert Aktoren           │                       │
│              │  - OPC UA Server (Port 4840) │                       │
│              │  - IP: 192.168.6.12          │                       │
│              └──────────────┬───────────────┘                       │
└─────────────────────────────┼────────────────────────────────────────┘
                              │ OPC UA (IEC 62541)
                              │ opc.tcp://192.168.6.12:4840
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Edge-/SCADA-Ebene (Edge Level)                    │
│                                                                      │
│         ┌─────────────────────────────────────────┐                 │
│         │          Raspberry Pi 4B                │                 │
│         │                                         │                 │
│         │  opc_client.py                          │                 │
│         │  ┌─────────────────────────────────┐    │                 │
│         │  │ OPC UA Client (Polling 1s)       │    │                 │
│         │  │ - Liest Tags von S7-1500         │    │                 │
│         │  │ - Speichert in Cache (dict)      │    │                 │
│         │  │ - Erkennt Alarme                 │    │                 │
│         │  │ - Reconnect bei Verbindungsverlust│   │                 │
│         │  │ - Schreibt Steuersignale (OPC)   │    │                 │
│         │  └──────────────┬──────────────────┘    │                 │
│         │                 │                        │                 │
│         │  app.py (Flask REST API)                 │                 │
│         │  ┌──────────────┴───────────────────┐    │                 │
│         │  │ GET  /api/data        → JSON      │    │                 │
│         │  │ GET  /api/tags/<n>    → JSON      │    │                 │
│         │  │ GET  /api/alerts      → JSON      │    │                 │
│         │  │ GET  /api/history/<n> → JSON      │    │                 │
│         │  │ GET  /api/config      → JSON      │    │                 │
│         │  │ POST /api/control/<n> → Schreiben │    │                 │
│         │  │ GET  /api/download/history → CSV  │    │                 │
│         │  └──────────────────────────────────┘    │                 │
│         │                                          │                 │
│         │  history.py (CSV-Logger)                 │                 │
│         │  ┌─────────────────────────────────┐     │                 │
│         │  │ Schreibt alle 5s → data/history  │     │                 │
│         │  └─────────────────────────────────┘     │                 │
│         └──────────────────────┬──────────────────┘                 │
└────────────────────────────────┼────────────────────────────────────┘
                                 │ HTTP (Port 5000)
                                 │ Polling alle 1,5 Sekunden
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Visualisierungsebene (HMI Level)                  │
│                                                                      │
│   ┌──────────────────┐    ┌─────────────────────┐                   │
│   │  Browser (PC)    │    │  Browser (Tablet)    │                   │
│   │  HTML5 Dashboard │    │  Responsive Layout   │                   │
│   │  Bootstrap 5     │    │  Bootstrap 5         │                   │
│   │  Polling (fetch) │    │  Polling (fetch)     │                   │
│   └──────────────────┘    └─────────────────────┘                   │
│                                                                      │
│   Visualisiert: Digitalwerte (LED-Indikatoren), Alarme (Banner),    │
│   Historietabelle, CSV-Download                                     │
└──────────────────────────────────────────────────────────────────────┘
```

> ⚠️ **Systemdruck (Analogwert)**: Aufgrund eines defekten IO-Link-Moduls nicht in Betrieb.
> Mit Lehrer abgesprochen und freigegeben.

---

## OPC UA – Open Platform Communications Unified Architecture

### Was ist OPC UA?

OPC UA (IEC 62541) ist ein industrieller Kommunikationsstandard für die
**sichere, plattformunabhängige Datenübertragung** zwischen Feldgeräten, Steuerungen und IT-Systemen.

**Vorteile gegenüber älteren Protokollen (Modbus, OPC DA):**

| Merkmal          | OPC Classic / Modbus | OPC UA           |
|------------------|----------------------|------------------|
| Plattform        | Windows only         | Cross-Platform   |
| Sicherheit       | Keine / DCOM         | TLS, Zertifikate |
| Datenmodell      | Flach                | Hierarchisch, typisiert |
| Entdeckung       | Manuell              | Discovery-Dienst |
| Standard         | Proprietär           | IEC 62541        |

### Transport-Schicht

In SmartView OPC wird das **Binary TCP** Protokoll genutzt:
```
opc.tcp://<IP>:<Port>
```
Standardport: **4840**

### Sicherheitsmodi

| Modus            | Beschreibung                              | Einsatz                 |
|-----------------|-------------------------------------------|-------------------------|
| `None`           | Keine Verschlüsselung, keine Signierung   | Geschlossenes Intranet  |
| `Sign`           | Signierung, keine Verschlüsselung         | Intranet                |
| `SignAndEncrypt` | Signierung + AES-256 Verschlüsselung      | Produktiv / WAN         |

SmartView OPC nutzt `None` (kein Passwort, kein Zertifikat) – geeignet für abgeschlossene Schulnetzwerke.

---

## Datenfluss: Von der SPS zum Browser

```
SPS (S7-1500)           Raspberry Pi 4B              Browser
     │                        │                          │
     │  OPC UA Read (1s)      │                          │
     │◄──────────────────────│  opc_client._poll_loop() │
     │  xEndlage = True       │                          │
     │──────────────────────►│  _values["endlage"]=True │
     │                        │                          │
     │                        │  HTTP GET /api/data      │
     │                        │◄─────────────────────────│
     │                        │  {"tags":{...}}          │
     │                        │─────────────────────────►│
     │                        │                          │  setInterval(1500ms)
     │                        │                          │  → updateDigitalCard()
     │                        │                          │  → LED grün/rot
```

**Latenz:** OPC UA Polling (1000ms) + HTTP Polling Browser (1500ms) ≈ **ca. 1–2 Sekunden**

### Steuerungs-Datenfluss (Schreiben)

```
Browser                  Raspberry Pi 4B          SPS (S7-1500)
   │                           │                        │
   │  POST /api/control/       │                        │
   │  taster_start             │                        │
   │  {"value": true}          │                        │
   │──────────────────────────►│                        │
   │                           │  OPC UA Write: True    │
   │                           │───────────────────────►│
   │  {"success": true}        │  Warte 300ms           │  → R_TRIG erkennt
   │◄──────────────────────────│  OPC UA Write: False   │    steigende Flanke
   │                           │───────────────────────►│  → Sequenz startet
```

---

## Siemens S7-1500 – OPC UA Konfiguration

### TIA Portal Einstellungen

1. **Gerätekonfiguration öffnen** → CPU S7-1500 auswählen
2. **Eigenschaften → Allgemein → OPC UA** öffnen
3. **"OPC UA Server aktivieren"** ankreuzen
4. **Port**: Standard 4840
5. **Sicherheit**: "Keine Sicherheit" (für Schulnetz ausreichend)
6. **DB-Variablen für OPC UA freigeben**: DB-Eigenschaften → Attribute → "Schreibzugriff über OPC UA"

### Node-ID Format (S7-1500)

```
ns=3;s="Datenbaustein"."Variablenname"
```

Beispiele für die Förderbandstation:

| Beschreibung        | Node-ID                                                                          |
|--------------------|----------------------------------------------------------------------------------|
| Endlage Eingefahren | `ns=3;s="Richten/Automatikbetrieb_Förderbandstation_DB"."xEndlage_Ausschiebezyl_Eingefahren"` |
| Taster Start        | `ns=3;s="Richten/Automatikbetrieb_Förderbandstation_DB"."xTaster_Start"`        |
| Systemdruck ⚠️     | `ns=3;s="Richten/Automatikbetrieb_Förderbandstation_DB"."Druck"`                |

**Werkzeug zur Node-ID Ermittlung:** [Unified Automation UaExpert](https://www.unified-automation.com/products/development-tools/uaexpert.html) (kostenlos)

---

## Verwendete Python-Bibliotheken

| Bibliothek     | Version  | Zweck                                              |
|---------------|----------|----------------------------------------------------|
| `opcua`       | 0.98.13  | OPC UA Client (synchron, S7-kompatibel)            |
| `flask`       | 3.0.3    | Web-Framework für REST API                         |
| `flask-cors`  | 4.0.0    | CORS-Header für Browser-Zugriff                    |
| `gunicorn`    | 22.0.0   | Produktiv-WSGI-Server für Raspberry Pi             |

---

## Industrie 4.0 Kontext

SmartView OPC implementiert die **Datenerfassungsschicht** der Industrie-4.0-Referenzarchitektur (RAMI 4.0):

```
┌─────────────────────────────────────────────┐
│  Unternehmensebene (ERP, MES, Cloud)        │ ← Nicht Teil dieses Projekts
├─────────────────────────────────────────────┤
│  Edge-/SCADA-Ebene                          │ ← SmartView OPC (Raspberry Pi)
├─────────────────────────────────────────────┤
│  Steuerungsebene (SPS)                      │ ← Siemens S7-1500
├─────────────────────────────────────────────┤
│  Feldebene (Sensoren, Aktoren)              │ ← Physische Förderbandstation
└─────────────────────────────────────────────┘
```

Der Raspberry Pi als **Edge Device** ermöglicht:
- Lokale Verarbeitung ohne Cloud-Abhängigkeit
- Kostengünstiger Einstieg in IIoT
- Flexible Erweiterung (Cloud-Upload, MQTT, InfluxDB)
