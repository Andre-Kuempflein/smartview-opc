# -*- coding: utf-8 -*-
"""
SmartView OPC – Zentrale Konfiguration
=======================================
Alle Einstellungen des Systems befinden sich in dieser Datei.

Hier werden festgelegt:
  - OPC UA Verbindung zur Siemens S7-1500
  - Welche Variablen (Tags) von der SPS gelesen werden
  - Welche Variablen auf die SPS geschrieben werden können (Steuerung)
  - Webserver-Einstellungen
  - CSV-Historisierungseinstellungen

Umgebungsvariablen überschreiben die Standardwerte (nützlich für Docker/Deployment).
"""

import os
import os.path

# ════════════════════════════════════════════════════════════════════════════
# ALLGEMEINE EINSTELLUNGEN
# ════════════════════════════════════════════════════════════════════════════

# Demo-Modus: Wenn True, werden Werte nur simuliert – keine echte SPS nötig.
# Nützlich für Entwicklung oder Präsentation ohne Anlagenanbindung.
# Aktivieren mit: export DEMO_MODE=true (Linux) oder set DEMO_MODE=true (Windows)
DEMO_MODE = os.environ.get('DEMO_MODE', 'false').lower() == 'true'

# OPC UA Verbindungsadresse der Siemens S7-1500 SPS.
# Format: opc.tcp://<IP-Adresse>:<Port>
# Standardport für OPC UA: 4840
OPC_UA_ENDPOINT = os.environ.get(
    'OPC_UA_ENDPOINT',
    'opc.tcp://192.168.6.12:4840'
)

# Polling-Intervall: Wie oft (in Millisekunden) werden neue Werte von der SPS abgerufen?
# 1000ms = jede Sekunde. Kleinere Werte erhöhen die Aktualität, belasten aber das Netzwerk.
POLLING_INTERVAL_MS = int(os.environ.get('POLLING_INTERVAL_MS', '1000'))

# Betriebsmodus des OPC UA Clients:
#   'polling'      → Raspberry Pi fragt die SPS aktiv an (Standard, einfacher)
#   'subscription' → SPS sendet Werte aktiv bei Änderung (effizienter, aber komplexer)
MODE = os.environ.get('OPC_MODE', 'polling')

# ════════════════════════════════════════════════════════════════════════════
# VARIABLEN-DEFINITIONEN (TAGS)
# ════════════════════════════════════════════════════════════════════════════

# Datenbaustein-Pfad in der SPS (TIA Portal Namenskonvention).
# Alle Variablen der Förderbandstation befinden sich in diesem Baustein.
DB_PATH = '"Richten/Automatikbetrieb_Förderbandstation_DB"'

# TAG_NODES: Variablen die nur GELESEN werden (Sensoren, Status, Messwerte)
# Aufbau jedes Eintrags:
#   node_id:      eindeutige Adresse der Variable im OPC UA Server
#   display_name: Anzeigename im Dashboard
#   type:         "digital" (Bool: Ein/Aus) oder "analog" (Zahl mit Einheit)
#   unit:         Einheit für Analogwerte (z.B. "bar", "°C")
#   min_alert:    Alarm wenn Wert UNTER diesem Grenzwert liegt
#   max_alert:    Alarm wenn Wert ÜBER diesem Grenzwert liegt
TAG_NODES = {

    # ── Endlagen des Ausschiebe-Zylinders ────────────────────────────────
    # Zeigen an ob der Zylinder vollständig ein- oder ausgefahren ist.
    "endlage_eingefahren": {
        "node_id":      f'ns=3;s={DB_PATH}."xEndlage_Ausschiebezyl_Eingefahren"',
        "display_name": "Endlage Eingefahren",
        "type":         "digital",
    },
    "endlage_ausgefahren": {
        "node_id":      f'ns=3;s={DB_PATH}."xEndlage_Ausschiebezyl_Ausgefahren"',
        "display_name": "Endlage Ausgefahren",
        "type":         "digital",
    },

    # ── Sensoren ──────────────────────────────────────────────────────────
    # Magazin-Sensor: True wenn Werkstücke im Magazin vorhanden sind.
    "sensor_magazin": {
        "node_id":      f'ns=3;s={DB_PATH}."xSensor_Magazin"',
        "display_name": "Sensor Magazin",
        "type":         "digital",
    },
    # Lichtschranke am Bandende: True wenn der Strahl unterbrochen ist (Werkstück erkannt).
    "sensor_lichtschranke": {
        "node_id":      f'ns=3;s={DB_PATH}."xSensor_Lichtschranke"',
        "display_name": "Lichtschranke Bandende",
        "type":         "digital",
    },

    # ── Status der Aktoren (Rückmeldung von der SPS) ──────────────────────
    # Zeigen an ob das Förderband läuft bzw. der Zylinder aktiv ist.
    "foerderband_status": {
        "node_id":      f'ns=3;s={DB_PATH}."xFörderband"',
        "display_name": "Förderband läuft",
        "type":         "digital",
    },
    "zylinder_einfahren": {
        "node_id":      f'ns=3;s={DB_PATH}."xAusschiebezylinder_Einfahren"',
        "display_name": "Zylinder Einfahren",
        "type":         "digital",
    },
    "zylinder_ausfahren": {
        "node_id":      f'ns=3;s={DB_PATH}."xAusschiebezylinder_Ausfahren"',
        "display_name": "Zylinder Ausfahren",
        "type":         "digital",
    },

    # ── Signallampen ──────────────────────────────────────────────────────
    # Zeigen den aktuellen Betriebszustand an (wird von der SPS gesetzt).
    "lampe_start": {
        "node_id":      f'ns=3;s={DB_PATH}."xLampe_Start"',
        "display_name": "Lampe Start",
        "type":         "digital",
    },
    "lampe_richten": {
        "node_id":      f'ns=3;s={DB_PATH}."xLampe_Richten"',
        "display_name": "Lampe Richten",
        "type":         "digital",
    },

    # ── Analogwert ────────────────────────────────────────────────────────
    # HINWEIS: Nicht funktionsfähig – das IO-Link-Modul ist defekt.
    # Mit Lehrer abgesprochen und freigegeben (siehe CHANGELOG.md v2.2.0).
    "druck": {
        "node_id":      f'ns=3;s={DB_PATH}."Druck"',
        "display_name": "Systemdruck",
        "type":         "analog",
        "unit":         "bar",
        "min_alert":    2.0,   # Alarm wenn Druck unter 2 bar fällt
        "max_alert":    8.0,   # Alarm wenn Druck über 8 bar steigt
    },
}

