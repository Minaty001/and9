/**
 * panel.js — Goals & Reminders sidebar panel logic.
 * Talks to /api/goals and /api/events endpoints.
 */

const sidePanel  = document.getElementById('sidePanel');
const sideOverlay = document.getElementById('sideOverlay');
const menuBtn    = document.getElementById('menuBtn');
const closePanelBtn = document.getElementById('closeSidePanel');
const goalsList  = document.getElementById('goalsList');
const eventsList = document.getElementById('eventsList');
const addGoalForm = document.getElementById('addGoalForm');
const newGoalInput = document.getElementById('newGoalInput');
const agentBadge = document.getElementById('agentBadge');

// ── Panel open / close ────────────────────────────────────────
function openPanel() {
    sidePanel.classList.add('open');
    sideOverlay.classList.add('show');
    loadGoals();
    loadEvents();
}
function closePanel() {
    sidePanel.classList.remove('open');
    sideOverlay.classList.remove('show');
}

menuBtn.addEventListener('click', openPanel);
closePanelBtn.addEventListener('click', closePanel);
sideOverlay.addEventListener('click', closePanel);

// ── Load Goals ────────────────────────────────────────────────
async function loadGoals() {
    goalsList.innerHTML = '<div class="panel-loading">Loading...</div>';
    try {
        const res  = await fetch('/api/goals?status=active');
        const data = await res.json();
        const goals = data.goals || [];
        if (!goals.length) {
            goalsList.innerHTML = '<div class="panel-empty">No active goals. Say "add goal &lt;title&gt;"</div>';
            return;
        }
        goalsList.innerHTML = goals.map(g => `
            <div class="panel-item goal-item" data-id="${g.id}">
                <span class="goal-pri ${g.priority}">${priIcon(g.priority)}</span>
                <span class="goal-title">${escHtml(g.title)}</span>
                <button class="done-btn" onclick="completeGoal(${g.id})" title="Mark done">✓</button>
            </div>
        `).join('');
    } catch {
        goalsList.innerHTML = '<div class="panel-empty">Could not load goals.</div>';
    }
}

function priIcon(p) {
    return p === 'high' ? '🔴' : p === 'low' ? '🟢' : '🟡';
}

async function completeGoal(id) {
    await fetch(`/api/goals/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'done' }),
    });
    loadGoals();
    showToast('Goal complete! 🎉');
}

// Add goal via form
addGoalForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = newGoalInput.value.trim();
    if (!title) return;
    newGoalInput.value = '';
    await fetch('/api/goals', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
    });
    loadGoals();
    showToast('Goal added! 💪');
});

// ── Load Events ───────────────────────────────────────────────
async function loadEvents() {
    eventsList.innerHTML = '<div class="panel-loading">Loading...</div>';
    try {
        const res  = await fetch('/api/events?hours=72');
        const data = await res.json();
        const due    = data.due    || [];
        const events = data.events || [];

        if (!due.length && !events.length) {
            eventsList.innerHTML = '<div class="panel-empty">No upcoming reminders. Say "remind me to..."</div>';
            return;
        }

        const dueHtml = due.map(e => `
            <div class="panel-item event-item due">
                <span>🔴 DUE: ${escHtml(e.title)}</span>
                <button class="done-btn" onclick="markEventDone(${e.id})" title="Dismiss">✓</button>
            </div>
        `).join('');

        const upHtml = events.map(e => {
            const t = (e.event_time || '').slice(0, 16).replace('T', ' ');
            return `
                <div class="panel-item event-item">
                    <span>🔔 ${t ? '<small>' + escHtml(t) + '</small><br>' : ''}${escHtml(e.title)}</span>
                    <button class="done-btn" onclick="markEventDone(${e.id})" title="Dismiss">✓</button>
                </div>`;
        }).join('');

        eventsList.innerHTML = dueHtml + upHtml;
    } catch {
        eventsList.innerHTML = '<div class="panel-empty">Could not load reminders.</div>';
    }
}

async function markEventDone(id) {
    await fetch(`/api/events/${id}/done`, { method: 'PATCH' });
    loadEvents();
    showToast('Reminder dismissed ✓');
}

// ── Quick chips ───────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(btn => {
    btn.addEventListener('click', () => {
        const msg = btn.getAttribute('data-msg');
        if (!msg) return;
        closePanel();
        // Fire into the main chat input and submit
        const input = document.getElementById('textInput');
        if (input) {
            input.value = msg;
            document.getElementById('sendBtn')?.click();
        }
    });
});

// ── Agent badge (shown after each response) ───────────────────
window.showAgentBadge = function(agent) {
    if (!agent || agent === 'chat') { agentBadge.textContent = ''; return; }
    const icons = {
        music: '🎵', goal: '🎯', reminder: '🔔', reflection: '📋',
        search: '🔍', research: '📚', coding: '💻', image: '🖼️',
    };
    agentBadge.textContent = (icons[agent] || '⚡') + ' ' + agent.toUpperCase();
    agentBadge.style.opacity = '1';
    setTimeout(() => { agentBadge.style.opacity = '0.3'; }, 4000);
};

// ── Toast notification ────────────────────────────────────────
function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add('show'), 10);
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 400); }, 2500);
}

// ── Helpers ───────────────────────────────────────────────────
function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Expose for script.js to call after each response
window.onJarvisResponse = function(data) {
    showAgentBadge(data.agent);
    // Auto-refresh panel if it's open and agent is goal/reminder
    if (sidePanel.classList.contains('open')) {
        if (['goal','reminder'].includes(data.agent)) {
            loadGoals();
            loadEvents();
        }
    }
};
