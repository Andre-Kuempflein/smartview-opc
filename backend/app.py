# -*- coding: utf-8 -*-
"""
SmartView OPC – Flask REST API
Stellt OPC UA Prozessdaten als JSON-Endpunkte bereit,
ermöglicht Zylindersteuerung über POST-Endpunkte
und liefert das Frontend als statische Dateien aus.
"""

import os
import sys
import logging
import atexit

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS

# ── Projektverzeichnis zum Path hinzufügen ──
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.config import FLASK_HOST, FLASK_PORT, TAG_NODES, CONTROL_NODES, DEMO_MODE
from backend.opc_client import OPCUAClient

# ── Logging ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("app")

# ── Flask-App ─────────────────────────────────
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
CORS(app)

# ── OPC UA Client ─────────────────────────────
opc = OPCUAClient()
opc.start()
atexit.register(opc.stop)


# ═══════════════════════════════════════════════
# REST API Endpunkte – LESEN
# ═══════════════════════════════════════════════


@app.route("/api/data")
def api_data():
    """Alle aktuellen Tag-Werte und Steuerungs-Zustände zurückgeben."""
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
    """Einzelnen Tag-Wert zurückgeben."""
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
    """Aktive Grenzwert-Alarme zurückgeben."""
    return jsonify({
        "connected": opc.is_connected(),
        "alerts": opc.get_alerts(),
    })


@app.route("/api/history/<tag_name>")
def api_history(tag_name):
    """Historische Werte eines Tags zurückgeben."""
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
    """Tag- und Steuerungs-Konfiguration für das Frontend."""
    config = {}
    for name, cfg in TAG_NODES.items():
        config[name] = {
            "display_name": cfg["display_name"],
            "unit": cfg["unit"],
            "type": cfg["type"],
            "min_alert": cfg.get("min_alert"),
            "max_alert": cfg.get("max_alert"),
        }
    controls = {}
    for name, cfg in CONTROL_NODES.items():
        controls[name] = {
            "display_name": cfg["display_name"],
            "icon": cfg.get("icon", "bi-toggle-off"),
        }
    return jsonify({"tags": config, "controls": controls})


# ═══════════════════════════════════════════════
# REST API Endpunkte – STEUERUNG (SCHREIBEN)
# ═══════════════════════════════════════════════


@app.route("/api/control/<ctrl_name>", methods=["POST"])
def api_control(ctrl_name):
    """Steuerungs-Ausgang schalten (EIN/AUS).

    Erwartet JSON: {"value": true} oder {"value": false}
    """
    if ctrl_name not in CONTROL_NODES:
        abort(404, description=f"Steuerung '{ctrl_name}' nicht gefunden.")

    data = request.get_json(silent=True)
    if data is None or "value" not in data:
        abort(400, description="JSON mit 'value' (true/false) erwartet.")

    value = bool(data["value"])
    success = opc.write_control(ctrl_name, value)

    if not success:
        abort(500, description=f"Fehler beim Schreiben von '{ctrl_name}'.")

    return jsonify({
        "success": True,
        "control": ctrl_name,
        "value": value,
        "display_name": CONTROL_NODES[ctrl_name]["display_name"],
    })


# ═══════════════════════════════════════════════
# Frontend (Statische Dateien)
# ═══════════════════════════════════════════════


@app.route("/")
def index():
    """Startseite des Dashboards."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    """Alle anderen statischen Dateien."""
    return send_from_directory(FRONTEND_DIR, path)


# ═══════════════════════════════════════════════
# Start
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    mode_label = "🟡 DEMO-MODUS" if DEMO_MODE else "🟢 LIVE-MODUS"
    print("=" * 55)
    print("  SmartView OPC – Flask REST API")
    print(f"  {mode_label}")
    print("=" * 55)
    print(f"  Dashboard: http://localhost:{FLASK_PORT}")
    print(f"  API:       http://localhost:{FLASK_PORT}/api/data")
    print("=" * 55)
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=False)
