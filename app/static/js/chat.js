/**
 * VenueFlow AI — AI Concierge Chat
 * Handles chat messaging, typing indicators, quick actions, and agent routing display.
 */

const Chat = (() => {
    let isProcessing = false;

    function init() {
        const form = document.getElementById('chat-form');
        if (!form) return;

        form.addEventListener('submit', handleSubmit);

        // Quick action buttons
        document.querySelectorAll('.quick-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const msg = btn.dataset.message;
                if (msg) sendMessage(msg);
            });
        });
    }

    async function handleSubmit(e) {
        e.preventDefault();
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message || isProcessing) return;

        input.value = '';
        await sendMessage(message);
    }

    async function sendMessage(message) {
        if (isProcessing) return;
        isProcessing = true;

        const zone = document.getElementById('user-zone-select')?.value || 'unknown';

        // Add user bubble
        addBubble(message, 'user');

        // Show typing indicator
        const typingId = showTyping();

        // Update send button state
        const sendBtn = document.getElementById('chat-send-btn');
        if (sendBtn) sendBtn.disabled = true;

        try {
            const response = await App.api('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, user_zone: zone }),
            });

            removeTyping(typingId);
            addBubble(response.message, 'system', response.agent, response.confidence);

            // Update agent badge
            const badge = document.getElementById('current-agent-badge');
            if (badge) {
                const agentEmojis = { navigator: '🧭', foodie: '🍕', safety: '🛡️', general: '🤖' };
                badge.textContent = `${agentEmojis[response.agent] || '🤖'} ${response.agent}`;
            }

        } catch (error) {
            removeTyping(typingId);
            addBubble('Sorry, I couldn\'t process that right now. Please try again.', 'system', 'error');
        }

        isProcessing = false;
        if (sendBtn) sendBtn.disabled = false;
    }

    function addBubble(text, type, agent = '', confidence = 0) {
        const container = document.getElementById('chat-messages');
        if (!container) return;

        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${type}`;

        const avatarEmoji = type === 'user' ? '👤' : { navigator: '🧭', foodie: '🍕', safety: '🛡️', general: '🤖', error: '⚠️' }[agent] || '🏟️';

        bubble.innerHTML = `
            <div class="bubble-avatar" aria-hidden="true">${avatarEmoji}</div>
            <div class="bubble-content">
                <p>${escapeHtml(text)}</p>
                ${agent && type !== 'user' ? `<div class="bubble-agent-tag">${agent} agent${confidence ? ` • ${Math.round(confidence * 100)}% confidence` : ''}</div>` : ''}
            </div>
        `;

        container.appendChild(bubble);
        container.scrollTop = container.scrollHeight;
    }

    function showTyping() {
        const container = document.getElementById('chat-messages');
        const id = 'typing-' + Date.now();
        const el = document.createElement('div');
        el.className = 'chat-bubble system';
        el.id = id;
        el.innerHTML = `
            <div class="bubble-avatar" aria-hidden="true">🤖</div>
            <div class="bubble-content">
                <div class="typing-indicator" aria-label="AI is thinking">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
        return id;
    }

    function removeTyping(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Auto-init when DOM ready
    document.addEventListener('DOMContentLoaded', init);

    return { sendMessage };
})();
