
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
import sqlite3
import os
import secrets
from datetime import timedelta
from werkzeug.utils import secure_filename
import logging

# Create the Flask application
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key
app.config['SESSION_PERMANENT'] = False  # Make sessions temporary
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=5)  # Set session timeout to 5 hours

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up the upload folder
upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

app.config['UPLOAD_FOLDER'] = upload_folder
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit for file uploads

# Get the path to our SQLite database
db_path = os.path.join(os.path.dirname(__file__), 'users.db')

# Function to count words in a file
def count_words(filename):
    with open(filename, 'r') as file:
        content = file.read()
        words = content.split()
        return len(words)

# Route for the home page
@app.route('/')
def index():
    logger.debug(f"Session contents: {session}")
    return render_template('index.html')

# Route for user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    logger.debug(f"Session contents: {session}")
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            password = request.form['password']
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']

            # Connect to the database and insert the new user
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("INSERT INTO users (username, password, firstname, lastname, email) VALUES (?, ?, ?, ?, ?)",
                      (username, password, firstname, lastname, email))
            conn.commit()
            conn.close()

            # Set the session and clear any existing flash messages
            session['username'] = username
            session['_flashes'] = []  # Clear any existing flash messages
            logger.info(f"User registered: {username}")
            flash('Registration successful!', 'success')
            return redirect(url_for('profile'))
        except sqlite3.Error as e:
            logger.error(f"Database error in register: {e}")
            flash(f"Database error occurred: {e}", 'error')
        except Exception as e:
            logger.error(f"Error in register: {e}")
            flash(f"An error occurred: {e}", 'error')
    return render_template('register.html')

# Route for user login
@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.debug(f"Session contents: {session}")
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form['username']
            password = request.form['password']

            # Check if the user exists and the password is correct
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = c.fetchone()
            conn.close()

            if user:
                # If the user exists, log them in
                session['username'] = username
                session['_flashes'] = []  # Clear any existing flash messages
                logger.info(f"User logged in: {username}")
                flash('Login successful!', 'success')
                return redirect(url_for('profile'))
            else:
                flash('Invalid username or password', 'error')
        except sqlite3.Error as e:
            logger.error(f"Database error in login: {e}")
            flash(f"Database error occurred: {e}", 'error')
        except Exception as e:
            logger.error(f"Error in login: {e}")
            flash(f"An error occurred: {e}", 'error')
    return render_template('login.html')

# Route for the user profile
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    logger.debug(f"Session contents: {session}")
    if 'username' not in session:
        logger.warning("Username not in session")
        flash('Please log in to access your profile', 'error')
        return redirect(url_for('login'))
    
    try:
        # Fetch the user's details from the database
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT username, firstname, lastname, email, filename, word_count FROM users WHERE username=?", (session['username'],))
        user = c.fetchone()

        if request.method == 'POST' and 'file' in request.files:
            file = request.files['file']
            if file and file.filename == 'Limerick-1.txt':
                # Save the uploaded file and count its words
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                word_count = count_words(filepath)
                
                # Update the user's information in the database
                c.execute("UPDATE users SET filename=?, word_count=? WHERE username=?", 
                          (filename, word_count, session['username']))
                conn.commit()
                flash('File uploaded successfully!', 'success')
                c.execute("SELECT username, firstname, lastname, email, filename, word_count FROM users WHERE username=?", (session['username'],))
                user = c.fetchone()  # Fetch updated user info
            else:
                flash('Invalid file. Please upload Limerick-1.txt', 'error')

        conn.close()

        if user:
            # If the user exists, show their profile
            return render_template('profile.html', user=user)
        else:
            flash('User not found', 'error')
            return redirect(url_for('login'))
    except sqlite3.Error as e:
        logger.error(f"Database error in profile: {e}")
        flash(f"Database error occurred: {e}", 'error')
    except Exception as e:
        logger.error(f"Error in profile: {e}")
        flash(f"An error occurred: {e}", 'error')
    return redirect(url_for('login'))

# Route for downloading uploaded files
@app.route('/download/<filename>')
def download_file(filename):
    if 'username' not in session:
        flash('Please log in to download files', 'error')
        return redirect(url_for('login'))
    try:
        return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)
    except Exception as e:
        logger.error(f"Error in download_file: {e}")
        flash(f"An error occurred while downloading the file: {e}", 'error')
        return redirect(url_for('profile'))

# Route for user logout
@app.route('/logout')
def logout():
    logger.debug(f"Session contents: {session}")
    session.clear()
    session['_flashes'] = []  # Clear any existing flash messages
    logger.info("User logged out")
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

