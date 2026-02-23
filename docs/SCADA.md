# SCADA-Recherche – SmartView OPC

## Was ist SCADA?

**SCADA** steht für **Supervisory Control and Data Acquisition** (Überwachung, Steuerung und Datenerfassung). Es handelt sich um eine Klasse von Softwaresystemen, die in der Automatisierungstechnik und Industrie eingesetzt werden, um Maschinen, Anlagen und Prozesse zu überwachen und zu steuern.

Typische Einsatzgebiete:
- Energieversorgung (Strom, Gas, Wasser)
- Fertigungsanlagen (Automotive, Chemie, Lebensmittel)
- Gebäudeautomation
- Wasseraufbereitung / Kläranlagen
- Öl- und Gasleitungen

---

## Systemarchitektur von SmartView OPC

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Feldbusebene (Field Level)                   │
│                                                                     │
│   Sensoren          Aktoren          Messtechnik                    │
│   (Temp., Druck,    (Pumpen,         (Durchfluss,                  │
│    Füllstand)        Ventile)         Energie)                      │
│        │                 │                 │                        │
│        └─────────────────┼─────────────────┘                       │
│                          │ PROFINET / PROFIBUS                      │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Steuerungsebene (Control Level)                   │
│                                                                      │
│              ┌──────────────────────────────┐                       │
│              │    Siemens S7-1516 (SPS)     │                       │
│              │                              │                       │
│              │  - Verarbeitet Sensordaten   │                       │
│              │  - Steuert Aktoren           │                       │
│              │  - OPC UA Server (Port 4840) │                       │
│              │  - Taktzeit: 10–100 ms       │                       │
│              └──────────────┬───────────────┘                       │
└─────────────────────────────┼────────────────────────────────────────┘
                              │ OPC UA (IEC 62541)
                              │ opc.tcp://192.168.x.x:4840
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
│         │  │ - Liest Tags von S7-1516         │    │                 │
│         │  │ - Speichert in Cache (dict)      │    │                 │
│         │  │ - Erkennt Alarme                 │    │                 │
│         │  │ - Reconnect bei Verbindungsverlust│   │                 │
│         │  └──────────────┬──────────────────┘    │                 │
│         │                 │                        │                 │
│         │  app.py (Flask) │                        │                 │
│         │  ┌──────────────┴───────────────────┐    │                 │
│         │  │ REST API                          │    │                 │
│         │  │  GET /api/tags     → JSON         │    │                 │
│         │  │  GET /api/tags/<n> → JSON         │    │                 │
│         │  │  GET /api/status   → JSON         │    │                 │
│         │  │  GET /api/alarms   → JSON         │    │                 │
│         │  │  GET /api/history  → JSON         │    │                 │
│         │  │  GET /api/stream   → SSE Stream   │    │                 │
│         │  └──────────────────────────────────┘    │                 │
│         │                                          │                 │
│         │  history.py (CSV-Logger)                 │                 │
│         │  ┌─────────────────────────────────┐     │                 │
│         │  │ Schreibt alle 60s → data/history │     │                 │
│         │  └─────────────────────────────────┘     │                 │
│         └──────────────────────┬──────────────────┘                 │
└────────────────────────────────┼────────────────────────────────────┘
                                 │ HTTP / SSE (Port 5000)
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    Visualisierungsebene (HMI Level)                  │
│                                                                      │
│   ┌──────────────────┐    ┌─────────────────────┐                   │
│   │  Browser (PC)    │    │  Browser (Tablet)    │                   │
│   │  HTML5 Dashboard │    │  Responsive Layout   │                   │
│   │  Bootstrap 5     │    │  Bootstrap 5         │                   │
│   │  SSE Live-Update │    │  SSE Live-Update     │                   │
│   └──────────────────┘    └─────────────────────┘                   │
│                                                                      │
│   Visualisiert: Analogwerte (Balken), Digitalwerte (EIN/AUS),       │
│   Alarme (blinkendes Banner), History (Tabelle)                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## OPC UA – Open Platform Communications Unified Architecture

### Was ist OPC UA?

OPC UA (IEC 62541) ist ein industrieller Kommunikationsstandard für die **sichere, plattformunabhängige Datenübertragung** zwischen Feldgeräten, Steuerungen und IT-Systemen.

**Vorteile gegenüber älteren Protokollen (Modbus, OPC DA):**
| Merkmal          | OPC Classic / Modbus | OPC UA         |
|------------------|----------------------|----------------|
| Plattform        | Windows only         | Cross-Platform |
| Sicherheit       | Keine / DCOM         | TLS, Zertifikate |
| Datenmodell      | Flach                | Hierarchisch, typisiert |
| Entdeckung       | Manuell              | Discovery-Dienst |
| Standard         | Proprietär           | IEC 62541      |

