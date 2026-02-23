# ============================================================
# history.py – CSV-Historisierung der Prozessdaten
# ============================================================
# Schreibt in regelmäßigen Abständen alle Tagwerte in eine
# CSV-Datei (data/history.csv).
#
# Die Datei kann später:
#   - im Browser über /api/history abgerufen werden
#   - mit Excel oder pandas ausgewertet werden
#   - als Nachweis für Qualitätssicherung genutzt werden
# ============================================================

import csv
import os
import threading
import time
import logging
from datetime import datetime

# Einstellungen aus der zentralen Konfigurationsdatei laden
from config import (
    HISTORY_ENABLED,
    HISTORY_FILE,
    HISTORY_INTERVAL_S,
    OPC_TAGS,
)

# Logger für diese Datei
logger = logging.getLogger(__name__)


# ============================================================
# Hauptklasse: HistoryLogger
# ============================================================

class HistoryLogger:
    """
    Speichert Prozessdaten zeitgestempelt in einer CSV-Datei.

    Lifecycle:
        logger = HistoryLogger(opc_client)
        logger.start()          # Startet Hintergrund-Logging
        logger.get_last_entries(50)  # Letzte 50 Einträge abrufen
        logger.stop()           # Logging beenden
    """

    def __init__(self, opc_client):
        """
        Args:
            opc_client: Instanz von OpcUaClient – wird verwendet, um
                        die aktuellen Werte abzufragen.
        """
        # Referenz auf den OPC UA Client
        self._opc = opc_client

        # Steuerungsflags
        self._running = False
        self._thread  = None

    # ----------------------------------------------------------
    # CSV-Datei initialisieren
    # ----------------------------------------------------------

    def _ensure_file(self):
        """
        Erstellt das Datenverzeichnis und die CSV-Datei falls noch
        nicht vorhanden. Schreibt die Kopfzeile (Spaltenüberschriften).
        """
        # Verzeichnis anlegen (z.B. "data/")
        directory = os.path.dirname(HISTORY_FILE)
        if directory:
            os.makedirs(directory, exist_ok=True)

        # Datei nur anlegen wenn noch nicht vorhanden
        if not os.path.isfile(HISTORY_FILE):
            with open(HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # Kopfzeile: erste Spalte = Zeitstempel, dann alle Tag-Namen
                headers = ["timestamp"] + list(OPC_TAGS.keys())
                writer.writerow(headers)

            logger.info(f"Neue History-Datei angelegt: {HISTORY_FILE}")

    # ----------------------------------------------------------
    # Einen Datensatz in die CSV schreiben
    # ----------------------------------------------------------

    def _write_row(self):
        """
        Holt die aktuellen Werte vom OPC UA Client und schreibt
        sie als neue Zeile in die CSV-Datei.
        """
        # Aktuelle Werte vom Cache des OPC Clients holen
        values = self._opc.get_all_values()

        if not values:
            # Noch keine Daten verfügbar (z.B. Verbindung noch nicht hergestellt)
            logger.debug("History: Keine Daten verfügbar – Schreiben übersprungen.")
            return

        # Zeile aufbauen: Zeitstempel zuerst, dann alle Werte in der
        # Reihenfolge wie sie in OPC_TAGS definiert sind
        row = [datetime.now().isoformat()]
        for tag_name in OPC_TAGS.keys():
            tag_data = values.get(tag_name)
            if tag_data is not None:
                row.append(tag_data["value"])
            else:
                row.append("")   # Leerer Eintrag wenn Wert nicht vorhanden

        # Zeile in die Datei schreiben (append-Modus)
        with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    # ----------------------------------------------------------
    # Hintergrund-Thread: Logging-Schleife
    # ----------------------------------------------------------

    def _log_loop(self):
        """
        Läuft als Hintergrundthread.
        Schreibt alle HISTORY_INTERVAL_S Sekunden einen Datensatz.
        """
        # CSV-Datei vorbereiten
        self._ensure_file()
        logger.info(
            f"History-Logging aktiv: alle {HISTORY_INTERVAL_S}s → {HISTORY_FILE}"
        )

        while self._running:
            try:
                self._write_row()
            except Exception as exc:
                logger.error(f"Fehler beim Schreiben der History: {exc}")

            # Warten bis zum nächsten Speicherintervall
            time.sleep(HISTORY_INTERVAL_S)

    # ----------------------------------------------------------
    # Historische Einträge abrufen (für API-Endpunkt)
    # ----------------------------------------------------------

    def get_last_entries(self, count=100):
        """
        Liest die letzten N Zeilen aus der CSV-Datei und gibt sie
        als Liste von Dictionaries zurück.

        Args:
            count (int): Anzahl der zurückzugebenden Einträge.

        Returns:
            list: [ { "timestamp": ..., "tag1": ..., "tag2": ... }, ... ]
        """
        if not os.path.isfile(HISTORY_FILE):
            return []   # Noch keine Datei vorhanden

        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_rows = list(reader)

            # Nur die letzten N Einträge zurückgeben
            return all_rows[-count:]

        except Exception as exc:
            logger.error(f"Fehler beim Lesen der History-Datei: {exc}")
            return []

    # ----------------------------------------------------------
    # Lifecycle: starten und stoppen
    # ----------------------------------------------------------

    def start(self):
        """
        Startet den History-Logging-Thread.
        Wenn HISTORY_ENABLED = False, passiert nichts.
        """
        if not HISTORY_ENABLED:
            logger.info("Historisierung ist deaktiviert (HISTORY_ENABLED=False).")
            return

        self._running = True
        self._thread  = threading.Thread(
            target=self._log_loop,
            name="HistoryThread",
            daemon=True,   # Thread endet automatisch mit dem Hauptprogramm
        )
        self._thread.start()
        logger.info("History-Logger gestartet.")

    def stop(self):
        """Stoppt den History-Logging-Thread."""
        self._running = False
        logger.info("History-Logger gestoppt.")
