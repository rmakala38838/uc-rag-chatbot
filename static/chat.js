// UC Cumberlands RAG Chat Widget
(function() {
    let isOpen = false;
    let chatHistory = [];
    let isLoading = false;

    window.toggleChat = function() {
        const panel = document.getElementById('chat-panel');
        const openIcon = document.getElementById('chat-icon-open');
        const closeIcon = document.getElementById('chat-icon-close');
        const badge = document.getElementById('chat-badge');

        isOpen = !isOpen;

        if (isOpen) {
            panel.classList.add('open');
            openIcon.style.display = 'none';
            closeIcon.style.display = 'block';
            badge.style.display = 'none';
            document.getElementById('chat-input').focus();
        } else {
            panel.classList.remove('open');
            openIcon.style.display = 'block';
            closeIcon.style.display = 'none';
        }
    };

    window.openChat = function() {
        if (!isOpen) toggleChat();
    };

    window.askQuestion = function(question) {
        if (!isOpen) toggleChat();
        setTimeout(() => {
            document.getElementById('chat-input').value = question;
            sendMessage();
        }, 300);
    };

    window.sendMessage = function() {
        if (isLoading) return;

        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        addMessage(message, 'user');
        chatHistory.push({ role: 'user', content: message });

        showTyping();
        isLoading = true;
        document.getElementById('send-btn').disabled = true;

        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: chatHistory })
        })
        .then(res => res.json())
        .then(data => {
            hideTyping();
            isLoading = false;
            document.getElementById('send-btn').disabled = false;

            const formatted = formatResponse(data.response);
            addMessage(formatted, 'bot');
            chatHistory.push({ role: 'assistant', content: data.response });

        })
        .catch(err => {
            hideTyping();
            isLoading = false;
            document.getElementById('send-btn').disabled = false;
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
            console.error('Chat error:', err);
        });
    };

    window.toggleSources = function() {
        const list = document.getElementById('sources-list');
        const chevron = document.querySelector('.sources-chevron');
        if (list.style.display === 'none') {
            list.style.display = 'block';
            chevron.style.transform = 'rotate(180deg)';
        } else {
            list.style.display = 'none';
            chevron.style.transform = 'rotate(0)';
        }
    };

    function addMessage(text, sender) {
        const messages = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.className = `message ${sender}-message`;
        div.innerHTML = `<div class="message-bubble">${text}</div>`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        const messages = document.getElementById('chat-messages');
        const div = document.createElement('div');
        div.id = 'typing-msg';
        div.className = 'message bot-message';
        div.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>`;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function hideTyping() {
        const el = document.getElementById('typing-msg');
        if (el) el.remove();
    }

    function formatResponse(text) {
        // Remove markdown headings
        text = text.replace(/^#{1,4}\s+(.+)$/gm, '<strong>$1</strong>');
        // Convert markdown links [text](url) to clickable HTML links
        text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener">$1</a>');
        // Also make plain URLs clickable
        text = text.replace(/(?<![">])(https?:\/\/[^\s<]+)/g,
            '<a href="$1" target="_blank" rel="noopener">$1</a>');
        // Convert bold **text**
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Remove horizontal rules
        text = text.replace(/^---+$/gm, '');
        // Convert bullet lines to HTML list
        text = text.replace(/((?:^[\-•]\s+.+\n?)+)/gm, function(match) {
            const items = match.trim().split('\n')
                .map(line => '<li>' + line.replace(/^[\-•]\s+/, '') + '</li>')
                .join('');
            return '<ul>' + items + '</ul>';
        });
        // Double newline = paragraph break
        text = text.replace(/\n\n+/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');
        text = '<p>' + text + '</p>';
        // Clean up empty paragraphs
        text = text.replace(/<p>\s*<\/p>/g, '');
        return text;
    }

    function showSources(sources) {
        const container = document.getElementById('chat-sources');
        const list = document.getElementById('sources-list');

        list.innerHTML = sources.map(s => `
            <div class="source-item">
                <a href="${s.url}" target="_blank" title="${s.title}">${s.title || 'Untitled'}</a>
                <span class="source-score">${Math.round(s.similarity * 100)}%</span>
            </div>
        `).join('');

        container.style.display = 'block';
        list.style.display = 'block';
    }

    // Hide badge after first open
    setTimeout(() => {
        const badge = document.getElementById('chat-badge');
        if (badge && !isOpen) {
            badge.style.animation = 'pulse 2s infinite';
        }
    }, 3000);
})();
