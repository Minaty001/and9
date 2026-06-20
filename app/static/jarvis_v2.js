// ═══════════════════════════════════════════════════════
// JARVIS v2 — Android-Optimized AI Assistant JS
// Features: Chat bubbles, memory recall, proactive engine,
//           YouTube mini-player, toast system, PWA offline
// ═══════════════════════════════════════════════════════

'use strict';

// ── DOM refs ────────────────────────────────────────────
const $ = id => document.getElementById(id);
const chatSection   = $('chatSection');
const chatMessages  = $('chatMessages');
const orbSection    = $('orbSection');
const textInput     = $('textInput');
const sendBtn       = $('sendBtn');
const sendIcon      = $('sendIcon');
const attachBtn     = $('attachBtn');
const clearInputBtn = $('clearInputBtn');
const proactiveCard = $('proactiveCard');
const proactiveText = $('proactiveText');
const proactiveClose= $('proactiveClose');
const agentBadge    = $('agentBadge');
const memoryBtn     = $('memoryRecallBtn');
const memoryDrawer  = $('memoryDrawer');
const closeMemoryDrawer = $('closeMemoryDrawer');
const memorySearchInput = $('memorySearchInput');
const memorySearchBtn   = $('memorySearchBtn');
const memoryResults     = $('memoryResults');
const memorySessions    = $('memorySessions');
const memoryStats       = $('memoryStats');
const ytPlayer      = $('ytPlayer');
const ytTitle       = $('ytTitle');
const ytClose       = $('ytClose');
const ytEmbed       = $('ytEmbed');
const toastContainer= $('toastContainer');
const briefingCard  = $('briefingCard');
const briefingTime  = $('briefingTime');
const briefingGreeting = $('briefingGreeting');
const briefingTip   = $('briefingTip');
const streakText    = $('streakText');
const dynamicChips  = $('dynamicChips');
const bottomChips   = $('bottomChips');

// ── State ───────────────────────────────────────────────
let chatMode       = false;   // false = orb view, true = chat bubbles
let isProcessing   = false;
let messageHistory = [];      // local chat log for session

// ── Device detection ────────────────────────────────────
const isAndroid = /android/i.test(navigator.userAgent);
const isMobile  = /mobile|tablet|android|iphone|ipad/i.test(navigator.userAgent);

