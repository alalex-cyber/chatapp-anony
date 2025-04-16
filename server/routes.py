from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session
from .models import db, User, Channel, Message, Post, Comment, Reaction
from .auth import require_login
from datetime import datetime, timedelta

routes = Blueprint('routes', __name__)


@routes.route('/')
def index():
    """Redirect to main chat page or login if not authenticated"""
    if 'user_id' in session:
        return redirect(url_for('routes.chat'))
    return redirect(url_for('auth.login'))


@routes.route('/chat')
@require_login
def chat():
    """Chat interface - the main communication tool"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        # Handle invalid user ID in session
        session.clear()
        return redirect(url_for('auth.login'))

    # Get all available channels
    channels = Channel.query.all()

    # Get recent activity for each channel
    channel_activity = {}
    for channel in channels:
        last_message = Message.query.filter_by(channel_id=channel.id).order_by(Message.timestamp.desc()).first()
        channel_activity[channel.id] = last_message.timestamp if last_message else None

    # Get online users (excluding current user)
    online_users = User.query.filter(User.is_online == True, User.id != user_id).all()

    return render_template('chat.html',
                           user=user,
                           channels=channels,
                           channel_activity=channel_activity,
                           online_users=online_users)


@routes.route('/social-feed')
@require_login
def social_feed():
    """Social feed interface for posts and interactions"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # Get recent posts (pagination could be added)
    posts = Post.query.order_by(Post.created_at.desc()).limit(20).all()

    # For each post, get author and like count
    post_data = []
    for post in posts:
        author = User.query.get(post.user_id)
        like_count = Reaction.query.filter_by(
            target_id=post.id,
            target_type='post',
            reaction_type='like'
        ).count()

        comment_count = Comment.query.filter_by(post_id=post.id).count()

        post_data.append({
            'post': post,
            'author': author,
            'like_count': like_count,
            'comment_count': comment_count
        })

    return render_template('social_feed.html',
                           user=user,
                           posts=post_data)


@routes.route('/settings')
@require_login
def settings():
    """User settings interface"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    return render_template('settings.html', user=user)


@routes.route('/profile')
@require_login
def profile():
    """User profile view"""
    user_id = session['user_id']
    user = User.query.get(user_id)

    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    # Get user stats
    post_count = Post.query.filter_by(user_id=user_id).count()
    comment_count = Comment.query.filter_by(user_id=user_id).count()
    message_count = Message.query.filter_by(user_id=user_id).count()

    # Calculate account age in days
    account_age = (datetime.utcnow() - user.created_at).days

    # Get recent activity
    recent_messages = Message.query.filter_by(user_id=user_id).order_by(Message.timestamp.desc()).limit(5).all()
    recent_posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).limit(5).all()

    return render_template('user_profile.html',
                           user=user,
                           post_count=post_count,
                           comment_count=comment_count,
                           message_count=message_count,
                           account_age=account_age,
                           recent_messages=recent_messages,
                           recent_posts=recent_posts)


# Additional route for viewing other users' profiles (limited info for anonymity)
@routes.route('/user/<int:user_id>')
@require_login
def view_user(user_id):
    """View another user's profile with limited information"""
    current_user_id = session['user_id']

    # Don't allow viewing your own profile via this route
    if user_id == current_user_id:
        return redirect(url_for('routes.profile'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('routes.chat'))

    # Get limited stats for anonymity
    post_count = Post.query.filter_by(user_id=user_id).count()
    days_active = (datetime.utcnow() - user.created_at).days

    # Check if user is online
    is_online = user.is_online
    last_seen = user.last_seen

    return render_template('view_user.html',
                           user=user,
                           post_count=post_count,
                           days_active=days_active,
                           is_online=is_online,
                           last_seen=last_seen)