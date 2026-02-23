# -*- coding: utf-8 -*-
"""
OPC UA Client für SmartView OPC
Unterstützt Polling- und Subscription-Modus.
Automatische Wiederverbindung bei Verbindungsverlust.
Schreib-Zugriff für Zylindersteuerung.
"""

import time
import math
import random
import threading
import logging
from datetime import datetime
from collections import deque

from backend.config import (
    OPC_UA_ENDPOINT,
    TAG_NODES,
    CONTROL_NODES,
    POLLING_INTERVAL_MS,
    MODE,
    HISTORY_MAX_LENGTH,
    DEMO_MODE,
)

logger = logging.getLogger("opc_client")


class OPCUAClient:
    """
    OPC UA Client mit Polling, Subscription und Schreib-Zugriff.
    Stellt gecachte Werte, Alerts, Historie und Steuerung bereit.
    """

    def __init__(self):
        self.endpoint = OPC_UA_ENDPOINT
        self.client = None
        self.connected = False
        self.running = False
        self.demo_mode = DEMO_MODE

        # Gecachte Werte: { tag_name: { value, timestamp, quality, ... } }
        self._values = {}
        # Alert-Zustand: { tag_name: { active, message, level } }
        self._alerts = {}
        # Historie: { tag_name: deque([ {value, timestamp} ]) }
        self._history = {}
        # Steuerungs-Zustände: { control_name: True/False }
        self._controls = {}

        self._lock = threading.Lock()
        self._thread = None
        self._demo_tick = 0

        # Initialisierung – Lesbare Tags
        for tag_name, tag_cfg in TAG_NODES.items():
            self._values[tag_name] = {
                "value": None,
                "timestamp": None,
                "quality": "unknown",
                "display_name": tag_cfg["display_name"],
                "unit": tag_cfg["unit"],
                "type": tag_cfg["type"],
            }
            self._history[tag_name] = deque(maxlen=HISTORY_MAX_LENGTH)

        # Initialisierung – Steuerbare Ausgänge
        for ctrl_name, ctrl_cfg in CONTROL_NODES.items():
            self._controls[ctrl_name] = {
                "value": False,
                "display_name": ctrl_cfg["display_name"],
                "icon": ctrl_cfg.get("icon", "bi-toggle-off"),
                "timestamp": None,
            }

    # ──────────────────────────────────────────
    # Verbindung
    # ──────────────────────────────────────────

    def connect(self):
        """Verbinde mit dem OPC UA Server."""
        if self.demo_mode:
            self.connected = True
            logger.info("DEMO-MODUS aktiv – keine echte OPC UA Verbindung.")
            return True
        try:
            from opcua import Client
            self.client = Client(self.endpoint)
            self.client.connect()
            self.connected = True
            logger.info("Verbunden mit %s", self.endpoint)
            return True
        except Exception as e:
            self.connected = False
            logger.error("Verbindungsfehler: %s", e)
            return False

    def disconnect(self):
        """Trenne die Verbindung."""
        self.running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        try:
            if self.client:
                self.client.disconnect()
        except Exception:
            pass
        self.connected = False
        logger.info("Verbindung getrennt.")

    def _reconnect(self):
        """Automatische Wiederverbindung mit Backoff."""
        wait = 2
        while self.running and not self.connected:
            logger.warning("Reconnect in %ds …", wait)
            time.sleep(wait)
            if self.connect():
                return True
            wait = min(wait * 2, 30)
        return False

    # ──────────────────────────────────────────
    # Werte lesen
    # ──────────────────────────────────────────

    def _read_all_tags(self):
        """Liest alle Tags vom OPC UA Server (oder simuliert im Demo-Modus)."""
        now = datetime.utcnow().isoformat() + "Z"

        if self.demo_mode:
            self._demo_tick += 1
            self._read_demo_values(now)
            return

        for tag_name, tag_cfg in TAG_NODES.items():
            try:
                node = self.client.get_node(tag_cfg["node_id"])
                raw_value = node.get_value()

                with self._lock:
                    self._values[tag_name]["value"] = raw_value
                    self._values[tag_name]["timestamp"] = now
                    self._values[tag_name]["quality"] = "good"

                    self._history[tag_name].append({
                        "value": raw_value,
                        "timestamp": now,
                    })

                self._check_alerts(tag_name, raw_value, tag_cfg)

            except Exception as e:
                with self._lock:
                    self._values[tag_name]["quality"] = "bad"
                logger.error("Fehler beim Lesen von '%s': %s", tag_name, e)

        # Steuerungs-Status von der SPS lesen
        for ctrl_name, ctrl_cfg in CONTROL_NODES.items():
            try:
                node = self.client.get_node(ctrl_cfg["node_id"])
                raw_value = node.get_value()
                with self._lock:
                    self._controls[ctrl_name]["value"] = bool(raw_value)
                    self._controls[ctrl_name]["timestamp"] = now
            except Exception as e:
                logger.error("Fehler beim Lesen von '%s': %s", ctrl_name, e)

    def _read_demo_values(self, now):
        """Simuliert Druckluft-Werte im Demo-Modus."""
        # Druckluft: schwankt realistisch zwischen 4 und 7 bar
        base = 5.5
        noise = random.uniform(-0.3, 0.3)
        wave = math.sin(self._demo_tick * 0.05) * 1.2
        value = round(base + wave + noise, 1)

        with self._lock:
            self._values["druckluft"]["value"] = value
            self._values["druckluft"]["timestamp"] = now
            self._values["druckluft"]["quality"] = "good"
            self._history["druckluft"].append({
                "value": value,
                "timestamp": now,
            })

        self._check_alerts("druckluft", value, TAG_NODES["druckluft"])

    def _check_alerts(self, tag_name, value, tag_cfg):
        """Prüft Grenzwerte und setzt Alerts."""
        if tag_cfg["type"] != "analog":
            return

        min_alert = tag_cfg.get("min_alert")
        max_alert = tag_cfg.get("max_alert")
        alert = None

        if max_alert is not None and value > max_alert:
            alert = {
                "active": True,
                "tag": tag_name,
                "display_name": tag_cfg["display_name"],
                "message": f"{tag_cfg['display_name']} = {value} {tag_cfg['unit']} "
                           f"(Grenzwert: {max_alert} {tag_cfg['unit']})",
                "level": "critical",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        elif min_alert is not None and value < min_alert:
            alert = {
                "active": True,
                "tag": tag_name,
                "display_name": tag_cfg["display_name"],
                "message": f"{tag_cfg['display_name']} = {value} {tag_cfg['unit']} "
                           f"(Minimum: {min_alert} {tag_cfg['unit']})",
                "level": "warning",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

        with self._lock:
            if alert:
                self._alerts[tag_name] = alert
            else:
                self._alerts.pop(tag_name, None)

    # ──────────────────────────────────────────
    # Werte schreiben (Steuerung)
    # ──────────────────────────────────────────

    def write_control(self, ctrl_name, value):
        """Schreibt einen Bool-Wert für einen Steuerungs-Ausgang.

        Args:
            ctrl_name: Name des Steuerungs-Tags (z.B. 'zylinder_hoch')
            value: True oder False

        Returns:
            True bei Erfolg, False bei Fehler
        """
        if ctrl_name not in CONTROL_NODES:
            logger.error("Unbekannter Steuerungs-Tag: '%s'", ctrl_name)
            return False

        now = datetime.utcnow().isoformat() + "Z"
        bool_value = bool(value)

        if self.demo_mode:
            # Im Demo-Modus nur intern speichern
            with self._lock:
                self._controls[ctrl_name]["value"] = bool_value
                self._controls[ctrl_name]["timestamp"] = now
            logger.info("DEMO: %s → %s", ctrl_name, "EIN" if bool_value else "AUS")
            return True

        if not self.connected:
            logger.error("Kann '%s' nicht schreiben – nicht verbunden.", ctrl_name)
            return False

        try:
            from opcua import ua
            ctrl_cfg = CONTROL_NODES[ctrl_name]
            node = self.client.get_node(ctrl_cfg["node_id"])
            node.set_value(ua.DataValue(ua.Variant(bool_value, ua.VariantType.Boolean)))

            with self._lock:
                self._controls[ctrl_name]["value"] = bool_value
                self._controls[ctrl_name]["timestamp"] = now

            logger.info("Geschrieben: %s → %s", ctrl_name, "EIN" if bool_value else "AUS")
            return True

        except Exception as e:
            logger.error("Fehler beim Schreiben von '%s': %s", ctrl_name, e)
            return False

    # ──────────────────────────────────────────
    # Polling-Modus
    # ──────────────────────────────────────────

    def _polling_loop(self):
        """Polling-Schleife: liest Werte im Intervall."""
        interval = POLLING_INTERVAL_MS / 1000.0
        while self.running:
            if not self.connected:
                self._reconnect()
                continue
            try:
                self._read_all_tags()
            except Exception as e:
                logger.error("Polling-Fehler: %s", e)
                if not self.demo_mode:
                    self.connected = False
            time.sleep(interval)

    # ──────────────────────────────────────────
    # Subscription-Modus (Bonus)
    # ──────────────────────────────────────────

    def _subscription_handler(self, node, val, data):
        """Callback für OPC UA Subscription."""
        now = datetime.utcnow().isoformat() + "Z"
        node_id_str = node.nodeid.to_string()
        for tag_name, tag_cfg in TAG_NODES.items():
            if tag_cfg["node_id"] == node_id_str:
                with self._lock:
                    self._values[tag_name]["value"] = val
                    self._values[tag_name]["timestamp"] = now
                    self._values[tag_name]["quality"] = "good"
                    self._history[tag_name].append({
                        "value": val,
                        "timestamp": now,
                    })
                self._check_alerts(tag_name, val, tag_cfg)
                break

    def _subscription_loop(self):
        """Subscription-Modus: registriert sich für Wertänderungen."""
        if self.demo_mode:
            # Im Demo-Modus einfach Polling verwenden
            self._polling_loop()
            return

        from opcua import Client
        while self.running:
            if not self.connected:
                self._reconnect()
                continue
            try:
                handler = SubHandler(self._subscription_handler)
                sub = self.client.create_subscription(
                    POLLING_INTERVAL_MS, handler
                )
                handles = []
                for tag_cfg in TAG_NODES.values():
                    node = self.client.get_node(tag_cfg["node_id"])
                    handle = sub.subscribe_data_change(node)
                    handles.append(handle)

                logger.info("Subscription aktiv für %d Tags.", len(handles))

                while self.running and self.connected:
                    time.sleep(1)

                sub.delete()
            except Exception as e:
                logger.error("Subscription-Fehler: %s", e)
                self.connected = False
                time.sleep(2)

    # ──────────────────────────────────────────
    # Start / Stopp
    # ──────────────────────────────────────────

    def start(self):
        """Startet den Client im konfigurierten Modus."""
        if self.demo_mode:
            logger.info("═══ DEMO-MODUS ═══ Keine OPC UA Verbindung.")
        if not self.connect():
            logger.warning("Erster Verbindungsversuch fehlgeschlagen – "
                           "Reconnect wird im Hintergrund versucht.")

        self.running = True
        target = self._subscription_loop if MODE == "subscription" else self._polling_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()
        logger.info("Client gestartet (Modus: %s, Demo: %s).", MODE, self.demo_mode)

    def stop(self):
        """Stoppt den Client."""
        self.disconnect()

    # ──────────────────────────────────────────
    # Öffentliche API
    # ──────────────────────────────────────────

    def get_all_values(self):
        """Alle aktuellen Werte als dict."""
        with self._lock:
            return {k: dict(v) for k, v in self._values.items()}

    def get_tag_value(self, tag_name):
        """Einzelnen Tag-Wert abfragen (oder None)."""
        with self._lock:
            entry = self._values.get(tag_name)
            return dict(entry) if entry else None

    def get_alerts(self):
        """Alle aktiven Alerts."""
        with self._lock:
            return list(self._alerts.values())

    def get_history(self, tag_name, limit=100):
        """Historische Werte eines Tags."""
        with self._lock:
            hist = self._history.get(tag_name)
            if hist is None:
                return None
            return list(hist)[-limit:]

    def get_control_states(self):
        """Alle Steuerungs-Zustände als dict."""
        with self._lock:
            return {k: dict(v) for k, v in self._controls.items()}

    def is_connected(self):
        """Verbindungsstatus."""
        return self.connected


class SubHandler:
    """OPC UA Subscription-Handler (Adapter)."""

    def __init__(self, callback):
        self._callback = callback

    def datachange_notification(self, node, val, data):
        self._callback(node, val, data)
