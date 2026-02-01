"""
Canal Telegram: python-telegram-bot. Recibe mensajes y delega en el núcleo del bot.
"""

import asyncio
import logging
import os
import re
import threading
from html import escape as html_escape
from http import HTTPStatus
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv
load_dotenv()

from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, request
import uvicorn

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

from core.sesiones import salir_sesion as salir_sesion_juego
from core.seguimiento_usuarios import (
    es_primera_vez,
    registrar_interaccion,
    MENSAJE_BIENVENIDA,
)
from bot.core import procesar_comando
from bot.simulation import ejecutar_simulacion_y_notificar
from bot.formatters import dividir_mensaje

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_WEBHOOK_URL = os.environ.get("TELEGRAM_WEBHOOK_URL")
LATENCIA_ENTRE_EVENTOS_SEGUNDOS = float(os.environ.get("LATENCIA_EVENTOS", "2"))


def _mensaje_para_telegram_html(texto: str) -> str:
    """Convierte *negrita* y _cursiva_ a <b>/<i>. Escapa HTML; [ ] y otros quedan seguros."""
    escaped = html_escape(texto)
    # *...* -> <b>...</b>, _..._ -> <i>...</i> (contenido ya escapado)
    out = re.sub(r"\*([^*]+)\*", r"<b>\1</b>", escaped)
    out = re.sub(r"_([^_]+)_", r"<i>\1</i>", out)
    return out


async def _send_to_telegram_async(bot, chat_id: int, mensajes: List[str]) -> None:
    """Envía una lista de mensajes a un chat. Ejecutar en el event loop del bot."""
    for m in mensajes:
        for chunk in dividir_mensaje(m):
            await bot.send_message(
                chat_id=chat_id,
                text=_mensaje_para_telegram_html(chunk),
                parse_mode="HTML",
            )
            await asyncio.sleep(0.3)


async def _enviar_a_jugadores_telegram_async(
    bot, user_ids: List[str], mensaje: str
) -> None:
    """Envía el mismo mensaje a varios chats. Ejecutar en el event loop del bot."""
    for uid in user_ids:
        for chunk in dividir_mensaje(mensaje):
            await bot.send_message(
                chat_id=int(uid),
                text=_mensaje_para_telegram_html(chunk),
                parse_mode="HTML",
            )
        await asyncio.sleep(0.5)


