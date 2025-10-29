#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba SMTP simplificado
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def test_smtp_simple():
    """Prueba SMTP básica sin caracteres especiales"""
    
    server = os.getenv('MAIL_SERVER', 'smtp.panel247.com')
    port = int(os.getenv('MAIL_PORT', 587))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    print(f"SMTP Test: {server}:{port}")
    print(f"Usuario: {username}")
    print(f"Password configurado: {'Si' if password else 'No'}")
    
    if not username or not password:
        print("ERROR: Credenciales no configuradas")
        return False
    
    try:
        # Crear mensaje básico
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = username
        msg['Subject'] = "Test Email DevPool"
        
        # Contenido simple sin caracteres especiales
        body = "Este es un test basico de email del sistema DevPool."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        print("Conectando al servidor SMTP...")
        
        # Conexión SMTP
        context = ssl.create_default_context()
        with smtplib.SMTP(server, port) as smtp_server:
            print("Iniciando TLS...")
            smtp_server.starttls(context=context)
            
            print("Autenticando...")
            smtp_server.login(username, password)
            
            print("Enviando email...")
            smtp_server.send_message(msg)
            
        print("SUCCESS: Email enviado correctamente!")
        return True
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        # Información adicional de debugging
        if hasattr(e, 'smtp_code'):
            print(f"SMTP Code: {e.smtp_code}")
        if hasattr(e, 'smtp_error'):
            print(f"SMTP Error: {e.smtp_error}")
        return False

if __name__ == "__main__":
    test_smtp_simple()