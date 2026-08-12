"""
Cliente de los WebServices del SRI (recepción y autorización).

Son servicios SOAP 1.1. Se construye el sobre a mano en vez de usar zeep porque
son dos operaciones con un contrato muy simple, y así no se arrastra una
dependencia pesada ni se depende de que el WSDL esté accesible al arrancar.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass, field

import requests
from lxml import etree

ENDPOINTS = {
    "1": {  # Pruebas
        "recepcion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
        "autorizacion": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    },
    "2": {  # Producción
        "recepcion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
        "autorizacion": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    },
}

SOBRE_RECEPCION = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.recepcion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:validarComprobante>
      <xml>{xml_base64}</xml>
    </ec:validarComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

SOBRE_AUTORIZACION = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:autorizacionComprobante>
      <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
    </ec:autorizacionComprobante>
  </soapenv:Body>
</soapenv:Envelope>"""

TIEMPO_ESPERA = 30


@dataclass
class RespuestaRecepcion:
    estado: str
    mensajes: list[dict[str, str]] = field(default_factory=list)

    @property
    def recibida(self) -> bool:
        return self.estado == "RECIBIDA"


@dataclass
class RespuestaAutorizacion:
    estado: str
    numero_autorizacion: str | None = None
    fecha_autorizacion: str | None = None
    comprobante: str | None = None
    mensajes: list[dict[str, str]] = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


def _extraer_mensajes(nodo: etree._Element) -> list[dict[str, str]]:
    mensajes = []
    for mensaje in nodo.iter("mensaje"):
        mensajes.append(
            {
                "identificador": _texto_de(mensaje, "identificador"),
                "mensaje": _texto_de(mensaje, "mensaje"),
                "informacion_adicional": _texto_de(mensaje, "informacionAdicional"),
                "tipo": _texto_de(mensaje, "tipo"),
            }
        )
    return mensajes


def _texto_de(nodo: etree._Element, etiqueta: str) -> str:
    hijo = nodo.find(etiqueta)
    return (hijo.text or "").strip() if hijo is not None else ""


def enviar_recepcion(xml_firmado: bytes, ambiente: str) -> RespuestaRecepcion:
    """Paso 1: el SRI valida esquema y firma, y responde RECIBIDA o DEVUELTA."""
    cuerpo = SOBRE_RECEPCION.format(xml_base64=base64.b64encode(xml_firmado).decode())

    respuesta = requests.post(
        ENDPOINTS[ambiente]["recepcion"],
        data=cuerpo.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
        timeout=TIEMPO_ESPERA,
    )
    respuesta.raise_for_status()

    arbol = etree.fromstring(respuesta.content)
    estado = next((e.text for e in arbol.iter("estado")), "DESCONOCIDO")
    return RespuestaRecepcion(estado=estado or "DESCONOCIDO", mensajes=_extraer_mensajes(arbol))


def consultar_autorizacion(clave_acceso: str, ambiente: str) -> RespuestaAutorizacion:
    """Paso 2: se consulta por clave de acceso el resultado de la autorización."""
    cuerpo = SOBRE_AUTORIZACION.format(clave_acceso=clave_acceso)

    respuesta = requests.post(
        ENDPOINTS[ambiente]["autorizacion"],
        data=cuerpo.encode("utf-8"),
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
        timeout=TIEMPO_ESPERA,
    )
    respuesta.raise_for_status()

    arbol = etree.fromstring(respuesta.content)
    autorizacion = next(iter(arbol.iter("autorizacion")), None)
    if autorizacion is None:
        return RespuestaAutorizacion(estado="SIN RESPUESTA", mensajes=_extraer_mensajes(arbol))

    return RespuestaAutorizacion(
        estado=_texto_de(autorizacion, "estado") or "DESCONOCIDO",
        numero_autorizacion=_texto_de(autorizacion, "numeroAutorizacion") or None,
        fecha_autorizacion=_texto_de(autorizacion, "fechaAutorizacion") or None,
        comprobante=_texto_de(autorizacion, "comprobante") or None,
        mensajes=_extraer_mensajes(autorizacion),
    )


def emitir(
    xml_firmado: bytes,
    clave_acceso: str,
    ambiente: str,
    reintentos: int = 4,
    espera_segundos: int = 3,
) -> tuple[RespuestaRecepcion, RespuestaAutorizacion | None]:
    """
    Flujo completo: recepción y luego consulta de autorización.

    El SRI no autoriza de forma síncrona: tras la recepción hay que esperar y
    reconsultar. Por eso el reintento con espera en vez de una sola llamada.
    """
    recepcion = enviar_recepcion(xml_firmado, ambiente)
    if not recepcion.recibida:
        return recepcion, None

    for intento in range(reintentos):
        if intento:
            time.sleep(espera_segundos)
        autorizacion = consultar_autorizacion(clave_acceso, ambiente)
        if autorizacion.estado not in ("", "SIN RESPUESTA", "EN PROCESO"):
            return recepcion, autorizacion

    return recepcion, consultar_autorizacion(clave_acceso, ambiente)
