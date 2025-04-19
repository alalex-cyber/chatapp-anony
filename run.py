import os
import sys
import click
from flask.cli import with_appcontext

# Add server directory to path if needed
sys.path.append("./server")

from server.app import app, db, socketio
from server.models import User, Channel, Student

@app.cli.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database with tables and initial data."""
    db.create_all()

    # Create default channels if they don't exist
    if Channel.query.count() == 0:
        channels = [
            Channel(name="General", description="General discussion for everyone"),
            Channel(name="Academic", description="Academic discussions and questions"),
            Channel(name="Campus Events", description="Information about campus events"),
            Channel(name="Study Groups", description="Find and organize study groups")
        ]
        db.session.add_all(channels)
        db.session.commit()
        click.echo(f"Created {len(channels)} default channels")

    click.echo("Database initialized!")

@app.cli.command("import-students")
@click.argument("file_path", type=click.Path(exists=True))
@with_appcontext
def import_students_command(file_path):
    """Import student IDs from a text file."""
    with open(file_path, 'r') as f:
        student_ids = [line.strip() for line in f if line.strip()]

    count = 0
    for student_id in student_ids:
        if not Student.query.get(student_id):
            db.session.add(Student(id=student_id))
            count += 1

    db.session.commit()
    click.echo(f"Imported {count} student IDs")

@app.cli.command("add-test-students")
@with_appcontext
def add_test_students():
    """Add sample student IDs for testing."""
    sample_ids = [
        'S12345678', 'S23456789', 'S34567890', 'S45678901', 'S56789012',
        'S67890123', 'S78901234', 'S89012345', 'S90123456', 'S01234567'
    ]

    count = 0
    for student_id in sample_ids:
        if not Student.query.get(student_id):
            db.session.add(Student(id=student_id))
            count += 1

    db.session.commit()
    click.echo(f"Added {count} test student IDs")

@app.cli.command("list-students")
@with_appcontext
def list_students():
    """List all student IDs in the system."""
    students = Student.query.all()

    if not students:
        click.echo("No students found in the database.")
        return

    click.echo(f"Found {len(students)} students:")

    for student in students:
        status = "Registered" if student.is_registered else "Not registered"
        click.echo(f"ID: {student.id} - {status}")

@app.cli.command("reset-user")
@click.argument("student_id")
@with_appcontext
def reset_user(student_id):
    """Reset a user account to allow re-registration."""
    student = Student.query.get(student_id)

    if not student:
        click.echo(f"Student ID {student_id} not found.")
        return

    if not student.is_registered:
        click.echo(f"Student ID {student_id} is not registered.")
        return

    # Find and delete the user
    user = User.query.filter_by(student_id=student_id).first()
    if user:
        # Delete user data
        db.session.delete(user)

    # Mark student as not registered
    student.is_registered = False
    db.session.commit()

    click.echo(f"User for Student ID {student_id} has been reset.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create tables before running
    socketio.run(app, debug=True, port=80)