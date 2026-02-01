"""
Punto de entrada del bot por Telegram.
- Con Gunicorn (Railway): se usa el atributo `app` (Flask WSGI).
- Ejecución directa: python -m entrypoints.telegram_bot → run_webhook (uvicorn).
"""

from dotenv import load_dotenv

load_dotenv()

from core.sesiones import crear_sesion_por_defecto
from channels.telegram import get_app, run_webhook

# Sesión por defecto al iniciar la aplicación (código se imprime en consola)
crear_sesion_por_defecto()

# Para Gunicorn (Railway): gunicorn entrypoints.telegram_bot:app
# Solo exponer app cuando se importa el módulo (no al ejecutar como script)
if __name__ != "__main__":
    app = get_app()

if __name__ == "__main__":
    run_webhook()
