"""
Pruebas del asistente de IA y del webhook de WhatsApp.

El modelo se sustituye por un doble: lo que se prueba es que la extracción se
valide correctamente y que el webhook rechace lo que debe rechazar, no que el
modelo responda bien.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


class RespuestaFalsa:
    """
    Imita la respuesta de `google-genai`.

    El motivo de parada llega dentro del primer candidato, no en la raíz como
    en otros SDK; el doble reproduce esa forma para que la prueba ejercite el
    mismo camino que producción.
    """

    class Candidato:
        def __init__(self, motivo: str) -> None:
            self.finish_reason = motivo

    def __init__(self, datos: dict | None, finish_reason: str = "STOP") -> None:
        self.text = json.dumps(datos) if datos is not None else None
        self.candidates = [self.Candidato(finish_reason)]


class ClienteFalso:
    def __init__(self, respuesta) -> None:
        self._respuesta = respuesta
        self.models = self

    def generate_content(self, **_):
        if isinstance(self._respuesta, Exception):
            raise self._respuesta
        return self._respuesta


EXTRACCION_VALIDA = {
    "intencion": "crear_factura",
    "cliente": {
        "identificacion": "1790016919001",
        "tipo_identificacion": "RUC",
        "nombre": "CORPORACION FAVORITA",
        "correo": "compras@favorita.com",
    },
    "detalles": [
        {
            "descripcion": "Servicios de consultoría",
            "cantidad": "1",
            "precio_unitario": "50.00",
            "precio_incluye_iva": False,
            "codigo_iva": "4",
        }
    ],
    "forma_pago": "contado",
    "datos_faltantes": [],
    "respuesta_sugerida": "Perfecto, preparo la factura.",
}


# --------------------------------------------------------------------------
# Extracción
# --------------------------------------------------------------------------


def test_extraccion_devuelve_entidades():
    from app.ia.extraccion import extraer_factura

    resultado = extraer_factura(
        "factura de 50 a Favorita RUC 1790016919001",
        cliente_ai=ClienteFalso(RespuestaFalsa(EXTRACCION_VALIDA)),
    )

    assert resultado.intencion == "crear_factura"
    assert resultado.cliente["identificacion"] == "1790016919001"
    assert len(resultado.detalles) == 1
    assert resultado.advertencias == []
    assert resultado.listo_para_emitir


def test_extraccion_detecta_identificacion_alucinada():
    """Si el modelo inventa un RUC, la validación del SRI lo caza."""
    from app.ia.extraccion import extraer_factura

    datos = json.loads(json.dumps(EXTRACCION_VALIDA))
    datos["cliente"]["identificacion"] = "1234567890123"  # verificador inválido

    resultado = extraer_factura(
        "…", cliente_ai=ClienteFalso(RespuestaFalsa(datos))
    )

    assert resultado.advertencias
    assert "no es válida" in resultado.advertencias[0]
    assert not resultado.listo_para_emitir


def test_extraccion_detecta_precio_cero():
    from app.ia.extraccion import extraer_factura

    datos = json.loads(json.dumps(EXTRACCION_VALIDA))
    datos["detalles"][0]["precio_unitario"] = "0"

    resultado = extraer_factura("…", cliente_ai=ClienteFalso(RespuestaFalsa(datos)))
    assert any("no tiene precio" in a for a in resultado.advertencias)


def test_precio_con_iva_incluido_se_convierte_a_base():
    """115 con IVA 15% incluido son 100 de base imponible."""
    from app.ia.extraccion import normalizar_detalles

    detalles = normalizar_detalles(
        {
            "detalles": [
                {
                    "descripcion": "Producto",
                    "cantidad": "1",
                    "precio_unitario": "115.00",
                    "precio_incluye_iva": True,
                    "codigo_iva": "4",
                }
            ]
        }
    )

    assert round(detalles[0]["precio_unitario"], 2) == Decimal("100.00")


def test_precio_sin_iva_no_se_toca():
    from app.ia.extraccion import normalizar_detalles

    detalles = normalizar_detalles(
        {
            "detalles": [
                {
                    "descripcion": "Producto",
                    "cantidad": "2",
                    "precio_unitario": "50.00",
                    "precio_incluye_iva": False,
                    "codigo_iva": "4",
                }
            ]
        }
    )

    assert detalles[0]["precio_unitario"] == Decimal("50.00")
    assert detalles[0]["cantidad"] == Decimal("2")


def test_tarifa_cero_no_divide():
    """Con IVA 0% el precio 'con IVA' es el mismo que sin IVA."""
    from app.ia.extraccion import normalizar_detalles

    detalles = normalizar_detalles(
        {
            "detalles": [
                {
                    "descripcion": "Pan",
                    "cantidad": "1",
                    "precio_unitario": "1.85",
                    "precio_incluye_iva": True,
                    "codigo_iva": "0",
                }
            ]
        }
    )

    assert detalles[0]["precio_unitario"] == Decimal("1.85")


def test_faltan_datos_no_esta_listo():
    from app.ia.extraccion import extraer_factura

    datos = json.loads(json.dumps(EXTRACCION_VALIDA))
    datos["datos_faltantes"] = ["identificacion_cliente"]

    resultado = extraer_factura("…", cliente_ai=ClienteFalso(RespuestaFalsa(datos)))
    assert not resultado.listo_para_emitir


def test_refusal_se_convierte_en_error_legible():
    """Un bloqueo de seguridad llega sin texto; no debe reventar."""
    from app.ia.extraccion import ErrorExtraccion, extraer_factura

    with pytest.raises(ErrorExtraccion, match="declinó"):
        extraer_factura(
            "…", cliente_ai=ClienteFalso(RespuestaFalsa(None, finish_reason="SAFETY"))
        )


def test_respuesta_truncada_se_reporta():
    """
    Un corte por longitud también llega sin texto. Distinguirlo del rechazo
    importa: uno se arregla acortando el mensaje y el otro reformulándolo.
    """
    from app.ia.extraccion import ErrorExtraccion, extraer_factura

    with pytest.raises(ErrorExtraccion, match="cortó"):
        extraer_factura(
            "…", cliente_ai=ClienteFalso(RespuestaFalsa(None, finish_reason="MAX_TOKENS"))
        )


def test_json_invalido_se_reporta_con_claridad():
    from app.ia.extraccion import ErrorExtraccion, extraer_factura

    class RespuestaRota(RespuestaFalsa):
        def __init__(self):
            super().__init__({})
            self.text = "esto no es json"

    with pytest.raises(ErrorExtraccion, match="no es JSON"):
        extraer_factura("…", cliente_ai=ClienteFalso(RespuestaRota()))


def test_el_esquema_declara_todos_los_campos_que_lee_el_codigo():
    """
    La salida estructurada se define con un modelo Pydantic. Si el modelo no
    declara un campo que `extraer_factura` luego lee, la extracción falla en
    producción con un KeyError y no aquí.
    """
    from app.ia.extraccion import ResultadoExtraccionEstructura

    campos = set(ResultadoExtraccionEstructura.model_fields)

    assert {
        "intencion",
        "cliente",
        "detalles",
        "forma_pago",
        "datos_faltantes",
        "respuesta_sugerida",
    } <= campos


# --------------------------------------------------------------------------
# Webhook
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cliente_web(tmp_path_factory):
    from fastapi.testclient import TestClient

    base = tmp_path_factory.mktemp("bd_wa") / "wa.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["WHATSAPP_SECRETO_APP"] = "secreto-de-prueba"
    os.environ["WHATSAPP_TOKEN_VERIFICACION"] = "token-de-prueba"
    # La allowlist es FAIL-CLOSED: sin este env var, _procesar rechazaría a
    # todos los remitentes de estas pruebas. Se autoriza el número usado abajo.
    os.environ["WHATSAPP_TELEFONOS_AUTORIZADOS"] = "593999,593000"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import crear_tablas
    from app.main import aplicacion

    crear_tablas()
    return iniciar_sesion(TestClient(aplicacion))


def _firmar(cuerpo: bytes) -> str:
    firma = hmac.new(b"secreto-de-prueba", cuerpo, hashlib.sha256).hexdigest()
    return f"sha256={firma}"


def test_verificacion_devuelve_el_challenge(cliente_web):
    respuesta = cliente_web.get(
        "/api/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-de-prueba",
            "hub.challenge": "1234567890",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.text == "1234567890"


def test_verificacion_rechaza_token_incorrecto(cliente_web):
    respuesta = cliente_web.get(
        "/api/whatsapp",
        params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "x"},
    )
    assert respuesta.status_code == 403


def test_webhook_rechaza_peticion_sin_firma(cliente_web):
    """Sin esto cualquiera podría inyectar mensajes y hacer que se facture."""
    respuesta = cliente_web.post("/api/whatsapp", json={"entry": []})
    assert respuesta.status_code == 403


def test_webhook_rechaza_firma_incorrecta(cliente_web):
    cuerpo = json.dumps({"entry": []}).encode()
    respuesta = cliente_web.post(
        "/api/whatsapp",
        content=cuerpo,
        headers={"X-Hub-Signature-256": "sha256=" + "0" * 64, "Content-Type": "application/json"},
    )
    assert respuesta.status_code == 403


def test_webhook_acepta_firma_valida(cliente_web):
    cuerpo = json.dumps({"entry": []}).encode()
    respuesta = cliente_web.post(
        "/api/whatsapp",
        content=cuerpo,
        headers={"X-Hub-Signature-256": _firmar(cuerpo), "Content-Type": "application/json"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {"recibido": True}


def test_extraer_mensajes_aplana_la_estructura_de_meta(cliente_web):
    from app.routers.whatsapp import _extraer_mensajes

    cuerpo = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": "593999", "type": "text", "text": {"body": "hola"}},
                                {"from": "593999", "type": "image"},
                            ]
                        }
                    }
                ]
            }
        ]
    }

    mensajes = _extraer_mensajes(cuerpo)
    assert len(mensajes) == 2
    assert mensajes[0]["text"]["body"] == "hola"


def test_extraer_mensajes_tolera_cuerpos_vacios(cliente_web):
    """Meta también envía eventos de estado sin mensajes."""
    from app.routers.whatsapp import _extraer_mensajes

    assert _extraer_mensajes({}) == []
    assert _extraer_mensajes({"entry": [{"changes": [{"value": {"statuses": []}}]}]}) == []


# --------------------------------------------------------------------------
# Orquestador
# --------------------------------------------------------------------------


def test_conversacion_expira(cliente_web):
    from datetime import datetime, timedelta, timezone

    from app.ia.orquestador import Conversacion

    vieja = Conversacion(
        telefono="593999",
        actualizada=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    assert vieja.expirada()
    assert not Conversacion(telefono="593999").expirada()


def test_confirmacion_y_cancelacion_reconocidas(cliente_web):
    from app.ia.orquestador import CANCELACIONES, CONFIRMACIONES

    assert "sí" in CONFIRMACIONES and "si" in CONFIRMACIONES
    assert "no" in CANCELACIONES and "cancelar" in CANCELACIONES


def test_cancelar_descarta_el_borrador(cliente_web):
    from app.base_datos import SesionLocal
    from app.ia.orquestador import atender_mensaje, obtener_conversacion

    conversacion = obtener_conversacion("593000")
    conversacion.borrador = {"importe_total": Decimal("10")}

    sesion = SesionLocal()
    try:
        respuesta = atender_mensaje("593000", "no", sesion)
    finally:
        sesion.close()

    assert "Cancelado" in respuesta
    assert obtener_conversacion("593000").borrador is None


# --------------------------------------------------------------------------
# Multimodal: audio e imagen
#
# `_procesar` tenía cero pruebas pese a manejar tres rutas externas (Graph
# API, Whisper, Claude Vision). Como con el resto del módulo, no se prueba
# que esos servicios respondan bien —eso lo prueban sus propios dueños—, sino
# que `_procesar` enruta y degrada con gracia cuando no responden.
# --------------------------------------------------------------------------


def test_audio_sin_media_id_pide_reenviar(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "atender_mensaje", lambda *a, **k: (_ for _ in ()).throw(AssertionError))

    wa._procesar({"from": "593999", "type": "audio", "audio": {}})

    assert len(enviados) == 1
    assert "no pude obtener el audio" in enviados[0].lower()


def test_audio_sin_descarga_avisa(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "_descargar_media", lambda media_id: (None, None))

    wa._procesar({"from": "593999", "type": "audio", "audio": {"id": "m1"}})

    assert "no pude descargar el audio" in enviados[0].lower()


def test_audio_sin_transcripcion_avisa_configuracion(cliente_web, monkeypatch):
    """Sin OPENAI_API_KEY ni faster-whisper, el audio no debe fallar en silencio."""
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "_descargar_media", lambda media_id: (b"audio-falso", "audio/ogg"))
    monkeypatch.setattr(wa, "_transcribir_audio", lambda audio_bytes, mime: None)

    wa._procesar({"from": "593999", "type": "audio", "audio": {"id": "m1"}})

    assert "no configurada" in enviados[0].lower()
    assert "OPENAI_API_KEY" in enviados[0]


def test_audio_transcrito_llega_marcado_al_orquestador(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    enviados = []
    llamadas = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "_descargar_media", lambda media_id: (b"audio-falso", "audio/ogg"))
    monkeypatch.setattr(wa, "_transcribir_audio", lambda audio_bytes, mime: "factura para Juan")

    def atender_falso(telefono, texto, sesion, es_audio=False, es_imagen=False):
        llamadas.append((telefono, texto, es_audio, es_imagen))
        return "Entendido"

    monkeypatch.setattr(wa, "atender_mensaje", atender_falso)

    wa._procesar({"from": "593999", "type": "voice", "voice": {"id": "m1"}})

    assert llamadas == [("593999", "factura para Juan", True, False)]
    assert enviados == ["Entendido"]


def test_imagen_sin_media_id_pide_reenviar(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))

    wa._procesar({"from": "593999", "type": "image", "image": {}})

    assert "no pude obtener la imagen" in enviados[0].lower()


def test_imagen_sin_ocr_avisa_configuracion(cliente_web, monkeypatch):
    """Sin ANTHROPIC_API_KEY, una foto de factura no debe fallar en silencio."""
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "_descargar_media", lambda media_id: (b"imagen-falsa", "image/jpeg"))
    monkeypatch.setattr(wa, "_ocr_imagen", lambda imagen_bytes, mime: None)

    wa._procesar({"from": "593999", "type": "image", "image": {"id": "m1"}})

    assert "no configurado" in enviados[0].lower()
    assert "ANTHROPIC_API_KEY" in enviados[0]


def test_imagen_con_ocr_llega_marcada_al_orquestador(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    llamadas = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: None)
    monkeypatch.setattr(wa, "_descargar_media", lambda media_id: (b"imagen-falsa", "image/jpeg"))
    monkeypatch.setattr(wa, "_ocr_imagen", lambda imagen_bytes, mime: "RUC: 1790016919001")

    def atender_falso(telefono, texto, sesion, es_audio=False, es_imagen=False):
        llamadas.append((telefono, texto, es_audio, es_imagen))
        return "Entendido"

    monkeypatch.setattr(wa, "atender_mensaje", atender_falso)

    wa._procesar({"from": "593999", "type": "image", "image": {"id": "m1"}})

    assert llamadas == [("593999", "RUC: 1790016919001", False, True)]


def test_tipo_no_soportado_explica_los_formatos_aceptados(cliente_web, monkeypatch):
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))

    wa._procesar({"from": "593999", "type": "sticker"})

    assert "texto, audio e imágenes" in enviados[0]


def test_remitente_no_autorizado_no_llega_al_orquestador(cliente_web, monkeypatch):
    """
    La firma HMAC de Meta solo prueba el origen, no la identidad. Un número
    fuera de la allowlist recibe un mensaje neutro y nunca toca el orquestador
    (que emitiría comprobantes reales).
    """
    import app.routers.whatsapp as wa

    enviados = []
    monkeypatch.setattr(wa, "enviar_mensaje", lambda destino, texto: enviados.append(texto))
    monkeypatch.setattr(wa, "atender_mensaje", lambda *a, **k: (_ for _ in ()).throw(AssertionError))

    wa._procesar({"from": "000000000", "type": "text", "text": {"body": "factura para Juan"}})

    assert len(enviados) == 1
    assert "no está autorizado" in enviados[0].lower()


def test_allowlist_normaliza_espacios_y_signo_mas():
    """El '+' y los espacios del formato E.164 no deben afectar la comparación."""
    from app.routers.whatsapp import _remitente_autorizado

    # '593999' está en la allowlist configurada por el fixture cliente_web,
    # pero _remitente_autorizado no depende del fixture: normaliza ambos lados.
    assert _remitente_autorizado("+593 999") == _remitente_autorizado("593999")
