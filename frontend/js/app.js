/**
 * SmartView OPC – Frontend Application
 * Polling-basierte Live-Aktualisierung der Prozessdaten
 * mit Zylindersteuerung über POST-Requests.
 */

// toggleControl muss global sein (onclick in HTML)
function toggleControl(ctrlName) {
    SmartViewApp.toggleControl(ctrlName);
}

const SmartViewApp = (() => {
    "use strict";

    // ── Konfiguration ─────────────────────────
    const API_BASE = "";
    const POLL_INTERVAL_MS = 1500;

    // Control-spezifische Labels
    const CONTROL_LABELS = {
        taster_start: { on: "SENDET...", off: "START" },
        schalter_stopp: { on: "SENDET...", off: "SCHLÜSSEL" },
        taster_reset: { on: "SENDET...", off: "RESET" },
    };

    // ── Zustandsverwaltung ────────────────────
    let previousValues = {};
    let controlStates = {};
    let isConnected = false;
    let pollTimer = null;
    let sending = {};  // Verhindert Doppelklicks

    // ── DOM-Elemente ──────────────────────────
    const statusDot = document.getElementById("status-dot");
    const statusText = document.getElementById("status-text");
    const lastUpdate = document.getElementById("last-update");
    const demoBadge = document.getElementById("demo-badge");
    const alertsContainer = document.getElementById("alerts-container");
    const alertCount = document.getElementById("alert-count");
    const alertList = document.getElementById("alert-list");


    // ═══════════════════════════════════════════
    // Datenabfrage
    // ═══════════════════════════════════════════

    async function fetchData() {
        try {
            const res = await fetch(`${API_BASE}/api/data`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            setConnectionStatus(data.connected);
            updateValues(data.tags);
            updateControls(data.controls);
            updateTimestamp();

            // Demo-Badge anzeigen
            if (data.demo_mode && demoBadge) {
                demoBadge.style.display = "inline-block";
            }

            // Alerts separat laden
            fetchAlerts();

        } catch (err) {
            console.error("Fehler beim Laden der Daten:", err);
            setConnectionStatus(false);
        }
    }

    async function fetchAlerts() {
        try {
            const res = await fetch(`${API_BASE}/api/alerts`);
            if (!res.ok) return;
            const data = await res.json();
            updateAlerts(data.alerts);
        } catch (err) {
            // Alerts sind optional
        }
    }


    // ═══════════════════════════════════════════
    // Werte-Update (Digital-Status + Analog)
    // ═══════════════════════════════════════════

    function updateValues(tags) {
        for (const [name, data] of Object.entries(tags)) {
            if (data.type === "analog") {
                updateAnalogCard(name, data);
            } else if (data.type === "digital") {
                updateDigitalCard(name, data);
            }

            // Quality-Badge
            const badge = document.getElementById(`quality-${name}`);
            if (badge) {
                badge.textContent = data.quality || "–";
                badge.className = "quality-badge " + (data.quality || "");
            }

            // Timestamp
            const timeEl = document.getElementById(`time-${name}`);
            if (timeEl && data.timestamp) {
                const d = new Date(data.timestamp);
                timeEl.textContent = d.toLocaleTimeString("de-DE");
            }
        }
    }

    function updateDigitalCard(name, data) {
        const indicator = document.getElementById(`indicator-${name}`);
        const label = document.getElementById(`label-${name}`);

        if (!indicator) return;

        const isOn = !!data.value;

        // LED-Indikator
        indicator.classList.remove("on", "off");
        indicator.classList.add(isOn ? "on" : "off");

        // Label
        if (label) {
            label.textContent = isOn ? "AKTIV" : "INAKTIV";
            label.classList.remove("on", "off");
            label.classList.add(isOn ? "on" : "off");
        }
    }

    function updateAnalogCard(name, data) {
        const valueEl = document.getElementById(`value-${name}`);
        const card = document.getElementById(`card-${name}`);

        if (!valueEl || data.value === null || data.value === undefined) return;

        const val = parseFloat(data.value);
        const formatted = Number.isInteger(val) ? val.toString() : val.toFixed(1);

        if (previousValues[name] !== formatted) {
            valueEl.textContent = formatted;
            valueEl.classList.remove("value-changed");
            void valueEl.offsetWidth;
            valueEl.classList.add("value-changed");
            previousValues[name] = formatted;
        }

        // Alert-Zustand
        if (card) {
            card.classList.remove("alert-active");
        }
    }


    // ═══════════════════════════════════════════
    // Steuerungs-Update
    // ═══════════════════════════════════════════

    function updateControls(controls) {
        if (!controls) return;

        for (const [name, data] of Object.entries(controls)) {
            controlStates[name] = data.value;

            const indicator = document.getElementById(`indicator-${name}`);
            const label = document.getElementById(`label-${name}`);
            const btn = document.getElementById(`btn-${name}`);
            const card = document.getElementById(`card-${name}`);
            const timeEl = document.getElementById(`time-${name}`);

            const isOn = !!data.value;

            // Indikator
            if (indicator) {
                indicator.classList.remove("on", "off");
                indicator.classList.add(isOn ? "on" : "off");
            }

            // Label
            if (label) {
                label.textContent = isOn ? "EIN" : "AUS";
                label.classList.remove("on", "off");
                label.classList.add(isOn ? "on" : "off");
            }

            // Button-Aussehen
            if (btn && !sending[name]) {
                const labels = CONTROL_LABELS[name] || { on: "AUSSCHALTEN", off: "EINSCHALTEN" };
                const btnLabel = btn.querySelector("span");
                if (btnLabel) {
                    btnLabel.textContent = isOn ? labels.on : labels.off;
                }
                btn.classList.remove("btn-outline-success", "btn-outline-danger", "btn-success", "btn-danger");
                if (isOn) {
                    btn.classList.add("btn-danger");
                } else {
                    btn.classList.add("btn-outline-success");
                }
            }

            // Karte hervorheben wenn aktiv
            if (card) {
                card.classList.remove("control-active");
                if (isOn) card.classList.add("control-active");
            }

            // Timestamp
            if (timeEl && data.timestamp) {
                const d = new Date(data.timestamp);
                timeEl.textContent = d.toLocaleTimeString("de-DE");
            }
        }
    }


    // ═══════════════════════════════════════════
    // Steuerung senden
    // ═══════════════════════════════════════════

    async function _toggleControl(ctrlName) {
        if (sending[ctrlName]) return;  // Doppelklick-Schutz

        const currentValue = controlStates[ctrlName] || false;
        const newValue = !currentValue;

        // Visuelles Feedback: Button deaktivieren
        const btn = document.getElementById(`btn-${ctrlName}`);
        if (btn) {
            sending[ctrlName] = true;
            btn.disabled = true;
            btn.classList.add("sending");
            const btnLabel = btn.querySelector("span");
            if (btnLabel) btnLabel.textContent = "Sende …";
        }

        try {
            const res = await fetch(`${API_BASE}/api/control/${ctrlName}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ value: newValue }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.description || `HTTP ${res.status}`);
            }

            const data = await res.json();
            controlStates[ctrlName] = data.value;

            // Sofort UI aktualisieren
            updateControls({ [ctrlName]: { value: data.value, timestamp: new Date().toISOString() } });

        } catch (err) {
            console.error(`Fehler beim Steuern von '${ctrlName}':`, err);
            // Fehler-Feedback
            if (btn) {
                btn.classList.add("btn-warning");
                setTimeout(() => btn.classList.remove("btn-warning"), 1500);
            }
        } finally {
            // Button wieder freigeben
            if (btn) {
                btn.disabled = false;
                btn.classList.remove("sending");
                sending[ctrlName] = false;
            }
        }
    }


    // ═══════════════════════════════════════════
    // Alerts
    // ═══════════════════════════════════════════

    function updateAlerts(alerts) {
        if (!alerts || alerts.length === 0) {
            alertsContainer.style.display = "none";
            document.querySelectorAll(".data-card.alert-active")
                .forEach(el => el.classList.remove("alert-active"));
            return;
        }

        alertsContainer.style.display = "block";
        alertCount.textContent = alerts.length;

        alertList.innerHTML = alerts.map(a => {
            const icon = a.level === "critical"
                ? "bi-exclamation-octagon-fill"
                : "bi-exclamation-triangle";
            const cls = a.level === "critical" ? "" : "warning";
            return `<div class="alert-item ${cls}">
                <i class="bi ${icon}"></i>
                <span>${a.message}</span>
            </div>`;
        }).join("");

        alerts.forEach(a => {
            const card = document.getElementById(`card-${a.tag}`);
            if (card) card.classList.add("alert-active");
        });
    }


    // ═══════════════════════════════════════════
    // Verbindungsstatus
    // ═══════════════════════════════════════════

    function setConnectionStatus(connected) {
        isConnected = connected;
        statusDot.classList.remove("connected", "disconnected");

        if (connected) {
            statusDot.classList.add("connected");
            statusText.textContent = "Verbunden";
        } else {
            statusDot.classList.add("disconnected");
            statusText.textContent = "Getrennt";
        }
    }

    function updateTimestamp() {
        const now = new Date();
        lastUpdate.textContent = "Aktualisiert: " + now.toLocaleTimeString("de-DE");
    }


    // ═══════════════════════════════════════════
    // Historie
    // ═══════════════════════════════════════════

    let historyTimer = null;
    const HISTORY_TAGS = ["endlage_eingefahren", "endlage_ausgefahren", "sensor_magazin", "foerderband_status"];
    const HISTORY_POLL_MS = 5000;

    async function fetchHistory() {
        const historyBody = document.getElementById("history-body");
        if (!historyBody) return;

        try {
            const results = await Promise.all(
                HISTORY_TAGS.map(tag =>
                    fetch(`${API_BASE}/api/history/${tag}`)
                        .then(r => r.ok ? r.json() : { history: [] })
                        .then(d => d.history.map(h => ({ ...h, tag })))
                )
            );

            // Alle Einträge zusammenführen und nach Zeit sortieren (neueste zuerst)
            const allEntries = results.flat()
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .slice(0, 50);

            if (allEntries.length === 0) {
                historyBody.innerHTML = '<tr><td colspan="3" class="text-muted text-center">Noch keine Daten verfügbar</td></tr>';
                return;
            }

            historyBody.innerHTML = allEntries.map(entry => {
                const d = new Date(entry.timestamp);
                const time = d.toLocaleTimeString("de-DE") + "." + String(d.getMilliseconds()).padStart(3, "0");
                const displayName = entry.tag === "endlage_eingefahren" ? "Eingefahren" : "Ausgefahren";
                const val = entry.value;
                const badge = val
                    ? '<span class="badge bg-success">AKTIV</span>'
                    : '<span class="badge bg-secondary">INAKTIV</span>';
                return `<tr><td class="text-muted">${time}</td><td>${displayName}</td><td>${badge}</td></tr>`;
            }).join("");

        } catch (err) {
            console.error("Fehler beim Laden der Historie:", err);
        }
    }


    // ═══════════════════════════════════════════
    // Polling starten
    // ═══════════════════════════════════════════

    function startPolling() {
        fetchData();
        pollTimer = setInterval(fetchData, POLL_INTERVAL_MS);
    }

    // ── Init ──────────────────────────────────
    document.addEventListener("DOMContentLoaded", () => {
        startPolling();

        // Historie: beim Aufklappen laden, beim Zuklappen stoppen
        const histCollapse = document.getElementById("history-collapse");
        const histBtn = document.getElementById("history-toggle-btn");
        if (histCollapse) {
            histCollapse.addEventListener("shown.bs.collapse", () => {
                fetchHistory();
                historyTimer = setInterval(fetchHistory, HISTORY_POLL_MS);
                if (histBtn) histBtn.innerHTML = '<i class="bi bi-chevron-up me-1"></i>Ausblenden';
            });
            histCollapse.addEventListener("hidden.bs.collapse", () => {
                clearInterval(historyTimer);
                historyTimer = null;
                if (histBtn) histBtn.innerHTML = '<i class="bi bi-chevron-down me-1"></i>Anzeigen';
            });
        }
    });

    // ── Public API ────────────────────────────
    return {
        toggleControl: _toggleControl,
    };

})();