def _enviar_a_jugadores_telegram_sync(
    bot, user_ids: List[str], mensaje: str, main_loop: asyncio.AbstractEventLoop
) -> None:
    """Envía el mismo mensaje a varios chats desde un hilo; programa en el loop principal."""
    coro = _enviar_a_jugadores_telegram_async(bot, user_ids, mensaje)
    future = asyncio.run_coroutine_threadsafe(coro, main_loop)
    future.result(timeout=120)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Procesa un mensaje de texto: delega en procesar_comando y envía respuestas."""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None:
        return

    user_id = str(chat_id)
    mensaje = update.message.text.strip()
    logger.info("Mensaje recibido de %s: %s", user_id, mensaje)

    es_primera_interaccion = es_primera_vez(user_id)
    if es_primera_interaccion:
        registrar_interaccion(user_id)

    bot = context.bot
    loop = asyncio.get_event_loop()
    pending_sends: List[tuple] = []  # (chat_id, mensajes) para enviar en el loop principal

    def run_command() -> tuple:
        def enviar_a_usuario(to_id: str, mensajes: List[str]) -> None:
            pending_sends.append((int(to_id), mensajes))

        return procesar_comando(mensaje, user_id, enviar_a_usuario)

    try:
        respuestas, sesion_simular = await loop.run_in_executor(None, run_command)
    except Exception as e:
        logger.error("Error procesando comando: %s", e, exc_info=True)
        respuestas = ["❌ Error procesando comando. Intenta de nuevo o usa /ayuda o /h."]
        sesion_simular = None

    # Enviar notificaciones a otros usuarios desde el loop principal (evita "Event loop is closed")
    for chat_id, mensajes in pending_sends:
        await _send_to_telegram_async(bot, chat_id, mensajes)

    if es_primera_interaccion:
        respuestas = [MENSAJE_BIENVENIDA] + (respuestas if respuestas else [])

    if not respuestas:
        respuestas = ["Escribí /h para ver los comandos disponibles."]

    for texto in respuestas:
        for chunk in dividir_mensaje(texto):
            await update.message.reply_text(
                _mensaje_para_telegram_html(chunk),
                parse_mode="HTML",
            )
            await asyncio.sleep(0.3)

    if sesion_simular is not None:
        def lanzar_simulacion() -> None:
            def enviar_a_jugadores(user_ids: List[str], msg: str) -> None:
                _enviar_a_jugadores_telegram_sync(bot, user_ids, msg, loop)

            ejecutar_simulacion_y_notificar(
                sesion_simular,
                enviar_a_jugadores=enviar_a_jugadores,
                salir_sesion_fn=salir_sesion_juego,
                latencia_entre_eventos_segundos=LATENCIA_ENTRE_EVENTOS_SEGUNDOS,
            )

        threading.Thread(target=lanzar_simulacion, daemon=True).start()


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a /start con bienvenida y ayuda."""
    if not update.message:
        return
    user_id = str(update.effective_chat.id) if update.effective_chat else ""
    if es_primera_vez(user_id):
        registrar_interaccion(user_id)
        await update.message.reply_text(
            _mensaje_para_telegram_html(MENSAJE_BIENVENIDA),
            parse_mode="HTML",
        )
    await update.message.reply_text(
        _mensaje_para_telegram_html(
            "Usa /sesion <nickname> para crear una partida o /u <código> <nickname> para unirte. /h para ayuda."
        ),
        parse_mode="HTML",
    )


def build_application(webhook: bool = False) -> Application:
    """Construye la aplicación de Telegram con handlers."""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN no está configurado en el entorno")

    builder = Application.builder().token(TELEGRAM_BOT_TOKEN)
    if webhook:
        builder = builder.updater(None)
    app = builder.build()

    app.add_handler(CommandHandler("start", cmd_start))
    # Incluir comandos (/sesion, /pool, etc.) para que los procese handle_message → procesar_comando
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    return app


def run_polling() -> None:
    """Arranca el bot en modo polling (bloqueante)."""
    application = build_application()
    logger.info("Bot de Telegram iniciado (polling)")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


def run_webhook() -> None:
    """Arranca el bot en modo webhook: registra la URL en Telegram y sirve updates por HTTP."""
    if not TELEGRAM_WEBHOOK_URL:
        raise ValueError(
            "TELEGRAM_WEBHOOK_URL no está configurado (ej. https://tudominio.com/telegram)"
        )

    application = build_application(webhook=True)
    path = urlparse(TELEGRAM_WEBHOOK_URL).path.rstrip("/") or "/telegram"

    flask_app = Flask(__name__)

    @flask_app.post(path)
    async def telegram_webhook():
        """Recibe updates de Telegram y los encola."""
        data = request.get_json(silent=True)
        if not data:
            return Response(status=HTTPStatus.BAD_REQUEST)
        await application.update_queue.put(
            Update.de_json(data=data, bot=application.bot)
        )
        return Response(status=HTTPStatus.OK)

    @flask_app.get("/health")
    def health():
        return Response("OK", status=HTTPStatus.OK)

    async def main():
        await application.bot.set_webhook(
            url=TELEGRAM_WEBHOOK_URL,
            allowed_updates=Update.ALL_TYPES,
        )
        logger.info("Webhook registrado: %s", TELEGRAM_WEBHOOK_URL)
        port = int(os.environ.get("PORT", 5000))
        config = uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            host="0.0.0.0",
            port=port,
            use_colors=False,
        )
        server = uvicorn.Server(config)
        async with application:
            await application.start()
            await server.serve()
            await application.stop()

    asyncio.run(main())
