from flask import session, current_app
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
from .models import db, User, Message, DirectMessage, Channel, Reaction
from .utils import sanitize_text, encrypt_message, decrypt_message
from .app import socketio

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("Client connected")
    if 'user_id' not in session:
        print("Connection rejected: No user_id in session")
        return False

    user = User.query.get(session['user_id'])
    if not user:
        print(f"Connection rejected: Invalid user_id {session.get('user_id')}")
        return False

    print(f"User {user.id} ({user.alias}) connected")
    user.is_online = True
    user.last_seen = datetime.utcnow()
    db.session.commit()

    # Broadcast to all users that this user is online
    emit('user_online', {
        "user_id": user.id,
        "alias": user.alias
    }, broadcast=True)

    # Join user's personal room for direct messages
    join_room(f"user_{user.id}")

    return True


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("Client disconnected")
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            print(f"User {user.id} ({user.alias}) disconnected")
            user.is_online = False
            user.last_seen = datetime.utcnow()
            db.session.commit()

            # Broadcast to all users that this user is offline
            emit('user_offline', {
                "user_id": user.id,
                "alias": user.alias
            }, broadcast=True)


@socketio.on('join')
def on_join(data):
    """Handle joining a channel room"""
    print(f"Join request received: {data}")
    if 'channel_id' not in data or 'user_id' not in session:
        print("Invalid join request - missing channel_id or user_id")
        return

    channel_id = data['channel_id']
    user_id = session['user_id']

    # Create a room name for the channel
    room = f"channel_{channel_id}"

    # Join the room
    join_room(room)
    print(f"User {user_id} joined room: {room}")

    # Let others know someone has joined
    user = User.query.get(user_id)
    channel = Channel.query.get(channel_id)

    if user and channel:
        # Notify others in the channel
        emit('user_joined_channel', {
            "user_id": user_id,
            "alias": user.alias,
            "channel_id": channel_id
        }, to=room, include_self=False)

        # Send system message
        emit('system_message', {
            "content": f"{user.alias} has joined #{channel.name}",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_id": channel_id
        }, to=room)


@socketio.on('leave')
def on_leave(data):
    """Handle leaving a channel room"""
    if 'channel_id' not in data or 'user_id' not in session:
        return

    channel_id = data['channel_id']
    user_id = session['user_id']

    # Get the room name
    room = f"channel_{channel_id}"

    # Leave the room
    leave_room(room)

    # Let others know someone has left
    user = User.query.get(user_id)
    channel = Channel.query.get(channel_id)

    if user and channel:
        # Notify others in the channel
        emit('user_left_channel', {
            "user_id": user_id,
            "alias": user.alias,
            "channel_id": channel_id
        }, to=room)

        # Send system message
        emit('system_message', {
            "content": f"{user.alias} has left #{channel.name}",
            "timestamp": datetime.utcnow().isoformat(),
            "channel_id": channel_id
        }, to=room)


@socketio.on('send_message')
def handle_send_message(data):
    """Handle sending a message to a channel"""
    print(f"Received message data: {data}")
    if 'content' not in data or 'channel_id' not in data:
        print("Invalid message data - missing content or channel_id")
        return {"error": "Invalid message data"}, 400

    if 'user_id' not in session:
        print("User not in session")
        return {"error": "Authentication required"}, 401

    user_id = session['user_id']
    content = sanitize_text(data['content'])
    channel_id = data['channel_id']

    print(f"Processing message from user {user_id} to channel {channel_id}: {content[:30]}...")

    # Check if channel exists
    channel = Channel.query.get(channel_id)
    if not channel:
        print(f"Channel {channel_id} not found")
        return {"error": "Channel not found"}, 404

    # Apply end-to-end encryption if enabled
    if current_app.config.get('ENCRYPTION_ENABLED', False):
        encrypted_content, key, nonce = encrypt_message(content)
        is_encrypted = True
    else:
        encrypted_content = content
        key = None
        nonce = None
        is_encrypted = False

    # Create and save the message
    try:
        new_message = Message(
            content=encrypted_content,
            user_id=user_id,
            channel_id=channel_id,
            is_encrypted=is_encrypted
        )

        db.session.add(new_message)
        db.session.commit()
        print(f"Message saved with ID: {new_message.id}")

        # Get user for response
        user = User.query.get(user_id)

        # Prepare the message data for broadcasting
        message_data = {
            "id": new_message.id,
            "content": content,  # Send original content to clients
            "timestamp": new_message.timestamp.isoformat(),
            "author": {
                "id": user.id,
                "alias": user.alias,
                "avatar_color": user.avatar_color,
                "avatar_face": user.avatar_face
            },
            "channel_id": channel_id,
            "is_encrypted": is_encrypted,
            "reactions": {}
        }

        # If message is encrypted, add encryption data
        if is_encrypted and key and nonce:
            message_data["encryption"] = {
                "key": key,
                "nonce": nonce
            }

        # Broadcast to the channel room
        room = f"channel_{channel_id}"
        print(f"Broadcasting message to room: {room}")
        emit('new_message', message_data, to=room)

        return message_data

    except Exception as e:
        print(f"Error saving message: {str(e)}")
        db.session.rollback()
        return {"error": "Failed to save message"}, 500


