# -*- coding: utf-8 -*-
"""
SmartView OPC – Flask REST API
==============================
Dieser Server ist der zentrale Einstiegspunkt des Programms.

Er verbindet drei Komponenten:
  1. opc_client.py  → liest und schreibt Werte zur SPS via OPC UA
  2. history.py     → speichert Werte regelmäßig als CSV-Datei
  3. Frontend       → liefert das Web-Dashboard als statische Dateien aus

Alle Prozessdaten werden über REST-Endpunkte als JSON bereitgestellt,
damit das Dashboard sie per HTTP-Polling abrufen kann.
"""

import os
import sys
import logging
import atexit

from flask import Flask, jsonify, request, send_from_directory, abort, send_file
from flask_cors import CORS

# ── Projektverzeichnis zum Python-Suchpfad hinzufügen ──────────────────────
# Damit funktionieren Imports wie "from backend.config import ..." korrekt,
# egal von wo aus das Programm gestartet wird.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import FLASK_HOST, FLASK_PORT, TAG_NODES, CONTROL_NODES, DEMO_MODE, HISTORY_FILE
from backend.opc_client import OPCUAClient

# ── Logging-Konfiguration ───────────────────────────────────────────────────
# Gibt alle Log-Meldungen mit Uhrzeit, Modul-Name und Level aus.
# Beispiel: "12:34:56 [app] INFO  Server gestartet"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

# ── Flask-App einrichten ────────────────────────────────────────────────────
# Das Frontend-Verzeichnis wird als statisches Verzeichnis eingebunden,
# damit index.html, CSS und JavaScript direkt ausgeliefert werden.
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# CORS aktivieren: erlaubt Browser-Anfragen von anderen Adressen (z.B. Entwicklung)
CORS(app)

# ── OPC UA Client starten ───────────────────────────────────────────────────
# Verbindet sich beim Start automatisch mit der SPS und beginnt mit dem Polling.
# Wenn DEMO_MODE=true ist, werden simulierte Werte verwendet (keine echte SPS nötig).
opc = OPCUAClient()
opc.start()
atexit.register(opc.stop)   # Verbindung sauber trennen wenn das Programm endet

# ── History-Logger starten ──────────────────────────────────────────────────
# Schreibt alle HISTORY_INTERVAL_S Sekunden die aktuellen Werte in eine CSV-Datei.
from backend.history import HistoryLogger
history_logger = HistoryLogger(opc)
history_logger.start()
atexit.register(history_logger.stop)


# ════════════════════════════════════════════════════════════════════════════
# REST API – LESEN
# ════════════════════════════════════════════════════════════════════════════


@app.route("/api/data")
def api_data():
    """
    Gibt alle aktuellen Werte als JSON zurück.

    Das Dashboard ruft diesen Endpunkt alle 1,5 Sekunden auf (Polling).
    Die Antwort enthält:
      - connected:  True/False – ist die SPS gerade erreichbar?
      - demo_mode:  True/False – läuft das Programm im Simulationsmodus?
      - tags:       alle Lesevariablen (Endlagen, Sensoren, Aktoren...)
      - controls:   alle Steuervariablen (Taster, Schalter...)
    """
    values = opc.get_all_values()
    controls = opc.get_control_states()
    return jsonify({
        "connected": opc.is_connected(),
        "demo_mode": DEMO_MODE,
        "tags": values,
        "controls": controls,
    })


@app.route("/api/tags/<tag_name>")
def api_tag(tag_name):
    """
    Gibt den aktuellen Wert eines einzelnen Tags zurück.

    Beispiel: GET /api/tags/endlage_eingefahren
    → {"connected": true, "tag": "endlage_eingefahren", "data": {...}}
    """
    value = opc.get_tag_value(tag_name)
    if value is None:
        abort(404, description=f"Tag '{tag_name}' nicht gefunden.")
    return jsonify({
        "connected": opc.is_connected(),
        "tag": tag_name,
        "data": value,
    })


@app.route("/api/alerts")
def api_alerts():
    """
    Gibt alle aktiven Grenzwert-Alarme zurück.

    Ein Alarm ist aktiv, wenn ein Analogwert unter- oder überschritten wird
    (definiert in config.py unter min_alert / max_alert).
    """
    return jsonify({
        "connected": opc.is_connected(),
        "alerts": opc.get_alerts(),
    })


