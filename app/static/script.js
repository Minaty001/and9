// ═══════════════════════════════════════════════
// JARVIS UI — Android-Optimized Voice + Text
// Voice fixes: en-IN lang, visible mic permission error,
//              proper restart loop, Hinglish TTS support
// ═══════════════════════════════════════════════

const canvas = document.getElementById("particles");
const statusText = document.getElementById("statusText");
const hintText = document.getElementById("hintText");
const voiceTrigger = document.getElementById("voiceTrigger");
const transcriptText = document.getElementById("transcriptText");
const responseText = document.getElementById("responseText");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");

// ══════════════ Device Detection ══════════════
const isAndroid = /android/i.test(navigator.userAgent);
const isIOS     = /ipad|iphone|ipod/i.test(navigator.userAgent);
const isMobile  = /mobile|tablet|android/i.test(navigator.userAgent);

// ══════════════ Canvas Setup ══════════════

function setupCanvas(canvasElement) {
    const rect = canvasElement.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvasElement.width = rect.width * dpr;
    canvasElement.height = rect.height * dpr;
    const ctx = canvasElement.getContext("2d");
    ctx.scale(dpr, dpr);
    return { ctx, width: rect.width, height: rect.height };
}

let { ctx, width, height } = setupCanvas(canvas);
let centerX = width / 2;
let centerY = height / 2;

const count = isMobile ? 80 : 150;
const baseRadius = width * 0.35;
const particles = [];

for (let i = 0; i < count; i++) {
    particles.push({
        angle: Math.random() * Math.PI * 2,
        radius: baseRadius + Math.random() * (width * 0.1),
        speed: 0.001 + Math.random() * 0.004,
        size: 1 + Math.random() * 2
    });
}

function animate() {
    ctx.clearRect(0, 0, width, height);
    particles.forEach(p => {
        p.angle += p.speed;
        const x = centerX + p.radius * Math.cos(p.angle);
        const y = centerY + p.radius * Math.sin(p.angle);
        const depth = Math.sin(p.angle);
        const opacity = 0.2 + (depth + 1) / 2;
        ctx.fillStyle = `rgba(255,165,0,${opacity * 0.7})`;
        ctx.beginPath();
        ctx.arc(x, y, p.size, 0, Math.PI * 2);
        ctx.fill();
    });
    requestAnimationFrame(animate);
}

// ══════════════ Haptic Feedback ══════════════

function vibrate(pattern) {
    if (navigator.vibrate) navigator.vibrate(pattern);
}

// ══════════════ Screen Wake Lock ══════════════

let wakeLock = null;

async function requestWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request('screen');
            wakeLock.addEventListener('release', () => { wakeLock = null; });
        }
    } catch (e) {}
}

function releaseWakeLock() {
    if (wakeLock) { wakeLock.release(); wakeLock = null; }
}

// ══════════════ Voice + Chat State ══════════════

let isListening = false;
let isSpeaking  = false;
let recognition = null;
let _ttsAudio   = null; // current HTMLAudioElement

// ══════════════ Speech Recognition Setup ══════════════

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous      = false;
    recognition.interimResults  = !isAndroid; // Android interim = buggy
    recognition.maxAlternatives = 1;

    // ── CRITICAL FIX: use en-IN for Hinglish support ──────────
    // 'en-US' rejects Indian accents and Hindi words.
    // 'en-IN' (Indian English) accepts Hinglish naturally on Chrome/Android.
    recognition.lang = 'en-IN';

    recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript   = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const t = event.results[i][0].transcript;
            if (event.results[i].isFinal) finalTranscript += t;
            else interimTranscript += t;
        }

        if (interimTranscript) {
            transcriptText.textContent = '🎤 ' + interimTranscript;
            transcriptText.style.opacity = '0.6';
        }

        if (finalTranscript) {
            transcriptText.textContent = '🎤 ' + finalTranscript;
            transcriptText.style.opacity = '1';
            sendToJarvis(finalTranscript);
        }
    };

    recognition.onerror = (event) => {
        console.warn("Speech Error:", event.error);

        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            // ── VISIBLE ERROR — previously this was silent ──
            isListening = false;
            updateUI('', 'MIC BLOCKED');
            hintText.textContent = '⚠ ALLOW MIC IN BROWSER SETTINGS · TAP ORB TO RETRY';
            hintText.style.color = '#ff4444';
            responseText.textContent = '🎤 Microphone access blocked. Open browser settings → allow mic for this site, then tap the orb again.';
            responseText.style.opacity = '1';
            vibrate([100, 50, 100]);

        } else if (event.error === 'no-speech') {
            // Silence detected — restart if still meant to be listening
            if (isListening && !isSpeaking) {
                setTimeout(startListening, 500);
            }
        } else if (event.error === 'network') {
            updateUI('', 'NO NETWORK');
            hintText.textContent = 'CHECK INTERNET CONNECTION';
        } else if (event.error === 'aborted') {
            // Intentional — do nothing
        } else {
            // Other transient errors — retry
            if (isListening && !isSpeaking) setTimeout(startListening, 300);
        }
    };

    recognition.onend = () => {
        // Auto-restart loop while listening is active
        if (isListening && !isSpeaking) {
            setTimeout(() => {
                if (isListening && !isSpeaking) {
                    try { recognition.start(); } catch(e) {}
                }
            }, isAndroid ? 350 : 120);
        }
    };
} else {
    // No Speech API
    console.warn("Web Speech API not supported in this browser.");
}

