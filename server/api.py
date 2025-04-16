from flask import Blueprint, request, jsonify, session, current_app
from .models import db, User, Channel, Message, Post, Comment, Reaction, DirectMessage, Student
from .auth import require_login
from .utils import sanitize_text, allowed_file, save_file, encrypt_message, decrypt_message
from datetime import datetime

api = Blueprint('api', __name__, url_prefix='/api')


# User endpoints
@api.route('/users/me', methods=['GET'])
@require_login
def get_current_user():
    """Get current user information"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.to_dict())


@api.route('/users/<int:user_id>', methods=['GET'])
@require_login
def get_user(user_id):
    """Get information about another user (limited for anonymity)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Return limited information for anonymity
    return jsonify({
        "id": user.id,
        "alias": user.alias,
        "avatar_color": user.avatar_color,
        "avatar_face": user.avatar_face,
        "is_online": user.is_online,
        "last_active": user.last_seen.isoformat() if user.last_seen else None
    })


@api.route('/users/settings', methods=['GET'])
@require_login
def get_user_settings():
    """Get current user's settings"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(user.get_settings())


@api.route('/users/settings', methods=['PUT'])
@require_login
def update_user_settings():
    """Update user settings"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update avatar if provided
    if 'avatar_color' in data:
        user.avatar_color = data['avatar_color']
    if 'avatar_face' in data:
        user.avatar_face = data['avatar_face']

    # Update settings JSON
    current_settings = user.get_settings()
    keys_to_update = [
        'theme', 'font_size', 'chat_bubble_style', 'online_status',
        'read_receipts', 'typing_indicators', 'sound_alerts', 'message_retention'
    ]

    for key in keys_to_update:
        if key in data:
            current_settings[key] = data[key]

    user.set_settings(current_settings)
    db.session.commit()

    return jsonify({"status": "success", "settings": user.get_settings()})


# Channel endpoints
@api.route('/channels', methods=['GET'])
@require_login
def get_channels():
    """Get all available channels"""
    channels = Channel.query.all()
    return jsonify([{
        "id": channel.id,
        "name": channel.name,
        "description": channel.description
    } for channel in channels])


