from functools import wraps
from flask import session, redirect, url_for, request, Blueprint, jsonify
from models import db, User
import secrets
import random
from datetime import datetime

auth = Blueprint('auth', __name__)


def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api'):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for('auth.create_anonymous_user', next=request.url))
        return f(*args, **kwargs)

    return decorated_function


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


@auth.route('/create-anonymous-user')
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
    session.permanent = True

    next_page = request.args.get('next', url_for('routes.chat'))
    return redirect(next_page)


@auth.route('/reset-identity', methods=['POST'])
@require_login
def reset_identity():
    user = User.query.get(session['user_id'])

    new_alias = generate_alias()
    new_avatar = generate_avatar_data()

    user.alias = new_alias
    user.avatar_color = new_avatar["color"]
    user.avatar_face = new_avatar["face"]

    db.session.commit()
    session['alias'] = new_alias

    return jsonify({
        "status": "success",
        "new_identity": {
            "alias": new_alias,
            "avatar_color": new_avatar["color"],
            "avatar_face": new_avatar["face"]
        }
    })