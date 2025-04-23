import os
import uuid
import qrcode
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Used for flash messages

# Configure upload folders
UPLOAD_FOLDER = os.path.join('static', 'uploads')
QR_FOLDER = os.path.join('static', 'qrcodes')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['QR_FOLDER'] = QR_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

# SQLite as a simple database alternative to MongoDB
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('menus.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS menus (
        id TEXT PRIMARY KEY,
        hotel_name TEXT NOT NULL,
        filename TEXT NOT NULL,
        qr_filename TEXT NOT NULL,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database
init_db()

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_qr_code(menu_id):
    # Create QR code with the download URL
    download_url = url_for('download_menu', menu_id=menu_id, _external=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(download_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    qr_filename = f"{menu_id}.png"
    qr_path = os.path.join(app.config['QR_FOLDER'], qr_filename)
    img.save(qr_path)
    
    return qr_filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_menu():
    if 'menu_pdf' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    
    file = request.files['menu_pdf']
    hotel_name = request.form.get('hotel_name', 'Unknown Hotel')
    
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        # Generate unique ID for the menu
        menu_id = str(uuid.uuid4())
        
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        file_ext = os.path.splitext(filename)[1]
        unique_filename = f"{menu_id}{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Generate QR code
        qr_filename = generate_qr_code(menu_id)
        
        # Save to database
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO menus (id, hotel_name, filename, qr_filename) VALUES (?, ?, ?, ?)',
            (menu_id, hotel_name, unique_filename, qr_filename)
        )
        conn.commit()
        conn.close()
        
        return redirect(url_for('display_qr', menu_id=menu_id))
    
    flash('Invalid file type. Please upload a PDF.')
    return redirect(url_for('index'))

@app.route('/qr/<menu_id>')
def display_qr(menu_id):
    conn = get_db_connection()
    menu = conn.execute('SELECT * FROM menus WHERE id = ?', (menu_id,)).fetchone()
    conn.close()
    
    if menu:
        return render_template('display.html', menu=menu)
    
    flash('Menu not found')
    return redirect(url_for('index'))

@app.route('/download/<menu_id>')
def download_menu(menu_id):
    conn = get_db_connection()
    menu = conn.execute('SELECT * FROM menus WHERE id = ?', (menu_id,)).fetchone()
    conn.close()
    
    if menu:
        return send_from_directory(
            directory=app.config['UPLOAD_FOLDER'],
            path=menu['filename'],
            as_attachment=True
        )
    
    flash('Menu not found')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)