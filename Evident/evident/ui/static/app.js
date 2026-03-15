// Evident Security Intelligence Agent - Frontend JavaScript

let isProcessing = false;
let currentSource = null;
let cy = null; // Cytoscape instance

// Poll /api/status until agent is ready, then dismiss loading screen
async function waitForAgent() {
    const overlay = document.getElementById('loading-overlay');
    const msgEl = document.getElementById('loading-message');
    const stepsEl = document.getElementById('loading-steps');
    const loadingBar = document.getElementById('loading-bar');
    let renderedSteps = [];

    while (true) {
        try {
            const res = await fetch('/api/status');
            if (res.ok) {
                const data = await res.json();

                // Update progress bar
                const progress = Math.min(95, (data.log.length / 5) * 100); // Assuming 5 steps for 100%
                if (loadingBar) {
                    loadingBar.style.width = `${progress}%`;
                }

                // Update steps log
                if (data.log && data.log.length > 0) {
                    stepsEl.innerHTML = ''; // Clear existing steps
                    data.log.forEach((step, index) => {
                        const stepItem = document.createElement('div');
                        const isLast = (index === data.log.length - 1);
                        stepItem.className = `loading-step-item ${isLast ? 'step-current' : 'step-done'}`;
                        stepItem.innerHTML = `
                            <span class="step-icon">${isLast ? '⚙️' : '✓'}</span>
                            <span class="step-text">${step}</span>
                        `;
                        stepsEl.appendChild(stepItem);
                    });
                    // Scroll to bottom
                    stepsEl.scrollTop = stepsEl.scrollHeight;
                }

                // Show current in-progress step
                msgEl.textContent = data.step;

                if (data.ready) {
                    // Mark all as done
                    stepsEl.querySelectorAll('.loading-step-item').forEach(el => {
                        el.classList.remove('step-current');
                        el.classList.add('step-done');
                        el.querySelector('.step-icon').textContent = '✅';
                    });
                    if (loadingBar) {
                        loadingBar.style.width = '100%';
                    }
                    await new Promise(r => setTimeout(r, 800));
                    overlay.classList.add('hidden');
                    break;
                }
            }
        } catch (e) {
            msgEl.textContent = 'Connecting to server...';
        }
        await new Promise(r => setTimeout(r, 1200));
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', async function () {
    initializeUI();

    // Wait for the agent to initialize, then load data
    await waitForAgent();
    loadSources();
    loadStats();
});

function initializeUI() {
    setupModals();
    setupTabs();
    setupGraphControls();

    const refreshBtn = document.getElementById('btn-refresh-graph');
    if (refreshBtn) refreshBtn.addEventListener('click', refreshGraph);
}

