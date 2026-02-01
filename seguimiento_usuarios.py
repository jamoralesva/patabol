"""
Seguimiento de usuarios que han interactuado con PATABOL (en memoria).
Permite detectar primera interacción y enviar mensaje de bienvenida.
"""

from typing import Set

# Usuarios que ya han enviado al menos un mensaje (número de teléfono)
_usuarios_que_ya_interactuaron: Set[str] = set()


def es_primera_vez(numero_telefono: str) -> bool:
    """True si es la primera vez que este usuario interactúa con el bot."""
    return numero_telefono not in _usuarios_que_ya_interactuaron


def registrar_interaccion(numero_telefono: str) -> None:
    """Registra que el usuario ha interactuado (llamar tras enviar mensaje)."""
    _usuarios_que_ya_interactuaron.add(numero_telefono)


def cantidad_usuarios_unicos() -> int:
    """Cantidad de usuarios que han interactuado (útil para logs/dashboard)."""
    return len(_usuarios_que_ya_interactuaron)


MENSAJE_BIENVENIDA = (
    "¡Bienvenido a PATABOL! Es un juego de simulación de fútbol donde tú y otro jugador "
    "elegís patabolistas de un mismo pool, formáis vuestros equipos y se simula un partido "
    "automáticamente. Para jugar: crea una sesión con /sesion <nickname> (te da un código para compartir) "
    "o únete a una existente con /u <código> <nickname>. Escribí /h para ver todos los comandos."
)
