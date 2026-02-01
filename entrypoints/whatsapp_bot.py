"""
Punto de entrada del bot por WhatsApp (Twilio).
- Con Gunicorn (Railway): gunicorn entrypoints.whatsapp_bot:app
- Ejecución directa: python -m entrypoints.whatsapp_bot → app.run()
"""

import os

from dotenv import load_dotenv

load_dotenv()

from core.sesiones import crear_sesion_por_defecto
from channels.whatsapp import app

# Sesión por defecto al iniciar la aplicación (código se imprime en consola)
crear_sesion_por_defecto()

# Para Gunicorn: gunicorn entrypoints.whatsapp_bot:app (app ya viene de channels.whatsapp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
