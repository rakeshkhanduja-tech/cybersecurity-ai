let labData = {
    current_step: 1,
    steps: []
};

document.addEventListener('DOMContentLoaded', () => {
    fetchLabStatus();

    document.getElementById('btn-next').addEventListener('click', handleNext);
    document.getElementById('btn-back').addEventListener('click', handleBack);
    document.getElementById('btn-reset-lab').addEventListener('click', resetLab);
});

async function fetchLabStatus() {
    try {
        const res = await fetch('/api/lab/status');
        const data = await res.json();
        labData = data;
        renderSidebar();
        renderStep();
    } catch (err) {
        console.error("Failed to fetch lab status:", err);
    }
}

function renderSidebar() {
    const nav = document.getElementById('lab-steps-nav');
    nav.innerHTML = labData.steps.map(step => `
        <li class="step-item ${step.id === labData.current_step ? 'active' : ''} ${labData.completed_steps.includes(step.id) ? 'completed' : ''}" onclick="goToStep(${step.id})">
            <div class="step-number">${labData.completed_steps.includes(step.id) ? '✓' : step.id}</div>
            <div class="step-info">
                <h3>${step.title}</h3>
                <p>${step.description}</p>
            </div>
        </li>
    `).join('');
}

function renderStep() {
    const display = document.getElementById('lab-step-display');
    const step = labData.steps.find(s => s.id === labData.current_step);

    if (!step) {
        display.innerHTML = '<div class="lab-header"><h1>Lab Complete! 🛡️</h1><p>You have successfully mastered security agent hardening.</p></div>';
        document.getElementById('btn-next').style.display = 'none';
        return;
    }

    const template = document.getElementById('template-step');
    const content = template.content.cloneNode(true);

    content.getElementById('step-id-badge').textContent = `Step ${step.id}`;
    content.getElementById('step-title').textContent = step.title;
    content.getElementById('step-description').textContent = step.description;
    content.getElementById('step-instructions').textContent = step.instructions;

    const interactive = content.getElementById('step-interactive-area');
    interactive.innerHTML = renderInteractive(step);

    display.innerHTML = '';
    display.appendChild(content);

    // Update buttons
    document.getElementById('btn-back').style.display = labData.current_step > 1 ? 'block' : 'none';
    document.getElementById('btn-next').textContent = step.id === 5 ? 'Validate & Finish' : 'Next Step';
}

function renderInteractive(step) {
    switch (step.component) {
        case 'StepLLMSetup':
            return `
                <div class="form-group">
                    <label>Provider</label>
                    <select id="lab-llm-provider" style="width: 100%; padding: 10px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); color: #fff; border-radius: 8px;">
                        <option value="gemini">Google Gemini</option>
                        <option value="openai">OpenAI</option>
                    </select>
                </div>
                <div class="form-group" style="margin-top: 15px;">
                    <label>API Key</label>
                    <input type="password" id="lab-api-key" placeholder="Enter key..." style="width: 100%; padding: 10px; background: rgba(0,0,0,0.2); border: 1px solid var(--border-color); color: #fff; border-radius: 8px;">
                </div>
            `;
        case 'StepAgentDeployment':
            return `
                <div style="display: flex; gap: 20px;">
                    <div style="flex: 1; border: 1px solid var(--border-color); padding: 15px; border-radius: 12px; background: rgba(255,0,0,0.05);">
                        <h4 style="color: var(--accent-red);">Insecure Sentinel</h4>
                        <p style="font-size: 0.8rem; margin-top: 5px;">Profile: VULNERABLE</p>
                        <button class="btn-primary" style="margin-top: 15px; width: 100%;">Deploy Vulnerable Agent</button>
                    </div>
                </div>
            `;
        case 'StepUseCaseViewer':
            return `
                <div style="background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; border-left: 4px solid var(--accent-red);">
                    <h4 style="margin-bottom: 10px;">${step.use_case.name}</h4>
                    <p style="font-size: 0.85rem; color: #aaa; margin-bottom: 15px;">Vulnerability: ${step.use_case.vulnerability}</p>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 4px; font-family: monospace; font-size: 0.8rem; margin-bottom: 10px;">
                        <span style="color: var(--accent-red);">ATTACK:</span> ${step.use_case.attack_scenario}
                    </div>
                    <div style="font-size: 0.85rem; color: var(--accent-orange);">Impact: ${step.use_case.impact}</div>
                </div>
            `;
        case 'StepFixAnalysis':
            return `
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div style="padding: 15px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: #888; margin-bottom: 5px;">HARDENED PROMPT</div>
                        <div style="font-style: italic; color: var(--accent-green); font-size: 0.9rem;">"${step.hardened_prompt}"</div>
                    </div>
                </div>
            `;
        case 'StepExercise':
            const ex = step.exercises[0];
            return `
                <div style="margin-bottom: 15px;">
                    <strong>Exercise:</strong> ${ex.name}
                    <p style="font-size: 0.85rem; color: #888; margin-top: 5px;">${ex.goal}</p>
                </div>
                <div id="code-editor" contenteditable="true" class="code-editor">${ex.starting_code}</div>
                <div id="validation-msg" class="validation-message"></div>
                <button onclick="submitExercise()" class="btn-primary" style="margin-top: 15px;">Validate Solution</button>
            `;
        default:
            return '';
    }
}

async function handleNext() {
    const step = labData.steps.find(s => s.id === labData.current_step);
    if (!step) return;

    if (step.id === 5) {
        // Exercise validation is handled separately by button click in renderInteractive
        return;
    }

    const res = await fetch('/api/lab/next', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ /* config data if any */ })
    });
    const data = await res.json();
    labData = { ...labData, ...data };
    renderSidebar();
    renderStep();
}

async function handleBack() {
    if (labData.current_step > 1) {
        labData.current_step--;
        renderSidebar();
        renderStep();
    }
}

async function resetLab() {
    if (confirm("Reset all lab progress?")) {
        const res = await fetch('/api/lab/reset', { method: 'POST' });
        const data = await res.json();
        labData = { ...labData, ...data };
        renderSidebar();
        renderStep();
    }
}

async function submitExercise() {
    const code = document.getElementById('code-editor').innerText;
    const res = await fetch('/api/lab/submit-exercise', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step_id: 5, result: code })
    });
    const data = await res.json();

    const msg = document.getElementById('validation-msg');
    msg.style.display = 'block';
    msg.textContent = data.message;
    msg.className = `validation-message ${data.success ? 'success' : 'error'}`;

    if (data.success) {
        setTimeout(fetchLabStatus, 2000);
    }
}

function goToStep(id) {
    if (labData.completed_steps.includes(id) || id === labData.current_step || labData.completed_steps.includes(id - 1)) {
        labData.current_step = id;
        renderSidebar();
        renderStep();
    }
}
