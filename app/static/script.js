document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chat-history');
    const promptInput = document.getElementById('prompt-input');
    const sendBtn = document.getElementById('send-btn');
    const modelSelect = document.getElementById('model-select');
    const logStream = document.getElementById('log-stream');
    const clearLogsBtn = document.getElementById('clear-logs-btn');

    let isWaitingForResponse = false;
    let conversationHistory = [];

    // --- WebSockets for Live Logs ---
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs`;

    let ws;

    function connectWebSocket() {
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            appendLog({ type: 'system', message: 'Connected to Live Gateway WebSocket' });
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                appendLog(data);
            } catch (e) {
                console.error("Failed to parse WS message", e);
            }
        };

        ws.onclose = () => {
            appendLog({ type: 'system', message: 'Disconnected from Live Gateway. Reconnecting in 3s...' });
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = (err) => {
            console.error('WebSocket Error:', err);
        };
    }

    connectWebSocket();

    // --- Chat Interface Logic ---

    promptInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    sendBtn.addEventListener('click', sendMessage);
    clearLogsBtn.addEventListener('click', () => {
        logStream.innerHTML = '';
        chatHistory.innerHTML = `
            <div class="welcome-message">
                <h3>Secure LLM Endpoint</h3>
                <p>All interactions are evaluated by real-time security guards.</p>
            </div>
        `;
        conversationHistory = [];
        appendLog({ type: 'system', message: 'Logs and Chat History cleared.' });
    });

    async function sendMessage() {
        const text = promptInput.value.trim();
        if (!text || isWaitingForResponse) return;

        const model = modelSelect.value;
        conversationHistory.push({ role: "user", content: text });

        appendChat('user', text);
        promptInput.value = '';
        setLoadingState(true);

        try {
            const response = await fetch('/v1/chat/completions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model: model,
                    messages: conversationHistory,
                    user: "web_ui_user"
                })
            });

            const data = await response.json();

            if (!response.ok) {
                // Remove the failed message from history so the user can try again or change prompt
                conversationHistory.pop();

                if (data.status === "Pending Approval") {
                    appendChat('error', `High-Risk Request Blocked.\nReason: ${data.message}\nRequest ID: ${data.request_id}`);
                } else {
                    appendChat('error', `Error: ${data.error || data.detail || 'Unknown error'}`);
                }
            } else {
                const reply = data.choices[0].message.content;
                conversationHistory.push({ role: "assistant", content: reply });
                appendChat('bot', reply);
            }
        } catch (error) {
            conversationHistory.pop();
            appendChat('error', `Network Error: ${error.message}`);
        } finally {
            setLoadingState(false);
        }
    }

    function appendChat(role, text) {
        const div = document.createElement('div');
        div.className = `chat-bubble chat-${role}`;
        div.textContent = text;
        chatHistory.appendChild(div);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function setLoadingState(isLoading) {
        isWaitingForResponse = isLoading;
        sendBtn.disabled = isLoading;
        sendBtn.innerHTML = isLoading ? '<i class="fas fa-spinner fa-spin"></i>' : '<span>Send</span>';
    }

    // --- Log Parsing and Rendering ---

    function appendLog(data) {
        const div = document.createElement('div');
        div.className = `log-card ${data.type}`;

        // Add status classes if present
        if (data.status) div.classList.add(data.status);

        const timeStr = new Date().toLocaleTimeString('en-US', { hour12: false, hour: "numeric", minute: "numeric", second: "numeric", fractionalSecondDigits: 3 });

        let contentHtml = `<div class="log-time">${timeStr} [${data.type.toUpperCase()}]</div>`;
        contentHtml += `<div class="log-content">${data.message || ''}</div>`;

        // Add specific key-value details based on the event
        if (data.risk_score !== undefined) {
            contentHtml += `<div class="log-key-value"><span class="log-key">Risk Score:</span><span class="log-value">${data.risk_score}</span></div>`;
        }
        if (data.reason) {
            contentHtml += `<div class="log-key-value" style="color:var(--danger)"><span class="log-key">Reason:</span><span class="log-value">${data.reason}</span></div>`;
        }
        if (data.latency !== undefined) {
            contentHtml += `<div class="log-key-value"><span class="log-key">Latency:</span><span class="log-value">${data.latency}s</span></div>`;
        }
        if (data.tokens !== undefined) {
            contentHtml += `<div class="log-key-value"><span class="log-key">Tokens:</span><span class="log-value">${data.tokens}</span></div>`;
        }

        div.innerHTML = contentHtml;
        logStream.appendChild(div);

        // Auto-scroll to the bottom whenever a new log arrives
        logStream.scrollTop = logStream.scrollHeight;
    }
});
