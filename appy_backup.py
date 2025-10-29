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
# from flask_limiter import Limiter  # Se habilitará en producción
# from flask_limiter.util import get_remote_address  # Se habilitará en producción  
# from flask_wtf.csrf import CSRFProtect  # Se habilitará en producción
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
# Generar secret key robusta si no existe
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Configuración de cookies seguras
app.config.update(
    # SESSION_COOKIE_SECURE=True,  # Se habilitará en producción HTTPS
    SESSION_COOKIE_HTTPONLY=True,  # No accesible via JavaScript
    SESSION_COOKIE_SAMESITE='Lax',  # Protección CSRF
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),  # Auto-logout 30 min
    # WTF_CSRF_TIME_LIMIT=None,  # Se habilitará en producción
)

# Inicializar protecciones de seguridad
# csrf = CSRFProtect(app)  # Se habilitará en producción
# limiter = Limiter(  # Se habilitará en producción
#     app=app,
#     key_func=get_remote_address,
#     default_limits=["200 per day", "50 per hour"],
#     storage_uri="memory://"
# )

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
    
    # Limpiar intentos antiguos (más de 15 minutos)
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip]
        if current_time - attempt_time < 900  # 15 minutos
    ]
    
    # Añadir nuevo intento
    failed_attempts[ip].append(current_time)
    
    # Bloquear si hay 5 o más intentos en 15 minutos
    if len(failed_attempts[ip]) >= 5:
        blocked_ips[ip] = current_time + 900  # Bloquear por 15 minutos
        return True
    
    return False

def log_security_event(event_type, details, ip=None):
    """Registrar eventos de seguridad"""
    timestamp = datetime.now().isoformat()
    ip = ip or get_remote_address()
    print(f"🚨 [SECURITY] {timestamp} - {event_type} - IP: {ip} - {details}")

def send_security_alert(event_type, details, ip=None):
    """Enviar alerta de seguridad por email"""
    try:
        admin_email = os.environ.get('ADMIN_EMAIL')
        if not admin_email:
            return
            
        alert_html = f'''
        <div style="background: #fee; border: 1px solid #f66; padding: 20px; border-radius: 10px;">
            <h2 style="color: #d00;">🚨 Alerta de Seguridad - DevPool ABCLM</h2>
            <p><strong>Evento:</strong> {event_type}</p>
            <p><strong>IP:</strong> {ip or get_remote_address()}</p>
            <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Detalles:</strong> {details}</p>
        </div>
        '''
        
        # Usar la función existente de envío de email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'🚨 Alerta de Seguridad - {event_type}'
        msg['From'] = app.config['MAIL_USERNAME']
        msg['To'] = admin_email
        
        html_part = MIMEText(alert_html, 'html', 'utf-8')
        msg.attach(html_part)
        
        # Enviar usando configuración SMTP existente
        context = ssl.create_default_context()
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            if app.config.get('MAIL_USE_TLS'):
                server.starttls(context=context)
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
            
    except Exception as e:
        print(f"❌ Error enviando alerta de seguridad: {e}")

