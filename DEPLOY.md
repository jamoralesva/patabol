# Guía de Despliegue: PATABOL Bot de WhatsApp

Esta guía te llevará paso a paso para desplegar el bot de PATABOL en WhatsApp usando Twilio y Railway.

## Prerrequisitos

- Cuenta de GitHub (para conectar el repositorio)
- Cuenta de Twilio (gratis para empezar)
- Cuenta de Railway (plan gratuito disponible)

## Paso 1: Configurar Twilio

### 1.1 Crear cuenta en Twilio

1. Ve a [twilio.com](https://www.twilio.com) y crea una cuenta
2. Verifica tu número de teléfono
3. Completa el proceso de verificación

### 1.2 Obtener número de WhatsApp

**Opción A: Sandbox (para pruebas)**

1. En el dashboard de Twilio, ve a **Messaging** > **Try it out** > **Send a WhatsApp message**
2. Sigue las instrucciones para unirte al sandbox
3. Envía el código de unión al número que Twilio te proporciona
4. Anota el número de WhatsApp de Twilio (formato: `whatsapp:+14155238886`)

**Opción B: Número aprobado (para producción)**

1. Ve a **Messaging** > **Settings** > **WhatsApp Sandbox Settings**
2. Solicita un número de WhatsApp aprobado (puede tomar algunos días)
3. Una vez aprobado, tendrás tu número de WhatsApp

### 1.3 Obtener credenciales

1. En el dashboard de Twilio, ve a **Settings** > **General**
2. Copia tu **Account SID** y **Auth Token**
3. Guárdalos de forma segura (los necesitarás más tarde)

## Paso 2: Preparar el código

### 2.1 Verificar archivos

Asegúrate de tener estos archivos en tu repositorio:

```
minibol/
├── patabol.py          # Lógica de dominio
├── cli.py              # CLI local
├── whatsapp_bot.py     # Bot de WhatsApp
├── requirements.txt    # Dependencias
├── Procfile            # Para Railway
├── runtime.txt         # Versión de Python
└── README.md
```

### 2.2 Probar localmente (opcional)

1. Instala las dependencias:
```bash
pip install -r requirements.txt
```

2. Crea un archivo `.env` con tus credenciales:
```env
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
PORT=5000
```

3. Instala ngrok para probar el webhook localmente:
```bash
# macOS
brew install ngrok

# O descarga desde https://ngrok.com
```

4. Inicia el servidor Flask:
```bash
python whatsapp_bot.py
```

5. En otra terminal, inicia ngrok:
```bash
ngrok http 5000
```

6. Copia la URL HTTPS de ngrok (ej: `https://abc123.ngrok.io`)

7. En Twilio, configura el webhook temporal:
   - Ve a **Messaging** > **Settings** > **WhatsApp Sandbox Settings**
   - En "When a message comes in", pega: `https://shaftlike-brittany-jellied.ngrok-free.dev/webhook`
   - Guarda los cambios

8. Prueba enviando un mensaje a tu número de Twilio WhatsApp con: `/ayuda`

## Paso 3: Desplegar en Railway

### 3.1 Crear cuenta en Railway

1. Ve a [railway.app](https://railway.app)
2. Inicia sesión con GitHub
3. Autoriza Railway para acceder a tus repositorios

### 3.2 Crear nuevo proyecto

1. En el dashboard de Railway, haz clic en **New Project**
2. Selecciona **Deploy from GitHub repo**
3. Elige tu repositorio `minibol`
4. Railway detectará automáticamente que es un proyecto Python

### 3.3 Configurar variables de entorno

1. En tu proyecto de Railway, ve a **Variables**
2. Agrega las siguientes variables:

```
TWILIO_ACCOUNT_SID=tu_account_sid_aqui
TWILIO_AUTH_TOKEN=tu_auth_token_aqui
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

**Nota:** No necesitas configurar `PORT`, Railway lo proporciona automáticamente.

### 3.4 Configurar el servicio

1. Railway debería detectar automáticamente el `Procfile`
2. Si no, ve a **Settings** > **Deploy** y configura:
   - **Start Command:** `gunicorn whatsapp_bot:app --bind 0.0.0.0:$PORT`

### 3.5 Obtener URL pública

1. En tu proyecto de Railway, ve a **Settings** > **Networking**
2. Haz clic en **Generate Domain** o usa el dominio proporcionado
3. Copia la URL (ej: `https://patabol-production.up.railway.app`)

## Paso 4: Configurar webhook en Twilio

1. Ve al dashboard de Twilio
2. Ve a **Messaging** > **Settings** > **WhatsApp Sandbox Settings**
3. En "When a message comes in", pega tu URL de Railway:
   ```
   https://tu-app.railway.app/webhook
   ```
4. Guarda los cambios

## Paso 5: Verificar el despliegue

### 5.1 Verificar logs

1. En Railway, ve a **Deployments**
2. Haz clic en el deployment más reciente
3. Revisa los logs para asegurarte de que no hay errores

### 5.2 Probar el bot

1. Envía un mensaje a tu número de Twilio WhatsApp: `/ayuda`
2. Deberías recibir la lista de comandos disponibles
3. Prueba el flujo completo:
   ```
   /generar 42
   /pool
   /seleccionar P001 P005 P008 P012 P015
   /jugar
   ```

### 5.3 Verificar logs en Railway

Si algo no funciona:
1. Revisa los logs en Railway
2. Verifica que las variables de entorno estén correctas
3. Verifica que el webhook en Twilio apunte a la URL correcta

## Solución de problemas

### El bot no responde

1. **Verifica los logs en Railway:**
   - Ve a **Deployments** > **View Logs**
   - Busca errores o excepciones

2. **Verifica las variables de entorno:**
   - Asegúrate de que `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `TWILIO_WHATSAPP_NUMBER` estén configuradas

3. **Verifica el webhook en Twilio:**
   - Asegúrate de que la URL apunte a `https://tu-app.railway.app/webhook`
   - Verifica que el método sea POST

4. **Verifica que el servicio esté activo:**
   - En Railway, verifica que el servicio esté "Active"
   - Revisa el health check: `https://tu-app.railway.app/health`

### Error 403 en webhook

- Verifica que `TWILIO_AUTH_TOKEN` esté configurado correctamente
- El bot valida las requests de Twilio por seguridad

### Mensajes no se envían

- Verifica que estés usando el formato correcto del número: `whatsapp:+14155238886`
- Asegúrate de estar en el sandbox de Twilio o tener un número aprobado
- Revisa los logs de Twilio en el dashboard

### Sesiones expiradas

- Las sesiones expiran después de 30 minutos de inactividad
- Usa `/limpiar` para resetear tu sesión
- Genera un nuevo pool con `/generar` si es necesario

## Comandos disponibles

Una vez desplegado, los usuarios pueden usar estos comandos:

- `/ayuda` - Muestra comandos disponibles
- `/generar [seed]` - Genera pool de 15 patabolistas
- `/pool` - Muestra pool disponible
- `/seleccionar <id1> <id2> <id3> <id4> <id5>` - Selecciona tu equipo
- `/jugar` - Simula partido
- `/estadisticas` - Muestra estadísticas del último partido
- `/limpiar` - Limpia tu sesión

## Costos

### Twilio

- **Sandbox:** Gratis para pruebas (mensajes limitados)
- **Número aprobado:** ~$0.005 por mensaje entrante/saliente
- **Crédito inicial:** $15.50 al registrarte

### Railway

- **Plan gratuito:** $5 de crédito mensual
- **Hobby:** $5/mes (si excedes el crédito gratuito)
- Para un bot pequeño, el plan gratuito suele ser suficiente

## Próximos pasos

- Monitorear uso y costos
- Considerar agregar Redis para sesiones persistentes
- Implementar rate limiting por usuario
- Agregar más comandos o funcionalidades
- Mejorar manejo de errores y logging

## Recursos útiles

- [Documentación de Twilio WhatsApp](https://www.twilio.com/docs/whatsapp)
- [Documentación de Railway](https://docs.railway.app)
- [Documentación de Flask](https://flask.palletsprojects.com/)
