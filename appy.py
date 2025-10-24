from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from datetime import datetime
import re
import json
import os
import uuid
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key')

# Configuración de correo (temporalmente deshabilitado)
mail = None
print("📧 Sistema de email DESHABILITADO temporalmente")

# ────────────────────────────────────────────────
# Configuración de Supabase
class SupabaseConnector:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        
        if not self.url or not self.key:
            raise ValueError("Variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas")
        
        self.client = create_client(self.url, self.key)
        
    def get_table(self, table_name):
        return self.client.table(table_name)

try:
    supabase_connector = SupabaseConnector()
    developers_table = supabase_connector.get_table('developers')
    admin_table = supabase_connector.get_table('admin')
    print("✅ Conexión a Supabase establecida")
except Exception as e:
    print(f"❌ Error conectando a Supabase: {e}")
    developers_table = None
    admin_table = None

# ────────────────────────────────────────────────
# FUNCIONES DE EMAIL (TEMPORALMENTE DESHABILITADAS)
def send_welcome_email(user_name: str, user_email: str, user_skills: str):
    """Envía email de bienvenida al usuario registrado - TEMPORALMENTE DESHABILITADO"""
    print(f"📧 Email deshabilitado temporalmente - no se envía email a {user_email}")
    print(f"📝 Usuario registrado: {user_name} ({user_email})")
    return True  # Retornar True para que no falle el registro

def send_admin_notification(user_data: dict):
    """Envía notificación al admin sobre nuevo registro - TEMPORALMENTE DESHABILITADO"""
    print("📧 Notificación admin deshabilitada temporalmente")
    print(f"📝 Nuevo registro: {user_data.get('name')} - {user_data.get('email')}")
    return True  # Retornar True para que no falle el registro

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
    # Obtener número de usuarios registrados
    try:
        response = developers_table.select('id').execute()
        num_usuarios = len(response.data) if response and hasattr(response, 'data') else 0
    except Exception:
        num_usuarios = 0
    return render_template('index.html', num_usuarios=num_usuarios)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.form
        required_fields = ['name', 'email', 'skills', 'experience_years']
        
        # Validar campos requeridos
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Campo {field} es requerido'}), 400
        
        # Validar email
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, data['email']):
            return jsonify({'error': 'Email no válido'}), 400
        
        # Validar años de experiencia
        try:
            experience_years = int(data['experience_years'])
            if experience_years < 0 or experience_years > 50:
                return jsonify({'error': 'Años de experiencia debe estar entre 0 y 50'}), 400
        except ValueError:
            return jsonify({'error': 'Años de experiencia debe ser un número'}), 400
        
        # Obtener IP del usuario
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
        print(f"IP registrada: {user_ip}")
        
        # Preparar datos para insertar
        developer_data = {
            'id': str(uuid.uuid4()),
            'name': data['name'].strip(),
            'email': data['email'].strip().lower(),
            'skills': data['skills'].strip(),
            'experience_years': experience_years,
            'portfolio_url': data.get('portfolio_url', '').strip() or None,
            'location': data.get('location', '').strip() or None,
            'ip': user_ip,
            'created_at': datetime.now().isoformat()
        }
        
        # Insertar en Supabase
        response = developers_table.insert(developer_data).execute()
        
        if response.data:
            print(f"✅ Usuario {data['name']} registrado exitosamente")
            
            # Intentar enviar emails (temporalmente deshabilitado)
            print("📧 Intentando enviar emails...")
            
            # Email de bienvenida
            print(f"📤 Enviando email de bienvenida a: {data['email']}")
            email_sent = send_welcome_email(
                user_name=data['name'],
                user_email=data['email'], 
                user_skills=data['skills']
            )
            print(f"📤 Resultado email bienvenida: {email_sent}")
            
            # Notificación admin
            print(f"📤 Enviando notificación admin para: {data['name']}")
            admin_notified = send_admin_notification(developer_data)
            print(f"📤 Resultado notificación admin: {admin_notified}")
            
            return jsonify({
                'success': True, 
                'message': 'Registro exitoso. ¡Bienvenido al DevPool!'
            }), 200
        else:
            return jsonify({'error': 'Error al registrar el usuario'}), 500
            
    except Exception as e:
        print(f"❌ Error en submit: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('admin_login.html', error='Usuario y contraseña requeridos')
        
        try:
            # Buscar admin en Supabase
            response = admin_table.select('hashed_password').eq('username', username).execute()
            print(f"Respuesta Supabase: {response}")
            
            if response.data:
                print(f"Datos: {response.data}")
                stored_hash = response.data[0]['hashed_password']
                
                if check_password_hash(stored_hash, password):
                    # Login exitoso
                    resp = redirect(url_for('admin_dashboard'))
                    resp.set_cookie('admin_logged', 'true', max_age=3600)  # 1 hora
                    return resp
                else:
                    return render_template('admin_login.html', error='Credenciales inválidas')
            else:
                return render_template('admin_login.html', error='Usuario no encontrado')
                
        except Exception as e:
            print(f"Error en login: {e}")
            return render_template('admin_login.html', error='Error del servidor')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    try:
        # Obtener todos los desarrolladores
        response = developers_table.select('*').order('created_at', desc=True).execute()
        developers = response.data if response.data else []
        
        return render_template('admin_dashboard.html', developers=developers)
    except Exception as e:
        print(f"Error en dashboard: {e}")
        return render_template('admin_dashboard.html', developers=[], error="Error cargando datos")

@app.route('/admin/logout')
def admin_logout():
    resp = redirect(url_for('admin_login'))
    resp.set_cookie('admin_logged', '', expires=0)
    return resp

@app.route('/admin/export')
@admin_required
def export_developers():
    try:
        response = developers_table.select('*').order('created_at', desc=True).execute()
        developers = response.data if response.data else []
        
        # Crear archivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"developers_export_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(developers, f, ensure_ascii=False, indent=2, default=str)
        
        return send_file(filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"Error en export: {e}")
        return jsonify({'error': 'Error exportando datos'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)