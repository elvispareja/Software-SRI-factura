"""
RIDE: Representación Impresa del Documento Electrónico.

Es lo único que el cliente final ve, así que debe contener los datos que el SRI
exige para que un tercero pueda verificar el comprobante: clave de acceso,
número de autorización, ambiente y fecha. Un RIDE sin clave de acceso es
inservible: es el dato con el que se consulta en el portal del SRI.

Los tres comprobantes que se imprimen —factura, guía de remisión y retención—
comparten cabecera (emisor a la izquierda, datos de autorización a la derecha)
y cambian solo en el cuerpo. Esa parte común vive en `_bloque_emisor`,
`_bloque_documento` y `_armar`, y cada `generar_ride_*` aporta lo suyo.
"""

from __future__ import annotations

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .estilos_pdf import (  # noqa: F401  (se reexportan: eran públicos de este módulo)
    GRIS_BORDE,
    GRIS_FONDO,
    NARANJA,
    TEXTO,
    TEXTO_SUAVE,
)
from .estilos_pdf import estilos as _estilos
from .estilos_pdf import marco as _marco
from .modelos import Factura
from .xml_guia_remision import GuiaRemision
from .xml_retencion import Retencion

NOMBRE_AMBIENTE = {"1": "PRUEBAS", "2": "PRODUCCIÓN"}


def _bloque_emisor(emisor, estilos) -> Table:
    contenido = [
        Paragraph(f"<b>{emisor.razon_social}</b>", estilos["titulo"]),
    ]
    if emisor.nombre_comercial:
        contenido.append(Paragraph(emisor.nombre_comercial, estilos["suave"]))
    contenido += [
        Spacer(1, 4),
        Paragraph(f"<b>RUC:</b> {emisor.ruc}", estilos["normal"]),
        Paragraph(f"<b>Matriz:</b> {emisor.direccion_matriz}", estilos["normal"]),
        Paragraph(f"<b>Sucursal:</b> {emisor.direccion_establecimiento}", estilos["normal"]),
        Paragraph(
            f"<b>Obligado a llevar contabilidad:</b> "
            f"{'SI' if emisor.obligado_contabilidad else 'NO'}",
            estilos["normal"],
        ),
    ]
    if emisor.contribuyente_rimpe:
        contenido.append(Paragraph(f"<b>{emisor.contribuyente_rimpe}</b>", estilos["normal"]))

    return Table([[contenido]], colWidths=[92 * mm], style=_marco())


def _bloque_documento(
    titulo: str,
    numero: str,
    clave_acceso: str,
    numero_autorizacion: str | None,
    fecha_autorizacion: str | None,
    ambiente: str,
    estilos,
) -> Table:
    autorizado = bool(numero_autorizacion)

    contenido = [
        Paragraph(f"<b>{titulo}</b>", estilos["titulo"]),
        Paragraph(f"<b>No.</b> {numero}", estilos["normal"]),
        Spacer(1, 4),
        Paragraph("NÚMERO DE AUTORIZACIÓN", estilos["etiqueta"]),
        Paragraph(
            numero_autorizacion or "PENDIENTE DE AUTORIZACIÓN",
            estilos["clave"] if autorizado else estilos["suave"],
        ),
        Spacer(1, 3),
        Paragraph("FECHA Y HORA DE AUTORIZACIÓN", estilos["etiqueta"]),
        Paragraph(fecha_autorizacion or "—", estilos["normal"]),
        Spacer(1, 3),
        Paragraph("AMBIENTE", estilos["etiqueta"]),
        Paragraph(NOMBRE_AMBIENTE.get(ambiente, "DESCONOCIDO"), estilos["normal"]),
        Spacer(1, 3),
        Paragraph("EMISIÓN", estilos["etiqueta"]),
        Paragraph("NORMAL", estilos["normal"]),
        Spacer(1, 3),
        Paragraph("CLAVE DE ACCESO", estilos["etiqueta"]),
        Paragraph(clave_acceso or "—", estilos["clave"]),
    ]

    return Table([[contenido]], colWidths=[92 * mm], style=_marco())


