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

/**
 * Message Synchronization Module
 * Handles message delivery reliability and recovery from network issues
 */
class MessageSyncManager {
    constructor(socket) {
        this.socket = socket;
        this.pendingMessages = [];
        this.sentMessages = new Map(); // Map of message ID to message data
        this.lastReceivedTimestamp = null;
        this.isOnline = navigator.onLine;
        
        // Load pending messages from local storage if any
        this.loadFromStorage();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
        
        // Listen for socket reconnect events
        this.socket.on('connect', () => this.handleReconnect());
        
        // Listen for acknowledgements
        this.socket.on('message_ack', data => this.handleMessageAck(data));
    }
    
    /**
     * Queue a message to be sent
     * @param {Object} messageData The message data to send
     * @returns {string} A temporary ID for the message
     */
    queueMessage(messageData) {
        // Generate a temporary ID for the message
        const tempId = 'temp_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Add to pending messages
        const pendingMessage = {
            id: tempId,
            data: messageData,
            attempts: 0,
            timestamp: Date.now()
        };
        
        this.pendingMessages.push(pendingMessage);
        this.saveToStorage();
        
        // Try to send immediately if we're online
        if (this.isOnline && this.socket.connected) {
            this.sendPendingMessages();
        }
        
        return tempId;
    }
    
    /**
     * Attempt to send all pending messages
     */
    sendPendingMessages() {
        if (!this.isOnline || !this.socket.connected || this.pendingMessages.length === 0) {
            return;
        }
        
        // Make a copy of the pending messages array since we'll be modifying it
        const messagesToSend = [...this.pendingMessages];
        
        for (const message of messagesToSend) {
            this.sendMessage(message);
        }
    }
    
    /**
     * Send an individual message
     * @param {Object} message The message object to send
     */
    sendMessage(message) {
        // Don't exceed max retry attempts
        if (message.attempts >= 5) {
            console.error(`Failed to send message after ${message.attempts} attempts`, message);
            // Remove from pending queue
            this.removePendingMessage(message.id);
            
            // Notify user
            this.notifyError(message);
            return;
        }
        
        // Increment attempt counter
        message.attempts++;
        this.saveToStorage();
        
        // Send the message
        this.socket.emit('send_message', message.data, (response) => {
            if (response && response.error) {
                console.error('Error sending message:', response.error);
                // Will retry on next reconnect
            } else if (response && response.status === 'success') {
                // Message sent successfully
                this.handleMessageSent(message, response);
            }
        });
    }
    
    /**
     * Handle successful message sending
     * @param {Object} pendingMessage The pending message that was sent
     * @param {Object} response The server response
     */
    handleMessageSent(pendingMessage, response) {
        // Remove from pending queue
        this.removePendingMessage(pendingMessage.id);
        
        // Map temporary ID to real ID
        if (response.message_id) {
            // Store in sent messages map
            this.sentMessages.set(response.message_id, {
                tempId: pendingMessage.id,
                data: pendingMessage.data,
                timestamp: pendingMessage.timestamp
            });
            
            // Clean up old sent messages (keep last 100)
            if (this.sentMessages.size > 100) {
                // Get keys sorted by timestamp
                const sortedKeys = Array.from(this.sentMessages.entries())
                    .sort((a, b) => a[1].timestamp - b[1].timestamp)
                    .map(entry => entry[0]);
                
                // Remove oldest
                this.sentMessages.delete(sortedKeys[0]);
            }
        }
    }
    
    /**
     * Handle message acknowledgement from server
     * @param {Object} data Message acknowledgement data
     */
    handleMessageAck(data) {
        if (data.message_id && this.sentMessages.has(data.message_id)) {
            // Message was successfully received and processed
            this.sentMessages.delete(data.message_id);
        }
    }
    
    /**
     * Remove a message from the pending queue
     * @param {string} messageId The ID of the message to remove
     */
    removePendingMessage(messageId) {
        const index = this.pendingMessages.findIndex(m => m.id === messageId);
        if (index !== -1) {
            this.pendingMessages.splice(index, 1);
            this.saveToStorage();
        }
    }
    
    /**
     * Handle going online
     */
    handleOnline() {
        console.log('Device is online, attempting to send pending messages');
        this.isOnline = true;
        this.sendPendingMessages();
    }
    
    /**
     * Handle going offline
     */
    handleOffline() {
        console.log('Device is offline, messages will be queued');
        this.isOnline = false;
    }
    
    /**
     * Handle socket reconnection
     */
    handleReconnect() {
        console.log('Socket reconnected, syncing messages');
        
        // Send any pending messages
        this.sendPendingMessages();
        
        // Request any missed messages
        if (this.lastReceivedTimestamp) {
            this.socket.emit('sync_messages', {
                channel_id: window.currentChannel,
                since: this.lastReceivedTimestamp
            });
        }
    }
    
    /**
     * Update the last received timestamp when a new message comes in
     * @param {string} timestamp ISO timestamp of the last received message
     */
    updateLastReceived(timestamp) {
        if (timestamp) {
            const date = new Date(timestamp);
            if (!isNaN(date.getTime())) {
                this.lastReceivedTimestamp = timestamp;
                localStorage.setItem('lastMessageTimestamp', timestamp);
            }
        }
    }
    
