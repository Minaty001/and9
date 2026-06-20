// ═══════════════════════════════════════════════
// JARVIS Timer Manager — countdown + alert
// ═══════════════════════════════════════════════

const TimerManager = (() => {
    const timers = {};
    let poller = null;
    let localInterval = null;

    // ── Start a timer display ─────────────────────────────────

    function startTimerDisplay(id, remaining, label) {
        timers[id] = {
            remaining: remaining,
            label: label || 'Alarm',
            startTime: Date.now(),
            duration: remaining,
        };

        const overlay = document.getElementById('timerOverlay');
        if (overlay) overlay.style.display = 'flex';

        renderTimers();
        startPolling();
        startLocalTick();
    }

    // ── Render ─────────────────────────────────────────────────

    function renderTimers() {
        const overlay = document.getElementById('timerOverlay');
        if (!overlay) return;

        const ids = Object.keys(timers);
        if (ids.length === 0) {
            overlay.style.display = 'none';
            return;
        }

        // Show the first (most recent) timer
        const t = timers[ids[0]];
        const display = document.getElementById('timerDisplay');
        const label = document.getElementById('timerLabel');
        const bar = document.getElementById('timerProgressBar');
        if (display) display.textContent = formatTime(t.remaining);
        if (label) label.textContent = t.label;
        if (bar && t.duration > 0) {
            const pct = (t.remaining / t.duration) * 100;
            bar.style.width = Math.max(0, pct) + '%';
        }
    }

    function formatTime(secs) {
        const h = Math.floor(secs / 3600);
        const m = Math.floor((secs % 3600) / 60);
        const s = secs % 60;

        if (h > 0) {
            return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
        }
        return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }

    // ── Local countdown tick ───────────────────────────────────

    function startLocalTick() {
        if (localInterval) return;
        localInterval = setInterval(() => {
            const now = Date.now();
            let changed = false;
            Object.keys(timers).forEach(id => {
                const t = timers[id];
                const elapsed = Math.floor((now - t.startTime) / 1000);
                t.remaining = Math.max(0, t.duration - elapsed);
                if (t.remaining === 0) changed = true;
            });
            if (changed) renderTimers();
            else renderTimers();
        }, 250);
    }

    // ── Alert polling ──────────────────────────────────────────

    function startPolling() {
        if (poller) return;
        poller = setInterval(async () => {
            try {
                const resp = await fetch('/api/timer/alerts');
                const data = await resp.json();
                if (data.alerts && data.alerts.length > 0) {
                    data.alerts.forEach(alert => {
                        showAlert(alert);
                        delete timers[alert.id];
                    });
                    renderTimers();
                }
            } catch (e) {
                // Silently retry
            }
        }, 1000);
    }

    function stopPolling() {
        if (poller) {
            clearInterval(poller);
            poller = null;
        }
        if (localInterval) {
            clearInterval(localInterval);
            localInterval = null;
        }
    }

    // ── Alert UI ───────────────────────────────────────────────

    function showAlert(timer) {
        // Vibrate
        if (navigator.vibrate) {
            navigator.vibrate([200, 100, 200, 100, 400]);
        }

        // Set overlay to alert mode
        const overlay = document.getElementById('timerOverlay');
        const display = document.getElementById('timerDisplay');
        const label = document.getElementById('timerLabel');
        const dismissBtn = document.getElementById('dismissTimerBtn');

        if (display) {
            display.textContent = '⏰';
            display.className = 'timer-display alerted';
        }
        if (label) {
            label.textContent = (timer.label || 'Alarm') + ' — Time\'s up!';
            label.className = 'timer-label alerted';
        }
        if (dismissBtn) dismissBtn.style.display = 'inline-block';
        if (overlay) {
            overlay.className = 'timer-overlay alerting';
            overlay.style.display = 'flex';
        }

        // TTS alert
        if (typeof speak === 'function') {
            speak('Time is up! ' + (timer.label || 'Alarm'));
        }

        // Audio beep via Web Audio API
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.value = 880;
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.8);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.8);

            // Second beep
            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.type = 'sine';
            osc2.frequency.value = 660;
            gain2.gain.setValueAtTime(0.3, ctx.currentTime + 1.0);
            gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 1.8);
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.start(ctx.currentTime + 1.0);
            osc2.stop(ctx.currentTime + 1.8);
        } catch (e) {
            // Audio not available
        }
    }

    // ── Dismiss ────────────────────────────────────────────────

    function dismissAlert() {
        const overlay = document.getElementById('timerOverlay');
        const display = document.getElementById('timerDisplay');
        const label = document.getElementById('timerLabel');
        const dismissBtn = document.getElementById('dismissTimerBtn');

        if (display) display.className = 'timer-display';
        if (label) label.className = 'timer-label';
        if (dismissBtn) dismissBtn.style.display = 'none';
        if (overlay) {
            overlay.className = 'timer-overlay';
            overlay.style.display = 'none';
        }

        if (Object.keys(timers).length === 0) {
            stopPolling();
        }
    }

    // ── Cancel timer via API ──────────────────────────────────

    async function cancelTimer(id) {
        if (id === undefined) {
            // Cancel the first (most recent) timer
            const ids = Object.keys(timers);
            if (ids.length === 0) return;
            id = parseInt(ids[0], 10);
        }
        try {
            await fetch(`/api/timer/${id}`, { method: 'DELETE' });
        } catch (e) {}
        delete timers[id];
        if (Object.keys(timers).length === 0) {
            dismissAlert();
        } else {
            renderTimers();
        }
    }

    // ── Public API ─────────────────────────────────────────────

    return {
        startTimerDisplay,
        cancelTimer,
        dismissAlert,
        showAlert,
    };
})();
