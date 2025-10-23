# 📧 Configuración SMTP para contacto@clmblockchain.org

## Obtener Configuración desde Thunderbird

### Paso 1: Abrir Configuración de Cuenta en Thunderbird
1. Abre Thunderbird
2. Ve a **Herramientas** → **Configuración de cuenta**
3. Selecciona la cuenta `contacto@clmblockchain.org`
4. Ve a **Configuración del servidor de salida (SMTP)**

### Paso 2: Anotar la Configuración SMTP
Busca y anota estos valores:

```
Servidor: ___________________ (ej: smtp.clmblockchain.org)
Puerto: __________________ (común: 587, 465, o 25)
Seguridad: ________________ (TLS/STARTTLS o SSL/TLS)
Autenticación: _____________ (Contraseña normal, OAuth2, etc.)
Nombre de usuario: ________ (debería ser contacto@clmblockchain.org)
```

## Configuraciones Comunes según Proveedor

### Si clmblockchain.org usa Google Workspace:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
```

### Si clmblockchain.org usa Microsoft 365:
```env
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
```

### Si clmblockchain.org usa cPanel/Hosting personalizado:
```env
MAIL_SERVER=mail.clmblockchain.org
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
```

### Si usa SSL en puerto 465:
```env
MAIL_SERVER=smtp.clmblockchain.org
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
```

## Paso 3: Actualizar el archivo .env

Una vez tengas la configuración correcta, actualiza estos valores en `.env`:

```env
MAIL_SERVER=el_servidor_smtp_correcto
MAIL_PORT=el_puerto_correcto
MAIL_USE_TLS=True_o_False
MAIL_USE_SSL=True_o_False
MAIL_USERNAME=contacto@clmblockchain.org
MAIL_PASSWORD=la_contraseña_del_email
```

## Paso 4: Probar la Configuración

Ejecuta la aplicación y registra un usuario de prueba para verificar que los emails se envían correctamente.

```bash
python appy.py
```

## Troubleshooting

### Error de autenticación:
- Verifica usuario y contraseña
- Algunos servidores requieren contraseñas de aplicación específicas

### Error de conexión:
- Verifica el servidor SMTP y puerto
- Comprueba configuración TLS/SSL
- Revisa firewall/antivirus

### Email no llega:
- Revisa carpeta de spam
- Verifica que el servidor permita envío desde aplicaciones externas