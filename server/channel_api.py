from flask import Blueprint, request, jsonify, session, current_app
from server.models import db, Message, Channel, User, Reaction
from server.auth import require_login
from server.utils import sanitize_text
from datetime import datetime
import logging

# Create logger
logger = logging.getLogger('api')

# Create blueprint
channel_api = Blueprint('channel_api', __name__, url_prefix='/api/channels')

@channel_api.route('/', methods=['GET'])
@require_login
def get_channels():
    """Get all available channels"""
    try:
        channels = Channel.query.all()
        
        result = []
        for channel in channels:
            # Get last message timestamp for sorting
            last_message = Message.query.filter_by(channel_id=channel.id).order_by(Message.timestamp.desc()).first()
            last_activity = last_message.timestamp if last_message else channel.created_at
            
            # Get unread message count
            # In a real app, you'd track which messages each user has read
            # This is a simplified example
            
            channel_data = {
                "id": channel.id,
                "name": channel.name,
                "description": channel.description,
                "last_activity": last_activity.isoformat(),
                "created_at": channel.created_at.isoformat()
            }
            
            result.append(channel_data)
            
        # Sort by last activity
        result.sort(key=lambda x: x['last_activity'], reverse=True)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error fetching channels: {str(e)}")
        return jsonify({"error": "Failed to fetch channels"}), 500


@channel_api.route('/<int:channel_id>', methods=['GET'])
@require_login
def get_channel(channel_id):
    """Get details for a specific channel"""
    try:
        channel = Channel.query.get(channel_id)
        if not channel:
            return jsonify({"error": "Channel not found"}), 404
            
        # Get message count
        message_count = Message.query.filter_by(channel_id=channel_id).count()
        
        # Get active users (users who have sent messages to this channel)
        active_users_query = db.session.query(User).join(Message).filter(
            Message.channel_id == channel_id
        ).distinct().limit(10).all()
        
        active_users = [{
            "id": user.id,
            "alias": user.alias,
            "avatar_color": user.avatar_color,
            "is_online": user.is_online
        } for user in active_users_query]
        
        return jsonify({
            "id": channel.id,
            "name": channel.name,
            "description": channel.description,
            "created_at": channel.created_at.isoformat(),
            "message_count": message_count,
            "active_users": active_users
        })
        
    except Exception as e:
        logger.error(f"Error fetching channel {channel_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch channel details"}), 500