@app.route("/api/history/<tag_name>")
def api_history(tag_name):
    """
    Gibt die im RAM gespeicherten Verlaufswerte eines Tags zurück.

    Der In-Memory-Verlauf wird beim Neustart des Servers geleert.
    Für dauerhafte Daten → /api/download/history (CSV-Datei).

    Maximale Anzahl Einträge: konfigurierbar über HISTORY_LIMIT (Standard: 100).
    """
    limit = int(os.environ.get("HISTORY_LIMIT", "100"))
    history = opc.get_history(tag_name, limit=limit)
    if history is None:
        abort(404, description=f"Tag '{tag_name}' nicht gefunden.")
    return jsonify({
        "tag": tag_name,
        "history": history,
    })


@app.route("/api/config")
def api_config():
    """
    Gibt die Konfiguration aller Tags und Steuerungen zurück.

    Das Frontend lädt diese Informationen einmalig beim Start, um zu wissen:
      - Welche Tags gibt es? (Anzeigename, Einheit, Grenzwerte)
      - Welche Steuerungen gibt es? (Icon, Puls oder Toggle?)
    """
    config = {}
    for name, cfg in TAG_NODES.items():
        config[name] = {
            "display_name": cfg["display_name"],
            "unit": cfg.get("unit", ""),
            "type": cfg["type"],
            "min_alert": cfg.get("min_alert"),
            "max_alert": cfg.get("max_alert"),
        }
    controls = {}
    for name, cfg in CONTROL_NODES.items():
        controls[name] = {
            "display_name": cfg["display_name"],
            "icon": cfg.get("icon", "bi-toggle-off"),
            "pulse": cfg.get("pulse", False),   # True = Puls (Ein→Aus), False = Toggle
        }
    return jsonify({"tags": config, "controls": controls})


@app.route("/api/download/history")
def api_download_history():
    """
    Stellt die CSV-Historiendatei zum Herunterladen bereit.

    Die Datei liegt unter data/history.csv und wird vom history.py-Modul
    alle paar Sekunden befüllt. Sie kann z.B. mit Excel geöffnet werden.
    """
    if os.path.exists(HISTORY_FILE):
        return send_file(HISTORY_FILE, as_attachment=True)
    else:
        abort(404, description="History-Datei existiert noch nicht.")


# ════════════════════════════════════════════════════════════════════════════
# REST API – SCHREIBEN (Steuerung)
# ════════════════════════════════════════════════════════════════════════════


@app.route("/api/control/<ctrl_name>", methods=["POST"])
def api_control(ctrl_name):
    """
    Sendet ein Steuerungs-Signal an die SPS.

    Erwartet JSON-Body: {"value": true} oder {"value": false}

    Puls-Taster (taster_start, taster_reset):
      → Schreibt True zur SPS, wartet 300ms im Hintergrund, schreibt dann False.
      → Erzeugt eine steigende Flanke, die die SPS-Sequenz startet.

    Toggle-Schalter (schalter_stopp):
      → Schreibt den übergebenen Wert direkt (True oder False bleibt gesetzt).

    Rückgabe bei Erfolg:  {"success": true, "control": "...", "value": ...}
    Rückgabe bei Fehler:  HTTP 500 mit Fehlerbeschreibung
    """
    if ctrl_name not in CONTROL_NODES:
        abort(404, description=f"Steuerung '{ctrl_name}' nicht gefunden.")

    data = request.get_json(silent=True)
    if data is None or "value" not in data:
        abort(400, description="JSON mit 'value' (true/false) erwartet.")

    value = bool(data["value"])
    success = opc.write_control(ctrl_name, value)

    if not success:
        abort(500, description=f"Fehler beim Schreiben von '{ctrl_name}'. "
                               f"Verbindung zur SPS prüfen.")

    return jsonify({
        "success": True,
        "control": ctrl_name,
        "value": value,
        "display_name": CONTROL_NODES[ctrl_name]["display_name"],
    })


# ════════════════════════════════════════════════════════════════════════════
# Frontend (Statische Dateien)
# ════════════════════════════════════════════════════════════════════════════


@app.route("/")
def index():
    """Startseite: liefert das Dashboard (index.html) aus."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Liefert alle anderen statischen Dateien aus (CSS, JS, Bilder...)."""
    return send_from_directory(FRONTEND_DIR, path)


# ════════════════════════════════════════════════════════════════════════════
# Programm-Start
# ════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    mode_label = "DEMO-MODUS (keine echte SPS)" if DEMO_MODE else "LIVE-MODUS (SPS verbunden)"
    print("=" * 55)
    print("  SmartView OPC – Förderbandstation")
    print(f"  Modus: {mode_label}")
    print("=" * 55)
    print(f"  Dashboard: http://localhost:{FLASK_PORT}")
    print(f"  API:       http://localhost:{FLASK_PORT}/api/data")
    print("=" * 55)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
