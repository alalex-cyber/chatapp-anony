from flask import Flask, render_template, redirect, url_for, request, flash, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure random key in production

# Mock user data for demo purposes
mock_users = {
    'student1': {
        'username': 'student1',
        'password': 'password123',
        'email': 'student1@university.edu',
        'department': 'Computer Science',
        'year': '3',
        'avatar': 'blue'
    }
}

@app.route('/')
def index():
    # Check if user is logged in, otherwise redirect to login
    if 'username' not in session:
        return redirect(url_for('login'))
    # Redirect to the main chat page if logged in
    return redirect(url_for('chat'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    # Check if user is already logged in
    if 'username' in session:
        return redirect(url_for('chat'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Simple authentication (replace with proper authentication in production)
        if username in mock_users and mock_users[username]['password'] == password:
            session['username'] = username
            return redirect(url_for('chat'))
        else:
            error = 'Invalid credentials. Please try again.'

    # Flash message if redirected from registration
    registered = request.args.get('registered')
    if registered == 'success':
        flash('Registration successful! Please log in.')

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        department = request.form['department']
        year = request.form['year']
        avatar = request.form['selected_avatar']

        # Check if username already exists
        if username in mock_users:
            return render_template('registration.html', error='Username already exists')

        # Add new user (in a real app, you would hash the password)
        mock_users[username] = {
            'username': username,
            'password': password,
            'email': email,
            'department': department,
            'year': year,
            'avatar': avatar
        }

        # Redirect to login page with success message
        return redirect(url_for('login', registered='success'))

    return render_template('registration.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/chat')
def chat():
    if 'username' in session:
        # Get username from session
        username = session['username']
        # Get user data
        user = mock_users.get(username)
        # Pass user to template
        return render_template('chat.html', user=user)
    return redirect(url_for('login'))


@app.route('/social-feed')
def social_feed():
    # If you're using session-based authentication
    if 'username' in session:
        username = session['username']
        user = mock_users.get(username)
        return render_template('social_feed.html', user=user)
    # For testing/temporary use, you can use a mock user
    else:
        mock_user = {"id": 1, "alias": "Anonymous"}
        return render_template('social_feed.html', user=mock_user)


@app.route('/settings')
def settings():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))
    # Serve the settings page
    return render_template('settings.html')


@app.route('/profile')
def profile():
    # Check if user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))

    # Get username from session
    username = session['username']
    user_data = mock_users.get(username)

    # Serve the user profile page
    return render_template('user_profile.html', user=user_data)


@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        # In a real application, you would:
        # 1. Check if email exists in your database
        # 2. Generate a secure reset token
        # 3. Store the token with an expiration time
        # 4. Send an email with a reset link

        # For demo purposes, we'll just flash a message
        flash('Password reset instructions sent to your email.')
        return redirect(url_for('login'))

    return render_template('forgot_password.html')
if __name__ == '__main__':
    app.run(debug=True)