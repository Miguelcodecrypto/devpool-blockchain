#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test SMTP con manejo de encoding UTF-8
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def test_smtp_utf8():
    """Prueba SMTP con manejo correcto de UTF-8"""
    
    server = os.getenv('MAIL_SERVER', 'smtp.panel247.com')
    port = int(os.getenv('MAIL_PORT', 587))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    print(f"SMTP UTF-8 Test: {server}:{port}")
    print(f"Usuario: {username}")
    
    if not username or not password:
        print("ERROR: Credenciales no configuradas")
        return False
    
    try:
        # Crear mensaje básico
        msg = MIMEMultipart()
        msg['From'] = username
        msg['To'] = username  
        msg['Subject'] = "Test DevPool - UTF8"
        
        body = "Email de prueba desde DevPool CLM."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        print("Conectando al servidor SMTP...")
        
        # Crear contexto SSL
        context = ssl.create_default_context()
        
        # Conexión SMTP con manejo de encoding
        server_smtp = smtplib.SMTP(server, port)
        server_smtp.starttls(context=context)
        
        print("Autenticando con encoding UTF-8...")
        # Intentar login con diferentes approaches
        try:
            # Método 1: Login directo
            server_smtp.login(username, password)
        except UnicodeEncodeError:
            print("Método 1 falló, probando método 2...")
            # Método 2: Convertir a bytes
            username_bytes = username.encode('utf-8')
            password_bytes = password.encode('utf-8')
            server_smtp.login(username_bytes, password_bytes)
        except Exception as e:
            print(f"Método 2 falló: {e}")
            # Método 3: Solo ASCII (reemplazar caracteres problemáticos)
            password_ascii = password.replace('Ñ', 'N').replace('ñ', 'n')
            print("Probando con conversión ASCII...")
            server_smtp.login(username, password_ascii)
        
        print("Enviando email...")
        server_smtp.send_message(msg)
        server_smtp.quit()
        
        print("✅ SUCCESS: Email enviado correctamente!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    test_smtp_utf8()