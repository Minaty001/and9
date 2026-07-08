// ═══════════════════════════════════════════════
// THE BOSS — Jarvis UI Script
// ═══════════════════════════════════════════════

'use strict';

const isAndroid = /android/i.test(navigator.userAgent);

// ── DOM refs ─────────────────────────────────────
const $ = id => document.getElementById(id);
const speakTrigger = $('speak-trigger');
const mainOrb = $('main-orb');
const clockTime = $('clock-time');
const clockDate = $('clock-date');
const statBattery = $('stat-battery');
const statMemory = $('stat-memory');
const statNetwork = $('stat-network');
const toastContainer = $('toastContainer');
const imageDisplay = $('imageDisplay');
const generatedImg = $('generatedImg');

// ═══════════════════════════════════════════════
// CLOCK — live every second
// ═══════════════════════════════════════════════

function updateClock() {
    const now = new Date();
    let hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    clockTime.textContent = `${hours}:${minutes} ${ampm}`;

    const options = { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' };
    clockDate.textContent = now.toLocaleDateString('en-US', options);

    // Update greeting based on time of day
    const greetingEl = document.querySelector('.greeting-text span');
    if (greetingEl) {
        const h = now.getHours();
        if (h < 12) greetingEl.textContent = 'Boss.';
        else if (h < 17) greetingEl.textContent = 'Boss.';
        else greetingEl.textContent = 'Boss.';
    }
}
setInterval(updateClock, 1000);
updateClock();

// ═══════════════════════════════════════════════
// SYSTEM STATS — live diagnostics
// ═══════════════════════════════════════════════

// Try to get real battery info
async function initBattery() {
    try {
        if ('getBattery' in navigator) {
            const battery = await navigator.getBattery();
            function updateBattery() {
                const level = Math.round(battery.level * 100);
                statBattery.textContent = level + '%';
            }
            updateBattery();
            battery.addEventListener('levelchange', updateBattery);
            battery.addEventListener('chargingchange', updateBattery);
        }
    } catch (e) {
        // Fallback: simulate
    }
}
initBattery();

// Memory fluctuation simulation
setInterval(() => {
    const currentMemory = Math.floor(58 + Math.random() * 8);
    statMemory.textContent = currentMemory + '%';
}, 4000);

// Battery fallback simulation (if no Battery API)
setInterval(() => {
    if (!('getBattery' in navigator)) {
        const el = statBattery;
        let val = parseInt(el.textContent);
        if (Math.random() > 0.85) {
            val = Math.max(5, val - 1);
            el.textContent = val + '%';
        }
    }
}, 5000);

// ═══════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════

function showToast(msg, type = '', duration = 3000) {
    const el = document.createElement('div');
    el.className = 'toast-msg ' + type;
    el.textContent = msg;
    toastContainer.appendChild(el);
    requestAnimationFrame(() => {
        el.classList.add('show');
        setTimeout(() => {
            el.classList.remove('show');
            setTimeout(() => el.remove(), 350);
        }, duration);
    });
}

// ═══════════════════════════════════════════════
// VOICE RECOGNITION
// ═══════════════════════════════════════════════

let isListening = false;
let isSpeaking = false;
let recognition = null;
let _ttsAudio = null;

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = !isAndroid;
    recognition.maxAlternatives = 1;
    recognition.lang = 'en-IN';

    recognition.onresult = (event) => {
        let finalTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            }
        }
        if (finalTranscript) {
            showToast('🎤 ' + finalTranscript, '', 2000);
            sendToJarvis(finalTranscript);
        }
    };

    recognition.onerror = (event) => {
        console.warn("Speech Error:", event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            isListening = false;
            setOrbState('');
            speakTrigger.textContent = "Tap to Speak";
            speakTrigger.style.color = '';
            showToast('⚠️ Microphone blocked. Allow mic in browser settings.', 'error');
        } else if (event.error === 'no-speech') {
            if (isListening && !isSpeaking) {
                setTimeout(startListening, 500);
            }
        } else if (event.error === 'aborted') {
            // Intentional
        } else {
            if (isListening && !isSpeaking) setTimeout(startListening, 300);
        }
    };

    recognition.onend = () => {
        if (isListening && !isSpeaking) {
            setTimeout(() => {
                if (isListening && !isSpeaking) {
                    try { recognition.start(); } catch (e) {}
                }
            }, isAndroid ? 350 : 120);
        }
    };
}

