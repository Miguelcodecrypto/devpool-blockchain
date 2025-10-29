#!/usr/bin/env python3
"""
Debugging de credenciales SMTP
"""
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()

def debug_credentials():
    """Debug de las credenciales para encontrar caracteres problemáticos"""
    
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    print("=== DEBUG CREDENCIALES SMTP ===")
    print(f"Username: {username}")
    print(f"Username bytes: {username.encode('utf-8') if username else 'None'}")
    print(f"Password length: {len(password) if password else 0}")
    
    if password:
        print(f"Password chars:")
        for i, char in enumerate(password):
            try:
                char.encode('ascii')
                status = "OK"
            except UnicodeEncodeError:
                status = f"PROBLEMA - UTF-8: {char.encode('utf-8')}"
            print(f"  [{i:2d}]: '{char}' - {status}")
    
    print("\n=== SOLUCIONES ===")
    if password:
        # Intentar diferentes codificaciones
        try:
            ascii_safe = password.encode('ascii')
            print("✅ Password es ASCII compatible")
        except UnicodeEncodeError as e:
            print(f"❌ Password NO es ASCII compatible: {e}")
            print("💡 Solución 1: Cambiar password por uno solo ASCII")
            print("💡 Solución 2: Usar encoding adecuado en SMTP")

if __name__ == "__main__":
    debug_credentials()