function setupGraphControls() {
    const layoutBtn = document.getElementById('btn-layout');
    const centerBtn = document.getElementById('btn-center');

    if (layoutBtn) {
        layoutBtn.addEventListener('click', () => {
            if (cy) {
                const layout = cy.layout({
                    name: 'cose',
                    animate: true,
                    animationDuration: 600,
                    padding: 30
                });
                layout.run();
            }
        });
    }

    if (centerBtn) {
        centerBtn.addEventListener('click', () => {
            if (cy) {
                cy.animate({
                    fit: {
                        eles: cy.elements(),
                        padding: 30
                    },
                    duration: 600
                });
            }
        });
    }
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - 'success', 'error', or 'info'
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</div>
        <div class="toast-message">${message}</div>
    `;

    // Create container if it doesn't exist
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// --- View Switching ---
function switchView(viewId) {
    console.log(`[UI] Switching to view: ${viewId}`);

    // Hide all view containers
    document.querySelectorAll('.view-container').forEach(v => v.classList.add('hidden-view'));

    // Show the target view
    const target = document.getElementById(`view-${viewId}`);
    if (target) {
        target.classList.remove('hidden-view');
    }

    // Update Header
    const titleEl = document.getElementById('view-name');
    const iconEl = document.getElementById('view-icon');
    const navItems = document.querySelectorAll('.nav-item');

    navItems.forEach(item => item.classList.remove('active'));

    const viewMeta = {
        'signals': { title: 'Active Signals', icon: '🛡️', btnId: 'btn-signals' },
        'chat': { title: 'Ask Evident', icon: '💬', btnId: 'btn-chat' },
        'data-plugs': { title: 'Data Plugs', icon: '🔗', btnId: 'btn-data-plugs' },
        'active-plugs': { title: 'Active Plugs', icon: '🔌', btnId: 'btn-active-plugs' },
        'active-agents': { title: 'Active Security Agents', icon: '🤖', btnId: 'btn-active-agents' },
        'agents': { title: 'Security Agents', icon: '🏗️', btnId: 'btn-agents' },
        'history': { title: 'Audit History', icon: '📜', btnId: 'btn-history' }
    };

    const meta = viewMeta[viewId];
    if (meta) {
        if (titleEl) titleEl.textContent = meta.title;
        if (iconEl) iconEl.textContent = meta.icon;
        const btn = document.getElementById(meta.btnId);
        if (btn) btn.classList.add('active');
    }

    // Load data for specific view
    if (viewId === 'active-plugs') loadActivePlugsView();
    if (viewId === 'history') loadHistoryView();
    if (viewId === 'active-agents') loadActiveAgentsView();
    if (viewId === 'agents') loadAllAgentsView();
    if (viewId === 'signals') {
        loadSources();
        loadStats();
    }
}

// --- Modals ---
function setupModals() {
    const settingsModal = document.getElementById('modal-settings');
    const dataPlugsModal = document.getElementById('modal-data-plugs');

    // Sidebar: Active Signals (Home)
    const btnSignals = document.getElementById('btn-signals');
    if (btnSignals) {
        btnSignals.addEventListener('click', () => {
            switchView('signals');
        });
    }

    // Sidebar: Ask Evident
    const btnChat = document.getElementById('btn-chat');
    if (btnChat) {
        btnChat.addEventListener('click', () => {
            switchView('chat');
        });
    }

    // Sidebar: Active Plugs
    const btnActivePlugs = document.getElementById('btn-active-plugs');
    if (btnActivePlugs) {
        btnActivePlugs.addEventListener('click', () => {
            switchView('active-plugs');
        });
    }

    // Sidebar: Data Plugs (Modal)
    document.getElementById('btn-data-plugs').addEventListener('click', () => {
        if (dataPlugsModal) {
            dataPlugsModal.classList.add('show');
            loadDataPlugsModal();
        }
    });

    // Sidebar: Settings (Modal)
    document.getElementById('btn-settings').addEventListener('click', () => {
        settingsModal.classList.add('show');
        loadSettingsConfig(); // Refactored to separate function
    });

    // Sidebar: Audit History
    const btnHistory = document.getElementById('btn-history');
    if (btnHistory) {
        btnHistory.addEventListener('click', () => {
            switchView('history');
        });
    }

    // Sidebar Placeholder: Active Security Agents
    const btnActiveAgents = document.getElementById('btn-active-agents');
    if (btnActiveAgents) {
        btnActiveAgents.addEventListener('click', () => {
            switchView('active-agents'); // Future view
        });
    }

    // Sidebar Placeholder: Security Agents
    const btnAgents = document.getElementById('btn-agents');
    if (btnAgents) {
        btnAgents.addEventListener('click', () => {
            switchView('agents');
        });
    }

    // Refresh Active Agents
    const btnRefreshActive = document.getElementById('btn-refresh-active-agents');
    if (btnRefreshActive) {
        btnRefreshActive.addEventListener('click', loadActiveAgentsView);
    }

    // Agent Config Modal Logic
    const modeSelect = document.getElementById('config-agent-mode');
    if (modeSelect) {
        modeSelect.addEventListener('change', () => {
            const freqGroup = document.getElementById('group-config-frequency');
            freqGroup.style.display = modeSelect.value === 'autonomous' ? 'block' : 'none';
        });
    }

    const btnSaveAgent = document.getElementById('btn-save-agent-config');
    if (btnSaveAgent) {
        btnSaveAgent.addEventListener('click', saveAgentProfile);
    }

    // Logo click goes home
    const logo = document.querySelector('.sidebar-logo');
    if (logo) {
        logo.style.cursor = 'pointer';
        logo.addEventListener('click', () => switchView('signals'));
    }

    document.querySelectorAll('.close-modal, .close-modal-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            modal.classList.remove('show');
        });
    });
}

// Move settings loading to separate function
async function loadSettingsConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();

        document.getElementById('settings-provider').value = data.provider || 'gemini';
        document.getElementById('settings-api-key').value = data.api_key || '';
        const schemaEl = document.getElementById('settings-schema');
        if (schemaEl) schemaEl.value = data.schema_preference || 'evident';

        const sourceModeEl = document.getElementById('settings-source-mode');
        if (sourceModeEl) {
            const currentMode = data.source_mode || 'sample';
            sourceModeEl.value = currentMode;
            updateSourceBadge(currentMode);
        }

        const stypeEl = document.getElementById('settings-storage-type');
        if (stypeEl && data.storage_config) {
            const s = data.storage_config;
            stypeEl.value = s.storage_type || 'local';
            // ... (storage fields population logic)
            populateStorageFields(s);
        }

        const modelSelect = document.getElementById('settings-model');
        modelSelect.innerHTML = `<option value="${data.model_id}">${data.model_id}</option>`;
        modelSelect.disabled = false;
    } catch (error) {
        console.error('Error loading config:', error);
    }
}
// Settings Modal Logic: Clear fetch context when provider changes
document.getElementById('settings-provider').addEventListener('change', () => {
    const modelSelect = document.getElementById('settings-model');
    modelSelect.disabled = true;
    modelSelect.innerHTML = '<option>Click Fetch Models</option>';
});

document.getElementById('btn-fetch-models').addEventListener('click', async () => {
    const provider = document.getElementById('settings-provider').value;
    const apiKey = document.getElementById('settings-api-key').value;
    const modelSelect = document.getElementById('settings-model');
    const fetchBtn = document.getElementById('btn-fetch-models');

    if (!provider) return;

    const originalText = fetchBtn.innerText;
    fetchBtn.innerText = 'Searching...';
    fetchBtn.disabled = true;

    try {
        // Note: If apiKey is masked (contains '...'), the backend list_models handles it by using stored key
        const response = await fetch('/api/models', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ provider, api_key: apiKey })
        });
        const data = await response.json();

        if (data.models && data.models.length > 0) {
            modelSelect.innerHTML = data.models.map(m => `<option value="${m}">${m}</option>`).join('');
            modelSelect.disabled = false;
            console.log(`[UI] Discovered ${data.models.length} models via API`);
        } else {
            modelSelect.innerHTML = '<option>No models found</option>';
        }
    } catch (error) {
        console.error('Error fetching models:', error);
        modelSelect.innerHTML = '<option>Error fetching models</option>';
    } finally {
        fetchBtn.innerText = originalText;
        fetchBtn.disabled = false;
    }
});

document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const provider = document.getElementById('settings-provider').value;
    const apiKey = document.getElementById('settings-api-key').value;
    const modelId = document.getElementById('settings-model').value;
    const schemaId = document.getElementById('settings-schema').value;
    const sourceMode = document.getElementById('settings-source-mode').value;
    const storageType = document.getElementById('settings-storage-type').value;

    // Storage specific fields
    const storageConfig = { storage_type: storageType };
    if (storageType === 'azure') {
        storageConfig.azure_account_name = document.getElementById('storage-azure-account').value;
        storageConfig.azure_container = document.getElementById('storage-azure-container').value;
        storageConfig.azure_keyvault_url = document.getElementById('storage-azure-vault').value;
        storageConfig.azure_secret_name = document.getElementById('storage-azure-secret').value;
    } else if (storageType === 'aws_s3') {
        storageConfig.aws_s3_bucket = document.getElementById('storage-aws-bucket').value;
        storageConfig.aws_region = document.getElementById('storage-aws-region').value;
        storageConfig.aws_secret_name = document.getElementById('storage-aws-secret').value;
    } else if (storageType === 'gcs') {
        storageConfig.gcp_project = document.getElementById('storage-gcs-project').value;
        storageConfig.gcs_bucket = document.getElementById('storage-gcs-bucket').value;
        storageConfig.gcp_secret_name = document.getElementById('storage-gcs-secret').value;
    }

    try {
        // Show loading overlay while agent rebuilds
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.classList.remove('hidden');
            document.getElementById('loading-message').textContent = 'Rebuilding intelligence layer for new data source...';
        }

        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider,
                api_key: apiKey,
                model_id: modelId,
                schema_preference: schemaId,
                source_mode: sourceMode,
                storage_config: storageConfig
            })
        });

        // Wait for agent to be ready again (it will be rebuilding in background)
        await waitForAgent();

        showToast('Configuration saved and intelligence layer rebuilt!', 'success');
        updateSourceBadge(sourceMode);
        settingsModal.classList.remove('show');
        loadStats();
        loadSources();
    } catch (error) {
        console.error(error);
        alert('Failed to save config');
    }
});

function populateStorageFields(s) {
    if (s.storage_type === 'azure') {
        document.getElementById('storage-azure-account').value = s.azure_account_name || '';
        document.getElementById('storage-azure-container').value = s.azure_container || '';
        document.getElementById('storage-azure-vault').value = s.azure_keyvault_url || '';
        document.getElementById('storage-azure-secret').value = s.azure_secret_name || '';
    } else if (s.storage_type === 'aws_s3') {
        document.getElementById('storage-aws-bucket').value = s.aws_s3_bucket || '';
        document.getElementById('storage-aws-region').value = s.aws_region || '';
        document.getElementById('storage-aws-secret').value = s.aws_secret_name || '';
    } else if (s.storage_type === 'gcs') {
        document.getElementById('storage-gcs-project').value = s.gcp_project || '';
        document.getElementById('storage-gcs-bucket').value = s.gcs_bucket || '';
        document.getElementById('storage-gcs-secret').value = s.gcp_secret_name || '';
    }
    toggleStorageFields();
}

async function loadActivePlugsView() {
    const listContainer = document.getElementById('view-active-plugs-list');

    listContainer.innerHTML = '<div class="loading">Fetching active plugs...</div>';

    try {
        const res = await fetch('/api/connectors/active');
        const data = await res.json();
        const plugs = data.active || [];

        // Update summary stats
        const totalRecords = plugs.reduce((sum, p) => sum + (p.records_generated || 0), 0);
        const runningCount = plugs.filter(p => !p.scheduler_paused).length;
        const pausedCount = plugs.filter(p => p.scheduler_paused).length;
        const setEl = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        setEl('ap-stat-total', plugs.length);
        setEl('ap-stat-records', totalRecords.toLocaleString());
        setEl('ap-stat-running', runningCount);
        setEl('ap-stat-paused', pausedCount);

        if (plugs.length === 0) {
            listContainer.innerHTML = `
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:200px; opacity:0.5; gap:12px;">
                    <span style="font-size:2.5rem;">🔌</span>
                    <p>No active data plugs found. Configure connectors via <strong>Data Plugs</strong>.</p>
                </div>`;
            return;
        }

        listContainer.innerHTML = plugs.map(plug => {
            const isPaused = plug.scheduler_paused;
            const statusColor = isPaused ? '#ffca28' : '#66bb6a';
            const statusLabel = isPaused ? 'Paused' : 'Running';
            const statusIcon = isPaused ? '⏸️' : '▶️';
            const lastRun = plug.last_run ? new Date(plug.last_run).toLocaleString() : 'Never';
            const displayName = plug.connector_id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

            return `
            <div class="active-plug-card" style="
                background: rgba(255,255,255,0.03);
                border: 1px solid rgba(255,255,255,0.08);
                border-left: 3px solid ${statusColor};
                border-radius: 12px;
                padding: 18px 20px;
                margin-bottom: 14px;
                display: grid;
                grid-template-columns: auto 1fr auto;
                gap: 16px;
                align-items: center;
                transition: background 0.2s;">
                <!-- Status Icon -->
                <div style="font-size:1.8rem; width:48px; height:48px; background: rgba(255,255,255,0.04); border-radius:10px; display:flex; align-items:center; justify-content:center;">
                    ${statusIcon}
                </div>
                <!-- Info -->
                <div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:5px;">
                        <h4 style="margin:0; font-size:1rem; color:#e8eaf6;">${displayName}</h4>
                        <span style="font-size:0.7rem; font-weight:600; padding:2px 8px; border-radius:20px; background: ${isPaused ? 'rgba(255,202,40,0.12)' : 'rgba(102,187,106,0.12)'}; color:${statusColor}; border: 1px solid ${statusColor}40;">${statusLabel}</span>
                    </div>
                    <div style="display:flex; gap:20px; font-size:0.78rem; color:#9fa8da;">
                        <span title="Last run time">🕐 ${lastRun}</span>
                        <span title="Records ingested">📊 ${(plug.records_generated || 0).toLocaleString()} records</span>
                        <span title="Schedule interval">⏱️ Every ${plug.interval_minutes || '?'}m</span>
                    </div>
                </div>
                <!-- Actions -->
                <div style="display:flex; gap:8px; flex-shrink:0;">
                    <button onclick="runConnectorNow('${plug.connector_id}')" class="btn-primary" style="padding:7px 14px; font-size:0.78rem;" title="Trigger immediate run">
                        ▶ Run Now
                    </button>
                    ${isPaused
                    ? `<button onclick="resumeConnector('${plug.connector_id}')" class="btn-secondary" style="padding:7px 14px; font-size:0.78rem;" title="Resume scheduler">▶ Resume</button>`
                    : `<button onclick="pauseConnector('${plug.connector_id}')" class="btn-secondary" style="padding:7px 14px; font-size:0.78rem;" title="Pause scheduler">⏸ Pause</button>`
                }
                    <button onclick="viewConnectorLogs('${plug.connector_id}')" class="btn-secondary" style="padding:7px 14px; font-size:0.78rem;" title="View connector logs">
                        📋 Logs
                    </button>
                </div>
            </div>`;
        }).join('');

    } catch (e) {
        console.error('[UI] Failed to load active plugs:', e);
        listContainer.innerHTML = '<div class="error-text" style="padding:20px;">Failed to load active plugs. Check server connection.</div>';
    }
}

async function pauseConnector(connectorId) {
    try {
        await fetch(`/api/connectors/pause/${connectorId}`, { method: 'POST' });
        showToast(`Paused ${connectorId}`, 'info');
        loadActivePlugsView(); // Refresh
    } catch (e) {
        showToast(`Failed to pause ${connectorId}`, 'error');
    }
}

async function resumeConnector(connectorId) {
    try {
        await fetch(`/api/connectors/resume/${connectorId}`, { method: 'POST' });
        showToast(`Resumed ${connectorId}`, 'success');
        loadActivePlugsView(); // Refresh
    } catch (e) {
        showToast(`Failed to resume ${connectorId}`, 'error');
    }
}

async function loadHistoryView() {
    const listContainer = document.getElementById('view-history-list');
    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        if (!data.history || data.history.length === 0) {
            listContainer.innerHTML = '<li class="history-item">No history yet</li>';
            return;
        }

        listContainer.innerHTML = '';
        data.history.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'history-item';
            if (index === 0) li.classList.add('active'); // Default selection
            li.innerHTML = `
                <div class="history-item-header">
                    <span class="history-item-time">${new Date(item.timestamp).toLocaleString()}</span>
                    <span class="history-item-schema">${item.schema || 'evident'}</span>
                </div>
                <div class="history-item-query">${item.query}</div>
            `;
            li.addEventListener('click', () => showHistoryViewDetails(item, li));
            listContainer.appendChild(li);

            if (index === 0) showHistoryViewDetails(item, li);
        });

    } catch (error) {
        listContainer.innerHTML = '<li class="history-item">Error loading history</li>';
    }
}

function showHistoryViewDetails(item, element) {
    document.querySelectorAll('#view-history-list .history-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    const detailsContainer = document.getElementById('view-history-details-content');

    let stepsHtml = '';
    if (item.execution_steps && item.execution_steps.length > 0) {
        stepsHtml = item.execution_steps.map(step => `
            <div class="step-card" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div class="step-header" style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span class="step-name" style="font-weight: 600; font-size: 0.8rem; color: #4fc3f7;">${step.step}</span>
                    <span class="step-time" style="font-size: 0.75rem; color: #666;">${new Date(step.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="step-desc" style="font-size: 0.8rem; color: #aaa;">${step.description}</div>
            </div>
        `).join('');
    } else {
        stepsHtml = '<div class="step-card">No execution steps recorded</div>';
    }

    detailsContainer.innerHTML = `
        <h3 style="margin-top: 0;">Interaction Details</h3>
        <p><strong>Query:</strong> ${item.query}</p>
        <p><strong>Response:</strong> ${item.response}</p>
        <div style="margin: 20px 0; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px;">
            <h4>Execution Trace</h4>
            ${stepsHtml}
        </div>
        <div style="font-size: 0.85rem; color: #888; background: rgba(0,0,0,0.1); padding: 15px; border-radius: 8px;">
            <p style="margin: 0 0 5px 0;">Tokens: ${item.tokens || 0} | Cost: $${(item.cost || 0).toFixed(4)}</p>
            <p style="margin: 0;">Context Summary: ${item.context_summary || 'N/A'}</p>
        </div>
    `;
}

window.toggleStorageFields = function () {
    const typeEl = document.getElementById('settings-storage-type');
    if (!typeEl) return;
    const type = typeEl.value;
    document.querySelectorAll('.storage-optional-fields').forEach(el => el.classList.add('hidden'));
    const activeGroup = document.getElementById(`storage-fields-${type.replace('_s3', '')}`);
    if (activeGroup) activeGroup.classList.remove('hidden');
};

function updateSourceBadge(mode) {
    const badge = document.getElementById('active-source-badge');
    if (!badge) return;

    if (mode === 'sample') {
        badge.innerText = 'SAMPLE DATA';
        badge.style.color = '#00e5ff';
        badge.style.borderColor = 'rgba(0, 229, 255, 0.2)';
    } else if (mode === 'livedata') {
        badge.innerText = 'LOCAL LIVEDATA';
        badge.style.color = '#ff9100';
        badge.style.borderColor = 'rgba(255, 145, 0, 0.2)';
    } else {
        badge.innerText = 'CLOUD STORAGE';
        badge.style.color = '#7c4dff';
        badge.style.borderColor = 'rgba(124, 77, 255, 0.2)';
    }
}

async function refreshGraph() {
    const btn = document.getElementById('btn-refresh-graph');
    if (!btn) return;

    const originalContent = btn.innerHTML;
    btn.innerHTML = '⏳';
    btn.disabled = true;

    // Use the toast system if available, else alert
    if (window.showToast) showToast('Regenerating Knowledge Graph...', 'info');
    else console.log('Regenerating Knowledge Graph...');

    try {
        const res = await fetch('/api/rebuild-graph', { method: 'POST' });
        const result = await res.json();

        if (result.status === 'success') {
            if (window.showToast) showToast(`Graph rebuilt with ${result.entities} entities!`, 'success');
            else alert(`Graph rebuilt with ${result.entities} entities!`);
            loadStats();
            loadSources();
        } else {
            if (window.showToast) showToast('Failed to rebuild graph.', 'error');
            else alert('Failed to rebuild graph.');
        }
    } catch (err) {
        console.error('Error rebuilding graph:', err);
    } finally {
        btn.innerHTML = originalContent;
        btn.disabled = false;
    }
}

async function runConnectorNow(connectorId) {
    if (window.showToast) showToast(`Triggering ingestion for ${connectorId}...`, 'info');
    try {
        const res = await fetch(`/api/connectors/run/${connectorId}`, { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            if (window.showToast) showToast(`Successfully triggered ${connectorId}`, 'success');
        } else {
            if (window.showToast) showToast(`Failed to trigger ${connectorId}`, 'error');
        }
    } catch (e) {
        console.error(e);
        if (window.showToast) showToast('Error triggering connector', 'error');
    }
}

function viewConnectorLogs(connectorId) {
    const logsModal = document.getElementById('modal-logs');
    if (logsModal) {
        logsModal.classList.add('show');
        loadConnectorLogs(connectorId);
    }
}

async function loadConnectorLogs(connectorId) {
    const listEl = document.getElementById('logs-list');
    const titleEl = document.getElementById('logs-modal-title');
    const contentEl = document.getElementById('log-content-panel');

    if (titleEl) titleEl.textContent = `Logs: ${connectorId}`;
    listEl.innerHTML = 'Loading...';
    contentEl.innerHTML = '<div class="placeholder-text">Select a log file on the left to view contents.</div>';

    try {
        const res = await fetch(`/api/connectors/logs/${connectorId}`);
        const data = await res.json();

        if (!data.logs || data.logs.length === 0) {
            listEl.innerHTML = '<div class="placeholder-text" style="padding: 10px;">No logs found for this connector.</div>';
            return;
        }

        listEl.innerHTML = data.logs.map(log => `
            <div class="history-item" onclick="showLogFileContent('${connectorId}', '${log}')">
                <div style="font-size: 0.8rem; word-break: break-all;">${log}</div>
            </div>
        `).join('');

    } catch (e) {
        listEl.innerHTML = '<div class="error">Failed to load logs</div>';
    }
}

window.showLogFileContent = async function (connectorId, filename) {
    const contentEl = document.getElementById('log-content-panel');
    contentEl.innerHTML = '<div class="loading">Reading log file...</div>';

    // Highlight active
    document.querySelectorAll('#logs-list .history-item').forEach(el => el.classList.remove('active'));
    // Find the item clicked (this is a bit hacky with onclick strings, but let's assume it works for now)

    try {
        const res = await fetch(`/api/connectors/logs/${connectorId}/${filename}`);
        const data = await res.json();

        if (data.content) {
            contentEl.innerHTML = `<pre style="margin: 0; padding: 20px; font-family: monospace; font-size: 0.85rem; color: #fff; white-space: pre-wrap; background: rgba(0,0,0,0.3); border-radius: 8px;">${data.content}</pre>`;
        } else {
            contentEl.innerHTML = '<div class="error">Log file is empty or could not be read.</div>';
        }
    } catch (e) {
        contentEl.innerHTML = '<div class="error">Error reading log file.</div>';
    }
};


// --- Data Plugs Logic ---
let _allDataPlugs = [];
let _dbConfigs = {};

async function loadDataPlugsModal() {
    const listEl = document.getElementById('connectors-browse-list');
    listEl.innerHTML = 'Loading...';

    try {
        // Fetch static plug specs
        const specsRes = await fetch('/api/connectors');
        const specsData = await specsRes.json();
        _allDataPlugs = specsData.connectors || [];

        // Fetch saved configs from DB
        const configRes = await fetch('/api/connectors/config');
        const configData = await configRes.json();
        _dbConfigs = configData.configs || {};

        renderConnectorList();

        // Add search listener
        const searchInput = document.getElementById('connector-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                const term = e.target.value.toLowerCase();
                renderConnectorList(term);
            });
        }

        // Auto-select first connector if list is not empty
        if (_allDataPlugs.length > 0) {
            renderPlugConfig(_allDataPlugs[0].id);
        } else {
            document.getElementById('connector-config-panel').innerHTML = '<div class="placeholder-text">No plugins defined in data_plugs.json</div>';
        }

    } catch (e) {
        listEl.innerHTML = '<div class="error">Failed to load extensions</div>';
    }
}

function renderConnectorList(filterTerm = '') {
    const listEl = document.getElementById('connectors-browse-list');

    let filtered = _allDataPlugs;
    if (filterTerm) {
        filtered = _allDataPlugs.filter(c =>
            c.name.toLowerCase().includes(filterTerm) ||
            c.category.toLowerCase().includes(filterTerm) ||
            c.description.toLowerCase().includes(filterTerm)
        );
    }

    let grouped = {};
    filtered.forEach(c => {
        if (!grouped[c.category]) grouped[c.category] = [];
        grouped[c.category].push(c);
    });

    let html = '';
    for (let cat in grouped) {
        html += `<h4 style="margin: 10px 0 5px 0; color: #4fc3f7; text-transform: uppercase; font-size: 0.8rem;">${cat}</h4>`;
        grouped[cat].forEach(c => {
            const isActive = _dbConfigs[c.id] && _dbConfigs[c.id].is_active;
            const statusDot = isActive ? '<span style="color:#00e676; font-size:12px;">●</span>' : '<span style="color:#ff5252; font-size:12px;">○</span>';

            html += `
                <div class="history-item" onclick="renderPlugConfig('${c.id}')" style="padding: 8px; margin-bottom: 4px;">
                     <div style="display:flex; justify-content:space-between; align-items:center;">
                         <strong>${c.icon} ${c.name}</strong>
                         ${statusDot}
                     </div>
                     <div style="font-size: 0.75rem; color:#888; margin-top:4px;">${c.description}</div>
                </div>
            `;
        });
    }

    listEl.innerHTML = html || '<div class="placeholder-text" style="padding: 20px;">No connectors found matching your search.</div>';
}

function renderPlugConfig(plugId) {
    const plug = _allDataPlugs.find(p => p.id === plugId);
    if (!plug) return;

    const dbEntry = _dbConfigs[plugId] || { config: {}, is_active: false };
    const savedConf = dbEntry.config;
    const isActive = dbEntry.is_active;

    const panel = document.getElementById('connector-config-panel');
    let html = `
        <h3 style="margin-top:0;">${plug.icon} ${plug.name}</h3>
        <p style="font-size:0.85rem; color:#aaa; margin-bottom:15px">${plug.description}</p>
        
        <div style="margin-bottom: 20px;">
            <label style="display:flex; align-items:center; cursor:pointer;">
                <input type="checkbox" id="plug-active-${plug.id}" ${isActive ? 'checked' : ''} style="margin-right:8px;">
                <span style="font-weight:bold;">Enable Connector</span>
            </label>
            <p style="font-size: 0.7rem; color:#888; margin-top:4px; margin-left: 20px;">When enabled, data will be actively ingested during batch cycles.</p>
        </div>
        
        <form id="form-plug-${plug.id}" onsubmit="savePlugConfig(event, '${plug.id}')">
            
            <div style="margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 15px;">
                <p style="font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #4fc3f7; font-weight: 600; margin: 0 0 10px 0;">Signals to Fetch</p>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
                    ${(plug.supported_signals || []).map(s => {
        const isChecked = !savedConf.selected_signals || savedConf.selected_signals.includes(s);
        return `
                            <label style="display:flex; align-items:center; gap:8px; font-size: 0.85rem; cursor:pointer;">
                                <input type="checkbox" name="signal-${s}" value="${s}" ${isChecked ? 'checked' : ''}>
                                ${s.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </label>
                        `;
    }).join('')}
                </div>
            </div>
    `;

    // Generate inputs for parameters
    (plug.parameters || []).forEach(param => {
        const val = savedConf[param] || '';
        const isSecret = param.toLowerCase().includes('key') || param.toLowerCase().includes('secret') || param.toLowerCase().includes('password');
        const inputType = isSecret ? 'password' : 'text';

        html += `
            <div class="form-group" style="margin-bottom:12px;">
                <label style="text-transform: capitalize;">${param.replace(/_/g, ' ')}</label>
                <input type="${inputType}" name="${param}" value="${val}" style="width:100%; padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.2); background:rgba(0,0,0,0.3); color:#fff;">
            </div>
        `;
    });

    // Poll Interval
    const interval = dbEntry.interval_minutes || 5;
    html += `
        <div class="form-group" style="margin-bottom:12px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.05);">
            <label>Poll Interval (Minutes)</label>
            <input type="number" id="plug-interval-${plug.id}" value="${interval}" min="1" max="1440" style="width:100%; padding:8px; border-radius:4px; border:1px solid rgba(255,255,255,0.2); background:rgba(0,0,0,0.3); color:#fff;">
        </div>
        
        <div style="margin-top: 20px; display:flex; justify-content:space-between; align-items:center;">
            <button type="button" onclick="testPlugConnection('${plug.id}')" class="btn-secondary">⚡ Test Connection</button>
            <button type="submit" class="btn-primary">Save Settings</button>
        </div>
    </form>
    `;

    panel.innerHTML = html;
}

window.testPlugConnection = async function (plugId) {
    const form = document.getElementById(`form-plug-${plugId}`);
    const formData = new FormData(form);
    const configData = {};
    for (let [key, value] of formData.entries()) {
        if (!key.startsWith('signal-')) {
            configData[key] = value;
        }
    }

    const btn = event.currentTarget;
    const originalText = btn.innerText;
    btn.innerText = 'Testing...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/connectors/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                connector_id: plugId,
                config: configData
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            showToast(`Connection to ${plugId} successful!`, 'success');
        } else {
            showToast(`Connection failed: ${data.message}`, 'error');
        }
    } catch (e) {
        showToast(`Error testing connection: ${e.message}`, 'error');
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

window.savePlugConfig = async function (e, plugId) {
    e.preventDefault();
    const form = document.getElementById(`form-plug-${plugId}`);
    const formData = new FormData(form);

    const configData = {
        selected_signals: []
    };
    for (let [key, value] of formData.entries()) {
        if (key.startsWith('signal-')) {
            configData.selected_signals.push(value);
        } else {
            configData[key] = value;
        }
    }

    const isActive = document.getElementById(`plug-active-${plugId}`).checked;
    const interval = parseInt(document.getElementById(`plug-interval-${plugId}`).value) || 5;

    try {
        const res = await fetch('/api/connectors/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                connector_id: plugId,
                config: configData,
                is_active: isActive,
                interval: interval
            })
        });

        const resJson = await res.json();
        if (resJson.status === 'success') {
            alert('Connector settings saved!');
            loadDataPlugsModal(); // Refresh list to show active tick
        } else {
            alert('Failed: ' + resJson.error);
        }
    } catch (e) {
        alert('Exception saving config.');
    }
}

async function loadActivePlugsModal() {
    const listEl = document.getElementById('active-plugs-list');
    const schemaEl = document.getElementById('active-plugs-schema');
    listEl.innerHTML = 'Loading status...';

    try {
        const [configRes, activeRes] = await Promise.all([
            fetch('/api/config'),
            fetch('/api/connectors/active')
        ]);
        const currentConf = await configRes.json();
        const data = await activeRes.json();
        const active = data.active || [];

        schemaEl.textContent = currentConf.schema_preference ? currentConf.schema_preference.toUpperCase() : 'EVIDENT';

        if (active.length === 0) {
            listEl.innerHTML = '<div class="placeholder-text" style="display:flex; flex-direction:column; align-items:center; gap:12px; padding: 30px; text-align: center;"><span style="font-size: 1.8rem;">🔌</span><span>No active connections.<br/>Get Data via <strong style="color:#4fc3f7">"Data Plugs"</strong> configuration interface.</span></div>';
            return;
        }

        let html = '';
        active.forEach(c => {
            const isPaused = c.scheduler_paused;
            const statusLabel = isPaused ? '<span style="color:#f48fbf; font-size:0.65rem; border:1px solid #f48fbf; padding:1px 4px; border-radius:3px;">PAUSED</span>' : '<span style="color:#00e676; font-size:0.65rem; border:1px solid #00e676; padding:1px 4px; border-radius:3px;">RUNNING</span>';

            html += `
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 1px solid rgba(255,255,255,0.1); padding: 12px 0;">
                    <div style="flex: 1;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <strong style="color:#fff;">${c.connector_id}</strong>
                            ${statusLabel}
                        </div>
                        <div style="font-size:0.75rem; color:#888; margin-top:4px;">Last Run: ${c.last_run || 'Never'} • Refresh: ${c.interval_minutes}m</div>
                    </div>
                    <div style="text-align:right; margin-right: 20px;">
                        <span style="font-size: 1.1rem; font-weight:bold; color: #4fc3f7;">${c.records_generated}</span>
                        <div style="font-size:0.65rem; color:#888;">Records</div>
                    </div>
                    <div style="display:flex; gap:6px;">
                        <button onclick="viewLogs('${c.connector_id}')" class="btn-small" style="background: rgba(255,255,255,0.1); color: #fff; border: 1px solid rgba(255,255,255,0.2);" title="View execution logs">📋 Logs</button>
                        <button onclick="runConnectorNow('${c.connector_id}')" class="btn-small btn-run" title="Run manual pull now">⚡ Run</button>
                        ${isPaused
                    ? `<button onclick="resumeConnector('${c.connector_id}')" class="btn-small btn-resume">▶ Resume</button>`
                    : `<button onclick="pauseConnector('${c.connector_id}')" class="btn-small btn-pause">⏸ Pause</button>`
                }
                    </div>
                </div>
            `;
        });
        listEl.innerHTML = html;

    } catch (e) {
        listEl.innerHTML = '<div class="error">Failed to load active connections.</div>';
    }
}

async function pauseConnector(id) {
    try {
        await fetch(`/api/connectors/pause/${id}`, { method: 'POST' });
        loadActivePlugsModal();
    } catch (e) { console.error(e); }
}

async function resumeConnector(id) {
    try {
        await fetch(`/api/connectors/resume/${id}`, { method: 'POST' });
        loadActivePlugsModal();
    } catch (e) { console.error(e); }
}

async function runConnectorNow(id) {
    try {
        const btn = event.target;
        const original = btn.innerHTML;
        btn.innerHTML = '...';
        btn.disabled = true;

        await fetch(`/api/connectors/run/${id}`, { method: 'POST' });

        setTimeout(() => {
            btn.innerHTML = original;
            btn.disabled = false;
            loadActivePlugsModal();
        }, 1500);
    } catch (e) {
        console.error(e);
    }
}

// --- Logs Logic ---
async function viewLogs(connectorId) {
    const modal = document.getElementById('modal-logs');
    const title = document.getElementById('logs-modal-title');
    const listEl = document.getElementById('logs-list');

    title.textContent = `Logs: ${connectorId}`;
    listEl.innerHTML = 'Loading...';
    modal.classList.add('show');

    try {
        const res = await fetch(`/api/connectors/logs/${connectorId}`);
        const data = await res.json();
        const logs = data.logs || [];

        if (logs.length === 0) {
            listEl.innerHTML = '<div class="placeholder-text">No logs found.</div>';
            return;
        }

        listEl.innerHTML = logs.map(f => `
            <div class="history-item" onclick="loadLogFile('${f}')">
                <div style="font-size: 0.85rem;">${f.split('_')[1].substring(0, 2)}:${f.split('_')[1].substring(2, 4)}:${f.split('_')[1].substring(4, 6)}</div>
                <div style="font-size: 0.7rem; color: #888;">${f.split('_')[0]}</div>
            </div>
        `).join('');

        // Auto-load latest
        loadLogFile(logs[0]);
    } catch (e) {
        listEl.innerHTML = 'Error loading logs.';
    }
}

async function loadLogFile(filename) {
    const panel = document.getElementById('log-content-panel');
    panel.innerHTML = '<div class="placeholder-text">Loading log content...</div>';

    // Highlight active in list
    document.querySelectorAll('#logs-list .history-item').forEach(el => {
        if (el.innerText.includes(filename.split('_')[0])) el.classList.add('active');
        else el.classList.remove('active');
    });

    try {
        const res = await fetch(`/api/connectors/logs/view/${filename}`);
        const data = await res.json();

        if (data.error) {
            panel.innerHTML = `<div class="error">${data.error}</div>`;
            return;
        }

        let html = `
            <div style="padding: 20px;">
                <h4 style="margin-top:0; color:#4fc3f7;">File: ${filename}</h4>
                <div class="table-container" style="background: rgba(0,0,0,0.3); border-radius: 4px;">
                    <table style="width:100%; border-collapse: collapse; font-size: 0.8rem;">
                        <thead style="background: rgba(255,255,255,0.05);">
                            <tr>
                                <th style="padding:8px; text-align:left; border-bottom:1px solid #444;">Time</th>
                                <th style="padding:8px; text-align:left; border-bottom:1px solid #444;">Level</th>
                                <th style="padding:8px; text-align:left; border-bottom:1px solid #444;">Comp</th>
                                <th style="padding:8px; text-align:left; border-bottom:1px solid #444;">Message</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        data.data.forEach(row => {
            const levelColor = row.Level === 'ERROR' ? '#ff5252' : (row.Level === 'WARNING' ? '#ffb74d' : '#fff');
            html += `
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
                    <td style="padding:6px 8px; color:#aaa; white-space:nowrap;">${row.Timestamp.split(' ')[1]}</td>
                    <td style="padding:6px 8px; color:${levelColor}; font-weight:bold;">${row.Level}</td>
                    <td style="padding:6px 8px; color:#888;">${row.Component}</td>
                    <td style="padding:6px 8px;">${row.Message}</td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        panel.innerHTML = html;

    } catch (e) {
        panel.innerHTML = '<div class="error">Failed to load log file.</div>';
    }
}



// --- Tabs ---
function setupTabs() {
    document.querySelectorAll('.viz-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            // Remove active class from all tabs and views
            document.querySelectorAll('.viz-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.viz-view').forEach(v => v.classList.remove('active'));

            // Add active class to clicked tab
            tab.classList.add('active');

            // Show corresponding view
            const viewId = `view-${tab.dataset.view}`;
            document.getElementById(viewId).classList.add('active');

            if (tab.dataset.view === 'graph') {
                loadGraph();
                // Pre-fetch all source data for cross-source relationships
                preloadAllSources();
            }
        });
    });
}

// Mapping of Evident source names → data plug IDs that provide them
const SOURCE_PLUG_MAP = {
    'cves': { plugIds: ['crowdstrike'], label: 'Vulnerabilities' },
    'assets': { plugIds: ['ad-identity', 'okta-identity', 'ms-graph', 'google-workspace', 'aws-cloudtrail'], label: 'Assets' },
    'logs': { plugIds: ['okta-identity', 'aws-cloudtrail', 'github-audit', 'stripe', 'atlassian', 'google-workspace', 'crowdstrike'], label: 'Security Logs' },
    'cloud_configs': { plugIds: ['aws-config', 'gcp-config', 'azure-config', 'aws-cloudtrail'], label: 'Cloud Config' },
    'signin_logs': { plugIds: ['ms-graph', 'okta-identity', 'snowflake'], label: 'Sign-in Logs' },
    'user_roles': { plugIds: ['ad-identity', 'ms-graph'], label: 'User Roles' },
    'role_permissions': { plugIds: ['ad-identity', 'ms-graph'], label: 'Permissions' },
};

// --- Sources & Data ---
async function loadSources() {
    try {
        // Fetch sources, connector configs, schema preference - all in parallel
        const [sourcesRes, configRes, connPlugsRes, activeRes] = await Promise.all([
            fetch('/api/sources'),
            fetch('/api/config'),
            fetch('/api/connectors'),
            fetch('/api/connectors/active')
        ]);

        const sourcesData = await sourcesRes.json();
        const configData = await configRes.json();
        const connData = await connPlugsRes.json();
        const activeData = await activeRes.json();

        const schema = (configData.schema_preference || 'evident').toUpperCase();
        const sourceMode = configData.source_mode || 'sample';
        updateSourceBadge(sourceMode);

        const allPlugs = connData.connectors || [];
        const activePlugIds = new Set((activeData.active || []).map(a => a.connector_id));

        // Build a plug lookup by id
        const plugById = {};
        allPlugs.forEach(p => plugById[p.id] = p);

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';

        sourcesData.sources.forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            sourceItem.dataset.name = source.name;
            sourceItem.onclick = () => {
                document.querySelectorAll('.source-item').forEach(el => el.classList.remove('active'));
                sourceItem.classList.add('active');
                currentSource = source.name;
                loadSourceData(source.name);
                const graphTab = document.querySelector('.viz-tab[data-view="graph"]');
                if (graphTab && graphTab.classList.contains('active')) {
                    buildSourceGraph(source.name);
                }
            };

            // Build Data Plug badges for this source
            const mapping = SOURCE_PLUG_MAP[source.name.toLowerCase()];
            let plugBadgesHtml = '';
            if (mapping) {
                mapping.plugIds.forEach(pid => {
                    const plug = plugById[pid];
                    if (!plug) return;
                    const isActive = activePlugIds.has(pid);
                    const dot = isActive
                        ? '<span style="color:#00e676; font-size:9px;">●</span>'
                        : '<span style="color:#546e7a; font-size:9px;">○</span>';
                    plugBadgesHtml += `
                        <span style="display:inline-flex; align-items:center; gap:3px; background:rgba(79,195,247,0.08); border:1px solid rgba(79,195,247,0.2); border-radius:10px; padding:1px 7px; font-size:0.68rem; color:#9fa8da; margin-right:4px;">
                            ${dot} ${plug.icon} ${plug.name}
                        </span>`;
                });
            }

            // Schema badge
            const schemaColor = schema === 'OCSF' ? '#66bb6a' : '#4fc3f7';
            const schemaBadge = `<span style="background:rgba(${schema === 'OCSF' ? '102,187,106' : '79,195,247'},0.12); border:1px solid ${schemaColor}44; border-radius:8px; padding:1px 7px; font-size:0.65rem; font-weight:700; color:${schemaColor}; letter-spacing:0.04em;">${schema}</span>`;

            sourceItem.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;">
                    <span class="source-name">${source.display_name}</span>
                    <span style="font-size:0.72rem; color:#9fa8da; white-space:nowrap; margin-left:8px;">${source.record_count} records</span>
                </div>
                <div style="margin-bottom:6px;">
                    <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.06em; color:#546e7a; font-weight:600; display:block; margin-bottom:4px;">Data Plugs</span>
                    <div style="display:flex; flex-wrap:wrap; gap:4px;">
                        ${plugBadgesHtml || '<span style="font-size:0.7rem; color:#546e7a; font-style:italic;">None configured</span>'}
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <span style="font-size:0.65rem; text-transform:uppercase; letter-spacing:0.06em; color:#546e7a; font-weight:600;">Schema</span>
                    ${schemaBadge}
                </div>
            `;
            sourcesList.appendChild(sourceItem);
        });

        // Auto-select the first source so the table is populated on startup
        const firstItem = sourcesList.querySelector('.source-item');
        if (firstItem) firstItem.click();
    } catch (error) {
        console.error('Error loading sources:', error);
        document.getElementById('sources-list').innerHTML =
            '<div class="error">Failed to load sources</div>';
    }
}

async function loadSourceData(sourceName) {
    currentSource = sourceName;
    const statusEl = document.getElementById('viz-status');
    const tbody = document.querySelector('#data-table tbody');
    const thead = document.querySelector('#data-table thead tr');

    statusEl.textContent = `Loading data for ${sourceName}...`;
    tbody.innerHTML = '<tr><td>Loading...</td></tr>';

    try {
        const response = await fetch(`/api/source-data/${sourceName}`);
        const data = await response.json();

        if (data.error) {
            statusEl.textContent = `Error: ${data.error}`;
            tbody.innerHTML = `<tr><td>Error loading data</td></tr>`;
            return;
        }

        statusEl.textContent = `Viewing ${data.data.length} records from ${sourceName}`;

        if (data.data.length === 0) {
            tbody.innerHTML = '<tr><td>No records found</td></tr>';
            return;
        }

        // Generate headers dynamically based on first item
        const headers = Object.keys(data.data[0]);
        thead.innerHTML = headers.map(h => `<th>${h}</th>`).join('');

        // Generate rows
        tbody.innerHTML = data.data.map(item => {
            return `<tr>${headers.map(h => `<td>${formatCellValue(item[h])}</td>`).join('')}</tr>`;
        }).join('');

    } catch (error) {
        console.error('Error loading source data:', error);
        statusEl.textContent = 'Error loading data';
        tbody.innerHTML = '';
    }
}

function formatCellValue(val) {
    if (typeof val === 'object' && val !== null) {
        return JSON.stringify(val); // Simple object representation
    }
    return val;
}

// --- Graph ---
// Called every time the Knowledge Graph tab is shown or a source changes
function loadGraph() {
    if (!currentSource) {
        showGraphEmpty(true);
        return;
    }
    showGraphEmpty(false);
    buildSourceGraph(currentSource);
}

function showGraphEmpty(show) {
    const empty = document.getElementById('graph-empty');
    const container = document.getElementById('cy-graph');
    if (empty) empty.style.display = show ? 'flex' : 'none';
    if (container) container.style.opacity = show ? '0' : '1';
}

// Node type → color mapping
const NODE_COLORS = {
    vulnerability: '#ff5252',
    asset: '#4fc3f7',
    user: '#ce93d8',
    event: '#ffb74d',
    cloud: '#80cbc4',
    role: '#a5d6a7',
    default: '#90a4ae'
};

function nodeColor(type) {
    return NODE_COLORS[type?.toLowerCase?.()] || NODE_COLORS.default;
}

// Convert source-data items into Cytoscape elements (nodes only, root level)
function buildCyElements(items) {
    return items.map((item, idx) => ({
        data: {
            id: item.id || `node-${idx}`,
            label: truncate(item.name || item.id || 'Node', 24),
            fullData: item,
            type: item.type || 'default',
            color: nodeColor(item.type)
        },
        classes: 'root-node'
    }));
}

function truncate(str, max) {
    return str && str.length > max ? str.slice(0, max) + '…' : str;
}

// Build or rebuild the Cytoscape instance for a source
async function buildSourceGraph(sourceName) {
    const container = document.getElementById('cy-graph');

    // Fetch source data
    let items = [];
    try {
        const res = await fetch(`/api/source-data/${sourceName}`);
        const json = await res.json();
        items = json.data || [];
    } catch (e) {
        console.error('Graph data fetch error:', e);
        return;
    }

    if (cy) { cy.destroy(); cy = null; }

    const elements = buildCyElements(items);

    cy = cytoscape({
        container,
        elements,
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': 'data(color)',
                    'label': 'data(label)',
                    'color': '#fff',
                    'text-valign': 'bottom',
                    'text-halign': 'center',
                    'text-margin-y': 6,
                    'font-size': '11px',
                    'font-family': 'Segoe UI, sans-serif',
                    'text-wrap': 'wrap',
                    'text-max-width': '90px',
                    'width': 46,
                    'height': 46,
                    'border-width': 2,
                    'border-color': 'rgba(255,255,255,0.15)',
                    'text-background-opacity': 0.6,
                    'text-background-color': '#0a0e27',
                    'text-background-padding': '3px',
                    'text-background-shape': 'roundrectangle',
                    'transition-property': 'border-color border-width background-color',
                    'transition-duration': '0.2s'
                }
            },
            {
                selector: 'node:selected, node.highlighted',
                style: {
                    'border-color': '#fff',
                    'border-width': 3,
                    'width': 56,
                    'height': 56
                }
            },
            {
                selector: 'node.expanded',
                style: {
                    'border-color': '#4fc3f7',
                    'border-width': 3
                }
            },
            {
                selector: 'node.relationship-node',
                style: {
                    'width': 34,
                    'height': 34,
                    'font-size': '9px',
                    'opacity': 0.85
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 1.5,
                    'line-color': 'rgba(255,255,255,0.2)',
                    'target-arrow-color': 'rgba(255,255,255,0.3)',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(label)',
                    'font-size': '9px',
                    'color': 'rgba(255,255,255,0.6)',
                    'text-rotation': 'autorotate',
                    'text-background-opacity': 0.5,
                    'text-background-color': '#0a0e27',
                    'text-background-padding': '2px'
                }
            },
            {
                selector: 'edge.relationship-edge',
                style: {
                    'line-color': 'rgba(79,195,247,0.4)',
                    'target-arrow-color': 'rgba(79,195,247,0.6)'
                }
            }
        ],
        layout: {
            name: items.length > 60 ? 'grid' : 'cose',
            animate: true,
            animationDuration: 600,
            padding: 30,
            nodeSpacing: () => 20,
            idealEdgeLength: () => 80,
            randomize: false
        }
    });

    // --- Selective relationship discovery ---
    cy.on('tap', 'node', async function (evt) {
        const node = evt.target;
        const data = node.data('fullData');

        // Ensure data is preloaded
        if (!_graphCacheReady) {
            await preloadAllSources();
        }

        // Show node detail panel + relationship list
        const relationships = findCrossSourceRelationships(data);
        showNodeInfo(data, node.data('type'), relationships, node.id());
    });

    cy.on('tap', function (evt) {
        if (evt.target === cy) {
            document.getElementById('graph-node-info').classList.add('hidden');
        }
    });

    setTimeout(() => { if (cy) cy.fit(undefined, 30); }, 800);
}


