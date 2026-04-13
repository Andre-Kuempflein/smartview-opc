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
        taster_start:   { on: "AKTIV",    off: "START"     },
        schalter_stopp: { on: "EIN",      off: "SCHLÜSSEL" },
        taster_reset:   { on: "AKTIV",    off: "RESET"     },
    };

    // ── Zustandsverwaltung ────────────────────
    let previousValues  = {};
    let controlStates   = {};
    let controlConfig   = {};   // pulse/toggle-Info aus /api/config
    let isConnected     = false;
    let pollTimer       = null;
    let sending         = {};   // Verhindert Doppelklicks

    // ── DOM-Elemente ──────────────────────────
    const statusDot         = document.getElementById("status-dot");
    const statusText        = document.getElementById("status-text");
    const lastUpdate        = document.getElementById("last-update");
    const demoBadge         = document.getElementById("demo-badge");
    const alertsContainer   = document.getElementById("alerts-container");
    const alertCount        = document.getElementById("alert-count");
    const alertList         = document.getElementById("alert-list");
    const toastContainer    = document.getElementById("toast-container");


    // ═══════════════════════════════════════════
    // Konfiguration laden (einmalig beim Start)
    // ═══════════════════════════════════════════

    async function loadConfig() {
        try {
            const res  = await fetch(`${API_BASE}/api/config`);
            if (!res.ok) return;
            const data = await res.json();
            controlConfig = data.controls || {};
        } catch (err) {
            console.warn("Config konnte nicht geladen werden:", err);
        }
    }


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

            if (data.demo_mode && demoBadge) {
                demoBadge.style.display = "inline-block";
            }

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

            const badge = document.getElementById(`quality-${name}`);
            if (badge) {
                badge.textContent = data.quality || "–";
                badge.className   = "quality-badge " + (data.quality || "");
            }

            const timeEl = document.getElementById(`time-${name}`);
            if (timeEl && data.timestamp) {
                const d = new Date(data.timestamp);
                timeEl.textContent = d.toLocaleTimeString("de-DE");
            }
        }
    }

    function updateDigitalCard(name, data) {
        const indicator = document.getElementById(`indicator-${name}`);
        const label     = document.getElementById(`label-${name}`);

        if (!indicator) return;

        const isOn = !!data.value;
        indicator.classList.remove("on", "off");
        indicator.classList.add(isOn ? "on" : "off");

        if (label) {
            label.textContent = isOn ? "AKTIV" : "INAKTIV";
            label.classList.remove("on", "off");
            label.classList.add(isOn ? "on" : "off");
        }
    }

    function updateAnalogCard(name, data) {
        const valueEl = document.getElementById(`value-${name}`);
        const card    = document.getElementById(`card-${name}`);

        if (!valueEl || data.value === null || data.value === undefined) return;

        const val       = parseFloat(data.value);
        const formatted = Number.isInteger(val) ? val.toString() : val.toFixed(1);

        if (previousValues[name] !== formatted) {
            valueEl.textContent = formatted;
            valueEl.classList.remove("value-changed");
            void valueEl.offsetWidth;
            valueEl.classList.add("value-changed");
            previousValues[name] = formatted;
        }

        if (card) card.classList.remove("alert-active");
    }


    // ═══════════════════════════════════════════
    // Steuerungs-Update
    // ═══════════════════════════════════════════

    function updateControls(controls) {
        if (!controls) return;

        for (const [name, data] of Object.entries(controls)) {
            controlStates[name] = data.value;

            const indicator = document.getElementById(`indicator-${name}`);
            const label     = document.getElementById(`label-${name}`);
            const btn       = document.getElementById(`btn-${name}`);
            const card      = document.getElementById(`card-${name}`);
            const timeEl    = document.getElementById(`time-${name}`);

            const isOn = !!data.value;

            if (indicator) {
                indicator.classList.remove("on", "off");
                indicator.classList.add(isOn ? "on" : "off");
            }

            if (label) {
                label.textContent = isOn ? "EIN" : "AUS";
                label.classList.remove("on", "off");
                label.classList.add(isOn ? "on" : "off");
            }

            if (btn && !sending[name]) {
                const labels   = CONTROL_LABELS[name] || { on: "AUSSCHALTEN", off: "EINSCHALTEN" };
                const btnLabel = btn.querySelector("span");
                if (btnLabel) {
                    btnLabel.textContent = isOn ? labels.on : labels.off;
                }
                btn.classList.remove(
                    "btn-outline-success", "btn-outline-danger",
                    "btn-success", "btn-danger"
                );
                btn.classList.add(isOn ? "btn-danger" : "btn-outline-success");
            }

            if (card) {
                card.classList.remove("control-active");
                if (isOn) card.classList.add("control-active");
            }

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
        if (sending[ctrlName]) return;

        // Keine Verbindung → sofort Fehler anzeigen, nicht senden
        if (!isConnected) {
            showToast("Keine Verbindung zur SPS – Signal kann nicht gesendet werden.", "danger");
            return;
        }

        // Puls-Buttons senden immer true (Backend pulst True→False).
        // Toggle-Buttons flippen den aktuellen Zustand.
        const isPulse   = controlConfig[ctrlName]?.pulse === true;
        const newValue  = isPulse ? true : !(controlStates[ctrlName] || false);

        // Visuelles Feedback: Button deaktivieren
        const btn = document.getElementById(`btn-${ctrlName}`);
        if (btn) {
            sending[ctrlName] = true;
            btn.disabled      = true;
            btn.classList.add("sending");
            const btnLabel = btn.querySelector("span");
            if (btnLabel) btnLabel.textContent = "Sende …";
        }

        try {
            const res = await fetch(`${API_BASE}/api/control/${ctrlName}`, {
                method:  "POST",
                headers: { "Content-Type": "application/json" },
                body:    JSON.stringify({ value: newValue }),
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.description || `HTTP ${res.status}`);
            }

            const data = await res.json();
            controlStates[ctrlName] = data.value;
            updateControls({ [ctrlName]: { value: data.value, timestamp: new Date().toISOString() } });

        } catch (err) {
            console.error(`Fehler beim Steuern von '${ctrlName}':`, err);
            showToast(`Fehler: ${err.message}`, "danger");
        } finally {
            if (btn) {
                btn.disabled = !isConnected;   // nur freigeben wenn verbunden
                btn.classList.remove("sending");
                sending[ctrlName] = false;
            }
        }
    }


    // ═══════════════════════════════════════════
    // Toast-Benachrichtigungen
    // ═══════════════════════════════════════════

    function showToast(message, type = "danger") {
        if (!toastContainer) return;

        const id      = `toast-${Date.now()}`;
        const bgClass = type === "danger" ? "bg-danger" : "bg-warning text-dark";

        const el = document.createElement("div");
        el.id        = id;
        el.className = `toast align-items-center text-white ${bgClass} border-0`;
        el.setAttribute("role", "alert");
        el.setAttribute("aria-live", "assertive");
        el.innerHTML = `
            <div class="d-flex">
                <div class="toast-body fw-semibold">
                    <i class="bi bi-exclamation-triangle-fill me-2"></i>${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto"
                        data-bs-dismiss="toast" aria-label="Schließen"></button>
            </div>`;

        toastContainer.appendChild(el);
        const toast = new bootstrap.Toast(el, { delay: 5000 });
        toast.show();
        el.addEventListener("hidden.bs.toast", () => el.remove());
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

        // Steuerungs-Buttons sperren/freigeben je nach Verbindung
        document.querySelectorAll("[id^='btn-']").forEach(btn => {
            if (!sending[btn.id.replace("btn-", "")]) {
                btn.disabled = !connected;
                btn.title    = connected ? "" : "Keine Verbindung zur SPS";
            }
        });
    }

    function updateTimestamp() {
        const now = new Date();
        lastUpdate.textContent = "Aktualisiert: " + now.toLocaleTimeString("de-DE");
    }


    // ═══════════════════════════════════════════
    // Historie
    // ═══════════════════════════════════════════

    let historyTimer = null;
    const HISTORY_TAGS     = ["endlage_eingefahren", "endlage_ausgefahren", "sensor_magazin", "foerderband_status"];
    const HISTORY_POLL_MS  = 5000;

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

            const allEntries = results.flat()
                .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
                .slice(0, 50);

            if (allEntries.length === 0) {
                historyBody.innerHTML = '<tr><td colspan="3" class="text-muted text-center">Noch keine Daten verfügbar</td></tr>';
                return;
            }

            historyBody.innerHTML = allEntries.map(entry => {
                const d    = new Date(entry.timestamp);
                const time = d.toLocaleTimeString("de-DE") + "." + String(d.getMilliseconds()).padStart(3, "0");
                const displayName = entry.tag === "endlage_eingefahren" ? "Eingefahren" : "Ausgefahren";
                const val  = entry.value;
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
    document.addEventListener("DOMContentLoaded", async () => {
        await loadConfig();   // Puls/Toggle-Konfiguration vorab laden
        startPolling();

        const histCollapse = document.getElementById("history-collapse");
        const histBtn      = document.getElementById("history-toggle-btn");
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
