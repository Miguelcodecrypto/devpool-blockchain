#!/usr/bin/env python3
"""
Test de credenciales SMTP2GO desde variables de entorno de Render
"""
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def test_render_smtp():
    """Test usando las variables de entorno de Render"""
    print("🔧 TEST DE CREDENCIALES SMTP2GO DESDE RENDER")
    print("=" * 50)
    
    # Configuración desde variables de entorno
    server = os.environ.get('MAIL_SERVER', 'mail.smtp2go.com')
    port = int(os.environ.get('MAIL_PORT', 2525))
    username = os.environ.get('MAIL_USERNAME')
    password = os.environ.get('MAIL_PASSWORD')
    
    print(f"📧 Servidor: {server}:{port}")
    print(f"👤 Usuario: {username if username else 'NO CONFIGURADO'}")
    print(f"🔑 Password: {'***CONFIGURADO***' if password else 'NO CONFIGURADO'}")
    print()
    
    if not username or not password:
        print("❌ CREDENCIALES NO ENCONTRADAS EN VARIABLES DE ENTORNO")
        print("💡 Verifica que MAIL_USERNAME y MAIL_PASSWORD estén en Render")
        return False
    
    try:
        print("🔗 Conectando a SMTP2GO...")
        
        # Crear conexión con timeout
        context = ssl.create_default_context()
        server_smtp = smtplib.SMTP(server, port, timeout=30)
        
        print("🔧 Iniciando STARTTLS...")
        server_smtp.starttls(context=context)
        
        print("🔑 Autenticando con credenciales de Render...")
        server_smtp.login(username, password)
        
        print("✅ ¡AUTENTICACIÓN EXITOSA!")
        
        # Cerrar conexión
        server_smtp.quit()
        print("🔚 Conexión cerrada correctamente")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ ERROR DE AUTENTICACIÓN: {e}")
        print("💡 Verifica que las credenciales en Render sean correctas")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    test_render_smtp()