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

from patabol import Patabolista, GeneradorPool, ResultadoPartido

logger = logging.getLogger(__name__)

# Máximo de jugadores por equipo (selección flexible: 1 a MAX_JUGADORES_EQUIPO)
MAX_JUGADORES_EQUIPO = 5
MAX_JUGADORES_EN_SESION = 2

# Identificador del jugador virtual (IA). No se envían mensajes WhatsApp a este "número".
BOT_NUMERO_TELEFONO = "PATABOL_BOT"

NOMBRES_EQUIPO_POR_DEFECTO = [
    "Los Rayos", "Fieras FC", "Tormenta", "Acero", "Relámpagos",
    "Águilas", "Leones", "Tigres", "Viento Norte", "Fuego Sagrado",
    "Hielo", "Sombra", "Bravo", "Noble", "Lince"
]


def generar_sesion_id() -> str:
    """Genera un código de sesión de 6 caracteres alfanuméricos."""
    caracteres = string.ascii_uppercase + string.digits
    return "".join(random.choice(caracteres) for _ in range(6))


def generar_nombre_equipo_aleatorio() -> str:
    """Genera un nombre de equipo por defecto aleatorio."""
    return random.choice(NOMBRES_EQUIPO_POR_DEFECTO)


class EstadoSesion(Enum):
    ESPERANDO_JUGADORES = "esperando_jugadores"
    SELECCIONANDO_EQUIPOS = "seleccionando_equipos"
    AMBOS_LISTOS = "ambos_listos"
    PARTIDO_SIMULADO = "partido_simulado"


@dataclass
class JugadorEnSesion:
    """Jugador dentro de una sesión: nickname, nombre del equipo y patabolistas elegidos."""
    numero_telefono: str
    nickname: str
    nombre_equipo: str
    equipo: List[Patabolista] = field(default_factory=list)

    def tiene_equipo_completo(self) -> bool:
        """True si ya confirmó su selección (al menos 1 jugador)."""
        return len(self.equipo) >= 1


@dataclass
class Sesion:
    """Sesión de juego: ID, pool de patabolistas y jugadores."""
    session_id: str
    pool: List[Patabolista]
    jugadores: Dict[str, JugadorEnSesion] = field(default_factory=dict)  # clave: numero_telefono
    estado: EstadoSesion = EstadoSesion.ESPERANDO_JUGADORES
    creador_numero: Optional[str] = None  # Quien creó la sesión (solo él puede agregar IA)
    # Último partido (para /estadisticas)
    ultimo_resultado: Optional[ResultadoPartido] = None
    ultimo_equipo_a: List[Patabolista] = field(default_factory=list)
    ultimo_equipo_b: List[Patabolista] = field(default_factory=list)
    ultimo_nombre_a: str = ""
    ultimo_nombre_b: str = ""

    def jugador_por_telefono(self, numero: str) -> Optional[JugadorEnSesion]:
        return self.jugadores.get(numero)

    def patabolistas_ya_seleccionados(self) -> List[Patabolista]:
        """Patabolistas ya elegidos por cualquier jugador en esta sesión."""
        elegidos = []
        for j in self.jugadores.values():
            elegidos.extend(j.equipo)
        return elegidos

    def pool_sin_seleccionar(self) -> List[Patabolista]:
        """Pool de patabolistas que nadie ha seleccionado aún (para mostrar en /pool)."""
        ya_elegidos = set(id(p) for p in self.patabolistas_ya_seleccionados())
        return [p for p in self.pool if id(p) not in ya_elegidos]

    def pool_disponible_para(self, numero_telefono: str) -> List[Patabolista]:
        """Pool disponible para un jugador: los que no han sido elegidos por el OTRO jugador (él puede re-elegir)."""
        elegidos_por_otros = []
        for num, j in self.jugadores.items():
            if num != numero_telefono:
                elegidos_por_otros.extend(j.equipo)
        ids_otros = set(id(p) for p in elegidos_por_otros)
        return [p for p in self.pool if id(p) not in ids_otros]

    def actualizar_estado(self) -> None:
        """Actualiza estado según si ambos tienen al menos 1 jugador seleccionado."""
        if len(self.jugadores) < MAX_JUGADORES_EN_SESION:
            self.estado = EstadoSesion.ESPERANDO_JUGADORES
            return
        todos_listos = all(j.tiene_equipo_completo() for j in self.jugadores.values())
        if todos_listos:
            self.estado = EstadoSesion.AMBOS_LISTOS
        else:
            self.estado = EstadoSesion.SELECCIONANDO_EQUIPOS

    def listas_para_simular(self) -> bool:
        """True si hay 2 jugadores y ambos tienen al menos 1 patabolista seleccionado."""
        if len(self.jugadores) != MAX_JUGADORES_EN_SESION:
            return False
        return all(j.tiene_equipo_completo() for j in self.jugadores.values())


# Almacén en memoria: session_id -> Sesion
_sesiones_activas: Dict[str, Sesion] = {}
# numero_telefono -> session_id (para saber en qué sesión está cada usuario)
_usuario_a_sesion: Dict[str, str] = {}


def crear_sesion_por_defecto() -> Sesion:
    """
    Crea la sesión por defecto al iniciar la aplicación (sin jugadores).
    Imprime el código de sesión en consola.
    """
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
    """
    Crea una nueva sesión con pool generado.
    El creador es el primer jugador. Imprime el Session ID en consola.
    """
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
    # Salida a stderr y flush para que se vea en consola siempre (Flask/gunicorn bufferizan stdout)
    print(f"\n>>> Sesión creada - Código: {session_id} <<<\n", file=sys.stderr, flush=True)

    return sesion


def unirse_sesion(
    session_id: str,
    numero_telefono: str,
    nickname: str,
    nombre_equipo: Optional[str] = None,
) -> tuple:
    """
    Une a un jugador a una sesión existente.
    Retorna (éxito, mensaje, sesión o None).
    """
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
    """
    Agrega al jugador virtual (IA) a la sesión. Solo el creador puede hacerlo.
    Retorna (éxito, mensaje, sesión o None).
    """
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
    """Obtiene una sesión por su código."""
    return _sesiones_activas.get(session_id.upper().strip())


def obtener_sesion_de_usuario(numero_telefono: str) -> Optional[Sesion]:
    """Obtiene la sesión en la que participa el usuario, si existe."""
    sid = _usuario_a_sesion.get(numero_telefono)
    if not sid:
        return None
    return _sesiones_activas.get(sid)


def salir_sesion(numero_telefono: str) -> None:
    """Quita al usuario de su sesión actual. Si no queda ningún humano, elimina la sesión."""
    sid = _usuario_a_sesion.pop(numero_telefono, None)
    if sid and sid in _sesiones_activas:
        sesion = _sesiones_activas[sid]
        sesion.jugadores.pop(numero_telefono, None)
        sesion.actualizar_estado()
        # Eliminar sesión si no queda nadie o solo queda la IA
        humanos = [k for k in sesion.jugadores if k != BOT_NUMERO_TELEFONO]
        if len(humanos) == 0:
            _sesiones_activas.pop(sid, None)
            logger.info("Sesión %s eliminada automáticamente (sin jugadores humanos).", sid)


def marcar_partido_simulado(session_id: str) -> None:
    """Marca la sesión como partido ya simulado."""
    sesion = _sesiones_activas.get(session_id)
    if sesion:
        sesion.estado = EstadoSesion.PARTIDO_SIMULADO
