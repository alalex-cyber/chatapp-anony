import secrets
import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request
from flask import session, flash, jsonify, current_app
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash

from server.models import db, User, Student, VerificationCode
from server.utils import sanitize_text, generate_verification_code

auth = Blueprint('auth', __name__)

# Initialize mail extension
mail = Mail()

def require_login(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api'):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login view"""
    if 'user_id' in session:
        return redirect(url_for('routes.chat'))

    error = None
    registered = request.args.get('registered')

    if request.method == 'POST':
        student_id = request.form.get('username')
        password = request.form.get('password')

        # Validate input
        if not student_id or not password:
            error = "Student ID and password are required."
            return render_template('login.html', error=error)

        # Check if student ID exists and is registered
        student = Student.query.get(student_id)

        if not student:
            error = "Invalid student ID. Please check and try again."
            return render_template('login.html', error=error)

        if not student.is_registered:
            error = "This Student ID is not registered. Please register first."
            return render_template('login.html', error=error)

        # Find user
        user = User.query.filter_by(student_id=student_id).first()

        if user and check_password_hash(user.password_hash, password):
            # Valid login
            session['user_id'] = user.id
            session['alias'] = user.alias
            session.permanent = True

            # Update online status
            user.is_online = True
            db.session.commit()

            # Redirect to next page or default
            next_page = request.args.get('next', url_for('routes.chat'))
            return redirect(next_page)
        else:
            error = "Invalid password. Please try again."

    return render_template('login.html', error=error, registered=registered)


@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration view"""
    error = None

    if request.method == 'POST':
        student_id = request.form.get('email')  # Using email field for student ID
        email = request.form.get('email_address', '').strip()  # New field for actual email
        
        # Validate input
        if not student_id:
            error = "Student ID is required."
            return render_template('registration.html', error=error)
        
        if not email:
            error = "Email address is required."
            return render_template('registration.html', error=error)

        # Check if student ID exists in the system
        student = Student.query.get(student_id)
        if not student:
            error = "This Student ID is not recognized. Please contact support."
            return render_template('registration.html', error=error)

        # Check if student is already registered
        if student.is_registered:
            error = "This Student ID is already registered."
            return render_template('registration.html', error=error)
            
        # Check if email is already in use
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = "This email is already in use."
            return render_template('registration.html', error=error)

        # Generate verification code
        verification_code = generate_verification_code()
        
        # Store the verification code
        expiration_time = datetime.utcnow() + timedelta(minutes=30)
        new_code = VerificationCode(
            student_id=student_id,
            email=email,
            code=verification_code,
            expires_at=expiration_time,
            type='registration'
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        # Send verification email
        send_verification_email(email, verification_code)
        
        # Store data in session for the verification step
        session['registration_student_id'] = student_id
        session['registration_email'] = email
        
        # Redirect to verification page
        return redirect(url_for('auth.verify_registration'))

    return render_template('registration.html', error=error)


@auth.route('/verify-registration', methods=['GET', 'POST'])
def verify_registration():
    """Verify email for registration"""
    error = None
    
    # Check if we have the required session data
    if 'registration_student_id' not in session or 'registration_email' not in session:
        flash('Registration session expired. Please start again.')
        return redirect(url_for('auth.register'))
    
    student_id = session['registration_student_id']
    email = session['registration_email']
    
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        avatar_color = request.form.get('selected_avatar', 'blue')
        
        # Validate input
        if not verification_code or not password or not confirm_password:
            error = "All fields are required."
            return render_template('verify_registration.html', error=error, email=email)
            
        if password != confirm_password:
            error = "Passwords do not match."
            return render_template('verify_registration.html', error=error, email=email)
        
        # Verify the code
        verification = VerificationCode.query.filter_by(
            student_id=student_id, 
            email=email,
            code=verification_code,
            type='registration'
        ).first()
        
        if not verification or verification.expires_at < datetime.utcnow():
            error = "Invalid or expired verification code."
            return render_template('verify_registration.html', error=error, email=email)
        
        # Code is valid, create the user
        from .utils import generate_alias, generate_avatar_data
        
        alias = generate_alias()
        while User.query.filter_by(alias=alias).first():
            alias = generate_alias()
            
        avatar_data = generate_avatar_data()
        
        new_user = User(
            student_id=student_id,
            email=email,
            alias=alias,
            avatar_color=avatar_data['color'],
            avatar_face=avatar_data['face'],
            password_hash=generate_password_hash(password)
        )
        
        # Mark student as registered
        student = Student.query.get(student_id)
        student.is_registered = True
        
        # Save to database
        db.session.add(new_user)
        db.session.delete(verification)  # Remove used verification code
        db.session.commit()
        
        # Clean up session
        session.pop('registration_student_id', None)
        session.pop('registration_email', None)
        
        flash('Registration successful! You can now log in with your Student ID and password.')
        return redirect(url_for('auth.login', registered='success'))
    
    return render_template('verify_registration.html', email=email)


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password view"""
    if request.method == 'POST':
        student_id = request.form.get('email')  # Using email field for student ID

        # Check if student ID exists and is registered
        student = Student.query.get(student_id)
        user = User.query.filter_by(student_id=student_id).first() if student else None

        if student and user:
            # Generate verification code
            verification_code = generate_verification_code()
            
            # Store the verification code
            expiration_time = datetime.utcnow() + timedelta(minutes=30)
            new_code = VerificationCode(
                student_id=student_id,
                email=user.email,
                code=verification_code,
                expires_at=expiration_time,
                type='password_reset'
            )
            
            db.session.add(new_code)
            db.session.commit()
            
            # Send password reset email
            send_password_reset_email(user.email, verification_code)
            
            # Store student_id in session for the reset step
            session['reset_student_id'] = student_id
            
            # Redirect to reset password page
            return redirect(url_for('auth.reset_password'))
        else:
            # Don't reveal if student ID exists for security
            flash('If this Student ID is registered, password reset instructions have been sent.')

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password with verification code"""
    error = None
    
    # Check if we have the required session data
    if 'reset_student_id' not in session:
        flash('Password reset session expired. Please start again.')
        return redirect(url_for('auth.forgot_password'))
    
    student_id = session['reset_student_id']
    
    if request.method == 'POST':
        verification_code = request.form.get('verification_code')
        new_password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not verification_code or not new_password or not confirm_password:
            error = "All fields are required."
            return render_template('reset_password.html', error=error)
            
        if new_password != confirm_password:
            error = "Passwords do not match."
            return render_template('reset_password.html', error=error)
        
        # Get user
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            error = "User not found."
            return render_template('reset_password.html', error=error)
        
        # Verify the code
        verification = VerificationCode.query.filter_by(
            student_id=student_id, 
            email=user.email,
            code=verification_code,
            type='password_reset'
        ).first()
        
        if not verification or verification.expires_at < datetime.utcnow():
            error = "Invalid or expired verification code."
            return render_template('reset_password.html', error=error)
        
        # Code is valid, update password
        user.password_hash = generate_password_hash(new_password)
        
        # Save changes and remove used code
        db.session.delete(verification)
        db.session.commit()
        
        # Clean up session
        session.pop('reset_student_id', None)
        
        flash('Your password has been reset successfully. You can now log in with your new password.')
        return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html')


@auth.route('/logout')
def logout():
    """Log out the current user"""
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            user.is_online = False
            db.session.commit()

    # Clear session
    session.pop('user_id', None)
    session.pop('alias', None)

    return redirect(url_for('auth.login'))


@auth.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification code"""
    if 'registration_student_id' in session and 'registration_email' in session:
        student_id = session['registration_student_id']
        email = session['registration_email']
        
        # Delete any existing codes
        VerificationCode.query.filter_by(
            student_id=student_id,
            email=email,
            type='registration'
        ).delete()
        
        # Generate new verification code
        verification_code = generate_verification_code()
        
        # Store the verification code
        expiration_time = datetime.utcnow() + timedelta(minutes=30)
        new_code = VerificationCode(
            student_id=student_id,
            email=email,
            code=verification_code,
            expires_at=expiration_time,
            type='registration'
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        # Send verification email
        send_verification_email(email, verification_code)
        
        flash("Verification code has been resent to your email.")
    else:
        flash("Session expired. Please start the registration process again.")
        return redirect(url_for('auth.register'))
        
    return redirect(url_for('auth.verify_registration'))


@auth.route('/resend-reset-code', methods=['POST'])
def resend_reset_code():
    """Resend password reset code"""
    if 'reset_student_id' in session:
        student_id = session['reset_student_id']
        
        # Get user
        user = User.query.filter_by(student_id=student_id).first()
        if not user:
            flash("User not found.")
            return redirect(url_for('auth.forgot_password'))
        
        # Delete any existing codes
        VerificationCode.query.filter_by(
            student_id=student_id,
            email=user.email,
            type='password_reset'
        ).delete()
        
        # Generate new verification code
        verification_code = generate_verification_code()
        
        # Store the verification code
        expiration_time = datetime.utcnow() + timedelta(minutes=30)
        new_code = VerificationCode(
            student_id=student_id,
            email=user.email,
            code=verification_code,
            expires_at=expiration_time,
            type='password_reset'
        )
        
        db.session.add(new_code)
        db.session.commit()
        
        # Send password reset email
        send_password_reset_email(user.email, verification_code)
        
        flash("Reset code has been resent to your email.")
    else:
        flash("Session expired. Please start the password reset process again.")
        return redirect(url_for('auth.forgot_password'))
        
    return redirect(url_for('auth.reset_password'))


# Email sending functions
def send_verification_email(email, code):
    """Send verification email with code"""
    try:
        subject = "Campus Connect - Email Verification"
        body = f"""
        <p>Hello,</p>
        <p>Your verification code for Campus Connect is: <strong>{code}</strong></p>
        <p>This code will expire in 30 minutes.</p>
        <p>If you did not request this code, please ignore this email.</p>
        <p>Regards,<br>Campus Connect Team</p>
        """
        
        msg = Message(
            subject=subject,
            recipients=[email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@campusconnect.com')
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send verification email: {str(e)}")
        return False


def send_password_reset_email(email, code):
    """Send password reset email with code"""
    try:
        subject = "Campus Connect - Password Reset"
        body = f"""
        <p>Hello,</p>
        <p>You requested to reset your password for Campus Connect.</p>
        <p>Your password reset code is: <strong>{code}</strong></p>
        <p>This code will expire in 30 minutes.</p>
        <p>If you did not request this reset, please ignore this email.</p>
        <p>Regards,<br>Campus Connect Team</p>
        """
        
        msg = Message(
            subject=subject,
            recipients=[email],
            html=body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'noreply@campusconnect.com')
        )
        
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send password reset email: {str(e)}")
        return False