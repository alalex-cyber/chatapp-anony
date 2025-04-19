from datetime import datetime
import json
from sqlalchemy.orm import foreign
from werkzeug.security import generate_password_hash, check_password_hash
from server.app import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    alias = db.Column(db.String(50), unique=True, nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=True)  # Optional for anonymous users
    email = db.Column(db.String(100), unique=True, nullable=True)  # Added email field
    password_hash = db.Column(db.String(200), nullable=True)  # Changed to password_hash
    avatar_color = db.Column(db.String(20), nullable=False)
    avatar_face = db.Column(db.String(20), nullable=False)
    settings = db.Column(db.Text, default='{}')
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    student_id = db.Column(db.String(20), db.ForeignKey('student.id'), unique=True, nullable=True)

    messages = db.relationship('Message', backref='author', lazy=True)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='author', lazy=True)
    reactions = db.relationship('Reaction', backref='user', lazy=True)
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
        
    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def verify_password(self, password):
        if self.password_hash:
            return check_password_hash(self.password_hash, password)
        return False

    def get_settings(self):
        return json.loads(self.settings)

    def set_settings(self, settings_dict):
        self.settings = json.dumps(settings_dict)

    def to_dict(self):
        return {
            'id': self.id,
            'alias': self.alias,
            'avatar_color': self.avatar_color,
            'avatar_face': self.avatar_face,
            'is_online': self.is_online,
            'email': self.email  # Include email in the dict
        }


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    messages = db.relationship('Message', backref='channel', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description
        }


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    channel_id = db.Column(db.Integer, db.ForeignKey('channel.id'), nullable=False)
    is_encrypted = db.Column(db.Boolean, default=False)  # Added for end-to-end encryption

    reactions = db.relationship('Reaction', backref='message', lazy=True,
                                cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'is_encrypted': self.is_encrypted
        }


class DirectMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_encrypted = db.Column(db.Boolean, default=False)  # Added for end-to-end encryption

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    comments = db.relationship('Comment', backref='post', lazy=True,
                              cascade='all, delete-orphan')
    reactions = db.relationship(
        'Reaction',
        primaryjoin="and_(Post.id==foreign(Reaction.target_id), Reaction.target_type=='post')",
        backref=db.backref('post_parent', uselist=False),
        lazy=True,
        viewonly=True
    )

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'image_url': self.image_url,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id,
            'comment_count': Comment.query.filter_by(post_id=self.id).count(),
            'like_count': Reaction.query.filter_by(
                target_id=self.id,
                target_type='post',
                reaction_type='like'
            ).count()
        }


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    reactions = db.relationship(
        'Reaction',
        primaryjoin="and_(Comment.id==foreign(Reaction.target_id), Reaction.target_type=='comment')",
        backref=db.backref('comment_parent', uselist=False),
        lazy=True,
        viewonly=True
    )


class Reaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reaction_type = db.Column(db.String(20), nullable=False)  # like, heart, etc.
    target_id = db.Column(db.Integer, nullable=False)  # polymorphic target
    target_type = db.Column(db.String(20), nullable=False)  # message, post, comment
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Used when target is a message
    message_id = db.Column(db.Integer, db.ForeignKey('message.id'), nullable=True)

    # Define a unique constraint to prevent duplicate reactions
    __table_args__ = (
        db.UniqueConstraint('user_id', 'target_id', 'target_type', 'reaction_type'),
    )


class Student(db.Model):
    id = db.Column(db.String(20), primary_key=True)
    is_registered = db.Column(db.Boolean, default=False)
    
    # Define relationship to User model
    user = db.relationship('User', backref='student', uselist=False)
    
    # Define relationship to VerificationCode model
    verification_codes = db.relationship('VerificationCode', backref='student', lazy=True,
                                        cascade='all, delete-orphan')


# New model for verification codes
class VerificationCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('student.id'), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'registration' or 'password_reset'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)