// ═══════════════════════════════════════════════
// ORB STATE MANAGEMENT
// ═══════════════════════════════════════════════

function setOrbState(state) {
    mainOrb.className = 'orb-container' + (state ? ' ' + state : '');
}

function startListening() {
    if (!recognition) {
        showToast('Voice not supported — use Chrome', 'error');
        return;
    }
    if (location.protocol !== 'https:' && location.hostname !== 'localhost' && location.hostname !== '127.0.0.1') {
        showToast('HTTPS required for voice', 'error');
        return;
    }
    isListening = true;
    setOrbState('listening');
    speakTrigger.textContent = "Listening...";
    speakTrigger.style.color = "#ff4444";
    try { recognition.start(); } catch (e) {}
}

function stopListening() {
    isListening = false;
    setOrbState('');
    speakTrigger.textContent = "Tap to Speak";
    speakTrigger.style.color = "";
    if (recognition) { try { recognition.stop(); } catch (e) {} }
}

function toggleListening() {
    if (isSpeaking) {
        stopSpeaking();
        return;
    }
    if (isListening) {
        stopListening();
    } else {
        startListening();
    }
}

// ═══════════════════════════════════════════════
// TTS — Server-side Edge TTS
// ═══════════════════════════════════════════════

function speak(text) {
    const cleaned = text
        .replace(/https?:\/\/\S+|www\.\S+/gi, '')
        .replace(/[#$%^&*_+{}\[\]|\\<>~`]/g, '')
        .replace(/[@:;]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    if (!cleaned) { finishSpeaking(); return; }

    if (recognition) { try { recognition.abort(); } catch (e) {} }
    if (_ttsAudio) { _ttsAudio.pause(); _ttsAudio = null; }

    isSpeaking = true;
    setOrbState('processing');
    speakTrigger.textContent = "Speaking...";
    speakTrigger.style.color = "#00ffaa";

    fetch('/api/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: cleaned }),
    })
    .then(resp => {
        if (!resp.ok) { finishSpeaking(); return null; }
        return resp.blob();
    })
    .then(blob => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        _ttsAudio = audio;
        audio.onended = () => {
            URL.revokeObjectURL(url);
            _ttsAudio = null;
            finishSpeaking();
        };
        audio.onerror = () => {
            URL.revokeObjectURL(url);
            _ttsAudio = null;
            finishSpeaking();
        };
        audio.play().catch(() => finishSpeaking());
    })
    .catch(() => finishSpeaking());
}

function stopSpeaking() {
    if (_ttsAudio) { _ttsAudio.pause(); _ttsAudio = null; }
    finishSpeaking();
}

function finishSpeaking() {
    isSpeaking = false;
    if (isListening) {
        setTimeout(startListening, isAndroid ? 500 : 200);
    } else {
        setOrbState('');
        speakTrigger.textContent = "Tap to Speak";
        speakTrigger.style.color = "";
    }
}

// ═══════════════════════════════════════════════
// SEND TO JARVIS (API call)
// ═══════════════════════════════════════════════

async function sendToJarvis(message) {
    if (!message.trim()) return;

    // Admin shortcut
    if (/admin\s*(panel|access)?$/i.test(message.trim())) {
        window.location.href = '/api/admin/panel';
        return;
    }

    // Check device control first
    if (typeof DeviceControl !== 'undefined') {
        const dr = DeviceControl.handle(message);
        if (dr) {
            const result = dr instanceof Promise ? await dr : dr;
            if (result) {
                showToast('⚡ ' + result.reply, 'success', 3000);
                if (result.speak) speak(result.speak);
                return;
            }
        }
    }

    // Stop mic while processing
    if (recognition && isListening) {
        try { recognition.abort(); } catch (e) {}
    }

    setOrbState('processing');
    speakTrigger.textContent = "Thinking...";
    speakTrigger.style.color = "#00d4ff";

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 100000);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
            signal: controller.signal,
        });
        clearTimeout(timeoutId);
        const data = await response.json();

        if (data.reply) {
            showToast('⚡ ' + data.reply.slice(0, 60) + (data.reply.length > 60 ? '...' : ''), 'success', 3000);
            speak(data.reply);
        }

        // Image display
        if (data.image_url) {
            generatedImg.src = data.image_url;
            imageDisplay.style.display = 'flex';
        }

        // YouTube link
        if (data.youtube_url) {
            window.open(data.youtube_url, '_blank');
        }

        // Timer
        if (data.metadata && data.metadata.timer) {
            const t = data.metadata.timer;
            if (typeof TimerManager !== 'undefined') {
                TimerManager.startTimerDisplay(t.id, t.remaining, t.label);
            }
        }

        if (data.error) {
            showToast('⚠️ ' + data.error, 'error');
        }

        // Device remote action
        if (data.intent || (data.metadata && data.metadata.task === 'device' && data.metadata.action && data.metadata.action !== 'none')) {
            if (typeof DeviceControl !== 'undefined' && DeviceControl.handleRemoteAction) {
                DeviceControl.handleRemoteAction(data);
            }
        }

    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            showToast('⏱️ Request timed out', 'error');
        } else {
            showToast('🔌 Connection lost', 'error');
        }
    }
}

