from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
import sqlite3
from datetime import datetime
import hashlib
import re
import json
import os
from functools import wraps
import psycopg2
from psycopg2 import sql

app = Flask(__name__)
app.secret_key = 'clave_secreta_123'

# Configuración de caché
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

def init_db():
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    c = conn.cursor()
    c.execute(sql.SQL('''CREATE TABLE IF NOT EXISTS developers (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            skills TEXT NOT NULL,
            experience_years INTEGER,
            portfolio_url TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )'''))
        c.execute('''CREATE TABLE IF NOT EXISTS admin (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            hashed_password TEXT NOT NULL
        )''')

        c.execute("SELECT COUNT(*) FROM admin")
        if c.fetchone()[0] == 0:
            # Use a strong username and password
            secure_username = "secure_admin"
            secure_password = "P@ssw0rd!2023#Strong"
            hashed_pwd = hash_password(secure_password)
            c.execute("INSERT INTO admin (username, hashed_password) VALUES (%s, %s)",
                 (secure_username, hashed_pwd))
        
        c.execute("SELECT COUNT(*) FROM admin")
        if c.fetchone()[0] == 0:
            hashed_pwd = hash_password("admin123")
            c.execute("INSERT INTO admin (username, hashed_password) VALUES (?, ?)",
                     ("admin", hashed_pwd))
        conn.commit()
    
    # ... (mantén el resto del código de creación de tablas)

def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.cookies.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Ruta principal
@app.route('/')
def index():
    return render_template('index.html')

# Registro de desarrolladores
@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        required_fields = ['name', 'email', 'skills', 'experience_years']
        
        if not all(data.get(field) for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '🚨 Faltan datos!',
                'details': 'Completa todos los campos requeridos'
            }), 400
            
        experience = int(data.get('experience_years'))
        if experience < 0:
            return jsonify({
                'status': 'error', 
                'message': '🕶️ Ups!',
                'details': 'Los años de experiencia no pueden ser negativos'
            }), 400

        if not is_valid_email(data.get('email')):
            return jsonify({
                'status': 'error',
                'message': '📧 Email inválido!',
                'details': 'Usa un formato correcto (ej: usuario@dominio.com)'
            }), 400

        developer_data = (
            data.get('name'),
            data.get('email'),
            data.get('skills'),
            experience,
            data.get('portfolio_url'),
            data.get('location'),
            datetime.utcnow()
        )

        with sqlite3.connect('devpool.db') as conn:
            try:
                conn.execute('''INSERT INTO developers 
                            (name, email, skills, experience_years, portfolio_url, location, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)''', developer_data)
                return jsonify({
                    'status': 'success',
                    'message': '🎉 ¡Registro exitoso!',
                    'details': 'Tu perfil blockchain está listo para brillar ✨',
                    'animation': 'confetti'
                }), 201
            except sqlite3.IntegrityError:
                return jsonify({
                    'status': 'error',
                    'message': '💥 Email duplicado!',
                    'details': 'Este correo ya está registrado en nuestro sistema'
                }), 409
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': '🚨 Error cósmico!',
            'details': str(e)
        }), 500

# Sistema de administración
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        with sqlite3.connect('devpool.db') as conn:
            c = conn.cursor()
            c.execute('SELECT hashed_password FROM admin WHERE username = ?', (username,))
            result = c.fetchone()
            
            if result and result[0] == hash_password(password):
                response = redirect(url_for('admin_dashboard'))
                response.set_cookie('admin_logged', 'true', max_age=3600)
                return response
            
        return render_template('admin_login.html', error='Credenciales inválidas')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    with sqlite3.connect('devpool.db') as conn:
        conn.row_factory = sqlite3.Row
        developers = conn.execute('''
            SELECT id, name, email, skills, experience_years,
                   portfolio_url as portfolio, location, created_at
            FROM developers
        ''').fetchall()
    return render_template('admin_dashboard.html', developers=developers)

@app.route('/admin/delete/<int:dev_id>', methods=['POST'])
@admin_required
def delete_developer(dev_id):
    with sqlite3.connect('devpool.db') as conn:
        conn.execute('DELETE FROM developers WHERE id = ?', (dev_id,))
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export')
@admin_required
def export_to_json():
    with sqlite3.connect('devpool.db') as conn:
        conn.row_factory = sqlite3.Row
        developers = [dict(row) for row in conn.execute('SELECT * FROM developers').fetchall()]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'developers_export_{timestamp}.json'
    
    with open(filename, 'w') as f:
        json.dump(developers, f, indent=4, default=str)
    
    response = send_file(filename, as_attachment=True)
    os.remove(filename)
    return response

@app.route('/admin/logout')
def admin_logout():
    response = redirect(url_for('index'))
    response.delete_cookie('admin_logged')
    return response

if __name__ == '__main__':
    init_db()
    app.run(debug=False)