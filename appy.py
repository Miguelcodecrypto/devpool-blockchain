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
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback_secret_key')

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

@app.route('/admin/delete/<string:dev_id>', methods=['POST'])
@admin_required
def delete_developer(dev_id):
    """Eliminar desarrollador por ID"""
    try:
        print(f"🗑️ Intentando eliminar desarrollador con ID: {dev_id}")
        
        # Eliminar por ID en Supabase
        response = developers_table.delete().eq('id', dev_id).execute()
        
        if response.data:
            print(f"✅ Desarrollador {dev_id} eliminado exitosamente")
            return redirect(url_for('admin_dashboard'))
        else:
            print(f"❌ No se encontró desarrollador con ID: {dev_id}")
            return jsonify({'error': 'Desarrollador no encontrado'}), 404
            
    except Exception as e:
        print(f"❌ Error eliminando desarrollador: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

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