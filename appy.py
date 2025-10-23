from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for
from flask_mail import Mail, Message
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
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_123')

# ────────────────────────────────────────────────
# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))

# Configuración adicional para evitar timeouts en producción
app.config['MAIL_SUPPRESS_SEND'] = os.environ.get('MAIL_SUPPRESS_SEND', 'False').lower() == 'true'

# Inicializar Flask-Mail solo si está configurado Y en desarrollo
try:
    # Control manual de emails en producción
    enable_emails = os.environ.get('ENABLE_EMAIL', 'False').lower() == 'true'
    is_production = os.environ.get('RENDER') or os.environ.get('PORT', '5000') == '10000'
    
    if is_production and not enable_emails:
        print("🔴 Emails deshabilitados en producción (ENABLE_EMAIL=False)")
        mail = None
    elif app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'):
        mail = Mail(app)
        print("✅ Sistema de email inicializado")
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
        self.client = self._create_client()
    
    def _create_client(self) -> Client:
        """Crea y autentica el cliente de Supabase"""
        if not self.url or not self.key:
            raise ValueError("Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY")
        
        return create_client(self.url, self.key)
    
    def get_table(self, table_name: str):
        """Devuelve referencia a una tabla"""
        return self.client.table(table_name)

# Inicializar conexión a Supabase
supabase_conn = SupabaseConnector()
users_table = supabase_conn.get_table('users')
skills_users_table = supabase_conn.get_table('skills_users')
roles_table = supabase_conn.get_table('roles')
skills_table = supabase_conn.get_table('skills')
developers_table = supabase_conn.get_table('developers')
admin_table = supabase_conn.get_table('admin')

# ────────────────────────────────────────────────
# Configuración de caché
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ────────────────────────────────────────────────
# VALIDACIÓN DE EMAIL
def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

