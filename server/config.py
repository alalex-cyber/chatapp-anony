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
    
    # Email settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'yes', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'yes', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@campusconnect.com')
    
    # Security settings for password reset
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT', 'precious-salt-for-dev')

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
    
    # For development, use a file-based email backend (logs emails instead of sending)
    MAIL_BACKEND = 'development'
    
    # Or use a real SMTP server with these settings for development:
    # MAIL_SERVER = 'localhost'
    # MAIL_PORT = 1025  # python -m smtpd -n -c DebuggingServer localhost:1025


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///campus_connect_test.db')
    WTF_CSRF_ENABLED = False
    ENCRYPTION_ENABLED = False
    
    # Use memory backend for email testing
    MAIL_BACKEND = 'memory'


class ProductionConfig(Config):
    """Production configuration."""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SOCKETIO_CORS_ALLOWED_ORIGINS = [
        'https://yourdomain.com',
        'https://www.yourdomain.com'
    ]

    # Always enable encryption in production
    ENCRYPTION_ENABLED = True
    
    # Ensure all email settings are provided in production
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Production-specific logging
        import logging
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler('campus_connect.log', maxBytes=10000, backupCount=3)
        handler.setLevel(logging.WARNING)
        app.logger.addHandler(handler)
        
        # Verify email configuration
        assert app.config['MAIL_USERNAME'] is not None, "MAIL_USERNAME must be configured"
        assert app.config['MAIL_PASSWORD'] is not None, "MAIL_PASSWORD must be configured"


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}