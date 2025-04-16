import os
import secrets
import random
import re
import base64
import json
from datetime import datetime
from flask import current_app
from werkzeug.utils import secure_filename
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


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
        "Thoughtful", "Wise", "Gentle", "Clever", "Kind", "Brave", "Bold",
        "Swift", "Nimble", "Agile", "Calm", "Serene", "Vibrant", "Eclectic",
        "Dynamic", "Earnest", "Jovial", "Quaint", "Zealous", "Noble", "Astute",
        "Diligent", "Tenacious", "Meticulous", "Precise", "Vigilant", "Prudent"
    ]

    nouns = [
        "Student", "Scholar", "Thinker", "Mind", "Intellect", "Learner",
        "Academic", "Researcher", "Reader", "Theorist", "Philosopher", "Sage",
        "Champion", "Pioneer", "Explorer", "Voyager", "Wanderer", "Observer",
        "Sentinel", "Guardian", "Keeper", "Visionary", "Seeker", "Enthusiast"
    ]

    # For uniqueness, add a random number
    random_number = random.randint(10, 999)
    return f"{random.choice(adjectives)} {random.choice(nouns)}{random_number}"


def generate_avatar_data():
    """Generate random avatar settings"""
    colors = current_app.config.get('AVATAR_COLORS', [
        "blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"
    ])

    faces = current_app.config.get('AVATAR_FACES', [
        "blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"
    ])

    return {
        "color": random.choice(colors),
        "face": random.choice(faces)
    }


# Content sanitization
def sanitize_text(text):
    """Basic sanitization for user input"""
    if not text:
        return ""

    # Remove script tags and other potentially dangerous HTML
    text = re.sub(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', '', text)
    text = re.sub(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', '', text)

    # Handle basic HTML encoding
    text = text.replace('<', '&lt;').replace('>', '&gt;')

    return text


# Encryption utilities for end-to-end encrypted chat
def generate_encryption_key():
    """Generate a secure encryption key"""
    return secrets.token_bytes(32)  # 256 bits key for AES-256-GCM


def derive_key(password, salt=None):
    """Derive an encryption key from a password"""
    if salt is None:
        salt = secrets.token_bytes(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    key = kdf.derive(password.encode())
    return key, salt


def encrypt_message(message, key=None):
    """Encrypt a message using AES-256-GCM"""
    if not current_app.config.get('ENCRYPTION_ENABLED', False):
        return message, None, None

    if key is None:
        key = generate_encryption_key()

    # Generate a random nonce
    nonce = secrets.token_bytes(12)

    # Encrypt the message
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, message.encode(), None)

    # Encode binary data as base64 for storage
    return (
        base64.b64encode(ciphertext).decode(),
        base64.b64encode(key).decode(),
        base64.b64encode(nonce).decode()
    )


def decrypt_message(encrypted_message, key, nonce):
    """Decrypt a message using AES-256-GCM"""
    if not current_app.config.get('ENCRYPTION_ENABLED', False):
        return encrypted_message

    # Decode from base64
    ciphertext = base64.b64decode(encrypted_message)
    key_bytes = base64.b64decode(key)
    nonce_bytes = base64.b64decode(nonce)

    # Decrypt the message
    aesgcm = AESGCM(key_bytes)
    plaintext = aesgcm.decrypt(nonce_bytes, ciphertext, None)

    return plaintext.decode()


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