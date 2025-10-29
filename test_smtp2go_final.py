#!/usr/bin/env python3
"""
Test final de SMTP2GO con dominio verificado
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

def test_smtp2go_verified():
    load_dotenv()
    
    print("🧪 TEST FINAL SMTP2GO - DOMINIO VERIFICADO")
    print("=" * 50)
    
    # Configuración
    server = 'mail.smtp2go.com'
    port = 2525
    username = os.getenv('MAIL_USERNAME')  # clmblockchain.org
    password = os.getenv('MAIL_PASSWORD')  # s6JDYQGFne8UGvg4
    from_email = 'contacto@clmblockchain.org'  # Email completo verificado
    to_email = 'contacto@clmblockchain.org'
    
    print(f"📧 Servidor: {server}:{port}")
    print(f"🔑 Usuario: {username}")
    print(f"📨 From: {from_email}")
    print(f"📬 To: {to_email}")
    print()
    
    try:
        # Crear mensaje
        msg = MIMEText("¡Test exitoso! El dominio clmblockchain.org está verificado en SMTP2GO y los emails funcionan correctamente.")
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = '✅ DevPool - Dominio Verificado en SMTP2GO'
        
        print("🔗 Conectando a SMTP2GO...")
        context = ssl.create_default_context()
        smtp_server = smtplib.SMTP(server, port, timeout=30)
        
        print("🔧 Iniciando STARTTLS...")
        smtp_server.starttls(context=context)
        
        print("🔑 Autenticando...")
        smtp_server.login(username, password)
        
        print("📤 Enviando email...")
        smtp_server.send_message(msg)
        smtp_server.quit()
        
        print()
        print("🎉 ¡EMAIL ENVIADO EXITOSAMENTE!")
        print("✅ Dominio verificado y funcionando")
        print("✅ SMTP2GO configurado correctamente")
        return True
        
    except smtplib.SMTPSenderRefused as e:
        if '550' in str(e) and 'not verified' in str(e):
            print(f"❌ ERROR: {e}")
            print("💡 El dominio aún no está verificado en SMTP2GO")
            print("💡 Espera unos minutos más y vuelve a intentar")
            return False
        else:
            print(f"❌ ERROR: {e}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    test_smtp2go_verified()