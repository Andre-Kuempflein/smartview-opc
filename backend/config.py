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
# │  1. OPC UA SERVER-ADRESSE DEINER SPS                        │
# │                                                             │
# │  Format: "opc.tcp://<SPS-IP>:<PORT>"                        │
# │  Der Standard-OPC-UA-Port bei Siemens ist 4840.             │
# └─────────────────────────────────────────────────────────────┘

OPC_UA_ENDPOINT = os.environ.get(
    "OPC_UA_ENDPOINT",
    "opc.tcp://192.168.6.12:4840"
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
# │  Endlagen des Ausschiebezylinders (Bool-Status).            │
# │  Werden nur gelesen und als Status-LEDs angezeigt.          │
# │                                                             │
# │  NodeIDs aus DB1 der S7-1500.                               │
# └─────────────────────────────────────────────────────────────┘

TAG_NODES = {

    # ─── Endlage: Zylinder eingefahren ────────────────────────
    "endlage_eingefahren": {
        "node_id": 'ns=3;s="DB1"."xEndlage_Ausschiebezyl_Eingefahren"',
        "display_name": "Endlage Eingefahren",
        "type": "digital",
    },

    # ─── Endlage: Zylinder ausgefahren ────────────────────────
    "endlage_ausgefahren": {
        "node_id": 'ns=3;s="DB1"."xEndlage_Ausschiebezyl_Ausgefahren"',
        "display_name": "Endlage Ausgefahren",
        "type": "digital",
    },
}


# ┌─────────────────────────────────────────────────────────────┐
# │  5. STEUERBARE AUSGÄNGE (SCHREIBEN AUF DIE SPS)             │
# │                                                             │
# │  Taster für die Förderbandstation.                          │
# │  Werden per Button-Klick auf die SPS geschrieben.           │
# │                                                             │
# │  Jeder Eintrag braucht:                                     │
# │    "node_id"      → Die OPC UA NodeID (zum Schreiben)       │
# │    "display_name" → Name für die Anzeige im Dashboard       │
# │    "icon"         → Bootstrap-Icon-Klasse                   │
# │                                                             │
# │  NodeIDs aus DB1 der S7-1500.                               │
# └─────────────────────────────────────────────────────────────┘

CONTROL_NODES = {

    # ─── Taster Start ──────────────────────────────────────────
    "taster_start": {
        "node_id": 'ns=3;s="DB1"."xTaster_Start"',
        "display_name": "Start",
        "icon": "bi-play-circle-fill",
    },

    # ─── Schalter Stopp ────────────────────────────────────────
    "schalter_stopp": {
        "node_id": 'ns=3;s="DB1"."xSchalter_Stopp"',
        "display_name": "Stopp",
        "icon": "bi-stop-circle-fill",
    },

    # ─── Taster Reset ─────────────────────────────────────────
    "taster_reset": {
        "node_id": 'ns=3;s="DB1"."xTaster_Reset"',
        "display_name": "Reset",
        "icon": "bi-arrow-counterclockwise",
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