@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator"""
    if 'channel_id' not in data or 'user_id' not in session:
        return

    user_id = session['user_id']
    channel_id = data['channel_id']

    user = User.query.get(user_id)
    if not user:
        return

    # Get the room name
    room = f"channel_{channel_id}"

    # Emit to everyone in the room except the sender
    emit('user_typing', {
        "user_id": user_id,
        "alias": user.alias,
        "channel_id": channel_id
    }, to=room, include_self=False)


@socketio.on('direct_message')
def handle_direct_message(data):
    """Handle direct messages between users"""
    print(f"Received direct message data: {data}")
    if 'content' not in data or 'recipient_id' not in data or 'user_id' not in session:
        print("Invalid direct message data")
        return {"error": "Invalid direct message data"}, 400

    sender_id = session['user_id']
    recipient_id = data['recipient_id']
    content = sanitize_text(data['content'])

    print(f"Processing direct message from user {sender_id} to user {recipient_id}")

    # Apply end-to-end encryption if enabled
    if current_app.config.get('ENCRYPTION_ENABLED', False):
        encrypted_content, key, nonce = encrypt_message(content)
        is_encrypted = True
    else:
        encrypted_content = content
        key = None
        nonce = None
        is_encrypted = False

    # Create and save the direct message
    try:
        new_dm = DirectMessage(
            content=encrypted_content,
            sender_id=sender_id,
            recipient_id=recipient_id,
            is_encrypted=is_encrypted,
            is_read=False
        )

        db.session.add(new_dm)
        db.session.commit()
        print(f"Direct message saved with ID: {new_dm.id}")

        # Get user data for response
        sender = User.query.get(sender_id)

        # Create a unique room for the conversation between these two users
        # We sort the IDs to ensure the same room name regardless of who sends the message
        room_ids = sorted([sender_id, recipient_id])
        room = f"dm_{room_ids[0]}_{room_ids[1]}"

        # Prepare message data for broadcasting
        message_data = {
            "id": new_dm.id,
            "content": content,  # Send original content
            "timestamp": new_dm.timestamp.isoformat(),
            "sender": {
                "id": sender.id,
                "alias": sender.alias,
                "avatar_color": sender.avatar_color,
                "avatar_face": sender.avatar_face
            },
            "recipient_id": recipient_id,
            "is_read": False,
            "is_encrypted": is_encrypted
        }

        # Add encryption data if applicable
        if is_encrypted and key and nonce:
            message_data["encryption"] = {
                "key": key,
                "nonce": nonce
            }

        # Broadcast to the DM room
        emit('new_direct_message', message_data, to=room)

        # Also emit to the recipient's personal room if they're online
        recipient = User.query.get(recipient_id)
        if recipient and recipient.is_online:
            emit('dm_notification', {
                "dm_id": new_dm.id,
                "sender": {
                    "id": sender.id,
                    "alias": sender.alias
                },
                "timestamp": new_dm.timestamp.isoformat()
            }, to=f"user_{recipient_id}")

        return message_data

    except Exception as e:
        print(f"Error saving direct message: {str(e)}")
        db.session.rollback()
        return {"error": "Failed to save direct message"}, 500


@socketio.on('mark_read')
def handle_mark_read(data):
    """Mark messages as read"""
    print(f"Marking messages as read: {data}")
    if 'message_ids' not in data or 'user_id' not in session:
        print("Invalid mark read data")
        return

    recipient_id = session['user_id']
    message_ids = data['message_ids']

    # Update read status for these messages
    try:
        updated = DirectMessage.query.filter(
            DirectMessage.id.in_(message_ids),
            DirectMessage.recipient_id == recipient_id
        ).update({DirectMessage.is_read: True}, synchronize_session=False)

        db.session.commit()
        print(f"Marked {updated} messages as read")

        return {"status": "success", "marked_read": updated}

    except Exception as e:
        print(f"Error marking messages as read: {str(e)}")
        db.session.rollback()
        return {"error": "Failed to mark messages as read"}, 500


@socketio.on('reaction')
def handle_reaction(data):
    """Add or remove a reaction to a message"""
    print(f"Received reaction data: {data}")
    if 'message_id' not in data or 'reaction_type' not in data or 'user_id' not in session:
        print("Invalid reaction data")
        return {"error": "Invalid reaction data"}, 400

    user_id = session['user_id']
    message_id = data['message_id']
    reaction_type = data['reaction_type']

    # Check if message exists
    message = Message.query.get(message_id)
    if not message:
        print(f"Message {message_id} not found")
        return {"error": "Message not found"}, 404

    # Check if reaction already exists
    existing_reaction = Reaction.query.filter_by(
        user_id=user_id,
        target_id=message_id,
        target_type='message',
        reaction_type=reaction_type
    ).first()

    try:
        # Toggle reaction
        if existing_reaction:
            # Remove reaction
            db.session.delete(existing_reaction)
            action = 'removed'
            print(f"Removed {reaction_type} reaction from message {message_id}")
        else:
            # Add reaction
            new_reaction = Reaction(
                user_id=user_id,
                target_id=message_id,
                target_type='message',
                reaction_type=reaction_type,
                message_id=message_id
            )
            db.session.add(new_reaction)
            action = 'added'
            print(f"Added {reaction_type} reaction to message {message_id}")

        db.session.commit()

        # Get updated reaction counts
        reactions = {}
        for reaction in message.reactions:
            if reaction.reaction_type not in reactions:
                reactions[reaction.reaction_type] = 0
            reactions[reaction.reaction_type] += 1

        # Broadcast reaction update to channel
        room = f"channel_{message.channel_id}"
        emit('reaction_update', {
            "message_id": message_id,
            "reactions": reactions,
            "user_id": user_id,
            "action": action,
            "reaction_type": reaction_type
        }, to=room)

        return {
            "status": "success",
            "action": action,
            "reactions": reactions
        }

    except Exception as e:
        print(f"Error processing reaction: {str(e)}")
        db.session.rollback()
        return {"error": "Failed to process reaction"}, 500