// -------------------------------------------------------
// Cross-source data cache – loaded once when graph opens
// -------------------------------------------------------
let _graphDataCache = {};   // { sourceName: [item, ...] }
let _graphCacheReady = false;

async function preloadAllSources() {
    if (_graphCacheReady) return;
    try {
        const res = await fetch('/api/sources');
        const { sources } = await res.json();
        await Promise.all(sources.map(async s => {
            try {
                const r = await fetch(`/api/source-data/${s.name}`);
                const json = await r.json();
                _graphDataCache[s.name] = json.data || [];
            } catch (_) { _graphDataCache[s.name] = []; }
        }));
        _graphCacheReady = true;
        console.log('[Graph] All source data pre-loaded for cross-source relationships');
    } catch (e) {
        console.warn('[Graph] Could not pre-load sources for graph:', e);
    }
}

// -------------------------------------------------------
// Fields to skip when building the shared-value index
// -------------------------------------------------------
const IGNORE_FIELDS = new Set([
    'id', 'entity_type', 'type', 'severity', 'score',
    'status', 'created_at', 'updated_at', 'timestamp',
    'description', 'details', 'notes'
]);

// Human-readable relationship label based on field name
function relLabel(field) {
    const labels = {
        hostname: 'ON HOST',
        host: 'ON HOST',
        asset_id: 'LINKED TO',
        affected_assets: 'AFFECTS',
        username: 'BY USER',
        user: 'BY USER',
        user_id: 'BY USER',
        cve_id: 'VULNERABLE TO',
        vulnerability_id: 'VULNERABLE TO',
        role: 'HAS ROLE',
        role_name: 'HAS ROLE',
        assigned_to: 'ASSIGNED TO',
        permissions: 'HAS PERMISSION',
        cloud_resource: 'USES RESOURCE',
        region: 'IN REGION',
        ip_address: 'FROM IP',
        source_ip: 'FROM IP'
    };
    return labels[field] || field.replace(/_/g, ' ').toUpperCase();
}

