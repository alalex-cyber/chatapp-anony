// chat.js - Place this in a static/js folder or include in the chat.html template

// Enhanced debugging
console.log("Chat.js loaded and initializing...");

// Initialize Socket.IO connection
console.log("Initializing Socket.IO connection");
const socket = io();

socket.on('connect', () => {
    console.log('Socket.IO connected successfully');
    joinChannel(currentChannel);
});

socket.on('connect_error', (err) => {
    console.error('Socket.IO connection error:', err);
});

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const messageForm = document.getElementById('message-form');
    const messageInput = document.getElementById('message-input');
    const messagesContainer = document.getElementById('messages-container');
    const channelItems = document.querySelectorAll('.channel');
    const typingIndicator = document.querySelector('.typing-indicator');
    let currentChannel = 1; // Default channel ID

    console.log("Chat.js initialized");

    // Initialize Socket.IO connection
    const socket = io();

    // Connection events
    socket.on('connect', () => {
        console.log('Socket.IO connected successfully');
        joinChannel(currentChannel);

        // Update UI to show connected status
        document.querySelector('.subtitle').textContent = 'Connected to chat server';
    });

    socket.on('connect_error', (err) => {
        console.error('Socket.IO connection error:', err);
        document.querySelector('.subtitle').textContent = 'Disconnected - trying to reconnect...';
    });

    // Join a channel
    function joinChannel(channelId) {
        console.log(`Joining channel: ${channelId}`);
        socket.emit('join', { channel_id: channelId });
        currentChannel = channelId;

        // Update UI to show active channel
        channelItems.forEach(channel => {
            const id = parseInt(channel.getAttribute('data-channel-id') || '1');
            if (id === channelId) {
                channel.classList.add('active');
            } else {
                channel.classList.remove('active');
            }
        });

        // Clear messages and load new ones
        messagesContainer.innerHTML = '';
        loadMessages(channelId);
    }

    // Load messages for a channel
    function loadMessages(channelId) {
        fetch(`/api/channels/${channelId}/messages`)
            .then(response => response.json())
            .then(data => {
                if (data.messages && Array.isArray(data.messages)) {
                    displayMessages(data.messages);
                } else {
                    console.error('Invalid message data format:', data);
                }
            })
            .catch(error => {
                console.error('Error loading messages:', error);
                messagesContainer.innerHTML = '<div class="system-message"><div class="system-message-content">Failed to load messages. Please try again later.</div></div>';
            });
    }

    // Display messages in the container
    function displayMessages(messages) {
        // Clear existing messages
        messagesContainer.innerHTML = '';

        if (messages.length === 0) {
            messagesContainer.innerHTML = '<div class="system-message"><div class="system-message-content">No messages yet. Start the conversation!</div></div>';
            return;
        }

        // Add date divider for the first message
        let currentDate = new Date(messages[0].timestamp).toLocaleDateString();
        messagesContainer.appendChild(createDateDivider(currentDate));

        // Add all messages
        messages.forEach((message, index) => {
            // Check if we need a new date divider
            const messageDate = new Date(message.timestamp).toLocaleDateString();
            if (messageDate !== currentDate) {
                currentDate = messageDate;
                messagesContainer.appendChild(createDateDivider(currentDate));
            }

            const messageElement = createMessageElement(message);
            messagesContainer.appendChild(messageElement);
        });

        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Create a date divider element
    function createDateDivider(dateString) {
        const divider = document.createElement('div');
        divider.className = 'date-divider';
        divider.innerHTML = `<div class="date-pill">${dateString}</div>`;
        return divider;
    }

    // Create a message element
    function createMessageElement(message) {
        const div = document.createElement('div');
        div.className = 'message';
        div.setAttribute('data-message-id', message.id);

        const avatarColor = message.author?.avatar_color || 'blue';

        div.innerHTML = `
            <div class="message-avatar ${avatarColor}">
                <div class="avatar-face ${avatarColor}">
                    <div class="avatar-dot ${avatarColor} left"></div>
                    <div class="avatar-dot ${avatarColor} right"></div>
                    <div class="avatar-mouth ${avatarColor}"></div>
                </div>
            </div>
            <div class="message-content">
                <div class="message-bubble">
                    <div class="message-header">
                        <span class="message-sender">${message.author?.alias || 'Anonymous'}</span>
                        <span class="message-time">${formatTime(message.timestamp)}</span>
                    </div>
                    <p class="message-text">${message.content}</p>
                    <div class="message-reactions">
                        ${renderReactions(message.reactions || {})}
                        <span class="add-reaction" data-message-id="${message.id}">+</span>
                    </div>
                </div>
                <div class="message-actions">
                    <span class="message-action" data-action="reply" data-message-id="${message.id}">Reply</span>
                    <span class="message-action" data-action="share" data-message-id="${message.id}">Share</span>
                </div>
            </div>
        `;

        // Add event listeners for reactions
        const addReactionButton = div.querySelector('.add-reaction');
        if (addReactionButton) {
            addReactionButton.addEventListener('click', function() {
                // Show emoji picker or reaction options
                // This could be implemented as a dropdown or modal
                alert('Reaction feature coming soon!');
            });
        }

        return div;
    }

    // Format timestamp
    function formatTime(timestamp) {
        if (!timestamp) return 'Unknown time';
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            console.error('Error formatting timestamp:', e);
            return 'Invalid time';
        }
    }

    // Render reactions
    function renderReactions(reactions) {
        if (!reactions || Object.keys(reactions).length === 0) return '';

        let html = '';
        for (const [type, count] of Object.entries(reactions)) {
            html += `<span class="reaction" data-type="${type}">${type} ${count}</span>`;
        }
        return html;
    }

    // Send a message
    function sendMessage(content, channelId) {
        if (!content.trim()) {
            console.log('Attempting to send empty message, ignoring');
            return;
        }

        const channel = channelId || currentChannel;
        console.log(`Sending message: "${content}" to channel ${channel}`);

        const messageData = {
            content: content,
            channel_id: channel
        };

        socket.emit('send_message', messageData);
        messageInput.value = '';

        // Show temporary sending indicator
        const sendingMessage = document.createElement('div');
        sendingMessage.className = 'system-message';
        sendingMessage.innerHTML = '<div class="system-message-content">Sending message...</div>';
        messagesContainer.appendChild(sendingMessage);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Remove the indicator after a brief delay
        setTimeout(() => {
            if (messagesContainer.contains(sendingMessage)) {
                messagesContainer.removeChild(sendingMessage);
            }
        }, 1000);
    }

    // Handle form submission
    if (messageForm) {
        messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            console.log('Message form submitted');
            sendMessage(messageInput.value, currentChannel);
        });
    }

    // Listen for new messages
    socket.on('new_message', (message) => {
        console.log('Received new message:', message);
        if (message.channel_id === currentChannel) {
            // Check if we need a new date divider
            const messageDate = new Date(message.timestamp).toLocaleDateString();
            const lastDivider = messagesContainer.querySelector('.date-divider:last-of-type');
            const lastDividerDate = lastDivider ? lastDivider.textContent.trim() : '';

            if (messageDate !== lastDividerDate) {
                messagesContainer.appendChild(createDateDivider(messageDate));
            }

            // Add the message
            const messageElement = createMessageElement(message);
            messagesContainer.appendChild(messageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else {
            // Update unread count for other channels
            const channelElement = document.querySelector(`.channel[data-channel-id="${message.channel_id}"]`);
            if (channelElement) {
                let badge = channelElement.querySelector('.channel-badge');
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'channel-badge';
                    channelElement.appendChild(badge);
                }
                const count = parseInt(badge.textContent || '0') + 1;
                badge.textContent = count;
            }
        }
    });

    // Handle typing indicator
    let typingTimeout;
    if (messageInput) {
        messageInput.addEventListener('input', () => {
            clearTimeout(typingTimeout);

            socket.emit('typing', { channel_id: currentChannel });

            typingTimeout = setTimeout(() => {
                console.log('Typing indicator cleared');
            }, 1000);
        });
    }

    // Listen for typing indicator
    socket.on('user_typing', (data) => {
        if (data.channel_id === currentChannel) {
            // Show typing indicator
            showTypingIndicator(data.alias);

            // Hide after 3 seconds
            setTimeout(() => {
                hideTypingIndicator();
            }, 3000);
        }
    });

    // Show typing indicator
    function showTypingIndicator(alias) {
        if (!typingIndicator) return;

        // Create indicator if it doesn't exist
        let indicator = document.querySelector('.typing-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'typing-indicator';
            indicator.innerHTML = `
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            messagesContainer.appendChild(indicator);
        }

        // Make sure it's visible and scroll to it
        indicator.style.display = 'flex';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Hide typing indicator
    function hideTypingIndicator() {
        const indicator = document.querySelector('.typing-indicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    // Channel switching
    channelItems.forEach(channel => {
        channel.addEventListener('click', () => {
            // Get channel ID and join
            const channelId = parseInt(channel.getAttribute('data-channel-id') || '1');
            joinChannel(channelId);

            // Reset badge count
            const badge = channel.querySelector('.channel-badge');
            if (badge) {
                badge.textContent = '0';
                // Hide badge if count is 0
                if (badge.textContent === '0') {
                    badge.style.display = 'none';
                }
            }
        });
    });

    // User online/offline events
    socket.on('user_online', (data) => {
        console.log('User online event:', data);
        // Update UI to show user is online
        document.querySelectorAll(`.dm-item[data-user-id="${data.user_id}"] .status-indicator`).forEach(indicator => {
            indicator.classList.remove('offline');
            indicator.classList.add('online');
        });
    });

    socket.on('user_offline', (data) => {
        console.log('User offline event:', data);
        // Update UI to show user is offline
        document.querySelectorAll(`.dm-item[data-user-id="${data.user_id}"] .status-indicator`).forEach(indicator => {
            indicator.classList.remove('online');
            indicator.classList.add('offline');
        });
    });
});