@channel_api.route('/<int:channel_id>/messages', methods=['GET'])
@require_login
def get_channel_messages(channel_id):
    """Get messages for a specific channel with pagination"""
    try:
        # Check if channel exists
        channel = Channel.query.get(channel_id)
        if not channel:
            return jsonify({"error": "Channel not found"}), 404
            
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to avoid huge requests
        if per_page > 100:
            per_page = 100
            
        # Get messages with pagination, ordered by timestamp
        messages = Message.query.filter_by(channel_id=channel_id) \
            .order_by(Message.timestamp.desc()) \
            .paginate(page=page, per_page=per_page, error_out=False)

        messages_data = []
        for message in messages.items:
            author = User.query.get(message.user_id)
            if not author:
                # Skip messages with missing authors
                continue

            # Handle encrypted content
            content = message.content
            if message.is_encrypted and current_app.config.get('ENCRYPTION_ENABLED'):
                # In a real app with end-to-end encryption, the client would decrypt
                # For this example, we're just acknowledging it's encrypted
                pass

            # Count reactions by type
            reactions = {}
            for reaction in message.reactions:
                reaction_type = reaction.reaction_type
                if reaction_type not in reactions:
                    reactions[reaction_type] = 0
                reactions[reaction_type] += 1
                
            # Check if current user has reacted to this message
            user_reactions = []
            for reaction in message.reactions:
                if reaction.user_id == session['user_id']:
                    user_reactions.append(reaction.reaction_type)

            messages_data.append({
                "id": message.id,
                "content": content,
                "timestamp": message.timestamp.isoformat(),
                "author": {
                    "id": author.id,
                    "alias": author.alias,
                    "avatar_color": author.avatar_color,
                    "avatar_face": author.avatar_face
                },
                "reactions": reactions,
                "user_reactions": user_reactions,
                "is_encrypted": message.is_encrypted
            })

        # Reverse for chronological order (oldest first)
        messages_data.reverse()

        return jsonify({
            "messages": messages_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": messages.total,
                "pages": messages.pages,
                "has_next": messages.has_next,
                "has_prev": messages.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching messages for channel {channel_id}: {str(e)}")
        return jsonify({"error": "Failed to fetch messages"}), 500


@channel_api.route('/<int:channel_id>/messages', methods=['POST'])
@require_login
def create_message(channel_id):
    """Create a new message in a channel (REST API fallback for socket.io)"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({"error": "Missing message content"}), 400

        # Check if channel exists
        channel = Channel.query.get(channel_id)
        if not channel:
            return jsonify({"error": "Channel not found"}), 404

        user_id = session['user_id']
        
        # Sanitize the content
        content = sanitize_text(data['content'])
        
        # Apply encryption if enabled
        is_encrypted = False
        if current_app.config.get('ENCRYPTION_ENABLED'):
            from .utils import encrypt_message
            encrypted_content, key, nonce = encrypt_message(content)
            is_encrypted = True
        else:
            encrypted_content = content

        # Create new message
        new_message = Message(
            content=encrypted_content,
            user_id=user_id,
            channel_id=channel_id,
            is_encrypted=is_encrypted,
            timestamp=datetime.utcnow()
        )

        db.session.add(new_message)
        db.session.commit()

        # Get author data for response
        author = User.query.get(user_id)

        # Response data
        message_data = {
            "id": new_message.id,
            "content": content,  # Original content for display
            "timestamp": new_message.timestamp.isoformat(),
            "author": {
                "id": author.id,
                "alias": author.alias,
                "avatar_color": author.avatar_color,
                "avatar_face": author.avatar_face
            },
            "reactions": {},
            "user_reactions": [],
            "is_encrypted": is_encrypted
        }

        # In a real app, you would also emit via socket.io
        # This is just the REST API fallback

        return jsonify(message_data), 201
        
    except Exception as e:
        logger.error(f"Error creating message in channel {channel_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to create message"}), 500


@channel_api.route('/<int:channel_id>/messages/<int:message_id>', methods=['DELETE'])
@require_login
def delete_message(channel_id, message_id):
    """Delete a message (user can only delete their own messages)"""
    try:
        # Check if message exists and belongs to this channel
        message = Message.query.filter_by(id=message_id, channel_id=channel_id).first()
        if not message:
            return jsonify({"error": "Message not found"}), 404

        # Check if user owns this message
        if message.user_id != session['user_id']:
            return jsonify({"error": "Unauthorized - you can only delete your own messages"}), 403

        # Delete message and related reactions
        db.session.delete(message)
        db.session.commit()

        return jsonify({"status": "success", "message": "Message deleted"})
        
    except Exception as e:
        logger.error(f"Error deleting message {message_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to delete message"}), 500


@channel_api.route('/<int:channel_id>/messages/<int:message_id>/reactions', methods=['POST'])
@require_login
def add_reaction(channel_id, message_id):
    """Add a reaction to a message"""
    try:
        data = request.get_json()
        if not data or 'reaction_type' not in data:
            return jsonify({"error": "Missing reaction type"}), 400

        # Check if message exists and belongs to this channel
        message = Message.query.filter_by(id=message_id, channel_id=channel_id).first()
        if not message:
            return jsonify({"error": "Message not found"}), 404

        user_id = session['user_id']
        reaction_type = data['reaction_type']

        # Check if reaction already exists (for toggling)
        existing_reaction = Reaction.query.filter_by(
            user_id=user_id,
            target_id=message_id,
            target_type='message',
            reaction_type=reaction_type,
            message_id=message_id
        ).first()

        if existing_reaction:
            # Toggle off (remove) the reaction
            db.session.delete(existing_reaction)
            db.session.commit()
            status = "removed"
        else:
            # Create new reaction
            new_reaction = Reaction(
                user_id=user_id,
                target_id=message_id,
                target_type='message',
                reaction_type=reaction_type,
                message_id=message_id
            )
            db.session.add(new_reaction)
            db.session.commit()
            status = "added"
            
        # Get updated reactions count
        reactions = {}
        for reaction in message.reactions:
            if reaction.reaction_type not in reactions:
                reactions[reaction.reaction_type] = 0
            reactions[reaction.reaction_type] += 1
            
        return jsonify({
            "status": status,
            "message_id": message_id,
            "reaction_type": reaction_type,
            "reactions": reactions
        })
        
    except Exception as e:
        logger.error(f"Error processing reaction for message {message_id}: {str(e)}")
        db.session.rollback()
        return jsonify({"error": "Failed to process reaction"}), 500