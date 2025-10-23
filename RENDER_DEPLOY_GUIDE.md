# 🚀 Guía de Despliegue en Render

## Problemas Identificados y Soluciones

### ✅ 1. Archivo Procfile Creado
**Problema**: Render necesita saber cómo ejecutar la aplicación
**Solución**: Creado `Procfile` con:
```
web: gunicorn appy:app
```

### ✅ 2. Debug Mode Corregido
**Problema**: Debug hardcodeado como True
**Solución**: Cambiado a usar variable de entorno `FLASK_DEBUG`

### ✅ 3. Gunicorn en Requirements
**Problema**: Faltaba servidor WSGI para producción
**Solución**: Gunicorn ya está en requirements.txt

## 🔧 Configuración Requerida en Render

### Variables de Entorno Necesarias:

```env
# Supabase (OBLIGATORIAS)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_KEY=tu_service_role_key

# Flask
SECRET_KEY=una_clave_secreta_muy_segura
FLASK_DEBUG=False

# Email (OBLIGATORIAS para que funcione el envío)
MAIL_SERVER=smtp.panel247.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=contacto@clmblockchain.org
MAIL_PASSWORD=tu_password_real
MAIL_DEFAULT_SENDER=contacto@clmblockchain.org
ADMIN_EMAIL=contacto@clmblockchain.org

# Puerto (opcional, Render lo maneja automáticamente)
PORT=10000
```

## 📋 Pasos para Configurar en Render

### 1. En tu Dashboard de Render:
- Ve a tu servicio web
- Clic en "Environment"
- Añade todas las variables de arriba

### 2. Especialmente Importante:
- **SUPABASE_URL**: Desde tu dashboard de Supabase
- **SUPABASE_KEY**: Service Role Key (no la anon key)
- **MAIL_PASSWORD**: La contraseña real del email

### 3. Deploy Settings:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: Se lee automáticamente del Procfile

## 🔍 Debugging en Render

### Ver Logs:
1. Ve a tu servicio en Render
2. Clic en "Logs"
3. Busca errores como:
   - `ModuleNotFoundError`
   - `Connection refused`
   - `Authentication failed`

### Errores Comunes:

#### Error: "No module named 'xyz'"
- Verificar que todas las dependencias están en requirements.txt

#### Error: "Connection to database failed"
- Verificar SUPABASE_URL y SUPABASE_KEY

#### Error: "Email authentication failed"
- Verificar MAIL_USERNAME y MAIL_PASSWORD

#### Error: 503 Service Unavailable
- Verificar que Procfile existe y está correcto

## 🧪 Test de Variables de Entorno

Puedes añadir esta ruta temporal para verificar configuración:

```python
@app.route('/test-config')
def test_config():
    return {
        'supabase_configured': bool(os.environ.get('SUPABASE_URL')),
        'mail_configured': bool(os.environ.get('MAIL_USERNAME')),
        'debug_mode': os.environ.get('FLASK_DEBUG', 'False'),
        'port': os.environ.get('PORT', '5000')
    }
```

## 🔄 Redeployment

Después de configurar las variables:
1. Ve a tu servicio en Render
2. Clic en "Manual Deploy" → "Deploy latest commit"
3. Monitorea los logs durante el deploy

## ✅ Verificación Final

La aplicación debería:
1. ✅ Iniciar sin errores
2. ✅ Conectar a Supabase
3. ✅ Mostrar la página principal
4. ✅ Permitir registros de usuarios
5. ✅ Enviar emails (si están configurados)