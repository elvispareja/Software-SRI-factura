"""
Generación del XML de factura, versión 1.1.0 de la ficha técnica del SRI.

El orden de los elementos importa: el XSD del SRI usa `xsd:sequence`, así que un
campo fuera de sitio provoca rechazo por "ERROR ESTRUCTURA XML" aunque el
contenido sea correcto.
"""

from __future__ import annotations

from decimal import Decimal

from lxml import etree

from .clave_acceso import DatosClaveAcceso, TIPO_COMPROBANTE, generar_clave_acceso
from .modelos import Factura

VERSION_FACTURA = "1.1.0"

# Id fijo que exige el SRI en el nodo raíz para poder referenciarlo en la firma.
ID_COMPROBANTE = "comprobante"


def _texto(padre: etree._Element, etiqueta: str, valor) -> etree._Element:
    elemento = etree.SubElement(padre, etiqueta)
    elemento.text = _formatear(valor)
    return elemento


def _formatear(valor) -> str:
    if isinstance(valor, Decimal):
        return f"{valor:.2f}"
    if isinstance(valor, bool):
        return "SI" if valor else "NO"
    return str(valor)


def construir_info_tributaria(
    raiz: etree._Element,
    factura: Factura,
    clave_acceso: str,
    cod_doc: str = TIPO_COMPROBANTE["factura"],
) -> None:
    emisor = factura.emisor
    info = etree.SubElement(raiz, "infoTributaria")

    _texto(info, "ambiente", factura.ambiente)
    _texto(info, "tipoEmision", factura.tipo_emision)
    _texto(info, "razonSocial", emisor.razon_social)
    if emisor.nombre_comercial:
        _texto(info, "nombreComercial", emisor.nombre_comercial)
    _texto(info, "ruc", emisor.ruc)
    _texto(info, "claveAcceso", clave_acceso)
    _texto(info, "codDoc", cod_doc)
    _texto(info, "estab", emisor.establecimiento)
    _texto(info, "ptoEmi", emisor.punto_emision)
    _texto(info, "secuencial", str(factura.secuencial).zfill(9))
    _texto(info, "dirMatriz", emisor.direccion_matriz)

    # Campos opcionales; solo se emiten si aplican al contribuyente.
    if emisor.agente_retencion:
        _texto(info, "agenteRetencion", emisor.agente_retencion)
    if emisor.contribuyente_rimpe:
        _texto(info, "contribuyenteRimpe", emisor.contribuyente_rimpe)


def construir_info_factura(raiz: etree._Element, factura: Factura) -> None:
    comprador = factura.comprador
    info = etree.SubElement(raiz, "infoFactura")

    _texto(info, "fechaEmision", factura.fecha_emision.strftime("%d/%m/%Y"))
    if factura.emisor.direccion_establecimiento:
        _texto(info, "dirEstablecimiento", factura.emisor.direccion_establecimiento)
    if factura.emisor.contribuyente_especial:
        _texto(info, "contribuyenteEspecial", factura.emisor.contribuyente_especial)
    _texto(info, "obligadoContabilidad", factura.emisor.obligado_contabilidad)
    _texto(info, "tipoIdentificacionComprador", comprador.tipo_identificacion)
    _texto(info, "razonSocialComprador", comprador.razon_social)
    _texto(info, "identificacionComprador", comprador.identificacion)
    _texto(info, "direccionComprador", comprador.direccion)
    _texto(info, "totalSinImpuestos", factura.total_sin_impuestos)
    _texto(info, "totalDescuento", factura.total_descuento)

    total_con_impuestos = etree.SubElement(info, "totalConImpuestos")
    for grupo in factura.impuestos_agrupados():
        impuesto = etree.SubElement(total_con_impuestos, "totalImpuesto")
        _texto(impuesto, "codigo", grupo["codigo"])
        _texto(impuesto, "codigoPorcentaje", grupo["codigo_porcentaje"])
        _texto(impuesto, "baseImponible", grupo["base_imponible"])
        _texto(impuesto, "valor", grupo["valor"])

    _texto(info, "propina", Decimal("0"))
    _texto(info, "importeTotal", factura.importe_total)
    _texto(info, "moneda", factura.moneda)

    pagos = etree.SubElement(info, "pagos")
    lista_pagos = factura.pagos or []
    if not lista_pagos:
        # Si no se detalló el pago, se declara el total como contado.
        pago = etree.SubElement(pagos, "pago")
        _texto(pago, "formaPago", "01")
        _texto(pago, "total", factura.importe_total)
    else:
        for item in lista_pagos:
            pago = etree.SubElement(pagos, "pago")
            _texto(pago, "formaPago", item.forma_pago)
            _texto(pago, "total", item.total)
            if item.plazo is not None:
                _texto(pago, "plazo", item.plazo)
            if item.unidad_tiempo:
                _texto(pago, "unidadTiempo", item.unidad_tiempo)


def construir_detalles(raiz: etree._Element, factura: Factura) -> None:
    detalles = etree.SubElement(raiz, "detalles")

    for item in factura.detalles:
        detalle = etree.SubElement(detalles, "detalle")
        _texto(detalle, "codigoPrincipal", item.codigo_principal)
        if item.codigo_auxiliar:
            _texto(detalle, "codigoAuxiliar", item.codigo_auxiliar)
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


def construir_info_adicional(raiz: etree._Element, factura: Factura) -> None:
    if not factura.info_adicional:
        return

    adicional = etree.SubElement(raiz, "infoAdicional")
    for nombre, valor in factura.info_adicional.items():
        campo = etree.SubElement(adicional, "campoAdicional", nombre=nombre)
        campo.text = str(valor)


def generar_xml_factura(
    factura: Factura,
    codigo_numerico: str,
    cod_doc: str = TIPO_COMPROBANTE["factura"],
) -> tuple[bytes, str]:
    """
    Devuelve `(xml_bytes, clave_acceso)`.

    El `codigo_numerico` son 8 dígitos que define el emisor; debe ser estable
    para un mismo comprobante, porque forma parte de la clave de acceso.

    `cod_doc` existe porque la **liquidación de compra** comparte exactamente
    esta estructura pero es el tipo `03`, no el `01`. Emitirla como factura la
    registraría ante el SRI como una venta en lugar de una compra, que es un
    error tributario, no de formato. El código va en dos sitios —la clave de
    acceso y `infoTributaria`— y deben coincidir.
    """
    datos_clave = DatosClaveAcceso(
        fecha_emision=factura.fecha_emision,
        tipo_comprobante=cod_doc,
        ruc=factura.emisor.ruc,
        ambiente=factura.ambiente,
        establecimiento=factura.emisor.establecimiento,
        punto_emision=factura.emisor.punto_emision,
        secuencial=factura.secuencial,
        codigo_numerico=codigo_numerico,
        tipo_emision=factura.tipo_emision,
    )
    clave_acceso = generar_clave_acceso(datos_clave)

    raiz = etree.Element("factura", id=ID_COMPROBANTE, version=VERSION_FACTURA)
    construir_info_tributaria(raiz, factura, clave_acceso, cod_doc)
    construir_info_factura(raiz, factura)
    construir_detalles(raiz, factura)
    construir_info_adicional(raiz, factura)

    xml = etree.tostring(raiz, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return xml, clave_acceso
