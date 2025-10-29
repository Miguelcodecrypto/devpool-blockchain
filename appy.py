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
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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

def get_remote_address():
    """Obtener IP del cliente"""
    return request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR') or '127.0.0.1'

print("🔧 Modo híbrido: Seguridad básica local + completa en producción")

# 📊 Sistema de monitoreo de intentos fallidos
failed_attempts = defaultdict(list)
blocked_ips = defaultdict(float)

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

# Configuración de correo - SMTP2GO (Render compatible)
try:
    # Configuración SMTP ROBUSTA - SMTP2GO por defecto
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'mail.smtp2go.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 2525))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'contacto@clmblockchain.org')
    
    # Logging detallado de configuración
    print("📧 [EMAIL CONFIG] Configuración SMTP:")
    print(f"📧 [EMAIL CONFIG] Servidor: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
    print(f"📧 [EMAIL CONFIG] Usuario: {app.config['MAIL_USERNAME']}")
    print(f"📧 [EMAIL CONFIG] Password configurado: {'SÍ' if app.config['MAIL_PASSWORD'] else 'NO'}")
    print(f"📧 [EMAIL CONFIG] TLS: {app.config['MAIL_USE_TLS']}, SSL: {app.config['MAIL_USE_SSL']}")
    
    # Configurar email solo si tiene credenciales
    if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
        mail = True
        print("✅ Sistema de email configurado correctamente")
    else:
        mail = None
        print("⚠️ Sistema de email NO configurado - faltan credenciales")
        
except Exception as e:
    mail = None
    print(f"❌ Error inicializando sistema de email: {e}")

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
# FUNCIONES DE EMAIL MEJORADAS CON DEBUGGING AVANZADO
def test_smtp_connection():
    """Prueba la conexión SMTP antes de enviar emails"""
    try:
        print("🧪 [SMTP TEST] Probando conexión SMTP...")
        
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print("❌ [SMTP TEST] Credenciales no configuradas")
            return False
        
        context = ssl.create_default_context()
        
        if app.config.get('MAIL_USE_SSL'):
            # SSL
            print(f"🔧 [SMTP TEST] Conectando con SSL al puerto {app.config['MAIL_PORT']}")
            with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], 
                                 context=context, timeout=30) as server:
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        else:
            # TLS
            print(f"🔧 [SMTP TEST] Conectando con TLS al puerto {app.config['MAIL_PORT']}")
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=30) as server:
                if app.config.get('MAIL_USE_TLS'):
                    server.starttls(context=context)
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        
        print("✅ [SMTP TEST] Conexión SMTP exitosa")
        return True
        
    except Exception as e:
        print(f"❌ [SMTP TEST] Error de conexión: {type(e).__name__}: {str(e)}")
        return False

def send_welcome_email(user_name: str, user_email: str, user_skills: str):
    """Envía email de bienvenida con debugging mejorado"""
    
    try:
        print(f"📧 [WELCOME] Iniciando envío de email de bienvenida a: {user_email}")
        
        # Verificar configuración
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print("❌ [WELCOME] Credenciales SMTP no configuradas")
            return False
        
        # Test de conexión primero
        if not test_smtp_connection():
            print("❌ [WELCOME] Test de conexión SMTP falló")
            return False
        
        # Renderizar template
        try:
            email_html = render_template('emails/welcome_email.html', 
                                        user_name=user_name, 
                                        user_skills=user_skills)
            print("✅ [WELCOME] Template renderizado correctamente")
        except Exception as template_error:
            print(f"❌ [WELCOME] Error renderizando template: {template_error}")
            return False
        
        # Crear mensaje
        message = MIMEMultipart("alternative")
        message["Subject"] = "Bienvenido al DevPool Blockchain CLM"
        message["From"] = app.config['MAIL_DEFAULT_SENDER']
        message["To"] = user_email
        
        # Agregar contenido HTML con encoding UTF-8
        html_part = MIMEText(email_html, "html", "utf-8")
        message.attach(html_part)
        
        print(f"📧 [WELCOME] Mensaje creado - Enviando desde {app.config['MAIL_USERNAME']} a {user_email}")
        
        # Enviar email
        context = ssl.create_default_context()
        
        if app.config.get('MAIL_USE_SSL'):
            # SSL (puerto 465)
            print(f"🔧 [WELCOME] Enviando con SSL en puerto {app.config['MAIL_PORT']}")
            with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], 
                                 context=context, timeout=60) as server:
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(message)
        else:
            # TLS (puerto 587)
            print(f"🔧 [WELCOME] Enviando con TLS en puerto {app.config['MAIL_PORT']}")
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=60) as server:
                if app.config.get('MAIL_USE_TLS'):
                    server.starttls(context=context)
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(message)
            
        print(f"✅ [WELCOME] Email de bienvenida enviado exitosamente a {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ [WELCOME] Error enviando email: {type(e).__name__}: {str(e)}")
        print(f"❌ [WELCOME] Detalles del error: {e}")
        return False

