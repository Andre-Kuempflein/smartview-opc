# -*- coding: utf-8 -*-
"""
KONFIGURATION – SmartView OPC
Aktualisiert für die Förderbandstation (DB1)
"""

import os

# ============================================================
# ALLGEMEINE EINSTELLUNGEN
# ============================================================

# DEMO-Modus: Wenn True, werden Werte nur simuliert (nützlich für Entwicklung ohne echte SPS).
# In der Produktion sollte dies auf 'False' gesetzt werden.
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'

# OPC UA Verbindung: Adresse der Siemens S7-1516 SPS.
# Standardmäßig Port 4840. Beispiel: opc.tcp://192.168.6.12:4840
OPC_UA_ENDPOINT = os.environ.get(
    'OPC_UA_ENDPOINT',
    'opc.tcp://192.168.6.12:4840'
)

# Abrufintervall: Wie oft (in Millisekunden) fragt das Backend die SPS nach neuen Werten?
# Standard: 1000ms (jede Sekunde).
POLLING_INTERVAL_MS = int(os.environ.get('POLLING_INTERVAL_MS', '1000'))

# Modus: 'polling' (Backend fragt an) oder 'subscription' (SPS sendet aktiv bei Änderungen).
MODE = os.environ.get('OPC_MODE', 'polling')

# ============================================================
# VARIABLEN (TAGS) DER SPS (S7-1500)
# ============================================================

# Pfad zum Datenbaustein DB2 in der SPS (TIA Portal Namenskonvention)
# DB2 wurde angelegt, da DB1 optimierten Zugriff hatte und OPC UA nicht zuließ
DB_PATH = '"DB2"'

TAG_NODES = {
    # ─── Endlagen (Zylinder) ──────────────────────────────────
    "endlage_eingefahren": {
        "node_id": f'ns=3;s={DB_PATH}."xEndlage_Ausschiebezyl_Eingefahren"',
        "display_name": "Endlage Eingefahren",
        "type": "digital",
    },
    "endlage_ausgefahren": {
        "node_id": f'ns=3;s={DB_PATH}."xEndlage_Ausschiebezyl_Ausgefahren"',
        "display_name": "Endlage Ausgefahren",
        "type": "digital",
    },

    # ─── Sensoren ──────────────────────────────────────────────
    "sensor_magazin": {
        "node_id": f'ns=3;s={DB_PATH}."xSensor_Magazin"',
        "display_name": "Sensor Magazin",
        "type": "digital",
    },
    "sensor_lichtschranke": {
        "node_id": f'ns=3;s={DB_PATH}."xSensor_Lichtschranke"',
        "display_name": "Lichtschranke Bandende",
        "type": "digital",
    },

    # ─── Aktoren Status ────────────────────────────────────────
    "foerderband_status": {
        "node_id": f'ns=3;s={DB_PATH}."xFörderband"',
        "display_name": "Förderband läuft",
        "type": "digital",
    },
    "zylinder_einfahren": {
        "node_id": f'ns=3;s={DB_PATH}."xAusschiebezylinder_Einfahren"',
        "display_name": "Zylinder Einfahren",
        "type": "digital",
    },
    "zylinder_ausfahren": {
        "node_id": f'ns=3;s={DB_PATH}."xAusschiebezylinder_Ausfahren"',
        "display_name": "Zylinder Ausfahren",
        "type": "digital",
    },

    # ─── Lampen ────────────────────────────────────────────────
    "lampe_start": {
        "node_id": f'ns=3;s={DB_PATH}."xLampe_Start"',
        "display_name": "Lampe Start",
        "type": "digital",
    },
    "lampe_richten": {
        "node_id": f'ns=3;s={DB_PATH}."xLampe_Richten"',
        "display_name": "Lampe Richten",
        "type": "digital",
    },

    # ─── Analogwerte ───────────────────────────────────────────
    "druck": {
        "node_id": f'ns=3;s={DB_PATH}."Druck"',
        "display_name": "Systemdruck",
        "type": "analog",
        "unit": "bar",
        "min_alert": 2.0,
        "max_alert": 8.0
    },
}

# ┌─────────────────────────────────────────────────────────────┐
# │  5. STEUERBARE AUSGÄNGE (SCHREIBEN AUF DIE SPS)             │
# └─────────────────────────────────────────────────────────────┘

CONTROL_NODES = {
    "taster_start": {
        "node_id": f'ns=3;s={DB_PATH}."xTaster_Start"',
        "display_name": "Start",
        "icon": "bi-play-circle-fill",
        "pulse": True # Sende Puls (True -> False)
    },
    "schalter_stopp": {
        "node_id": f'ns=3;s={DB_PATH}."xSchalter_Stopp"',
        "display_name": "Stopp",
        "icon": "bi-stop-circle-fill",
        "pulse": False
    },
    "taster_reset": {
        "node_id": f'ns=3;s={DB_PATH}."xTaster_Reset"',
        "display_name": "Reset",
        "icon": "bi-arrow-counterclockwise",
        "pulse": True # Sende Puls
    },
}

# Tag für den Stopp-Schalter Status (Read-only)
TAG_NODES["schalter_stopp_status"] = {
    "node_id": f'ns=3;s={DB_PATH}."xSchalter_Stopp"',
    "display_name": "Not-Halt Status",
    "type": "digital"
}

# ============================================================
# WEBSERVER & FLASK KONFIGURATION
# ============================================================

# Der Host des Webservers. '0.0.0.0' bedeutet, er lauscht im gesamten Netzwerk.
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')

# Der Port des Webservers (Standard: 5000 -> erreichbar über http://IP:5000)
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))

# Maximale Anzahl an Einträgen, die im RAM (Arbeitsspeicher) für die Live-Historie-Tabelle gehalten werden.
HISTORY_MAX_LENGTH = int(os.environ.get('HISTORY_MAX_LENGTH', '500'))

# ============================================================
# DAUERHAFTE CSV-HISTORISIERUNG
# ============================================================

# CSV History Logging aktivieren/deaktivieren (Speichert Werte in einer Datei)
HISTORY_ENABLED = os.environ.get('HISTORY_ENABLED', 'true').lower() == 'true'

# Intervall: Wie oft (in Sekunden) wird eine neue Zeile in die CSV geschrieben?
HISTORY_INTERVAL_S = int(os.environ.get('HISTORY_INTERVAL_S', '5'))

# Speicherpfad der CSV-Datei (wird relativ zum Hauptverzeichnis des Projekts im Ordner 'data/' abgelegt)
import os.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HISTORY_FILE = os.path.join(PROJECT_ROOT, "data", "history.csv")