@api.route('/channels/<int:channel_id>/messages', methods=['GET'])
@require_login
def get_channel_messages(channel_id):
    """Get messages for a specific channel with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    # Get messages with pagination
    messages = Message.query.filter_by(channel_id=channel_id) \
        .order_by(Message.timestamp.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    messages_data = []
    for message in messages.items:
        author = User.query.get(message.user_id)

        # Decrypt message if needed
        content = message.content
        if message.is_encrypted and current_app.config.get('ENCRYPTION_ENABLED'):
            # In a real app, we would retrieve the encryption keys from a secure store
            # For demo purposes, we're just handling the fact that messages are encrypted
            pass

        # Count reactions by type
        reactions = {}
        for reaction in message.reactions:
            reaction_type = reaction.reaction_type
            if reaction_type not in reactions:
                reactions[reaction_type] = 0
            reactions[reaction_type] += 1

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
            "is_encrypted": message.is_encrypted
        })

    # Reverse to get chronological order
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


# Message endpoints
@api.route('/messages', methods=['POST'])
@require_login
def create_message():
    """Create a new message in a channel"""
    data = request.get_json()
    if not data or 'content' not in data or 'channel_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if channel exists
    channel = Channel.query.get(data['channel_id'])
    if not channel:
        return jsonify({"error": "Channel not found"}), 404

    # Sanitize the content
    content = sanitize_text(data['content'])

    # Apply encryption if enabled
    if current_app.config.get('ENCRYPTION_ENABLED'):
        encrypted_content, key, nonce = encrypt_message(content)
        is_encrypted = True
    else:
        encrypted_content = content
        is_encrypted = False

    # Create new message
    new_message = Message(
        content=encrypted_content,
        user_id=session['user_id'],
        channel_id=data['channel_id'],
        is_encrypted=is_encrypted
    )

    db.session.add(new_message)
    db.session.commit()

    # Get author data for response
    author = User.query.get(new_message.user_id)

    # Response data
    message_data = {
        "id": new_message.id,
        "content": content,  # Return original content for display
        "timestamp": new_message.timestamp.isoformat(),
        "author": {
            "id": author.id,
            "alias": author.alias,
            "avatar_color": author.avatar_color,
            "avatar_face": author.avatar_face
        },
        "reactions": {},
        "is_encrypted": is_encrypted
    }

    # The socket event for real-time update is handled in sockets.py

    return jsonify(message_data), 201


@api.route('/messages/<int:message_id>', methods=['GET'])
@require_login
def get_message(message_id):
    """Get a specific message"""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    author = User.query.get(message.user_id)

    # Count reactions
    reactions = {}
    for reaction in message.reactions:
        reaction_type = reaction.reaction_type
        if reaction_type not in reactions:
            reactions[reaction_type] = 0
        reactions[reaction_type] += 1

    return jsonify({
        "id": message.id,
        "content": message.content,
        "timestamp": message.timestamp.isoformat(),
        "author": {
            "id": author.id,
            "alias": author.alias,
            "avatar_color": author.avatar_color,
            "avatar_face": author.avatar_face
        },
        "channel_id": message.channel_id,
        "reactions": reactions,
        "is_encrypted": message.is_encrypted
    })


@api.route('/messages/<int:message_id>', methods=['DELETE'])
@require_login
def delete_message(message_id):
    """Delete a message (user can only delete their own messages)"""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    # Check if user owns this message
    if message.user_id != session['user_id']:
        return jsonify({"error": "Unauthorized"}), 403

    # Delete message and related reactions
    db.session.delete(message)
    db.session.commit()

    return jsonify({"status": "success", "message": "Message deleted"})


# Post endpoints for social feed
@api.route('/posts', methods=['GET'])
@require_login
def get_posts():
    """Get posts for the social feed with pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Get posts with pagination
    posts = Post.query.order_by(Post.created_at.desc()) \
        .paginate(page=page, per_page=per_page, error_out=False)

    posts_data = []
    for post in posts.items:
        author = User.query.get(post.user_id)

        # Get like count
        like_count = Reaction.query.filter_by(
            target_id=post.id,
            target_type='post',
            reaction_type='like'
        ).count()

        # Check if current user has liked this post
        user_liked = Reaction.query.filter_by(
            target_id=post.id,
            target_type='post',
            reaction_type='like',
            user_id=session['user_id']
        ).first() is not None

        # Get comment count
        comment_count = Comment.query.filter_by(post_id=post.id).count()

        posts_data.append({
            "id": post.id,
            "content": post.content,
            "image_url": post.image_url,
            "created_at": post.created_at.isoformat(),
            "author": {
                "id": author.id,
                "alias": author.alias,
                "avatar_color": author.avatar_color,
                "avatar_face": author.avatar_face
            },
            "like_count": like_count,
            "comment_count": comment_count,
            "user_liked": user_liked
        })

    return jsonify({
        "posts": posts_data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": posts.total,
            "pages": posts.pages,
            "has_next": posts.has_next,
            "has_prev": posts.has_prev
        }
    })


@api.route('/posts', methods=['POST'])
@require_login
def create_post():
    """Create a new post in the social feed"""
    # Check content type for file upload
    image_url = None

    if request.content_type and request.content_type.startswith('multipart/form-data'):
        # Handle form submission with possible file
        content = request.form.get('content')
        image = request.files.get('image')

        if image and allowed_file(image.filename):
            image_url = save_file(image)
    else:
        # Handle JSON request
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({"error": "Missing content"}), 400

        content = data['content']
        image_url = None  # JSON requests don't support file uploads

    # Sanitize content
    content = sanitize_text(content)

    # Create new post
    new_post = Post(
        content=content,
        image_url=image_url,
        user_id=session['user_id']
    )

    db.session.add(new_post)
    db.session.commit()

    # Get author data for response
    author = User.query.get(new_post.user_id)

    return jsonify({
        "id": new_post.id,
        "content": new_post.content,
        "image_url": new_post.image_url,
        "created_at": new_post.created_at.isoformat(),
        "author": {
            "id": author.id,
            "alias": author.alias,
            "avatar_color": author.avatar_color,
            "avatar_face": author.avatar_face
        },
        "like_count": 0,
        "comment_count": 0,
        "user_liked": False
    }), 201


