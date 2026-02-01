"""
Canal WhatsApp: Flask + Twilio. Recibe mensajes y delega en el núcleo del bot.
"""

import os
import time
import logging
import threading
from typing import List

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

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

app = Flask(__name__)

TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER")
LATENCIA_ENTRE_EVENTOS_SEGUNDOS = float(os.environ.get("LATENCIA_EVENTOS", "2"))


def _log_mensaje_enviado(destino: str, cuerpo: str, via: str = "API") -> None:
    preview_una_linea = cuerpo.replace("\n", " ")
    logger.info("[WhatsApp %s] Enviando a %s: %s", via, destino, preview_una_linea)


def _enviar_un_mensaje_con_reintento(
    client: Client, body: str, from_: str, to: str, max_reintentos_429: int = 1
) -> bool:
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
                espera = 4
                logger.info("429 Too Many Requests: esperando %s s antes de reintentar...", espera)
                time.sleep(espera)
            else:
                logger.error("Error enviando mensaje a %s: %s (code %s)", to, e.msg, e.code)
                return False
        except Exception as e:
            logger.error("Error enviando mensaje a %s: %s", to, e)
            return False
    return False


def _enviar_a_un_usuario(to_id: str, mensajes: List[str]) -> None:
    """Envía una lista de mensajes a un usuario (divide mensajes largos)."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
        logger.error("Credenciales de Twilio no configuradas")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for mensaje in mensajes:
            chunks = dividir_mensaje(mensaje)
            for chunk in chunks:
                _log_mensaje_enviado(to_id, chunk, via="API")
                _enviar_un_mensaje_con_reintento(
                    client, chunk, TWILIO_WHATSAPP_NUMBER, to_id,
                )
                time.sleep(0.5)
    except Exception as e:
        logger.error("Error inicializando cliente de Twilio: %s", e)


def _enviar_a_jugadores(user_ids: List[str], mensaje: str) -> None:
    """Envía el mismo mensaje a todos los user_ids (respeta rate limit sandbox)."""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_WHATSAPP_NUMBER:
        logger.error("Credenciales de Twilio no configuradas")
        return
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        for user_id in user_ids:
            chunks = dividir_mensaje(mensaje)
            for chunk in chunks:
                _log_mensaje_enviado(user_id, chunk, via="API")
                _enviar_un_mensaje_con_reintento(
                    client, chunk, TWILIO_WHATSAPP_NUMBER, user_id,
                )
            time.sleep(3)
    except Exception as e:
        logger.error("Error inicializando cliente de Twilio: %s", e)


@app.route("/health", methods=["GET"])
def health():
    return Response("OK", status=200)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        return Response("Webhook activo", status=200)

    if TWILIO_AUTH_TOKEN:
        validator = RequestValidator(TWILIO_AUTH_TOKEN)
        if request.headers.get("X-Forwarded-Proto") or request.headers.get("X-Forwarded-Host"):
            proto = (request.headers.get("X-Forwarded-Proto") or request.scheme).strip()
            host = (request.headers.get("X-Forwarded-Host") or request.host).strip()
            if ":" in host and host.split(":")[-1].isdigit():
                host = host.rsplit(":", 1)[0]
            url = f"{proto}://{host}{request.full_path}"
        else:
            url = request.url
        signature = request.headers.get("X-Twilio-Signature", "")
        if not validator.validate(url, request.form, signature):
            logger.warning("Request no válido de Twilio (URL usada para validar: %s)", url)
            return Response("Unauthorized", status=403)

    numero_origen = request.form.get("From", "")
    mensaje = request.form.get("Body", "").strip()
    logger.info("Mensaje recibido de %s: %s", numero_origen, mensaje)

    es_primera_interaccion = es_primera_vez(numero_origen)
    if es_primera_interaccion:
        registrar_interaccion(numero_origen)

    def enviar_a_usuario(to_id: str, mensajes: List[str]) -> None:
        _enviar_a_un_usuario(to_id, mensajes)

    try:
        respuestas, sesion_simular = procesar_comando(mensaje, numero_origen, enviar_a_usuario)
    except Exception as e:
        logger.error("Error procesando comando: %s", e, exc_info=True)
        respuestas = ["❌ Error procesando comando. Intenta de nuevo o usa /ayuda o /h."]
        sesion_simular = None

    if es_primera_interaccion:
        respuestas = [MENSAJE_BIENVENIDA] + (respuestas if respuestas else [])

    if not respuestas:
        respuestas = ["Escribí /h para ver los comandos disponibles."]

    twiml = MessagingResponse()
    for texto in respuestas:
        _log_mensaje_enviado(numero_origen, texto, via="TwiML")
        twiml.message(texto)

    if sesion_simular is not None:
        def lanzar_simulacion():
            time.sleep(1)
            ejecutar_simulacion_y_notificar(
                sesion_simular,
                enviar_a_jugadores=_enviar_a_jugadores,
                salir_sesion_fn=salir_sesion_juego,
                latencia_entre_eventos_segundos=LATENCIA_ENTRE_EVENTOS_SEGUNDOS,
            )

        threading.Thread(target=lanzar_simulacion, daemon=True).start()

    return Response(str(twiml), mimetype="text/xml")


def create_app() -> Flask:
    """Factory para la app Flask (opcional)."""
    return app
