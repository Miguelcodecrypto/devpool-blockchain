from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
from datetime import datetime, timedelta
import re
import json
import os
import uuid
import secrets
import time
from collections import defaultdict
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# 🔐 CONFIGURACIÓN DE SEGURIDAD MEJORADA
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Configuración de cookies seguras
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
)

print("🔧 Modo SIN EMAIL - Solo testing de funcionalidad básica")

# 📊 Sistema de monitoreo de intentos fallidos
failed_attempts = defaultdict(list)
blocked_ips = defaultdict(float)

def get_remote_address():
    """Obtener IP del cliente"""
    return request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR') or '127.0.0.1'

def is_ip_blocked(ip):
    """Verificar si una IP está bloqueada temporalmente"""
    if ip in blocked_ips:
        if time.time() < blocked_ips[ip]:
            return True
        else:
            del blocked_ips[ip]
    return False

def record_failed_attempt(ip):
    """Registrar intento fallido y bloquear si es necesario"""
    current_time = time.time()
    
    # Limpiar intentos antiguos
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip]
        if current_time - attempt_time < 900
    ]
    
    # Añadir nuevo intento
    failed_attempts[ip].append(current_time)
    
    # Bloquear si hay 5 o más intentos en 15 minutos
    if len(failed_attempts[ip]) >= 5:
        blocked_ips[ip] = current_time + 900
        return True
    
    return False

def log_security_event(event_type, details, ip=None):
    """Registrar eventos de seguridad"""
    timestamp = datetime.now().isoformat()
    ip = ip or get_remote_address()
    print(f"🚨 [SECURITY] {timestamp} - {event_type} - IP: {ip} - {details}")

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
# FUNCIONES DE EMAIL SIMULADAS (SIN ENVÍO REAL)
def send_welcome_email(user_name: str, user_email: str, user_skills: str):
    """Simula envío de email de bienvenida (sin envío real)"""
    print(f"📧 [SIMULADO] Email de bienvenida para {user_name} ({user_email})")
    print(f"📧 [SIMULADO] Habilidades: {user_skills}")
    print("✅ [SIMULADO] Email de bienvenida 'enviado' exitosamente")
    return True

def send_admin_notification(user_data: dict):
    """Simula notificación al admin (sin envío real)"""
    print(f"📧 [SIMULADO] Notificación admin para nuevo registro:")
    print(f"📧 [SIMULADO] - Nombre: {user_data.get('name')}")
    print(f"📧 [SIMULADO] - Email: {user_data.get('email')}")
    print(f"📧 [SIMULADO] - Skills: {user_data.get('skills')}")
    print("✅ [SIMULADO] Notificación admin 'enviada' exitosamente")
    return True

