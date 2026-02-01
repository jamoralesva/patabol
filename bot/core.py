"""
Núcleo del bot: procesamiento de comandos (canal-agnóstico).
"""

import random
import logging
from collections import defaultdict
from typing import Dict, Optional, List, Tuple, Callable

from core.patabol import Patabolista, Rol

from core.sesiones import (
    Sesion,
    JugadorEnSesion,
    EstadoEquipo,
    MAX_JUGADORES_EQUIPO,
    BOT_NUMERO_TELEFONO,
    crear_sesion as crear_sesion_juego,
    unirse_sesion as unirse_sesion_juego,
    agregar_bot_a_sesion,
    obtener_sesion_de_usuario,
    salir_sesion as salir_sesion_juego,
)

from bot.formatters import (
    formatear_pool,
    formatear_detalle_patabolista,
    formatear_resultado,
    formatear_estadisticas,
)

logger = logging.getLogger(__name__)

# Filtros para /pool: keyword -> Rol
FILTROS_POOL = {
    "port": Rol.PORTERO,
    "def": Rol.DEFENSA,
    "med": Rol.MEDIO,
    "del": Rol.DELANTERO,
}

MAX_POOL_SIN_FILTRO = 15

# Alias de comandos: alias -> comando completo
ALIASES = {
    "/u": "/unirse",
    "/p": "/pool",
    "/d": "/detalle",
    "/s": "/seleccionar",
    "/a": "/seleccionar_auto",
    "/q": "/quitar",
    "/e": "/equipo",
    "/c": "/confirmar",
    "/est": "/estadisticas",
    "/h": "/ayuda",
}

MENSAJE_NO_CONECTADO = (
    "❌ No estás conectado a ninguna sesión.\n\n"
    "Para jugar:\n• Crea una sesión: _/sesion_ <nickname> [nombre_equipo]\n"
    "• O únete a una existente: _/unirse_ *(/u)* <código> <nickname> [nombre_equipo]\n\n"
    "Pide el código a quien organice si vas a unirte."
)

MENSAJE_AYUDA = """⚽ PATABOL - Comandos disponibles:

_/sesion_ <nickname> [nombre_equipo] - Crea una nueva sesión (te une y te da el código para compartir)
_/unirse_ *(/u)* <código> <nickname> [nombre_equipo] - Únete a una sesión existente. Creador: _/u_ *ia* [nombre_equipo] para jugar vs IA (nombre opcional)
_/pool_ *(/p)* [port|def|med|del] - Pool disponible. Filtros: port (porteros), def (defensas), med (medios), del (delanteros)
_/detalle_ *(/d)* <id> - Muestra detalle de un patabolista
_/seleccionar_ *(/s)* <id1> [id2] ... - Selecciona tu equipo (entre 1 y 5 jugadores)
_/seleccionar_auto_ *(/a)* - Elige tu equipo automáticamente (5 jugadores, con portero)
_/quitar_ *(/q)* <id> - Devuelve un jugador de tu equipo al pool para elegir otro
_/equipo_ *(/e)* - Muestra tu equipo actualmente seleccionado
_/confirmar_ *(/c)* - Confirma tu equipo (el partido inicia automáticamente cuando ambos confirman)
_/estadisticas_ *(/est)* - Muestra estadísticas del último partido
_/salir_ - Salir de la sesión actual
_/ayuda_ *(/h)* - Muestra esta ayuda
"""


def normalizar_id_patabolista(texto: str) -> str:
    """Normaliza ID de patabolista: insensible a mayúsculas y sin ceros a la izquierda. P001 -> P1, p15 -> P15."""
    texto = texto.strip().upper()
    if texto.startswith("P") and len(texto) > 1 and texto[1:].isdigit():
        return "P" + str(int(texto[1:]))
    return texto


