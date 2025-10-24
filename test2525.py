import smtplib
import ssl
from email.mime.text import MIMEText
import os

def test_smtp_port(host, port, username, password, from_email, to_email):
    """
    Prueba de conexión SMTP en un puerto específico
    """
    print(f"\n{'='*50}")
    print(f"Probando conexión a {host}:{port}")
    print(f"{'='*50}\n")
    
    try:
        # Intentar conexión TLS
        print(f"1. Intentando conexión TLS en puerto {port}...")
        server = smtplib.SMTP(host, port, timeout=10)
        server.ehlo()
        
        print("2. Iniciando STARTTLS...")
        server.starttls()
        server.ehlo()
        
        print("3. Autenticando...")
        server.login(username, password)
        
        print("4. Preparando email de prueba...")
        msg = MIMEText("Este es un email de prueba desde Render - Puerto 2525")
        msg['Subject'] = 'Prueba SMTP Puerto 2525 - Render'
        msg['From'] = from_email
        msg['To'] = to_email
        
        print("5. Enviando email...")
        server.send_message(msg)
        server.quit()
        
        print(f"\n✅ ÉXITO: El puerto {port} funciona correctamente!")
        print(f"✅ Email enviado a {to_email}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ ERROR DE AUTENTICACIÓN: {e}")
        print("Verifica tus credenciales")
        return False
        
    except smtplib.SMTPException as e:
        print(f"\n❌ ERROR SMTP: {e}")
        return False
        
    except ConnectionRefusedError:
        print(f"\n❌ CONEXIÓN RECHAZADA: El puerto {port} está BLOQUEADO")
        return False
        
    except TimeoutError:
        print(f"\n❌ TIMEOUT: No se pudo conectar al puerto {port}")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR INESPERADO: {type(e).__name__}: {e}")
        return False

# Configuración de prueba
if __name__ == "__main__":
    # Configuración para SMTP2GO (compatible con Render)
    SMTP_HOST = os.getenv('SMTP_HOST', 'mail.smtp2go.com')
    SMTP_USER = os.getenv('SMTP_USER', 'tu-usuario-smtp2go')
    SMTP_PASS = os.getenv('SMTP_PASS', 'tu-contraseña-smtp2go')
    FROM_EMAIL = os.getenv('FROM_EMAIL', 'contacto@clmblockchain.org')
    TO_EMAIL = os.getenv('TO_EMAIL', 'martinezsolar@yahoo.es')
    
    print("PRUEBA DE CONECTIVIDAD SMTP EN RENDER")
    print(f"Host: {SMTP_HOST}")
    print(f"Usuario: {SMTP_USER}")
    print(f"Desde: {FROM_EMAIL}")
    print(f"Para: {TO_EMAIL}")
    
    # Probar puerto 2525
    result_2525 = test_smtp_port(
        SMTP_HOST, 
        2525, 
        SMTP_USER, 
        SMTP_PASS, 
        FROM_EMAIL, 
        TO_EMAIL
    )
    
    # Opcional: comparar con puerto 587 (debería fallar en Render free)
    print(f"\n\n{'='*50}")
    print("COMPARACIÓN: Probando puerto 587 (debería FALLAR)")
    print(f"{'='*50}")
    result_587 = test_smtp_port(
        SMTP_HOST, 
        587, 
        SMTP_USER, 
        SMTP_PASS, 
        FROM_EMAIL, 
        TO_EMAIL
    )
    
    # Resumen
    print(f"\n\n{'='*50}")
    print("RESUMEN DE PRUEBAS")
    print(f"{'='*50}")
    print(f"Puerto 2525: {'✅ FUNCIONA' if result_2525 else '❌ BLOQUEADO'}")
    print(f"Puerto 587:  {'✅ FUNCIONA' if result_587 else '❌ BLOQUEADO'}")
    print(f"{'='*50}\n")