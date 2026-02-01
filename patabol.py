"""
PATABOL - Juego de simulación de fútbol
Lógica del dominio del juego (sin presentación)
"""

import random
from enum import Enum
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


# ================================
# DOMINIO DEL JUEGO
# ================================

class Rol(Enum):
    """Roles de los patabolistas"""
    PORTERO = "Portero"
    DEFENSA = "Defensa"
    MEDIO = "Medio"
    DELANTERO = "Delantero"


@dataclass
class Patabolista:
    """Representa un patabolista con sus atributos y estadísticas"""
    id: str
    nombre: str
    rol_preferido: Rol
    control: int
    velocidad: int
    fuerza: int
    regate: int
    magia: int  # Atributo oculto
    
    # Estadísticas de partido
    toques: int = 0
    pases: int = 0
    regates_exitosos: int = 0
    robos: int = 0
    faltas: int = 0
    goles: int = 0
    atajadas: int = 0
    
    def reset_estadisticas(self):
        """Reinicia las estadísticas del jugador"""
        self.toques = 0
        self.pases = 0
        self.regates_exitosos = 0
        self.robos = 0
        self.faltas = 0
        self.goles = 0
        self.atajadas = 0
    
    def obtener_atributos_visibles(self) -> Dict[str, int]:
        """Retorna solo los atributos visibles (sin magia)"""
        return {
            "control": self.control,
            "velocidad": self.velocidad,
            "fuerza": self.fuerza,
            "regate": self.regate
        }
    
    def obtener_estadisticas(self) -> Dict[str, int]:
        """Retorna las estadísticas del jugador"""
        return {
            "toques": self.toques,
            "pases": self.pases,
            "regates_exitosos": self.regates_exitosos,
            "robos": self.robos,
            "faltas": self.faltas,
            "goles": self.goles,
            "atajadas": self.atajadas
        }

    @property
    def nombre_con_id(self) -> str:
        """Nombre del patabolista con su ID entre corchetes: 'Nombre [P1]'"""
        return f"{self.nombre} [{self.id}]"


