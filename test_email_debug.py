#!/usr/bin/env python3
"""
Test completo del sistema de email con debugging detallado
"""
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def test_smtp_connection():
    """Test completo de conexión SMTP2GO"""
    print("🔧 INICIANDO TEST DE EMAIL COMPLETO")
    print("=" * 50)
    
    # Configuración
    server = os.environ.get('MAIL_SERVER', 'mail.smtp2go.com')
    port = int(os.environ.get('MAIL_PORT', 2525))
    username = os.environ.get('MAIL_USERNAME')
    password = os.environ.get('MAIL_PASSWORD')
    
    print(f"📧 Servidor: {server}:{port}")
    print(f"👤 Usuario: {username}")
    print(f"🔑 Password: {'***' if password else 'NO CONFIGURADO'}")
    print()
    
    if not username or not password:
        print("❌ CREDENCIALES NO CONFIGURADAS")
        return False
    
    try:
        # Crear mensaje de prueba
        message = MIMEMultipart("alternative")
        message["Subject"] = "🧪 Test DevPool Email System"
        message["From"] = "contacto@clmblockchain.org"
        message["To"] = "miguelcodecrypto@gmail.com"  # Email de prueba
        
        html_content = """
        <html>
          <body>
            <h2>🧪 Test de Email DevPool</h2>
            <p>Si recibes este email, el sistema funciona correctamente.</p>
            <p><strong>Servidor:</strong> SMTP2GO</p>
            <p><strong>Dominio:</strong> clmblockchain.org verificado</p>
          </body>
        </html>
        """
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        print("🔗 Conectando a SMTP2GO...")
        
        # Conectar con TLS
        context = ssl.create_default_context()
        server_smtp = smtplib.SMTP(server, port, timeout=30)
        
        print("🔧 Iniciando STARTTLS...")
        server_smtp.starttls(context=context)
        
        print("🔑 Autenticando...")
        server_smtp.login(username, password)
        
        print("📤 Enviando mensaje de prueba...")
        server_smtp.send_message(message)
        
        print("🔚 Cerrando conexión...")
        server_smtp.quit()
        
        print("✅ ¡EMAIL DE PRUEBA ENVIADO EXITOSAMENTE!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    test_smtp_connection()