// ══════════════ sendToJarvis ══════════════

async function sendToJarvis(message) {
    if (!message.trim()) return;

    // Admin shortcut
    const msgLower = message.toLowerCase().replace(/\s+/g, ' ').trim();
    if (msgLower.includes('admin access') || msgLower.includes('admin panel') || msgLower === 'admin') {
        speak("Opening admin panel. Authentication required.");
        vibrate([50, 30, 50]);
        setTimeout(() => { window.location.href = '/api/admin/panel'; }, 1500);
        return;
    }

    // Device control commands
    if (typeof DeviceControl !== 'undefined') {
        const deviceResult = DeviceControl.handle(message);
        if (deviceResult) {
            if (deviceResult instanceof Promise) {
                const result = await deviceResult;
                if (result) {
                    transcriptText.textContent = '🎤 ' + message;
                    responseText.textContent = result.reply;
                    responseText.style.opacity = '1';
                    vibrate(30);
                    if (result.speak) speak(result.speak);
                    return;
                }
            } else {
                transcriptText.textContent = '🎤 ' + message;
                responseText.textContent = deviceResult.reply;
                responseText.style.opacity = '1';
                vibrate(30);
                if (deviceResult.speak) speak(deviceResult.speak);
                return;
            }
        }
    }

    // Stop listening while processing
    if (recognition && isListening) {
        try { recognition.abort(); } catch(e) {}
    }

    updateUI('processing', 'PROCESSING...');
    responseText.textContent = '⏳ Thinking...';
    responseText.style.opacity = '0.5';
    vibrate(50);

    const controller = new AbortController();
    const timeoutId  = setTimeout(() => controller.abort(), 100000); // 100s — matches backend 90s fallback

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
            responseText.textContent = data.reply;
            responseText.style.opacity = '1';
            vibrate(30);

            // Auto-open YouTube if a song was found
            if (data.youtube_url) {
                setTimeout(() => {
                    window.open(data.youtube_url, '_blank');
                }, 800);
            }

            // Start timer if the response contains one
            if (data.metadata && data.metadata.timer) {
                const t = data.metadata.timer;
                TimerManager.startTimerDisplay(t.id, t.remaining, t.label);
            }

            speak(data.reply);

            // Trigger remote device action if returned from backend
            if (data.intent || (data.metadata && data.metadata.task === "device" && data.metadata.action && data.metadata.action !== "none")) {
                if (typeof DeviceControl !== 'undefined' && DeviceControl.handleRemoteAction) {
                    DeviceControl.handleRemoteAction(data);
                }
            }
        }

        // Notify panel.js (agent badge + auto-refresh)
        if (typeof window.onJarvisResponse === 'function') {
            window.onJarvisResponse(data);
        }

        if (data.image_url) {
            const display = document.getElementById("imageDisplay");
            const img     = document.getElementById("generatedImg");
            img.src = data.image_url;
            display.style.display = 'flex';
            vibrate([50, 30, 50]);
        } else if (data.error) {
            updateUI('', 'NEURAL ERROR');
            responseText.textContent = '⚠️ ' + (data.error || 'Unknown error');
            speak("I encountered a neural link error.");
        }

    } catch (error) {
        clearTimeout(timeoutId);
        vibrate([100, 50, 100]);
        if (error.name === 'AbortError') {
            updateUI('', 'TIMEOUT');
            responseText.textContent = '⏱️ Request timed out';
            speak("The cognitive link timed out.");
        } else {
            updateUI('', 'OFFLINE');
            responseText.textContent = '🔌 Connection lost';
            speak("Connection to core server lost.");
        }
    }
}

// ══════════════ TTS — Server-side Edge TTS (works on Render.com) ══════════════
// Calls /api/tts which uses Microsoft Edge TTS neural voices server-side.
// Returns MP3 audio played via HTMLAudioElement — works on ALL browsers.
// No browser Speech Synthesis API dependency.

