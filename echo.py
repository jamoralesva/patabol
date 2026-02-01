"""
App Flask tipo echo para validar la conexión con la API de Twilio (WhatsApp).
Responde con un único mensaje TwiML que repite lo que el usuario envió.
"""

import os
import logging
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from twilio.base.exceptions import TwilioRestException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")


def _respuesta_twiml_error(mensaje: str = "Ocurrió un error. Intenta de nuevo.") -> Response:
    """Devuelve una respuesta 200 con TwiML de error para que el usuario reciba un mensaje."""
    twiml = MessagingResponse()
    twiml.message(mensaje)
    return Response(str(twiml), mimetype="text/xml")


@app.route("/health", methods=["GET"])
def health():
    """Health check."""
    return Response("OK", status=200)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    """Webhook que recibe mensajes de Twilio y responde con un único mensaje (echo)."""
    if request.method == "GET":
        return Response("Webhook echo activo", status=200)

    try:
        if TWILIO_AUTH_TOKEN:
            validator = RequestValidator(TWILIO_AUTH_TOKEN)
            url = request.url
            signature = request.headers.get("X-Twilio-Signature", "")
            if not validator.validate(url, request.form, signature):
                logger.warning("Request no válido de Twilio (firma)")
                return Response("Unauthorized", status=403)

        numero_origen = request.form.get("From", "")
        body = request.form.get("Body", "").strip()

        logger.info("Mensaje recibido de %s: %s", numero_origen, body or "(vacío)")

        # Un solo mensaje en la respuesta (recomendado para sandbox: 1 msg cada 3 s)
        texto_respuesta = body if body else "No enviaste texto. Escribí algo y te lo devuelvo."
        twiml = MessagingResponse()
        twiml.message(texto_respuesta)

        logger.info("Enviando echo a %s: %s", numero_origen, texto_respuesta[:80])

        return Response(str(twiml), mimetype="text/xml")

    except TwilioRestException as e:
        logger.warning(
            "Twilio API error: status=%s code=%s msg=%s uri=%s",
            e.status, e.code, e.msg, e.uri,
        )
        return _respuesta_twiml_error(f"Error de Twilio ({e.status}): {e.msg or 'intenta más tarde.'}")

    except Exception as e:
        logger.error("Error en webhook echo: %s", e, exc_info=True)
        return _respuesta_twiml_error()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
