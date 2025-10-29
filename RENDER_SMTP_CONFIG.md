# 🔧 CONFIGURACIÓN CORRECTA DE SMTP PARA RENDER

## ✅ **CONFIGURACIÓN VALIDADA:**

### **Variables de entorno para Render (Environment):**

```env
# Base de datos
SUPABASE_URL=https://cjynpeeknghtbpdrtnwg.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNqeW5wZWVrbmdodGJwZHJ0bndnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTExNDM3NiwiZXhwIjoyMDY0NjkwMzc2fQ.3FxF_lCqIlVe7AxVCLG8CecMt7Q7-gPo73ZkBS2w7Lg

# Seguridad
SECRET_KEY=tu_clave_secreta_super_segura_123
FLASK_DEBUG=False

# Email DonDominio (FUNCIONANDO)
MAIL_SERVER=smtp.panel247.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=contacto@clmblockchain.org
MAIL_PASSWORD=CLM$YearEmail2025
MAIL_DEFAULT_SENDER=contacto@clmblockchain.org
ADMIN_EMAIL=contacto@clmblockchain.org
```

## 📋 **NOTAS IMPORTANTES:**

### **Puerto 587 vs 2525:**
- ✅ **Puerto 587** - DonDominio (smtp.panel247.com) - **FUNCIONA**
- ❌ **Puerto 2525** - SMTP2GO (mail.smtp2go.com) - **NO es para DonDominio**

### **Si Render bloquea puerto 587:**
**Alternativa con SMTP2GO:**
```env
MAIL_SERVER=mail.smtp2go.com
MAIL_PORT=2525
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=tu_usuario_smtp2go
MAIL_PASSWORD=tu_password_smtp2go
```

## 🚀 **CONFIGURACIÓN FINAL PARA RENDER:**

Usar **DonDominio puerto 587** que ya está funcionando localmente.

Si hay problemas en Render, cambiar a **SMTP2GO puerto 2525**.

---
**Status:** ✅ Configuración correcta identificada