@api.route('/posts/<int:post_id>', methods=['DELETE'])
@require_login
def delete_post(post_id):
    """Delete a post (user can only delete their own posts)"""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    # Check if user owns this post
    if post.user_id != session['user_id']:
        return jsonify({"error": "Unauthorized"}), 403

    # Delete post and related comments/reactions
    db.session.delete(post)
    db.session.commit()

    return jsonify({"status": "success", "message": "Post deleted"})


# Comment endpoints
@api.route('/posts/<int:post_id>/comments', methods=['GET'])
@require_login
def get_comments(post_id):
    """Get comments for a specific post"""
    # Check if post exists
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at).all()

    comments_data = []
    for comment in comments:
        author = User.query.get(comment.user_id)

        # Get like count
        like_count = Reaction.query.filter_by(
            target_id=comment.id,
            target_type='comment',
            reaction_type='like'
        ).count()

        # Check if current user has liked this comment
        user_liked = Reaction.query.filter_by(
            target_id=comment.id,
            target_type='comment',
            reaction_type='like',
            user_id=session['user_id']
        ).first() is not None

        comments_data.append({
            "id": comment.id,
            "content": comment.content,
            "created_at": comment.created_at.isoformat(),
            "author": {
                "id": author.id,
                "alias": author.alias,
                "avatar_color": author.avatar_color,
                "avatar_face": author.avatar_face
            },
            "like_count": like_count,
            "user_liked": user_liked
        })

    return jsonify(comments_data)


@api.route('/posts/<int:post_id>/comments', methods=['POST'])
@require_login
def create_comment(post_id):
    """Create a comment on a post"""
    # Check if post exists
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"error": "Missing content"}), 400

    # Sanitize content
    content = sanitize_text(data['content'])

    # Create comment
    new_comment = Comment(
        content=content,
        user_id=session['user_id'],
        post_id=post_id
    )

    db.session.add(new_comment)
    db.session.commit()

    # Get author data for response
    author = User.query.get(new_comment.user_id)

    return jsonify({
        "id": new_comment.id,
        "content": new_comment.content,
        "created_at": new_comment.created_at.isoformat(),
        "author": {
            "id": author.id,
            "alias": author.alias,
            "avatar_color": author.avatar_color,
            "avatar_face": author.avatar_face
        },
        "like_count": 0,
        "user_liked": False
    }), 201


@api.route('/comments/<int:comment_id>', methods=['DELETE'])
@require_login
def delete_comment(comment_id):
    """Delete a comment (user can only delete their own comments)"""
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    # Check if user owns this comment
    if comment.user_id != session['user_id']:
        return jsonify({"error": "Unauthorized"}), 403

    # Delete comment and related reactions
    db.session.delete(comment)
    db.session.commit()

    return jsonify({"status": "success", "message": "Comment deleted"})


