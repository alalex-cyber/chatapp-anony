from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional
from flask_wtf.file import FileAllowed, FileRequired


class LoginForm(FlaskForm):
    """Form for user login"""
    username = StringField('Student ID', validators=[
        DataRequired(message="Student ID is required")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required")
    ])
    remember = BooleanField('Remember Me')


class RegistrationForm(FlaskForm):
    """Form for user registration"""
    email = StringField('Student ID', validators=[
        DataRequired(message="Student ID is required")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password"),
        EqualTo('password', message="Passwords must match")
    ])
    selected_avatar = HiddenField('Avatar', default='blue')


class MessageForm(FlaskForm):
    """Form for sending a chat message"""
    content = TextAreaField('Message', validators=[
        DataRequired(message="Message cannot be empty"),
        Length(max=2000, message="Message too long (max 2000 characters)")
    ])
    channel_id = HiddenField('Channel ID', validators=[DataRequired()])


class PostForm(FlaskForm):
    """Form for creating a post in the social feed"""
    content = TextAreaField('Post Content', validators=[
        DataRequired(message="Post content cannot be empty"),
        Length(max=5000, message="Post too long (max 5000 characters)")
    ])
    image = FileField('Image', validators=[
        Optional(),
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')
    ])


class CommentForm(FlaskForm):
    """Form for adding a comment to a post"""
    content = TextAreaField('Comment', validators=[
        DataRequired(message="Comment cannot be empty"),
        Length(max=1000, message="Comment too long (max 1000 characters)")
    ])
    post_id = HiddenField('Post ID', validators=[DataRequired()])


class SettingsForm(FlaskForm):
    """Form for user settings"""
    avatar_color = SelectField('Avatar Color', choices=[
        ('blue', 'Blue'),
        ('pink', 'Pink'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('teal', 'Teal'),
        ('red', 'Red')
    ])

    avatar_face = SelectField('Avatar Face', choices=[
        ('blue', 'Blue'),
        ('pink', 'Pink'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('teal', 'Teal'),
        ('red', 'Red')
    ])

    theme = SelectField('Theme', choices=[
        ('dark', 'Dark Mode'),
        ('light', 'Light Mode'),
        ('system', 'System Default')
    ])

    font_size = SelectField('Font Size', choices=[
        ('12', '12px'),
        ('14', '14px'),
        ('16', '16px'),
        ('18', '18px'),
        ('20', '20px')
    ])

    chat_bubble_style = SelectField('Chat Bubble Style', choices=[
        ('modern', 'Modern'),
        ('classic', 'Classic'),
        ('compact', 'Compact'),
        ('minimal', 'Minimal')
    ])

    online_status = SelectField('Online Status', choices=[
        ('online', 'Online'),
        ('away', 'Away'),
        ('invisible', 'Invisible')
    ])

    read_receipts = BooleanField('Read Receipts')
    typing_indicators = BooleanField('Typing Indicators')
    sound_alerts = BooleanField('Sound Alerts')

    message_retention = SelectField('Message Retention', choices=[
        ('forever', 'Forever'),
        ('1month', '1 Month'),
        ('1week', '1 Week'),
        ('24hours', '24 Hours')
    ])


class ForgotPasswordForm(FlaskForm):
    """Form for requesting a password reset"""
    email = StringField('Student ID', validators=[
        DataRequired(message="Student ID is required")
    ])


class StudentImportForm(FlaskForm):
    """Form for admin to import student IDs"""
    student_ids = TextAreaField('Student IDs (one per line)', validators=[
        DataRequired(message="Please enter at least one student ID")
    ])