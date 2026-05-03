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
    
    if (typeof AGENT_MODE !== 'undefined' && AGENT_MODE === 'autonomous') {
        loadProposedActions();
        
        // Setup filter listeners
        const filterInput = document.getElementById('action-filter');
        const severitySelect = document.getElementById('severity-filter');
        if (filterInput) filterInput.addEventListener('input', renderActionTable);
        if (severitySelect) severitySelect.addEventListener('change', renderActionTable);
    }

    // Auto-refresh
    setInterval(loadLogs, 5000);
    setInterval(loadActivity, 5000);
    if (typeof AGENT_MODE !== 'undefined' && AGENT_MODE === 'autonomous') {
        setInterval(loadProposedActions, 10000);
    }
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

        listEl.innerHTML = data.activities.map(act => {
            const details = act.details || {};
            const objective = details.objective || 'No objective specified';
            const analysis = details.analysis || 'Analysis pending...';
            
            return `
                <div style="background: rgba(255,255,255,0.03); border-radius: 8px; padding: 20px; margin-bottom: 20px; border-left: 4px solid #4fc3f7;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <div style="font-size: 0.8rem; color: #888;">${act.timestamp}</div>
                        <div style="font-size: 0.8rem; background: rgba(79, 195, 247, 0.2); color: #4fc3f7; padding: 2px 8px; border-radius: 4px;">Action: ${act.action_taken}</div>
                    </div>
                    <h3 style="margin: 0 0 10px 0; font-size: 1.1rem; color: #fff;">${act.summary}</h3>
                    <div style="color: #ccc; font-size: 0.9rem; line-height: 1.5;">Objective: ${objective}</div>
                    <div style="margin-top: 15px; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 6px; font-family: monospace; font-size: 0.8rem; color: #aaa; white-space: pre-wrap;">${analysis}</div>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Failed to load activity", err);
    }
}

let _localActions = [];

async function loadProposedActions() {
    const listEl = document.getElementById('proposed-actions-body');
    if (!listEl) return;

    try {
        const res = await fetch(`/api/agents/actions/${AGENT_ID}`);
        const data = await res.json();
        
        _localActions = data.actions || [];
        renderActionTable();
        updateSummaryStats();
    } catch (err) {
        console.error("Failed to load proposed actions", err);
    }
}

function renderActionTable() {
    const listEl = document.getElementById('proposed-actions-body');
    if (!listEl) return;

    const filterText = (document.getElementById('action-filter')?.value || '').toLowerCase();
    const severityFilter = document.getElementById('severity-filter')?.value || '';

    const filtered = _localActions.filter(act => {
        const matchesText = act.description.toLowerCase().includes(filterText) || 
                          (act.command && act.command.toLowerCase().includes(filterText));
        const matchesSeverity = !severityFilter || act.severity === severityFilter;
        return matchesText && matchesSeverity;
    });

    if (filtered.length === 0) {
        listEl.innerHTML = `<tr><td colspan="4" style="padding: 40px; text-align: center; color: #555;">No actions match your filters.</td></tr>`;
        return;
    }

    listEl.innerHTML = filtered.map(act => {
        const severityColors = {
            'Critical': '#ef5350',
            'High': '#ff7043',
            'Medium': '#ffca28',
            'Low': '#9ccc65'
        };
        const color = severityColors[act.severity] || '#888';
        
        const isRun = act.action_type === 'Run';
        
        return `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 15px 20px;">
                    <div style="font-weight: 500; color: #fff; margin-bottom: 4px;">${act.description}</div>
                    <div style="font-size: 0.75rem; color: #666;">ID: ACTION-${act.id} • ${act.timestamp}</div>
                </td>
                <td style="padding: 15px 20px;">
                    <span style="color: ${color}; background: ${color}22; border: 1px solid ${color}44; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: bold; text-transform: uppercase;">
                        ${act.severity}
                    </span>
                </td>
                <td style="padding: 15px 20px;">
                    <code style="background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px; color: #aaa; font-size: 0.75rem;">${act.command || 'N/A'}</code>
                </td>
                <td style="padding: 15px 20px; text-align: center;">
                    ${isRun ? `
                        <button class="btn-primary" style="padding: 5px 15px; font-size: 0.75rem;" onclick="executeAction(${act.id})">Run</button>
                    ` : `
                        <span style="font-size: 0.75rem; color: #888; font-style: italic;">Manual</span>
                    `}
                </td>
            </tr>
        `;
    }).join('');
}

function updateSummaryStats() {
    const pendingCount = _localActions.length;
    const criticalCount = _localActions.filter(a => a.severity === 'Critical' || a.severity === 'High').length;
    
    const pendEl = document.getElementById('stat-pending');
    const critEl = document.getElementById('stat-critical');
    
    if (pendEl) pendEl.textContent = pendingCount;
    if (critEl) critEl.textContent = criticalCount;
}

async function executeAction(actionId) {
    if (!confirm('Are you sure you want to execute this remediation command?')) return;

    try {
        const res = await fetch(`/api/agents/actions/run/${actionId}`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'success') {
            alert('Action initiated successfully. Check Activity Feed for results.');
            loadProposedActions();
            loadActivity();
        } else {
            alert('Error executing action: ' + data.message);
        }
    } catch (err) {
        console.error("Execution failed", err);
        alert('Failed to connect to backend for execution.');
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
