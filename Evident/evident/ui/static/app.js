// Evident Security Intelligence Agent - Frontend JavaScript

let isProcessing = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function () {
    loadSources();
    loadStats();

    // Auto-resize textarea
    const textarea = document.getElementById('question-input');
    textarea.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });
});

// Load data sources
async function loadSources() {
    try {
        const response = await fetch('/api/sources');
        const data = await response.json();

        const sourcesList = document.getElementById('sources-list');
        sourcesList.innerHTML = '';

        data.sources.forEach(source => {
            const sourceItem = document.createElement('div');
            sourceItem.className = 'source-item';
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

// Load statistics
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
