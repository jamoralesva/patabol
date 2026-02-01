# ⚽ PATABOL

Juego de simulación de fútbol desarrollado en Python con Programación Orientada a Objetos.

## 📋 Descripción

PATABOL es un simulador de partidos de fútbol donde puedes:
- Generar un pool de patabolistas con atributos únicos
- Seleccionar tu equipo de 5 jugadores
- Simular partidos de 5 minutos con narrativa en tiempo real
- Ver estadísticas detalladas y resultados

**¡Disponible en WhatsApp, Telegram y CLI!** Misma experiencia por comandos en todos los canales.

## 🎮 Características

- **Sistema de atributos**: Control, Velocidad, Fuerza, Regate (visibles) y Magia (oculta)
- **Roles**: Portero, Defensa, Medio, Delantero
- **Simulación realista**: Partidos de 5 minutos divididos en 30 estados de 10 segundos
- **Narrativa deportiva**: Relato minuto a minuto de los eventos del partido
- **Sistema de magia**: Atributo oculto que influye en jugadas épicas
- **Multi-canal**: Mismos comandos en CLI, WhatsApp y Telegram

## 🏗️ Arquitectura de la aplicación

El proyecto está organizado en capas para separar dominio, lógica del bot y canales:

```
patabol/
├── core/                    # Núcleo del dominio
│   ├── patabol.py           # Lógica del juego (Patabolista, SimuladorPartido, etc.)
│   ├── sesiones.py          # Gestión de sesiones de juego (en memoria)
│   └── seguimiento_usuarios.py   # Primera interacción y bienvenida
│
├── bot/                     # Núcleo del bot (canal-agnóstico)
│   ├── core.py              # Procesamiento de comandos (procesar_comando)
│   ├── formatters.py        # Formateo de mensajes (pool, resultado, estadísticas)
│   └── simulation.py        # Ejecución de la simulación y notificación
│
├── channels/                # Adaptadores por canal
│   ├── whatsapp.py          # Flask + Twilio (webhook, envío de mensajes)
│   ├── telegram.py          # python-telegram-bot (polling)
│   └── cli.py               # REPL por comandos (misma experiencia que WhatsApp)
│
├── entrypoints/             # Puntos de entrada
│   ├── cli.py               # Ejecutar: python -m entrypoints.cli
│   ├── whatsapp_bot.py      # Ejecutar: python -m entrypoints.whatsapp_bot
│   └── telegram_bot.py     # Ejecutar: python -m entrypoints.telegram_bot
│
├── requirements.txt
├── Procfile                 # gunicorn entrypoints.whatsapp_bot:app
└── README.md
```

- **core**: Dominio del juego y estado (sesiones, usuarios). Sin dependencias de presentación.
- **bot**: Interpreta comandos y formatea respuestas. Recibe un callback para notificar a otros usuarios; no conoce Twilio ni Flask.
- **channels**: Cada canal (WhatsApp, Telegram, CLI) adapta entrada/salida y llama al bot.
- **entrypoints**: Scripts para arrancar cada canal (CLI, servidor WhatsApp o bot Telegram).

## 🚀 Instalación

### Modo CLI

No requiere dependencias externas. Python 3.7 o superior.

```bash
python --version
python -m entrypoints.cli
```

### Bot de WhatsApp

Para desplegar el bot de WhatsApp, consulta la [guía de despliegue](DEPLOY.md).

**Requisitos:** Cuenta Twilio, Railway (o similar), Python 3.7+

**Prueba local:**
```bash
pip install -r requirements.txt
python -m entrypoints.whatsapp_bot
```

### Bot de Telegram

**Requisitos:** Token de bot de Telegram (crear con [@BotFather](https://t.me/BotFather)), Python 3.7+

**Configuración:** Añade en tu `.env`:
```
TELEGRAM_BOT_TOKEN=tu_token_aquí
```

**Prueba local:**
```bash
pip install -r requirements.txt
python -m entrypoints.telegram_bot
```

## 📖 Uso

### CLI, WhatsApp y Telegram (mismos comandos)

- `/sesion` &lt;nickname&gt; [nombre_equipo] — Crear sesión (te da código para compartir)
- `/unirse` *(/u)* &lt;código&gt; &lt;nickname&gt; [nombre_equipo] — Unirse a una sesión. Creador: `/u ia` [nombre_equipo] para jugar vs IA
- `/pool` *(/p)* [port|def|med|del] — Ver pool disponible (filtros por rol)
- `/detalle` *(/d)* &lt;id&gt; — Detalle de un patabolista
- `/seleccionar` *(/s)* &lt;id1&gt; [id2] … — Elegir tu equipo (1–5 jugadores)
- `/seleccionar_auto` *(/a)* — Equipo automático
- `/quitar` *(/q)* &lt;id&gt; — Devolver un jugador al pool
- `/equipo` *(/e)* — Ver tu equipo
- `/confirmar` *(/c)* — Confirmar equipo (el partido arranca cuando ambos confirman)
- `/estadisticas` *(/est)* — Estadísticas del último partido
- `/salir` — Salir de la sesión
- `/ayuda` *(/h)* — Ayuda

**Ejemplo de flujo (CLI, WhatsApp o Telegram):**
```
/sesion Leo Los Rayos
/u ia
/pool
/s P1 P5 P8 P3 P10
/confirmar
```

## 🎯 Reglas del Juego

- **Duración**: 5 minutos (30 estados de 10 s)
- **Equipos**: 1–5 jugadores por equipo (1 portero recomendado)
- **Goles**: Solo delanteros pueden intentar gol
- **Magia**: Atributo oculto que aumenta probabilidades de éxito

## 📊 Atributos

- **Control** (1–10): Mantener posesión
- **Velocidad** (1–10): Rapidez
- **Fuerza** (1–10): Físico (más faltas)
- **Regate** (1–10): Eludir oponentes
- **Magia** (1–10): Oculto, influye en eventos especiales

## 🔧 Extensibilidad

- Nuevos roles o acciones en `core.patabol`
- Nuevos comandos en `bot.core`
- Nuevos canales en `channels/` usando la misma API del bot

## 📚 Documentación

- [Guía de Despliegue](DEPLOY.md) — Desplegar el bot de WhatsApp (Twilio + Railway)

## 📄 Licencia

Proyecto personal para fines educativos.
