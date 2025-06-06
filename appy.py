from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from datetime import datetime
import hashlib
import re
import json
import os
import psycopg2
from psycopg2.errors import UniqueViolation
from psycopg2.extras import RealDictCursor
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Cargar variables de entorno (útil en local)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_123')

# ────────────────────────────────────────────────
# Configuración de caché
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ────────────────────────────────────────────────
# CONEXIÓN A SUPABASE (PostgreSQL)
def get_db_connection():
    try:
        return psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
    except KeyError:
        raise RuntimeError("Falta la variable DATABASE_URL en el entorno")

# ────────────────────────────────────────────────
# INICIALIZACIÓN DE LA BASE DE DATOS
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS developers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                skills TEXT NOT NULL,
                experience_years INTEGER CHECK (experience_years >= 0),
                portfolio_url TEXT,
                location TEXT,
                created_at TIMESTAMP
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL
            );
        ''')
        cursor.execute("SELECT COUNT(*) FROM admin")
        if cursor.fetchone()["count"] == 0:
            hashed_pwd = generate_password_hash("admin123")
            cursor.execute(
                "INSERT INTO admin (username, hashed_password) VALUES (%s, %s)",
                ("admin", hashed_pwd)
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# ────────────────────────────────────────────────
# VALIDACIÓN DE EMAIL
def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# ────────────────────────────────────────────────
# DECORADOR PARA ÁREAS PROTEGIDAS
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.cookies.get('admin_logged'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# ────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        required_fields = ['name', 'email', 'skills', 'experience_years']

        if not all(data.get(field) for field in required_fields):
            return jsonify({'status': 'error', 'message': '🚨 Faltan datos!', 'details': 'Completa todos los campos requeridos'}), 400

        experience = int(data.get('experience_years'))
        if experience < 0:
            return jsonify({'status': 'error', 'message': '🕶️ Ups!', 'details': 'Los años de experiencia no pueden ser negativos'}), 400

        if not is_valid_email(data.get('email')):
            return jsonify({'status': 'error', 'message': '📧 Email inválido!', 'details': 'Usa un formato correcto'}), 400

        developer_data = (
            data.get('name'),
            data.get('email'),
            data.get('skills'),
            experience,
            data.get('portfolio_url'),
            data.get('location'),
            datetime.utcnow()
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO developers (name, email, skills, experience_years, portfolio_url, location, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', developer_data)
            conn.commit()
            return jsonify({'status': 'success', 'message': '🎉 ¡Registro exitoso!', 'animation': 'confetti'}), 201

        except UniqueViolation:
            conn.rollback()
            return jsonify({'status': 'error', 'message': '💥 Email duplicado!', 'details': 'Este correo ya está registrado'}), 409
        finally:
            conn.close()

    except Exception as e:
        return jsonify({'status': 'error', 'message': '🚨 Error cósmico!', 'details': str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT hashed_password FROM admin WHERE username = %s', (username,))
        result = cursor.fetchone()
        conn.close()

        if result and check_password_hash(result['hashed_password'], password):
            response = redirect(url_for('admin_dashboard'))
            response.set_cookie('admin_logged', 'true', max_age=3600)
            return response

        return render_template('admin_login.html', error='Credenciales inválidas')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM developers ORDER BY created_at DESC')
    developers = cursor.fetchall()
    conn.close()
    return render_template('admin_dashboard.html', developers=developers)

@app.route('/admin/delete/<int:dev_id>', methods=['POST'])
@admin_required
def delete_developer(dev_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM developers WHERE id = %s', (dev_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export')
@admin_required
def export_to_json():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM developers')
    developers = cursor.fetchall()
    conn.close()

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

# ────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    app.run(debug=False)