def _bloque_comprador(factura: Factura, estilos) -> Table:
    comprador = factura.comprador
    filas = [
        [
            Paragraph("<b>Razón social:</b>", estilos["normal"]),
            Paragraph(comprador.razon_social, estilos["normal"]),
            Paragraph("<b>Identificación:</b>", estilos["normal"]),
            Paragraph(comprador.identificacion, estilos["normal"]),
        ],
        [
            Paragraph("<b>Dirección:</b>", estilos["normal"]),
            Paragraph(comprador.direccion, estilos["normal"]),
            Paragraph("<b>Fecha emisión:</b>", estilos["normal"]),
            Paragraph(factura.fecha_emision.strftime("%d/%m/%Y"), estilos["normal"]),
        ],
    ]

    tabla = Table(filas, colWidths=[24 * mm, 78 * mm, 26 * mm, 60 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _tabla_detalles(factura: Factura, estilos) -> Table:
    cabecera = ["Cód.", "Descripción", "Cant.", "P. Unit.", "Desc.", "Total"]
    filas = [[Paragraph(f"<b>{texto}</b>", estilos["etiqueta"]) for texto in cabecera]]

    for detalle in factura.detalles:
        filas.append(
            [
                Paragraph(detalle.codigo_principal, estilos["suave"]),
                Paragraph(detalle.descripcion, estilos["normal"]),
                Paragraph(f"{detalle.cantidad:g}", estilos["normal"]),
                Paragraph(f"{detalle.precio_unitario:.2f}", estilos["normal"]),
                Paragraph(f"{detalle.descuento:.2f}", estilos["normal"]),
                Paragraph(f"{detalle.base_imponible:.2f}", estilos["normal"]),
            ]
        )

    tabla = Table(
        filas,
        colWidths=[22 * mm, 78 * mm, 16 * mm, 22 * mm, 20 * mm, 30 * mm],
        repeatRows=1,
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GRIS_FONDO),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _tabla_totales(factura: Factura, estilos) -> Table:
    filas = []
    for grupo in factura.impuestos_agrupados():
        etiqueta = (
            f"SUBTOTAL {grupo['tarifa']:g}%"
            if grupo["tarifa"] > 0
            else f"SUBTOTAL {grupo['tarifa']:g}%"
        )
        filas.append([etiqueta, f"{grupo['base_imponible']:.2f}"])

    filas.append(["SUBTOTAL SIN IMPUESTOS", f"{factura.total_sin_impuestos:.2f}"])
    filas.append(["TOTAL DESCUENTO", f"{factura.total_descuento:.2f}"])

    for grupo in factura.impuestos_agrupados():
        if grupo["tarifa"] > 0:
            filas.append([f"IVA {grupo['tarifa']:g}%", f"{grupo['valor']:.2f}"])

    filas.append(["VALOR TOTAL", f"{factura.importe_total:.2f}"])

    datos = [
        [Paragraph(etiqueta, estilos["normal"]), Paragraph(valor, estilos["normal"])]
        for etiqueta, valor in filas
    ]

    tabla = Table(datos, colWidths=[45 * mm, 30 * mm], hAlign="RIGHT")
    tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), GRIS_FONDO),
                ("TEXTCOLOR", (0, -1), (-1, -1), NARANJA),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return tabla


def _armar(
    emisor,
    titulo: str,
    numero: str,
    clave_acceso: str,
    numero_autorizacion: str | None,
    fecha_autorizacion: str | None,
    ambiente: str,
    cuerpo: list,
    estilos,
) -> io.BytesIO:
    """
    Monta el PDF: cabecera común, aviso de pruebas y el cuerpo que le pasen.

    Es lo que comparten los tres comprobantes. El aviso de ambiente de pruebas
    va aquí y no en cada generador porque olvidarlo en uno solo produciría un
    documento que parece válido y no lo es.
    """
    buffer = io.BytesIO()

    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=f"RIDE {numero}",
        author=emisor.razon_social,
    )

    cabecera = Table(
        [
            [
                _bloque_emisor(emisor, estilos),
                _bloque_documento(
                    titulo,
                    numero,
                    clave_acceso,
                    numero_autorizacion,
                    fecha_autorizacion,
                    ambiente,
                    estilos,
                ),
            ]
        ],
        colWidths=[92 * mm, 92 * mm],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]),
    )

    elementos = [cabecera, Spacer(1, 6 * mm)]

    if ambiente == "1":
        elementos.append(
            Paragraph(
                "<b>DOCUMENTO EMITIDO EN AMBIENTE DE PRUEBAS — SIN VALIDEZ TRIBUTARIA</b>",
                ParagraphStyle(
                    "aviso",
                    fontSize=9,
                    textColor=colors.HexColor("#b45309"),
                    alignment=1,
                    spaceAfter=6,
                ),
            )
        )

    elementos += cuerpo

    documento.build(elementos)
    buffer.seek(0)
    return buffer


def _info_adicional(info: dict, estilos) -> list:
    if not info:
        return []
    elementos = [Spacer(1, 5 * mm), Paragraph("<b>Información adicional</b>", estilos["normal"])]
    elementos += [Paragraph(f"{nombre}: {valor}", estilos["suave"]) for nombre, valor in info.items()]
    return elementos


