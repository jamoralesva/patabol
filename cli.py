"""
Interfaz de línea de comandos para PATABOL
Maneja toda la interacción con el usuario a través de la terminal
"""

import random
import json
from typing import List

from patabol import (
    Patabolista,
    GeneradorPool,
    SimuladorPartido,
    ResultadoPartido,
    Rol
)


class InterfazCLI:
    """Interfaz de línea de comandos para PATABOL"""
    
    def __init__(self):
        self.pool: List[Patabolista] = []
        self.equipo_usuario: List[Patabolista] = []
        self.equipo_rival: List[Patabolista] = []
        self.generador = GeneradorPool()
    
    def mostrar_separador(self):
        """Muestra un separador visual"""
        print("\n" + "=" * 60 + "\n")
    
    def mostrar_pool(self):
        """Muestra el pool de patabolistas disponibles"""
        if not self.pool:
            print("No hay pool generado. Genera uno primero.")
            return
        
        print("\n📋 POOL DE PATABOLISTAS DISPONIBLES")
        print("-" * 60)
        for i, patabolista in enumerate(self.pool, 1):
            attrs = patabolista.obtener_atributos_visibles()
            print(f"{i:2d}. {patabolista.nombre_con_id} | "
                  f"Rol: {patabolista.rol_preferido.value:10s} | "
                  f"C:{attrs['control']} V:{attrs['velocidad']} "
                  f"F:{attrs['fuerza']} R:{attrs['regate']}")
    
    def seleccionar_equipo(self, nombre_equipo: str = "Tu Equipo") -> List[Patabolista]:
        """Permite seleccionar 5 jugadores para un equipo"""
        equipo = []
        disponibles = self.pool.copy()
        
        print(f"\n⚽ Selección de jugadores para {nombre_equipo}")
        print("Necesitas seleccionar 5 jugadores (1 portero, 4 de campo)")
        
        roles_necesarios = [Rol.PORTERO] + [None] * 4  # 1 portero, 4 cualquiera
        
        for i in range(5):
            self.mostrar_separador()
            print(f"Selección {i+1}/5")
            
            if i == 0:
                print("Debes seleccionar un PORTERO")
                porteros_disponibles = [p for p in disponibles if p.rol_preferido == Rol.PORTERO]
                if not porteros_disponibles:
                    print("⚠️  No hay porteros disponibles. Selecciona cualquier jugador.")
                    porteros_disponibles = disponibles
            
            print("\nJugadores disponibles:")
            for idx, jugador in enumerate(disponibles, 1):
                attrs = jugador.obtener_atributos_visibles()
                print(f"  {idx}. {jugador.nombre_con_id} "
                      f"({jugador.rol_preferido.value}) - "
                      f"C:{attrs['control']} V:{attrs['velocidad']} "
                      f"F:{attrs['fuerza']} R:{attrs['regate']}")
            
            while True:
                try:
                    seleccion = input(f"\nSelecciona jugador {i+1}/5 (número o 'q' para salir): ").strip()
                    if seleccion.lower() == 'q':
                        return []
                    
                    idx = int(seleccion) - 1
                    if 0 <= idx < len(disponibles):
                        jugador_seleccionado = disponibles.pop(idx)
                        equipo.append(jugador_seleccionado)
                        print(f"✅ {jugador_seleccionado.nombre_con_id} agregado al equipo")
                        break
                    else:
                        print("❌ Número inválido. Intenta de nuevo.")
                except ValueError:
                    print("❌ Entrada inválida. Ingresa un número.")
        
        return equipo
    
    def generar_equipo_rival_automatico(self):
        """Genera automáticamente el equipo rival"""
        disponibles = [p for p in self.pool if p not in self.equipo_usuario]
        
        # Seleccionar 1 portero
        porteros = [p for p in disponibles if p.rol_preferido == Rol.PORTERO]
        if porteros:
            portero = random.choice(porteros)
            disponibles.remove(portero)
            self.equipo_rival = [portero]
        else:
            self.equipo_rival = [random.choice(disponibles)]
            disponibles.remove(self.equipo_rival[0])
        
        # Seleccionar 4 más
        self.equipo_rival.extend(random.sample(disponibles, min(4, len(disponibles))))
        
        print("\n🤖 Equipo Rival generado automáticamente:")
        for jugador in self.equipo_rival:
            attrs = jugador.obtener_atributos_visibles()
            print(f"  - {jugador.nombre_con_id} ({jugador.rol_preferido.value})")
    
    def mostrar_narrativa_partido(self, resultado: ResultadoPartido):
        """Muestra la narrativa del partido"""
        print("\n" + "=" * 60)
        print("📺 NARRATIVA DEL PARTIDO")
        print("=" * 60 + "\n")
        
        minuto_actual = -1
        eventos_por_minuto = {}
        
        # Agrupar eventos por minuto
        for evento in resultado.eventos:
            if evento.minuto not in eventos_por_minuto:
                eventos_por_minuto[evento.minuto] = []
            eventos_por_minuto[evento.minuto].append(evento)
        
        # Mostrar narrativa
        for minuto in sorted(eventos_por_minuto.keys()):
            print(f"\n⏱️  Minuto {minuto + 1}:")
            for evento in eventos_por_minuto[minuto]:
                if evento.tipo == "gol":
                    print(f"  ⚽ {evento.descripcion}")
                elif evento.tipo == "falta":
                    print(f"  🟨 {evento.descripcion}")
                elif evento.tipo == "robo":
                    print(f"  🏃 {evento.descripcion}")
                elif evento.tipo == "regate":
                    print(f"  ✨ {evento.descripcion}")
                elif evento.tipo == "pase":
                    print(f"  📍 {evento.descripcion}")
                else:
                    print(f"  • {evento.descripcion}")
    
    def mostrar_resultado_final(self, resultado: ResultadoPartido):
        """Muestra el resultado final del partido"""
        self.mostrar_separador()
        print("🏆 RESULTADO FINAL")
        print("-" * 60)
        print(f"Tu Equipo:     {resultado.goles_equipo_a}")
        print(f"Equipo Rival:  {resultado.goles_equipo_b}")
        
        if resultado.goles_equipo_a > resultado.goles_equipo_b:
            print("\n🎉 ¡VICTORIA! Has ganado el partido.")
        elif resultado.goles_equipo_a < resultado.goles_equipo_b:
            print("\n😔 Derrota. Mejor suerte la próxima vez.")
        else:
            print("\n🤝 Empate. Buen partido.")
        
        print(f"\n⭐ Jugador del Partido: {resultado.jugador_del_partido.nombre_con_id}")
        stats = resultado.jugador_del_partido.obtener_estadisticas()
        print(f"   Goles: {stats['goles']}, Regates: {stats['regates_exitosos']}, "
              f"Robos: {stats['robos']}, Pases: {stats['pases']}")
    
    def mostrar_estadisticas(self, resultado: ResultadoPartido):
        """Muestra estadísticas resumidas"""
        self.mostrar_separador()
        print("📊 ESTADÍSTICAS RESUMIDAS")
        print("-" * 60)
        
        print("\n👥 Tu Equipo:")
        for jugador in self.equipo_usuario:
            stats = jugador.obtener_estadisticas()
            print(f"  {jugador.nombre_con_id}: "
                  f"G:{stats['goles']} P:{stats['pases']} "
                  f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} "
                  f"F:{stats['faltas']}")
        
        print("\n🤖 Equipo Rival:")
        for jugador in self.equipo_rival:
            stats = jugador.obtener_estadisticas()
            print(f"  {jugador.nombre_con_id}: "
                  f"G:{stats['goles']} P:{stats['pases']} "
                  f"Rg:{stats['regates_exitosos']} Rb:{stats['robos']} "
                  f"F:{stats['faltas']}")
    
    def exportar_resultado_json(self, resultado: ResultadoPartido, filename: str = "resultado_partido.json"):
        """Exporta el resultado a JSON"""
        datos = {
            "marcador": {
                "equipo_a": resultado.goles_equipo_a,
                "equipo_b": resultado.goles_equipo_b
            },
            "jugador_del_partido": {
                "id": resultado.jugador_del_partido.id,
                "nombre": resultado.jugador_del_partido.nombre_con_id
            },
            "eventos": [
                {
                    "minuto": e.minuto,
                    "segundo": e.segundo,
                    "descripcion": e.descripcion,
                    "tipo": e.tipo
                }
                for e in resultado.eventos
            ],
            "estadisticas_equipo_a": resultado.estadisticas_equipo_a,
            "estadisticas_equipo_b": resultado.estadisticas_equipo_b
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultado exportado a {filename}")
    
    def menu_principal(self):
        """Menú principal del juego"""
        while True:
            self.mostrar_separador()
            print("⚽ PATABOL - Menú Principal")
            print("1. Generar pool de patabolistas")
            print("2. Ver pool disponible")
            print("3. Seleccionar mi equipo")
            print("4. Simular partido")
            print("5. Salir")
            
            opcion = input("\nSelecciona una opción: ").strip()
            
            if opcion == "1":
                seed_input = input("Ingresa seed (Enter para aleatorio): ").strip()
                seed = int(seed_input) if seed_input else None
                self.generador = GeneradorPool(seed=seed)
                self.pool = self.generador.generar_pool(15)
                print(f"\n✅ Pool de {len(self.pool)} patabolistas generado")
                self.mostrar_pool()
            
            elif opcion == "2":
                self.mostrar_pool()
            
            elif opcion == "3":
                if not self.pool:
                    print("❌ Primero debes generar un pool")
                    continue
                self.equipo_usuario = self.seleccionar_equipo("Tu Equipo")
                if self.equipo_usuario:
                    self.generar_equipo_rival_automatico()
            
            elif opcion == "4":
                if not self.equipo_usuario or not self.equipo_rival:
                    print("❌ Debes seleccionar tu equipo primero")
                    continue
                
                print("\n🎮 Iniciando simulación del partido...")
                simulador = SimuladorPartido(self.equipo_usuario, self.equipo_rival)
                resultado = simulador.simular()
                
                self.mostrar_narrativa_partido(resultado)
                self.mostrar_resultado_final(resultado)
                self.mostrar_estadisticas(resultado)
                
                exportar = input("\n¿Exportar resultado a JSON? (s/n): ").strip().lower()
                if exportar == 's':
                    self.exportar_resultado_json(resultado)
            
            elif opcion == "5":
                print("\n👋 ¡Hasta luego!")
                break
            
            else:
                print("❌ Opción inválida")


def main():
    """Función principal"""
    interfaz = InterfazCLI()
    interfaz.menu_principal()


if __name__ == "__main__":
    main()