// ═══════════════════════════════════════════════════════
// TOAST SYSTEM
// ═══════════════════════════════════════════════════════
function showToast(msg, type = '', duration = 3000) {
  const el = document.createElement('div');
  el.className = `toast-msg ${type}`;
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

// ═══════════════════════════════════════════════════════
// CHAT BUBBLE SYSTEM
// ═══════════════════════════════════════════════════════
function switchToChatMode() {
  if (chatMode) return;
  chatMode = true;
  orbSection.style.display = 'none';
  chatSection.style.display = 'flex';
}

function addBubble(role, text, agentName = '') {
  switchToChatMode();
  const wrap = document.createElement('div');
  wrap.className = `msg-bubble ${role}`;

  if (role === 'jarvis') {
    const hdr = document.createElement('div');
    hdr.className = 'msg-header';
    hdr.textContent = `⚡ JARVIS${agentName ? ' · ' + agentName.toUpperCase() : ''}`;
    wrap.appendChild(hdr);
  }

  // Support markdown-ish formatting
  const content = document.createElement('div');
  content.innerHTML = formatResponse(text);
  wrap.appendChild(content);

  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  meta.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  wrap.appendChild(meta);

  chatMessages.appendChild(wrap);
  wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
  messageHistory.push({ role, text, ts: Date.now() });
  return wrap;
}

function addTypingIndicator() {
  const wrap = document.createElement('div');
  wrap.className = 'msg-bubble jarvis typing';
  wrap.id = 'typingBubble';
  [1,2,3].forEach(() => {
    const d = document.createElement('div');
    d.className = 'typing-dot';
    wrap.appendChild(d);
  });
  chatMessages.appendChild(wrap);
  wrap.scrollIntoView({ behavior: 'smooth', block: 'end' });
  return wrap;
}

function removeTypingIndicator() {
  const el = $('typingBubble');
  if (el) el.remove();
}

function formatResponse(text) {
  if (!text) return '';
  return text
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(0,212,255,0.1);padding:1px 5px;border-radius:4px;font-family:monospace;font-size:0.9em">$1</code>')
    .replace(/\n/g, '<br>');
}

// ═══════════════════════════════════════════════════════
// SEND MESSAGE
// ═══════════════════════════════════════════════════════
async function sendToJarvisV2(message) {
  if (!message.trim() || isProcessing) return;

  // Admin shortcut
  if (/admin\s*(panel|access)?$/i.test(message.trim())) {
    window.location.href = '/api/admin/panel';
    return;
  }

  // Local device commands first
  if (typeof DeviceControl !== 'undefined') {
    const dr = DeviceControl.handle(message);
    if (dr) {
      const result = dr instanceof Promise ? await dr : dr;
      if (result) {
        addBubble('user', message);
        addBubble('jarvis', result.reply, 'device');
        if (result.speak && typeof speak === 'function') speak(result.speak);
        return;
      }
    }
  }

  // Add user bubble
  addBubble('user', message);
  textInput.value = '';
  clearInputBtn.style.display = 'none';

  // UI state
  isProcessing = true;
  sendBtn.classList.add('loading');
  sendIcon.textContent = '⏳';
  if (typeof updateUI === 'function') updateUI('processing', 'PROCESSING...');

  const typing = addTypingIndicator();
  if (typeof vibrate === 'function') vibrate(30);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 90000);

  try {
    const resp = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    const data = await resp.json();

    removeTypingIndicator();

    const reply = data.reply || data.response || '';
    const agent = data.agent || '';

    // Add JARVIS bubble
    addBubble('jarvis', reply, agent);

    // Agent badge
    if (agentBadge && agent) {
      agentBadge.textContent = `${agent.toUpperCase()} · ${data.time_ms || 0}ms`;
      agentBadge.style.opacity = '1';
      setTimeout(() => { agentBadge.style.opacity = '0'; }, 4000);
    }

    // TTS
    if (reply && typeof speak === 'function') speak(reply);

    // YouTube mini-player
    if (data.youtube_url) {
      openYtPlayer(data.youtube_url, reply);
    }

    // Image display
    if (data.image_url) {
      $('generatedImg').src = data.image_url;
      $('imageDisplay').style.display = 'flex';
    }

    // Memory recall badge
    if (data.metadata?.cache_hit) {
      showToast('⚡ Fast recall — cache hit!', 'success', 2000);
    }

    // Device intent
    if ((data.intent || data.metadata?.action) && typeof DeviceControl !== 'undefined') {
      DeviceControl.handleRemoteAction(data);
    }

    // Panel refresh
    if (typeof window.onJarvisResponse === 'function') window.onJarvisResponse(data);

    if (typeof updateUI === 'function') updateUI('', 'SYSTEM ONLINE');

  } catch (err) {
    clearTimeout(timeoutId);
    removeTypingIndicator();
    const msg = err.name === 'AbortError'
      ? '⏱️ Request timed out. Try again!'
      : '🔌 Connection lost. Check internet.';
    addBubble('jarvis', msg);
    showToast(err.name === 'AbortError' ? 'Timeout ⏱️' : 'Offline 🔌', 'error');
    if (typeof updateUI === 'function') updateUI('', 'OFFLINE');
  } finally {
    isProcessing = false;
    sendBtn.classList.remove('loading');
    sendIcon.textContent = '➤';
    if (typeof isListening !== 'undefined' && isListening && typeof startListening === 'function') {
      setTimeout(startListening, 400);
    }
  }
}

// ═══════════════════════════════════════════════════════
// YOUTUBE MINI PLAYER
// ═══════════════════════════════════════════════════════
function openYtPlayer(url, title = '') {
  let videoId = '';
  const m1 = url.match(/v=([^&]+)/);
  const m2 = url.match(/youtu\.be\/([^?]+)/);
  if (m1) videoId = m1[1];
  else if (m2) videoId = m2[1];

  if (!videoId) {
    window.open(url, '_blank');
    return;
  }

  ytTitle.textContent = '🎵 ' + (title.slice(0, 40) || 'Playing...');
  ytEmbed.innerHTML = `<iframe 
    src="https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0" 
    allow="autoplay; encrypted-media" allowfullscreen></iframe>`;
  ytPlayer.style.display = 'block';
}

ytClose.addEventListener('click', () => {
  ytPlayer.style.display = 'none';
  ytEmbed.innerHTML = '';
});

// ═══════════════════════════════════════════════════════
// MEMORY RECALL DRAWER
// ═══════════════════════════════════════════════════════
memoryBtn.addEventListener('click', () => {
  memoryDrawer.classList.add('open');
  loadMemoryStats();
  loadSessionsSummary();
});

