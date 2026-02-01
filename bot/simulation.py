"""
Ejecución de la simulación del partido y notificación a jugadores.
Canal-agnóstico: recibe callbacks para enviar mensajes y salir de sesión.
"""

import time
import logging
from typing import List, Callable

from core.patabol import SimuladorPartido

from core.sesiones import Sesion, BOT_NUMERO_TELEFONO, marcar_partido_simulado

from bot.formatters import (
    formatear_evento_unico,
    formatear_resultado,
    formatear_estadisticas,
)

logger = logging.getLogger(__name__)


def ejecutar_simulacion_y_notificar(
    sesion: Sesion,
    enviar_a_jugadores: Callable[[List[str], str], None],
    salir_sesion_fn: Callable[[str], None],
    latencia_entre_eventos_segundos: float = 2.0,
) -> None:
    """
    Ejecuta el partido, guarda resultado en la sesión y notifica a jugadores humanos
    (excluye BOT): mensaje de inicio, evento por evento con latencia, resultado y estadísticas.
    Al final llama salir_sesion_fn para cada jugador humano.

    enviar_a_jugadores(user_ids, mensaje): envía el mensaje a todos los user_ids.
    salir_sesion_fn(user_id): saca al usuario de la sesión.
    """
    jugadores_list = list(sesion.jugadores.values())
    if len(jugadores_list) != 2:
        logger.warning("Simulación solicitada pero la sesión no tiene exactamente 2 jugadores")
        return
    jugador_a, jugador_b = jugadores_list[0], jugadores_list[1]
    equipo_a = jugador_a.equipo
    equipo_b = jugador_b.equipo
    user_ids = [
        j.numero_telefono
        for j in (jugador_a, jugador_b)
        if j.numero_telefono != BOT_NUMERO_TELEFONO
    ]

    simulador = SimuladorPartido(equipo_a, equipo_b)
    resultado = simulador.simular()

    sesion.ultimo_resultado = resultado
    sesion.ultimo_equipo_a = equipo_a
    sesion.ultimo_equipo_b = equipo_b
    sesion.ultimo_nombre_a = jugador_a.nombre_equipo
    sesion.ultimo_nombre_b = jugador_b.nombre_equipo
    marcar_partido_simulado(sesion.session_id)

    enviar_a_jugadores(user_ids, "🎮 ¡Iniciando partido!")

    for evento in resultado.eventos:
        msg = formatear_evento_unico(evento)
        enviar_a_jugadores(user_ids, msg)
        time.sleep(latencia_entre_eventos_segundos)

    resultado_msg = formatear_resultado(
        resultado, sesion.ultimo_nombre_a, sesion.ultimo_nombre_b
    )
    stats_msg = formatear_estadisticas(
        equipo_a, equipo_b, sesion.ultimo_nombre_a, sesion.ultimo_nombre_b
    )
    enviar_a_jugadores(user_ids, resultado_msg)
    enviar_a_jugadores(user_ids, stats_msg)

    enviar_a_jugadores(
        user_ids,
        "Sesión finalizada. Creá una nueva con /sesion para jugar otra vez.",
    )
    for user_id in user_ids:
        salir_sesion_fn(user_id)
