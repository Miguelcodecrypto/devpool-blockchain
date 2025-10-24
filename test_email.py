#!/usr/bin/env python3
"""
Script de prueba rápida para Gmail SMTP directo
"""
import smtplib
import ssl
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def test_gmail_smtp():
    """Prueba conexión directa a Gmail"""
    
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    print(f"🧪 PRUEBA DE GMAIL SMTP")
    print(f"📧 Usuario: {username}")
    print(f"🔑 Password: {'Sí' if password else 'No'} ({len(password or '')} chars)")
    
    if not username or not password:
        print("❌ Variables de entorno no configuradas")
        return False
    
    try:
        # Crear mensaje de prueba
        message = MIMEMultipart("alternative")
        message["Subject"] = "🧪 Test DevPool Email System"
        message["From"] = username
        message["To"] = username  # Enviar a nosotros mismos
        
        html_content = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #6366f1;">🧪 Prueba de Email</h2>
            <p>Este es un email de prueba del sistema DevPool.</p>
            <p><strong>Estado:</strong> ✅ Sistema funcionando correctamente</p>
            <p><strong>Fecha:</strong> {}</p>
        </div>
        """.format("2025-10-24 11:00")
        
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Configurar timeout
        original_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(15)
        
        print("🔗 Conectando a Gmail...")
        
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=15) as server:
                print("🔐 Autenticando...")
                server.login(username, password)
                
                print("📤 Enviando email...")
                text = message.as_string()
                server.sendmail(username, username, text)
                
            print("✅ ¡Email enviado exitosamente!")
            return True
            
        finally:
            socket.setdefaulttimeout(original_timeout)
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    test_gmail_smtp()