# Configuración de correo DonDominio
try:
    # Configuración SMTP - SOPORTE MÚLTIPLES PROVEEDORES
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'mail.smtp2go.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 2525))
    
    # Configuración específica por proveedor
    if 'smtp2go.com' in app.config['MAIL_SERVER']:
        # SMTP2GO - Puerto 2525 TLS (Render compatible)
        app.config['MAIL_USE_TLS'] = True
        app.config['MAIL_USE_SSL'] = False
        print("🔧 Configuración SMTP2GO: TLS en puerto 2525 (Render compatible)")
    elif 'smtp.panel247.com' in app.config['MAIL_SERVER']:
        # DonDominio - Configuración por puerto
        if app.config['MAIL_PORT'] == 587:
            app.config['MAIL_USE_TLS'] = True
            app.config['MAIL_USE_SSL'] = False
            print("🔧 Configuración DonDominio: TLS en puerto 587")
        elif app.config['MAIL_PORT'] == 2525:
            app.config['MAIL_USE_TLS'] = True
            app.config['MAIL_USE_SSL'] = False
            print("🔧 Configuración DonDominio: TLS en puerto 2525 (Render compatible)")
        elif app.config['MAIL_PORT'] == 465:
            app.config['MAIL_USE_TLS'] = False
            app.config['MAIL_USE_SSL'] = True
            print("🔧 Configuración DonDominio: SSL en puerto 465")
    else:
        # Configuración genérica
        app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
        app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
        print(f"🔧 Configuración genérica: Puerto {app.config['MAIL_PORT']}")
    
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
    
    # Configurar email solo si tiene credenciales
    if app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
        mail = True  # Marca que el email está configurado
        print("✅ Sistema de email DonDominio configurado")
        print(f"📧 Servidor: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
        print(f"📧 Usuario: {app.config['MAIL_USERNAME']}")
        print(f"🔒 TLS: {app.config['MAIL_USE_TLS']}, SSL: {app.config['MAIL_USE_SSL']}")
    else:
        mail = None
        print("⚠️ Sistema de email no configurado - funcionará sin emails")
except Exception as e:
    mail = None
    print(f"⚠️ Error inicializando sistema de email: {e}")

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
# FUNCIONES DE EMAIL CON DONDOMINIO SMTP
def send_welcome_email(user_name: str, user_email: str, user_skills: str):
    """Envía email de bienvenida al usuario registrado usando DonDominio"""
    
    try:
        # Verificar configuración de email antes de intentar enviar
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print("⚠️ Configuración de email incompleta, saltando envío")
            return False
        
        # Renderizar template de email
        email_html = render_template('emails/welcome_email.html', 
                                    user_name=user_name, 
                                    user_skills=user_skills)
        
        # SMTP directo con DonDominio
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        print(f"🔧 [WELCOME] Conectando a DonDominio SMTP...")
        print(f"� [WELCOME] Servidor: {app.config['MAIL_SERVER']}:{app.config['MAIL_PORT']}")
        
        # Crear mensaje
        message = MIMEMultipart("alternative")
        message["Subject"] = "🚀 ¡Bienvenido al DevPool Blockchain CLM!"
        message["From"] = "contacto@clmblockchain.org"  # Dominio verificado en SMTP2GO
        message["To"] = user_email
        
        # Crear parte HTML
        html_part = MIMEText(email_html, "html")
        message.attach(html_part)
        
        # Conectar según configuración TLS/SSL con timeout
        try:
            if app.config.get('MAIL_USE_SSL'):
                # SSL (puerto 465)
                print(f"🔧 [WELCOME] Usando SSL en puerto {app.config['MAIL_PORT']}")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], 
                                     context=context, timeout=30) as server:
                    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                    print("🔧 [WELCOME] Enviando mensaje...")
                    server.send_message(message)
            else:
                # TLS (puerto 587)
                print(f"🔧 [WELCOME] Usando TLS en puerto {app.config['MAIL_PORT']}")
                with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=30) as server:
                    if app.config.get('MAIL_USE_TLS'):
                        print("🔧 [WELCOME] Iniciando STARTTLS...")
                        server.starttls()
                    print("🔧 [WELCOME] Autenticando...")
                    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                    print("🔧 [WELCOME] Enviando mensaje...")
                    server.send_message(message)
        except Exception as smtp_error:
            print(f"🔧 [WELCOME] Error SMTP específico: {type(smtp_error).__name__}: {str(smtp_error)}")
            raise smtp_error
            
        print(f"✅ Email de bienvenida enviado a {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando email a {user_email}: {type(e).__name__}: {str(e)}")
        return False

