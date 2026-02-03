document.addEventListener('DOMContentLoaded', () => {
    console.log('🔌 ws-client.js loaded - initializing WebSocket...');
    const wsIndicator = document.getElementById('ws-indicator');
    const statusText = wsIndicator ? wsIndicator.nextElementSibling : null;

    // Note: Indicator is optional - WebSocket should always connect
    const updateIndicator = (color, title, text) => {
        if (wsIndicator) {
            wsIndicator.style.backgroundColor = color;
            wsIndicator.setAttribute('title', title);
        }
        if (statusText) {
            statusText.textContent = text;
        }
    };

    // Initial state (if indicator exists)
    updateIndicator('#95a5a6', 'Conectando...', 'Conectando...'); // Gray

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;

    let ws;
    let reconnectTimeout;
    let heartbeatInterval;
    const RECONNECT_DELAY = 2000; // 2 seconds
    const HEARTBEAT_INTERVAL = 25000; // 25 seconds (keep connection alive)

    const stopHeartbeat = () => {
        if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
        }
    };

    const startHeartbeat = () => {
        stopHeartbeat();
        heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                console.log('💓 WebSocket heartbeat ping');
                ws.send('ping'); // Keep connection alive
            }
        }, HEARTBEAT_INTERVAL);
    };

    const connectWebSocket = () => {
        // Clear any pending reconnect
        if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
            reconnectTimeout = null;
        }

        // Don't create a new connection if one is already open or connecting
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            console.log('🔌 WebSocket already connected/connecting, skipping');
            return;
        }

        console.log('🔌 Attempting WebSocket connection to:', wsUrl);
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✅ WebSocket connected successfully');
            updateIndicator('#28a745', 'Conectado', 'En Vivo'); // Green
            startHeartbeat();
        };

        ws.onmessage = (event) => {
            // Ignore pong responses
            if (event.data === 'pong') return;

            try {
                const message = JSON.parse(event.data);
                console.log('📨 WebSocket message received:', message);

                // Cuando el monitor termina un ciclo, notifica a todos los componentes
                if (message.type === 'db_updated') {
                    if (message.notification && window.showToast) {
                        window.showToast(message.notification, message.level || 'info');
                    }
                    window.dispatchEvent(new CustomEvent('data-refresh-needed', { detail: message }));
                }
            } catch (e) {
                console.warn('WebSocket received non-JSON message:', event.data);
            }
        };

        ws.onclose = (event) => {
            console.warn('🔌 WebSocket disconnected. Code:', event.code, 'Reason:', event.reason || 'none');
            updateIndicator('#dc3545', 'Desconectado. Reconectando...', 'Reconectando...'); // Red
            stopHeartbeat();

            // Schedule reconnect with setTimeout (not setInterval to avoid multiple attempts)
            reconnectTimeout = setTimeout(() => {
                console.log('🔄 Attempting to reconnect WebSocket...');
                connectWebSocket();
            }, RECONNECT_DELAY);
        };

        ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            // Don't close here - let onclose handle reconnection
        };
    };

    connectWebSocket();
});