class GeneradorPool:
    """Genera pools de patabolistas con distribución realista"""
    
    NOMBRES_POSIBLES = [
        "Leo", "Bruno", "Carlos", "Diego", "Luis", "Miguel", "Javier",
        "Andrés", "Fernando", "Ricardo", "Sergio", "Alejandro", "Roberto",
        "Daniel", "Pablo", "Manuel", "Francisco", "Antonio", "José", "Juan"
    ]
    
    APELLIDOS_POSIBLES = [
        "Rayo", "Fierro", "Veloz", "Torre", "Acero", "Rápido", "Fuerte",
        "Ágil", "Noble", "Bravo", "Lince", "Tigre", "León", "Águila",
        "Trueno", "Relámpago", "Viento", "Fuego", "Hielo", "Sombra"
    ]
    
    def __init__(self, seed: Optional[int] = None):
        """Inicializa el generador con una semilla opcional"""
        if seed is not None:
            random.seed(seed)
        self.nombres_usados = set()
    
    def _generar_nombre_unico(self) -> str:
        """Genera un nombre único combinando nombre y apellido"""
        while True:
            nombre = random.choice(self.NOMBRES_POSIBLES)
            apellido = random.choice(self.APELLIDOS_POSIBLES)
            nombre_completo = f"{nombre} {apellido}"
            if nombre_completo not in self.nombres_usados:
                self.nombres_usados.add(nombre_completo)
                return nombre_completo
    
    def _generar_magia(self) -> int:
        """Genera magia según distribución: 60% 1-3, 30% 4-6, 9% 7-8, 1% 9-10"""
        rand = random.random()
        if rand < 0.60:
            return random.randint(1, 3)
        elif rand < 0.90:
            return random.randint(4, 6)
        elif rand < 0.99:
            return random.randint(7, 8)
        else:
            return random.randint(9, 10)
    
    def _generar_atributos_por_rol(self, rol: Rol) -> Tuple[int, int, int, int]:
        """Genera atributos influenciados por el rol"""
        base = random.randint(1, 10)
        
        if rol == Rol.PORTERO:
            # Porteros: alta fuerza, control medio-alto
            control = min(10, base + random.randint(0, 3))
            velocidad = random.randint(2, 6)
            fuerza = min(10, base + random.randint(2, 4))
            regate = random.randint(1, 5)
        elif rol == Rol.DEFENSA:
            # Defensas: alta fuerza, control medio
            control = random.randint(3, 7)
            velocidad = random.randint(3, 7)
            fuerza = min(10, base + random.randint(1, 3))
            regate = random.randint(2, 6)
        elif rol == Rol.MEDIO:
            # Medios: balanceados
            control = min(10, base + random.randint(0, 2))
            velocidad = random.randint(4, 8)
            fuerza = random.randint(3, 7)
            regate = min(10, base + random.randint(0, 2))
        else:  # DELANTERO
            # Delanteros: alta velocidad y regate
            control = random.randint(4, 8)
            velocidad = min(10, base + random.randint(1, 3))
            fuerza = random.randint(2, 6)
            regate = min(10, base + random.randint(2, 4))
        
        return (
            max(1, min(10, control)),
            max(1, min(10, velocidad)),
            max(1, min(10, fuerza)),
            max(1, min(10, regate))
        )
    
    def generar_pool(self, cantidad: int = 15) -> List[Patabolista]:
        """Genera un pool de patabolistas con distribución de roles"""
        pool = []
        
        # Distribución: 2 Porteros, 4 Defensas, 5 Medios, 4 Delanteros
        roles_distribucion = [
            Rol.PORTERO, Rol.PORTERO,
            Rol.DEFENSA, Rol.DEFENSA, Rol.DEFENSA, Rol.DEFENSA,
            Rol.MEDIO, Rol.MEDIO, Rol.MEDIO, Rol.MEDIO, Rol.MEDIO,
            Rol.DELANTERO, Rol.DELANTERO, Rol.DELANTERO, Rol.DELANTERO
        ]
        
        # Ajustar si la cantidad es diferente
        if cantidad != 15:
            roles_distribucion = self._ajustar_distribucion(cantidad)
        
        for i, rol in enumerate(roles_distribucion[:cantidad]):
            nombre = self._generar_nombre_unico()
            control, velocidad, fuerza, regate = self._generar_atributos_por_rol(rol)
            magia = self._generar_magia()
            
            patabolista = Patabolista(
                id=f"P{i+1}",
                nombre=nombre,
                rol_preferido=rol,
                control=control,
                velocidad=velocidad,
                fuerza=fuerza,
                regate=regate,
                magia=magia
            )
            pool.append(patabolista)
        
        return pool
    
    def _ajustar_distribucion(self, cantidad: int) -> List[Rol]:
        """Ajusta la distribución de roles para cantidades diferentes a 15"""
        roles = []
        porteros = max(1, cantidad // 8)
        defensas = max(1, cantidad // 4)
        medios = max(1, cantidad // 3)
        delanteros = cantidad - porteros - defensas - medios
        
        roles.extend([Rol.PORTERO] * porteros)
        roles.extend([Rol.DEFENSA] * defensas)
        roles.extend([Rol.MEDIO] * medios)
        roles.extend([Rol.DELANTERO] * delanteros)
        
        return roles[:cantidad]


@dataclass
class Evento:
    """Representa un evento durante el partido"""
    minuto: int
    segundo: int
    descripcion: str
    tipo: str  # "gol", "falta", "robo", "pase", "regate", "magia"


@dataclass
class ResultadoPartido:
    """Resultado completo de un partido"""
    goles_equipo_a: int
    goles_equipo_b: int
    eventos: List[Evento]
    estadisticas_equipo_a: Dict[str, Dict[str, int]]
    estadisticas_equipo_b: Dict[str, Dict[str, int]]
    jugador_del_partido: Optional[Patabolista] = None


class SimuladorPartido:
    """Simula un partido de PATABOL"""
    
    DURACION_TOTAL = 300  # 5 minutos
    PASO_TIEMPO = 10  # 10 segundos por estado
    TOTAL_ESTADOS = 30
    
    def __init__(self, equipo_a: List[Patabolista], equipo_b: List[Patabolista]):
        """Inicializa el simulador con dos equipos"""
        self.equipo_a = equipo_a
        self.equipo_b = equipo_b
        self.posesion_equipo_a = True
        self.jugador_con_pelota: Optional[Patabolista] = None
        self.goles_a = 0
        self.goles_b = 0
        self.eventos: List[Evento] = []
        self.estado_actual = 0
        
        # Resetear estadísticas
        for jugador in equipo_a + equipo_b:
            jugador.reset_estadisticas()
    
    def _obtener_portero_rival(self) -> Patabolista:
        """Obtiene el portero del equipo rival"""
        equipo_rival = self.equipo_b if self.posesion_equipo_a else self.equipo_a
        for jugador in equipo_rival:
            if jugador.rol_preferido == Rol.PORTERO:
                return jugador
        # Si no hay portero, retorna el primer jugador
        return equipo_rival[0]
    
    def _obtener_jugadores_rivales(self) -> List[Patabolista]:
        """Obtiene los jugadores del equipo rival"""
        return self.equipo_b if self.posesion_equipo_a else self.equipo_a
    
    def _calcular_probabilidad_exito(self, atributo: int, base: float = 0.5) -> float:
        """Calcula probabilidad de éxito basada en atributo"""
        return min(0.95, base + (atributo - 5) * 0.1)
    
    def _aplicar_magia(self, jugador: Patabolista, probabilidad_base: float) -> Tuple[float, bool]:
        """Aplica efecto de magia en la probabilidad. Retorna (prob_ajustada, hubo_magia)"""
        if jugador.magia >= 9:
            # Legendario: boost significativo
            return min(0.98, probabilidad_base + 0.3), True
        elif jugador.magia >= 7:
            # Alto: boost moderado
            return min(0.95, probabilidad_base + 0.15), True
        elif jugador.magia >= 4:
            # Medio: boost pequeño
            return min(0.90, probabilidad_base + 0.05), False
        else:
            return probabilidad_base, False
    
    def _avanzar_con_pelota(self, jugador: Patabolista) -> str:
        """Intenta avanzar con la pelota"""
        jugador.toques += 1
        prob = self._calcular_probabilidad_exito(jugador.control, 0.6)
        prob, hubo_magia = self._aplicar_magia(jugador, prob)
        
        if random.random() < prob:
            return "conservar_pelota"
        else:
            return "perder_pelota"
    
    def _intentar_quitar_pelota(self, atacante: Patabolista, defensor: Patabolista) -> str:
        """Intenta quitar la pelota"""
        atacante.toques += 1
        defensor.toques += 1
        
        # Probabilidad basada en regate del atacante vs fuerza del defensor
        prob_ataque = self._calcular_probabilidad_exito(atacante.regate, 0.5)
        prob_defensa = self._calcular_probabilidad_exito(defensor.fuerza, 0.5)
        
        prob_final = prob_ataque - (prob_defensa - 0.5) * 0.3
        prob_final, hubo_magia = self._aplicar_magia(atacante, prob_final)
        
        # Probabilidad de falta (mayor con fuerza alta del defensor)
        prob_falta = 0.1 + (defensor.fuerza - 5) * 0.05
        
        if random.random() < prob_falta:
            defensor.faltas += 1
            return "falta"
        elif random.random() < prob_final:
            return "conservar_pelota"
        else:
            defensor.robos += 1
            return "perder_pelota"
    
    def _intentar_gol(self, delantero: Patabolista, portero: Patabolista) -> str:
        """Intenta hacer gol (solo delanteros)"""
        delantero.toques += 1
        
        # Probabilidad basada en control y regate del delantero vs control del portero
        prob_gol = self._calcular_probabilidad_exito(delantero.control, 0.3)
        prob_gol += self._calcular_probabilidad_exito(delantero.regate, 0.2)
        prob_atajada = self._calcular_probabilidad_exito(portero.control, 0.4)
        
        prob_final = prob_gol - (prob_atajada - 0.4) * 0.4
        prob_final, hubo_magia = self._aplicar_magia(delantero, prob_final)
        
        if random.random() < prob_final:
            delantero.goles += 1
            return "gol"
        else:
            portero.atajadas += 1
            return "atajada"
    
    def _lanzar_pelota(self, jugador: Patabolista) -> str:
        """Intenta lanzar la pelota a un compañero"""
        jugador.toques += 1
        jugador.pases += 1
        
        prob = self._calcular_probabilidad_exito(jugador.control, 0.7)
        prob, hubo_magia = self._aplicar_magia(jugador, prob)
        
        if random.random() < prob:
            return "conservar_pelota"
        else:
            return "perder_pelota"
    
    def _seleccionar_accion(self, jugador: Patabolista) -> str:
        """Selecciona una acción aleatoria para el jugador"""
        acciones = ["avanzar_con_pelota", "lanzar_pelota"]
        
        # Si es delantero y está cerca del área, puede intentar gol
        if jugador.rol_preferido == Rol.DELANTERO and random.random() < 0.3:
            return "intentar_gol"
        
        # Si hay defensores cerca, puede intentar quitar
        if random.random() < 0.4:
            return "intentar_quitar_pelota"
        
        return random.choice(acciones)
    
    def _seleccionar_jugador_aleatorio(self, equipo: List[Patabolista]) -> Patabolista:
        """Selecciona un jugador aleatorio del equipo"""
        return random.choice(equipo)
    
    def _procesar_estado(self, estado: int) -> None:
        """Procesa un estado del partido (10 segundos)"""
        segundo = estado * self.PASO_TIEMPO
        minuto = segundo // 60
        
        # Si no hay jugador con pelota, seleccionar uno
        if self.jugador_con_pelota is None:
            equipo_actual = self.equipo_a if self.posesion_equipo_a else self.equipo_b
            self.jugador_con_pelota = self._seleccionar_jugador_aleatorio(equipo_actual)
        
        jugador = self.jugador_con_pelota
        accion = self._seleccionar_accion(jugador)
        resultado = None
        hubo_magia = False
        
        # Ejecutar acción
        if accion == "avanzar_con_pelota":
            resultado = self._avanzar_con_pelota(jugador)
            if resultado == "conservar_pelota":
                self.eventos.append(Evento(
                    minuto, segundo % 60,
                    f"{jugador.nombre_con_id} avanza con la pelota",
                    "avance"
                ))
        
        elif accion == "lanzar_pelota":
            resultado = self._lanzar_pelota(jugador)
            if resultado == "conservar_pelota":
                compañero = self._seleccionar_jugador_aleatorio(
                    self.equipo_a if self.posesion_equipo_a else self.equipo_b
                )
                jugador.pases += 1
                compañero.toques += 1
                self.jugador_con_pelota = compañero
                self.eventos.append(Evento(
                    minuto, segundo % 60,
                    f"{jugador.nombre_con_id} pasa a {compañero.nombre_con_id}",
                    "pase"
                ))
        
        elif accion == "intentar_quitar_pelota":
            defensor = self._seleccionar_jugador_aleatorio(self._obtener_jugadores_rivales())
            resultado = self._intentar_quitar_pelota(jugador, defensor)
            
            if resultado == "falta":
                defensor.faltas += 1
                self.eventos.append(Evento(
                    minuto, segundo % 60,
                    f"Falta de {defensor.nombre_con_id} sobre {jugador.nombre_con_id}",
                    "falta"
                ))
            elif resultado == "perder_pelota":
                defensor.robos += 1
                self.posesion_equipo_a = not self.posesion_equipo_a
                self.jugador_con_pelota = defensor
                self.eventos.append(Evento(
                    minuto, segundo % 60,
                    f"{defensor.nombre_con_id} roba la pelota a {jugador.nombre_con_id}",
                    "robo"
                ))
            else:
                jugador.regates_exitosos += 1
                self.eventos.append(Evento(
                    minuto, segundo % 60,
                    f"{jugador.nombre_con_id} regatea a {defensor.nombre_con_id}",
                    "regate"
                ))
        
        elif accion == "intentar_gol":
            if jugador.rol_preferido == Rol.DELANTERO:
                portero = self._obtener_portero_rival()
                resultado = self._intentar_gol(jugador, portero)
                
                if resultado == "gol":
                    if self.posesion_equipo_a:
                        self.goles_a += 1
                    else:
                        self.goles_b += 1
                    
                    # Verificar si hubo magia
                    prob_magia = jugador.magia / 10.0
                    hubo_magia = random.random() < prob_magia
                    
                    descripcion = f"⚽ GOOOL de {jugador.nombre_con_id}!"
                    if hubo_magia or jugador.magia >= 7:
                        descripcion += " ¡Jugada ÉPICA con toque mágico!"
                    
                    self.eventos.append(Evento(
                        minuto, segundo % 60,
                        descripcion,
                        "gol"
                    ))
                    self.jugador_con_pelota = None
                else:
                    self.eventos.append(Evento(
                        minuto, segundo % 60,
                        f"{portero.nombre_con_id} ataja el intento de {jugador.nombre_con_id}",
                        "atajada"
                    ))
                    self.jugador_con_pelota = None
        
        # Si perdió la pelota, cambiar posesión
        if resultado == "perder_pelota" and accion != "intentar_quitar_pelota":
            self.posesion_equipo_a = not self.posesion_equipo_a
            self.jugador_con_pelota = None
    
    def simular(self) -> ResultadoPartido:
        """Simula el partido completo"""
        # Inicializar con posesión aleatoria
        self.posesion_equipo_a = random.random() < 0.5
        self.jugador_con_pelota = None
        
        # Simular los 30 estados
        for estado in range(self.TOTAL_ESTADOS):
            self._procesar_estado(estado)
        
        # Calcular estadísticas
        stats_a = {jugador.id: jugador.obtener_estadisticas() for jugador in self.equipo_a}
        stats_b = {jugador.id: jugador.obtener_estadisticas() for jugador in self.equipo_b}
        
        # Determinar jugador del partido
        todos_jugadores = self.equipo_a + self.equipo_b
        jugador_del_partido = max(
            todos_jugadores,
            key=lambda j: j.goles * 3 + j.regates_exitosos * 2 + j.robos + j.pases
        )
        
        return ResultadoPartido(
            goles_equipo_a=self.goles_a,
            goles_equipo_b=self.goles_b,
            eventos=self.eventos,
            estadisticas_equipo_a=stats_a,
            estadisticas_equipo_b=stats_b,
            jugador_del_partido=jugador_del_partido
        )