// -------------------------------------------------------
// Find all cross-source relationships for a given item, grouped by relLabel + source
// Returns { "Label (Source)": [rel1, rel2, ...] }
// -------------------------------------------------------
function findCrossSourceRelationships(item) {
    const results = {};
    const NULL_VALS = new Set(['null', 'none', 'n/a', '', 'undefined', 'unknown']);

    // Collect non-trivial field values from this item
    const selfFields = Object.entries(item)
        .filter(([k, v]) => !IGNORE_FIELDS.has(k) && v != null)
        .map(([k, v]) => ({
            field: k,
            values: (Array.isArray(v) ? v : String(v).split(',')).map(x => String(x).trim().toLowerCase())
                .filter(x => x.length > 1 && !NULL_VALS.has(x))
        }))
        .filter(f => f.values.length > 0);

    if (selfFields.length === 0) return results;

    // For each other source, check every entity
    for (const [sourceName, entities] of Object.entries(_graphDataCache)) {
        for (const other of entities) {
            // Skip if it's the same entity
            if (other.id && other.id === item.id) continue;

            for (const { field: selfField, values: selfVals } of selfFields) {
                for (const [otherField, otherRaw] of Object.entries(other)) {
                    if (IGNORE_FIELDS.has(otherField) || otherRaw == null) continue;
                    const otherVals = (Array.isArray(otherRaw) ? otherRaw : String(otherRaw).split(','))
                        .map(x => String(x).trim().toLowerCase())
                        .filter(x => x.length > 1 && !NULL_VALS.has(x));

                    const overlap = selfVals.find(sv => otherVals.includes(sv));
                    if (overlap) {
                        const label = relLabel(selfField);
                        const groupKey = `${label} (${sourceName})`;

                        if (!results[groupKey]) results[groupKey] = [];

                        results[groupKey].push({
                            relatedItem: other,
                            sourceName,
                            fieldOnSelf: selfField,
                            fieldOnOther: otherField,
                            matchValue: overlap,
                            relName: label
                        });
                        break; // one match per entity
                    }
                }
                // Avoid redundant processing if already matched
                if (Object.values(results).flat().find(r => r.relatedItem === other)) break;
            }
        }
    }

    return results;
}

