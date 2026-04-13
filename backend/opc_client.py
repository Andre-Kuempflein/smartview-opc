# -*- coding: utf-8 -*-
"""
SmartView OPC – OPC UA Client
==============================
Diese Datei kümmert sich um die gesamte Kommunikation mit der Siemens S7-1500 SPS.

Was dieser Client macht:
  - Verbindet sich beim Start mit dem OPC UA Server der SPS
  - Liest regelmäßig (alle 1 Sekunde) alle konfigurierten Tags aus
  - Speichert die Werte in einem Cache (dict), damit die API sie schnell liefern kann
  - Erkennt Grenzwert-Überschreitungen und setzt Alarme
  - Schreibt Steuersignale (Start, Reset, Schlüsselschalter) auf die SPS
  - Verbindet sich automatisch neu wenn die Verbindung verloren geht

Im Demo-Modus (DEMO_MODE=true) werden simulierte Werte verwendet –
dann ist keine echte SPS nötig.
"""

import time
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
    OPC UA Client für die Förderbandstation.

    Stellt gecachte Werte, Alarme, Verlauf und Steuerung bereit.

    Typische Verwendung:
        client = OPCUAClient()
        client.start()                        # Verbindung aufbauen + Polling starten
        values = client.get_all_values()      # Aktuelle Werte abrufen
        client.write_control("taster_start", True)  # Signal an SPS senden
        client.stop()                         # Verbindung sauber beenden
    """

    def __init__(self):
        self.endpoint  = OPC_UA_ENDPOINT
        self.client    = None       # OPC UA Verbindungsobjekt (wird beim connect gesetzt)
        self.connected = False      # True wenn Verbindung zur SPS besteht
        self.running   = False      # True solange der Polling-Thread laufen soll
        self.demo_mode = DEMO_MODE  # True = keine echte SPS, nur simulierte Werte

        # ── Interner Datenspeicher ──────────────────────────────────────────
        # Alle Daten werden im RAM gehalten und bei jedem Poll aktualisiert.

        # Aktuelle Tag-Werte: { tag_name: { value, timestamp, quality, ... } }
        self._values = {}

        # Aktive Alarme: { tag_name: { message, level, timestamp, ... } }
        self._alerts = {}

        # Verlauf der letzten N Messwerte pro Tag
        self._history = {}

        # Zustände der Steuer-Ausgänge: { ctrl_name: { value, timestamp } }
        self._controls = {}

        # Threading-Lock: verhindert gleichzeitigen Zugriff aus mehreren Threads
        self._lock   = threading.Lock()
        self._thread = None

        # Zähler für den Demo-Modus (simuliert zeitbasierte Wertänderungen)
        self._demo_tick = 0

        # ── Initialisierung der Datenspeicher ───────────────────────────────
        # Alle Tags mit Startwerten befüllen, bevor der erste Poll läuft.

        for tag_name, tag_cfg in TAG_NODES.items():
            self._values[tag_name] = {
                "value":        None,
                "timestamp":    None,
                "quality":      "unknown",   # "good" oder "bad" nach erstem Lesen
                "display_name": tag_cfg["display_name"],
                "unit":         tag_cfg.get("unit", ""),
                "type":         tag_cfg["type"],
            }
            # Verlaufsspeicher mit begrenzter Größe (älteste Einträge werden gelöscht)
            self._history[tag_name] = deque(maxlen=HISTORY_MAX_LENGTH)

        for ctrl_name, ctrl_cfg in CONTROL_NODES.items():
            self._controls[ctrl_name] = {
                "value":        False,
                "display_name": ctrl_cfg["display_name"],
                "icon":         ctrl_cfg.get("icon", "bi-toggle-off"),
                "timestamp":    None,
            }

    # ════════════════════════════════════════════════════════════════════════
    # Verbindung aufbauen / trennen
    # ════════════════════════════════════════════════════════════════════════

    def connect(self):
        """
        Baut die Verbindung zum OPC UA Server der SPS auf.

        Im Demo-Modus wird keine echte Verbindung aufgebaut –
        der Client gilt trotzdem als "verbunden".

        Rückgabe: True bei Erfolg, False bei Fehler
        """
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
        """Trennt die Verbindung zur SPS sauber."""
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
        """
        Versucht automatisch die Verbindung wiederherzustellen.
        Wartezeit verdoppelt sich bei jedem Fehlversuch (max. 30 Sekunden).
        """
        wait = 2
        while self.running and not self.connected:
            logger.warning("Reconnect in %ds …", wait)
            time.sleep(wait)
            if self.connect():
                return True
            wait = min(wait * 2, 30)
        return False

    # ════════════════════════════════════════════════════════════════════════
    # Werte von der SPS lesen
    # ════════════════════════════════════════════════════════════════════════

    def _read_all_tags(self):
        """
        Liest alle konfigurierten Tags in einem Durchgang von der SPS.
        Im Demo-Modus werden simulierte Werte verwendet.

        Bei einem Lesefehler eines einzelnen Tags wird dieser Tag auf
        quality="bad" gesetzt, der Rest wird normal weitergepolt.
        """
        now = datetime.utcnow().isoformat() + "Z"

        if self.demo_mode:
            self._demo_tick += 1
            self._read_demo_values(now)
            return

        # ── Alle Lese-Tags abfragen ─────────────────────────────────────────
        for tag_name, tag_cfg in TAG_NODES.items():
            try:
                node      = self.client.get_node(tag_cfg["node_id"])
                raw_value = node.get_value()

                with self._lock:
                    self._values[tag_name]["value"]     = raw_value
                    self._values[tag_name]["timestamp"] = now
                    self._values[tag_name]["quality"]   = "good"
                    self._history[tag_name].append({
                        "value":     raw_value,
                        "timestamp": now,
                    })

                self._check_alerts(tag_name, raw_value, tag_cfg)

            except Exception as e:
                with self._lock:
                    self._values[tag_name]["quality"] = "bad"
                logger.error("Fehler beim Lesen von '%s': %s", tag_name, e)

        # ── Steuerungs-Zustände von der SPS zurücklesen ─────────────────────
        # Damit das Dashboard sieht ob z.B. der Schlüsselschalter aktiv ist.
        for ctrl_name, ctrl_cfg in CONTROL_NODES.items():
            try:
                node      = self.client.get_node(ctrl_cfg["node_id"])
                raw_value = node.get_value()
                with self._lock:
                    self._controls[ctrl_name]["value"]     = bool(raw_value)
                    self._controls[ctrl_name]["timestamp"] = now
            except Exception as e:
                logger.error("Fehler beim Lesen von '%s': %s", ctrl_name, e)

    def _read_demo_values(self, now):
        """
        Simuliert Endlagen-Wechsel im Demo-Modus.
        Der Zylinder wechselt alle ~5 Sekunden zwischen ein- und ausgefahren.
        """
        eingefahren = (self._demo_tick // 5) % 2 == 0
        ausgefahren = not eingefahren

        with self._lock:
            self._values["endlage_eingefahren"]["value"]     = eingefahren
            self._values["endlage_eingefahren"]["timestamp"] = now
            self._values["endlage_eingefahren"]["quality"]   = "good"
            self._history["endlage_eingefahren"].append({"value": eingefahren, "timestamp": now})

            self._values["endlage_ausgefahren"]["value"]     = ausgefahren
            self._values["endlage_ausgefahren"]["timestamp"] = now
            self._values["endlage_ausgefahren"]["quality"]   = "good"
            self._history["endlage_ausgefahren"].append({"value": ausgefahren, "timestamp": now})

    def _check_alerts(self, tag_name, value, tag_cfg):
        """
        Prüft ob ein Analogwert einen Grenzwert über- oder unterschritten hat.
        Digitale Tags werden nicht geprüft.

        Bei Überschreitung wird ein Alarm-Eintrag gesetzt (sichtbar im Dashboard).
        Bei Rückkehr in den Normalbereich wird der Alarm automatisch gelöscht.
        """
        if tag_cfg["type"] != "analog":
            return

        min_alert = tag_cfg.get("min_alert")
        max_alert = tag_cfg.get("max_alert")
        alert     = None

        if max_alert is not None and value > max_alert:
            alert = {
                "active":       True,
                "tag":          tag_name,
                "display_name": tag_cfg["display_name"],
                "message":      f"{tag_cfg['display_name']} = {value} {tag_cfg['unit']} "
                                f"(Grenzwert: {max_alert} {tag_cfg['unit']})",
                "level":        "critical",
                "timestamp":    datetime.utcnow().isoformat() + "Z",
            }
        elif min_alert is not None and value < min_alert:
            alert = {
                "active":       True,
                "tag":          tag_name,
                "display_name": tag_cfg["display_name"],
                "message":      f"{tag_cfg['display_name']} = {value} {tag_cfg['unit']} "
                                f"(Minimum: {min_alert} {tag_cfg['unit']})",
                "level":        "warning",
                "timestamp":    datetime.utcnow().isoformat() + "Z",
            }

        with self._lock:
            if alert:
                self._alerts[tag_name] = alert
            else:
                self._alerts.pop(tag_name, None)   # Alarm löschen wenn Wert normal

    # ════════════════════════════════════════════════════════════════════════
    # Werte auf die SPS schreiben (Steuerung)
    # ════════════════════════════════════════════════════════════════════════

    def write_control(self, ctrl_name, value):
        """
        Schreibt ein Steuerungs-Signal auf die SPS.

        Puls-Taster (pulse=True in config.py):
          → Schreibt True synchron (Fehler werden sofort erkannt).
          → Schreibt False nach 300ms in einem Hintergrund-Thread,
            damit der HTTP-Request nicht blockiert wird.
          → Erzeugt eine steigende Flanke: die SPS-Sequenz startet.

        Toggle-Schalter (pulse=False):
          → Schreibt den übergebenen Wert direkt (bleibt gesetzt bis geändert).

        Im Demo-Modus wird nur der interne Cache aktualisiert.

        Args:
            ctrl_name: Name der Steuerung (z.B. 'taster_start')
            value:     True oder False

        Rückgabe: True bei Erfolg, False bei Fehler
        """
        if ctrl_name not in CONTROL_NODES:
            logger.error("Unbekannter Steuerungs-Tag: '%s'", ctrl_name)
            return False

        now        = datetime.utcnow().isoformat() + "Z"
        bool_value = bool(value)

        # ── Demo-Modus: nur intern speichern, nichts senden ─────────────────
        if self.demo_mode:
            with self._lock:
                self._controls[ctrl_name]["value"]     = bool_value
                self._controls[ctrl_name]["timestamp"] = now
            logger.info("DEMO: %s → %s", ctrl_name, "EIN" if bool_value else "AUS")
            return True

        # ── Prüfen ob Verbindung besteht ────────────────────────────────────
        if not self.connected:
            logger.error("Kann '%s' nicht schreiben – nicht verbunden.", ctrl_name)
            return False

        try:
            from opcua import ua
            ctrl_cfg = CONTROL_NODES[ctrl_name]
            node     = self.client.get_node(ctrl_cfg["node_id"])

            if ctrl_cfg.get("pulse"):
                # ── Puls-Modus: True senden, dann nach 300ms False ──────────
                # True wird synchron gesendet: schlägt es fehl, gibt die Funktion
                # sofort False zurück und der API-Endpunkt antwortet mit HTTP 500.
                logger.info("Sende Puls an '%s' (True → False nach 300ms)", ctrl_name)
                node.set_value(ua.DataValue(ua.Variant(True, ua.VariantType.Boolean)))

                # False-Reset im Hintergrund: Flask blockiert nicht 300ms
                def _reset_pulse(n=node, cn=ctrl_name):
                    time.sleep(0.3)
                    try:
                        n.set_value(ua.DataValue(ua.Variant(False, ua.VariantType.Boolean)))
                        logger.info("Puls-Reset OK: %s", cn)
                    except Exception as ex:
                        logger.error("Puls-Reset-Fehler '%s': %s", cn, ex)

                threading.Thread(target=_reset_pulse, daemon=True).start()

                with self._lock:
                    self._controls[ctrl_name]["value"]     = False
                    self._controls[ctrl_name]["timestamp"] = now
                return True

            else:
                # ── Toggle-Modus: Wert direkt schreiben und halten ──────────
                node.set_value(ua.DataValue(ua.Variant(bool_value, ua.VariantType.Boolean)))
                with self._lock:
                    self._controls[ctrl_name]["value"]     = bool_value
                    self._controls[ctrl_name]["timestamp"] = now
                logger.info("Geschrieben: %s → %s", ctrl_name, "EIN" if bool_value else "AUS")
                return True

        except Exception as e:
            logger.error("Fehler beim Schreiben von '%s': %s", ctrl_name, e)
            return False

    # ════════════════════════════════════════════════════════════════════════
    # Polling-Schleife
    # ════════════════════════════════════════════════════════════════════════

    def _polling_loop(self):
        """
        Läuft als Hintergrund-Thread.
        Fragt alle POLLING_INTERVAL_MS Millisekunden die SPS nach neuen Werten.
        Bei Verbindungsverlust wird automatisch reconnect versucht.
        """
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
                    self.connected = False   # Verbindung als verloren markieren → Reconnect
            time.sleep(interval)

    # ════════════════════════════════════════════════════════════════════════
    # Subscription-Modus (alternative zu Polling)
    # ════════════════════════════════════════════════════════════════════════

    def _subscription_handler(self, node, val, data):
        """
        Callback-Funktion für den Subscription-Modus.
        Wird automatisch aufgerufen sobald die SPS einen neuen Wert sendet.
        """
        now        = datetime.utcnow().isoformat() + "Z"
        node_id_str = node.nodeid.to_string()
        for tag_name, tag_cfg in TAG_NODES.items():
            if tag_cfg["node_id"] == node_id_str:
                with self._lock:
                    self._values[tag_name]["value"]     = val
                    self._values[tag_name]["timestamp"] = now
                    self._values[tag_name]["quality"]   = "good"
                    self._history[tag_name].append({"value": val, "timestamp": now})
                self._check_alerts(tag_name, val, tag_cfg)
                break

    def _subscription_loop(self):
        """
        Subscription-Modus: Die SPS sendet aktiv bei jeder Wertänderung.
        Vorteil gegenüber Polling: geringere Netzwerklast, schnellere Reaktion.
        Im Demo-Modus wird stattdessen die normale Polling-Schleife genutzt.
        """
        if self.demo_mode:
            self._polling_loop()
            return

        from opcua import Client
        while self.running:
            if not self.connected:
                self._reconnect()
                continue
            try:
                handler = SubHandler(self._subscription_handler)
                sub     = self.client.create_subscription(POLLING_INTERVAL_MS, handler)
                handles = []
                for tag_cfg in TAG_NODES.values():
                    node   = self.client.get_node(tag_cfg["node_id"])
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

    # ════════════════════════════════════════════════════════════════════════
    # Start / Stopp
    # ════════════════════════════════════════════════════════════════════════

    def start(self):
        """
        Startet den OPC UA Client:
          1. Verbindung zur SPS aufbauen (oder Demo-Modus aktivieren)
          2. Polling-/Subscription-Thread im Hintergrund starten
        """
        if not self.connect():
            logger.warning("Erster Verbindungsversuch fehlgeschlagen – "
                           "Reconnect wird im Hintergrund versucht.")

        self.running = True
        target = self._subscription_loop if MODE == "subscription" else self._polling_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()
        logger.info("Client gestartet (Modus: %s, Demo: %s).", MODE, self.demo_mode)

    def stop(self):
        """Stoppt den Client und trennt die Verbindung zur SPS."""
        self.disconnect()

    # ════════════════════════════════════════════════════════════════════════
    # Öffentliche Zugriffsmethoden (für app.py und history.py)
    # ════════════════════════════════════════════════════════════════════════

    def get_all_values(self):
        """Gibt alle aktuellen Tag-Werte als Dictionary zurück (thread-sicher)."""
        with self._lock:
            return {k: dict(v) for k, v in self._values.items()}

    def get_tag_value(self, tag_name):
        """Gibt den Wert eines einzelnen Tags zurück, oder None wenn nicht gefunden."""
        with self._lock:
            entry = self._values.get(tag_name)
            return dict(entry) if entry else None

    def get_alerts(self):
        """Gibt alle aktiven Alarme als Liste zurück."""
        with self._lock:
            return list(self._alerts.values())

    def get_history(self, tag_name, limit=100):
        """
        Gibt die letzten N gespeicherten Werte eines Tags zurück.
        Rückgabe: Liste mit {value, timestamp} Einträgen, oder None wenn Tag unbekannt.
        """
        with self._lock:
            hist = self._history.get(tag_name)
            if hist is None:
                return None
            return list(hist)[-limit:]

    def get_control_states(self):
        """Gibt die aktuellen Zustände aller Steuerungs-Ausgänge zurück."""
        with self._lock:
            return {k: dict(v) for k, v in self._controls.items()}

    def is_connected(self):
        """Gibt True zurück wenn die Verbindung zur SPS aktiv ist."""
        return self.connected


class SubHandler:
    """
    Adapter-Klasse für den OPC UA Subscription-Modus.
    Leitet eingehende Wertänderungen an die Callback-Funktion des Clients weiter.
    """

    def __init__(self, callback):
        self._callback = callback

    def datachange_notification(self, node, val, data):
        self._callback(node, val, data)
