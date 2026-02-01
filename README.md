# ⚽ PATABOL

Juego de simulación de fútbol desarrollado en Python con Programación Orientada a Objetos.

## 📋 Descripción

PATABOL es un simulador de partidos de fútbol donde puedes:
- Generar un pool de patabolistas con atributos únicos
- Seleccionar tu equipo de 5 jugadores
- Simular partidos de 5 minutos con narrativa en tiempo real
- Ver estadísticas detalladas y resultados

**¡Ahora disponible en WhatsApp!** Juega desde tu teléfono usando el bot de WhatsApp.

## 🎮 Características

- **Sistema de atributos**: Control, Velocidad, Fuerza, Regate (visibles) y Magia (oculta)
- **Roles**: Portero, Defensa, Medio, Delantero
- **Simulación realista**: Partidos de 5 minutos divididos en 30 estados de 10 segundos
- **Narrativa deportiva**: Relato minuto a minuto de los eventos del partido
- **Sistema de magia**: Atributo oculto que influye en jugadas épicas
- **Exportación**: Resultados exportables a JSON

## 🚀 Instalación

### Modo CLI (Local)

No requiere dependencias externas. Solo necesitas Python 3.7 o superior.

```bash
# Verificar versión de Python
python --version

# Ejecutar el juego
python cli.py
```

### Bot de WhatsApp

Para desplegar el bot de WhatsApp, consulta la [guía de despliegue completa](DEPLOY.md).

**Requisitos:**
- Cuenta de Twilio
- Cuenta de Railway (o similar)
- Python 3.7+

**Instalación local (para pruebas):**
```bash
pip install -r requirements.txt
python whatsapp_bot.py
```

## 📖 Uso

### Modo CLI

1. **Generar pool de patabolistas**
   - Opción 1 del menú
   - Puedes ingresar una seed para reproducibilidad

2. **Ver pool disponible**
   - Opción 2 del menú
   - Muestra todos los jugadores con sus atributos visibles

3. **Seleccionar mi equipo**
   - Opción 3 del menú
   - Debes seleccionar 5 jugadores (1 portero obligatorio)
   - El equipo rival se genera automáticamente

4. **Simular partido**
   - Opción 4 del menú
   - Se muestra la narrativa del partido
   - Resultado final y estadísticas
   - Opción de exportar a JSON

### Bot de WhatsApp

Una vez desplegado, envía comandos por WhatsApp:

- `/ayuda` - Muestra comandos disponibles
- `/generar [seed]` - Genera pool de 15 patabolistas
- `/pool` - Muestra pool disponible
- `/seleccionar <id1> <id2> <id3> <id4> <id5>` - Selecciona tu equipo
- `/jugar` - Simula partido
- `/estadisticas` - Muestra estadísticas del último partido
- `/limpiar` - Limpia tu sesión

**Ejemplo de flujo:**
```
/generar 42
/pool
/seleccionar P001 P005 P008 P012 P015
/jugar
```

## 🎯 Reglas del Juego

- **Duración**: 5 minutos (300 segundos) divididos en 30 estados
- **Equipos**: 5 jugadores por equipo (1 portero + 4 de campo)
- **Goles**: Solo los delanteros pueden intentar hacer gol
- **Magia**: Atributo oculto que aumenta probabilidades de éxito
  - 60% de jugadores tienen magia 1-3
  - 30% tienen magia 4-6
  - 9% tienen magia 7-8
  - 1% tienen magia 9-10 (legendarios)

## 📊 Atributos

- **Control** (1-10): Habilidad para mantener la posesión
- **Velocidad** (1-10): Rapidez de movimiento
- **Fuerza** (1-10): Capacidad física (mayor probabilidad de faltas)
- **Regate** (1-10): Habilidad para eludir oponentes
- **Magia** (1-10): Atributo oculto que influye en eventos especiales

## 🏗️ Arquitectura

El código está organizado en dos capas principales:

### Dominio (Lógica del Juego)
- `Patabolista`: Entidad principal con atributos y estadísticas
- `GeneradorPool`: Genera pools de jugadores con distribución realista
- `SimuladorPartido`: Simula partidos completos
- `ResultadoPartido`: Contiene el resultado estructurado

### Presentación
- `InterfazCLI` (`cli.py`): Maneja la interacción por consola
- `WhatsAppBot` (`whatsapp_bot.py`): Bot de WhatsApp usando Twilio
- Menú interactivo (CLI) o comandos por WhatsApp
- Visualización de datos adaptada a cada interfaz
- Exportación de resultados (CLI)

## 📝 Ejemplo de Uso

```
⚽ PATABOL - Menú Principal
1. Generar pool de patabolistas
2. Ver pool disponible
3. Seleccionar mi equipo
4. Simular partido
5. Salir

Selecciona una opción: 1
Ingresa seed (Enter para aleatorio): 42

✅ Pool de 15 patabolistas generado
...
```

## 🔧 Extensibilidad

El código está diseñado para ser fácilmente extensible:
- Nuevos roles de jugadores
- Nuevas acciones durante el partido
- Diferentes sistemas de puntuación
- Múltiples modos de juego

## 📚 Documentación Adicional

- [Guía de Despliegue](DEPLOY.md) - Instrucciones completas para desplegar el bot de WhatsApp

## 📄 Licencia

Proyecto personal para fines educativos.
