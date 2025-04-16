from flask import Flask, render_template, redirect, url_for, request, jsonify, session, flash
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
import os
import secrets
import json
import random

from flask_socketio import join_room

# Import shared extensions
from server.extensions import db, socketio

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_development')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///campus_connect.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions with the app
db.init_app(app)
socketio.init_app(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
print("SocketIO initialized with CORS allowed origins:")

migrate = Migrate(app, db)
CORS(app)

# Import models after extensions are initialized
from server.models import User, Channel, Message, Post, Comment, Reaction, Student, DirectMessage


# Helper functions
def generate_alias():
    adjectives = [
        "Anonymous", "Mysterious", "Hidden", "Secret", "Unknown", "Unnamed",
        "Silent", "Quiet", "Peaceful", "Creative", "Curious", "Brilliant",
        "Thoughtful", "Wise", "Gentle", "Clever", "Kind", "Brave", "Bold"
    ]
    return f"{random.choice(adjectives)}"


def generate_avatar_data():
    colors = ["blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"]
    faces = ["blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"]
    return {"color": random.choice(colors), "face": random.choice(faces)}


# Routes
@app.route('/')
def index():
    return redirect(url_for('chat'))


@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('create_anonymous_user', next=url_for('chat')))
    return render_template('chat.html')


@app.route('/social-feed')
def social_feed():
    if 'user_id' not in session:
        return redirect(url_for('create_anonymous_user', next=url_for('social_feed')))
    return render_template('social_feed.html')


@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('create_anonymous_user', next=url_for('settings')))
    return render_template('settings.html')


@app.route('/create-anonymous-user')
def create_anonymous_user():
    session_id = secrets.token_hex(16)
    alias = generate_alias()
    avatar_data = generate_avatar_data()

    new_user = User(
        alias=alias,
        session_id=session_id,
        avatar_color=avatar_data["color"],
        avatar_face=avatar_data["face"]
    )

    db.session.add(new_user)
    db.session.commit()

    session['user_id'] = new_user.id
    session['alias'] = new_user.alias

    next_page = request.args.get('next', url_for('chat'))
    return redirect(next_page)


# API endpoints
@app.route('/api/messages', methods=['GET'])
def get_channel_messages():
    channel_id = request.args.get('channel_id', 1, type=int)
    messages = Message.query.filter_by(channel_id=channel_id).order_by(Message.timestamp).all()

    messages_data = []
    for message in messages:
        author = User.query.get(message.user_id)
        messages_data.append({
            "id": message.id,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "author": {
                "id": author.id,
                "alias": author.alias,
                "avatar_color": author.avatar_color,
                "avatar_face": author.avatar_face
            }
        })

    return jsonify(messages_data)


@app.route('/api/messages', methods=['POST'])
def create_message():
    data = request.get_json()

    if not data or 'content' not in data or 'channel_id' not in data:
        return jsonify({"error": "Missing required fields"}), 400

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    # Create the message using ORM
    new_message = Message(
        content=data['content'],
        user_id=user_id,
        channel_id=data['channel_id']
    )

    db.session.add(new_message)
    db.session.commit()

    # Get the author
    author = User.query.get(new_message.user_id)

    # Prepare message data for response
    message_data = {
        "id": new_message.id,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "author": {
            "id": author.id,
            "alias": author.alias,
            "avatar_color": author.avatar_color,
            "avatar_face": author.avatar_face
        }
    }

    # Emit via Socket.IO
    socketio.emit('new_message', message_data, room=f"channel_{data['channel_id']}")

    return jsonify(message_data), 201


# Socket events
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.is_online = True
            db.session.commit()
            emit('user_online', {"user_id": user.id, "alias": user.alias}, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.is_online = False
            user.last_seen = datetime.utcnow()
            db.session.commit()
            emit('user_offline', {"user_id": user.id, "alias": user.alias}, broadcast=True)


@socketio.on('join')
def on_join(data):
    if 'channel_id' in data:
        room = f"channel_{data['channel_id']}"
        join_room(room)


@socketio.on('typing')
def handle_typing(data):
    if 'channel_id' in data:
        room = f"channel_{data['channel_id']}"
        user = User.query.get(session['user_id'])
        emit('typing', {"user_id": user.id, "alias": user.alias}, room=room, include_self=False)


# CLI Commands
@app.cli.command("init-db")
def init_db_command():
    """Initialize the database with tables and initial data."""
    db.create_all()

    # Create default channels if they don't exist
    if Channel.query.count() == 0:
        db.session.add(Channel(name="General", description="General discussion for everyone"))
        db.session.add(Channel(name="Social Feed", description="Share moments with your campus community"))
        db.session.commit()

    print("Initialized the database.")


# Initialize database
# Create an app context for database initialization
with app.app_context():
    db.create_all()
    # Create default channels if they don't exist
    if Channel.query.count() == 0:
        db.session.add(Channel(name="General", description="General discussion for everyone"))
        db.session.add(Channel(name="Social Feed", description="Share moments with your campus community"))
        db.session.commit()

# Run app
if __name__ == '__main__':
    socketio.run(app, debug=True)