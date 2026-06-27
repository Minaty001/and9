// ═══════════════════════════════════════════════
// JARVIS Timer Manager — countdown + alert + pause/resume
// ═══════════════════════════════════════════════

const TimerManager = (() => {
    const timers = {};
    let poller = null;
    let localInterval = null;
    let serverSyncInterval = null;

    // ── Start a timer display ─────────────────────────────────

    function startTimerDisplay(id, remaining, label) {
        timers[id] = {
            remaining: remaining,
            label: label || 'Alarm',
            startTime: Date.now(),
            duration: remaining,
            status: 'active',
            timerId: id,
        };

        const overlay = document.getElementById('timerOverlay');
        if (overlay) overlay.style.display = 'flex';

        renderTimers();
        startPolling();
        startLocalTick();
        startServerSync();
        updateButtons();
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
        const label = document.getElementById('timerLabel');
        const bar = document.getElementById('timerProgressBar');

        if (label) {
            label.textContent = t.label;
            if (t.status === 'paused') {
                label.textContent = '⏸ ' + t.label + ' (Paused)';
            }
        }

        // Update digit display
        updateDigitDisplay(t.remaining);

        if (bar && t.duration > 0) {
            const pct = (t.remaining / t.duration) * 100;
            bar.style.width = Math.max(0, pct) + '%';
        }

        updateButtons();
    }

    // ── Animated digit display ─────────────────────────────────

    function updateDigitDisplay(secs) {
        const totalSecs = Math.max(0, Math.floor(secs));
        const h = Math.floor(totalSecs / 3600);
        const m = Math.floor((totalSecs % 3600) / 60);
        const s = totalSecs % 60;

        // If hours > 0, show HH:MM:SS format using the digit spans
        const mTens = document.getElementById('timerDigitMinTens');
        const mOnes = document.getElementById('timerDigitMinOnes');
        const sTens = document.getElementById('timerDigitSecTens');
        const sOnes = document.getElementById('timerDigitSecOnes');
        const sep = document.querySelector('.timer-sep');

        if (h > 0) {
            // Show hours by prepending hour digits
            // We only have 2 digits MM:SS — use a text fallback for hours
            const display = document.getElementById('timerDisplay');
            display.textContent = `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
            // Hide digit spans
            document.querySelectorAll('.timer-digit').forEach(el => el.style.display = 'none');
            if (sep) sep.style.display = 'none';
            return;
        }

        // Show digit spans
        document.querySelectorAll('.timer-digit').forEach(el => el.style.display = 'inline');
        if (sep) sep.style.display = 'inline';

        animateDigit(mTens, Math.floor(m / 10));
        animateDigit(mOnes, m % 10);
        animateDigit(sTens, Math.floor(s / 10));
        animateDigit(sOnes, s % 10);
    }

    function animateDigit(el, newValue) {
        if (!el) return;
        const oldValue = el.textContent;
        if (oldValue === String(newValue)) return;

        // Flip animation: slide down
        el.classList.remove('digit-flip');
        // Force reflow
        void el.offsetWidth;
        el.textContent = newValue;
        el.classList.add('digit-flip');
    }

    // ── Button visibility ──────────────────────────────────────

    function updateButtons() {
        const t = getCurrentTimer();
        if (!t) return;

        const cancelBtn = document.getElementById('cancelTimerBtn');
        const pauseBtn = document.getElementById('pauseTimerBtn');
        const resumeBtn = document.getElementById('resumeTimerBtn');
        const dismissBtn = document.getElementById('dismissTimerBtn');

        if (t.status === 'paused') {
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
            if (pauseBtn) pauseBtn.style.display = 'none';
            if (resumeBtn) resumeBtn.style.display = 'inline-block';
            if (dismissBtn) dismissBtn.style.display = 'none';
        } else if (t.status === 'expired' || (t.remaining <= 0 && t.status === 'active')) {
            if (cancelBtn) cancelBtn.style.display = 'none';
            if (pauseBtn) pauseBtn.style.display = 'none';
            if (resumeBtn) resumeBtn.style.display = 'none';
            if (dismissBtn) dismissBtn.style.display = 'inline-block';
        } else {
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
            if (pauseBtn) pauseBtn.style.display = 'inline-block';
            if (resumeBtn) resumeBtn.style.display = 'none';
            if (dismissBtn) dismissBtn.style.display = 'none';
        }
    }

    function getCurrentTimer() {
        const ids = Object.keys(timers);
        if (ids.length === 0) return null;
        return timers[ids[0]];
    }

    // ── Local countdown tick ───────────────────────────────────

    function startLocalTick() {
        if (localInterval) return;
        localInterval = setInterval(() => {
            const now = Date.now();
            let changed = false;
            Object.keys(timers).forEach(id => {
                const t = timers[id];
                if (t.status === 'paused') return; // don't tick paused
                const elapsed = Math.floor((now - t.startTime) / 1000);
                t.remaining = Math.max(0, t.duration - elapsed);
                if (t.remaining === 0) changed = true;
            });
            renderTimers();
        }, 250);
    }

    // ── Server status sync (every 5s for accuracy) ─────────────

    function startServerSync() {
        if (serverSyncInterval) return;
        serverSyncInterval = setInterval(async () => {
            const t = getCurrentTimer();
            if (!t || !t.timerId) return;
            try {
                const resp = await fetch(`/api/timer/${t.timerId}`);
                if (!resp.ok) return;
                const data = await resp.json();
                if (data.status === 'paused') {
                    t.status = 'paused';
                    t.remaining = data.remaining;
                } else if (data.status === 'active') {
                    if (t.status === 'paused') {
                        // Timer was resumed on server — update
                        t.status = 'active';
                        t.startTime = Date.now();
                        t.duration = data.remaining;
                        t.remaining = data.remaining;
                    } else {
                        t.remaining = data.remaining;
                    }
                }
                renderTimers();
            } catch (e) {
                // Silently retry
            }
        }, 5000);
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
                        if (timers[alert.id]) {
                            timers[alert.id].status = 'expired';
                            timers[alert.id].remaining = 0;
                        }
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
        if (serverSyncInterval) {
            clearInterval(serverSyncInterval);
            serverSyncInterval = null;
        }
    }

    // ── Pause / Resume API ─────────────────────────────────────

    async function pauseTimer() {
        const t = getCurrentTimer();
        if (!t || !t.timerId) return;
        try {
            const resp = await fetch(`/api/timer/${t.timerId}/pause`, { method: 'POST' });
            if (!resp.ok) return;
            const data = await resp.json();
            t.status = 'paused';
            t.remaining = data.remaining;
            renderTimers();
        } catch (e) {
            // Silently retry
        }
    }

    async function resumeTimer() {
        const t = getCurrentTimer();
        if (!t || !t.timerId) return;
        try {
            const resp = await fetch(`/api/timer/${t.timerId}/resume`, { method: 'POST' });
            if (!resp.ok) return;
            const data = await resp.json();
            t.status = 'active';
            t.remaining = data.remaining;
            t.startTime = Date.now();
            t.duration = data.remaining;
            renderTimers();
        } catch (e) {
            // Silently retry
        }
    }

    // ── Alert UI ───────────────────────────────────────────────

    function showAlert(timer) {
        // Vibrate
        if (navigator.vibrate) {
            navigator.vibrate([200, 100, 200, 100, 400]);
        }

        const overlay = document.getElementById('timerOverlay');
        const display = document.getElementById('timerDisplay');
        const label = document.getElementById('timerLabel');
        const dismissBtn = document.getElementById('dismissTimerBtn');

        if (display) {
            // Restore digit spans for the alert screen
            const digitSpans = document.querySelectorAll('.timer-digit');
            if (digitSpans.length) {
                digitSpans.forEach(el => el.style.display = 'none');
                const sep = document.querySelector('.timer-sep');
                if (sep) sep.style.display = 'none';
            }
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

        const cancelBtn = document.getElementById('cancelTimerBtn');
        const pauseBtn = document.getElementById('pauseTimerBtn');
        const resumeBtn = document.getElementById('resumeTimerBtn');
        if (cancelBtn) cancelBtn.style.display = 'none';
        if (pauseBtn) pauseBtn.style.display = 'none';
        if (resumeBtn) resumeBtn.style.display = 'none';

        // TTS
        if (typeof window.speak === 'function') {
            window.speak('Time is up! ' + (timer.label || 'Alarm'));
        }

        // Audio beep
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

    async function cancelTimer() {
        const ids = Object.keys(timers);
        if (ids.length === 0) return;
        const id = parseInt(ids[0], 10);
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
        pauseTimer,
        resumeTimer,
    };
})();
