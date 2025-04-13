from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

@app.route('/')
def index():
    # Redirect to the main chat page
    return redirect(url_for('chat'))

@app.route('/chat')
def chat():
    # Serve the university chat page
    return render_template('chat.html')

@app.route('/social-feed')
def social_feed():
    # Serve the social feed page (renamed from events)
    return render_template('social_feed.html')

@app.route('/settings')
def settings():
    # Serve the settings page
    return render_template('settings.html')  # or 'anonymous_settings.html' depending on what you name it

if __name__ == '__main__':
    app.run(debug=True)