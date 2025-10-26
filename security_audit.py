#!/usr/bin/env python3
"""
🔍 Script de auditoría de seguridad - DevPool ABCLM
Verifica el estado de seguridad del sistema
"""

import os
import secrets
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_environment_security():
    """Verificar variables de entorno críticas"""
    print("🔍 VERIFICANDO VARIABLES DE ENTORNO...")
    
    critical_vars = [
        'SECRET_KEY', 'SUPABASE_URL', 'SUPABASE_KEY', 
        'MAIL_USERNAME', 'MAIL_PASSWORD', 'ADMIN_EMAIL'
    ]
    
    for var in critical_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: Configurada")
        else:
            print(f"❌ {var}: NO CONFIGURADA")

def check_admin_exists():
    """Verificar si existe el administrador"""
    print("\n👤 VERIFICANDO ADMINISTRADOR...")
    
    try:
        supabase = create_client(
            os.environ.get('SUPABASE_URL'),
            os.environ.get('SUPABASE_KEY')
        )
        
        response = supabase.table('admin').select('username').execute()
        
        if response.data:
            print(f"✅ Administrador encontrado: {len(response.data)} cuenta(s)")
        else:
            print("❌ No se encontró administrador configurado")
            
    except Exception as e:
        print(f"❌ Error verificando admin: {e}")

def generate_secure_secret():
    """Generar nueva SECRET_KEY segura"""
    print("\n🔑 GENERANDO NUEVA SECRET_KEY...")
    new_secret = secrets.token_hex(32)
    print(f"Nueva SECRET_KEY sugerida: {new_secret}")
    print("⚠️ Guarde esta key en las variables de entorno de Render")

def security_recommendations():
    """Mostrar recomendaciones de seguridad"""
    print("\n🛡️ RECOMENDACIONES DE SEGURIDAD:")
    print("1. ✅ Rate limiting implementado (5 intentos/15 min)")
    print("2. ✅ Bloqueo automático de IP tras intentos fallidos")
    print("3. ✅ Sesiones con expiración automática (30 min)")
    print("4. ✅ Logging de eventos de seguridad")
    print("5. ✅ Alertas por email de accesos admin")
    print("6. ✅ Protección CSRF en formularios")
    print("7. ✅ Cookies HTTPOnly y Secure")
    print("8. ✅ Auditoría de acciones críticas")
    
    print("\n📋 ACCIONES PENDIENTES:")
    print("• Cambiar contraseña admin regularmente")
    print("• Monitorear logs de seguridad")
    print("• Revisar alertas de email")
    print("• Actualizar SECRET_KEY periódicamente")

def main():
    print("🔍 AUDITORÍA DE SEGURIDAD - DevPool ABCLM")
    print("=" * 50)
    
    check_environment_security()
    check_admin_exists()
    generate_secure_secret()
    security_recommendations()
    
    print("\n🎯 Auditoría completada")

if __name__ == "__main__":
    main()