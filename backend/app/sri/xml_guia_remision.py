"""
XML de Guía de Remisión, versión 1.1.0 de la ficha técnica del SRI.

Estructura distinta a la de los demás comprobantes: no lleva importes ni
impuestos. Lo que declara es quién traslada (transportista y placa), desde
dónde y hasta dónde, y qué se mueve.

Los destinatarios van anidados dentro de `destinatarios`, y cada uno lleva sus
propios detalles: el SRI permite una guía con varias entregas. Aquí se emite un
único destinatario, que cubre el caso habitual; ampliarlo es añadir elementos a
esa lista sin tocar el resto.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from lxml import etree

from .clave_acceso import DatosClaveAcceso, TIPO_COMPROBANTE, generar_clave_acceso
from .modelos import Emisor
from .xml_factura import ID_COMPROBANTE, _texto

VERSION_GUIA = "1.1.0"

# Tabla 15 de la ficha técnica: motivo del traslado.
MOTIVOS_SRI = {
    "Venta": "Venta",
    "Compra": "Compra",
    "Traslado entre bodegas": "Traslado entre establecimientos de una misma empresa",
    "Devolución": "Devolución",
    "Consignación": "Consignación",
    "Reparación / mantenimiento": "Traslado para reparación o mantenimiento",
    "Exportación": "Exportación",
}


@dataclass
class ItemGuia:
    codigo_interno: str
    descripcion: str
    cantidad: Decimal
    codigo_adicional: str | None = None


@dataclass
class Destinatario:
    identificacion: str
    razon_social: str
    direccion: str
    motivo_traslado: str
    ruta: str | None = None
    documento_aduanero: str | None = None
    # Documento que sustenta el traslado (normalmente la factura).
    cod_doc_sustento: str | None = None
    num_doc_sustento: str | None = None
    fecha_doc_sustento: date | None = None
    items: list[ItemGuia] = field(default_factory=list)


@dataclass
class GuiaRemision:
    emisor: Emisor
    fecha_emision: date
    secuencial: int
    # Datos del transportista
    transportista_tipo_identificacion: str
    transportista_identificacion: str
    transportista_razon_social: str
    placa: str
    # Vigencia del traslado
    direccion_partida: str
    fecha_inicio: date
    fecha_fin: date
    destinatarios: list[Destinatario]
    ambiente: str = "1"
    tipo_emision: str = "1"
    info_adicional: dict[str, str] = field(default_factory=dict)


def generar_xml_guia_remision(guia: GuiaRemision, codigo_numerico: str) -> tuple[bytes, str]:
    datos_clave = DatosClaveAcceso(
        fecha_emision=guia.fecha_emision,
        tipo_comprobante=TIPO_COMPROBANTE["guia_remision"],
        ruc=guia.emisor.ruc,
        ambiente=guia.ambiente,
        establecimiento=guia.emisor.establecimiento,
        punto_emision=guia.emisor.punto_emision,
        secuencial=guia.secuencial,
        codigo_numerico=codigo_numerico,
        tipo_emision=guia.tipo_emision,
    )
    clave_acceso = generar_clave_acceso(datos_clave)

    raiz = etree.Element("guiaRemision", id=ID_COMPROBANTE, version=VERSION_GUIA)

    # --- infoTributaria ---
    info = etree.SubElement(raiz, "infoTributaria")
    _texto(info, "ambiente", guia.ambiente)
    _texto(info, "tipoEmision", guia.tipo_emision)
    _texto(info, "razonSocial", guia.emisor.razon_social)
    if guia.emisor.nombre_comercial:
        _texto(info, "nombreComercial", guia.emisor.nombre_comercial)
    _texto(info, "ruc", guia.emisor.ruc)
    _texto(info, "claveAcceso", clave_acceso)
    _texto(info, "codDoc", TIPO_COMPROBANTE["guia_remision"])
    _texto(info, "estab", guia.emisor.establecimiento)
    _texto(info, "ptoEmi", guia.emisor.punto_emision)
    _texto(info, "secuencial", str(guia.secuencial).zfill(9))
    _texto(info, "dirMatriz", guia.emisor.direccion_matriz)

    # --- infoGuiaRemision ---
    info_guia = etree.SubElement(raiz, "infoGuiaRemision")
    _texto(info_guia, "dirEstablecimiento", guia.emisor.direccion_establecimiento)
    _texto(info_guia, "dirPartida", guia.direccion_partida)
    _texto(info_guia, "razonSocialTransportista", guia.transportista_razon_social)
    _texto(info_guia, "tipoIdentificacionTransportista", guia.transportista_tipo_identificacion)
    _texto(info_guia, "rucTransportista", guia.transportista_identificacion)
    if guia.emisor.contribuyente_especial:
        _texto(info_guia, "contribuyenteEspecial", guia.emisor.contribuyente_especial)
    _texto(info_guia, "obligadoContabilidad", guia.emisor.obligado_contabilidad)
    _texto(info_guia, "fechaIniTransporte", guia.fecha_inicio.strftime("%d/%m/%Y"))
    _texto(info_guia, "fechaFinTransporte", guia.fecha_fin.strftime("%d/%m/%Y"))
    _texto(info_guia, "placa", guia.placa)

    # --- destinatarios ---
    destinatarios = etree.SubElement(raiz, "destinatarios")
    for entrada in guia.destinatarios:
        destinatario = etree.SubElement(destinatarios, "destinatario")
        _texto(destinatario, "identificacionDestinatario", entrada.identificacion)
        _texto(destinatario, "razonSocialDestinatario", entrada.razon_social)
        _texto(destinatario, "dirDestinatario", entrada.direccion)
        _texto(
            destinatario,
            "motivoTraslado",
            MOTIVOS_SRI.get(entrada.motivo_traslado, entrada.motivo_traslado),
        )
        if entrada.documento_aduanero:
            _texto(destinatario, "docAduaneroUnico", entrada.documento_aduanero)
        if entrada.cod_doc_sustento:
            _texto(destinatario, "codEstabDestino", guia.emisor.establecimiento)
        if entrada.ruta:
            _texto(destinatario, "ruta", entrada.ruta)

        # El documento sustento es opcional, pero si va uno deben ir los tres.
        if entrada.cod_doc_sustento and entrada.num_doc_sustento:
            _texto(destinatario, "codDocSustento", entrada.cod_doc_sustento)
            _texto(destinatario, "numDocSustento", entrada.num_doc_sustento)
            if entrada.fecha_doc_sustento:
                _texto(
                    destinatario,
                    "fechaEmisionDocSustento",
                    entrada.fecha_doc_sustento.strftime("%d/%m/%Y"),
                )

        detalles = etree.SubElement(destinatario, "detalles")
        for item in entrada.items:
            detalle = etree.SubElement(detalles, "detalle")
            _texto(detalle, "codigoInterno", item.codigo_interno)
            if item.codigo_adicional:
                _texto(detalle, "codigoAdicional", item.codigo_adicional)
            _texto(detalle, "descripcion", item.descripcion)
            _texto(detalle, "cantidad", f"{item.cantidad:.6f}")

    # --- infoAdicional ---
    if guia.info_adicional:
        adicional = etree.SubElement(raiz, "infoAdicional")
        for nombre, valor in guia.info_adicional.items():
            campo = etree.SubElement(adicional, "campoAdicional", nombre=nombre)
            campo.text = str(valor)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return xml, clave_acceso
