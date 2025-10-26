from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
from datetime import datetime, timedelta
import re
import json
import os
import uuid
import secrets
import time
from collections import defaultdict
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

# 🔐 CONFIGURACIÓN DE SEGURIDAD BÁSICA (sin dependencias externas)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

# Configuración básica de cookies seguras
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
)

# 📊 Sistema básico de monitoreo de intentos fallidos (en memoria)
failed_attempts = defaultdict(list)
blocked_ips = defaultdict(float)

def get_remote_address():
    """Obtener IP del cliente (versión básica)"""
    return request.environ.get('HTTP_X_FORWARDED_FOR') or request.environ.get('REMOTE_ADDR') or '127.0.0.1'

def is_ip_blocked(ip):
    """Verificar si una IP está bloqueada temporalmente"""
    if ip in blocked_ips:
        if time.time() < blocked_ips[ip]:
            return True
        else:
            del blocked_ips[ip]
    return False

def record_failed_attempt(ip):
    """Registrar intento fallido y bloquear si es necesario"""
    current_time = time.time()
    
    # Limpiar intentos antiguos (más de 15 minutos)
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip]
        if current_time - attempt_time < 900
    ]
    
    # Añadir nuevo intento
    failed_attempts[ip].append(current_time)
    
    # Bloquear si hay 5 o más intentos en 15 minutos
    if len(failed_attempts[ip]) >= 5:
        blocked_ips[ip] = current_time + 900
        return True
    
    return False

def log_security_event(event_type, details, ip=None):
    """Registrar eventos de seguridad"""
    timestamp = datetime.now().isoformat()
    ip = ip or get_remote_address()
    print(f"🚨 [SECURITY] {timestamp} - {event_type} - IP: {ip} - {details}")

print("🔧 Versión básica de seguridad iniciada (sin Flask-Limiter)")
print("🔍 Para versión completa, instalar: pip install Flask-Limiter Flask-WTF")

if __name__ == '__main__':
    print("🚀 Servidor de prueba iniciado en modo básico")
    print("📝 Accede a: http://localhost:5000")
    print("👤 Admin: http://localhost:5000/admin/login")
    app.run(debug=True, port=5000)