def muestra_estratificada_pool(pool: List[Patabolista], n: int) -> List[Patabolista]:
    """Devuelve hasta n patabolistas del pool con muestra estratificada por rol."""
    if len(pool) <= n:
        return pool
    por_rol: Dict[Rol, List[Patabolista]] = defaultdict(list)
    for p in pool:
        por_rol[p.rol_preferido].append(p)
    resultado = []
    total = len(pool)
    restante = n
    roles_orden = [Rol.PORTERO, Rol.DEFENSA, Rol.MEDIO, Rol.DELANTERO]
    for rol in roles_orden:
        if rol not in por_rol or restante <= 0:
            continue
        grupo = por_rol[rol]
        tomar = max(1, round(n * len(grupo) / total)) if total else len(grupo)
        tomar = min(tomar, restante, len(grupo))
        resultado.extend(random.sample(grupo, tomar))
        restante -= tomar
    if len(resultado) < n and len(resultado) < len(pool):
        faltan = [p for p in pool if p not in resultado]
        extra = min(n - len(resultado), len(faltan))
        resultado.extend(random.sample(faltan, extra))
    return resultado[:n]


def _seleccionar_equipo_bot_si_aplica(sesion: Sesion) -> None:
    """
    La IA solo selecciona y confirma su equipo cuando el jugador humano ya confirmó el suyo.
    """
    if len(sesion.jugadores) != 2:
        return
    bot_jugador = sesion.jugadores.get(BOT_NUMERO_TELEFONO)
    if not bot_jugador or bot_jugador.equipo:
        return
    disponible = sesion.pool_disponible_para(BOT_NUMERO_TELEFONO)
    if not disponible:
        return
    cantidad = min(MAX_JUGADORES_EQUIPO, len(disponible))
    porteros = [p for p in disponible if p.rol_preferido == Rol.PORTERO]
    equipo = []
    if porteros and cantidad > 0:
        equipo.append(random.choice(porteros))
    candidatos = [p for p in disponible if p not in equipo]
    faltan = cantidad - len(equipo)
    if faltan > 0 and candidatos:
        equipo.extend(random.sample(candidatos, min(faltan, len(candidatos))))
    if equipo:
        bot_jugador.equipo = equipo
        bot_jugador.estado_equipo = EstadoEquipo.CONFIRMADO
        sesion.actualizar_estado()


def _mensaje_config_equipo(jugador: JugadorEnSesion) -> str:
    """Construye el mensaje con la configuración final del equipo de un jugador."""
    msg = f"✅ {jugador.nickname} confirmó el equipo *{jugador.nombre_equipo}*:\n"
    for i, p in enumerate(jugador.equipo, 1):
        msg += f"  {i}. {p.nombre_con_id} ({p.rol_preferido.value})\n"
    return msg


def _enviar_config_equipo_a_todos(
    sesion: Sesion,
    jugador: JugadorEnSesion,
    enviar_a_usuario: Callable[[str, List[str]], None],
    excluir_user_id: Optional[str] = None,
) -> None:
    """Envía a todos los jugadores humanos la configuración final del equipo (opcionalmente excluyendo uno)."""
    user_ids = [
        j.numero_telefono
        for j in sesion.jugadores.values()
        if j.numero_telefono != BOT_NUMERO_TELEFONO and j.numero_telefono != excluir_user_id
    ]
    if not user_ids:
        return
    msg = _mensaje_config_equipo(jugador)
    for user_id in user_ids:
        enviar_a_usuario(user_id, [msg])


