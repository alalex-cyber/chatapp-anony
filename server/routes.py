from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session, flash, current_app
from models import db, User, Channel, Message, Post, Comment, Reaction
from werkzeug.utils import secure_filename
import os
import secrets
from auth import require_login

routes = Blueprint('routes', __name__)
api = Blueprint('api', __name__, url_prefix='/api')


# Main routes
@routes.route('/')
def index():
    return redirect(url_for('routes.chat'))


@routes.route('/chat')
@require_login
def chat():
    return render_template('chat.html')


@routes.route('/social-feed')
@require_login
def social_feed():
    return render_template('social_feed.html')


@routes.route('/settings')
@require_login
def settings():
    return render_template('settings.html')


# API endpoints for messages
@api.route('/messages', methods=['GET'])
@require_login
def get_messages():
    channel_id = request.args.get('channel_id', 1, type=int)
    messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.timestamp).all()

    messages_data = []
    for message in messages:
        author = User.query.get(message.user_id)
        reactions_data = {}
        for reaction in message.reactions:
            reactions_data[reaction.reaction_type] = reactions_data.get(reaction.reaction_type, 0) + 1

        messages_data.append({
            "id": message.id,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "author": {
                "id": author.id,
                "alias": author.alias,
                "avatar_color": author.avatar_color,
                "avatar_face": author.avatar_face
            },
            "reactions": reactions_data
        })

    return jsonify(messages_data)


@api.route('/messages', methods=['POST'])
@require_login
def create_message():
    data = request.get_json()

    if not data or 'content' not in data or 'channel_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    new_message = Message(
        content=data['content'],
        user_id=session['user_id'],
        channel_id=data['channel_id']
    )

    db.session.add(new_message)
    db.session.commit()

    return jsonify(new_message.to_dict()), 201


# API endpoints for posts
@api.route('/posts', methods=['GET'])
@require_login
def get_posts():
    posts = Post.query.order_by(Post.created_at.desc()).all()

    posts_data = []
    for post in posts:
        author = User.query.get(post.user_id)
        posts_data.append({
            "id": post.id,
            "content": post.content,
            "image_url": post.image_url,
            "created_at": post.created_at.isoformat(),
            "author": author.to_dict(),
            "comment_count": Comment.query.filter_by(post_id=post.id).count(),
            "like_count": Reaction.query.filter_by(target_id=post.id, target_type='post', reaction_type='like').count()
        })

    return jsonify(posts_data)


@api.route('/posts', methods=['POST'])
@require_login
def create_post():
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        content = request.form.get('content')
        image = request.files.get('image')

        image_url = None
        if image and allowed_file(image.filename):
            filename = secure_filename(f"{secrets.token_hex(8)}_{image.filename}")
            image.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            image_url = f"/static/uploads/{filename}"
    else:
        data = request.get_json()
        if not data or 'content' not in data:
            return jsonify({"error": "Missing content"}), 400
        content = data['content']
        image_url = data.get('image_url')

    new_post = Post(content=content, image_url=image_url, user_id=session['user_id'])
    db.session.add(new_post)
    db.session.commit()

    return jsonify(new_post.to_dict()), 201


# Utility function
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']