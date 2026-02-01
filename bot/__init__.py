"""
Núcleo del bot PATABOL: comandos, formateo y simulación.
Independiente del canal (WhatsApp, CLI, Telegram).
"""

from bot.core import procesar_comando
from bot.simulation import ejecutar_simulacion_y_notificar

__all__ = ["procesar_comando", "ejecutar_simulacion_y_notificar"]