function _cleanForTTS(text) {
    return text
        .replace(/https?:\/\/\S+|www\.\S+/gi, '')
        .replace(/[#$%^&*_+{}\[\]|\\<>~`]/g, '')
        .replace(/[@:;]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
}

async function speak(text) {
    const cleaned = _cleanForTTS(text);
    if (!cleaned) { finishSpeaking(); return; }

    // Stop mic while speaking
    if (recognition) { try { recognition.abort(); } catch(e) {} }

    // Stop any current audio
    if (_ttsAudio) { _ttsAudio.pause(); _ttsAudio = null; }

    isSpeaking = true;
    updateUI('speaking', 'SPEAKING...');

    try {
        const resp = await fetch('/api/tts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: cleaned }),
        });

        if (!resp.ok) {
            console.warn('TTS server error:', resp.status);
            finishSpeaking();
            return;
        }

        const blob = await resp.blob();
        const url  = URL.createObjectURL(blob);
        const audio = new Audio(url);
        _ttsAudio = audio;

        audio.onended = () => {
            URL.revokeObjectURL(url);
            _ttsAudio = null;
            finishSpeaking();
        };
        audio.onerror = (e) => {
            console.warn('Audio playback error:', e);
            URL.revokeObjectURL(url);
            _ttsAudio = null;
            finishSpeaking();
        };

        // Android requires user-gesture to play — we're inside a tap/send handler so this is fine
        await audio.play();

    } catch (err) {
        console.warn('TTS fetch failed:', err);
        finishSpeaking();
    }
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
        updateUI('', 'SYSTEM ONLINE');
    }
}

// ══════════════ UI State Manager ══════════════

function updateUI(state, text) {
    if (statusText) statusText.textContent = text;
    if (voiceTrigger) voiceTrigger.className = 'center ' + state;
    if (!hintText) return;
    // Reset color on any state change
    hintText.style.color = '';

    if (state === 'listening') {
        hintText.textContent = 'LISTENING... TAP ORB TO STOP';
    } else if (state === 'processing') {
        hintText.textContent = 'PROCESSING NEURAL QUERY...';
    } else if (state === 'speaking') {
        hintText.textContent = 'JARVIS IS SPEAKING... TAP TO INTERRUPT';
    } else {
        hintText.textContent = isListening ? 'ALWAYS ON | READY' : 'TAP ORB FOR VOICE · TYPE BELOW';
    }
}

// ══════════════ Voice Toggle ══════════════

function toggleListening() {
    if (isSpeaking) {
        stopSpeaking();
        vibrate(30);
        return;
    }

    vibrate(50);

    if (isListening) {
        isListening = false;
        releaseWakeLock();
        if (recognition) { try { recognition.stop(); } catch(e) {} }
        updateUI('', 'SYSTEM ONLINE');
        transcriptText.textContent = '';
    } else {
        requestWakeLock();
        startListening();
    }
}

function startListening() {
    if (!recognition) {
        hintText.textContent = 'VOICE NOT SUPPORTED — USE CHROME ON ANDROID';
        hintText.style.color = '#ff4444';
        textInput.focus();
        return;
    }

    // Check if page is served over HTTPS (required for mic on mobile)
    if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
        hintText.textContent = '⚠ HTTPS REQUIRED FOR VOICE';
        hintText.style.color = '#ff4444';
        return;
    }

    isListening = true;
    updateUI('listening', 'LISTENING...');

    try {
        recognition.start();
    } catch (e) {
        // InvalidStateError = already started — safe to ignore
    }
}

// ══════════════ Text Input ══════════════

function sendTypedMessage() {
    const msg = textInput.value.trim();
    if (!msg) return;
    transcriptText.textContent = '⌨️ ' + msg;
    textInput.value = '';
    textInput.blur(); // hide keyboard on Android
    sendToJarvis(msg);
}

// ══════════════ Event Listeners ══════════════

// Touch events for orb (faster than click on Android)
let touchHandled = false;

voiceTrigger.addEventListener('touchend', (e) => {
    e.preventDefault();
    touchHandled = true;
    toggleListening();
    setTimeout(() => { touchHandled = false; }, 300);
}, { passive: false });

voiceTrigger.addEventListener('click', (e) => {
    if (touchHandled) return;
    toggleListening();
});

// Text input
sendBtn.addEventListener('click', sendTypedMessage);
textInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') { e.preventDefault(); sendTypedMessage(); }
});

// Android keyboard resize
if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', () => {
        document.body.style.height = window.visualViewport.height + 'px';
    });
}

// Image overlay close
document.getElementById("imageDisplay").addEventListener('click', function() {
    this.style.display = 'none';
});

// Orientation change
window.addEventListener('orientationchange', () => {
    setTimeout(() => {
        const result = setupCanvas(canvas);
        ctx = result.ctx; width = result.width; height = result.height;
        centerX = width / 2; centerY = height / 2;
        resizeBg();
    }, 300);
});

