"""
Canal CLI: REPL por comandos. Misma experiencia que WhatsApp (mismos comandos y flujo).
"""

import re
import sys
from typing import List

from core.sesiones import crear_sesion_por_defecto, salir_sesion as salir_sesion_juego
from bot.core import procesar_comando
from bot.simulation import ejecutar_simulacion_y_notificar

CLI_USER_ID = "cli_user"

# ANSI: bold \033[1m, italic \033[3m, reset \033[0m
_ANSI_BOLD = "\033[1m"
_ANSI_ITALIC = "\033[3m"
_ANSI_RESET = "\033[0m"


def _mensaje_para_consola(texto: str, stream=None) -> str:
    """Aplica estilos ANSI a *negrita* y _cursiva_ si la salida es una TTY."""
    stream = stream or sys.stdout
    if not (hasattr(stream, "isatty") and stream.isatty()):
        return texto
    # Primero negrita (*...*), luego cursiva (_..._)
    out = re.sub(r"\*([^*]+)\*", _ANSI_BOLD + r"\1" + _ANSI_RESET, texto)
    out = re.sub(r"_([^_]+)_", _ANSI_ITALIC + r"\1" + _ANSI_RESET, out)
    return out


def _enviar_a_usuario_cli(to_id: str, mensajes: List[str]) -> None:
    """Envía mensajes por consola (para notificaciones a otros jugadores, ej. creador)."""
    for m in mensajes:
        if to_id != CLI_USER_ID:
            print(f"[Para otro jugador] {_mensaje_para_consola(m, sys.stderr)}", file=sys.stderr)
        else:
            print(_mensaje_para_consola(m))


def _enviar_a_jugadores_cli(user_ids: List[str], mensaje: str) -> None:
    """En CLI todos los jugadores humanos ven lo mismo en consola."""
    print(_mensaje_para_consola(mensaje))


def main() -> None:
    crear_sesion_por_defecto()
    print("⚽ PATABOL - CLI (mismos comandos que WhatsApp)")
    print("Escribí /sesion <nickname> [nombre_equipo] para crear una sesión.")
    print("Luego /u ia [nombre_equipo] para jugar vs IA. /h para ayuda.\n")

    while True:
        try:
            linea = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 ¡Hasta luego!")
            break
        if not linea:
            continue

        respuestas, sesion_simular = procesar_comando(
            linea, CLI_USER_ID, _enviar_a_usuario_cli
        )
        for r in respuestas:
            print(_mensaje_para_consola(r))

        if sesion_simular is not None:
            ejecutar_simulacion_y_notificar(
                sesion_simular,
                enviar_a_jugadores=_enviar_a_jugadores_cli,
                salir_sesion_fn=salir_sesion_juego,
                latencia_entre_eventos_segundos=2.0,
            )


if __name__ == "__main__":
    main()