closeMemoryDrawer.addEventListener('click', () => {
  memoryDrawer.classList.remove('open');
});

memorySearchBtn.addEventListener('click', doMemorySearch);
memorySearchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter') doMemorySearch();
});

async function doMemorySearch() {
  const q = memorySearchInput.value.trim();
  if (!q) return;
  memoryResults.innerHTML = '<div style="text-align:center;padding:20px;opacity:0.5;font-size:13px;">🔍 Searching...</div>';

  try {
    const r = await fetch(`/api/memory/recall?q=${encodeURIComponent(q)}&limit=10`);
    const data = await r.json();
    renderMemoryResults(data, q);
  } catch (e) {
    memoryResults.innerHTML = '<div style="color:#ff4757;padding:10px;font-size:13px;">Search failed</div>';
  }
}

function renderMemoryResults(data, query) {
  const eps = data.matched_episodes || [];
  const hit = data.cache_hit;

  memoryStats.textContent = `${eps.length} results${hit ? ' · ⚡ cache' : ''} · query: "${query}"`;

  if (!eps.length) {
    memoryResults.innerHTML = '<div class="panel-empty">Kuch nahi mila. Alag keyword try karo.</div>';
    return;
  }

  memoryResults.innerHTML = '';
  eps.forEach(ep => {
    const div = document.createElement('div');
    div.className = 'memory-ep';
    const ts = ep.timestamp ? ep.timestamp.slice(0,16).replace('T',' ') : '';
    div.innerHTML = `
      <div class="ep-role">${ep.role === 'user' ? '👤 YOU' : '⚡ JARVIS'} · Session ${ep.session_id}</div>
      <div class="ep-content">${ep.content.slice(0,200)}${ep.content.length>200?'...':''}</div>
      <div class="ep-time">${ts} · ${ep.topic || 'general'}</div>`;
    // Tap to ask about it
    div.addEventListener('click', () => {
      memoryDrawer.classList.remove('open');
      const txt = `Yaad hai kya: "${ep.content.slice(0,80)}"`;
      textInput.value = txt;
      textInput.focus();
    });
    memoryResults.appendChild(div);
  });
}

async function loadSessionsSummary() {
  memorySessions.innerHTML = '';
  try {
    const r = await fetch('/api/memory/sessions?limit=4');
    const data = await r.json();
    const sessions = data.sessions || [];
    if (!sessions.length) return;

    const header = document.createElement('div');
    header.style.cssText = 'font-size:11px;font-family:monospace;color:rgba(0,212,255,0.5);letter-spacing:2px;text-transform:uppercase;padding:8px 0 4px;';
    header.textContent = 'PAST SESSIONS';
    memorySessions.appendChild(header);

    sessions.forEach(s => {
      const div = document.createElement('div');
      div.className = 'session-card';
      div.innerHTML = `
        <div class="session-id">Session #${s.session_id} · ${s.ended_at === 'active' ? '🟢 Active' : s.ended_at}</div>
        <div>${(s.summary || 'No summary').slice(0,100)}</div>`;
      memorySessions.appendChild(div);
    });
  } catch(e) {}
}

async function loadMemoryStats() {
  try {
    const r = await fetch('/api/memory/cache/stats');
    const d = await r.json();
    memoryStats.textContent = `Cache: ${d.size}/${d.max_size} entries · ${d.total_hits} hits · TTL ${d.ttl_sec}s`;
  } catch(e) {}
}

// ═══════════════════════════════════════════════════════
// PROACTIVE ENGINE (client-side)
// ═══════════════════════════════════════════════════════
async function loadProactiveData() {
  try {
    const r = await fetch('/api/proactive/briefing');
    const d = await r.json();

    // Update briefing card
    if (briefingTime) briefingTime.textContent = d.time || '--:--';
    if (briefingGreeting) briefingGreeting.textContent = d.greeting || '';
    if (briefingTip) briefingTip.textContent = d.tip || '';

    // Streak
    if (streakText) streakText.textContent = d.streak?.message || 'Start your streak today!';

    // Proactive suggestion
    if (d.suggestion) {
      proactiveText.textContent = d.suggestion;
      proactiveCard.style.display = 'flex';
    }

    // Dynamic chips
    if (d.quick_actions?.length && dynamicChips) {
      dynamicChips.innerHTML = '';
      d.quick_actions.forEach(a => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.dataset.msg = a.msg;
        btn.textContent = a.label;
        dynamicChips.appendChild(btn);
      });
    }
  } catch(e) {
    // Fallback: static greeting
    const hour = new Date().getHours();
    const greet = hour < 12 ? 'Good morning! ☀️' : hour < 17 ? 'Good afternoon! 🌤' : 'Good evening! 🌙';
    if (briefingGreeting) briefingGreeting.textContent = greet;
    if (briefingTime) briefingTime.textContent = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
  }
}

