# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════
  KONFIGURATION – SmartView OPC
  Hier trägst du die Verbindungsdaten deiner echten SPS ein.
═══════════════════════════════════════════════════════════════════
"""

import os


# ┌─────────────────────────────────────────────────────────────┐
# │  0. DEMO-MODUS                                              │
# │                                                             │
# │  Auf True setzen, um OHNE echte SPS zu testen.              │
# │  Die App simuliert dann Druckluft-Werte und erlaubt         │
# │  das Umschalten der Zylinder im Browser (ohne OPC UA).      │
# │                                                             │
# │  Für den echten Betrieb auf False setzen!                   │
# └─────────────────────────────────────────────────────────────┘

DEMO_MODE = os.environ.get("DEMO_MODE", "true").lower() == "true"


# ┌─────────────────────────────────────────────────────────────┐
# │  1. OPC UA SERVER-ADRESSE DEINER SPS                       │
# │                                                             │
# │  Format: "opc.tcp://<SPS-IP>:<PORT>"                        │
# │  Der Standard-OPC-UA-Port bei Siemens ist 4840.             │
# └─────────────────────────────────────────────────────────────┘

OPC_UA_ENDPOINT = os.environ.get(
    "OPC_UA_ENDPOINT",
    "opc.tcp://192.168.30.2:4840"
)


# ┌─────────────────────────────────────────────────────────────┐
# │  2. POLLING-INTERVALL                                       │
# │                                                             │
# │  Wie oft soll der Client Werte von der SPS lesen?           │
# │  Angabe in Millisekunden. Empfohlen: 500–2000 ms.           │
# └─────────────────────────────────────────────────────────────┘

POLLING_INTERVAL_MS = int(os.environ.get("POLLING_INTERVAL_MS", "1000"))


# ┌─────────────────────────────────────────────────────────────┐
# │  3. MODUS: POLLING ODER SUBSCRIPTION                        │
# │                                                             │
# │  "polling"      = Client fragt Werte aktiv ab (einfacher)   │
# │  "subscription" = SPS schickt Wertänderungen (effizienter)  │
# └─────────────────────────────────────────────────────────────┘

MODE = os.environ.get("OPC_MODE", "polling")


# ┌─────────────────────────────────────────────────────────────┐
# │  4. TAG-ZUORDNUNG: LESBARE SPS-VARIABLEN                    │
# │                                                             │
# │  Nur Druckluft als analoger Messwert.                       │
# │                                                             │
# │  ⚠️  Trage deine echte NodeID ein!                          │
# │      Findest du mit UaExpert oder im TIA Portal.            │
# └─────────────────────────────────────────────────────────────┘

TAG_NODES = {

    # ─── ANALOGWERT: Druckluft ────────────────────────────────
    # Ersetze die node_id mit der NodeID deiner Druckluft-Variable
    # Beispiel: 'ns=3;s="DB_Prozess"."Druckluft"'
    "druckluft": {
        "node_id": 'ns=2;i=2',  # ← HIER deine echte NodeID eintragen!
        "display_name": "Druckluft",
        "unit": "bar",
        "type": "analog",
        "min_alert": 3.0,    # Alarm wenn Wert unter 3 bar
        "max_alert": 8.0,    # Alarm wenn Wert über 8 bar
    },
}


# ┌─────────────────────────────────────────────────────────────┐
# │  5. STEUERBARE AUSGÄNGE (SCHREIBEN AUF DIE SPS)             │
# │                                                             │
# │  Hier definierst du die Zylinder und Aktoren, die           │
# │  über das Dashboard gesteuert werden können.                │
# │                                                             │
# │  Jeder Eintrag braucht:                                     │
# │    "node_id"      → Die OPC UA NodeID (zum Schreiben)       │
# │    "display_name" → Name für die Anzeige im Dashboard       │
# │    "icon"         → Bootstrap-Icon-Klasse                   │
# │                                                             │
# │  ⚠️  Trage deine echten NodeIDs ein!                        │
# └─────────────────────────────────────────────────────────────┘

CONTROL_NODES = {

    # ─── Zylinder Hoch ────────────────────────────────────────
    "zylinder_hoch": {
        "node_id": 'ns=3;s="Zylinder_Hoch"',  # ← HIER deine echte NodeID!
        "display_name": "Zylinder Hoch",
        "icon": "bi-arrow-up-circle-fill",
    },

    # ─── Zylinder Runter ──────────────────────────────────────
    "zylinder_runter": {
        "node_id": 'ns=3;s="Zylinder_Runter"',  # ← HIER deine echte NodeID!
        "display_name": "Zylinder Runter",
        "icon": "bi-arrow-down-circle-fill",
    },

    # ─── Auswerfer ────────────────────────────────────────────
    "auswerfer": {
        "node_id": 'ns=3;s="Auswerfer"',  # ← HIER deine echte NodeID!
        "display_name": "Auswerfer",
        "icon": "bi-box-arrow-right",
    },

    # ─── Luftrutsche ──────────────────────────────────────────
    "luftrutsche": {
        "node_id": 'ns=3;s="Luftrutsche"',  # ← HIER deine echte NodeID!
        "display_name": "Luftrutsche",
        "icon": "bi-wind",
    },
}


# ┌─────────────────────────────────────────────────────────────┐
# │  6. FLASK-SERVER (normalerweise nicht ändern)               │
# └─────────────────────────────────────────────────────────────┘

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))


# ┌─────────────────────────────────────────────────────────────┐
# │  7. HISTORIE (normalerweise nicht ändern)                   │
# └─────────────────────────────────────────────────────────────┘

HISTORY_MAX_LENGTH = int(os.environ.get("HISTORY_MAX_LENGTH", "500"))