// Visibility change (Android tab switch)
document.addEventListener('visibilitychange', () => {
    if (!document.hidden && isListening) requestWakeLock();
    // Edge TTS audio pauses automatically when tab is hidden (HTMLAudioElement behavior)
});

// ══════════════ Init ══════════════
animate();
updateUI('', 'SYSTEM ONLINE');
console.log(`JARVIS v5 | ${isAndroid ? 'Android' : isIOS ? 'iOS' : 'Desktop'} | Voice: ${!!recognition} | TTS: ${!!window.speechSynthesis}`);

// ══════════════ Sci-Fi Solar System ══════════════
const bgCanvas = document.getElementById("bgCanvas");
const bgCtx    = bgCanvas.getContext("2d");

function resizeBg() {
    bgCanvas.width  = window.innerWidth;
    bgCanvas.height = window.innerHeight;
}
window.addEventListener('resize', resizeBg);
resizeBg();

const planets = [
    { radius: 140, size: 2.5, speed: 0.006,  color: "#00ffff", angle: Math.random() * Math.PI * 2, hasRings: false },
    { radius: 210, size: 4.5, speed: 0.004,  color: "#ff4444", angle: Math.random() * Math.PI * 2, hasRings: false },
    { radius: 310, size: 6.5, speed: 0.003,  color: "#ffb700", angle: Math.random() * Math.PI * 2, hasRings: false },
    { radius: 420, size: 5,   speed: 0.002,  color: "#00ff88", angle: Math.random() * Math.PI * 2, hasRings: false },
    { radius: 540, size: 9,   speed: 0.0012, color: "#0088ff", angle: Math.random() * Math.PI * 2, hasRings: true  },
    { radius: 680, size: 3.5, speed: 0.0009, color: "#ff00ff", angle: Math.random() * Math.PI * 2, hasRings: false },
    { radius: 840, size: 3,   speed: 0.0006, color: "#aaddff", angle: Math.random() * Math.PI * 2, hasRings: false },
];

const numStars = isMobile ? 200 : 400;
const stars = [];
for (let i = 0; i < numStars; i++) {
    stars.push({
        x: Math.random() * window.innerWidth,
        y: Math.random() * window.innerHeight,
        size: Math.random() * 1.5,
        opacity: Math.random(),
    });
}

function animateSolarSystem() {
    bgCtx.fillStyle = "rgba(3, 5, 12, 0.3)";
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

    const cx = bgCanvas.width / 2;
    const cy = bgCanvas.height / 2;

    stars.forEach(star => {
        bgCtx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
        bgCtx.beginPath();
        bgCtx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        bgCtx.fill();

        star.opacity += (Math.random() - 0.5) * 0.03;
        if (star.opacity < 0.05) star.opacity = 0.05;
        if (star.opacity > 1)    star.opacity = 1;

        star.x -= 0.15;
        if (star.x < 0) { star.x = bgCanvas.width; star.y = Math.random() * bgCanvas.height; }
    });

    planets.forEach(p => {
        p.angle += p.speed;
        const px = cx + Math.cos(p.angle) * p.radius;
        const py = cy + Math.sin(p.angle) * p.radius;

        bgCtx.beginPath();
        bgCtx.moveTo(cx, cy);
        bgCtx.lineTo(px, py);
        bgCtx.strokeStyle = "rgba(255, 255, 255, 0.03)";
        bgCtx.lineWidth = 1;
        bgCtx.stroke();

        bgCtx.shadowBlur  = isMobile ? 15 : 25;
        bgCtx.shadowColor = p.color;
        bgCtx.fillStyle   = p.color;
        bgCtx.beginPath();
        bgCtx.arc(px, py, p.size, 0, Math.PI * 2);
        bgCtx.fill();
        bgCtx.shadowBlur = 0;

        if (p.hasRings) {
            bgCtx.beginPath();
            bgCtx.ellipse(px, py, p.size * 2.8, p.size * 0.8, p.angle, 0, Math.PI * 2);
            bgCtx.strokeStyle = "rgba(0, 136, 255, 0.6)";
            bgCtx.lineWidth = 1.5;
            bgCtx.stroke();

            bgCtx.beginPath();
            bgCtx.ellipse(px, py, p.size * 4, p.size * 1.1, p.angle, 0, Math.PI * 2);
            bgCtx.strokeStyle = "rgba(0, 136, 255, 0.2)";
            bgCtx.lineWidth = 1;
            bgCtx.stroke();
        }
    });

    requestAnimationFrame(animateSolarSystem);
}

animateSolarSystem();

// Close image display on click
document.getElementById('imageDisplay').addEventListener('click', function() {
    this.style.display = 'none';
});
