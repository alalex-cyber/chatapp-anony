from flask import Blueprint, request, jsonify, session, current_app
from models import db, User, Channel, Message, Post, Comment, Reaction, DirectMessage
from auth import require_login
from utils import save_file, sanitize_text
from datetime import datetime

api = Blueprint('api', __name__, url_prefix='/api')


# User endpoints
@api.route('/users/current', methods=['GET'])
@require_login
def get_current_user():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict())


@api.route('/users/settings', methods=['GET'])
@require_login
def get_user_settings():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.get_settings())


@api.route('/users/settings', methods=['PUT'])
@require_login
def update_user_settings():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update available attributes
    if 'avatar_color' in data:
        user.avatar_color = data['avatar_color']
    if 'avatar_face' in data:
        user.avatar_face = data['avatar_face']

    # Update settings JSON
    current_settings = user.get_settings()
    for key in ['theme', 'font_size', 'chat_bubble_style', 'online_status',
                'read_receipts', 'typing_indicators', 'sound_alerts', 'message_retention']:
        if key in data:
            current_settings[key] = data[key]

    user.set_settings(current_settings)
    db.session.commit()

    return jsonify({"status": "success", "settings": user.get_settings()})


# Channel endpoints
@api.route('/channels', methods=['GET'])
@require_login
def get_channels():
    channels = Channel.query.all()
    return jsonify([channel.to_dict() for channel in channels])


# Expanded message endpoints
@api.route('/messages/<int:message_id>', methods=['PUT'])
@require_login
def update_message(message_id):
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.user_id != session['user_id']:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content"}), 400

    message.content = sanitize_text(data['content'])
    db.session.commit()

    return jsonify(message.to_dict())


@api.route('/messages/<int:message_id>', methods=['DELETE'])
@require_login
def delete_message(message_id):
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.user_id != session['user_id']:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(message)
    db.session.commit()

    return jsonify({"status": "success"})


# Reaction endpoints
@api.route('/reactions', methods=['POST'])
@require_login
def add_reaction():
    data = request.get_json()
    if not data or 'target_id' not in data or 'target_type' not in data or 'reaction_type' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if reaction already exists
    existing = Reaction.query.filter_by(
        user_id=session['user_id'],
        target_id=data['target_id'],
        target_type=data['target_type'],
        reaction_type=data['reaction_type']
    ).first()

    if existing:
        # Toggle off the reaction
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"status": "removed"})

    # Create new reaction
    new_reaction = Reaction(
        user_id=session['user_id'],
        target_id=data['target_id'],
        target_type=data['target_type'],
        reaction_type=data['reaction_type']
    )

    # Also set message_id if target is a message
    if data['target_type'] == 'message':
        new_reaction.message_id = data['target_id']

    db.session.add(new_reaction)
    db.session.commit()

    return jsonify({"status": "added"})


# Comments endpoints
@api.route('/posts/<int:post_id>/comments', methods=['GET'])
@require_login
def get_comments(post_id):
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at).all()

    comments_data = []
    for comment in comments:
        author = User.query.get(comment.user_id)
        comments_data.append({
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author": author.to_dict(),
            "like_count": Reaction.query.filter_by(
                target_id=comment.id,
                target_type='comment',
                reaction_type='like'
            ).count()
        })

    return jsonify(comments_data)


@api.route('/posts/<int:post_id>/comments', methods=['POST'])
@require_login
def create_comment(post_id):
    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content"}), 400

    new_comment = Comment(
        content=sanitize_text(data['content']),
        user_id=session['user_id'],
        post_id=post_id
    )

    db.session.add(new_comment)
    db.session.commit()

    author = User.query.get(new_comment.user_id)
    return jsonify({
        "id": new_comment.id,
        "content": new_comment.content,
        "created_at": new_comment.created_at.isoformat(),
        "author": author.to_dict()
    }), 201


# Direct Message endpoints
@api.route('/direct-messages', methods=['GET'])
@require_login
def get_direct_messages():
    user_id = session['user_id']
    recipient_id = request.args.get('recipient_id', type=int)

    if not recipient_id:
        return jsonify({"error": "Recipient ID required"}), 400

    # Get messages between the two users
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == recipient_id)) |
        ((DirectMessage.sender_id == recipient_id) & (DirectMessage.recipient_id == user_id))
    ).order_by(DirectMessage.timestamp).all()

    messages_data = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)
        messages_data.append({
            "id": msg.id,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "sender": sender.to_dict(),
            "is_read": msg.is_read
        })

    # Mark unread messages as read
    DirectMessage.query.filter_by(
        recipient_id=user_id,
        sender_id=recipient_id,
        is_read=False
    ).update({DirectMessage.is_read: True})

    db.session.commit()

    return jsonify(messages_data)


@api.route('/direct-messages', methods=['POST'])
@require_login
def send_direct_message():
    data = request.get_json()
    if not data or 'content' not in data or 'recipient_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    new_message = DirectMessage(
        content=sanitize_text(data['content']),
        sender_id=session['user_id'],
        recipient_id=data['recipient_id'],
        is_read=False
    )

    db.session.add(new_message)
    db.session.commit()

    sender = User.query.get(new_message.sender_id)
    return jsonify({
        "id": new_message.id,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "sender": sender.to_dict(),
        "is_read": new_message.is_read
    }), 201