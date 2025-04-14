import os
import secrets
import random
import re
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename


# File handling utilities
def allowed_file(filename, allowed_extensions=None):
    """Check if the file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config['ALLOWED_EXTENSIONS']
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in allowed_extensions


def save_file(file, folder=None):
    """Save uploaded file with secure filename"""
    if folder is None:
        folder = current_app.config['UPLOAD_FOLDER']

    filename = secure_filename(f"{secrets.token_hex(8)}_{file.filename}")
    file_path = os.path.join(folder, filename)
    file.save(file_path)

    # Return the relative path for storage in the database
    return os.path.join('/static/uploads', filename)


# User and avatar utilities
def generate_alias():
    """Generate a random anonymous alias"""
    adjectives = [
        "Anonymous", "Mysterious", "Hidden", "Secret", "Unknown", "Unnamed",
        "Silent", "Quiet", "Peaceful", "Creative", "Curious", "Brilliant",
        "Thoughtful", "Wise", "Gentle", "Clever", "Kind", "Brave", "Bold"
    ]
    return f"{random.choice(adjectives)}"


def generate_avatar():
    """Generate random avatar settings"""
    colors = current_app.config['AVATAR_COLORS']
    faces = current_app.config['AVATAR_FACES']
    return {
        "color": random.choice(colors),
        "face": random.choice(faces)
    }


# Content sanitization
def sanitize_text(text):
    """Basic sanitization for user input"""
    # Remove script tags and other potentially dangerous HTML
    text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text)
    text = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', text)
    return text


# Datetime formatting
def format_timestamp(timestamp, format_string="%b %d, %Y at %H:%M"):
    """Format a datetime object or ISO string to a human-readable string"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return timestamp.strftime(format_string)


def get_relative_time(timestamp):
    """Get a human-readable relative time (e.g., '2 hours ago')"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

    now = datetime.utcnow()
    diff = now - timestamp

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f"{days} day{'s' if days > 1 else ''} ago"
    else:
        return timestamp.strftime("%b %d, %Y")