"""
XML de Nota de Débito, versión 1.0.0 de la ficha técnica del SRI.

Es la contraria de la nota de crédito: en vez de disminuir el valor de un
comprobante anterior, lo aumenta —intereses de mora, gastos de cobranza, un
recargo que no se facturó a tiempo—. Como aquélla, no vale por sí sola: sin
`codDocModificado`, `numDocModificado` y `fechaEmisionDocSustento` el SRI la
rechaza.

DIFERENCIA ESTRUCTURAL CON LA NOTA DE CRÉDITO
---------------------------------------------
La nota de débito **no lleva `<detalles>`**. Donde la de crédito enumera los
artículos que se devuelven, ésta declara `<motivos>`: una lista de razones con
su importe. Tiene sentido —lo que se cobra de más no es mercadería, es un
concepto— pero implica que su XML no se puede derivar del de la factura
cambiando cuatro etiquetas, y por eso vive en su propio módulo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from lxml import etree

from .clave_acceso import DatosClaveAcceso, TIPO_COMPROBANTE, generar_clave_acceso
from .modelos import Comprador, Emisor, PORCENTAJES_IVA, redondear
from .xml_factura import ID_COMPROBANTE, _texto

VERSION_NOTA_DEBITO = "1.0.0"


@dataclass
class MotivoDebito:
    """Una razón del cobro adicional, con su importe."""

    razon: str
    valor: Decimal


@dataclass
class NotaDebito:
    emisor: Emisor
    comprador: Comprador
    fecha_emision: date
    secuencial: int
    motivos: list[MotivoDebito]
    # Documento que se modifica
    cod_doc_modificado: str
    num_doc_modificado: str
    fecha_emision_doc_sustento: date
    # El recargo puede o no llevar IVA según el concepto: los intereses de mora
    # no son objeto de IVA, mientras que un servicio recargado sí lo lleva.
    codigo_iva: str = "4"
    ambiente: str = "1"
    tipo_emision: str = "1"
    moneda: str = "DOLAR"
    info_adicional: dict[str, str] = field(default_factory=dict)

    @property
    def tarifa(self) -> Decimal:
        return PORCENTAJES_IVA.get(self.codigo_iva, Decimal("0"))

    @property
    def total_sin_impuestos(self) -> Decimal:
        return redondear(sum((m.valor for m in self.motivos), Decimal("0")))

    @property
    def valor_iva(self) -> Decimal:
        return redondear(self.total_sin_impuestos * self.tarifa / Decimal("100"))

    @property
    def valor_total(self) -> Decimal:
        return redondear(self.total_sin_impuestos + self.valor_iva)


def generar_xml_nota_debito(nota: NotaDebito, codigo_numerico: str) -> tuple[bytes, str]:
    datos_clave = DatosClaveAcceso(
        fecha_emision=nota.fecha_emision,
        tipo_comprobante=TIPO_COMPROBANTE["nota_debito"],
        ruc=nota.emisor.ruc,
        ambiente=nota.ambiente,
        establecimiento=nota.emisor.establecimiento,
        punto_emision=nota.emisor.punto_emision,
        secuencial=nota.secuencial,
        codigo_numerico=codigo_numerico,
        tipo_emision=nota.tipo_emision,
    )
    clave_acceso = generar_clave_acceso(datos_clave)

    raiz = etree.Element("notaDebito", id=ID_COMPROBANTE, version=VERSION_NOTA_DEBITO)

    # --- infoTributaria ---
    info = etree.SubElement(raiz, "infoTributaria")
    _texto(info, "ambiente", nota.ambiente)
    _texto(info, "tipoEmision", nota.tipo_emision)
    _texto(info, "razonSocial", nota.emisor.razon_social)
    if nota.emisor.nombre_comercial:
        _texto(info, "nombreComercial", nota.emisor.nombre_comercial)
    _texto(info, "ruc", nota.emisor.ruc)
    _texto(info, "claveAcceso", clave_acceso)
    _texto(info, "codDoc", TIPO_COMPROBANTE["nota_debito"])
    _texto(info, "estab", nota.emisor.establecimiento)
    _texto(info, "ptoEmi", nota.emisor.punto_emision)
    _texto(info, "secuencial", str(nota.secuencial).zfill(9))
    _texto(info, "dirMatriz", nota.emisor.direccion_matriz)

    # --- infoNotaDebito ---
    info_nota = etree.SubElement(raiz, "infoNotaDebito")
    _texto(info_nota, "fechaEmision", nota.fecha_emision.strftime("%d/%m/%Y"))
    if nota.emisor.direccion_establecimiento:
        _texto(info_nota, "dirEstablecimiento", nota.emisor.direccion_establecimiento)
    _texto(info_nota, "tipoIdentificacionComprador", nota.comprador.tipo_identificacion)
    _texto(info_nota, "razonSocialComprador", nota.comprador.razon_social)
    _texto(info_nota, "identificacionComprador", nota.comprador.identificacion)
    if nota.emisor.contribuyente_especial:
        _texto(info_nota, "contribuyenteEspecial", nota.emisor.contribuyente_especial)
    _texto(info_nota, "obligadoContabilidad", nota.emisor.obligado_contabilidad)

    # Referencia obligatoria al documento que se modifica.
    _texto(info_nota, "codDocModificado", nota.cod_doc_modificado)
    _texto(info_nota, "numDocModificado", nota.num_doc_modificado)
    _texto(
        info_nota,
        "fechaEmisionDocSustento",
        nota.fecha_emision_doc_sustento.strftime("%d/%m/%Y"),
    )

    _texto(info_nota, "totalSinImpuestos", nota.total_sin_impuestos)

    impuestos = etree.SubElement(info_nota, "impuestos")
    impuesto = etree.SubElement(impuestos, "impuesto")
    _texto(impuesto, "codigo", "2")
    _texto(impuesto, "codigoPorcentaje", nota.codigo_iva)
    _texto(impuesto, "tarifa", nota.tarifa)
    _texto(impuesto, "baseImponible", nota.total_sin_impuestos)
    _texto(impuesto, "valor", nota.valor_iva)

    _texto(info_nota, "valorTotal", nota.valor_total)

    # --- motivos ---
    # Aquí va lo que en la factura serían los detalles: la nota de débito
    # cobra conceptos, no artículos.
    motivos = etree.SubElement(raiz, "motivos")
    for entrada in nota.motivos:
        motivo = etree.SubElement(motivos, "motivo")
        _texto(motivo, "razon", entrada.razon)
        _texto(motivo, "valor", entrada.valor)

    # --- infoAdicional ---
    if nota.info_adicional:
        adicional = etree.SubElement(raiz, "infoAdicional")
        for nombre, valor in nota.info_adicional.items():
            campo = etree.SubElement(adicional, "campoAdicional", nombre=nombre)
            campo.text = str(valor)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return xml, clave_acceso
