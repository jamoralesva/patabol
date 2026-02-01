"""
Formateo de mensajes del bot (canal-agnóstico).
"""

import logging
from typing import List, Optional

from core.patabol import Patabolista, ResultadoPartido, Evento

logger = logging.getLogger(__name__)


def dividir_mensaje(mensaje: str, max_length: int = 4000) -> List[str]:
    """Divide un mensaje largo en múltiples mensajes."""
    if len(mensaje) <= max_length:
        return [mensaje]
    mensajes = []
    lineas = mensaje.split("\n")
    mensaje_actual = ""
    for linea in lineas:
        if len(mensaje_actual) + len(linea) + 1 > max_length:
            if mensaje_actual:
                mensajes.append(mensaje_actual)
            mensaje_actual = linea + "\n"
        else:
            mensaje_actual += linea + "\n"
    if mensaje_actual:
        mensajes.append(mensaje_actual)
    return mensajes


def valor_a_estrellas(valor: int) -> str:
    """Convierte un valor (1-10) a formato de estrellas (1-5)."""
    num_estrellas = min(5, max(1, (valor + 1) // 2))
    estrellas_llenas = "⭐" * num_estrellas
    estrellas_vacias = "☆" * (5 - num_estrellas)
    return f"{estrellas_llenas}{estrellas_vacias}"


def formatear_detalle_patabolista(patabolista: Patabolista) -> str:
    """Formatea el detalle completo de un patabolista con estrellas."""
    attrs = patabolista.obtener_atributos_visibles()
    mensaje = "👤 DETALLE DE PATABOLISTA\n"
    mensaje += "=" * 30 + "\n\n"
    mensaje += f"🆔 ID: {patabolista.id}\n"
    mensaje += f"📛 Nombre: {patabolista.nombre_con_id}\n"
    mensaje += f"🏷️ Rol: {patabolista.rol_preferido.value}\n\n"
    mensaje += "📊 ATRIBUTOS:\n"
    mensaje += f"🎯 Control:   {valor_a_estrellas(attrs['control'])} ({attrs['control']}/10)\n"
    mensaje += f"⚡ Velocidad: {valor_a_estrellas(attrs['velocidad'])} ({attrs['velocidad']}/10)\n"
    mensaje += f"💪 Fuerza:    {valor_a_estrellas(attrs['fuerza'])} ({attrs['fuerza']}/10)\n"
    mensaje += f"🌀 Regate:    {valor_a_estrellas(attrs['regate'])} ({attrs['regate']}/10)\n"
    return mensaje


def formatear_evento_unico(evento: Evento) -> str:
    """Formatea un solo evento del partido."""
    if evento.tipo == "gol":
        return f"⚽ {evento.descripcion}"
    if evento.tipo == "falta":
        return f"🟨 {evento.descripcion}"
    if evento.tipo == "robo":
        return f"🏃 {evento.descripcion}"
    if evento.tipo == "regate":
        return f"✨ {evento.descripcion}"
    if evento.tipo == "pase" or evento.tipo == "avance":
        return f"📍 {evento.descripcion}"
    if evento.tipo == "atajada":
        return f"🧤 {evento.descripcion}"
    return f"• {evento.descripcion}"


def formatear_pool(
    pool: List[Patabolista],
    mensaje_adicional: Optional[str] = None,
) -> str:
    """Formatea el pool de patabolistas. Si mensaje_adicional, se añade al final."""
    if not pool:
        return "No hay patabolistas disponibles en el pool (ya fueron elegidos)."
    mensaje = "📋 POOL DE PATABOLISTAS\n"
    mensaje += "=" * 30 + "\n\n"
    for i, patabolista in enumerate(pool, 1):
        mensaje += f"{i}. {patabolista.nombre_con_id}\n"
        mensaje += f"   🏷️ Rol: {patabolista.rol_preferido.value}\n"
    if mensaje_adicional:
        mensaje += "\n" + mensaje_adicional
    logger.info(mensaje)
    return mensaje


def formatear_narrativa(resultado: ResultadoPartido) -> List[str]:
    """Formatea la narrativa del partido (lista de mensajes por longitud)."""
    eventos_por_minuto = {}
    for evento in resultado.eventos:
        if evento.minuto not in eventos_por_minuto:
            eventos_por_minuto[evento.minuto] = []
        eventos_por_minuto[evento.minuto].append(evento)
    narrativa = "📺 NARRATIVA DEL PARTIDO\n"
    narrativa += "=" * 30 + "\n\n"
    for minuto in sorted(eventos_por_minuto.keys()):
        narrativa += f"⏱️ Minuto {minuto + 1}:\n"
        for evento in eventos_por_minuto[minuto]:
            if evento.tipo == "gol":
                narrativa += f"⚽ {evento.descripcion}\n"
            elif evento.tipo == "falta":
                narrativa += f"🟨 {evento.descripcion}\n"
            elif evento.tipo == "robo":
                narrativa += f"🏃 {evento.descripcion}\n"
            elif evento.tipo == "regate":
                narrativa += f"✨ {evento.descripcion}\n"
            elif evento.tipo == "pase":
                narrativa += f"📍 {evento.descripcion}\n"
            else:
                narrativa += f"• {evento.descripcion}\n"
        narrativa += "\n"
    return dividir_mensaje(narrativa)


def formatear_resultado(
    resultado: ResultadoPartido,
    nombre_equipo_a: str,
    nombre_equipo_b: str,
) -> str:
    """Formatea el resultado final con nombres de equipo."""
    mensaje = "🏆 RESULTADO FINAL\n"
    mensaje += "=" * 30 + "\n"
    mensaje += f"{nombre_equipo_a}: {resultado.goles_equipo_a}\n"
    mensaje += f"{nombre_equipo_b}: {resultado.goles_equipo_b}\n\n"
    if resultado.goles_equipo_a > resultado.goles_equipo_b:
        mensaje += f"🎉 ¡Ganador: {nombre_equipo_a}!\n\n"
    elif resultado.goles_equipo_a < resultado.goles_equipo_b:
        mensaje += f"🎉 ¡Ganador: {nombre_equipo_b}!\n\n"
    else:
        mensaje += "🤝 Empate. Buen partido.\n\n"
    mensaje += f"⭐ Jugador del Partido: {resultado.jugador_del_partido.nombre_con_id}\n"
    stats = resultado.jugador_del_partido.obtener_estadisticas()
    mensaje += f"Goles: {stats['goles']}, Regates: {stats['regates_exitosos']}, "
    mensaje += f"Robos: {stats['robos']}, Pases: {stats['pases']}\n"
    return mensaje


def formatear_estadisticas(
    equipo_a: List[Patabolista],
    equipo_b: List[Patabolista],
    nombre_equipo_a: str,
    nombre_equipo_b: str,
) -> str:
    """Formatea las estadísticas con nombres de equipo."""
    mensaje = "📊 ESTADÍSTICAS RESUMIDAS\n"
    mensaje += "=" * 30 + "\n\n"
    mensaje += f"👥 {nombre_equipo_a}:\n"
    for jugador in equipo_a:
        stats = jugador.obtener_estadisticas()
        mensaje += f"{jugador.nombre_con_id}:\n"
        mensaje += f"  G:{stats['goles']} P:{stats['pases']} "
        mensaje += f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} F:{stats['faltas']}\n"
    mensaje += f"\n👥 {nombre_equipo_b}:\n"
    for jugador in equipo_b:
        stats = jugador.obtener_estadisticas()
        mensaje += f"{jugador.nombre_con_id}:\n"
        mensaje += f"  G:{stats['goles']} P:{stats['pases']} "
        mensaje += f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} F:{stats['faltas']}\n"
    return mensaje