    /**
     * Save pending messages to local storage
     */
    saveToStorage() {
        try {
            localStorage.setItem('pendingMessages', JSON.stringify(this.pendingMessages));
        } catch (e) {
            console.error('Failed to save pending messages to storage', e);
        }
    }
    
    /**
     * Load pending messages from local storage
     */
    loadFromStorage() {
        try {
            // Load pending messages
            const pendingData = localStorage.getItem('pendingMessages');
            if (pendingData) {
                this.pendingMessages = JSON.parse(pendingData);
            }
            
            // Load last received timestamp
            const lastTimestamp = localStorage.getItem('lastMessageTimestamp');
            if (lastTimestamp) {
                this.lastReceivedTimestamp = lastTimestamp;
            }
        } catch (e) {
            console.error('Failed to load messages from storage', e);
            this.pendingMessages = [];
        }
    }
    
    /**
     * Notify user of error sending message
     * @param {Object} message The message that failed to send
     */
    notifyError(message) {
        // Find the temporary message element
        const tempElement = document.querySelector(`.message[data-temp-id="${message.id}"]`);
        if (tempElement) {
            tempElement.classList.add('message-error');
            
            // Add retry button
            const retryButton = document.createElement('button');
            retryButton.className = 'message-retry-button';
            retryButton.textContent = 'Retry';
            retryButton.addEventListener('click', () => {
                tempElement.classList.remove('message-error');
                retryButton.remove();
                
                // Reset attempts and try again
                message.attempts = 0;
                this.pendingMessages.push(message);
                this.saveToStorage();
                this.sendMessage(message);
            });
            
            tempElement.querySelector('.message-content').appendChild(retryButton);
        }
    }
}

// Integration with main chat.js

// After initializing socket connection:
let syncManager;

function setupSocketConnection() {
    console.log("Initializing Socket.IO connection");
    
    // Use single socket instance
    socket = io({
        reconnection: true,
        reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
        reconnectionDelay: RECONNECT_DELAY,
        timeout: 10000
    });
    
    // Initialize the sync manager after socket is created
    syncManager = new MessageSyncManager(socket);
    
    // Connection events
    socket.on('connect', handleSocketConnect);
    // ... other event handlers
}

// Update the handleNewMessage function to track the last received timestamp
function handleNewMessage(message) {
    console.log('Received new message:', message);
    
    // Update the last received timestamp for sync
    if (message.timestamp) {
        syncManager.updateLastReceived(message.timestamp);
    }
    
    // Only show message if it's for the current channel
    if (message.channel_id === currentChannel) {
        // Check if we need a new date divider
        const messageDate = new Date(message.timestamp).toLocaleDateString();
        checkAndAddDateDivider(messageDate);
        
        // Add the message
        const messageElement = createMessageElement(message);
        messagesContainer.appendChild(messageElement);
        scrollToBottom();
    } else {
        // Update unread count for other channels
        updateUnreadCount(message.channel_id);
    }
}

// Update sendMessage to use the sync manager
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
    
    // Create and display a temporary message
    const tempMessageId = syncManager.queueMessage(messageData);
    
    // Create a temporary visual representation of the message
    const currentUser = {
        alias: USER_ALIAS || 'You',
        avatar_color: 'blue', // Default
        avatar_face: 'blue'   // Default
    };
    
    const tempMessage = {
        id: tempMessageId,
        content: content,
        timestamp: new Date().toISOString(),
        author: currentUser,
        reactions: {},
        is_temp: true
    };
    
    // Add a temporary message to the UI
    const messageElement = createMessageElement(tempMessage);
    messageElement.classList.add('message-pending');
    messageElement.setAttribute('data-temp-id', tempMessageId);
    messagesContainer.appendChild(messageElement);
    
    // Clear the input field
    messageInput.value = '';
    
    // Scroll to the new message
    scrollToBottom();
}

// Add a socket handler for missed messages sync
socket.on('sync_messages', messages => {
    console.log('Received missed messages:', messages);
    
    if (Array.isArray(messages) && messages.length > 0) {
        // Sort by timestamp
        messages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // Process each message
        messages.forEach(message => {
            // Check if we already have this message (avoid duplicates)
            if (!document.querySelector(`.message[data-message-id="${message.id}"]`)) {
                handleNewMessage(message);
            }
        });
    }
});

// Add CSS for pending and error message states
const style = document.createElement('style');
style.textContent = `
.message-pending {
    opacity: 0.7;
}

.message-pending .message-bubble::after {
    content: "⏳";
    position: absolute;
    right: 10px;
    bottom: 10px;
    font-size: 12px;
}

.message-error {
    opacity: 0.6;
}

.message-error .message-bubble {
    border: 1px solid #ef4444;
}

.message-retry-button {
    background-color: #ef4444;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 4px 8px;
    margin-top: 8px;
    cursor: pointer;
    font-size: 12px;
}

.message-retry-button:hover {
    background-color: #dc2626;
}
`;
document.head.appendChild(style);