# ────────────────────────────────────────────────
# DECORADOR PARA ÁREAS PROTEGIDAS
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged'):
            log_security_event("UNAUTHORIZED_ACCESS_ATTEMPT", f"Acceso no autorizado a {request.endpoint}")
            session.clear()
            return redirect(url_for('admin_login'))
        
        session['admin_last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
        return f(*args, **kwargs)
    return decorated_function

# ────────────────────────────────────────────────
@app.route('/')
def index():
    try:
        response = developers_table.select('id').execute()
        num_usuarios = len(response.data) if response and hasattr(response, 'data') else 0
    except Exception:
        num_usuarios = 0
    return render_template('index.html', num_usuarios=num_usuarios)

@app.route('/submit', methods=['POST'])
def submit():
    try:
        print("🔍 [SUBMIT] Recibiendo datos del formulario...")
        
        data = request.form
        print(f"🔍 [SUBMIT] Datos recibidos: {dict(data)}")
        
        required_fields = ['name', 'email', 'skills', 'experience_years']
        
        missing_fields = []
        for field in required_fields:
            value = data.get(field)
            if not value or not value.strip():
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ [SUBMIT] Campos faltantes: {missing_fields}")
            return jsonify({'error': f'Campos requeridos faltantes: {", ".join(missing_fields)}'}), 400
        
        print(f"✅ [SUBMIT] Validación inicial completada para: {data.get('name')}")
        
        # Validar email
        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_pattern, data['email']):
            print(f"❌ [SUBMIT] Email inválido: {data['email']}")
            return jsonify({'error': 'Email no válido'}), 400
        
        # Validar años de experiencia
        try:
            experience_years = int(data['experience_years'])
            if experience_years < 0 or experience_years > 50:
                return jsonify({'error': 'Años de experiencia debe estar entre 0 y 50'}), 400
        except ValueError:
            return jsonify({'error': 'Años de experiencia debe ser un número'}), 400
        
        # Obtener IP del usuario
        user_ip = get_remote_address()
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
            
            # EMAILS SIMULADOS (SIN ENVÍO REAL)
            print("📧 [MODO TEST] Simulando envío de emails...")
            
            email_sent = send_welcome_email(
                user_name=data['name'],
                user_email=data['email'], 
                user_skills=data['skills']
            )
            
            admin_notified = send_admin_notification(developer_data)
            
            return jsonify({
                'success': True, 
                'message': '🎉 ¡Registro exitoso! (Modo test - emails simulados)',
                'email_status': {
                    'welcome_sent': email_sent,
                    'admin_notified': admin_notified,
                    'mode': 'simulated'
                }
            }), 200
        else:
            return jsonify({'error': 'Error al registrar el usuario'}), 500
            
    except Exception as e:
        print(f"❌ Error en submit: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    client_ip = get_remote_address()
    
    if is_ip_blocked(client_ip):
        log_security_event("BLOCKED_IP_ACCESS", f"Acceso bloqueado", client_ip)
        return render_template('admin_login.html', 
                             error='IP bloqueada temporalmente'), 429
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            log_security_event("LOGIN_MISSING_CREDENTIALS", f"Sin credenciales", client_ip)
            return render_template('admin_login.html', error='Usuario y contraseña requeridos')
        
        try:
            response = admin_table.select('hashed_password').eq('username', username).execute()
            
            if response.data:
                stored_hash = response.data[0]['hashed_password']
                
                if check_password_hash(stored_hash, password):
                    if client_ip in failed_attempts:
                        del failed_attempts[client_ip]
                    
                    session.permanent = True
                    session['admin_logged'] = True
                    session['admin_token'] = secrets.token_hex(32)
                    session['admin_login_time'] = datetime.now().isoformat()
                    session['admin_last_activity'] = datetime.now().isoformat()
                    session['admin_username'] = username
                    
                    log_security_event("SUCCESSFUL_LOGIN", f"Login exitoso: {username}", client_ip)
                    
                    return redirect(url_for('admin_dashboard'))
                else:
                    blocked = record_failed_attempt(client_ip)
                    log_security_event("FAILED_LOGIN", f"Contraseña incorrecta: {username}", client_ip)
                    
                    if blocked:
                        return render_template('admin_login.html', 
                                             error='Demasiados intentos fallidos'), 429
                    
                    return render_template('admin_login.html', error='Credenciales inválidas')
            else:
                blocked = record_failed_attempt(client_ip)
                log_security_event("FAILED_LOGIN", f"Usuario no encontrado: {username}", client_ip)
                
                if blocked:
                    return render_template('admin_login.html', 
                                         error='Demasiados intentos fallidos'), 429
                
                return render_template('admin_login.html', error='Credenciales inválidas')
                
        except Exception as e:
            log_security_event("LOGIN_ERROR", f"Error: {str(e)}", client_ip)
            print(f"Error en login: {e}")
            return render_template('admin_login.html', error='Error del servidor')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    try:
        response = developers_table.select('*').order('created_at', desc=True).execute()
        developers = response.data if response.data else []
        
        return render_template('admin_dashboard.html', developers=developers)
    except Exception as e:
        print(f"Error en dashboard: {e}")
        return render_template('admin_dashboard.html', developers=[], error="Error cargando datos")

@app.route('/admin/logout')
def admin_logout():
    username = session.get('admin_username', 'Unknown')
    log_security_event("ADMIN_LOGOUT", f"Usuario {username} cerró sesión")
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/delete/<string:dev_id>', methods=['POST'])
@admin_required
def delete_developer(dev_id):
    try:
        print(f"🗑️ Intentando eliminar desarrollador con ID: {dev_id}")
        
        info_response = developers_table.select('name, email').eq('id', dev_id).execute()
        
        if info_response.data:
            dev_info = info_response.data[0]
            
            response = developers_table.delete().eq('id', dev_id).execute()
            
            if response.data:
                print(f"✅ Desarrollador {dev_id} eliminado exitosamente")
                log_security_event("DEVELOPER_DELETED", 
                                 f"Admin eliminó: {dev_info['name']} ({dev_info['email']})")
                return redirect(url_for('admin_dashboard'))
            else:
                print(f"❌ Error en eliminación de ID: {dev_id}")
                return jsonify({'error': 'Error eliminando desarrollador'}), 500
        else:
            print(f"❌ No se encontró desarrollador con ID: {dev_id}")
            return jsonify({'error': 'Desarrollador no encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error eliminando desarrollador: {e}")
        log_security_event("DELETE_ERROR", f"Error en eliminación: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/admin/export')
@admin_required
def export_developers():
    try:
        response = developers_table.select('*').order('created_at', desc=True).execute()
        developers = response.data if response.data else []
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"developers_export_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(developers, f, ensure_ascii=False, indent=2, default=str)
        
        log_security_event("DATA_EXPORT", 
                         f"Admin exportó {len(developers)} registros")
        
        return send_file(filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"Error en export: {e}")
        log_security_event("EXPORT_ERROR", f"Error en exportación: {str(e)}")
        return "Error en exportación", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("🚀 Iniciando DevPool en modo SIN EMAIL")
    print("📧 Los emails serán simulados en la consola")
    app.run(host='0.0.0.0', port=port, debug=True)