# ────────────────────────────────────────────────
# ENVÍO DE EMAILS
def send_welcome_email(user_name: str, user_email: str, user_skills: str):
    """Envía email de bienvenida al usuario registrado"""
    global mail
    
    # Si mail es None (producción o no configurado), no hacer nada
    if not mail:
        print(f"📧 Email deshabilitado - no se envía email a {user_email}")
        return False
        
    try:
        # Verificar configuración de email antes de intentar enviar
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            print("⚠️ Configuración de email incompleta, saltando envío")
            return False
        
        # Renderizar template de email
        email_html = render_template('emails/welcome_email.html', 
                                    user_name=user_name, 
                                    user_skills=user_skills)
        
        msg = Message(
            subject='🚀 ¡Bienvenido al DevPool Blockchain CLM!',
            recipients=[user_email],
            html=email_html,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Timeout usando threading para compatibilidad multiplataforma
        import threading
        
        email_result = {'success': False, 'error': None}
        
        def send_email_thread():
            try:
                with app.app_context():
                    mail.send(msg)
                email_result['success'] = True
            except Exception as e:
                email_result['error'] = str(e)
        
        # Crear y ejecutar thread con timeout
        thread = threading.Thread(target=send_email_thread)
        thread.start()
        thread.join(timeout=10)  # Timeout de 10 segundos
        
        if thread.is_alive():
            print(f"⏰ Timeout enviando email a {user_email}")
            return False
        
        if email_result['success']:
            print(f"✅ Email de bienvenida enviado a {user_email}")
            return True
        else:
            print(f"❌ Error enviando email a {user_email}: {email_result['error']}")
            return False
        
    except Exception as e:
        print(f"⚠️ Error enviando email a {user_email}: {str(e)}")
        # En producción, no fallar el registro por problemas de email
        return False

def send_admin_notification(user_data: dict):
    """Envía notificación al admin sobre nuevo registro"""
    global mail
    
    # Si mail es None (producción o no configurado), no hacer nada
    if not mail:
        print("📧 Email deshabilitado - no se envía notificación admin")
        return False
        
    try:
        admin_email = os.environ.get('ADMIN_EMAIL')
        # Verificar configuración de email
        if not admin_email or not app.config.get('MAIL_USERNAME'):
            print("⚠️ Email no configurado, saltando notificación admin")
            return False
            
        msg = Message(
            subject=f'🔔 Nuevo registro en DevPool: {user_data.get("name")}',
            recipients=[admin_email],
            html=f'''
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
            ''',
            sender=app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Timeout usando threading para compatibilidad multiplataforma
        import threading
        
        email_result = {'success': False, 'error': None}
        
        def send_email_thread():
            try:
                with app.app_context():
                    mail.send(msg)
                email_result['success'] = True
            except Exception as e:
                email_result['error'] = str(e)
        
        # Crear y ejecutar thread con timeout
        thread = threading.Thread(target=send_email_thread)
        thread.start()
        thread.join(timeout=10)  # Timeout de 10 segundos
        
        if thread.is_alive():
            print(f"⏰ Timeout enviando notificación de admin para {user_data.get('name')}")
            return False
        
        if email_result['success']:
            print(f"✅ Notificación de admin enviada para {user_data.get('name')}")
            return True
        else:
            print(f"❌ Error enviando notificación admin: {email_result['error']}")
            return False
        
    except Exception as e:
        print(f"❌ Error enviando notificación admin: {str(e)}")
        return False

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

        if not all(data.get(field) for field in required_fields):
            return jsonify({'status': 'error', 'message': '🚨 Faltan datos!', 'details': 'Completa todos los campos requeridos'}), 400

        experience = int(data.get('experience_years'))
        if experience < 0:
            return jsonify({'status': 'error', 'message': '🕶️ Ups!', 'details': 'Los años de experiencia no pueden ser negativos'}), 400

        if not is_valid_email(data.get('email')):
            return jsonify({'status': 'error', 'message': '📧 Email inválido!', 'details': 'Usa un formato correcto'}), 400

        # Normalizar la URL de portfolio
        portfolio_url = data.get('portfolio_url') or None
        if portfolio_url:
            if not portfolio_url.startswith(('http://', 'https://')):
                portfolio_url = 'https://' + portfolio_url
        # Obtener IP del usuario
        if request.headers.get('X-Forwarded-For'):
            ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        else:
            ip = request.remote_addr
        if not ip:
            ip = "Sin IP"
        print(f"IP registrada: {ip}")
        developer_data = {
            "name": data.get('name'),
            "email": data.get('email'),
            "skills": data.get('skills'),
            "experience_years": experience,
            "portfolio_url": portfolio_url,
            "location": data.get('location') or None,
            "created_at": datetime.utcnow().isoformat(),
            "ip": ip
        }

        # Insertar en Supabase
        response = developers_table.insert(developer_data).execute()
        if response.data:
            # En producción, no intentar emails para evitar timeouts
            email_sent = False
            admin_notified = False
            
            # Solo enviar emails en desarrollo (cuando mail está disponible)
            if mail:
                print("📧 Intentando enviar emails...")
                print(f"🔧 Mail object disponible: {mail is not None}")
                print(f"🔧 MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
                print(f"🔧 MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
                try:
                    print(f"📤 Enviando email de bienvenida a: {data.get('email')}")
                    email_sent = send_welcome_email(
                        user_name=data.get('name'),
                        user_email=data.get('email'),
                        user_skills=data.get('skills')
                    )
                    print(f"📤 Resultado email bienvenida: {email_sent}")
                    
                    print(f"📤 Enviando notificación admin para: {data.get('name')}")
                    admin_notified = send_admin_notification(developer_data)
                    print(f"📤 Resultado notificación admin: {admin_notified}")
                except Exception as e:
                    print(f"⚠️ Error general en sistema de emails: {str(e)}")
                    import traceback
                    traceback.print_exc()
            else:
                print("📧 Sistema de email deshabilitado - registro exitoso sin envío de emails")
            
            # Obtener el número actualizado de usuarios
            try:
                count_response = developers_table.select('id').execute()
                num_usuarios = len(count_response.data) if count_response and hasattr(count_response, 'data') else 0
            except Exception:
                num_usuarios = 0
                
            # Mensaje de éxito con información del email
            success_message = '🎉 ¡Registro exitoso!'
            if email_sent:
                success_message += ' 📧 Revisa tu email para la bienvenida!'
            
            print(f"🎯 Preparando respuesta - email_sent: {email_sent}, admin_notified: {admin_notified}")
            
            return jsonify({
                'status': 'success',
                'message': success_message,
                'animation': 'confetti',
                'num_usuarios': num_usuarios,
                'email_sent': email_sent,
                'admin_notified': admin_notified
            }), 201
        else:
            error = response.error.message if response.error else "Error desconocido"
            if "duplicate key" in error.lower():
                return jsonify({'status': 'error', 'message': '💥 Email duplicado!', 'details': 'Este correo ya está registrado'}), 409
            return jsonify({'status': 'error', 'message': '🚨 Error en Supabase', 'details': error}), 500

    except Exception as e:
        return jsonify({'status': 'error', 'message': '🚨 Error cósmico!', 'details': str(e)}), 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            # Buscar admin en Supabase
            response = admin_table.select("hashed_password").eq("username", username).execute()
            print("Respuesta Supabase:", response)
            print("Datos:", getattr(response, 'data', None))
        except Exception as e:
            return render_template('admin_login.html', error=f"Error de conexión o tabla: {str(e)}")

        if not response or not hasattr(response, 'data'):
            return render_template('admin_login.html', error='No se pudo consultar la tabla admin.')

        if response.data and len(response.data) > 0:
            admin_record = response.data[0]
            if check_password_hash(admin_record['hashed_password'], password):
                response = redirect(url_for('admin_dashboard'))
                response.set_cookie('admin_logged', 'true', max_age=3600, httponly=True, samesite='Strict')
                return response
            else:
                return render_template('admin_login.html', error='Contraseña incorrecta.')
        else:
            return render_template('admin_login.html', error='Usuario no encontrado o tabla vacía.')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():

    import pytz
    from dateutil import parser
    # Obtener todos los desarrolladores
    response = developers_table.select("*").order("created_at", desc=True).execute()
    developers = response.data
    # Convertir la hora UTC a hora local de España (CET/CEST) respetando horario de verano/invierno
    if developers:
        spain_tz = pytz.timezone('Europe/Madrid')
        for dev in developers:
            created_at = dev.get('created_at')
            if created_at:
                try:
                    dt_utc = parser.isoparse(created_at)
                    if dt_utc.tzinfo is None:
                        dt_utc = pytz.utc.localize(dt_utc)
                    dt_local = dt_utc.astimezone(spain_tz)
                    dev['created_at_local'] = dt_local.strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    dev['created_at_local'] = created_at
        developers = sorted(developers, key=lambda d: d.get('created_at', ''), reverse=True)
    return render_template('admin_dashboard.html', developers=developers)

@app.route('/admin/delete/<string:dev_id>', methods=['POST'])
@admin_required
def delete_developer(dev_id):
    # Eliminar por ID en Supabase
    response = developers_table.delete().eq('id', dev_id).execute()
    
    if response.data and len(response.data) > 0:
        return redirect(url_for('admin_dashboard'))
    else:
        return jsonify({'status': 'error', 'message': 'Desarrollador no encontrado'}), 404

@app.route('/admin/export')
@admin_required
def export_to_json():
    # Obtener todos los desarrolladores
    response = developers_table.select("*").execute()
    developers = response.data

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

@app.route('/health')
def health_check():
    """Endpoint de salud para verificar que la aplicación funciona"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat(),
        'email_system': 'configured' if mail else 'disabled',
        'supabase': 'configured' if os.environ.get('SUPABASE_URL') else 'missing'
    })

# ────────────────────────────────────────────────
if __name__ == '__main__':
    # Configuración para desarrollo y producción
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=port
    )