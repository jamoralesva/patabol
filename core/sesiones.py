"""
Gestión de sesiones de juego PATABOL (en memoria).
Cada sesión tiene un pool de patabolistas compartido y hasta 2 jugadores.
"""

import random
import string
import sys
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from core.patabol import Patabolista, GeneradorPool, ResultadoPartido

logger = logging.getLogger(__name__)

MAX_JUGADORES_EQUIPO = 5
MAX_JUGADORES_EN_SESION = 2
BOT_NUMERO_TELEFONO = "PATABOL_BOT"

NOMBRES_EQUIPO_POR_DEFECTO = [
    "Los Rayos", "Fieras FC", "Tormenta", "Acero", "Relámpagos",
    "Águilas", "Leones", "Tigres", "Viento Norte", "Fuego Sagrado",
    "Hielo", "Sombra", "Bravo", "Noble", "Lince"
]


def generar_sesion_id() -> str:
    caracteres = string.ascii_uppercase + string.digits
    return "".join(random.choice(caracteres) for _ in range(6))


def generar_nombre_equipo_aleatorio() -> str:
    return random.choice(NOMBRES_EQUIPO_POR_DEFECTO)


class EstadoSesion(Enum):
    ESPERANDO_JUGADORES = "esperando_jugadores"
    SELECCIONANDO_EQUIPOS = "seleccionando_equipos"
    AMBOS_LISTOS = "ambos_listos"
    PARTIDO_SIMULADO = "partido_simulado"


class EstadoEquipo(Enum):
    PENDIENTE_CONFIRMACION = "pendiente_confirmacion"
    CONFIRMADO = "confirmado"


@dataclass
class JugadorEnSesion:
    numero_telefono: str
    nickname: str
    nombre_equipo: str
    equipo: List[Patabolista] = field(default_factory=list)
    estado_equipo: "EstadoEquipo" = EstadoEquipo.PENDIENTE_CONFIRMACION

    def tiene_equipo_completo(self) -> bool:
        return len(self.equipo) >= 1

    def equipo_confirmado(self) -> bool:
        return self.estado_equipo == EstadoEquipo.CONFIRMADO


@dataclass
class Sesion:
    session_id: str
    pool: List[Patabolista]
    jugadores: Dict[str, JugadorEnSesion] = field(default_factory=dict)
    estado: EstadoSesion = EstadoSesion.ESPERANDO_JUGADORES
    creador_numero: Optional[str] = None
    ultimo_resultado: Optional[ResultadoPartido] = None
    ultimo_equipo_a: List[Patabolista] = field(default_factory=list)
    ultimo_equipo_b: List[Patabolista] = field(default_factory=list)
    ultimo_nombre_a: str = ""
    ultimo_nombre_b: str = ""

    def jugador_por_telefono(self, numero: str) -> Optional[JugadorEnSesion]:
        return self.jugadores.get(numero)

    def patabolistas_ya_seleccionados(self) -> List[Patabolista]:
        elegidos = []
        for j in self.jugadores.values():
            elegidos.extend(j.equipo)
        return elegidos

    def pool_sin_seleccionar(self) -> List[Patabolista]:
        ya_elegidos = set(id(p) for p in self.patabolistas_ya_seleccionados())
        return [p for p in self.pool if id(p) not in ya_elegidos]

    def pool_disponible_para(self, numero_telefono: str) -> List[Patabolista]:
        elegidos_por_otros = []
        for num, j in self.jugadores.items():
            if num != numero_telefono:
                elegidos_por_otros.extend(j.equipo)
        ids_otros = set(id(p) for p in elegidos_por_otros)
        return [p for p in self.pool if id(p) not in ids_otros]

    def actualizar_estado(self) -> None:
        if len(self.jugadores) < MAX_JUGADORES_EN_SESION:
            self.estado = EstadoSesion.ESPERANDO_JUGADORES
            return
        todos_listos = all(j.tiene_equipo_completo() for j in self.jugadores.values())
        if todos_listos:
            self.estado = EstadoSesion.AMBOS_LISTOS
        else:
            self.estado = EstadoSesion.SELECCIONANDO_EQUIPOS

    def listas_para_simular(self) -> bool:
        if len(self.jugadores) != MAX_JUGADORES_EN_SESION:
            return False
        return all(j.tiene_equipo_completo() for j in self.jugadores.values())

    def equipos_confirmados(self) -> bool:
        if len(self.jugadores) != MAX_JUGADORES_EN_SESION:
            return False
        return all(j.tiene_equipo_completo() and j.equipo_confirmado() for j in self.jugadores.values())


_sesiones_activas: Dict[str, Sesion] = {}
_usuario_a_sesion: Dict[str, str] = {}


def crear_sesion_por_defecto() -> Sesion:
    session_id = generar_sesion_id()
    while session_id in _sesiones_activas:
        session_id = generar_sesion_id()
    generador = GeneradorPool()
    pool = generador.generar_pool(15)
    sesion = Sesion(
        session_id=session_id,
        pool=pool,
        jugadores={},
        estado=EstadoSesion.ESPERANDO_JUGADORES,
        creador_numero=None,
    )
    _sesiones_activas[session_id] = sesion
    logger.info("Sesión por defecto creada - Código: %s", session_id)
    print(f"\n>>> Sesión por defecto - Código: {session_id} <<<\n", file=sys.stderr, flush=True)
    return sesion