def generar_ride(
    factura: Factura,
    numero: str,
    clave_acceso: str,
    numero_autorizacion: str | None = None,
    fecha_autorizacion: str | None = None,
    ambiente: str = "1",
    titulo: str = "FACTURA",
) -> io.BytesIO:
    """Devuelve el PDF del RIDE listo para descargar o adjuntar al correo."""
    estilos = _estilos()

    cuerpo = [
        _bloque_comprador(factura, estilos),
        Spacer(1, 4 * mm),
        _tabla_detalles(factura, estilos),
        Spacer(1, 4 * mm),
        _tabla_totales(factura, estilos),
    ]
    cuerpo += _info_adicional(factura.info_adicional, estilos)

    return _armar(
        factura.emisor,
        titulo,
        numero,
        clave_acceso,
        numero_autorizacion,
        fecha_autorizacion,
        ambiente,
        cuerpo,
        estilos,
    )


# --------------------------------------------------------------------------
# Guía de remisión
# --------------------------------------------------------------------------


def _bloque_traslado(guia: GuiaRemision, estilos) -> Table:
    filas = [
        [
            Paragraph("<b>Transportista:</b>", estilos["normal"]),
            Paragraph(guia.transportista_razon_social, estilos["normal"]),
            Paragraph("<b>Identificación:</b>", estilos["normal"]),
            Paragraph(guia.transportista_identificacion, estilos["normal"]),
        ],
        [
            Paragraph("<b>Placa:</b>", estilos["normal"]),
            Paragraph(guia.placa, estilos["normal"]),
            Paragraph("<b>Traslado:</b>", estilos["normal"]),
            Paragraph(
                f"{guia.fecha_inicio:%d/%m/%Y} — {guia.fecha_fin:%d/%m/%Y}",
                estilos["normal"],
            ),
        ],
        [
            Paragraph("<b>Punto de partida:</b>", estilos["normal"]),
            Paragraph(guia.direccion_partida, estilos["normal"]),
            Paragraph("", estilos["normal"]),
            Paragraph("", estilos["normal"]),
        ],
    ]

    tabla = Table(filas, colWidths=[28 * mm, 74 * mm, 26 * mm, 60 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _bloque_destinatario(destinatario, estilos) -> list:
    """Cada destinatario es un bloque de datos seguido de su tabla de ítems."""
    filas = [
        [
            Paragraph("<b>Destinatario:</b>", estilos["normal"]),
            Paragraph(destinatario.razon_social, estilos["normal"]),
            Paragraph("<b>Identificación:</b>", estilos["normal"]),
            Paragraph(destinatario.identificacion, estilos["normal"]),
        ],
        [
            Paragraph("<b>Dirección:</b>", estilos["normal"]),
            Paragraph(destinatario.direccion, estilos["normal"]),
            Paragraph("<b>Motivo:</b>", estilos["normal"]),
            Paragraph(destinatario.motivo_traslado, estilos["normal"]),
        ],
    ]
    if destinatario.ruta:
        filas.append(
            [
                Paragraph("<b>Ruta:</b>", estilos["normal"]),
                Paragraph(destinatario.ruta, estilos["normal"]),
                Paragraph("", estilos["normal"]),
                Paragraph("", estilos["normal"]),
            ]
        )

    datos = Table(filas, colWidths=[28 * mm, 74 * mm, 26 * mm, 60 * mm])
    datos.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    cabecera = ["Cód.", "Descripción", "Cantidad"]
    filas_items = [[Paragraph(f"<b>{t}</b>", estilos["etiqueta"]) for t in cabecera]]
    for item in destinatario.items:
        filas_items.append(
            [
                Paragraph(item.codigo_interno, estilos["suave"]),
                Paragraph(item.descripcion, estilos["normal"]),
                Paragraph(f"{item.cantidad:g}", estilos["normal"]),
            ]
        )

    items = Table(filas_items, colWidths=[30 * mm, 128 * mm, 30 * mm], repeatRows=1)
    items.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GRIS_FONDO),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return [datos, Spacer(1, 2 * mm), items]


def generar_ride_guia(
    guia: GuiaRemision,
    numero: str,
    clave_acceso: str,
    numero_autorizacion: str | None = None,
    fecha_autorizacion: str | None = None,
) -> io.BytesIO:
    """
    RIDE de la guía de remisión.

    Sin bloque de totales: la guía no documenta una venta sino un traslado, así
    que lo que se imprime es quién transporta, entre qué puntos y qué se mueve.
    """
    estilos = _estilos()

    cuerpo = [_bloque_traslado(guia, estilos)]
    for destinatario in guia.destinatarios:
        cuerpo += [Spacer(1, 4 * mm), *_bloque_destinatario(destinatario, estilos)]

    cuerpo += _info_adicional(guia.info_adicional, estilos)

    return _armar(
        guia.emisor,
        "GUÍA DE REMISIÓN",
        numero,
        clave_acceso,
        numero_autorizacion,
        fecha_autorizacion,
        guia.ambiente,
        cuerpo,
        estilos,
    )


# --------------------------------------------------------------------------
# Comprobante de retención
# --------------------------------------------------------------------------

NOMBRE_IMPUESTO = {"1": "RENTA", "2": "IVA", "6": "ISD"}


def _bloque_sujeto_retenido(retencion: Retencion, estilos) -> Table:
    sujeto = retencion.sujeto_retenido
    filas = [
        [
            Paragraph("<b>Razón social:</b>", estilos["normal"]),
            Paragraph(sujeto.razon_social, estilos["normal"]),
            Paragraph("<b>Identificación:</b>", estilos["normal"]),
            Paragraph(sujeto.identificacion, estilos["normal"]),
        ],
        [
            Paragraph("<b>Dirección:</b>", estilos["normal"]),
            Paragraph(sujeto.direccion, estilos["normal"]),
            Paragraph("<b>Fecha emisión:</b>", estilos["normal"]),
            Paragraph(retencion.fecha_emision.strftime("%d/%m/%Y"), estilos["normal"]),
        ],
        [
            Paragraph("<b>Período fiscal:</b>", estilos["normal"]),
            Paragraph(retencion.periodo_fiscal, estilos["normal"]),
            Paragraph("", estilos["normal"]),
            Paragraph("", estilos["normal"]),
        ],
    ]

    tabla = Table(filas, colWidths=[26 * mm, 76 * mm, 26 * mm, 60 * mm])
    tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _tabla_retenciones(retencion: Retencion, estilos) -> Table:
    cabecera = [
        "Comp.",
        "Núm. documento",
        "Fecha doc.",
        "Impuesto",
        "Cód.",
        "Base",
        "%",
        "Retenido",
    ]
    filas = [[Paragraph(f"<b>{t}</b>", estilos["etiqueta"]) for t in cabecera]]

    for detalle in retencion.detalles:
        fecha = (
            detalle.fecha_emision_doc_sustento.strftime("%d/%m/%Y")
            if detalle.fecha_emision_doc_sustento
            else "—"
        )
        filas.append(
            [
                Paragraph(detalle.cod_doc_sustento, estilos["suave"]),
                Paragraph(detalle.num_doc_sustento or "—", estilos["suave"]),
                Paragraph(fecha, estilos["suave"]),
                Paragraph(
                    NOMBRE_IMPUESTO.get(detalle.codigo_impuesto, detalle.codigo_impuesto),
                    estilos["normal"],
                ),
                Paragraph(detalle.codigo_retencion, estilos["normal"]),
                Paragraph(f"{detalle.base_imponible:.2f}", estilos["normal"]),
                Paragraph(f"{detalle.porcentaje_retener:g}", estilos["normal"]),
                Paragraph(f"{detalle.valor_retenido:.2f}", estilos["normal"]),
            ]
        )

    tabla = Table(
        filas,
        colWidths=[14 * mm, 38 * mm, 22 * mm, 22 * mm, 14 * mm, 26 * mm, 14 * mm, 38 * mm],
        repeatRows=1,
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GRIS_FONDO),
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (5, 1), (-1, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def _total_retenido(retencion: Retencion, estilos) -> Table:
    tabla = Table(
        [
            [
                Paragraph("TOTAL RETENIDO", estilos["normal"]),
                Paragraph(f"{retencion.total_retenido:.2f}", estilos["normal"]),
            ]
        ],
        colWidths=[45 * mm, 30 * mm],
        hAlign="RIGHT",
    )
    tabla.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
                ("TEXTCOLOR", (0, 0), (-1, -1), NARANJA),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return tabla


def generar_ride_retencion(
    retencion: Retencion,
    numero: str,
    clave_acceso: str,
    numero_autorizacion: str | None = None,
    fecha_autorizacion: str | None = None,
) -> io.BytesIO:
    """
    RIDE del comprobante de retención.

    El documento sustento va en la tabla, una vez por línea: en la versión
    1.0.0 del XML cada impuesto lleva el suyo, y el proveedor necesita ver
    contra qué factura se le retuvo.
    """
    estilos = _estilos()

    cuerpo = [
        _bloque_sujeto_retenido(retencion, estilos),
        Spacer(1, 4 * mm),
        _tabla_retenciones(retencion, estilos),
        Spacer(1, 4 * mm),
        _total_retenido(retencion, estilos),
    ]
    cuerpo += _info_adicional(retencion.info_adicional, estilos)

    return _armar(
        retencion.emisor,
        "COMPROBANTE DE RETENCIÓN",
        numero,
        clave_acceso,
        numero_autorizacion,
        fecha_autorizacion,
        retencion.ambiente,
        cuerpo,
        estilos,
    )