// Update briefing clock every minute
setInterval(() => {
  if (briefingTime) {
    briefingTime.textContent = new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
  }
}, 60000);

proactiveClose?.addEventListener('click', () => {
  proactiveCard.style.display = 'none';
});

// Click suggestion → send to JARVIS
proactiveCard?.addEventListener('click', e => {
  if (e.target === proactiveClose) return;
  const txt = proactiveText.textContent;
  if (txt) {
    proactiveCard.style.display = 'none';
    addBubble('user', txt);
    sendToJarvisV2(txt);
  }
});

// ═══════════════════════════════════════════════════════
// INPUT HANDLING
// ═══════════════════════════════════════════════════════
textInput.addEventListener('input', () => {
  clearInputBtn.style.display = textInput.value ? 'block' : 'none';
});

clearInputBtn.addEventListener('click', () => {
  textInput.value = '';
  clearInputBtn.style.display = 'none';
  textInput.focus();
});

sendBtn.addEventListener('click', () => {
  const msg = textInput.value.trim();
  if (msg) {
    textInput.value = '';
    clearInputBtn.style.display = 'none';
    textInput.blur();
    sendToJarvisV2(msg);
  } else {
    // If no text, toggle voice
    if (typeof toggleListening === 'function') toggleListening();
  }
});

textInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    const msg = textInput.value.trim();
    if (msg) {
      textInput.value = '';
      clearInputBtn.style.display = 'none';
      sendToJarvisV2(msg);
    }
  }
});

// Attach button = toggle voice
attachBtn.addEventListener('click', () => {
  if (typeof toggleListening === 'function') {
    toggleListening();
    attachBtn.classList.toggle('recording', typeof isListening !== 'undefined' && isListening);
  }
});

// Bottom chips
bottomChips?.addEventListener('click', e => {
  const chip = e.target.closest('.bchip');
  if (!chip) return;
  const msg = chip.dataset.msg;
  if (msg) {
    if (msg.endsWith(' ')) {
      textInput.value = msg;
      textInput.focus();
      textInput.setSelectionRange(msg.length, msg.length);
    } else {
      sendToJarvisV2(msg);
    }
  }
});

// Dynamic chips in panel
document.addEventListener('click', e => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const msg = chip.dataset.msg;
  if (!msg) return;
  // Close panel if open
  $('sidePanel')?.classList.remove('open');
  $('sideOverlay')?.classList.remove('show');
  sendToJarvisV2(msg);
});

// ═══════════════════════════════════════════════════════
// OVERRIDE: sendToJarvis from script.js → use v2
// ═══════════════════════════════════════════════════════
// This replaces the old sendToJarvis so voice input also uses chat bubbles
window.sendToJarvis = sendToJarvisV2;

// Override speak to also update attachBtn state
const _origSpeak = window.speak;
if (_origSpeak) {
  window.speak = async function(text) {
    await _origSpeak(text);
    attachBtn?.classList.remove('recording');
  };
}

// ═══════════════════════════════════════════════════════
// IMAGE OVERLAY
// ═══════════════════════════════════════════════════════
$('imageDisplay')?.addEventListener('click', function() {
  this.style.display = 'none';
});

// ═══════════════════════════════════════════════════════
// KEYBOARD / VIEWPORT (Android keyboard fix)
// ═══════════════════════════════════════════════════════
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', () => {
    const vh = window.visualViewport.height;
    document.querySelector('.main-container').style.bottom =
      (window.innerHeight - vh + 64) + 'px';
  });
}

// ═══════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════
(async function init() {
  // Load proactive data
  await loadProactiveData();

  // Welcome message after 1s
  setTimeout(() => {
    const hour = new Date().getHours();
    const greet = hour < 12 ? 'Subah ki shubhkamnaen! ☀️' : hour < 17 ? 'Dopahar mein swagat! 🌤' : 'Shaam ko namaste! 🌙';
    showToast(`${greet} JARVIS ready!`, 'success', 3000);
  }, 1200);

  console.log(`JARVIS v2 | ${isAndroid ? '🤖 Android' : '🖥 Desktop'} | Chat mode ready`);
})();