def crear_sesion(numero_creador: str, nickname_creador: str, nombre_equipo: Optional[str] = None) -> Sesion:
    session_id = generar_sesion_id()
    while session_id in _sesiones_activas:
        session_id = generar_sesion_id()
    generador = GeneradorPool()
    pool = generador.generar_pool(15)
    nombre_equipo = nombre_equipo or generar_nombre_equipo_aleatorio()
    jugador = JugadorEnSesion(
        numero_telefono=numero_creador,
        nickname=nickname_creador,
        nombre_equipo=nombre_equipo,
        equipo=[],
    )
    sesion = Sesion(
        session_id=session_id,
        pool=pool,
        jugadores={numero_creador: jugador},
        estado=EstadoSesion.SELECCIONANDO_EQUIPOS,
        creador_numero=numero_creador,
    )
    _sesiones_activas[session_id] = sesion
    _usuario_a_sesion[numero_creador] = session_id
    logger.info("Sesión creada - Código: %s", session_id)
    print(f"\n>>> Sesión creada - Código: {session_id} <<<\n", file=sys.stderr, flush=True)
    return sesion


def unirse_sesion(
    session_id: str,
    numero_telefono: str,
    nickname: str,
    nombre_equipo: Optional[str] = None,
) -> tuple:
    session_id = session_id.upper().strip()
    if session_id not in _sesiones_activas:
        return False, f"No existe una sesión con el código {session_id}.", None
    sesion = _sesiones_activas[session_id]
    if len(sesion.jugadores) >= MAX_JUGADORES_EN_SESION:
        return False, "La sesión ya tiene el máximo de jugadores.", None
    if numero_telefono in sesion.jugadores:
        return False, "Ya estás en esta sesión.", None
    nombre_equipo = nombre_equipo or generar_nombre_equipo_aleatorio()
    jugador = JugadorEnSesion(
        numero_telefono=numero_telefono,
        nickname=nickname,
        nombre_equipo=nombre_equipo,
        equipo=[],
    )
    sesion.jugadores[numero_telefono] = jugador
    _usuario_a_sesion[numero_telefono] = session_id
    sesion.actualizar_estado()
    return True, f"Te uniste a la sesión como '{nickname}' (equipo: {nombre_equipo}).", sesion


def agregar_bot_a_sesion(
    session_id: str,
    numero_creador: str,
    nombre_equipo: Optional[str] = None,
) -> tuple:
    session_id = session_id.upper().strip()
    if session_id not in _sesiones_activas:
        return False, f"No existe una sesión con el código {session_id}.", None
    sesion = _sesiones_activas[session_id]
    if sesion.creador_numero is None or sesion.creador_numero != numero_creador:
        return False, "Solo el creador de la sesión puede agregar a la IA.", None
    if len(sesion.jugadores) >= MAX_JUGADORES_EN_SESION:
        return False, "La sesión ya tiene el máximo de jugadores.", None
    if BOT_NUMERO_TELEFONO in sesion.jugadores:
        return False, "La IA ya está en esta sesión.", None
    nombre_equipo = nombre_equipo or generar_nombre_equipo_aleatorio()
    jugador_bot = JugadorEnSesion(
        numero_telefono=BOT_NUMERO_TELEFONO,
        nickname="IA",
        nombre_equipo=nombre_equipo,
        equipo=[],
    )
    sesion.jugadores[BOT_NUMERO_TELEFONO] = jugador_bot
    sesion.actualizar_estado()
    return True, f"✅ IA unida a la sesión (equipo: {nombre_equipo}). Elige tu equipo con /s o /a; la IA elegirá el suyo automáticamente.", sesion


def obtener_sesion_por_id(session_id: str) -> Optional[Sesion]:
    return _sesiones_activas.get(session_id.upper().strip())


def obtener_sesion_de_usuario(numero_telefono: str) -> Optional[Sesion]:
    sid = _usuario_a_sesion.get(numero_telefono)
    if not sid:
        return None
    return _sesiones_activas.get(sid)


def salir_sesion(numero_telefono: str) -> None:
    sid = _usuario_a_sesion.pop(numero_telefono, None)
    if sid and sid in _sesiones_activas:
        sesion = _sesiones_activas[sid]
        sesion.jugadores.pop(numero_telefono, None)
        sesion.actualizar_estado()
        humanos = [k for k in sesion.jugadores if k != BOT_NUMERO_TELEFONO]
        if len(humanos) == 0:
            _sesiones_activas.pop(sid, None)
            logger.info("Sesión %s eliminada automáticamente (sin jugadores humanos).", sid)


def marcar_partido_simulado(session_id: str) -> None:
    sesion = _sesiones_activas.get(session_id)
    if sesion:
        sesion.estado = EstadoSesion.PARTIDO_SIMULADO