def send_admin_notification(user_data: dict):
    """Envía notificación al admin con debugging mejorado"""
    
    try:
        admin_email = os.environ.get('ADMIN_EMAIL')
        print(f"📧 [ADMIN] Iniciando notificación admin para: {user_data.get('name')}")
        
        # Verificar configuración
        if not admin_email:
            print("❌ [ADMIN] ADMIN_EMAIL no configurado")
            return False
            
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print("❌ [ADMIN] Credenciales SMTP no configuradas")
            return False
        
        # Preparar HTML del email admin
        admin_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">Nuevo Desarrollador Registrado</h2>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>Información del registro:</h3>
                <p><strong>Nombre:</strong> {user_data.get("name")}</p>
                <p><strong>Email:</strong> {user_data.get("email")}</p>
                <p><strong>Habilidades:</strong> {user_data.get("skills")}</p>
                <p><strong>Experiencia:</strong> {user_data.get("experience_years")} años</p>
                <p><strong>Portfolio:</strong> {user_data.get("portfolio_url", "No proporcionado")}</p>
                <p><strong>Ubicación:</strong> {user_data.get("location", "No proporcionada")}</p>
                <p><strong>IP:</strong> {user_data.get("ip")}</p>
                <p><strong>Fecha:</strong> {user_data.get("created_at")}</p>
            </div>
            
            <div style="background: #6366f1; color: white; padding: 15px; border-radius: 10px; text-align: center;">
                <p style="margin: 0;">DevPool Blockchain CLM - Panel de Administración</p>
            </div>
        </div>
        '''
            
        # Crear mensaje
        message = MIMEMultipart("alternative")
        message["Subject"] = f"Nuevo registro DevPool: {user_data.get('name')}"
        message["From"] = app.config['MAIL_DEFAULT_SENDER']
        message["To"] = admin_email
        
        # Agregar contenido HTML
        html_part = MIMEText(admin_html, "html", "utf-8")
        message.attach(html_part)
        
        print(f"📧 [ADMIN] Enviando notificación desde {app.config['MAIL_USERNAME']} a {admin_email}")
        
        # Enviar email
        context = ssl.create_default_context()
        
        if app.config.get('MAIL_USE_SSL'):
            with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], 
                                 context=context, timeout=60) as server:
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(message)
        else:
            with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=60) as server:
                if app.config.get('MAIL_USE_TLS'):
                    server.starttls(context=context)
                server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                server.send_message(message)
            
        print(f"✅ [ADMIN] Notificación admin enviada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ [ADMIN] Error enviando notificación: {type(e).__name__}: {str(e)}")
        return False

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
        print("🔍 [SUBMIT] === NUEVO REGISTRO INICIADO ===")
        
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
        print(f"🔍 [SUBMIT] IP registrada: {user_ip}")
        
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
        
        print(f"🔍 [SUBMIT] Insertando en Supabase: {developer_data['name']} ({developer_data['email']})")
        
        # Insertar en Supabase
        response = developers_table.insert(developer_data).execute()
        
        if response.data:
            print(f"✅ [SUBMIT] Usuario {data['name']} registrado exitosamente en BD")
            
            # INTENTAR ENVÍO DE EMAILS CON DEBUGGING DETALLADO
            print("📧 [SUBMIT] === INICIANDO ENVÍO DE EMAILS ===")
            
            # Email de bienvenida
            email_sent = False
            admin_notified = False
            
            try:
                print(f"📧 [SUBMIT] Enviando email de bienvenida...")
                email_sent = send_welcome_email(
                    user_name=data['name'],
                    user_email=data['email'], 
                    user_skills=data['skills']
                )
                print(f"📧 [SUBMIT] Resultado email bienvenida: {email_sent}")
            except Exception as email_error:
                print(f"❌ [SUBMIT] Error crítico en email bienvenida: {email_error}")
            
            # Notificación admin
            try:
                print(f"📧 [SUBMIT] Enviando notificación admin...")
                admin_notified = send_admin_notification(developer_data)
                print(f"📧 [SUBMIT] Resultado notificación admin: {admin_notified}")
            except Exception as admin_error:
                print(f"❌ [SUBMIT] Error crítico en notificación admin: {admin_error}")
            
            print("📧 [SUBMIT] === ENVÍO DE EMAILS COMPLETADO ===")
            
            # RESPUESTA AL USUARIO SIEMPRE EXITOSA
            response_message = '🎉 ¡Registro exitoso! Bienvenido al DevPool Blockchain CLM'
            if not email_sent:
                response_message += ' (Email de confirmación en proceso)'
            
            return jsonify({
                'success': True, 
                'message': response_message,
                'email_status': {
                    'welcome_sent': email_sent,
                    'admin_notified': admin_notified,
                    'mode': 'production'
                }
            }), 200
        else:
            print("❌ [SUBMIT] Error insertando en Supabase")
            return jsonify({'error': 'Error al registrar el usuario'}), 500
            
    except Exception as e:
        print(f"❌ [SUBMIT] Error crítico en submit: {str(e)}")
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

# RUTAS DE DEBUGGING PARA EMAILS
@app.route('/test-email-config')
def test_email_config():
    """Endpoint para verificar configuración de email"""
    try:
        return jsonify({
            'status': 'success',
            'config': {
                'server': app.config.get('MAIL_SERVER'),
                'port': app.config.get('MAIL_PORT'),
                'username': app.config.get('MAIL_USERNAME'),
                'password_configured': bool(app.config.get('MAIL_PASSWORD')),
                'use_tls': app.config.get('MAIL_USE_TLS'),
                'use_ssl': app.config.get('MAIL_USE_SSL'),
                'admin_email': os.environ.get('ADMIN_EMAIL')
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/test-smtp-connection')
def test_smtp_connection_endpoint():
    """Endpoint para probar conexión SMTP"""
    try:
        result = test_smtp_connection()
        return jsonify({
            'status': 'success' if result else 'error',
            'message': 'Conexión SMTP exitosa' if result else 'Error de conexión SMTP',
            'server': f"{app.config.get('MAIL_SERVER')}:{app.config.get('MAIL_PORT')}"
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        })

@app.route('/test-send-email')
def test_send_email():
    """Endpoint para probar envío real de email"""
    try:
        # Datos de prueba
        test_data = {
            'name': 'Test Usuario DevPool',
            'email': os.environ.get('ADMIN_EMAIL', 'test@example.com'),
            'skills': 'Testing, Debugging, DevOps'
        }
        
        print(f"🧪 [TEST EMAIL] Enviando email de prueba a: {test_data['email']}")
        
        # Intentar envío
        result = send_welcome_email(
            user_name=test_data['name'],
            user_email=test_data['email'],
            user_skills=test_data['skills']
        )
        
        return jsonify({
            'status': 'success' if result else 'error',
            'message': f'Envío de email: {"exitoso" if result else "fallido"}',
            'details': {
                'to': test_data['email'],
                'from': app.config.get('MAIL_USERNAME'),
                'result': result
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print("🚀 === INICIANDO DEVPOOL BLOCKCHAIN CLM ===")
    print(f"🌍 Puerto: {port}")
    print(f"🔧 Debug: {debug_mode}")
    print(f"📧 Email configurado: {'SÍ' if mail else 'NO'}")
    print("🚀 ==========================================")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)