// -------------------------------------------------------
// Manual expansion: Add a specific relationship to the graph
// -------------------------------------------------------
function addRelationshipToGraph(parentId, relDataJson) {
    if (!cy) return;
    const rel = JSON.parse(decodeURIComponent(relDataJson));
    _addSingleRel(parentId, rel);
}

// -------------------------------------------------------
// Grouped expansion: Add ALL relationships in a group
// -------------------------------------------------------
function addRelationshipGroupToGraph(parentId, relsJson) {
    if (!cy) return;
    const rels = JSON.parse(decodeURIComponent(relsJson));

    // Add all nodes/edges first
    rels.forEach(rel => _addSingleRel(parentId, rel, false));

    // Run layout once at the end
    cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 500,
        padding: 40,
        componentSpacing: 50,
        nodeSpacing: () => 30,
        fit: false
    }).run();
}

// -------------------------------------------------------
// Batch removal: Remove ALL relationships in a category
// -------------------------------------------------------
function removeRelationshipGroupFromGraph(parentId, relsJson) {
    if (!cy) return;
    const rels = JSON.parse(decodeURIComponent(relsJson));

    rels.forEach(rel => {
        const relNodeId = `rel-${parentId}-${rel.sourceName}-${(rel.relatedItem.id || '').toString().replace(/[^a-z0-9]/gi, '_')}`;
        const node = cy.getElementById(relNodeId);
        if (node.length) {
            // Remove the specific edge and the node if it's not connected to anything else
            node.connectedEdges().remove();
            node.remove();
        }
    });
}

