import os
import sqlite3
import hashlib
from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from extensions import db
from models import User, Movie
from services import tmdb               

load_dotenv()

app = Flask(__name__)

# --- CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('FLASK_SECRET_KEY')
app.config['TMDB_API_KEY'] = os.getenv('TMDB_API_KEY')
app.config['UPLOAD_FOLDER'] = 'flask_app/uploads'

db.init_app(app)

# --- CONTEXT PROCESSOR ---
@app.context_processor
def inject_genres():
    try:
        all_genres = tmdb.get_genres()
        return dict(all_genres=all_genres)
    except:
        return dict(all_genres=[])

# --- DB HELPERS ---
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        username TEXT UNIQUE NOT NULL, 
        password TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS global_comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        has_gore INTEGER DEFAULT 0,
        has_extreme INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        movie_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        review_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

# --- MAIN ROUTES ---

@app.route('/')
def home():
    offset = request.args.get('offset', 0, type=int)
    hide_gore = request.args.get('hide_gore') == '1'
    hide_extreme = request.args.get('hide_extreme') == '1'
    target_rating = request.args.get('rating', 'all')

    all_movies = tmdb.get_popular_movies()
    filtered_movies = []

    for movie in all_movies:
        movie_genres = movie.get('genre_ids', []) if isinstance(movie, dict) else getattr(movie, 'genre_ids', [])
        is_adult = movie.get('adult', False) if isinstance(movie, dict) else getattr(movie, 'adult', False)
        str_genres = [str(g) for g in movie_genres]
        
        keep_movie = True
        if hide_gore and '27' in str_genres: keep_movie = False
        if hide_extreme and is_adult: keep_movie = False
        if target_rating == 'G' and '16' not in str_genres and '10751' not in str_genres:
            keep_movie = False

        if keep_movie: filtered_movies.append(movie)

    display_list = filtered_movies if filtered_movies else all_movies
    movies_to_show = display_list[offset : offset + 3]

    conn = get_db_connection()
    comments = conn.execute('''
        SELECT global_comments.*, users.username FROM global_comments 
        JOIN users ON global_comments.user_id = users.id 
        ORDER BY created_at DESC LIMIT 20
    ''').fetchall()
    conn.close()
    
    return render_template('home.html', movies=movies_to_show, offset=offset, 
                           has_prev=offset > 0, has_next=(offset + 3) < len(display_list), 
                           comments=comments)

@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    lang = session.get('language', 'en-US')
    movie = tmdb.get_movie_details(movie_id, language=lang)
    trailer = tmdb.get_movie_trailer(movie_id, language=lang)
    conn = get_db_connection()
    reviews = conn.execute('''
        SELECT reviews.*, users.username FROM reviews 
        JOIN users ON reviews.user_id = users.id 
        WHERE movie_id = ? ORDER BY created_at DESC
    ''', (movie_id,)).fetchall()
    conn.close()
    return render_template('movie_detail.html', movie=movie, trailer=trailer, reviews=reviews)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    conn = get_db_connection()
    posts = conn.execute('''
        SELECT global_comments.*, users.username FROM global_comments 
        JOIN users ON global_comments.user_id = users.id 
        ORDER BY created_at DESC
    ''').fetchall()
    conn.close()
    return render_template('dashboard.html', username=session.get('username'), posts=posts)

@app.route('/post_thought', methods=['POST'])
def post_thought():
    if 'user_id' not in session: return redirect(url_for('login'))
    title = request.form.get('title', 'Untitled')
    content = request.form.get('content')
    has_gore = 1 if request.form.get('has_gore') == '1' else 0
    has_extreme = 1 if request.form.get('has_extreme') == '1' else 0
    conn = get_db_connection()
    conn.execute('INSERT INTO global_comments (user_id, content, has_gore, has_extreme) VALUES (?, ?, ?, ?)',
                 (session['user_id'], f"[{title}] {content}", has_gore, has_extreme))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/submit_review_from_dashboard', methods=['POST'])
def submit_review_from_dashboard():
    return redirect(url_for('dashboard'))

@app.route('/set_language', methods=['POST'])
def set_language():
    selected_lang = request.form.get('language', 'en-US')
    session['language'] = selected_lang
    return redirect(request.referrer or url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        return redirect(url_for('thx'))
    return render_template('contact.html')

@app.route('/thx')
def thx():
    return render_template('thx.html')

@app.route('/genre/<int:genre_id>')
def genre_page(genre_id):
    movies = tmdb.get_movies_by_genre(genre_id)
    return render_template('genre_results.html', movies=movies, genre_name="Genre Results")

@app.route('/search')
def search():
    query = request.args.get('q', '')
    movies = tmdb.search_movies(query) if query else []
    return render_template('genre_results.html', movies=movies, genre_name=f"Results for: {query}")

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('dashboard'))
    return render_template('upload.html')

# --- AUTH ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = hash_password(request.form.get('password'))
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            return redirect(url_for('login'))
        except: return "Error: User exists."
        finally: conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = hash_password(request.form.get('password'))
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5001)