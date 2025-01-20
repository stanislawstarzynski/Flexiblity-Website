# Import necessary modules
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

# Initialize Flask application
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get('SECRET_KEY', 'your_default_secret_key')  # Use environment variable or default
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "instance", "database.db")}'

# Configure email settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'flexiblitywebsite.stanislaw@gmail.com'
app.config['MAIL_PASSWORD'] = 'owme dell fjvr ssgy'
app.config['MAIL_DEFAULT_SENDER'] = 'flexiblitywebsite.stanislaw@gmail.com'

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Allowed file extensions for photo uploads
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# ==========================
# DATABASE MODELS
# ==========================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

class TrainingTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    position_name = db.Column(db.String(100), nullable=False)
    template_level = db.Column(db.String(20), nullable=False)
    image_path = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)

# ==========================
# HELPER FUNCTIONS
# ==========================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================
# ROUTES
# ==========================
@app.route("/")
def about():
    return render_template("about.html")

@app.route("/positions")
def positions():
    return render_template("positions.html")

@app.route("/survey")
def survey():
    return render_template("survey.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    if request.method == 'POST':
        email = request.form['email']
        message = request.form['message']

        if not email or not message:
            flash('All fields are required.', 'error')
            return redirect(url_for('contact'))

        try:
            msg = Message('Contact Form Submission', recipients=[app.config['MAIL_USERNAME']])
            msg.body = f"From: {email}\n\nMessage:\n{message}"
            mail.send(msg)
            return redirect(url_for('contact', success=1))
        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while sending your message. Please try again.', 'error')
            return redirect(url_for('contact'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            username = request.form['username']
            email = request.form['email']
            password = request.form['password']

            if not username or not email or not password:
                flash('All fields are required.')
                return redirect(url_for('register'))

            if len(password) < 8:
                flash('Password must be at least 8 characters long.')
                return redirect(url_for('register'))

            if User.query.filter_by(email=email).first():
                flash('Email already registered.')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error During Registration: {e}")
            flash('An error occurred during registration. Please try again.')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!')
            return redirect(url_for('profile'))

        flash('Invalid email or password.')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        photo = request.files['photo']
        description = request.form['description']

        if photo and allowed_file(photo.filename):
            photo_path = f'static/uploads/{photo.filename}'
            photo.save(photo_path)

            new_progress = Progress(user_id=session['user_id'], photo=photo_path, description=description)
            db.session.add(new_progress)
            db.session.commit()
            flash('Progress photo added successfully!')
        else:
            flash('Invalid file type. Please upload a valid image.')

    progress_entries = Progress.query.filter_by(user_id=session['user_id']).all()
    return render_template('profile.html', username=session['username'], progress_entries=progress_entries)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/submit-survey', methods=['POST'])
def submit_survey():
    position = request.form.get('position')
    level = None

    if position == "Forward Fold":
        question = request.form.get('forward_fold_question')
        level = "Advanced" if question == "yes" else "Beginner"
    elif position == "Bridge":
        question = request.form.get('bridge_question')
        level = "Advanced" if question == "yes" else "Beginner"
    elif position == "Front Split":
        question_1 = request.form.get('front_split_question_1')
        if question_1 == "no":
            level = "Beginner"
        else:
            question_2 = request.form.get('front_split_question_2')
            level = "Advanced" if question_2 == "yes" else "Beginner"
    elif position == "Middle Split":
        question = request.form.get('middle_split_question')
        level = "Advanced" if question == "less_30cm" else "Beginner"
    elif position == "Pancake":
        question = request.form.get('pancake_question')
        level = "Advanced" if question == "yes" else "Beginner"

    template = TrainingTemplate.query.filter_by(position_name=position, template_level=level).first()

    return render_template('survey.html', template=template)

# ==========================
# RUN THE APP
# ==========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Manually seed data
        if TrainingTemplate.query.count() == 0:
            templates = [
                TrainingTemplate(
                    position_name='Forward Fold',
                    template_level='Beginner',
                    image_path='static/templates/forward_fold_beginner.png',
                    description='Forward Fold template for beginners.'
                ),
                TrainingTemplate(
                    position_name='Forward Fold',
                    template_level='Advanced',
                    image_path='static/templates/forward_fold_advanced.png',
                    description='Forward Fold template for advanced practitioners.'
                ),
                TrainingTemplate(
                    position_name='Bridge',
                    template_level='Beginner',
                    image_path='static/templates/bridge_beginner.png',
                    description='Bridge template for beginners.'
                ),
                TrainingTemplate(
                    position_name='Bridge',
                    template_level='Advanced',
                    image_path='static/templates/bridge_advanced.png',
                    description='Bridge template for advanced practitioners.'
                ),
                TrainingTemplate(
                    position_name='Front Split',
                    template_level='Beginner',
                    image_path='static/templates/front_split_beginner.png',
                    description='Front Split template for beginners.'
                ),
                TrainingTemplate(
                    position_name='Front Split',
                    template_level='Advanced',
                    image_path='static/templates/front_split_advanced.png',
                    description='Front Split template for advanced practitioners.'
                ),
                TrainingTemplate(
                    position_name='Middle Split',
                    template_level='Beginner',
                    image_path='static/templates/middle_split_beginner.png',
                    description='Middle Split template for beginners.'
                ),
                TrainingTemplate(
                    position_name='Middle Split',
                    template_level='Advanced',
                    image_path='static/templates/middle_split_advanced.png',
                    description='Middle Split template for advanced practitioners.'
                ),
                TrainingTemplate(
                    position_name='Pancake',
                    template_level='Beginner',
                    image_path='static/templates/pancake_beginner.png',
                    description='Pancake template for beginners.'
                ),
                TrainingTemplate(
                    position_name='Pancake',
                    template_level='Advanced',
                    image_path='static/templates/pancake_advanced.png',
                    description='Pancake template for advanced practitioners.'
                ),
            ]
            db.session.bulk_save_objects(templates)
            db.session.commit()
            print("Training templates have been seeded.")
    app.run(debug=True, host='0.0.0.0', port=5000)
