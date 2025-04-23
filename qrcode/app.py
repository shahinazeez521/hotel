from flask import Flask, request, render_template, flash, redirect, url_for, send_from_directory
import os
import qrcode
from werkzeug.utils import secure_filename
import sqlite3
from contextlib import contextmanager
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['QRCODE_FOLDER'] = 'static/qrcodes'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SERVER_NAME'] = None  # Dynamic host/port

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['QRCODE_FOLDER'], exist_ok=True)

# Database setup
DATABASE = 'menus.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hotel_name TEXT NOT NULL,
                pdf_filename TEXT NOT NULL,
                qr_filename TEXT NOT NULL
            )
        ''')
        conn.commit()

# Initialize database
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_menu', methods=['POST'])
def upload_menu():
    if 'menu_pdf' not in request.files or not request.form.get('hotel_name'):
        flash('Missing file or hotel name')
        return redirect(url_for('index'))
    
    file = request.files['menu_pdf']
    hotel_name = request.form['hotel_name']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    
    # Validate file (case-insensitive extension and MIME type)
    if file and (file.filename.lower().endswith('.pdf') and file.mimetype == 'application/pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(file_path)
            logger.debug(f'Saved file: {file_path}')
        except Exception as e:
            logger.error(f'Error saving file: {str(e)}')
            flash(f'Error saving file: {str(e)}')
            return redirect(url_for('index'))
        
        # Generate QR code
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO menus (hotel_name, pdf_filename, qr_filename) VALUES (?, ?, ?)',
                              (hotel_name, filename, ''))  # Temporary qr_filename
                menu_id = cursor.lastrowid
                conn.commit()
                logger.debug(f'Inserted menu: id={menu_id}, hotel_name={hotel_name}, pdf_filename={filename}')
            except sqlite3.OperationalError as e:
                logger.error(f'Database error: {str(e)}')
                flash(f'Database error: {str(e)}')
                return redirect(url_for('index'))
            
        qr_filename = f'qr_{menu_id}.png'
        qr_path = os.path.join(app.config['QRCODE_FOLDER'], qr_filename)
        
        # Generate external URL
        download_url = f"{request.host_url}download_menu/{menu_id}"
        try:
            qr = qrcode.make(download_url)
            qr.save(qr_path)
            logger.debug(f'Generated QR code: {qr_path}, URL: {download_url}')
        except Exception as e:
            logger.error(f'Error generating QR code: {str(e)}')
            flash(f'Error generating QR code: {str(e)}')
            return redirect(url_for('index'))
        
        # Update QR filename
        with get_db() as conn:
            conn.execute('UPDATE menus SET qr_filename = ? WHERE id = ?', (qr_filename, menu_id))
            conn.commit()
            logger.debug(f'Updated menu id={menu_id} with qr_filename={qr_filename}')
        
        return redirect(url_for('display', menu_id=menu_id))
    else:
        logger.warning(f'Invalid file: filename={file.filename}, mimetype={file.mimetype}')
        flash('Invalid file format. Please upload a valid PDF.')
        return redirect(url_for('index'))

@app.route('/display/<int:menu_id>')
def display(menu_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, hotel_name, pdf_filename, qr_filename FROM menus WHERE id = ?', (menu_id,))
        menu = cursor.fetchone()
    
    if not menu:
        logger.error(f'Menu not found for id={menu_id}')
        flash('Menu not found')
        return redirect(url_for('index'))
    
    menu_dict = {
        'id': menu[0],
        'hotel_name': menu[1],
        'pdf_filename': menu[2],
        'qr_filename': menu[3]
    }
    logger.debug(f'Displaying menu: {menu_dict}')
    return render_template('display.html', menu=menu_dict)

@app.route('/download_menu/<int:menu_id>')
def download_menu(menu_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT pdf_filename FROM menus WHERE id = ?', (menu_id,))
        menu = cursor.fetchone()
    
    if not menu:
        logger.error(f'Menu not found for download: id={menu_id}')
        flash('Menu not found')
        return redirect(url_for('index'))
    
    pdf_filename = menu[0]
    try:
        logger.debug(f'Serving file: {pdf_filename}')
        return send_from_directory(app.config['UPLOAD_FOLDER'], pdf_filename, as_attachment=True)
    except FileNotFoundError:
        logger.error(f'PDF file not found: {pdf_filename}')
        flash('PDF file not found')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)