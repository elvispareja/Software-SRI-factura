"""
XML de Comprobante de Retención, versión 1.0.0 de la ficha técnica del SRI.

La retención declara cuánto se retuvo al proveedor por cada impuesto, siempre
referida al documento sustento (normalmente la factura de compra).

NOTA DE VERSIÓN: el SRI publica también la versión 2.0.0, que reagrupa los
impuestos bajo `docsSustento` y admite varios documentos por retención. Aquí se
implementa la 1.0.0 por ser la más simple y estar plenamente vigente; migrar a
2.0.0 es cambiar solo la construcción de `infoCompRetencion`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from lxml import etree

from .clave_acceso import DatosClaveAcceso, TIPO_COMPROBANTE, generar_clave_acceso
from .modelos import Comprador, Emisor, redondear
from .xml_factura import ID_COMPROBANTE, _texto

VERSION_RETENCION = "1.0.0"

# Tabla 20 del SRI: impuesto sobre el que se retiene.
IMPUESTOS_RETENCION = {
    "renta": "1",
    "iva": "2",
    "isd": "6",
}


@dataclass
class DetalleRetencion:
    """Una línea de retención: impuesto, código, base y porcentaje."""

    codigo_impuesto: str  # 1 renta, 2 IVA, 6 ISD
    codigo_retencion: str  # código de la tabla del SRI según el concepto
    base_imponible: Decimal
    porcentaje_retener: Decimal
    # Documento sustento sobre el que se retiene
    cod_doc_sustento: str = "01"
    num_doc_sustento: str = ""
    fecha_emision_doc_sustento: date | None = None

    @property
    def valor_retenido(self) -> Decimal:
        return redondear(self.base_imponible * self.porcentaje_retener / Decimal("100"))


@dataclass
class Retencion:
    emisor: Emisor
    sujeto_retenido: Comprador
    fecha_emision: date
    secuencial: int
    periodo_fiscal: str  # formato MM/AAAA
    detalles: list[DetalleRetencion]
    ambiente: str = "1"
    tipo_emision: str = "1"
    info_adicional: dict[str, str] = field(default_factory=dict)

    @property
    def total_retenido(self) -> Decimal:
        return redondear(sum((d.valor_retenido for d in self.detalles), Decimal("0")))


def generar_xml_retencion(retencion: Retencion, codigo_numerico: str) -> tuple[bytes, str]:
    datos_clave = DatosClaveAcceso(
        fecha_emision=retencion.fecha_emision,
        tipo_comprobante=TIPO_COMPROBANTE["retencion"],
        ruc=retencion.emisor.ruc,
        ambiente=retencion.ambiente,
        establecimiento=retencion.emisor.establecimiento,
        punto_emision=retencion.emisor.punto_emision,
        secuencial=retencion.secuencial,
        codigo_numerico=codigo_numerico,
        tipo_emision=retencion.tipo_emision,
    )
    clave_acceso = generar_clave_acceso(datos_clave)

    raiz = etree.Element("comprobanteRetencion", id=ID_COMPROBANTE, version=VERSION_RETENCION)

    # --- infoTributaria ---
    info = etree.SubElement(raiz, "infoTributaria")
    _texto(info, "ambiente", retencion.ambiente)
    _texto(info, "tipoEmision", retencion.tipo_emision)
    _texto(info, "razonSocial", retencion.emisor.razon_social)
    if retencion.emisor.nombre_comercial:
        _texto(info, "nombreComercial", retencion.emisor.nombre_comercial)
    _texto(info, "ruc", retencion.emisor.ruc)
    _texto(info, "claveAcceso", clave_acceso)
    _texto(info, "codDoc", TIPO_COMPROBANTE["retencion"])
    _texto(info, "estab", retencion.emisor.establecimiento)
    _texto(info, "ptoEmi", retencion.emisor.punto_emision)
    _texto(info, "secuencial", str(retencion.secuencial).zfill(9))
    _texto(info, "dirMatriz", retencion.emisor.direccion_matriz)

    # --- infoCompRetencion ---
    info_retencion = etree.SubElement(raiz, "infoCompRetencion")
    _texto(info_retencion, "fechaEmision", retencion.fecha_emision.strftime("%d/%m/%Y"))
    if retencion.emisor.direccion_establecimiento:
        _texto(info_retencion, "dirEstablecimiento", retencion.emisor.direccion_establecimiento)
    if retencion.emisor.contribuyente_especial:
        _texto(info_retencion, "contribuyenteEspecial", retencion.emisor.contribuyente_especial)
    _texto(info_retencion, "obligadoContabilidad", retencion.emisor.obligado_contabilidad)
    _texto(
        info_retencion,
        "tipoIdentificacionSujetoRetenido",
        retencion.sujeto_retenido.tipo_identificacion,
    )
    _texto(info_retencion, "razonSocialSujetoRetenido", retencion.sujeto_retenido.razon_social)
    _texto(info_retencion, "identificacionSujetoRetenido", retencion.sujeto_retenido.identificacion)
    _texto(info_retencion, "periodoFiscal", retencion.periodo_fiscal)

    # --- impuestos ---
    impuestos = etree.SubElement(raiz, "impuestos")
    for detalle in retencion.detalles:
        impuesto = etree.SubElement(impuestos, "impuesto")
        _texto(impuesto, "codigo", detalle.codigo_impuesto)
        _texto(impuesto, "codigoRetencion", detalle.codigo_retencion)
        _texto(impuesto, "baseImponible", detalle.base_imponible)
        _texto(impuesto, "porcentajeRetener", detalle.porcentaje_retener)
        _texto(impuesto, "valorRetenido", detalle.valor_retenido)
        _texto(impuesto, "codDocSustento", detalle.cod_doc_sustento)
        _texto(impuesto, "numDocSustento", detalle.num_doc_sustento)
        if detalle.fecha_emision_doc_sustento:
            _texto(
                impuesto,
                "fechaEmisionDocSustento",
                detalle.fecha_emision_doc_sustento.strftime("%d/%m/%Y"),
            )

    # --- infoAdicional ---
    if retencion.info_adicional:
        adicional = etree.SubElement(raiz, "infoAdicional")
        for nombre, valor in retencion.info_adicional.items():
            campo = etree.SubElement(adicional, "campoAdicional", nombre=nombre)
            campo.text = str(valor)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return xml, clave_acceso