def procesar_comando(
    comando: str,
    user_id: str,
    enviar_a_usuario: Callable[[str, List[str]], None],
) -> Tuple[List[str], Optional[Sesion]]:
    """
    Procesa un comando y retorna (lista de respuestas para el usuario, sesión si debe disparar simulación).
    enviar_a_usuario(otro_user_id, lista_mensajes): callback para notificar a otros usuarios (ej. creador al unirse alguien).
    """
    partes = comando.strip().split()
    if not partes:
        return (["Comando no reconocido. Usa /ayuda o /h para ver comandos disponibles."], None)

    cmd = partes[0].lower()
    cmd = ALIASES.get(cmd, cmd)
    sesion = obtener_sesion_de_usuario(user_id)

    if not sesion:
        if cmd == "/sesion":
            if len(partes) < 2:
                return ([f"❌ Uso: /sesion <nickname> [nombre_equipo]\nEjemplo: /sesion Leo Los Rayos\n\n{MENSAJE_NO_CONECTADO}"], None)
            nickname = partes[1]
            nombre_equipo = " ".join(partes[2:]) if len(partes) > 2 else None
            nueva_sesion = crear_sesion_juego(user_id, nickname, nombre_equipo)
            msg = (
                f"✅ Sesión creada. Te uniste como '{nickname}' (equipo: {nueva_sesion.jugadores[user_id].nombre_equipo}).\n\n"
                f"📌 Código para compartir con otros jugadores: *{nueva_sesion.session_id}*\n\n"
                "• Para jugar contra la IA: _/u ia_ o _/u ia_ <nombre_equipo>\n"
                "• Para que otro jugador se una: /u <código> <nickname>\n\n"
                "Usa /p para ver patabolistas y /s para elegir tu equipo."
            )
            return ([msg, MENSAJE_AYUDA], None)
        if cmd == "/unirse":
            if len(partes) < 3:
                return ([f"❌ Uso: /unirse <código> <nickname> [nombre_equipo]\nEjemplo: /unirse ABC123 Ana\n\n{MENSAJE_NO_CONECTADO}"], None)
            codigo = partes[1]
            nickname = partes[2]
            nombre_equipo = " ".join(partes[3:]) if len(partes) > 3 else None
            ok, msg, sesion_unido = unirse_sesion_juego(codigo, user_id, nickname, nombre_equipo)
            if ok:
                if sesion_unido and sesion_unido.creador_numero and sesion_unido.creador_numero != user_id:
                    jug = sesion_unido.jugadores.get(user_id)
                    notif_creador = f"👤 {jug.nickname} se unió a tu sesión (equipo: {jug.nombre_equipo})."
                    enviar_a_usuario(sesion_unido.creador_numero, [notif_creador])
                return ([msg, MENSAJE_AYUDA], None)
            return ([msg], None)
        return ([MENSAJE_NO_CONECTADO], None)

    if cmd == "/ayuda" or cmd == "/help":
        return ([MENSAJE_AYUDA], None)

    if cmd == "/iniciar":
        return (["Usa /sesion <nickname> [nombre_equipo] para crear una nueva sesión, o /u <código> <nickname> para unirte a una existente."], None)

    if cmd == "/sesion":
        return (["Actualmente estás en una sesión, debes salir con el comando /salir."], None)

    if cmd == "/unirse":
        if len(partes) >= 2 and partes[1].lower() == "ia":
            codigo = sesion.session_id
            nombre_equipo_ia = " ".join(partes[2:]).strip() or None
            ok, msg, sesion_con_bot = agregar_bot_a_sesion(codigo, user_id, nombre_equipo_ia)
            if ok and sesion_con_bot and sesion_con_bot.creador_numero:
                bot_jug = sesion_con_bot.jugadores.get(BOT_NUMERO_TELEFONO)
                notif_creador = f"🤖 La IA se unió a tu sesión (equipo: {bot_jug.nombre_equipo if bot_jug else '?'})."
                enviar_a_usuario(sesion_con_bot.creador_numero, [notif_creador])
            return ([msg], None)
        return (["❌ Ya estás en una sesión. Usa /salir primero."], None)

    if cmd == "/salir":
        if not sesion:
            return (["No estás en ninguna sesión."], None)
        salir_sesion_juego(user_id)
        return (["✅ Has salido de la sesión."], None)

    if cmd == "/pool":
        disponible = sesion.pool_sin_seleccionar()
        filtro_rol = None
        if len(partes) > 1:
            clave = partes[1].lower().strip()
            filtro_rol = FILTROS_POOL.get(clave)
            if filtro_rol is not None:
                disponible = [p for p in disponible if p.rol_preferido == filtro_rol]
        mensaje_adicional = None
        if len(disponible) > MAX_POOL_SIN_FILTRO and filtro_rol is None:
            muestra = muestra_estratificada_pool(disponible, MAX_POOL_SIN_FILTRO)
            no_mostrados = len(disponible) - len(muestra)
            mensaje_adicional = (
                f"📌 Hay {no_mostrados} jugadores más.\n"
                "Filtros: /p port (porteros), /p def (defensas), /p med (medios), /p del (delanteros)"
            )
            disponible = muestra
        elif not disponible and filtro_rol is not None:
            return ([f"❌ No hay patabolistas disponibles con ese filtro. Usa /p para ver todos."], None)
        return ([formatear_pool(disponible, mensaje_adicional)], None)

    if cmd == "/detalle":
        if len(partes) != 2:
            return (["❌ Uso: /detalle <id> o /d <id>\nEjemplo: /d P1"], None)
        id_buscado = normalizar_id_patabolista(partes[1])
        patabolista_encontrado = None
        for p in sesion.pool:
            if normalizar_id_patabolista(p.id) == id_buscado:
                patabolista_encontrado = p
                break
        if not patabolista_encontrado:
            return ([f"❌ Patabolista {id_buscado} no encontrado. Usa /pool para ver IDs."], None)
        return ([formatear_detalle_patabolista(patabolista_encontrado)], None)

    if cmd == "/seleccionar":
        disponible = sesion.pool_disponible_para(user_id)
        if not disponible:
            return (["❌ No hay patabolistas disponibles para elegir (ya fueron seleccionados)."], None)
        ids = partes[1:]
        if not ids:
            return (["❌ Debes elegir al menos un patabolista.\nEjemplo: /s P1 P5 P8"], None)
        if len(ids) > MAX_JUGADORES_EQUIPO:
            return ([f"❌ Máximo {MAX_JUGADORES_EQUIPO} jugadores por equipo.\nEjemplo: /s P1 P5 P8"], None)
        equipo = []
        disponibles_ids = {normalizar_id_patabolista(p.id): p for p in disponible}
        for id_jugador in ids:
            id_norm = normalizar_id_patabolista(id_jugador)
            if id_norm not in disponibles_ids:
                return ([f"❌ {id_jugador} no está disponible (no existe o ya fue elegido por el otro). Usa /pool."], None)
            equipo.append(disponibles_ids[id_norm])
        jugador_sesion = sesion.jugador_por_telefono(user_id)
        jugador_sesion.equipo = equipo
        jugador_sesion.estado_equipo = EstadoEquipo.PENDIENTE_CONFIRMACION
        sesion.actualizar_estado()
        mensaje = f"✅ Equipo ({jugador_sesion.nombre_equipo}) seleccionado:\n"
        for j in equipo:
            mensaje += f"  - {j.nombre_con_id} ({j.rol_preferido.value})\n"
        if sesion.listas_para_simular():
            mensaje += "\nUsá _/confirmar_ o _/c_ para confirmar tu equipo. Solo equipos confirmados pueden jugar."
        elif sesion.jugadores.get(BOT_NUMERO_TELEFONO):
            mensaje += "\nUsá _/confirmar_ o _/c_ para confirmar tu equipo. La IA elegirá el suyo cuando confirmes."
        else:
            mensaje += "\nEsperando al otro jugador para que elija su equipo."
        return ([mensaje], None)

    if cmd == "/seleccionar_auto":
        disponible = sesion.pool_disponible_para(user_id)
        if not disponible:
            return (["❌ No hay patabolistas disponibles para elegir (ya fueron seleccionados)."], None)
        cantidad = min(MAX_JUGADORES_EQUIPO, len(disponible))
        porteros = [p for p in disponible if p.rol_preferido == Rol.PORTERO]
        equipo = []
        if porteros and cantidad > 0:
            equipo.append(random.choice(porteros))
        candidatos = [p for p in disponible if p not in equipo]
        faltan = cantidad - len(equipo)
        if faltan > 0 and candidatos:
            equipo.extend(random.sample(candidatos, min(faltan, len(candidatos))))
        if not equipo:
            return (["❌ No se pudo armar el equipo automáticamente. Usa /pool y /seleccionar."], None)
        jugador_sesion = sesion.jugador_por_telefono(user_id)
        jugador_sesion.equipo = equipo
        jugador_sesion.estado_equipo = EstadoEquipo.PENDIENTE_CONFIRMACION
        sesion.actualizar_estado()
        mensaje = f"✅ Equipo ({jugador_sesion.nombre_equipo}) seleccionado automáticamente:\n"
        for j in equipo:
            mensaje += f"  - {j.nombre_con_id} ({j.rol_preferido.value})\n"
        if sesion.listas_para_simular():
            mensaje += "\nUsá _/confirmar_ o _/c_ para confirmar tu equipo. Solo equipos confirmados pueden jugar."
        elif sesion.jugadores.get(BOT_NUMERO_TELEFONO):
            mensaje += "\nUsá _/confirmar_ o _/c_ para confirmar tu equipo. La IA elegirá el suyo cuando confirmes."
        else:
            mensaje += "\nEsperando al otro jugador para que elija su equipo."
        return ([mensaje], None)

    if cmd == "/quitar":
        if len(partes) != 2:
            return (["❌ Uso: /quitar <id> o /q <id>\nEjemplo: /q P3\nDevuelve ese jugador al pool para elegir otro."], None)
        id_buscado = normalizar_id_patabolista(partes[1])
        jugador_sesion = sesion.jugador_por_telefono(user_id)
        if not jugador_sesion or not jugador_sesion.equipo:
            return (["❌ No tienes jugadores seleccionados. Usa /seleccionar o /seleccionar_auto."], None)
        en_equipo = [p for p in jugador_sesion.equipo if normalizar_id_patabolista(p.id) == id_buscado]
        if not en_equipo:
            return ([f"❌ {id_buscado} no está en tu equipo. Tus jugadores: {', '.join(p.id for p in jugador_sesion.equipo)}"], None)
        jugador_sesion.equipo = [p for p in jugador_sesion.equipo if normalizar_id_patabolista(p.id) != id_buscado]
        jugador_sesion.estado_equipo = EstadoEquipo.PENDIENTE_CONFIRMACION
        sesion.actualizar_estado()
        nombre_devuelto = en_equipo[0].nombre_con_id
        return ([f"✅ {nombre_devuelto} devuelto al pool. Usa /pool para ver disponibles y /seleccionar para elegir otro."], None)

    if cmd == "/equipo":
        jugador_sesion = sesion.jugador_por_telefono(user_id)
        if not jugador_sesion or not jugador_sesion.equipo:
            return (["❌ No tienes jugadores seleccionados aún. Usa /s o /a para elegir tu equipo."], None)
        mensaje = f"👥 Tu equipo: {jugador_sesion.nombre_equipo}\n"
        mensaje += "=" * 30 + "\n\n"
        for i, j in enumerate(jugador_sesion.equipo, 1):
            mensaje += f"{i}. {j.nombre_con_id} ({j.rol_preferido.value})\n"
        return ([mensaje], None)

    if cmd == "/confirmar":
        jugador_sesion = sesion.jugador_por_telefono(user_id)
        if not jugador_sesion or not jugador_sesion.equipo:
            return (["❌ No tienes jugadores seleccionados. Usa /s o /a para elegir tu equipo."], None)
        if jugador_sesion.equipo_confirmado():
            return (["✅ Tu equipo ya está confirmado."], None)
        jugador_sesion.estado_equipo = EstadoEquipo.CONFIRMADO
        mensaje_config = _mensaje_config_equipo(jugador_sesion)
        _enviar_config_equipo_a_todos(sesion, jugador_sesion, enviar_a_usuario, excluir_user_id=user_id)
        respuestas = [mensaje_config]
        bot_jugador = sesion.jugadores.get(BOT_NUMERO_TELEFONO)
        if bot_jugador and not bot_jugador.equipo:
            _seleccionar_equipo_bot_si_aplica(sesion)
            bot_jugador = sesion.jugadores.get(BOT_NUMERO_TELEFONO)
            if bot_jugador and bot_jugador.equipo_confirmado():
                _enviar_config_equipo_a_todos(sesion, bot_jugador, enviar_a_usuario)
        if sesion.equipos_confirmados():
            respuestas.append("🎮 Ambos equipos confirmados. ¡Iniciando partido!")
            return (respuestas, sesion)
        return (respuestas, None)

    if cmd == "/estadisticas":
        if not sesion.ultimo_resultado:
            return (["❌ No hay partido jugado aún en esta sesión."], None)
        msg1 = formatear_resultado(
            sesion.ultimo_resultado,
            sesion.ultimo_nombre_a,
            sesion.ultimo_nombre_b,
        )
        msg2 = formatear_estadisticas(
            sesion.ultimo_equipo_a,
            sesion.ultimo_equipo_b,
            sesion.ultimo_nombre_a,
            sesion.ultimo_nombre_b,
        )
        return ([msg1, msg2], None)

    return (["❌ Comando no reconocido. Usa /ayuda o /h para ver comandos disponibles."], None)
