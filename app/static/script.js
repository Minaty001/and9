/**
 * ═══════════════════════════════════════════════════════
 * JARVIS UI — Professional Module Architecture
 * Android & Mobile Optimized (Voice + Particles + Sci-Fi Background)
 * ═══════════════════════════════════════════════════════
 */

'use strict';

const JarvisApp = (() => {
  // ── DOM Element Cache ────────────────────────────────
  const DOM = {
    canvas: document.getElementById('particles'),
    statusText: document.getElementById('statusText'),
    hintText: document.getElementById('hintText'),
    voiceTrigger: document.getElementById('voiceTrigger'),
    transcriptText: document.getElementById('transcriptText'),
    responseText: document.getElementById('responseText'),
    textInput: document.getElementById('textInput'),
    sendBtn: document.getElementById('sendBtn'),
    imageDisplay: document.getElementById('imageDisplay'),
    generatedImg: document.getElementById('generatedImg'),
    bgCanvas: document.getElementById('bgCanvas'),
  };

  // ── Environment & System State ────────────────────────
  const CONFIG = {
    isAndroid: /android/i.test(navigator.userAgent),
    isIOS: /ipad|iphone|ipod/i.test(navigator.userAgent),
    isMobile: /mobile|tablet|android/i.test(navigator.userAgent),
    lang: 'en-IN',
    apiTimeoutMs: 100000,
  };

  const STATE = {
    isListening: false,
    isSpeaking: false,
    wakeLock: null,
    recognition: null,
    ttsAudio: null,
    touchHandled: false,
  };

  // ── Haptic Feedback & Utilities ──────────────────────
  const Utils = {
    vibrate(pattern) {
      if (navigator.vibrate) {
        try { navigator.vibrate(pattern); } catch (e) {}
      }
    },

    async requestWakeLock() {
      try {
        if ('wakeLock' in navigator) {
          STATE.wakeLock = await navigator.wakeLock.request('screen');
          STATE.wakeLock.addEventListener('release', () => { STATE.wakeLock = null; });
        }
      } catch (e) {}
    },

    releaseWakeLock() {
      if (STATE.wakeLock) {
        try { STATE.wakeLock.release(); } catch (e) {}
        STATE.wakeLock = null;
      }
    },

    updateUI(state, text) {
      if (DOM.statusText) DOM.statusText.textContent = text;
      if (DOM.voiceTrigger) DOM.voiceTrigger.className = 'center ' + state;
      if (!DOM.hintText) return;
      DOM.hintText.style.color = '';

      if (state === 'listening') {
        DOM.hintText.textContent = 'LISTENING... TAP ORB TO STOP';
      } else if (state === 'processing') {
        DOM.hintText.textContent = 'PROCESSING NEURAL QUERY...';
      } else if (state === 'speaking') {
        DOM.hintText.textContent = 'JARVIS IS SPEAKING... TAP TO INTERRUPT';
      } else {
        DOM.hintText.textContent = STATE.isListening ? 'ALWAYS ON | READY' : 'TAP ORB FOR VOICE · TYPE BELOW';
      }
    },
  };

  // ── Particle Visualizer Engine ───────────────────────
  const Visualizer = {
    ctx: null,
    width: 0,
    height: 0,
    particles: [],

    init() {
      if (!DOM.canvas) return;
      const rect = DOM.canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      DOM.canvas.width = rect.width * dpr;
      DOM.canvas.height = rect.height * dpr;
      this.ctx = DOM.canvas.getContext('2d');
      this.ctx.scale(dpr, dpr);
      this.width = rect.width;
      this.height = rect.height;

      const count = CONFIG.isMobile ? 80 : 150;
      const baseRadius = this.width * 0.35;
      this.particles = [];

      for (let i = 0; i < count; i++) {
        this.particles.push({
          angle: Math.random() * Math.PI * 2,
          radius: baseRadius + Math.random() * (this.width * 0.1),
          speed: 0.001 + Math.random() * 0.004,
          size: 1 + Math.random() * 2,
        });
      }
      this.animate();
    },

    animate() {
      if (!this.ctx) return;
      this.ctx.clearRect(0, 0, this.width, this.height);
      const cx = this.width / 2;
      const cy = this.height / 2;

      this.particles.forEach(p => {
        p.angle += p.speed;
        const x = cx + p.radius * Math.cos(p.angle);
        const y = cy + p.radius * Math.sin(p.angle);
        const depth = Math.sin(p.angle);
        const opacity = 0.2 + (depth + 1) / 2;

        this.ctx.fillStyle = `rgba(255,165,0,${opacity * 0.7})`;
        this.ctx.beginPath();
        this.ctx.arc(x, y, p.size, 0, Math.PI * 2);
        this.ctx.fill();
      });
      requestAnimationFrame(() => this.animate());
    },
  };

  // ── Sci-Fi Background Solar System ───────────────────
  const SolarSystem = {
    ctx: null,
    width: 0,
    height: 0,
    planets: [],
    stars: [],

    init() {
      if (!DOM.bgCanvas) return;
      this.ctx = DOM.bgCanvas.getContext('2d');
      this.resize();
      window.addEventListener('resize', () => this.resize());

      this.planets = [
        { radius: 140, size: 2.5, speed: 0.006,  color: '#00ffff', angle: Math.random() * Math.PI * 2, hasRings: false },
        { radius: 210, size: 4.5, speed: 0.004,  color: '#ff4444', angle: Math.random() * Math.PI * 2, hasRings: false },
        { radius: 310, size: 6.5, speed: 0.003,  color: '#ffb700', angle: Math.random() * Math.PI * 2, hasRings: false },
        { radius: 420, size: 5,   speed: 0.002,  color: '#00ff88', angle: Math.random() * Math.PI * 2, hasRings: false },
        { radius: 540, size: 9,   speed: 0.0012, color: '#0088ff', angle: Math.random() * Math.PI * 2, hasRings: true  },
        { radius: 680, size: 3.5, speed: 0.0009, color: '#ff00ff', angle: Math.random() * Math.PI * 2, hasRings: false },
        { radius: 840, size: 3,   speed: 0.0006, color: '#aaddff', angle: Math.random() * Math.PI * 2, hasRings: false },
      ];

      const numStars = CONFIG.isMobile ? 200 : 400;
      this.stars = [];
      for (let i = 0; i < numStars; i++) {
        this.stars.push({
          x: Math.random() * window.innerWidth,
          y: Math.random() * window.innerHeight,
          size: Math.random() * 1.5,
          opacity: Math.random(),
        });
      }
      this.animate();
    },

    resize() {
      if (!DOM.bgCanvas) return;
      DOM.bgCanvas.width = window.innerWidth;
      DOM.bgCanvas.height = window.innerHeight;
      this.width = DOM.bgCanvas.width;
      this.height = DOM.bgCanvas.height;
    },

    animate() {
      if (!this.ctx) return;
      this.ctx.fillStyle = 'rgba(3, 5, 12, 0.3)';
      this.ctx.fillRect(0, 0, this.width, this.height);

      const cx = this.width / 2;
      const cy = this.height / 2;

      this.stars.forEach(star => {
        this.ctx.fillStyle = `rgba(255, 255, 255, ${star.opacity})`;
        this.ctx.beginPath();
        this.ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
        this.ctx.fill();

        star.opacity += (Math.random() - 0.5) * 0.03;
        if (star.opacity < 0.05) star.opacity = 0.05;
        if (star.opacity > 1)    star.opacity = 1;

        star.x -= 0.15;
        if (star.x < 0) { star.x = this.width; star.y = Math.random() * this.height; }
      });

      this.planets.forEach(p => {
        p.angle += p.speed;
        const px = cx + Math.cos(p.angle) * p.radius;
        const py = cy + Math.sin(p.angle) * p.radius;

        this.ctx.beginPath();
        this.ctx.moveTo(cx, cy);
        this.ctx.lineTo(px, py);
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();

        this.ctx.shadowBlur  = CONFIG.isMobile ? 15 : 25;
        this.ctx.shadowColor = p.color;
        this.ctx.fillStyle   = p.color;
        this.ctx.beginPath();
        this.ctx.arc(px, py, p.size, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;

        if (p.hasRings) {
          this.ctx.beginPath();
          this.ctx.ellipse(px, py, p.size * 2.8, p.size * 0.8, p.angle, 0, Math.PI * 2);
          this.ctx.strokeStyle = 'rgba(0, 136, 255, 0.6)';
          this.ctx.lineWidth = 1.5;
          this.ctx.stroke();

          this.ctx.beginPath();
          this.ctx.ellipse(px, py, p.size * 4, p.size * 1.1, p.angle, 0, Math.PI * 2);
          this.ctx.strokeStyle = 'rgba(0, 136, 255, 0.2)';
          this.ctx.lineWidth = 1;
          this.ctx.stroke();
        }
      });

      requestAnimationFrame(() => this.animate());
    },
  };

  // ── Speech Engine ────────────────────────────────────
  const SpeechEngine = {
    init() {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        console.warn('Web Speech API not supported in this browser.');
        return;
      }

      STATE.recognition = new SpeechRecognition();
      STATE.recognition.continuous = false;
      STATE.recognition.interimResults = !CONFIG.isAndroid;
      STATE.recognition.maxAlternatives = 1;
      STATE.recognition.lang = CONFIG.lang;

      STATE.recognition.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript   = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const t = event.results[i][0].transcript;
          if (event.results[i].isFinal) finalTranscript += t;
          else interimTranscript += t;
        }

        if (interimTranscript && DOM.transcriptText) {
          DOM.transcriptText.textContent = '🎤 ' + interimTranscript;
          DOM.transcriptText.style.opacity = '0.6';
        }

        if (finalTranscript) {
          if (DOM.transcriptText) {
            DOM.transcriptText.textContent = '🎤 ' + finalTranscript;
            DOM.transcriptText.style.opacity = '1';
          }
          ChatService.send(finalTranscript);
        }
      };

      STATE.recognition.onerror = (event) => {
        console.warn('Speech Error:', event.error);
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          STATE.isListening = false;
          Utils.updateUI('', 'MIC BLOCKED');
          if (DOM.hintText) {
            DOM.hintText.textContent = '⚠ ALLOW MIC IN BROWSER SETTINGS · TAP ORB TO RETRY';
            DOM.hintText.style.color = '#ff4444';
          }
          if (DOM.responseText) {
            DOM.responseText.textContent = '🎤 Microphone access blocked. Open browser settings → allow mic for this site, then tap the orb again.';
            DOM.responseText.style.opacity = '1';
          }
          Utils.vibrate([100, 50, 100]);
        } else if (event.error === 'no-speech') {
          if (STATE.isListening && !STATE.isSpeaking) {
            setTimeout(() => this.start(), 500);
          }
        } else if (event.error === 'network') {
          Utils.updateUI('', 'NO NETWORK');
          if (DOM.hintText) DOM.hintText.textContent = 'CHECK INTERNET CONNECTION';
        } else if (event.error !== 'aborted') {
          if (STATE.isListening && !STATE.isSpeaking) {
            setTimeout(() => this.start(), 300);
          }
        }
      };

      STATE.recognition.onend = () => {
        if (STATE.isListening && !STATE.isSpeaking) {
          setTimeout(() => {
            if (STATE.isListening && !STATE.isSpeaking) {
              try { STATE.recognition.start(); } catch (e) {}
            }
          }, CONFIG.isAndroid ? 350 : 120);
        }
      };
    },

    start() {
      if (!STATE.recognition) {
        if (DOM.hintText) {
          DOM.hintText.textContent = 'VOICE NOT SUPPORTED — USE CHROME ON ANDROID';
          DOM.hintText.style.color = '#ff4444';
        }
        if (DOM.textInput) DOM.textInput.focus();
        return;
      }

      if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
        if (DOM.hintText) {
          DOM.hintText.textContent = '⚠ HTTPS REQUIRED FOR VOICE';
          DOM.hintText.style.color = '#ff4444';
        }
        return;
      }

      STATE.isListening = true;
      Utils.updateUI('listening', 'LISTENING...');

      try {
        STATE.recognition.start();
      } catch (e) {}
    },

    stop() {
      STATE.isListening = false;
      Utils.releaseWakeLock();
      if (STATE.recognition) {
        try { STATE.recognition.stop(); } catch (e) {}
      }
      Utils.updateUI('', 'SYSTEM ONLINE');
      if (DOM.transcriptText) DOM.transcriptText.textContent = '';
    },

    toggle() {
      if (STATE.isSpeaking) {
        TTSService.stop();
        Utils.vibrate(30);
        return;
      }

      Utils.vibrate(50);

      if (STATE.isListening) {
        this.stop();
      } else {
        Utils.requestWakeLock();
        this.start();
      }
    },
  };

  // ── Edge TTS Service ─────────────────────────────────
  const TTSService = {
    cleanText(text) {
      return text
        .replace(/https?:\/\/\S+|www\.\S+/gi, '')
        .replace(/[#$%^&*_+{}\[\]|\\<>~`]/g, '')
        .replace(/[@:;]/g, ' ')
        .replace(/\s+/g, ' ')
        .trim();
    },

    async speak(text) {
      const cleaned = this.cleanText(text);
      if (!cleaned) { this.finish(); return; }

      if (STATE.recognition) {
        try { STATE.recognition.abort(); } catch (e) {}
      }

      if (STATE.ttsAudio) {
        STATE.ttsAudio.pause();
        STATE.ttsAudio = null;
      }

      STATE.isSpeaking = true;
      Utils.updateUI('speaking', 'SPEAKING...');

      try {
        const resp = await fetch('/api/tts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text: cleaned }),
        });

        if (!resp.ok) {
          console.warn('TTS server error:', resp.status);
          this.finish();
          return;
        }

        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        STATE.ttsAudio = audio;

        audio.onended = () => {
          URL.revokeObjectURL(url);
          STATE.ttsAudio = null;
          this.finish();
        };

        audio.onerror = (e) => {
          console.warn('Audio playback error:', e);
          URL.revokeObjectURL(url);
          STATE.ttsAudio = null;
          this.finish();
        };

        await audio.play();
      } catch (err) {
        console.warn('TTS fetch failed:', err);
        this.finish();
      }
    },

    stop() {
      if (STATE.ttsAudio) {
        STATE.ttsAudio.pause();
        STATE.ttsAudio = null;
      }
      this.finish();
    },

    finish() {
      STATE.isSpeaking = false;
      if (STATE.isListening) {
        setTimeout(() => SpeechEngine.start(), CONFIG.isAndroid ? 500 : 200);
      } else {
        Utils.updateUI('', 'SYSTEM ONLINE');
      }
    },
  };

  // ── Chat & Command Service ───────────────────────────
  const ChatService = {
    async send(message) {
      if (!message.trim()) return;

      const msgLower = message.toLowerCase().replace(/\s+/g, ' ').trim();
      if (msgLower.includes('admin access') || msgLower.includes('admin panel') || msgLower === 'admin') {
        TTSService.speak('Opening admin panel. Authentication required.');
        Utils.vibrate([50, 30, 50]);
        setTimeout(() => { window.location.href = '/api/admin/panel'; }, 1500);
        return;
      }

      if (typeof DeviceControl !== 'undefined') {
        const deviceResult = DeviceControl.handle(message);
        if (deviceResult) {
          const result = (deviceResult instanceof Promise) ? await deviceResult : deviceResult;
          if (result) {
            if (DOM.transcriptText) DOM.transcriptText.textContent = '🎤 ' + message;
            if (DOM.responseText) {
              DOM.responseText.textContent = result.reply;
              DOM.responseText.style.opacity = '1';
            }
            Utils.vibrate(30);
            if (result.speak) TTSService.speak(result.speak);
            return;
          }
        }
      }

      if (STATE.recognition && STATE.isListening) {
        try { STATE.recognition.abort(); } catch (e) {}
      }

      Utils.updateUI('processing', 'PROCESSING...');
      if (DOM.responseText) {
        DOM.responseText.textContent = '⏳ Thinking...';
        DOM.responseText.style.opacity = '0.5';
      }
      Utils.vibrate(50);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.apiTimeoutMs);

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
          if (DOM.responseText) {
            DOM.responseText.textContent = data.reply;
            DOM.responseText.style.opacity = '1';
          }
          Utils.vibrate(30);

          if (data.youtube_url) {
            setTimeout(() => { window.open(data.youtube_url, '_blank'); }, 800);
          }

          if (data.metadata && data.metadata.timer && typeof TimerManager !== 'undefined') {
            const t = data.metadata.timer;
            TimerManager.startTimerDisplay(t.id, t.remaining, t.label);
          }

          TTSService.speak(data.reply);

          if (data.intent || (data.metadata && data.metadata.task === 'device' && data.metadata.action && data.metadata.action !== 'none')) {
            if (typeof DeviceControl !== 'undefined' && DeviceControl.handleRemoteAction) {
              DeviceControl.handleRemoteAction(data);
            }
          }
        }

        if (typeof window.onJarvisResponse === 'function') {
          window.onJarvisResponse(data);
        }

        if (data.image_url) {
          if (DOM.generatedImg) DOM.generatedImg.src = data.image_url;
          if (DOM.imageDisplay) DOM.imageDisplay.style.display = 'flex';
          Utils.vibrate([50, 30, 50]);
        } else if (data.error) {
          Utils.updateUI('', 'NEURAL ERROR');
          if (DOM.responseText) DOM.responseText.textContent = '⚠️ ' + (data.error || 'Unknown error');
          TTSService.speak('I encountered a neural link error.');
        }

      } catch (error) {
        clearTimeout(timeoutId);
        Utils.vibrate([100, 50, 100]);
        if (error.name === 'AbortError') {
          Utils.updateUI('', 'TIMEOUT');
          if (DOM.responseText) DOM.responseText.textContent = '⏱️ Request timed out';
          TTSService.speak('The cognitive link timed out.');
        } else {
          Utils.updateUI('', 'OFFLINE');
          if (DOM.responseText) DOM.responseText.textContent = '🔌 Connection lost';
          TTSService.speak('Connection to core server lost.');
        }
      }
    },

    sendTypedMessage() {
      if (!DOM.textInput) return;
      const msg = DOM.textInput.value.trim();
      if (!msg) return;
      if (DOM.transcriptText) DOM.transcriptText.textContent = '⌨️ ' + msg;
      DOM.textInput.value = '';
      DOM.textInput.blur();
      this.send(msg);
    },
  };

  // ── Setup Event Listeners ────────────────────────────
  function initEvents() {
    if (DOM.voiceTrigger) {
      DOM.voiceTrigger.addEventListener('touchend', (e) => {
        e.preventDefault();
        STATE.touchHandled = true;
        SpeechEngine.toggle();
        setTimeout(() => { STATE.touchHandled = false; }, 300);
      }, { passive: false });

      DOM.voiceTrigger.addEventListener('click', () => {
        if (STATE.touchHandled) return;
        SpeechEngine.toggle();
      });
    }

    if (DOM.sendBtn) {
      DOM.sendBtn.addEventListener('click', () => ChatService.sendTypedMessage());
    }

    if (DOM.textInput) {
      DOM.textInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          ChatService.sendTypedMessage();
        }
      });
    }

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', () => {
        document.body.style.height = window.visualViewport.height + 'px';
      });
    }

    if (DOM.imageDisplay) {
      DOM.imageDisplay.addEventListener('click', function() {
        this.style.display = 'none';
      });
    }

    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        Visualizer.init();
        SolarSystem.resize();
      }, 300);
    });

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && STATE.isListening) Utils.requestWakeLock();
    });
  }

  // ── Module Public API ────────────────────────────────
  return {
    init() {
      Visualizer.init();
      SolarSystem.init();
      SpeechEngine.init();
      initEvents();
      Utils.updateUI('', 'SYSTEM ONLINE');
      console.log(`JARVIS v5 (Refactored) | ${CONFIG.isAndroid ? 'Android' : CONFIG.isIOS ? 'iOS' : 'Desktop'} | Voice: ${!!STATE.recognition}`);
    },
    sendToJarvis: (msg) => ChatService.send(msg),
    speak: (text) => TTSService.speak(text),
    stopSpeaking: () => TTSService.stop(),
    toggleListening: () => SpeechEngine.toggle(),
    startListening: () => SpeechEngine.start(),
    updateUI: (st, txt) => Utils.updateUI(st, txt),
    vibrate: (pat) => Utils.vibrate(pat),
  };
})();

// Expose backward-compatible global functions
window.sendToJarvis = (msg) => JarvisApp.sendToJarvis(msg);
window.speak = (txt) => JarvisApp.speak(txt);
window.stopSpeaking = () => JarvisApp.stopSpeaking();
window.toggleListening = () => JarvisApp.toggleListening();
window.startListening = () => JarvisApp.startListening();
window.updateUI = (st, txt) => JarvisApp.updateUI(st, txt);
window.vibrate = (pat) => JarvisApp.vibrate(pat);

// Initialize on DOM load
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => JarvisApp.init());
} else {
  JarvisApp.init();
}
