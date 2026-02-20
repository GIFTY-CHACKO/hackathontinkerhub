import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, g, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
DATABASE = 'database.db'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS collectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            company_name TEXT,
            address TEXT,
            phone TEXT NOT NULL,
            area TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_filename TEXT,
            location TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            message TEXT,
            rating INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

with app.app_context():
    init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if request.method == 'POST':
        location = request.form['location'].strip()
        description = request.form['description']
        
        file = request.files['image']
        filename = None
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO reports (image_filename, location, description) VALUES (?, ?, ?)", (filename, location, description))
        db.commit()
        
        # Get all collectors
        cursor.execute("SELECT * FROM collectors")
        rows = cursor.fetchall()
        
        # Convert to list of dictionaries
        all_collectors = []
        for row in rows:
            all_collectors.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'company_name': row[3],
                'address': row[4],
                'phone': row[5],
                'area': row[6]
            })
        
        # MATCHING - check if collector's area is in location
        matched_collectors = []
        location_lower = location.lower()
        
        for c in all_collectors:
            area_lower = c['area'].strip().lower()
            if area_lower in location_lower:
                matched_collectors.append(c)
        
        print(f"Location: {location}")
        print(f"Matched: {matched_collectors}")
        
        return render_template('upload.html', success=True, collectors=matched_collectors)
    
    return render_template('upload.html', success=False)

@app.route('/upload', methods=['GET', 'POST'])
def upload_waste():
    return report()

@app.route('/collector', methods=['GET', 'POST'])
def collector():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        company = request.form['company']
        address = request.form['address']
        phone = request.form['phone']
        area = request.form['area']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO collectors (name, email, company_name, address, phone, area) VALUES (?, ?, ?, ?, ?, ?)", (name, email, company, address, phone, area))
        db.commit()
        
        flash("Collector registered successfully!", "success")
        return redirect(url_for('collector'))
    
    return render_template('register_collector.html')

@app.route('/register_collector', methods=['GET', 'POST'])
def register_collector():
    return collector()

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        name = request.form['name']
        message = request.form['message']
        rating = request.form['rating']
        cursor.execute("INSERT INTO feedback (name, message, rating) VALUES (?, ?, ?)", (name, message, rating))
        db.commit()
        flash("Feedback submitted!", "success")
        return redirect(url_for('feedback'))
    
    cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
    feedbacks = []
    for row in cursor.fetchall():
        feedbacks.append({'name': row[0], 'message': row[1], 'rating': row[2]})
    
    return render_template('feedback.html', feedbacks=feedbacks)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)