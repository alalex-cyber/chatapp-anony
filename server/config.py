import os
from datetime import timedelta


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_key_for_development')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)

    # WebSocket settings
    SOCKETIO_ASYNC_MODE = 'eventlet'
    SOCKETIO_CORS_ALLOWED_ORIGINS = '*'

    # Upload settings
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    # Avatar generation
    AVATAR_COLORS = ["blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"]
    AVATAR_FACES = ["blue", "pink", "yellow", "green", "purple", "orange", "teal", "red"]

    # Encryption settings (for end-to-end encrypted chat)
    ENCRYPTION_ENABLED = True
    ENCRYPTION_ALGORITHM = 'AES-256-GCM'  # Advanced encryption for messages

    # Student verification settings
    VERIFY_STUDENT_IDS = True

    @staticmethod
    def init_app(app):
        # Create upload directory if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL', 'sqlite:///campus_connect_dev.db')

    # For easier development, we might disable encryption
    ENCRYPTION_ENABLED = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///campus_connect_test.db')
    WTF_CSRF_ENABLED = False
    ENCRYPTION_ENABLED = False


class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SOCKETIO_CORS_ALLOWED_ORIGINS = [
        'https://yourdomain.com',
        'https://www.yourdomain.com'
    ]

    # Always enable encryption in production
    ENCRYPTION_ENABLED = True

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler('campus_connect.log', maxBytes=10000, backupCount=3)
        handler.setLevel(logging.WARNING)
        app.logger.addHandler(handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}