# ── Schlüsselschalter als Lese-Tag zusätzlich verfügbar machen ─────────────
# Damit sein Status im Dashboard als Indikator angezeigt werden kann
# (zusätzlich zur Steuerung über CONTROL_NODES).
TAG_NODES["schalter_stopp_status"] = {
    "node_id":      f'ns=3;s={DB_PATH}."xSchalter_Stopp"',
    "display_name": "Schlüsselschalter Status",
    "type":         "digital",
}

# ════════════════════════════════════════════════════════════════════════════
# STEUERBARE AUSGÄNGE (SCHREIBEN AUF DIE SPS)
# ════════════════════════════════════════════════════════════════════════════

# CONTROL_NODES: Variablen die GESCHRIEBEN werden können (Taster, Schalter)
# Aufbau jedes Eintrags:
#   node_id:      Adresse der Variable im OPC UA Server
#   display_name: Anzeigename im Dashboard
#   icon:         Bootstrap-Icon für den Button (https://icons.getbootstrap.com)
#   pulse:        True  = Puls-Taster (schreibt True, dann nach 300ms automatisch False)
#                 False = Toggle-Schalter (hält den gesetzten Wert)
CONTROL_NODES = {

    # Start-Taster: Puls – löst eine steigende Flanke in der SPS aus.
    # Die SPS erkennt den Flankenwechsel (R_TRIG) und startet die Sequenz.
    "taster_start": {
        "node_id":      f'ns=3;s={DB_PATH}."xTaster_Start"',
        "display_name": "Start",
        "icon":         "bi-play-circle-fill",
        "pulse":        True,
    },

    # Schlüsselschalter: Toggle – bleibt auf dem gesetzten Wert.
    # True = Anlage freigegeben, False = Anlage gesperrt.
    "schalter_stopp": {
        "node_id":      f'ns=3;s={DB_PATH}."xSchalter_Stopp"',
        "display_name": "Schlüsselschalter",
        "icon":         "bi-stop-circle-fill",
        "pulse":        False,
    },

    # Reset-Taster: Puls – fährt den Zylinder zurück in die Grundstellung.
    "taster_reset": {
        "node_id":      f'ns=3;s={DB_PATH}."xTaster_Reset"',
        "display_name": "Reset",
        "icon":         "bi-arrow-counterclockwise",
        "pulse":        True,
    },
}

# ════════════════════════════════════════════════════════════════════════════
# WEBSERVER-KONFIGURATION
# ════════════════════════════════════════════════════════════════════════════

# Host: '0.0.0.0' bedeutet der Server ist im gesamten Netzwerk erreichbar.
# Zum Einschränken auf lokalen Zugriff: '127.0.0.1'
FLASK_HOST = os.environ.get('FLASK_HOST', '0.0.0.0')

# Port: Das Dashboard ist erreichbar unter http://<IP>:5000
FLASK_PORT = int(os.environ.get('FLASK_PORT', '5000'))

# Maximale Anzahl an Verlaufswerten die pro Tag im RAM gehalten werden.
# Ältere Werte werden automatisch gelöscht (FIFO-Prinzip).
HISTORY_MAX_LENGTH = int(os.environ.get('HISTORY_MAX_LENGTH', '500'))

# ════════════════════════════════════════════════════════════════════════════
# CSV-HISTORISIERUNG
# ════════════════════════════════════════════════════════════════════════════

# CSV-Logging aktivieren oder deaktivieren.
HISTORY_ENABLED = os.environ.get('HISTORY_ENABLED', 'true').lower() == 'true'

# Wie oft (in Sekunden) wird eine neue Zeile in die CSV-Datei geschrieben?
# 5 = alle 5 Sekunden ein neuer Datensatz.
HISTORY_INTERVAL_S = int(os.environ.get('HISTORY_INTERVAL_S', '5'))

# Pfad zur CSV-Datei (relativ zum Projektstamm-Verzeichnis).
# Wird automatisch erstellt wenn noch nicht vorhanden.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HISTORY_FILE = os.path.join(PROJECT_ROOT, "data", "history.csv")
