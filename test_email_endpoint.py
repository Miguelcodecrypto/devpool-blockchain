#!/usr/bin/env python3
"""
Endpoint de testing para verificar email en producción
"""
from flask import Flask, jsonify
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

app = Flask(__name__)

@app.route('/test-email')
def test_email_endpoint():
    """Endpoint para probar email en producción"""
    try:
        # Configuración
        server = os.environ.get('MAIL_SERVER', 'mail.smtp2go.com')
        port = int(os.environ.get('MAIL_PORT', 2525))
        username = os.environ.get('MAIL_USERNAME')
        password = os.environ.get('MAIL_PASSWORD')
        
        # Verificar credenciales
        if not username or not password:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales no configuradas',
                'details': {
                    'server': server,
                    'port': port,
                    'username': bool(username),
                    'password': bool(password)
                }
            })
        
        # Test de conexión
        context = ssl.create_default_context()
        server_smtp = smtplib.SMTP(server, port, timeout=30)
        server_smtp.starttls(context=context)
        server_smtp.login(username, password)
        server_smtp.quit()
        
        return jsonify({
            'status': 'success',
            'message': 'Conexión SMTP exitosa',
            'details': {
                'server': server,
                'port': port,
                'username': username
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        })

if __name__ == '__main__':
    app.run(debug=True)