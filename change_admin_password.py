#!/usr/bin/env python3
"""
🔐 Script para gestión de contraseñas de administrador - DevPool ABCLM
Permite cambiar la contraseña del admin de forma segura
"""

import os
import getpass
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from supabase import create_client

# Cargar variables de entorno
load_dotenv()

def main():
    print("🔐 GESTIÓN DE CONTRASEÑA ADMIN - DevPool ABCLM")
    print("=" * 50)
    
    # Configurar cliente Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Variables de entorno SUPABASE_URL y SUPABASE_KEY no configuradas")
        return
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Solicitar nueva contraseña
    print("\n📝 Ingrese la nueva contraseña para el administrador:")
    new_password = getpass.getpass("Nueva contraseña: ")
    
    if len(new_password) < 8:
        print("❌ La contraseña debe tener al menos 8 caracteres")
        return
    
    confirm_password = getpass.getpass("Confirmar contraseña: ")
    
    if new_password != confirm_password:
        print("❌ Las contraseñas no coinciden")
        return
    
    # Generar hash seguro
    hashed_password = generate_password_hash(new_password)
    
    try:
        # Actualizar contraseña en Supabase
        admin_table = supabase.table('admin')
        
        # Verificar si existe el admin
        check_response = admin_table.select('id').eq('username', 'admin').execute()
        
        if check_response.data:
            # Actualizar contraseña existente
            update_response = admin_table.update({
                'hashed_password': hashed_password
            }).eq('username', 'admin').execute()
            
            if update_response.data:
                print("✅ Contraseña actualizada exitosamente")
            else:
                print("❌ Error actualizando la contraseña")
        else:
            # Crear nuevo admin
            insert_response = admin_table.insert({
                'username': 'admin',
                'hashed_password': hashed_password
            }).execute()
            
            if insert_response.data:
                print("✅ Administrador creado exitosamente")
            else:
                print("❌ Error creando el administrador")
                
    except Exception as e:
        print(f"❌ Error conectando con la base de datos: {e}")

if __name__ == "__main__":
    main()