// ═══════════════════════════════════════════════
// TAP TO SPEAK — click handler
// ═══════════════════════════════════════════════

speakTrigger.addEventListener('click', toggleListening);

// ═══════════════════════════════════════════════
// HEX BUTTON ACTIONS
// ═══════════════════════════════════════════════

const actionMap = {
    'voice': () => toggleListening(),
    'apps': () => sendToJarvis('Show me my apps'),
    'browser': () => sendToJarvis('Open browser and search'),
    'music': () => sendToJarvis('Play some music'),
    'notes': () => sendToJarvis('Show my notes'),
    'ai-chat': () => sendToJarvis('Start AI chat session'),
    'tasks': () => sendToJarvis('Show my tasks and goals'),
    'weather': () => sendToJarvis("What's the weather today?"),
    'news': () => sendToJarvis('Latest news'),
    'settings': () => { window.location.href = '/api/admin/panel'; },
    'jarvis': () => sendToJarvis('What can you do?'),
    'history': () => sendToJarvis('Show my conversation history'),
};

document.querySelectorAll('.hex-btn-wrapper').forEach(btn => {
    btn.addEventListener('click', () => {
        const action = btn.dataset.action;

        // Neon click animation splash
        const hexSvg = btn.querySelector('svg.hex-svg');
        const label = btn.querySelector('.hex-label');
        if (hexSvg) {
            hexSvg.style.fill = 'rgba(0, 240, 255, 0.4)';
            hexSvg.style.filter = 'drop-shadow(0 0 15px #00f0ff)';
            setTimeout(() => {
                hexSvg.style.fill = 'rgba(4, 18, 38, 0.7)';
                hexSvg.style.filter = 'drop-shadow(0 0 4px var(--neon-glow))';
            }, 300);
        }

        if (action && actionMap[action]) {
            actionMap[action]();
        }
    });
});

// Bottom nav items
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
        const action = item.dataset.action;
        if (action && actionMap[action]) {
            actionMap[action]();
        }
    });
});

// Center trigger button
$('center-trigger').addEventListener('click', () => {
    sendToJarvis('Home');
});

// ═══════════════════════════════════════════════
// IMAGE OVERLAY — close on tap
// ═══════════════════════════════════════════════

imageDisplay.addEventListener('click', function() {
    this.style.display = 'none';
});

// ═══════════════════════════════════════════════
// KEYBOARD / VIEWPORT (Android keyboard fix)
// ═══════════════════════════════════════════════

if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        document.body.style.height = window.visualViewport.height + 'px';
    });
}

// ═══════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════

console.log('THE BOSS UI | Voice: ' + !!recognition + ' | Android: ' + isAndroid);
showToast('⚡ SYSTEM ONLINE', 'success', 2000);
