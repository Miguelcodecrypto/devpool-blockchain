#!/usr/bin/env python3
"""
Script de prueba para DonDominio SMTP
"""
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def test_dondominio_smtp():
    """Prueba conexión directa a DonDominio"""
    
    server = os.getenv('MAIL_SERVER', 'smtp.panel247.com')
    port = int(os.getenv('MAIL_PORT', 587))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    use_tls = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    use_ssl = os.getenv('MAIL_USE_SSL', 'False').lower() == 'true'
    
    print(f"🧪 PRUEBA DE DONDOMINIO SMTP")
    print(f"📧 Servidor: {server}:{port}")
    print(f"📧 Usuario: {username}")
    print(f"🔑 Password: {'Sí' if password else 'No'} ({len(password or '')} chars)")
    print(f"🔒 TLS: {use_tls}, SSL: {use_ssl}")
    
    if not username or not password:
        print("❌ Variables de entorno no configuradas")
        return False
    
    try:
        # Crear mensaje de prueba
        message = MIMEMultipart("alternative")
        message["Subject"] = "🧪 Test DevPool DonDominio"
        message["From"] = username
        message["To"] = username  # Enviar a nosotros mismos
        
        html_content = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">🧪 Prueba de Email DonDominio</h2>
            <p>Este es un email de prueba del sistema DevPool con DonDominio.</p>
            <p><strong>Estado:</strong> ✅ Sistema funcionando correctamente</p>
            <p><strong>Servidor:</strong> smtp.panel247.com</p>
            <p><strong>Fecha:</strong> 2025-10-24</p>
        </div>
        """
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        print("🔗 Conectando a DonDominio...")
        
        if use_ssl:
            # Conexión SSL (puerto 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, context=context) as smtp_server:
                print("🔐 Autenticando con SSL...")
                smtp_server.login(username, password)
                
                print("📤 Enviando email...")
                text = message.as_string()
                smtp_server.sendmail(username, username, text)
        else:
            # Conexión TLS (puerto 587)
            with smtplib.SMTP(server, port) as smtp_server:
                if use_tls:
                    print("🔐 Iniciando TLS...")
                    smtp_server.starttls()
                
                print("🔐 Autenticando...")
                smtp_server.login(username, password)
                
                print("📤 Enviando email...")
                text = message.as_string()
                smtp_server.sendmail(username, username, text)
                
        print("✅ ¡Email DonDominio enviado exitosamente!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    test_dondominio_smtp()