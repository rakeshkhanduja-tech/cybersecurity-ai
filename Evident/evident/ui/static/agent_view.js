/**
 * agent_view.js — Frontend logic for the dedicated Agent Deep-Dive Window
 */

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupControls();

    if (AGENT_MODE !== 'autonomous') {
        setupChat();
    }

    // Initial data load
    loadLogs();
    loadActivity();

    // Auto-refresh every 5 seconds
    setInterval(loadLogs, 5000);
    setInterval(loadActivity, 5000);
});

function setupTabs() {
    const tabs = document.querySelectorAll('.agent-tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.agent-tab-content').forEach(c => c.classList.remove('active'));

            tab.classList.add('active');
            const contentId = tab.getAttribute('data-tab');
            document.getElementById(contentId).classList.add('active');

            if (contentId === 'tab-logs') loadLogs();
            if (contentId === 'tab-activity') loadActivity();
        });
    });
}

function setupControls() {
    const btnPause = document.getElementById('btn-agent-pause');
    const btnResume = document.getElementById('btn-agent-resume');

    if (btnPause) {
        btnPause.addEventListener('click', async () => {
            const res = await fetch(`/api/agents/pause/${AGENT_ID}`, { method: 'POST' });
            if (res.ok) {
                btnPause.style.display = 'none';
                btnResume.style.display = 'block';
                document.getElementById('agent-status-label').textContent = 'Paused';
                document.getElementById('agent-status-label').style.color = '#ffca28';
            }
        });
    }

    if (btnResume) {
        btnResume.addEventListener('click', async () => {
            const res = await fetch(`/api/agents/resume/${AGENT_ID}`, { method: 'POST' });
            if (res.ok) {
                btnResume.style.display = 'none';
                btnPause.style.display = 'block';
                document.getElementById('agent-status-label').textContent = 'Running';
                document.getElementById('agent-status-label').style.color = '#2ecc71';
            }
        });
    }
}

async function loadLogs() {
    const listEl = document.getElementById('agent-log-list');
    if (!listEl) return;

    try {
        const res = await fetch(`/api/agents/logs/${AGENT_ID}?limit=100`);
        const data = await res.json();

        if (data.logs.length === 0) {
            listEl.innerHTML = '<div style="padding: 20px; color: #555;">No logs available yet.</div>';
            return;
        }

        listEl.innerHTML = data.logs.map(log => {
            const traceColor = log.level === 'ERROR' ? '#ef5350' : '#4fc3f7';
            return `
                <div class="log-entry">
                    <span class="log-ts">[${log.timestamp.split(' ')[1]}]</span>
                    <span class="log-level ${log.level}">${log.level}</span>
                    <span class="log-msg">${log.message}</span>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Failed to load logs", err);
    }
}

async function loadActivity() {
    const listEl = document.getElementById('tab-activity');
    if (!listEl) return;

    try {
        const res = await fetch(`/api/agents/activity/${AGENT_ID}?limit=50`);
        const data = await res.json();

        if (data.activities.length === 0) {
            listEl.innerHTML = '<div style="padding: 20px; color: #555;">No activity recorded yet for this agent.</div>';
            return;
        }

        listEl.innerHTML = data.activities.map(act => `
            <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #4fc3f7;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <div style="font-size: 0.8rem; color: #888;">${act.timestamp}</div>
                    <div style="font-size: 0.8rem; background: rgba(79, 195, 247, 0.2); color: #4fc3f7; padding: 2px 8px; border-radius: 4px;">Action: ${act.action_taken}</div>
                </div>
                <h3 style="margin: 0 0 10px 0; font-size: 1.1rem; color: #fff;">${act.summary}</h3>
                <div style="color: #ccc; font-size: 0.9rem; line-height: 1.5;">Objective: ${act.details.objective}</div>
                <div style="margin-top: 15px; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; font-family: monospace; font-size: 0.8rem; color: #aaa; white-space: pre-wrap;">${act.details.analysis}</div>
            </div>
        `).join('');

    } catch (err) {
        console.error("Failed to load activity", err);
    }
}

function setupChat() {
    const btnSend = document.getElementById('btn-agent-send');
    const input = document.getElementById('agent-chat-input');
    const messages = document.getElementById('agent-chat-messages');

    if (!btnSend || !input) return;

    btnSend.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        // Add user message
        appendMessage('user', text);
        input.value = '';

        try {
            const res = await fetch('/api/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question: text })
            });
            const data = await res.json();
            appendMessage('agent', data.answer);
        } catch (err) {
            appendMessage('error', 'Failed to communicate with intelligence engine.');
        }
    }

    function appendMessage(role, text) {
        const msg = document.createElement('div');
        msg.className = `message ${role}-message`;
        msg.innerHTML = `<div class="message-content">${text}</div>`;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
    }
}
