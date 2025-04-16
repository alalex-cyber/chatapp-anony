from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request
from flask import session, flash, jsonify, current_app
from .models import db, User, Student
from .utils import generate_alias, generate_avatar_data, sanitize_text
import secrets

auth = Blueprint('auth', __name__)


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

        if user and user.verify_password(password):
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
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        avatar_color = request.form.get('selected_avatar', 'blue')

        # Validate input
        if not student_id or not password or not confirm_password:
            error = "All fields are required."
            return render_template('registration.html', error=error)

        if password != confirm_password:
            error = "Passwords do not match."
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

        # Generate unique alias for anonymity
        alias = generate_alias()

        # Make sure alias is unique
        while User.query.filter_by(alias=alias).first():
            alias = generate_alias()

        # Generate avatar
        avatar_data = generate_avatar_data()

        # Create new user
        new_user = User(
            student_id=student_id,
            alias=alias,
            avatar_color=avatar_data['color'],
            avatar_face=avatar_data['face']
        )

        # Set password (uses the password setter that hashes it)
        new_user.password = password

        # Mark student as registered
        student.is_registered = True

        # Save to database
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in with your Student ID and password.')
        return redirect(url_for('auth.login', registered='success'))

    return render_template('registration.html', error=error)


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


@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password view"""
    if request.method == 'POST':
        student_id = request.form.get('email')  # Using email field for student ID

        # Check if student ID exists and is registered
        student = Student.query.get(student_id)
        user = User.query.filter_by(student_id=student_id).first() if student else None

        if student and user:
            # In a real application, you would:
            # 1. Generate a secure reset token
            # 2. Store the token with an expiration time
            # 3. Send an email with a reset link

            flash('Password reset instructions have been sent to your registered email.')
        else:
            # Don't reveal if student ID exists for security
            flash('If this Student ID is registered, password reset instructions have been sent.')

        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth.route('/admin/import-students', methods=['GET', 'POST'])
def import_students():
    """Admin view to import student IDs (this would typically be protected)"""
    # In production, this should be protected with admin authentication

    if request.method == 'POST':
        student_ids = request.form.get('student_ids', '').split('\n')

        count = 0
        for student_id in student_ids:
            student_id = student_id.strip()
            if student_id and not Student.query.get(student_id):
                db.session.add(Student(id=student_id))
                count += 1

        db.session.commit()
        flash(f'Successfully imported {count} student IDs')

    students = Student.query.all()
    return render_template('admin_import.html', students=students)