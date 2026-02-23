# ============================================================
# Dockerfile – SmartView OPC
# ============================================================
# Erstellt ein Docker-Image mit dem kompletten SmartView OPC System.
#
# Build:
#   docker build -t smartview-opc .
#
# Manueller Start:
#   docker run -p 5000:5000 -v $(pwd)/data:/app/data smartview-opc
#
# Empfohlen: docker-compose (siehe docker-compose.yml)
# ============================================================

# ── Basis-Image: Python 3.11 (schlank, Debian-Basis) ───────────────────────
FROM python:3.11-slim

# Metadaten (optional aber best practice)
LABEL maintainer="SmartView OPC Team"
LABEL description="SCADA Dashboard für Siemens S7-1516 via OPC UA"
LABEL version="1.0"

# ── Arbeitsverzeichnis im Container ────────────────────────────────────────
WORKDIR /app

# ── Systempakete aktualisieren (Sicherheitspatches) ────────────────────────
# --no-install-recommends: Nur absolut notwendige Pakete
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Python-Abhängigkeiten installieren (eigener Layer für Docker-Cache) ────
# Erst nur requirements.txt kopieren, damit bei Code-Änderungen
# die Python-Pakete nicht neu installiert werden müssen.
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Quellcode kopieren ───────────────────────────────────────────────────
COPY backend/  ./backend/
COPY frontend/ ./frontend/

# ── Datenverzeichnis anlegen (CSV-History) ──────────────────────────────
# Wird auch als Volume gemountet (docker-compose.yml)
RUN mkdir -p data

# ── Nicht-Root-Benutzer für Sicherheit ───────────────────────────────────
# Best Practice: Anwendungen nicht als root laufen lassen
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# ── Port freigeben ───────────────────────────────────────────────────────
# <<< HIER BITTE Port anpassen wenn FLASK_PORT in config.py geändert wurde >>>
EXPOSE 5000

# ── Umgebungsvariablen ───────────────────────────────────────────────────
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
# PYTHONUNBUFFERED=1: Log-Ausgaben sofort anzeigen (kein Puffern)

# ── Startbefehl ──────────────────────────────────────────────────────────
# Für Produktion: gunicorn (mehrere Worker-Prozesse)
# SSE (Server-Sent Events) erfordert sync-Worker (kein eventlet/gevent)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--threads", "8", \
     "--timeout", "120", \
     "--chdir", "backend", \
     "app:app"]