def send_admin_notification(user_data: dict):
    """Envía notificación al admin sobre nuevo registro usando DonDominio"""
    
    try:
        admin_email = os.environ.get('ADMIN_EMAIL')
        # Verificar configuración de email
        if not admin_email or not app.config.get('MAIL_USERNAME'):
            print("⚠️ Email no configurado, saltando notificación admin")
            return False
            
        # Preparar HTML del email admin
        admin_html = f'''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">🎉 Nuevo Desarrollador Registrado</h2>
            
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
            
        # SMTP directo con DonDominio
        import smtplib
        import ssl
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        print(f"🔧 [ADMIN] Conectando a DonDominio SMTP...")
        
        # Crear mensaje
        message = MIMEMultipart("alternative")
        message["Subject"] = f"📧 Nuevo registro en DevPool: {user_data.get('name')}"
        message["From"] = "contacto@clmblockchain.org"  # Dominio verificado en SMTP2GO
        message["To"] = admin_email
        
        # Crear parte HTML
        html_part = MIMEText(admin_html, "html")
        message.attach(html_part)
        
        # Conectar según configuración TLS/SSL con timeout
        try:
            if app.config.get('MAIL_USE_SSL'):
                # SSL (puerto 465)
                print(f"🔧 [ADMIN] Usando SSL en puerto {app.config['MAIL_PORT']}")
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], 
                                     context=context, timeout=30) as server:
                    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                    server.send_message(message)
            else:
                # TLS (puerto 587)
                print(f"🔧 [ADMIN] Usando TLS en puerto {app.config['MAIL_PORT']}")
                with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'], timeout=30) as server:
                    if app.config.get('MAIL_USE_TLS'):
                        print("🔧 [ADMIN] Iniciando STARTTLS...")
                        server.starttls()
                    print("🔧 [ADMIN] Autenticando...")
                    server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
                    print("🔧 [ADMIN] Enviando mensaje...")
                    server.send_message(message)
        except Exception as smtp_error:
            print(f"🔧 [ADMIN] Error SMTP específico: {type(smtp_error).__name__}: {str(smtp_error)}")
            raise smtp_error
            
        print(f"✅ Notificación de admin enviada para {user_data.get('name')}")
        return True
        
    except Exception as e:
        print(f"❌ Error enviando notificación admin: {str(e)}")
        return False

# ────────────────────────────────────────────────
# DECORADOR PARA ÁREAS PROTEGIDAS
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si la sesión existe y es válida
        if not session.get('admin_logged'):
            log_security_event("UNAUTHORIZED_ACCESS_ATTEMPT", f"Acceso no autorizado a {request.endpoint}")
            session.clear()
            return redirect(url_for('admin_login'))
        
        # Verificar expiración de sesión (opcional en desarrollo)
        # login_time = session.get('admin_login_time')
        # if login_time:
        #     login_datetime = datetime.fromisoformat(login_time)
        #     if datetime.now() - login_datetime > timedelta(minutes=30):
        #         log_security_event("SESSION_EXPIRED", f"Sesión expirada para admin")
        #         session.clear()
        #         return redirect(url_for('admin_login'))
        
        # Renovar timestamp de actividad
        session['admin_last_activity'] = datetime.now().isoformat()
        session.permanent = True
        
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
        print("🔍 [SUBMIT] Recibiendo datos del formulario...")
        
        data = request.form
        print(f"🔍 [SUBMIT] Datos recibidos: {dict(data)}")
        print(f"🔍 [SUBMIT] Content-Type: {request.content_type}")
        
        required_fields = ['name', 'email', 'skills', 'experience_years']
        
        # Validar campos requeridos con logging detallado
        missing_fields = []
        for field in required_fields:
            value = data.get(field)
            print(f"🔍 [SUBMIT] Campo '{field}': '{value}'")
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
            
            # ENVÍO DIRECTO DE EMAILS - VERSIÓN CORREGIDA
            print("📧 Enviando emails directamente...")
            
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
            
            # RESPUESTA AL USUARIO
            return jsonify({
                'success': True, 
                'message': '🎉 ¡Registro exitoso! Bienvenido al DevPool Blockchain CLM',
                'email_status': {
                    'welcome_sent': email_sent,
                    'admin_notified': admin_notified
                }
            }), 200
        else:
            return jsonify({'error': 'Error al registrar el usuario'}), 500
            
    except Exception as e:
        print(f"❌ Error en submit: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
# @limiter.limit("5 per 15 minutes")  # Se habilitará en producción
def admin_login():
    client_ip = get_remote_address()
    
    # Verificar si la IP está bloqueada
    if is_ip_blocked(client_ip):
        log_security_event("BLOCKED_IP_ACCESS", f"Acceso bloqueado por múltiples intentos fallidos", client_ip)
        return render_template('admin_login.html', 
                             error='IP bloqueada temporalmente por múltiples intentos fallidos. Intente en 15 minutos.'), 429
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            log_security_event("LOGIN_MISSING_CREDENTIALS", f"Intento de login sin credenciales", client_ip)
            return render_template('admin_login.html', error='Usuario y contraseña requeridos')
        
        try:
            # Buscar admin en Supabase
            response = admin_table.select('hashed_password').eq('username', username).execute()
            
            if response.data:
                stored_hash = response.data[0]['hashed_password']
                
                if check_password_hash(stored_hash, password):
                    # Login exitoso - limpiar intentos fallidos
                    if client_ip in failed_attempts:
                        del failed_attempts[client_ip]
                    
                    # Crear sesión segura
                    session.permanent = True
                    session['admin_logged'] = True
                    session['admin_token'] = secrets.token_hex(32)
                    session['admin_login_time'] = datetime.now().isoformat()
                    session['admin_last_activity'] = datetime.now().isoformat()
                    session['admin_username'] = username
                    
                    log_security_event("SUCCESSFUL_LOGIN", f"Login exitoso para usuario: {username}", client_ip)
                    
                    # Enviar alerta de login admin
                    send_security_alert("Login Admin", f"Usuario {username} ha iniciado sesión", client_ip)
                    
                    return redirect(url_for('admin_dashboard'))
                else:
                    # Contraseña incorrecta
                    blocked = record_failed_attempt(client_ip)
                    log_security_event("FAILED_LOGIN", f"Contraseña incorrecta para usuario: {username}", client_ip)
                    
                    if blocked:
                        send_security_alert("IP Bloqueada", f"IP bloqueada por múltiples intentos fallidos", client_ip)
                        return render_template('admin_login.html', 
                                             error='Demasiados intentos fallidos. IP bloqueada por 15 minutos.'), 429
                    
                    return render_template('admin_login.html', error='Credenciales inválidas')
            else:
                # Usuario no encontrado
                blocked = record_failed_attempt(client_ip)
                log_security_event("FAILED_LOGIN", f"Usuario no encontrado: {username}", client_ip)
                
                if blocked:
                    send_security_alert("IP Bloqueada", f"IP bloqueada por múltiples intentos fallidos", client_ip)
                    return render_template('admin_login.html', 
                                         error='Demasiados intentos fallidos. IP bloqueada por 15 minutos.'), 429
                
                return render_template('admin_login.html', error='Credenciales inválidas')
                
        except Exception as e:
            log_security_event("LOGIN_ERROR", f"Error del servidor en login: {str(e)}", client_ip)
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
    username = session.get('admin_username', 'Unknown')
    log_security_event("ADMIN_LOGOUT", f"Usuario {username} cerró sesión")
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/delete/<string:dev_id>', methods=['POST'])
@admin_required
# @limiter.limit("10 per minute")  # Se habilitará en producción
def delete_developer(dev_id):
    """Eliminar desarrollador por ID"""
    try:
        print(f"🗑️ Intentando eliminar desarrollador con ID: {dev_id}")
        
        # Obtener información del desarrollador antes de eliminar
        info_response = developers_table.select('name, email').eq('id', dev_id).execute()
        
        if info_response.data:
            dev_info = info_response.data[0]
            
            # Eliminar por ID en Supabase
            response = developers_table.delete().eq('id', dev_id).execute()
            
            if response.data:
                print(f"✅ Desarrollador {dev_id} eliminado exitosamente")
                log_security_event("DEVELOPER_DELETED", 
                                 f"Admin {session.get('admin_username')} eliminó desarrollador: {dev_info['name']} ({dev_info['email']})")
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
# @limiter.limit("5 per hour")  # Se habilitará en producción
def export_developers():
    try:
        response = developers_table.select('*').order('created_at', desc=True).execute()
        developers = response.data if response.data else []
        
        # Crear archivo JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"developers_export_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(developers, f, ensure_ascii=False, indent=2, default=str)
        
        log_security_event("DATA_EXPORT", 
                         f"Admin {session.get('admin_username')} exportó {len(developers)} registros")
        
        return send_file(filename, as_attachment=True, download_name=filename)
        
    except Exception as e:
        print(f"Error en export: {e}")
        log_security_event("EXPORT_ERROR", f"Error en exportación: {str(e)}")
        return "Error en exportación", 500

@app.route('/test-email-config')
def test_email_config():
    """Endpoint temporal para probar configuración de email"""
    try:
        # Verificar configuración
        server = app.config.get('MAIL_SERVER')
        port = app.config.get('MAIL_PORT')
        username = app.config.get('MAIL_USERNAME')
        password = app.config.get('MAIL_PASSWORD')
        
        return jsonify({
            'status': 'success',
            'config': {
                'server': server,
                'port': port,
                'username': username,
                'password_configured': bool(password),
                'use_tls': app.config.get('MAIL_USE_TLS'),
                'use_ssl': app.config.get('MAIL_USE_SSL')
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/test-smtp-connection')
def test_smtp_connection():
    """Endpoint temporal para probar conexión SMTP"""
    try:
        server = app.config.get('MAIL_SERVER')
        port = app.config.get('MAIL_PORT')
        username = app.config.get('MAIL_USERNAME')
        password = app.config.get('MAIL_PASSWORD')
        
        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales no configuradas'
            })
        
        # Test de conexión
        context = ssl.create_default_context()
        server_smtp = smtplib.SMTP(server, port, timeout=30)
        server_smtp.starttls(context=context)
        server_smtp.login(username, password)
        server_smtp.quit()
        
        return jsonify({
            'status': 'success',
            'message': 'Conexión SMTP exitosa',
            'server': f"{server}:{port}"
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
            'name': 'Test Usuario',
            'email': 'olaya.soriano@gmail.com',
            'skills': 'Testing, Debugging'
        }
        
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
                'from': 'contacto@clmblockchain.org',
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
    app.run(host='0.0.0.0', port=port, debug=True)