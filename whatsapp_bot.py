"""
Bot de WhatsApp para PATABOL usando Twilio API
Maneja la interacción con usuarios a través de WhatsApp
"""

import os
import random
import time
import logging
import threading
from collections import defaultdict
from typing import Dict, Optional, List, Tuple
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from patabol import (
    Patabolista,
    SimuladorPartido,
    ResultadoPartido,
    Rol,
    Evento,
)

from sesiones import (
    Sesion,
    JugadorEnSesion,
    MAX_JUGADORES_EQUIPO,
    BOT_NUMERO_TELEFONO,
    crear_sesion as crear_sesion_juego,
    crear_sesion_por_defecto,
    unirse_sesion as unirse_sesion_juego,
    agregar_bot_a_sesion,
    obtener_sesion_de_usuario,
    salir_sesion as salir_sesion_juego,
    marcar_partido_simulado,
)
from seguimiento_usuarios import (
    es_primera_vez,
    registrar_interaccion,
    MENSAJE_BIENVENIDA,
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Variables de entorno
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
# Latencia en segundos entre envío de cada evento del partido (solo presentación)
LATENCIA_ENTRE_EVENTOS_SEGUNDOS = float(os.environ.get('LATENCIA_EVENTOS', '2'))

# Sesión por defecto al iniciar la aplicación (código se imprime en consola)
crear_sesion_por_defecto()


def normalizar_id_patabolista(texto: str) -> str:
    """Normaliza ID de patabolista: insensible a mayúsculas y sin ceros a la izquierda. P001 -> P1, p15 -> P15."""
    texto = texto.strip().upper()
    if texto.startswith("P") and len(texto) > 1 and texto[1:].isdigit():
        return "P" + str(int(texto[1:]))
    return texto


def dividir_mensaje(mensaje: str, max_length: int = 4000) -> List[str]:
    """Divide un mensaje largo en múltiples mensajes"""
    if len(mensaje) <= max_length:
        return [mensaje]
    
    mensajes = []
    lineas = mensaje.split('\n')
    mensaje_actual = ""
    
    for linea in lineas:
        if len(mensaje_actual) + len(linea) + 1 > max_length:
            if mensaje_actual:
                mensajes.append(mensaje_actual)
            mensaje_actual = linea + '\n'
        else:
            mensaje_actual += linea + '\n'
    
    if mensaje_actual:
        mensajes.append(mensaje_actual)
    
    return mensajes


def valor_a_estrellas(valor: int) -> str:
    """Convierte un valor (1-10) a formato de estrellas (1-5)"""
    # Mapear 1-10 a 1-5 estrellas
    # 1-2 -> 1 estrella, 3-4 -> 2, 5-6 -> 3, 7-8 -> 4, 9-10 -> 5
    num_estrellas = min(5, max(1, (valor + 1) // 2))
    estrellas_llenas = "⭐" * num_estrellas
    estrellas_vacias = "☆" * (5 - num_estrellas)
    return f"{estrellas_llenas}{estrellas_vacias}"


def formatear_detalle_patabolista(patabolista: Patabolista) -> str:
    """Formatea el detalle completo de un patabolista con estrellas"""
    attrs = patabolista.obtener_atributos_visibles()
    
    mensaje = f"👤 DETALLE DE PATABOLISTA\n"
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
    """Formatea un solo evento del partido para envío por WhatsApp."""
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


# Filtros para /pool: keyword -> Rol
FILTROS_POOL = {
    "port": Rol.PORTERO,
    "def": Rol.DEFENSA,
    "med": Rol.MEDIO,
    "del": Rol.DELANTERO,
}

MAX_POOL_SIN_FILTRO = 15


def _seleccionar_equipo_bot_si_aplica(sesion: Sesion) -> None:
    """
    La máquina siempre elige después del jugador: solo se llama tras fijar el equipo del humano.
    Si el otro jugador es la IA y no tiene equipo, le asigna uno desde el pool disponible
    (lo que quedó tras la elección del humano; misma lógica que /seleccionar_auto).
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
        sesion.actualizar_estado()


def muestra_estratificada_pool(pool: List[Patabolista], n: int) -> List[Patabolista]:
    """Devuelve hasta n patabolistas del pool con muestra estratificada por rol."""
    if len(pool) <= n:
        return pool
    por_rol = defaultdict(list)
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
        # Proporcional: tomar al menos 1 si hay, hasta lo que toque
        tomar = max(1, round(n * len(grupo) / total)) if total else len(grupo)
        tomar = min(tomar, restante, len(grupo))
        resultado.extend(random.sample(grupo, tomar))
        restante -= tomar
    # Si sobran slots, rellenar sin repetir
    if len(resultado) < n and len(resultado) < len(pool):
        faltan = [p for p in pool if p not in resultado]
        extra = min(n - len(resultado), len(faltan))
        resultado.extend(random.sample(faltan, extra))
    return resultado[:n]


def formatear_pool_whatsapp(
    pool: List[Patabolista],
    mensaje_adicional: Optional[str] = None,
) -> str:
    """Formatea el pool para WhatsApp. Si mensaje_adicional, se añade al final."""
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


def formatear_narrativa_whatsapp(resultado: ResultadoPartido) -> List[str]:
    """Formatea la narrativa del partido para WhatsApp"""
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


def formatear_resultado_whatsapp(
    resultado: ResultadoPartido,
    nombre_equipo_a: str,
    nombre_equipo_b: str,
) -> str:
    """Formatea el resultado final para WhatsApp con nombres de equipo."""
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


def formatear_estadisticas_whatsapp(
    equipo_a: List[Patabolista],
    equipo_b: List[Patabolista],
    nombre_equipo_a: str,
    nombre_equipo_b: str,
) -> str:
    """Formatea las estadísticas para WhatsApp con nombres de equipo."""
    mensaje = "📊 ESTADÍSTICAS RESUMIDAS\n"
    mensaje += "=" * 30 + "\n\n"
    
    mensaje += f"👥 {nombre_equipo_a}:\n"
    for jugador in equipo_a:
        stats = jugador.obtener_estadisticas()
        mensaje += f"{jugador.nombre_con_id}:\n"
        mensaje += f"  G:{stats['goles']} P:{stats['pases']} "
        mensaje += f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} "
        mensaje += f"F:{stats['faltas']}\n"
    
    mensaje += f"\n👥 {nombre_equipo_b}:\n"
    for jugador in equipo_b:
        stats = jugador.obtener_estadisticas()
        mensaje += f"{jugador.nombre_con_id}:\n"
        mensaje += f"  G:{stats['goles']} P:{stats['pases']} "
        mensaje += f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} "
        mensaje += f"F:{stats['faltas']}\n"
    
    return mensaje


# Alias de comandos: alias -> comando completo
ALIASES = {
    "/u": "/unirse",
    "/p": "/pool",
    "/d": "/detalle",
    "/s": "/seleccionar",
    "/a": "/seleccionar_auto",
    "/q": "/quitar",
    "/e": "/equipo",
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
_/estadisticas_ *(/est)* - Muestra estadísticas del último partido
_/salir_ - Salir de la sesión actual
_/ayuda_ *(/h)* - Muestra esta ayuda
"""


def procesar_comando(comando: str, numero_origen: str) -> Tuple[List[str], Optional[Sesion]]:
    """
    Procesa un comando y retorna (lista de respuestas para el usuario, sesión si debe disparar simulación).
    Si el segundo valor es una Sesion, el webhook debe lanzar la simulación y enviar a ambos jugadores.
    """
    partes = comando.strip().split()
    if not partes:
        return (["Comando no reconocido. Usa /ayuda o /h para ver comandos disponibles."], None)

    cmd = partes[0].lower()
    cmd = ALIASES.get(cmd, cmd)  # Resolver alias
    sesion = obtener_sesion_de_usuario(numero_origen)

    # Si no está conectado a ninguna sesión: permitir /sesion y /unirse; el resto recibe mensaje
    if not sesion:
        if cmd == "/sesion":
            if len(partes) < 2:
                return ([f"❌ Uso: /sesion <nickname> [nombre_equipo]\nEjemplo: /sesion Leo Los Rayos\n\n{MENSAJE_NO_CONECTADO}"], None)
            nickname = partes[1]
            nombre_equipo = " ".join(partes[2:]) if len(partes) > 2 else None
            nueva_sesion = crear_sesion_juego(numero_origen, nickname, nombre_equipo)
            msg = (
                f"✅ Sesión creada. Te uniste como '{nickname}' (equipo: {nueva_sesion.jugadores[numero_origen].nombre_equipo}).\n\n"
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
            ok, msg, sesion_unido = unirse_sesion_juego(codigo, numero_origen, nickname, nombre_equipo)
            if ok:
                # Notificar al creador que alguien se unió (si hay creador y no es el mismo que se unió)
                if sesion_unido and sesion_unido.creador_numero and sesion_unido.creador_numero != numero_origen:
                    jug = sesion_unido.jugadores.get(numero_origen)
                    notif_creador = f"👤 {jug.nickname} se unió a tu sesión (equipo: {jug.nombre_equipo})."
                    enviar_mensajes_multiples(sesion_unido.creador_numero, [notif_creador])
                return ([msg, MENSAJE_AYUDA], None)
            return ([msg], None)
        # Cualquier otro mensaje sin sesión: enviar mensaje para que se conecte
        return ([MENSAJE_NO_CONECTADO], None)

    if cmd == "/ayuda" or cmd == "/help":
        return ([MENSAJE_AYUDA], None)

    if cmd == "/iniciar":
        return (["Usa /sesion <nickname> [nombre_equipo] para crear una nueva sesión, o /u <código> <nickname> para unirte a una existente."], None)

    if cmd == "/sesion":
        return (["Actualmente estás en una sesión, debes salir con el comando /salir."], None)

    if cmd == "/unirse":
        # /u ia [nombre_equipo] — solo el creador puede agregar la IA. Código no hace falta (usa tu sesión). Nombre opcional (aleatorio si no se pasa).
        if len(partes) >= 2 and partes[1].lower() == "ia":
            codigo = sesion.session_id
            nombre_equipo_ia = " ".join(partes[2:]).strip() or None  # None → nombre al azar en agregar_bot_a_sesion
            ok, msg, sesion_con_bot = agregar_bot_a_sesion(codigo, numero_origen, nombre_equipo_ia)
            if ok and sesion_con_bot and sesion_con_bot.creador_numero:
                # Notificar al creador que la IA se unió (envío explícito por API para asegurar que reciba el mensaje)
                bot_jug = sesion_con_bot.jugadores.get(BOT_NUMERO_TELEFONO)
                notif_creador = f"🤖 La IA se unió a tu sesión (equipo: {bot_jug.nombre_equipo if bot_jug else '?'})."
                enviar_mensajes_multiples(sesion_con_bot.creador_numero, [notif_creador])
            return ([msg], None)
        return (["❌ Ya estás en una sesión. Usa /salir primero."], None)

    if cmd == "/salir":
        if not sesion:
            return (["No estás en ninguna sesión."], None)
        salir_sesion_juego(numero_origen)
        return (["✅ Has salido de la sesión."], None)

    if cmd == "/pool":
        disponible = sesion.pool_sin_seleccionar()
        filtro_rol = None
        if len(partes) > 1:
            clave = partes[1].lower().strip()
            filtro_rol = FILTROS_POOL.get(clave)
            if filtro_rol is not None:
                disponible = [p for p in disponible if p.rol_preferido == filtro_rol]
            # Si la clave no es un filtro conocido, se ignora y se muestran todos
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
        return ([formatear_pool_whatsapp(disponible, mensaje_adicional)], None)

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
        disponible = sesion.pool_disponible_para(numero_origen)
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

        jugador_sesion = sesion.jugador_por_telefono(numero_origen)
        jugador_sesion.equipo = equipo
        sesion.actualizar_estado()
        _seleccionar_equipo_bot_si_aplica(sesion)

        mensaje = f"✅ Equipo ({jugador_sesion.nombre_equipo}) seleccionado:\n"
        for j in equipo:
            mensaje += f"  - {j.nombre_con_id} ({j.rol_preferido.value})\n"
        if sesion.listas_para_simular():
            mensaje += "\n🎮 ¡Ambos equipos listos! El partido se simulará en breve."
            return ([mensaje], sesion)
        mensaje += "\nEsperando al otro jugador para que elija su equipo."
        return ([mensaje], None)

    if cmd == "/seleccionar_auto":
        disponible = sesion.pool_disponible_para(numero_origen)
        if not disponible:
            return (["❌ No hay patabolistas disponibles para elegir (ya fueron seleccionados)."], None)
        cantidad = min(MAX_JUGADORES_EQUIPO, len(disponible))
        porteros = [p for p in disponible if p.rol_preferido == Rol.PORTERO]
        resto = [p for p in disponible if p.rol_preferido != Rol.PORTERO]
        equipo = []
        if porteros and cantidad > 0:
            equipo.append(random.choice(porteros))
        candidatos = [p for p in disponible if p not in equipo]
        faltan = cantidad - len(equipo)
        if faltan > 0 and candidatos:
            equipo.extend(random.sample(candidatos, min(faltan, len(candidatos))))
        if not equipo:
            return (["❌ No se pudo armar el equipo automáticamente. Usa /pool y /seleccionar."], None)

        jugador_sesion = sesion.jugador_por_telefono(numero_origen)
        jugador_sesion.equipo = equipo
        sesion.actualizar_estado()
        _seleccionar_equipo_bot_si_aplica(sesion)

        mensaje = f"✅ Equipo ({jugador_sesion.nombre_equipo}) seleccionado automáticamente:\n"
        for j in equipo:
            mensaje += f"  - {j.nombre_con_id} ({j.rol_preferido.value})\n"
        if sesion.listas_para_simular():
            mensaje += "\n🎮 ¡Ambos equipos listos! El partido se simulará en breve."
            return ([mensaje], sesion)
        mensaje += "\nEsperando al otro jugador para que elija su equipo."
        return ([mensaje], None)

    if cmd == "/quitar":
        if len(partes) != 2:
            return (["❌ Uso: /quitar <id> o /q <id>\nEjemplo: /q P3\nDevuelve ese jugador al pool para elegir otro."], None)
        id_buscado = normalizar_id_patabolista(partes[1])
        jugador_sesion = sesion.jugador_por_telefono(numero_origen)
        if not jugador_sesion or not jugador_sesion.equipo:
            return (["❌ No tienes jugadores seleccionados. Usa /seleccionar o /seleccionar_auto."], None)
        en_equipo = [p for p in jugador_sesion.equipo if normalizar_id_patabolista(p.id) == id_buscado]
        if not en_equipo:
            return ([f"❌ {id_buscado} no está en tu equipo. Tus jugadores: {', '.join(p.id for p in jugador_sesion.equipo)}"], None)
        jugador_sesion.equipo = [p for p in jugador_sesion.equipo if normalizar_id_patabolista(p.id) != id_buscado]
        sesion.actualizar_estado()
        nombre_devuelto = en_equipo[0].nombre_con_id
        return ([f"✅ {nombre_devuelto} devuelto al pool. Usa /pool para ver disponibles y /seleccionar para elegir otro."], None)

    if cmd == "/equipo":
        jugador_sesion = sesion.jugador_por_telefono(numero_origen)
        if not jugador_sesion or not jugador_sesion.equipo:
            return (["❌ No tienes jugadores seleccionados aún. Usa /s o /a para elegir tu equipo."], None)
        mensaje = f"👥 Tu equipo: {jugador_sesion.nombre_equipo}\n"
        mensaje += "=" * 30 + "\n\n"
        for i, j in enumerate(jugador_sesion.equipo, 1):
            mensaje += f"{i}. {j.nombre_con_id} ({j.rol_preferido.value})\n"
        return ([mensaje], None)

    if cmd == "/estadisticas":
        if not sesion.ultimo_resultado:
            return (["❌ No hay partido jugado aún en esta sesión."], None)
        msg1 = formatear_resultado_whatsapp(
            sesion.ultimo_resultado,
            sesion.ultimo_nombre_a,
            sesion.ultimo_nombre_b,
        )
        msg2 = formatear_estadisticas_whatsapp(
            sesion.ultimo_equipo_a,
            sesion.ultimo_equipo_b,
            sesion.ultimo_nombre_a,
            sesion.ultimo_nombre_b,
        )
        return ([msg1, msg2], None)

    return (["❌ Comando no reconocido. Usa /ayuda o /h para ver comandos disponibles."], None)


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint para Railway"""
    return Response("OK", status=200)


@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """Endpoint principal para recibir mensajes de Twilio"""
    if request.method == 'GET':
        return Response("Webhook activo", status=200)

    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        url = request.url
        signature = request.headers.get('X-Twilio-Signature', '')
        if not validator.validate(url, request.form, signature):
            logger.warning("Request no válido de Twilio")
            return Response("Unauthorized", status=403)

    numero_origen = request.form.get('From', '')
    mensaje = request.form.get('Body', '').strip()
    logger.info(f"Mensaje recibido de {numero_origen}: {mensaje}")

    es_primera_interaccion = es_primera_vez(numero_origen)
    if es_primera_interaccion:
        registrar_interaccion(numero_origen)

    try:
        respuestas, sesion_simular = procesar_comando(mensaje, numero_origen)
    except Exception as e:
        logger.error(f"Error procesando comando: {e}", exc_info=True)
        respuestas = ["❌ Error procesando comando. Intenta de nuevo o usa /ayuda o /h."]
        sesion_simular = None

    # Primera interacción: siempre enviar al menos el mensaje de bienvenida
    if es_primera_interaccion:
        respuestas = [MENSAJE_BIENVENIDA] + (respuestas if respuestas else [])

    # Asegurar que siempre haya al menos un mensaje en la respuesta (p. ej. mensaje vacío o error)
    if not respuestas:
        respuestas = ["Escribí /h para ver los comandos disponibles."]

    twiml = MessagingResponse()
    for texto in respuestas:
        _log_mensaje_enviado(numero_origen, texto, via="TwiML")
        twiml.message(texto)

    if sesion_simular is not None:
        def lanzar_simulacion():
            time.sleep(1)
            _ejecutar_simulacion_y_enviar_a_ambos(sesion_simular)
        threading.Thread(target=lanzar_simulacion, daemon=True).start()

    return Response(str(twiml), mimetype='text/xml')


def _log_mensaje_enviado(destino: str, cuerpo: str, via: str = "API") -> None:
    """Registra en logs el envío de un mensaje a WhatsApp (cuerpo truncado si es largo)."""
    preview = cuerpo[:200] + "..." if len(cuerpo) > 200 else cuerpo
    preview_una_linea = preview.replace("\n", " ")
    logger.info("[WhatsApp %s] Enviando a %s: %s", via, destino, preview_una_linea)


def _enviar_un_mensaje_con_reintento(client: Client, body: str, from_: str, to: str, max_reintentos_429: int = 1) -> bool:
    """
    Envía un mensaje con la API de Twilio. Si Twilio devuelve 429 (Too Many Requests),
    espera y reintenta hasta max_reintentos_429 veces. Retorna True si se envió, False si falló.
    """
    for intento in range(max_reintentos_429 + 1):
        try:
            client.messages.create(body=body, from_=from_, to=to)
            return True
        except TwilioRestException as e:
            logger.warning(
                "Twilio API error: status=%s code=%s msg=%s uri=%s",
                e.status, e.code, e.msg, e.uri,
            )
            if e.status == 429 and intento < max_reintentos_429:
                espera = 4  # Sandbox: 1 msg cada 3 s; dar margen
                logger.info("429 Too Many Requests: esperando %s s antes de reintentar...", espera)
                time.sleep(espera)
            else:
                logger.error("Error enviando mensaje a %s: %s (code %s)", to, e.msg, e.code)
                return False
        except Exception as e:
            logger.error("Error enviando mensaje a %s: %s", to, e)
            return False
    return False


def enviar_mensajes_multiples(numero_destino: str, mensajes: List[str]):
    """
    Envía múltiples mensajes usando la API de Twilio directamente.
    Registra en logs cualquier error de la API (p. ej. 429 Too Many Requests).
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
        logger.error("Credenciales de Twilio no configuradas")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for mensaje in mensajes:
            _log_mensaje_enviado(numero_destino, mensaje, via="API")
            _enviar_un_mensaje_con_reintento(
                client, mensaje, TWILIO_WHATSAPP_NUMBER, numero_destino,
            )
            time.sleep(0.5)
    except Exception as e:
        logger.error("Error inicializando cliente de Twilio: %s", e)


def enviar_a_ambos_jugadores(numeros: List[str], mensaje: str):
    """
    Envía el mismo mensaje a todos los números de la lista.
    Registra en logs errores de la API (p. ej. 429). En sandbox respeta ~1 msg cada 3 s.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
        logger.error("Credenciales de Twilio no configuradas")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for numero in numeros:
            _log_mensaje_enviado(numero, mensaje, via="API")
            _enviar_un_mensaje_con_reintento(
                client, mensaje, TWILIO_WHATSAPP_NUMBER, numero,
            )
            time.sleep(3)  # Sandbox: 1 mensaje cada 3 segundos
    except Exception as e:
        logger.error("Error inicializando cliente de Twilio: %s", e)


def _ejecutar_simulacion_y_enviar_a_ambos(sesion: Sesion):
    """
    Ejecuta el partido, guarda resultado en la sesión y envía solo a jugadores humanos
    (excluye BOT): mensaje de inicio, evento por evento con latencia, resultado y estadísticas.
    """
    jugadores_list = list(sesion.jugadores.values())
    if len(jugadores_list) != 2:
        logger.warning("Simulación solicitada pero la sesión no tiene exactamente 2 jugadores")
        return
    jugador_a, jugador_b = jugadores_list[0], jugadores_list[1]
    equipo_a = jugador_a.equipo
    equipo_b = jugador_b.equipo
    numeros = [
        j.numero_telefono for j in (jugador_a, jugador_b)
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

    enviar_a_ambos_jugadores(numeros, "🎮 ¡Iniciando partido!")

    for evento in resultado.eventos:
        msg = formatear_evento_unico(evento)
        enviar_a_ambos_jugadores(numeros, msg)
        time.sleep(LATENCIA_ENTRE_EVENTOS_SEGUNDOS)

    resultado_msg = formatear_resultado_whatsapp(
        resultado, sesion.ultimo_nombre_a, sesion.ultimo_nombre_b
    )
    stats_msg = formatear_estadisticas_whatsapp(
        equipo_a, equipo_b, sesion.ultimo_nombre_a, sesion.ultimo_nombre_b
    )
    enviar_a_ambos_jugadores(numeros, resultado_msg)
    enviar_a_ambos_jugadores(numeros, stats_msg)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
