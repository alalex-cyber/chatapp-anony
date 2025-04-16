# In app.py or a separate database.py file
import sqlite3
from flask import g
from server.app import app

DATABASE = 'campus_connect.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def add_message(content, user_id, channel_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO messages (content, user_id, channel_id) VALUES (?, ?, ?)',
        (content, user_id, channel_id)
    )
    db.commit()
    return cursor.lastrowid


def get_messages(channel_id, limit=50):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT m.id, m.content, m.timestamp, 
               u.id as user_id, u.alias, u.avatar_color, u.avatar_face
        FROM messages m
        JOIN users u ON m.user_id = u.id
        WHERE m.channel_id = ?
        ORDER BY m.timestamp DESC
        LIMIT ?
    ''', (channel_id, limit))

    messages = cursor.fetchall()
    result = []

    for message in messages:
        result.append({
            'id': message['id'],
            'content': message['content'],
            'timestamp': message['timestamp'],
            'author': {
                'id': message['user_id'],
                'alias': message['alias'],
                'avatar_color': message['avatar_color'],
                'avatar_face': message['avatar_face']
            }
        })

    # Return in chronological order
    return list(reversed(result))