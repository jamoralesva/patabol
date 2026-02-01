"""
Punto de entrada del bot por Telegram.
Carga env, crea sesión por defecto y arranca el bot en modo webhook.
"""

from dotenv import load_dotenv

load_dotenv()

from core.sesiones import crear_sesion_por_defecto
from channels.telegram import run_webhook

# Sesión por defecto al iniciar la aplicación (código se imprime en consola)
crear_sesion_por_defecto()

if __name__ == "__main__":
    run_webhook()
