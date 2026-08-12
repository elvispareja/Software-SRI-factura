"""
XML de Nota de Crédito, versión 1.1.0 de la ficha técnica del SRI.

Una nota de crédito siempre modifica un comprobante anterior: sin
`codDocModificado`, `numDocModificado` y `fechaEmisionDocSustento` el SRI la
rechaza. El `valorModificacion` es el importe total que se está devolviendo o
anulando, y debe cuadrar con la suma de los detalles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from lxml import etree

from .clave_acceso import DatosClaveAcceso, TIPO_COMPROBANTE, generar_clave_acceso
from .modelos import Comprador, Detalle, Emisor, redondear
from .xml_factura import ID_COMPROBANTE, _texto

VERSION_NOTA_CREDITO = "1.1.0"

# Tabla 3 del SRI: tipo del documento que se está modificando.
DOCUMENTO_MODIFICADO = {"factura": "01", "nota_venta": "03", "liquidacion_compra": "03"}


@dataclass
class NotaCredito:
    emisor: Emisor
    comprador: Comprador
    fecha_emision: date
    secuencial: int
    detalles: list[Detalle]
    motivo: str
    # Documento que se modifica
    cod_doc_modificado: str
    num_doc_modificado: str
    fecha_emision_doc_sustento: date
    ambiente: str = "1"
    tipo_emision: str = "1"
    moneda: str = "DOLAR"
    info_adicional: dict[str, str] = field(default_factory=dict)

    @property
    def total_sin_impuestos(self) -> Decimal:
        return redondear(sum((d.base_imponible for d in self.detalles), Decimal("0")))

    def impuestos_agrupados(self) -> list[dict]:
        grupos: dict[str, dict] = {}
        for detalle in self.detalles:
            grupo = grupos.setdefault(
                detalle.codigo_iva,
                {
                    "codigo": "2",
                    "codigo_porcentaje": detalle.codigo_iva,
                    "base_imponible": Decimal("0"),
                    "valor": Decimal("0"),
                    "tarifa": detalle.tarifa,
                },
            )
            grupo["base_imponible"] = redondear(grupo["base_imponible"] + detalle.base_imponible)
            grupo["valor"] = redondear(grupo["valor"] + detalle.valor_iva)
        return [grupos[codigo] for codigo in sorted(grupos)]

    @property
    def valor_modificacion(self) -> Decimal:
        """Importe total de la nota: base + IVA. Es lo que se devuelve al cliente."""
        iva = sum((g["valor"] for g in self.impuestos_agrupados()), Decimal("0"))
        return redondear(self.total_sin_impuestos + iva)


def generar_xml_nota_credito(nota: NotaCredito, codigo_numerico: str) -> tuple[bytes, str]:
    datos_clave = DatosClaveAcceso(
        fecha_emision=nota.fecha_emision,
        tipo_comprobante=TIPO_COMPROBANTE["nota_credito"],
        ruc=nota.emisor.ruc,
        ambiente=nota.ambiente,
        establecimiento=nota.emisor.establecimiento,
        punto_emision=nota.emisor.punto_emision,
        secuencial=nota.secuencial,
        codigo_numerico=codigo_numerico,
        tipo_emision=nota.tipo_emision,
    )
    clave_acceso = generar_clave_acceso(datos_clave)

    raiz = etree.Element("notaCredito", id=ID_COMPROBANTE, version=VERSION_NOTA_CREDITO)

    # --- infoTributaria ---
    info = etree.SubElement(raiz, "infoTributaria")
    _texto(info, "ambiente", nota.ambiente)
    _texto(info, "tipoEmision", nota.tipo_emision)
    _texto(info, "razonSocial", nota.emisor.razon_social)
    if nota.emisor.nombre_comercial:
        _texto(info, "nombreComercial", nota.emisor.nombre_comercial)
    _texto(info, "ruc", nota.emisor.ruc)
    _texto(info, "claveAcceso", clave_acceso)
    _texto(info, "codDoc", TIPO_COMPROBANTE["nota_credito"])
    _texto(info, "estab", nota.emisor.establecimiento)
    _texto(info, "ptoEmi", nota.emisor.punto_emision)
    _texto(info, "secuencial", str(nota.secuencial).zfill(9))
    _texto(info, "dirMatriz", nota.emisor.direccion_matriz)

    # --- infoNotaCredito ---
    info_nota = etree.SubElement(raiz, "infoNotaCredito")
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
    _texto(info_nota, "valorModificacion", nota.valor_modificacion)
    _texto(info_nota, "moneda", nota.moneda)

    total_con_impuestos = etree.SubElement(info_nota, "totalConImpuestos")
    for grupo in nota.impuestos_agrupados():
        impuesto = etree.SubElement(total_con_impuestos, "totalImpuesto")
        _texto(impuesto, "codigo", grupo["codigo"])
        _texto(impuesto, "codigoPorcentaje", grupo["codigo_porcentaje"])
        _texto(impuesto, "baseImponible", grupo["base_imponible"])
        _texto(impuesto, "valor", grupo["valor"])

    _texto(info_nota, "motivo", nota.motivo)

    # --- detalles ---
    detalles = etree.SubElement(raiz, "detalles")
    for item in nota.detalles:
        detalle = etree.SubElement(detalles, "detalle")
        _texto(detalle, "codigoInterno", item.codigo_principal)
        if item.codigo_auxiliar:
            _texto(detalle, "codigoAdicional", item.codigo_auxiliar)
        _texto(detalle, "descripcion", item.descripcion)
        _texto(detalle, "cantidad", f"{item.cantidad:.6f}")
        _texto(detalle, "precioUnitario", f"{item.precio_unitario:.6f}")
        _texto(detalle, "descuento", item.descuento)
        _texto(detalle, "precioTotalSinImpuesto", item.base_imponible)

        impuestos = etree.SubElement(detalle, "impuestos")
        impuesto = etree.SubElement(impuestos, "impuesto")
        _texto(impuesto, "codigo", "2")
        _texto(impuesto, "codigoPorcentaje", item.codigo_iva)
        _texto(impuesto, "tarifa", item.tarifa)
        _texto(impuesto, "baseImponible", item.base_imponible)
        _texto(impuesto, "valor", item.valor_iva)

    # --- infoAdicional ---
    if nota.info_adicional:
        adicional = etree.SubElement(raiz, "infoAdicional")
        for nombre, valor in nota.info_adicional.items():
            campo = etree.SubElement(adicional, "campoAdicional", nombre=nombre)
            campo.text = str(valor)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return xml, clave_acceso