// Helper for adding a single rel node/edge
function _addSingleRel(parentId, rel, runLayout = true) {
    const relNodeId = `rel-${parentId}-${rel.sourceName}-${(rel.relatedItem.id || Math.random()).toString().replace(/[^a-z0-9]/gi, '_')}`;

    if (!cy.getElementById(relNodeId).length) {
        const rType = rel.relatedItem.type || rel.relatedItem.entity_type || rel.sourceName.replace(/s$/, '');
        cy.add([
            {
                group: 'nodes',
                data: {
                    id: relNodeId,
                    label: truncate(rel.relatedItem.name || rel.relatedItem.id || 'Related', 22),
                    type: rType,
                    color: nodeColor(rType),
                    fullData: rel.relatedItem
                },
                classes: 'relationship-node'
            },
            {
                group: 'edges',
                data: {
                    id: `edge-${parentId}-${relNodeId}`,
                    source: parentId,
                    target: relNodeId,
                    label: rel.relName
                },
                classes: 'relationship-edge'
            }
        ]);

        if (runLayout) {
            cy.layout({
                name: 'cose',
                animate: true,
                animationDuration: 500,
                padding: 30,
                componentSpacing: 40,
                nodeSpacing: () => 20,
                fit: false
            }).run();
        }
    }
}

