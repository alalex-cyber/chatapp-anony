from flask import Flask, render_template, redirect, url_for, request, session, flash
from flask_migrate import Migrate
from flask_cors import CORS
from flask_mail import Mail
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import dotenv

db = SQLAlchemy()
socketio = SocketIO()
mail = Mail()

# Create application factory function
def create_app(config_name='default'):
    # Initialize Flask app
    app = Flask(__name__)
    
    # Configure app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_key_for_development')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///campus_connect.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Load configuration
    if os.environ.get('FLASK_ENV') == 'production':
        from server.config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from .config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Set up logging
    setup_logging(app)
    
    # Initialize extensions
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", logger=True, engineio_logger=True)
    mail.init_app(app)  # Initialize Flask-Mail
    app.logger.info("Extensions initialized")
    
    # Initialize other extensions
    migrate = Migrate(app, db)
    CORS(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        initialize_database(app)
    
    return app

def setup_logging(app):
    """Configure logging for the application"""
    import logging
    if not app.debug:
        # Set up file handler for production
        from logging.handlers import RotatingFileHandler
        import logging
        
        if not os.path.exists('logs'):
            os.mkdir('logs')
            
        file_handler = RotatingFileHandler('logs/campus_connect.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Campus Connect startup')
    else:
        # Set up console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(console_handler)
        
        # Create loggers for main components
        loggers = ['socketio', 'api', 'auth', 'mail']
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG if app.debug else logging.INFO)
            logger.addHandler(console_handler)

def register_blueprints(app):
    """Register Flask blueprints"""
    # Import and register blueprints
    from server.auth import auth
    app.register_blueprint(auth)
    
    from server.routes import routes
    app.register_blueprint(routes)
    
    # Register the channel API blueprint
    from server.channel_api import channel_api
    app.register_blueprint(channel_api)
    
    # Import other API routes
    from server.api import api
    app.register_blueprint(api)
    
    # Register basic routes
    register_basic_routes(app)

def register_basic_routes(app):
    """Register basic application routes"""
    @app.route('/')
    def index():
        return redirect(url_for('routes.chat'))

def register_error_handlers(app):
    """Register error handlers"""
    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith('/api/'):
            return {'error': 'Resource not found'}, 404
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()  # Roll back db session in case of error
        app.logger.error(f'Server Error: {error}')
        if request.path.startswith('/api/'):
            return {'error': 'Internal server error'}, 500
        return render_template('errors/500.html'), 500

def initialize_database(app):
    """Initialize database with tables and default data"""
    from server.models import User, Channel, Message, Post, Comment, Reaction, Student, VerificationCode, DirectMessage
    
    # Create tables
    db.create_all()
    
    # Create default channels if they don't exist
    initialize_channels(app)
    
    # Initialize test students if in development
    initialize_test_students(app)

def initialize_channels(app):
    """Initialize default channels"""
    from server.models import Channel
    
    if Channel.query.count() == 0:
        app.logger.info("Creating default channels")
        
        channels = [
            Channel(name="General", description="General discussion for everyone"),
            Channel(name="Social Feed", description="Share moments with your campus community"),
            Channel(name="Academic", description="Academic discussions and questions"),
            Channel(name="Events", description="Campus events and activities")
        ]
        
        db.session.add_all(channels)
        db.session.commit()
        
        app.logger.info(f"Created {len(channels)} default channels")

def initialize_test_students(app):
    """Initialize test student IDs for development"""
    from server.models import Student
    
    # Only add test students if we don't have any yet
    if Student.query.count() == 0:
        app.logger.info("Adding test student IDs")
        
        test_students = [
            "S1234567",
            "S2345678",
            "S3456789",
            "S4567890",
            "S5678901",
            "S6789012"
        ]
        
        for student_id in test_students:
            student = Student(id=student_id)
            db.session.add(student)
        
        db.session.commit()
        app.logger.info(f"Added {len(test_students)} test student IDs")

# Create the Flask application
app = create_app()

# Import socket event handlers
import server.sockets

# Run app
if __name__ == '__main__':
    socketio.run(app, debug=app.debug)