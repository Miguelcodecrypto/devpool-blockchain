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
app.secret_key = os.environ.get('SECRET_KEY', 'clave_secreta_123')

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

        developer_data = {
            "name": data.get('name'),
            "email": data.get('email'),
            "skills": data.get('skills'),
            "experience_years": experience,
            "portfolio_url": data.get('portfolio_url') or None,
            "location": data.get('location') or None,
            "created_at": datetime.utcnow().isoformat()
        }

        # Insertar en Supabase
        response = developers_table.insert(developer_data).execute()
        
        if response.data:
            return jsonify({
                'status': 'success', 
                'message': '🎉 ¡Registro exitoso!',
                'animation': 'confetti'
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
    # Obtener todos los desarrolladores
    response = developers_table.select("*").order("created_at", desc=True).execute()
    developers = response.data
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

# ────────────────────────────────────────────────
if __name__ == '__main__':
    # Configuración importante para producción
    debug_mode = True  # Activar modo debug siempre
    port = int(os.environ.get('PORT', 5000))
    app.run(
        debug=debug_mode,
        host='0.0.0.0',
        port=port
    )