function collapseNode(node) {
    const cyInst = node.cy();
    node.removeClass('expanded');
    // Remove all nodes/edges created by expansion of this node
    const prefix = `rel-${node.id()}-`;
    cyInst.elements('node.relationship-node').filter(n => n.id().startsWith(prefix)).connectedEdges().remove();
    cyInst.elements('node.relationship-node').filter(n => n.id().startsWith(prefix)).remove();
    document.getElementById('graph-node-info').classList.add('hidden');
}

function showNodeInfo(data, type, groupedRelationships = {}, nodeId = null) {
    const panel = document.getElementById('graph-node-info');
    const title = document.getElementById('node-info-title');
    const body = document.getElementById('node-info-body');

    title.textContent = `${(type || 'Node').toUpperCase()}: ${data.name || data.id || ''}`;

    const skip = new Set(['id', 'name', 'type', 'entity_type']);
    const detailsRows = Object.entries(data)
        .filter(([k, v]) => !skip.has(k) && v !== null && v !== undefined && v !== '')
        .map(([k, v]) => `<tr><td class="ni-key">${k.replace(/_/g, ' ')}</td><td class="ni-val">${formatCellValue(v)}</td></tr>`)
        .join('');

    let html = '';
    if (detailsRows) {
        html += `<div class="ni-section-title">Details</div><table class="ni-table"><tbody>${detailsRows}</tbody></table>`;
    }

    // Add Grouped Relationships Section
    const groups = Object.entries(groupedRelationships);
    if (groups.length > 0) {
        html += `<div class="ni-section-title">Potential Connections</div>`;
        html += `<div class="ni-rel-list">`;
        groups.forEach(([groupKey, rels]) => {
            const relsData = encodeURIComponent(JSON.stringify(rels));
            const count = rels.length;
            const label = rels[0].relName;
            const source = rels[0].sourceName;

            html += `
                <div class="ni-rel-item group-item">
                    <div class="ni-rel-info">
                        <div class="ni-rel-type">${label}</div>
                        <div class="ni-rel-target">${source.toUpperCase()} (${count})</div>
                    </div>
                    <div class="ni-rel-actions">
                        <button class="ni-add-btn" onclick="addRelationshipGroupToGraph('${nodeId}', '${relsData}')" title="Expand category">+</button>
                        <button class="ni-remove-btn" onclick="removeRelationshipGroupFromGraph('${nodeId}', '${relsData}')" title="Remove category">−</button>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    } else {
        html += `<div class="ni-section-title">Potential Connections</div><p style="color:#888; font-size:0.75rem; padding: 0 4px;">No cross-source connections found.</p>`;
    }

    body.innerHTML = html || '<p style="color:#888">No additional data.</p>';
    panel.classList.remove('hidden');
}

// --- Audit History ---
async function loadHistory() {
    const listContainer = document.getElementById('history-list');
    listContainer.innerHTML = '<li class="history-item">Loading...</li>';

    try {
        const response = await fetch('/api/history');
        const data = await response.json();

        listContainer.innerHTML = '';

        data.history.forEach(item => {
            const li = document.createElement('li');
            li.className = 'history-item';
            li.innerHTML = `
                <div class="history-query">${item.query}</div>
                <div class="history-meta">
                    <span>${new Date(item.timestamp).toLocaleTimeString()}</span>
                    <span>${item.model}</span>
                </div>
            `;
            li.onclick = () => showHistoryDetails(item, li);
            listContainer.appendChild(li);
        });

    } catch (error) {
        listContainer.innerHTML = '<li class="history-item">Error loading history</li>';
    }
}

function showHistoryDetails(item, element) {
    // Highlight active
    document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
    element.classList.add('active');

    const detailsContainer = document.getElementById('history-details-content');

    let stepsHtml = '';
    if (item.execution_steps && item.execution_steps.length > 0) {
        stepsHtml = item.execution_steps.map(step => `
            <div class="step-card">
                <div class="step-header">
                    <span class="step-name">${step.step}</span>
                    <span class="step-time">${new Date(step.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="step-desc">${step.description}</div>
            </div>
        `).join('');
    } else {
        stepsHtml = '<div class="step-card">No execution steps recorded</div>';
    }

    detailsContainer.innerHTML = `
        <h3>Interaction Details</h3>
        <p><strong>Query:</strong> ${item.query}</p>
        <p><strong>Response:</strong> ${item.response}</p>
        <div style="margin: 15px 0; border-top: 1px solid #333; padding-top: 15px;">
            <h4>Execution Trace (Explain)</h4>
            ${stepsHtml}
        </div>
        <div style="font-size: 0.9rem; color: #888;">
            <p>Tokens: ${item.tokens} | Cost: $${item.cost}</p>
            <p>Context Summary: ${item.context_summary || 'N/A'}</p>
        </div>
    `;
}

// --- Stats --- (Existing Logic)
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('stat-entities').textContent = data.total_entities || 0;
        document.getElementById('stat-vectors').textContent =
            data.rag_stats?.vector_store?.document_count || 0;
        document.getElementById('stat-nodes').textContent =
            data.smg_stats?.node_count || 0;
        document.getElementById('stat-edges').textContent =
            data.smg_stats?.relationship_count || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// --- Chat Logic --- (Preserved and Updated)

// Handle keyboard shortcuts
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendQuestion();
    }
}

// Ask a predefined question
function askQuestion(question) {
    document.getElementById('question-input').value = question;
    sendQuestion();
}

// Send question to API
async function sendQuestion() {
    if (isProcessing) return;

    const input = document.getElementById('question-input');
    const question = input.value.trim();

    if (!question) return;

    // Clear input
    input.value = '';
    input.style.height = 'auto';

    // Add user message to chat
    addMessage(question, 'user');

    // Show loading indicator
    const loadingId = addLoadingMessage();

    // Disable send button
    isProcessing = true;
    const sendButton = document.getElementById('send-button');
    sendButton.disabled = true;

    try {
        const response = await fetch('/api/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ question })
        });

        const data = await response.json();

        // Remove loading indicator
        removeMessage(loadingId);

        // Add agent response
        if (data.error) {
            addMessage(`Error: ${data.error}`, 'agent');
        } else {
            addMessage(data.answer, 'agent', {
                sources: data.sources,
                model: data.model,
                tokens: data.tokens,
                cost: data.cost
            });
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage(`Error: Failed to get response. ${error.message}`, 'agent');
    } finally {
        isProcessing = false;
        sendButton.disabled = false;
    }
}

// Add message to chat
function addMessage(text, type, metadata = null) {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;

    const icon = type === 'user' ? '👤' : '🤖';
    const label = type === 'user' ? 'You' : 'Evident';

    let metaHtml = '';
    if (metadata) {
        const parts = [];
        if (metadata.sources && metadata.sources.length > 0) {
            parts.push(`Sources: ${metadata.sources.join(', ')}`);
        }
        if (metadata.model) {
            parts.push(`Model: ${metadata.model}`);
        }
        if (metadata.tokens) {
            parts.push(`Tokens: ${metadata.tokens}`);
        }
        if (metadata.cost) {
            parts.push(`Cost: $${metadata.cost.toFixed(4)}`);
        }

        if (parts.length > 0) {
            metaHtml = `<div class="message-meta">${parts.join(' • ')}</div>`;
        }
    }

    messageDiv.innerHTML = `
        <div class="message-icon">${icon}</div>
        <div class="message-content">
            <p><strong>${label}:</strong> ${formatMessage(text)}</p>
            ${metaHtml}
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return messageDiv.id = `msg-${Date.now()}`;
}

// Add loading message
function addLoadingMessage() {
    const messagesContainer = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    const id = `loading-${Date.now()}`;
    messageDiv.id = id;
    messageDiv.className = 'message agent-message';

    messageDiv.innerHTML = `
        <div class="message-icon">🤖</div>
        <div class="message-content">
            <p><strong>Evident:</strong> <span class="loading-indicator"></span> Analyzing security data...</p>
        </div>
    `;

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    return id;
}

// Remove message
function removeMessage(id) {
    const message = document.getElementById(id);
    if (message) {
        message.remove();
    }
}

// Format message text (preserve line breaks, lists, etc.)
function formatMessage(text) {
    // Convert markdown-style lists
    text = text.replace(/^\* (.+)$/gm, '<li>$1</li>');
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');

    // Wrap lists
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

    // Convert line breaks
    text = text.replace(/\n\n/g, '</p><p>');
    text = text.replace(/\n/g, '<br>');

    // Bold text
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    return text;
}

// --- Security Agents Functions ---

async function loadActiveAgentsView() {
    const listEl = document.getElementById('active-agents-list');
    if (!listEl) return;

    listEl.innerHTML = '<div class="loading">Fetching active agents...</div>';

    try {
        const response = await fetch('/api/agents/active');
        const data = await response.json();
        renderAgents(data.agents, 'active-agents-list', true);
    } catch (err) {
        listEl.innerHTML = '<div class="error">Failed to load active agents</div>';
    }
}

async function loadAllAgentsView() {
    const gridEl = document.getElementById('all-agents-grid');
    if (!gridEl) return;

    gridEl.innerHTML = '<div class="loading">Loading available security agents...</div>';

    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        renderAgents(data.agents, 'all-agents-grid', false);
    } catch (err) {
        gridEl.innerHTML = '<div class="error">Failed to load security agents</div>';
    }
}

function renderAgents(agents, containerId, isActiveView) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (agents.length === 0) {
        container.innerHTML = '<div class="empty-state">No agents found. Enable them from the Security Agents menu.</div>';
        return;
    }

    container.innerHTML = '';

    agents.forEach(agent => {
        const card = document.createElement('div');
        card.className = 'agent-card';
        card.style.cursor = 'pointer';

        // Click on the card body opens the dedicated view
        card.onclick = (e) => {
            if (e.target.tagName === 'BUTTON') return;
            window.open(`/agent-view/${agent.id}`, `agent_${agent.id}`, 'width=1200,height=800');
        };

        const signalsHtml = agent.supported_signals.map(s => `<span class="agent-signal-chip">${s.replace('_', ' ')}</span>`).join('');

        const statusIcon = agent.is_active ? (agent.is_paused ? '⏸' : '●') : '○';
        const statusText = agent.is_active ? (agent.is_paused ? 'Paused' : 'Active') : 'Disabled';
        const statusClass = agent.is_active ? (agent.is_paused ? 'paused' : 'active') : '';

        card.innerHTML = `
            <div class="agent-card-header">
                <div class="agent-icon">${agent.icon || '🤖'}</div>
                <div class="agent-title-area">
                    <div class="agent-category-tag">${agent.category}</div>
                    <h3>${agent.name}</h3>
                </div>
            </div>
            <p class="agent-description">${agent.description}</p>
            <div class="agent-meta">
                ${signalsHtml}
            </div>
            <div class="agent-footer" style="flex-direction: column; gap: 12px; align-items: stretch;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div class="agent-status-badge ${statusClass}">
                        ${statusIcon} ${statusText}
                    </div>
                    <div style="font-size: 0.75rem; color: #888;">Mode: ${agent.active_mode || 'Interactive'}</div>
                </div>
                <div class="agent-actions" style="display: flex; gap: 8px;">
                    <button class="agent-btn-config" style="flex: 1;" onclick="toggleAgent('${agent.id}', ${agent.is_active})">
                        ${agent.is_active ? 'Disable' : 'Enable'}
                    </button>
                    <button class="agent-btn-config" style="flex: 1; border-color: #666; color: #ccc;" onclick="openAgentConfig('${agent.id}')">
                        ⚙️ Config
                    </button>
                    ${agent.is_active ? `
                        <button class="agent-btn-config" style="border-color: #888;" title="${agent.is_paused ? 'Resume' : 'Pause'}" onclick="toggleAgentPause('${agent.id}', ${agent.is_paused})">
                            ${agent.is_paused ? '▶' : '⏸'}
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

async function openAgentConfig(agentId) {
    const modal = document.getElementById('modal-agent-config');
    if (!modal) return;

    try {
        const response = await fetch('/api/agents');
        const data = await response.json();
        const agent = data.agents.find(a => a.id === agentId);

        if (!agent) return;

        document.getElementById('config-agent-id').value = agentId;
        document.getElementById('agent-config-title').textContent = `🤖 Configure ${agent.name}`;
        document.getElementById('config-agent-mode').value = agent.active_mode || agent.profile.mode;
        document.getElementById('config-agent-frequency').value = agent.active_interval || agent.profile.frequency_minutes;
        document.getElementById('config-agent-prompt').value = agent.profile.system_prompt;
        document.getElementById('config-agent-notify').value = agent.profile.notification_method || 'email';

        // Show/hide frequency based on mode
        const freqGroup = document.getElementById('group-config-frequency');
        freqGroup.style.display = document.getElementById('config-agent-mode').value === 'autonomous' ? 'block' : 'none';

        // Signals list
        const signalsContainer = document.getElementById('config-agent-signals-list');
        signalsContainer.innerHTML = agent.supported_signals.map(s => `
            <label style="background: rgba(255,255,255,0.05); padding: 5px 10px; border-radius: 4px; display: flex; align-items: center; gap: 6px; cursor: pointer; font-size: 0.8rem;">
                <input type="checkbox" name="agent-signal" value="${s}" checked>
                ${s.replace('_', ' ')}
            </label>
        `).join('');

        modal.classList.add('show');
    } catch (err) {
        showToast('Failed to load agent profile', 'error');
    }
}

async function saveAgentProfile() {
    const agentId = document.getElementById('config-agent-id').value;
    const mode = document.getElementById('config-agent-mode').value;
    const freq = parseInt(document.getElementById('config-agent-frequency').value);
    const prompt = document.getElementById('config-agent-prompt').value;
    const notify = document.getElementById('config-agent-notify').value;

    const signals = Array.from(document.querySelectorAll('input[name="agent-signal"]:checked')).map(cb => cb.value);

    const config = {
        mode: mode,
        frequency_minutes: freq,
        system_prompt: prompt,
        notification_method: notify,
        supported_signals: signals
    };

    try {
        const response = await fetch('/api/agents/enable', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId, config: config })
        });
        const data = await response.json();
        if (data.status === 'success') {
            showToast('Configuration saved successfully!');
            document.getElementById('modal-agent-config').classList.remove('show');
            loadActiveAgentsView();
            loadAllAgentsView();
        }
    } catch (err) {
        showToast('Failed to save configuration', 'error');
    }
}

async function toggleAgent(agentId, currentStatus) {
    if (currentStatus) {
        if (!confirm(`Are you sure you want to disable ${agentId}?`)) return;

        try {
            const response = await fetch(`/api/agents/disable/${agentId}`, { method: 'POST' });
            const data = await response.json();
            if (data.status === 'success') {
                showToast(`Agent ${agentId} disabled`);
                loadActiveAgentsView();
                loadAllAgentsView();
            }
        } catch (err) {
            showToast('Failed to disable agent', 'error');
        }
    } else {
        // Simple enable with current/default config
        try {
            const response = await fetch('/api/agents/enable', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ agent_id: agentId, config: {} })
            });
            const data = await response.json();
            if (data.status === 'success') {
                showToast(`Agent ${agentId} enabled!`);
                loadActiveAgentsView();
                loadAllAgentsView();
            }
        } catch (err) {
            showToast('Failed to enable agent', 'error');
        }
    }
}

async function toggleAgentPause(agentId, isPaused) {
    const endpoint = isPaused ? 'resume' : 'pause';
    try {
        const res = await fetch(`/api/agents/${endpoint}/${agentId}`, { method: 'POST' });
        if (res.ok) {
            showToast(`Agent ${agentId} ${isPaused ? 'resumed' : 'paused'}`);
            loadActiveAgentsView();
            loadAllAgentsView();
        }
    } catch (err) {
        showToast('Operation failed', 'error');
    }
}