### Transport-Schicht

In SmartView OPC wird das **Binary TCP** Protokoll genutzt:
```
opc.tcp://<IP>:<Port>
```

Standardport: **4840** (kann in TIA Portal konfiguriert werden)

### Sicherheitsmodi

| Modus              | Beschreibung                              | Einsatz         |
|-------------------|-------------------------------------------|-----------------|
| `None`             | Keine Verschlüsselung, keine Signierung   | Geschlossenes Intranet |
| `Sign`             | Signierung, keine Verschlüsselung         | Intranet        |
| `SignAndEncrypt`   | Signierung + AES-256 Verschlüsselung      | Produktiv / WAN |

SmartView OPC unterstützt `NoSecurity` und `Basic256Sha256` (konfigurierbar in `config.py`).

---

## Datenfluss: Von der SPS zum Browser

```
SPS (S7-1516)           Raspberry Pi 4B              Browser
     │                        │                          │
     │  OPC UA Read           │                          │
     │ ◄──────────────────── │  opc_client._poll_loop() │
     │  value=85.3°C          │                          │
     │ ──────────────────────►│  data_cache["temp"]=85.3 │
     │                        │                          │
     │                        │  SSE /api/stream         │
     │                        │ ─────────────────────────►
     │                        │  data: {"tags":{...}}    │
     │                        │                          │
     │                        │   EventSource.onmessage()│
     │                        │  ◄─────────────────────  │
     │                        │   renderAnalogCard()     │
     │                        │   → Fortschrittsbalken   │
     │                        │     wird aktualisiert    │
```

Latenz: SPS-Zyklus (10ms) + OPC UA Polling (1000ms) + SSE (sofort) ≈ **~1 Sekunde**

---

## Siemens S7-1516 – OPC UA Konfiguration

### TIA Portal Einstellungen

1. **Gerätekonfiguration öffnen** → CPU S7-1516 auswählen
2. **Eigenschaften → Allgemein → OPC UA** öffnen
3. **"OPC UA Server aktivieren"** ankreuzen
4. **Port**: Standard 4840 (oder anpassen)
5. **Sicherheit**: "Keine Sicherheit" oder Zertifikat auswählen
6. **DB-Variablen für OPC UA freigeben**: Rechtsklick auf Variable → "OPC UA Zugriff: Lesen"

### Node-ID Format (S7-1516)

```
ns=3;s="Datenbaustein"."Variablenname"
```

Beispiele:
| Beschreibung        | Node-ID                                    |
|--------------------|--------------------------------------------|
| Kesseltemperatur   | `ns=3;s="DB_Prozess"."Temperatur_Kessel"`  |
| Pumpe 1 Lauf       | `ns=3;s="DB_Prozess"."Pumpe1_Lauf"`        |
| Druck Leitung      | `ns=3;s="DB_Prozess"."Druck_Leitung"`      |

**Werkzeug zur Node-ID Ermittlung:** [Unified Automation UaExpert](https://www.unified-automation.com/products/development-tools/uaexpert.html) (kostenlos, Windows/Linux)

---

## Verwendete Python-Bibliotheken

| Bibliothek | Version | Zweck |
|-----------|---------|-------|
| `opcua`   | 0.98.13 | OPC UA Client (synchron, S7-kompatibel) |
| `flask`   | 3.0.3   | Web-Framework für REST API + SSE |
| `gunicorn`| 22.0.0  | Produktiv-WSGI-Server für Raspberry Pi |

---

## Industrie 4.0 Kontext

SmartView OPC implementiert die **Datenerfassungsschicht** der Industrie-4.0-Referenzarchitektur (RAMI 4.0):

```
┌─────────────────────────────────────────────┐
│  Unternehmensebene (ERP, MES, Cloud)        │ ← Nicht Teil dieses Projekts
├─────────────────────────────────────────────┤
│  Edge-/SCADA-Ebene                         │ ← SmartView OPC (Raspberry Pi)
├─────────────────────────────────────────────┤
│  Steuerungsebene (SPS)                      │ ← Siemens S7-1516
├─────────────────────────────────────────────┤
│  Feldebene (Sensoren, Aktoren)              │ ← Physische Anlage
└─────────────────────────────────────────────┘
```

Der Raspberry Pi als **Edge Device** ermöglicht:
- Lokale Verarbeitung ohne Cloud-Abhängigkeit
- Kostengünstiger Einstieg in IIoT
- Flexible Erweiterung (Cloud-Upload, MQTT, InfluxDB)
