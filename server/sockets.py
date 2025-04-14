from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import session
from models import db, User, Message
from datetime import datetime

socketio = SocketIO()


@socketio.on('connect')
def handle_connect():
    if 'user_id' not in session:
        return False

    user = User.query.get(session['user_id'])
    if user:
        user.is_online = True
        db.session.commit()

        emit('user_online', {
            "user_id": user.id,
            "alias": user.alias
        }, broadcast=True)

        return True
    return False


@socketio.on('disconnect')
def handle_disconnect():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.is_online = False
            user.last_seen = datetime.utcnow()
            db.session.commit()

            emit('user_offline', {
                "user_id": user.id,
                "alias": user.alias
            }, broadcast=True)


@socketio.on('join')
def on_join(data):
    if 'channel_id' in data:
        room = f"channel_{data['channel_id']}"
        join_room(room)


@socketio.on('send_message')
def handle_send_message(data):
    if 'content' not in data or 'channel_id' not in data or 'user_id' not in session:
        return

    user_id = session['user_id']
    user = User.query.get(user_id)

    new_message = Message(
        content=data['content'],
        user_id=user_id,
        channel_id=data['channel_id']
    )

    db.session.add(new_message)
    db.session.commit()

    message_data = {
        "id": new_message.id,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "author": {
            "id": user.id,
            "alias": user.alias,
            "avatar_color": user.avatar_color,
            "avatar_face": user.avatar_face
        }
    }

    room = f"channel_{data['channel_id']}"
    emit('new_message', message_data, room=room)


@socketio.on('typing')
def handle_typing(data):
    if 'channel_id' in data and 'user_id' in session:
        user = User.query.get(session['user_id'])
        room = f"channel_{data['channel_id']}"

        emit('user_typing', {
            "user_id": user.id,
            "alias": user.alias
        }, room=room, include_self=False)