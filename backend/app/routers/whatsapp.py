"""
Webhook de WhatsApp Business (Meta Graph API).

Flujo: Meta entrega el mensaje aquí → se extraen las entidades con Claude →
se contesta al usuario. La emisión real del comprobante se hace desde el
orquestador, nunca directamente en el webhook: Meta reintenta las entregas y
un webhook que factura de forma directa emitiría duplicados.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..base_datos import SesionLocal, obtener_sesion
from ..ia.orquestador import atender_mensaje
from ..seguridad import usuario_actual

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
registro = logging.getLogger(__name__)

TOKEN_VERIFICACION = os.getenv("WHATSAPP_TOKEN_VERIFICACION", "")
SECRETO_APP = os.getenv("WHATSAPP_SECRETO_APP", "")
TOKEN_ACCESO = os.getenv("WHATSAPP_TOKEN_ACCESO", "")
ID_NUMERO = os.getenv("WHATSAPP_ID_NUMERO", "")
VERSION_GRAPH = os.getenv("WHATSAPP_VERSION_GRAPH", "v21.0")


def _normalizar_telefono(numero: str) -> str:
    """Normaliza un número para comparar: quita espacios y el prefijo '+'."""
    return numero.replace(" ", "").replace("+", "").strip()


# ALLOWLIST de teléfonos autorizados a facturar por WhatsApp.
#
# La firma HMAC de Meta (_firma_valida) solo prueba que el mensaje viene de
# Meta, NO que el remitente esté autorizado. Sin esta lista, cualquiera que
# escriba al número del bot podría disparar la emisión de comprobantes. Se lee
# de WHATSAPP_TELEFONOS_AUTORIZADOS (números separados por comas) y se normaliza
# quitando espacios y '+' para que el formato del env no importe.
TELEFONOS_AUTORIZADOS = frozenset(
    _normalizar_telefono(t)
    for t in os.getenv("WHATSAPP_TELEFONOS_AUTORIZADOS", "").split(",")
    if t.strip()
)


def _remitente_autorizado(remitente: str) -> bool:
    """
    Indica si un remitente puede facturar por WhatsApp.

    Política FAIL-CLOSED: si la allowlist está vacía o no configurada, no se
    autoriza a nadie. Es preferible no facturar a facturar para un desconocido.
    """
    if not TELEFONOS_AUTORIZADOS:
        return False
    return _normalizar_telefono(remitente) in TELEFONOS_AUTORIZADOS

# Imports opcionales — no deben romper el webhook si no están instalados.
try:
    import openai  # type: ignore
except ImportError:  # pragma: no cover
    openai = None  # type: ignore

try:
    import anthropic  # type: ignore
except ImportError:  # pragma: no cover
    anthropic = None  # type: ignore


def _firma_valida(cuerpo: bytes, cabecera: str | None) -> bool:
    """
    Verifica la firma HMAC-SHA256 que Meta envía en X-Hub-Signature-256.

    Sin esto, cualquiera que conozca la URL podría inyectar mensajes falsos y
    hacer que el sistema emita facturas.
    """
    if not SECRETO_APP:
        # Sin secreto configurado no se puede verificar nada: se rechaza en
        # lugar de aceptar a ciegas.
        registro.error("WHATSAPP_SECRETO_APP no está configurado; se rechaza el webhook.")
        return False

    if not cabecera or not cabecera.startswith("sha256="):
        return False

    esperada = hmac.new(SECRETO_APP.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, cabecera.removeprefix("sha256="))


@router.get("")
def verificar_webhook(request: Request):
    """
    Handshake de verificación de Meta.

    Meta llama una sola vez con `hub.challenge` al registrar la URL y espera
    ese mismo valor de vuelta en texto plano.
    """
    parametros = request.query_params

    if parametros.get("hub.mode") != "subscribe":
        raise HTTPException(400, "Modo de verificación no soportado.")
    if not TOKEN_VERIFICACION or parametros.get("hub.verify_token") != TOKEN_VERIFICACION:
        raise HTTPException(403, "Token de verificación incorrecto.")

    return Response(content=parametros.get("hub.challenge", ""), media_type="text/plain")


def enviar_mensaje(destino: str, texto: str) -> None:
    """Envía un mensaje de texto por la Graph API."""
    if not (TOKEN_ACCESO and ID_NUMERO):
        registro.warning("WhatsApp sin credenciales; el mensaje no se envió: %s", texto[:80])
        return

    respuesta = requests.post(
        f"https://graph.facebook.com/{VERSION_GRAPH}/{ID_NUMERO}/messages",
        headers={"Authorization": f"Bearer {TOKEN_ACCESO}"},
        json={
            "messaging_product": "whatsapp",
            "to": destino,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=15,
    )

    if not respuesta.ok:
        registro.error("Error enviando a WhatsApp (%s): %s", respuesta.status_code, respuesta.text)


def _extraer_mensajes(cuerpo: dict) -> list[dict]:
    """Aplana la estructura anidada de Meta a una lista de mensajes."""
    mensajes = []

    for entrada in cuerpo.get("entry", []):
        for cambio in entrada.get("changes", []):
            valor = cambio.get("value", {})
            for mensaje in valor.get("messages", []):
                mensajes.append(mensaje)

    return mensajes


# ---------------------------------------------------------------------------
# Multimodal: audio / imagen
# ---------------------------------------------------------------------------


def _descargar_media(media_id: str) -> tuple[bytes | None, str | None]:
    """
    Descarga un archivo de la Graph API a partir de su media_id.

    Paso 1: GET /{media_id} → { url }
    Paso 2: GET {url} con Bearer TOKEN_ACCESO → bytes
    """
    if not TOKEN_ACCESO:
        registro.warning("WHATSAPP_TOKEN_ACCESO no configurado; no se puede descargar media %s", media_id)
        return None, None

    try:
        meta_resp = requests.get(
            f"https://graph.facebook.com/{VERSION_GRAPH}/{media_id}",
            headers={"Authorization": f"Bearer {TOKEN_ACCESO}"},
            timeout=15,
        )
        if not meta_resp.ok:
            registro.error("Graph API media info falló (%s): %s", meta_resp.status_code, meta_resp.text)
            return None, None
        media_url = meta_resp.json().get("url")
        if not media_url:
            registro.error("Graph API no devolvió url para media %s: %s", media_id, meta_resp.text)
            return None, None

        bin_resp = requests.get(
            media_url,
            headers={"Authorization": f"Bearer {TOKEN_ACCESO}"},
            timeout=30,
        )
        if not bin_resp.ok:
            registro.error("Descarga de media falló (%s): %s", bin_resp.status_code, bin_resp.text)
            return None, None

        mime = bin_resp.headers.get("Content-Type")
        return bin_resp.content, mime
    except Exception as exc:  # noqa: BLE001
        registro.exception("Error descargando media %s: %s", media_id, exc)
        return None, None


def _transcribir_audio(audio_bytes: bytes, mime: str | None) -> str | None:
    """
    Transcribe audio a texto. Prioridad: OpenAI Whisper → faster-whisper → None.

    Si no hay OPENAI_API_KEY ni librerías instaladas, devuelve None para que
    el caller responda con el fallback sin romper el webhook.
    """
    api_key = os.getenv("OPENAI_API_KEY", "")

    # Intento 1: OpenAI Whisper API
    if api_key and openai is not None:
        try:
            cliente = openai.OpenAI(api_key=api_key)  # type: ignore
            # El nombre del archivo necesita extensión para que Whisper detecte el formato.
            ext = "ogg" if mime and "ogg" in mime else "mp3"
            nombre = f"audio.{ext}"
            import io

            archivo = io.BytesIO(audio_bytes)
            # openai >=1.0 espera un file-like con atributo name
            archivo.name = nombre  # type: ignore
            trans = cliente.audio.transcriptions.create(
                model="whisper-1",
                file=archivo,
                language="es",
            )
            texto = getattr(trans, "text", "") or ""
            texto = texto.strip()
            if texto:
                registro.info("Audio transcrito vía OpenAI Whisper: %s", texto[:120])
                return texto
        except Exception as exc:  # noqa: BLE001
            registro.warning("Transcripción OpenAI falló, probando fallback: %s", exc)

    # Intento 2: faster-whisper local
    try:
        from faster_whisper import WhisperModel  # type: ignore

        import io
        import tempfile

        # faster-whisper trabaja con archivo en disco
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        try:
            modelo = WhisperModel("small", device="cpu", compute_type="int8")
            segmentos, _info = modelo.transcribe(tmp_path, language="es")
            texto = " ".join(s.text for s in segmentos).strip()
            if texto:
                registro.info("Audio transcrito vía faster-whisper: %s", texto[:120])
                return texto
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    except ImportError:
        pass
    except Exception as exc:  # noqa: BLE001
        registro.warning("Transcripción faster-whisper falló: %s", exc)

    return None


def _ocr_imagen(imagen_bytes: bytes, mime: str | None) -> str | None:
    """
    Extrae texto estructurado de una imagen (foto de RUC/recibo) vía Claude Vision.

    Si no hay ANTHROPIC_API_KEY o la librería no está instalada, devuelve None.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key or anthropic is None:
        return None

    try:
        cliente = anthropic.Anthropic(api_key=api_key)  # type: ignore
        media_type = mime or "image/jpeg"
        # La API de Anthropic solo acepta algunos mime; normaliza.
        if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
            media_type = "image/jpeg"
        b64 = base64.b64encode(imagen_bytes).decode()
        prompt = (
            "Extrae RUC/cédula, nombre/razón social, montos, conceptos y fecha "
            "del recibo/foto en texto estructurado. Si es un documento de identidad "
            "o RUC, extrae solo identificación y nombre. Responde en español, "
            "en líneas clave: valor."
        )
        resp = cliente.messages.create(
            model=os.getenv("MODELO_CLAUDE", "claude-opus-5"),
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": b64},
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        texto = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        texto = (texto or "").strip()
        if texto:
            registro.info("Imagen OCR vía Claude Vision: %s", texto[:200])
            return texto
    except Exception as exc:  # noqa: BLE001
        registro.exception("OCR de imagen falló: %s", exc)

    return None


def _procesar(mensaje: dict) -> None:
    """Atiende un mensaje y responde. Corre en segundo plano."""
    remitente = mensaje.get("from", "")

    # ALLOWLIST — se comprueba ANTES de descargar media o llamar al orquestador.
    # La firma HMAC solo garantiza el origen (Meta), no la identidad autorizada
    # del remitente. FAIL-CLOSED: si la allowlist está vacía no se procesa a
    # nadie. Se responde un mensaje neutro para no filtrar si el número existe.
    if not _remitente_autorizado(remitente):
        registro.warning("Remitente no autorizado intentó facturar por WhatsApp: %s", remitente)
        enviar_mensaje(remitente, "Este número no está autorizado para facturar por WhatsApp.")
        return

    tipo = mensaje.get("type", "")

    texto: str | None = None
    es_audio = False
    es_imagen = False

    if tipo in ("audio", "voice"):
        es_audio = True
        audio_obj = mensaje.get("audio") or mensaje.get("voice") or {}
        media_id = audio_obj.get("id")
        if not media_id:
            enviar_mensaje(remitente, "No pude obtener el audio. Reenvíalo por favor.")
            return
        audio_bytes, mime = _descargar_media(media_id)
        if audio_bytes is None:
            enviar_mensaje(remitente, "No pude descargar el audio. Inténtalo de nuevo.")
            return
        transcrito = _transcribir_audio(audio_bytes, mime)
        if transcrito is None:
            registro.warning("Audio recibido sin transcripción (falta OPENAI_API_KEY o librerías)")
            enviar_mensaje(
                remitente,
                "Audio recibido — transcripción no configurada (falta OPENAI_API_KEY). "
                "Instala Whisper o configura OPENAI_API_KEY para habilitar audio.",
            )
            return
        texto = transcrito

    elif tipo == "image":
        es_imagen = True
        image_obj = mensaje.get("image") or {}
        media_id = image_obj.get("id")
        if not media_id:
            enviar_mensaje(remitente, "No pude obtener la imagen. Reenvíala por favor.")
            return
        imagen_bytes, mime = _descargar_media(media_id)
        if imagen_bytes is None:
            enviar_mensaje(remitente, "No pude descargar la imagen. Inténtalo de nuevo.")
            return
        ocr = _ocr_imagen(imagen_bytes, mime)
        if ocr is None:
            registro.warning("Imagen recibida sin OCR (falta ANTHROPIC_API_KEY)")
            enviar_mensaje(
                remitente,
                "Imagen recibida — OCR no configurado (falta ANTHROPIC_API_KEY). "
                "Configura ANTHROPIC_API_KEY para habilitar el reconocimiento de imágenes.",
            )
            return
        texto = ocr

    elif tipo == "text":
        texto = mensaje.get("text", {}).get("body", "")

    else:
        enviar_mensaje(
            remitente,
            "Por ahora entiendo texto, audio e imágenes. "
            "Envía tu solicitud en cualquiera de esos formatos.",
        )
        return

    if not texto:
        enviar_mensaje(remitente, "No pude entender el mensaje vacío. Inténtalo de nuevo.")
        return

    # SESIÓN DE BD POR TAREA: esta función corre en una BackgroundTask, DESPUÉS
    # de que FastAPI ya cerró la sesión del request. Reusar aquella sesión daría
    # errores (sesión cerrada) y, si llegan varios mensajes a la vez, se
    # compartiría entre hilos (SQLAlchemy Session no es thread-safe). Por eso
    # abrimos aquí una SesionLocal() propia y la cerramos siempre con finally.
    sesion = SesionLocal()
    try:
        # Se propaga es_audio/es_imagen al orquestador para anotar el historial.
        try:
            respuesta = atender_mensaje(remitente, texto, sesion, es_audio=es_audio, es_imagen=es_imagen)
        except TypeError:
            # Compatibilidad si el orquestador aún no acepta los flags
            respuesta = atender_mensaje(remitente, texto, sesion)
    except Exception:  # noqa: BLE001 - el webhook nunca debe reventar por un mensaje
        registro.exception("Fallo procesando mensaje de %s", remitente)
        respuesta = "Tuve un problema procesando tu mensaje. Inténtalo de nuevo en un momento."
    finally:
        sesion.close()

    enviar_mensaje(remitente, respuesta)


@router.post("", status_code=200)
async def recibir_webhook(
    request: Request,
    tareas: BackgroundTasks,
):
    """
    Recibe los mensajes entrantes.

    Se responde 200 de inmediato y el trabajo va a segundo plano: Meta corta a
    los 20 segundos y reintenta si no recibe respuesta, lo que duplicaría el
    procesamiento del mismo mensaje.

    No se inyecta la sesión del request: la BackgroundTask corre después de que
    FastAPI la cierra, así que cada tarea (_procesar) abre su propia SesionLocal.
    """
    cuerpo_bruto = await request.body()

    if not _firma_valida(cuerpo_bruto, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403, "Firma del webhook inválida.")

    cuerpo = await request.json()

    for mensaje in _extraer_mensajes(cuerpo):
        tareas.add_task(_procesar, mensaje)

    return {"recibido": True}


class MensajeSimulado(BaseModel):
    telefono: str
    texto: str

@router.post("/simulador", dependencies=[Depends(usuario_actual)])
def chat_simulador(mensaje: MensajeSimulado, sesion: Session = Depends(obtener_sesion)):
    """
    Ruta para probar el chatbot localmente sin conectarse a Meta.
    Permite desarrollar y validar la extracción y emisión directamente desde el frontend.

    Exige sesión, y no es opcional: este endpoint llama al orquestador de forma
    síncrona, y el orquestador emite comprobantes de verdad firmados con el
    certificado del contribuyente. Sin la sesión, cualquiera que conociera la
    URL podía facturar a nombre de la empresa con dos peticiones: uno con los
    datos y otro con el texto "si". El resto del router queda fuera del cierre
    global porque Meta se autentica con HMAC, pero esta ruta no la llama Meta.
    """
    try:
        # Llama al orquestador de manera síncrona para que el frontend reciba
        # la respuesta inmediatamente.
        respuesta = atender_mensaje(mensaje.telefono, mensaje.texto, sesion)
        return {"respuesta": respuesta}
    except Exception as e:
        registro.exception("Fallo en simulador con %s", mensaje.telefono)
        return {"respuesta": f"Error interno del servidor: {e}"}

