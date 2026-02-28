// Evident Security Intelligence Agent - Frontend JavaScript

let isProcessing = false;
let currentSource = null;
let cy = null; // Cytoscape instance

// Poll /api/status until agent is ready, then dismiss loading screen
async function waitForAgent() {
    const overlay = document.getElementById('loading-overlay');
    const msgEl = document.getElementById('loading-message');
    const stepsEl = document.getElementById('loading-steps');
    let renderedSteps = [];

    while (true) {
        try {
            const res = await fetch('/api/status');
            if (res.ok) {
                const data = await res.json();

                // Render completed steps
                const log = data.log || [];
                if (log.length !== renderedSteps.length) {
                    // Add new steps that aren't rendered yet
                    for (let i = renderedSteps.length; i < log.length; i++) {
                        const item = document.createElement('div');
                        item.className = 'loading-step-item step-done';
                        item.innerHTML = `<span class="step-icon">✅</span><span>${log[i]}</span>`;
                        // Mark the previous-last as done before adding new
                        if (stepsEl.lastChild) {
                            stepsEl.lastChild.classList.remove('step-current');
                            stepsEl.lastChild.classList.add('step-done');
                            stepsEl.lastChild.querySelector('.step-icon').textContent = '✅';
                        }
                        stepsEl.appendChild(item);
                        stepsEl.scrollTop = stepsEl.scrollHeight;
                    }
                    renderedSteps = [...log];
                }

                // Show current in-progress step
                msgEl.textContent = data.step;

                // Mark the last rendered item as "current" (spinner)
                if (stepsEl.lastChild && !data.ready) {
                    stepsEl.lastChild.classList.remove('step-done');
                    stepsEl.lastChild.classList.add('step-current');
                    stepsEl.lastChild.querySelector('.step-icon').textContent = '⚙️';
                }

                if (data.ready) {
                    // Mark all as done
                    stepsEl.querySelectorAll('.loading-step-item').forEach(el => {
                        el.classList.remove('step-current');
                        el.classList.add('step-done');
                        el.querySelector('.step-icon').textContent = '✅';
                    });
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

    // Add listener for Ask Evident button
    document.getElementById('btn-ask-evident').addEventListener('click', () => {
        window.open('/chat', '_blank');
    });

    // Wait for the agent to initialize, then load data
    await waitForAgent();
    loadSources();
    loadStats();
});

function initializeUI() {
    setupModals();
    setupTabs();
}

// --- Modals ---
function setupModals() {
    const configModal = document.getElementById('modal-config');
    const historyModal = document.getElementById('modal-history');

    document.getElementById('btn-config').addEventListener('click', async () => {
        configModal.classList.add('show');

        // Load current config from server to pre-fill
        try {
            const response = await fetch('/api/config');
            const data = await response.json();

            document.getElementById('config-provider').value = data.provider;
            document.getElementById('config-api-key').value = data.api_key;

            const modelSelect = document.getElementById('config-model');
            modelSelect.innerHTML = `<option value="${data.model_id}">${data.model_id}</option>`;
            modelSelect.disabled = false;
        } catch (error) {
            console.error('Error loading config:', error);
        }
    });

    document.getElementById('btn-history').addEventListener('click', () => {
        historyModal.classList.add('show');
        loadHistory();
    });

    document.querySelectorAll('.close-modal, .close-modal-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            modal.classList.remove('show');
        });
    });

    // Config Modal Logic: Clear fetch context when provider changes
    document.getElementById('config-provider').addEventListener('change', () => {
        const modelSelect = document.getElementById('config-model');
        modelSelect.disabled = true;
        modelSelect.innerHTML = '<option>Click Fetch Models</option>';
    });

    document.getElementById('btn-fetch-models').addEventListener('click', async () => {
        const provider = document.getElementById('config-provider').value;
        const apiKey = document.getElementById('config-api-key').value;
        const modelSelect = document.getElementById('config-model');
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

    document.getElementById('btn-save-config').addEventListener('click', async () => {
        const provider = document.getElementById('config-provider').value;
        const apiKey = document.getElementById('config-api-key').value;
        const modelId = document.getElementById('config-model').value;

        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, api_key: apiKey, model_id: modelId })
            });
            const data = await response.json();

            if (data.status === 'success') {
                alert('Configuration saved!');
                configModal.classList.remove('show');
            } else {
                alert('Error: ' + data.error);
            }
        } catch (error) {
            alert('Failed to save config');
        }
    });
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

// --- Sources & Data ---
async function loadSources() {
    try {
        const response = await fetch('/api/sources');
        const data = await response.json();

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';

        data.sources.forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
            sourceItem.dataset.name = source.name; // Store name for click handler
            sourceItem.onclick = () => {
                document.querySelectorAll('.source-item').forEach(el => el.classList.remove('active'));
                sourceItem.classList.add('active');
                currentSource = source.name;
                loadSourceData(source.name);
                // If graph tab is active, reload graph for this source
                const graphTab = document.querySelector('.viz-tab[data-view="graph"]');
                if (graphTab && graphTab.classList.contains('active')) {
                    buildSourceGraph(source.name);
                }
            };

            sourceItem.innerHTML = `
                <div class="source-header">
                    <span class="source-name">${source.display_name}</span>
                    <span class="source-status ${source.status}">✓</span>
                </div>
                <div class="source-count">${source.record_count} records</div>
            `;
            sourcesList.appendChild(sourceItem);
        });
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