# Reaction endpoints
@api.route('/reactions', methods=['POST'])
@require_login
def add_reaction():
    """Add or toggle a reaction (like, heart, etc.)"""
    data = request.get_json()
    if not data or 'target_id' not in data or 'target_type' not in data or 'reaction_type' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    # Check if valid target_type
    if data['target_type'] not in ['message', 'post', 'comment']:
        return jsonify({"error": "Invalid target type"}), 400

    user_id = session['user_id']
    target_id = data['target_id']
    target_type = data['target_type']
    reaction_type = data['reaction_type']

    # Check if target exists
    if target_type == 'message':
        target = Message.query.get(target_id)
    elif target_type == 'post':
        target = Post.query.get(target_id)
    elif target_type == 'comment':
        target = Comment.query.get(target_id)

    if not target:
        return jsonify({"error": f"{target_type.capitalize()} not found"}), 404

    # Check if reaction already exists (for toggling)
    existing_reaction = Reaction.query.filter_by(
        user_id=user_id,
        target_id=target_id,
        target_type=target_type,
        reaction_type=reaction_type
    ).first()

    if existing_reaction:
        # Toggle off (remove) the reaction
        db.session.delete(existing_reaction)
        db.session.commit()
        return jsonify({"status": "removed"})

    # Create new reaction
    new_reaction = Reaction(
        user_id=user_id,
        target_id=target_id,
        target_type=target_type,
        reaction_type=reaction_type
    )

    # Set message_id if target is a message
    if target_type == 'message':
        new_reaction.message_id = target_id

    db.session.add(new_reaction)
    db.session.commit()

    return jsonify({"status": "added"})


# Direct Message endpoints
@api.route('/direct-messages', methods=['GET'])
@require_login
def get_direct_messages():
    """Get direct messages between current user and another user"""
    user_id = session['user_id']
    recipient_id = request.args.get('user_id', type=int)

    if not recipient_id:
        return jsonify({"error": "Recipient ID required"}), 400

    # Check if recipient exists
    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({"error": "Recipient not found"}), 404

    # Get messages between the two users
    messages = DirectMessage.query.filter(
        ((DirectMessage.sender_id == user_id) & (DirectMessage.recipient_id == recipient_id)) |
        ((DirectMessage.sender_id == recipient_id) & (DirectMessage.recipient_id == user_id))
    ).order_by(DirectMessage.timestamp).all()

    messages_data = []
    for msg in messages:
        sender = User.query.get(msg.sender_id)

        # Decrypt message if needed
        content = msg.content
        if msg.is_encrypted and current_app.config.get('ENCRYPTION_ENABLED'):
            # In a real app, we would retrieve the encryption keys from a secure store
            pass

        messages_data.append({
            "id": msg.id,
            "content": content,
            "timestamp": msg.timestamp.isoformat(),
            "sender": {
                "id": sender.id,
                "alias": sender.alias,
                "avatar_color": sender.avatar_color,
                "avatar_face": sender.avatar_face
            },
            "is_read": msg.is_read,
            "is_encrypted": msg.is_encrypted
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
    """Send a direct message to another user"""
    data = request.get_json()
    if not data or 'content' not in data or 'recipient_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    sender_id = session['user_id']
    recipient_id = data['recipient_id']

    # Check if recipient exists
    recipient = User.query.get(recipient_id)
    if not recipient:
        return jsonify({"error": "Recipient not found"}), 404

    # Sanitize content
    content = sanitize_text(data['content'])

    # Apply encryption if enabled
    if current_app.config.get('ENCRYPTION_ENABLED'):
        encrypted_content, key, nonce = encrypt_message(content)
        is_encrypted = True
    else:
        encrypted_content = content
        is_encrypted = False

    # Create direct message
    new_dm = DirectMessage(
        content=encrypted_content,
        sender_id=sender_id,
        recipient_id=recipient_id,
        is_encrypted=is_encrypted,
        is_read=False
    )

    db.session.add(new_dm)
    db.session.commit()

    # Get sender data for response
    sender = User.query.get(sender_id)

    message_data = {
        "id": new_dm.id,
        "content": content,  # Original content for display
        "timestamp": new_dm.timestamp.isoformat(),
        "sender": {
            "id": sender.id,
            "alias": sender.alias,
            "avatar_color": sender.avatar_color,
            "avatar_face": sender.avatar_face
        },
        "is_read": False,
        "is_encrypted": is_encrypted
    }

    # The socket event for real-time update is handled in sockets.py

    return jsonify(message_data), 201