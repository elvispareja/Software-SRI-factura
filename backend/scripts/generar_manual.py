"""
Genera el manual de usuario en PDF, con diagramas.

    python scripts/generar_manual.py [ruta_de_salida]

Los diagramas se dibujan con primitivas de ReportLab en vez de incrustar
imágenes: así el manual se regenera solo, sin depender de capturas que
envejecen en cuanto cambia una pantalla.
"""

from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Paleta: la misma del sistema, para que el manual y la pantalla se
# reconozcan como lo mismo.
NARANJA = colors.HexColor("#d95f00")
AZUL = colors.HexColor("#2563b0")
VERDE = colors.HexColor("#1a7f4b")
ROJO = colors.HexColor("#c0392b")
GRIS_TEXTO = colors.HexColor("#101423")
GRIS_SUAVE = colors.HexColor("#4a5568")
GRIS_BORDE = colors.HexColor("#c8cdd8")
GRIS_FONDO = colors.HexColor("#eef1f6")
AMARILLO_FONDO = colors.HexColor("#fdf3e3")

ANCHO_UTIL = 186 * mm


def estilos():
    base = getSampleStyleSheet()
    return {
        "portada": ParagraphStyle(
            "portada", parent=base["Title"], fontSize=26, leading=32,
            textColor=GRIS_TEXTO, spaceAfter=6,
        ),
        "subportada": ParagraphStyle(
            "subportada", parent=base["Normal"], fontSize=12, leading=17,
            textColor=GRIS_SUAVE, alignment=TA_CENTER,
        ),
        "h1": ParagraphStyle(
            "h1", parent=base["Heading1"], fontSize=17, leading=22,
            textColor=NARANJA, spaceBefore=14, spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2", parent=base["Heading2"], fontSize=12.5, leading=17,
            textColor=GRIS_TEXTO, spaceBefore=12, spaceAfter=5,
        ),
        "texto": ParagraphStyle(
            "texto", parent=base["Normal"], fontSize=9.5, leading=14.5,
            textColor=GRIS_TEXTO, spaceAfter=6,
        ),
        "nota": ParagraphStyle(
            "nota", parent=base["Normal"], fontSize=9, leading=13.5,
            textColor=GRIS_SUAVE,
        ),
        "celda": ParagraphStyle(
            "celda", parent=base["Normal"], fontSize=8.6, leading=12.5,
            textColor=GRIS_TEXTO,
        ),
        "celdaCab": ParagraphStyle(
            "celdaCab", parent=base["Normal"], fontSize=8.4, leading=11,
            textColor=colors.white,
        ),
        "codigo": ParagraphStyle(
            "codigo", parent=base["Normal"], fontName="Courier", fontSize=8.6,
            leading=12.5, textColor=GRIS_TEXTO,
        ),
        "pie": ParagraphStyle(
            "pie", parent=base["Normal"], fontSize=7.5, textColor=GRIS_SUAVE,
            alignment=TA_CENTER,
        ),
    }


E = estilos()


# ==========================================================================
# Diagramas
# ==========================================================================


class Flujo(Flowable):
    """Cadena horizontal de cajas con flechas: un proceso paso a paso."""

    def __init__(self, pasos, ancho=ANCHO_UTIL, alto=26 * mm, color=AZUL):
        super().__init__()
        self.pasos = pasos
        self.width = ancho
        self.height = alto
        self.color = color

    def draw(self):
        lienzo = self.canv
        n = len(self.pasos)
        flecha = 7 * mm
        caja = (self.width - flecha * (n - 1)) / n
        alto_caja = 15 * mm
        y = (self.height - alto_caja) / 2

        for indice, (titulo, detalle) in enumerate(self.pasos):
            x = indice * (caja + flecha)

            lienzo.setFillColor(GRIS_FONDO)
            lienzo.setStrokeColor(self.color)
            lienzo.setLineWidth(1)
            lienzo.roundRect(x, y, caja, alto_caja, 3 * mm, stroke=1, fill=1)

            lienzo.setFillColor(self.color)
            lienzo.setFont("Helvetica-Bold", 8.5)
            lienzo.drawCentredString(x + caja / 2, y + alto_caja - 6 * mm, titulo)

            lienzo.setFillColor(GRIS_SUAVE)
            lienzo.setFont("Helvetica", 7)
            for linea_i, linea in enumerate(detalle.split("\n")):
                lienzo.drawCentredString(
                    x + caja / 2, y + alto_caja - 9.5 * mm - linea_i * 3.2 * mm, linea
                )

            if indice < n - 1:
                cx = x + caja
                cy = y + alto_caja / 2
                lienzo.setStrokeColor(self.color)
                lienzo.setLineWidth(1.2)
                lienzo.line(cx + 1 * mm, cy, cx + flecha - 2 * mm, cy)
                lienzo.setFillColor(self.color)
                p = lienzo.beginPath()
                p.moveTo(cx + flecha - 1 * mm, cy)
                p.lineTo(cx + flecha - 3.2 * mm, cy + 1.4 * mm)
                p.lineTo(cx + flecha - 3.2 * mm, cy - 1.4 * mm)
                p.close()
                lienzo.drawPath(p, fill=1, stroke=0)


class Pantalla(Flowable):
    """Boceto de una pantalla: barra lateral, cabecera y contenido."""

    def __init__(self, titulo, opciones, filas, resaltar=None, ancho=ANCHO_UTIL):
        super().__init__()
        self.titulo = titulo
        self.opciones = opciones
        self.filas = filas
        self.resaltar = resaltar
        self.width = ancho
        self.height = 62 * mm

    def draw(self):
        lienzo = self.canv
        w, h = self.width, self.height

        lienzo.setFillColor(colors.white)
        lienzo.setStrokeColor(GRIS_BORDE)
        lienzo.setLineWidth(1)
        lienzo.roundRect(0, 0, w, h, 2 * mm, stroke=1, fill=1)

        # Barra de título de la ventana
        lienzo.setFillColor(GRIS_FONDO)
        lienzo.rect(0, h - 6 * mm, w, 6 * mm, stroke=0, fill=1)
        for indice, color in enumerate([ROJO, NARANJA, VERDE]):
            lienzo.setFillColor(color)
            lienzo.circle(5 * mm + indice * 4 * mm, h - 3 * mm, 1.1 * mm, stroke=0, fill=1)

        # Barra lateral
        lateral = 38 * mm
        lienzo.setFillColor(colors.HexColor("#f7f8fb"))
        lienzo.rect(0, 0, lateral, h - 6 * mm, stroke=0, fill=1)
        lienzo.setStrokeColor(GRIS_BORDE)
        lienzo.line(lateral, 0, lateral, h - 6 * mm)

        y = h - 12 * mm
        for opcion in self.opciones:
            activa = opcion == self.resaltar
            if activa:
                lienzo.setFillColor(colors.HexColor("#fdece0"))
                lienzo.roundRect(2 * mm, y - 1.6 * mm, lateral - 4 * mm, 5 * mm, 1 * mm,
                                 stroke=0, fill=1)
            lienzo.setFillColor(NARANJA if activa else GRIS_SUAVE)
            lienzo.setFont("Helvetica-Bold" if activa else "Helvetica", 7)
            lienzo.drawString(4.5 * mm, y, opcion)
            y -= 5.4 * mm

        # Cabecera del contenido
        lienzo.setFillColor(GRIS_TEXTO)
        lienzo.setFont("Helvetica-Bold", 10)
        lienzo.drawString(lateral + 5 * mm, h - 14 * mm, self.titulo)

        # Filas del contenido
        y = h - 22 * mm
        ancho_fila = w - lateral - 10 * mm
        for etiqueta, valor, tono in self.filas:
            lienzo.setFillColor(GRIS_FONDO)
            lienzo.roundRect(lateral + 5 * mm, y - 2 * mm, ancho_fila, 6.5 * mm, 1.2 * mm,
                             stroke=0, fill=1)
            lienzo.setFillColor(GRIS_TEXTO)
            lienzo.setFont("Helvetica", 7.6)
            lienzo.drawString(lateral + 8 * mm, y, etiqueta)

            color = {"ok": VERDE, "aviso": NARANJA, "error": ROJO}.get(tono, GRIS_SUAVE)
            lienzo.setFillColor(color)
            lienzo.setFont("Helvetica-Bold", 7.6)
            lienzo.drawRightString(lateral + ancho_fila + 2 * mm, y, valor)
            y -= 8 * mm


class Semaforo(Flowable):
    """Los estados de un comprobante ante el SRI, en fila."""

    def __init__(self, estados, ancho=ANCHO_UTIL):
        super().__init__()
        self.estados = estados
        self.width = ancho
        self.height = 30 * mm

    def draw(self):
        lienzo = self.canv
        n = len(self.estados)
        caja = self.width / n

        for indice, (nombre, color, texto) in enumerate(self.estados):
            x = indice * caja + 2 * mm
            ancho = caja - 4 * mm

            lienzo.setFillColor(color)
            lienzo.roundRect(x, self.height - 8 * mm, ancho, 6 * mm, 3 * mm,
                             stroke=0, fill=1)
            lienzo.setFillColor(colors.white)
            lienzo.setFont("Helvetica-Bold", 7.5)
            lienzo.drawCentredString(x + ancho / 2, self.height - 6 * mm, nombre)

            lienzo.setFillColor(GRIS_SUAVE)
            lienzo.setFont("Helvetica", 6.6)
            for linea_i, linea in enumerate(texto.split("\n")):
                lienzo.drawCentredString(
                    x + ancho / 2, self.height - 12 * mm - linea_i * 3.2 * mm, linea
                )


class Arquitectura(Flowable):
    """Las tres piezas del sistema y por dónde se hablan."""

    def __init__(self, ancho=ANCHO_UTIL):
        super().__init__()
        self.width = ancho
        self.height = 58 * mm

    def draw(self):
        lienzo = self.canv
        w = self.width

        def caja(x, y, ancho, alto, titulo, lineas, color):
            lienzo.setFillColor(GRIS_FONDO)
            lienzo.setStrokeColor(color)
            lienzo.setLineWidth(1.2)
            lienzo.roundRect(x, y, ancho, alto, 2.5 * mm, stroke=1, fill=1)
            lienzo.setFillColor(color)
            lienzo.setFont("Helvetica-Bold", 9)
            lienzo.drawCentredString(x + ancho / 2, y + alto - 6 * mm, titulo)
            lienzo.setFillColor(GRIS_SUAVE)
            lienzo.setFont("Helvetica", 7)
            for indice, linea in enumerate(lineas):
                lienzo.drawCentredString(
                    x + ancho / 2, y + alto - 10.5 * mm - indice * 3.6 * mm, linea
                )

        ancho_caja = 52 * mm
        alto_caja = 26 * mm
        y_alto = self.height - alto_caja - 2 * mm

        caja(0, y_alto, ancho_caja, alto_caja, "Tú",
             ["Navegador web", "o WhatsApp"], AZUL)
        caja((w - ancho_caja) / 2, y_alto, ancho_caja, alto_caja, "El sistema",
             ["Calcula, firma", "y guarda"], NARANJA)
        caja(w - ancho_caja, y_alto, ancho_caja, alto_caja, "SRI",
             ["Recibe y", "autoriza"], VERDE)

        # Flechas entre cajas
        cy = y_alto + alto_caja / 2
        for x_ini, x_fin in [
            (ancho_caja, (w - ancho_caja) / 2),
            ((w + ancho_caja) / 2, w - ancho_caja),
        ]:
            lienzo.setStrokeColor(GRIS_SUAVE)
            lienzo.setLineWidth(1)
            lienzo.line(x_ini + 2 * mm, cy, x_fin - 3 * mm, cy)
            lienzo.setFillColor(GRIS_SUAVE)
            p = lienzo.beginPath()
            p.moveTo(x_fin - 1.5 * mm, cy)
            p.lineTo(x_fin - 4 * mm, cy + 1.5 * mm)
            p.lineTo(x_fin - 4 * mm, cy - 1.5 * mm)
            p.close()
            lienzo.drawPath(p, fill=1, stroke=0)

        # Caja inferior: lo que devuelve
        y_bajo = 2 * mm
        lienzo.setFillColor(AMARILLO_FONDO)
        lienzo.setStrokeColor(NARANJA)
        lienzo.setDash(2, 2)
        lienzo.roundRect(0, y_bajo, w, 18 * mm, 2.5 * mm, stroke=1, fill=1)
        lienzo.setDash()

        lienzo.setFillColor(GRIS_TEXTO)
        lienzo.setFont("Helvetica-Bold", 8)
        lienzo.drawString(5 * mm, y_bajo + 12.5 * mm, "Lo que obtienes de vuelta")
        lienzo.setFillColor(GRIS_SUAVE)
        lienzo.setFont("Helvetica", 7.4)
        lienzo.drawString(5 * mm, y_bajo + 8 * mm,
                          "XML firmado (el documento legal)  ·  RIDE en PDF (lo que se entrega al cliente)")
        lienzo.drawString(5 * mm, y_bajo + 4 * mm,
                          "Número de autorización  ·  Reportes para el 103 y el 104")


# ==========================================================================
# Utilidades de composición
# ==========================================================================


def tabla(cabeceras, filas, anchos):
    datos = [[Paragraph(f"<b>{c}</b>", E["celdaCab"]) for c in cabeceras]]
    datos += [[Paragraph(str(celda), E["celda"]) for celda in fila] for fila in filas]

    t = Table(datos, colWidths=anchos, repeatRows=1)
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GRIS_TEXTO),
            ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafbfd")]),
        ])
    )
    return t


def aviso(titulo, cuerpo, color=NARANJA, fondo=AMARILLO_FONDO):
    contenido = [
        Paragraph(f"<b>{titulo}</b>", E["texto"]),
        Paragraph(cuerpo, E["nota"]),
    ]
    t = Table([[contenido]], colWidths=[ANCHO_UTIL])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), fondo),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, color),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ])
    )
    return t


def paso_numerado(numero, titulo, cuerpo):
    burbuja = Table(
        [[Paragraph(f'<font color="white"><b>{numero}</b></font>', E["texto"])]],
        colWidths=[8 * mm], rowHeights=[8 * mm],
    )
    burbuja.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NARANJA),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ])
    )

    texto = [Paragraph(f"<b>{titulo}</b>", E["texto"]), Paragraph(cuerpo, E["nota"])]

    t = Table([[burbuja, texto]], colWidths=[10 * mm, ANCHO_UTIL - 10 * mm])
    t.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ])
    )
    return t


def pie_de_pagina(lienzo, documento):
    lienzo.saveState()
    lienzo.setFont("Helvetica", 7.5)
    lienzo.setFillColor(GRIS_SUAVE)
    lienzo.drawCentredString(
        A4[0] / 2, 10 * mm,
        f"Sistema de Facturación Electrónica SRI · Manual de uso · página {documento.page}",
    )
    lienzo.setStrokeColor(GRIS_BORDE)
    lienzo.setLineWidth(0.5)
    lienzo.line(12 * mm, 14 * mm, A4[0] - 12 * mm, 14 * mm)
    lienzo.restoreState()


# ==========================================================================
# Contenido del manual
# ==========================================================================


def construir(ruta: Path) -> Path:
    documento = SimpleDocTemplate(
        str(ruta), pagesize=A4,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=14 * mm, bottomMargin=20 * mm,
        title="Manual de uso — Facturación Electrónica SRI",
        author="Sistema de Facturación Electrónica SRI",
    )

    c = []  # contenido

    # ---------------------------------------------------------------- portada
    c += [
        Spacer(1, 30 * mm),
        Paragraph("Manual de uso", ParagraphStyle(
            "t", parent=E["portada"], alignment=TA_CENTER)),
        Paragraph("Sistema de Facturación Electrónica SRI — Ecuador", E["subportada"]),
        Spacer(1, 12 * mm),
        Arquitectura(),
        Spacer(1, 10 * mm),
        aviso(
            "Para quién es este manual",
            "Para quien va a usar el sistema, no para quien lo programó. Explica qué "
            "hace cada pantalla, en qué orden usarlas y qué significa cada estado. "
            "No hace falta saber nada de facturación electrónica para seguirlo.",
            AZUL, colors.HexColor("#eef4fc"),
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------- qué es el sistema
    c += [
        Paragraph("1. Qué hace este sistema", E["h1"]),
        Paragraph(
            "Emite los documentos que el SRI exige en Ecuador y los envía a sus "
            "servidores para que los autorice. Tú capturas los datos; el sistema "
            "calcula los impuestos, arma el archivo XML con el formato oficial, lo "
            "<b>firma electrónicamente</b> y lo transmite. Cuando el SRI responde, "
            "guarda el número de autorización y genera el PDF que se entrega al cliente.",
            E["texto"],
        ),
        Spacer(1, 4 * mm),
        Paragraph("Los siete documentos que emite", E["h2"]),
        tabla(
            ["Documento", "Para qué sirve", "Cuándo lo usas"],
            [
                ["<b>Factura</b>",
                 "Respalda una venta de bienes o servicios",
                 "Es el documento del día a día"],
                ["<b>Nota de venta</b>",
                 "Venta simplificada",
                 "Régimen simplificado"],
                ["<b>Nota de crédito</b>",
                 "<b>Resta</b> valor a un documento ya emitido",
                 "Devolución, descuento posterior, anulación"],
                ["<b>Nota de débito</b>",
                 "<b>Suma</b> valor a un documento ya emitido",
                 "Intereses de mora, gastos de cobranza"],
                ["<b>Liquidación de compra</b>",
                 "Respalda una compra a quien no puede facturar",
                 "Compras a personas sin RUC"],
                ["<b>Guía de remisión</b>",
                 "Respalda el traslado físico de mercadería",
                 "Cuando la mercadería viaja"],
                ["<b>Retención</b>",
                 "Declara lo que retienes al pagar a un proveedor",
                 "Solo si eres agente de retención"],
            ],
            [34 * mm, 84 * mm, 68 * mm],
        ),
        Spacer(1, 6 * mm),
        aviso(
            "La factura no se corrige: se compensa",
            "Una vez que el SRI autoriza una factura, no se puede editar ni borrar — "
            "queda registrada en sus servidores. Si cobraste de más, emites una "
            "<b>nota de crédito</b>; si cobraste de menos, una <b>nota de débito</b>. "
            "Por eso el sistema no ofrece un botón de «editar factura emitida».",
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------------- primer uso
    c += [
        Paragraph("2. Antes de emitir: la configuración inicial", E["h1"]),
        Paragraph(
            "Se hace una sola vez. Sin estos cuatro pasos el sistema no puede emitir, "
            "y te lo dirá con un mensaje explicando qué falta.",
            E["texto"],
        ),
        Spacer(1, 3 * mm),
        Flujo([
            ("1. Empresa", "RUC y\ndirección"),
            ("2. Certificado", "Archivo .p12\ny su clave"),
            ("3. Numeración", "Establecimiento\ny punto de emisión"),
            ("4. Catálogos", "Clientes y\nartículos"),
        ], color=NARANJA),
        Spacer(1, 4 * mm),
        paso_numerado(
            1, "Datos de tu empresa  —  Configuraciones → Empresa",
            "RUC, razón social y dirección de la matriz. Estos datos salen impresos en "
            "cada documento y viajan al SRI, así que deben coincidir exactamente con lo "
            "que tienes registrado ante ellos. Si eres agente de retención o "
            "contribuyente especial, márcalo aquí: el sistema no te dejará emitir "
            "retenciones sin ese dato.",
        ),
        paso_numerado(
            2, "Certificado de firma  —  Configuraciones → Firma Electrónica",
            "Es un archivo <b>.p12</b> que compras al Banco Central, Security Data, ANF o "
            "Uanataca. Funciona como tu firma: sin él, el SRI rechaza todo. Se sube una "
            "vez, junto con su contraseña, y el sistema la guarda cifrada. El archivo "
            "nunca vuelve a salir del servidor.",
        ),
        paso_numerado(
            3, "Establecimientos y puntos de emisión  —  Configuraciones",
            "El SRI numera los documentos como <b>001-001-000000123</b>: los tres primeros "
            "dígitos son el local, los tres siguientes la caja, y los nueve últimos el "
            "correlativo. Si ya venías facturando, pon aquí el número por el que ibas "
            "para no repetir ninguno.",
        ),
        paso_numerado(
            4, "Clientes y artículos  —  Receptores y Artículos",
            "Los clientes se registran una vez y se reutilizan. El sistema <b>valida la "
            "cédula y el RUC</b> con el algoritmo oficial: si el dígito verificador no "
            "cuadra, te avisa antes de emitir, porque es de los rechazos más frecuentes "
            "del SRI.",
        ),
        Spacer(1, 3 * mm),
        aviso(
            "El rol del receptor importa",
            "Al registrar a alguien eliges si es <b>Cliente</b>, <b>Proveedor</b> o "
            "<b>Transportista</b>. No es decorativo: solo aparecerán transportistas al "
            "hacer una guía de remisión, y solo proveedores al hacer una retención. "
            "Evita emitir una retención a un cliente por equivocación.",
            AZUL, colors.HexColor("#eef4fc"),
        ),
        PageBreak(),
    ]

    # ----------------------------------------------------- emitir una factura
    c += [
        Paragraph("3. Emitir una factura, paso a paso", E["h1"]),
        Spacer(1, 2 * mm),
        Pantalla(
            "Nueva Factura",
            ["Inicio", "Receptores", "Artículos", "Comprobantes", "Cotizaciones",
             "Guías de Remisión", "Retenciones", "Reportes"],
            [
                ("1. Buscar y elegir el cliente", "escribe el nombre", ""),
                ("2. Agregar artículos y cantidades", "el total se recalcula", "ok"),
                ("3. Revisar el resumen de la derecha", "subtotal, IVA, total", ""),
                ("4. Pulsar «Emitir al SRI»", "listo para emitir", "ok"),
            ],
            resaltar="Comprobantes",
        ),
        Spacer(1, 5 * mm),
        Paragraph(
            "El total se recalcula con cada tecla. La columna de la derecha muestra el "
            "subtotal, el desglose de IVA por tarifa y el total; si algo impide emitir "
            "—falta el cliente, hay una línea en cero— aparece ahí en rojo y el botón "
            "de emitir queda deshabilitado hasta que se corrija.",
            E["texto"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Qué pasa cuando pulsas «Emitir al SRI»", E["h2"]),
        Flujo([
            ("Se guarda", "en tu base\nde datos"),
            ("Se firma", "con tu\ncertificado"),
            ("Se envía", "a los servidores\ndel SRI"),
            ("Responde", "autorizado\no rechazado"),
        ], color=VERDE),
        Spacer(1, 4 * mm),
        aviso(
            "Si se cae la conexión no pierdes nada",
            "El documento se guarda <b>firmado</b> antes de intentar el envío. Si el SRI "
            "no responde, queda en estado <b>Error</b> con el XML ya listo, y basta con "
            "pulsar «Reintentar» en el listado. No se vuelve a firmar ni cambia de número.",
            VERDE, colors.HexColor("#eaf6ef"),
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------------- estados
    c += [
        Paragraph("4. Los estados: qué significa cada uno", E["h1"]),
        Paragraph(
            "En el listado de comprobantes cada fila lleva una etiqueta de color. "
            "Esto es lo que quiere decir cada una y qué debes hacer.",
            E["texto"],
        ),
        Spacer(1, 3 * mm),
        Semaforo([
            ("Borrador", GRIS_SUAVE, "Creado pero\nno enviado"),
            ("Pendiente", NARANJA, "El SRI lo recibió\ny lo procesa"),
            ("Autorizado", VERDE, "Listo. Ya es\nun documento legal"),
            ("Devuelto", ROJO, "Rechazado al\nrecibirlo"),
            ("Rechazado", ROJO, "No superó la\nautorización"),
        ]),
        Spacer(1, 3 * mm),
        tabla(
            ["Estado", "Qué significa", "Qué haces"],
            [
                ["<b>Borrador</b>",
                 "Lo capturaste pero aún no se envió",
                 "Pulsa «Emitir»"],
                ["<b>Pendiente</b>",
                 "El SRI lo recibió pero aún no responde. Es normal: la autorización "
                 "no es instantánea",
                 "Pulsa «Consultar» al rato"],
                ["<b>Autorizado</b>",
                 "Tiene número de autorización. Ya es un documento tributario válido",
                 "Entrégalo al cliente"],
                ["<b>Devuelto</b>",
                 "El SRI lo rechazó al recibirlo, normalmente por un dato mal formado",
                 "Lee el motivo bajo la fila, corrige y reintenta"],
                ["<b>Rechazado</b>",
                 "Llegó bien pero no se autorizó (firma inválida, RUC no habilitado…)",
                 "Lee el motivo y reintenta"],
                ["<b>Error</b>",
                 "No se pudo contactar al SRI. El documento quedó firmado",
                 "Reintenta cuando haya conexión"],
                ["<b>Anulado</b>",
                 "Lo anulaste antes de enviarlo",
                 "Nada; no cuenta en los reportes"],
            ],
            [26 * mm, 96 * mm, 64 * mm],
        ),
        Spacer(1, 5 * mm),
        aviso(
            "Cuando el SRI rechaza, el motivo está en pantalla",
            "Despliega la fila del comprobante y verás el mensaje literal del SRI, con su "
            "código. Ese texto es lo único que permite saber qué corregir, así que se "
            "guarda tal cual llega, sin reinterpretarlo.",
            ROJO, colors.HexColor("#fdeeec"),
        ),
        PageBreak(),
    ]

    # ------------------------------------------------- pantallas del sistema
    c += [
        Paragraph("5. Qué hay en cada pantalla", E["h1"]),
        tabla(
            ["Pantalla", "Para qué sirve"],
            [
                ["<b>Inicio</b>",
                 "Resumen del negocio: facturado del mes y del año, ticket promedio, "
                 "gráfica de los doce meses, clientes y artículos que más facturan, y un "
                 "aviso si hay comprobantes sin autorizar. <b>Todas las cifras salen de "
                 "documentos autorizados</b>: los borradores no cuentan como ventas."],
                ["<b>Receptores</b>",
                 "Tus clientes, proveedores y transportistas. Valida cédulas y RUC."],
                ["<b>Artículos</b>",
                 "Productos y servicios con su precio, IVA y stock. Calcula el precio "
                 "desde el costo, distinguiendo <b>markup</b> (% sobre el costo) de "
                 "<b>margen</b> (% sobre la venta): con 10 de costo y 50%, uno da 15 y el "
                 "otro 20."],
                ["<b>Comprobantes</b>",
                 "Facturas, notas de crédito y de débito. Desde aquí se emite, se "
                 "reconsulta, y se descarga el PDF y el XML."],
                ["<b>Cotizaciones</b>",
                 "Propuestas al cliente. <b>No se envían al SRI</b>: no son documentos "
                 "tributarios. Solo se imprimen."],
                ["<b>Notas de venta / Liquidaciones</b>",
                 "Los otros dos tipos de venta, cada uno con su numeración propia."],
                ["<b>Guías de remisión</b>",
                 "Quién transporta, con qué placa, desde dónde y hasta dónde. No lleva "
                 "importes: documenta un traslado, no una venta."],
                ["<b>Retenciones</b>",
                 "Lo que retienes al pagar a un proveedor. Precarga el porcentaje según "
                 "el concepto, pero lo puedes cambiar."],
                ["<b>Reportes</b>",
                 "IVA en ventas (para el <b>formulario 104</b>), retenciones emitidas "
                 "(para el <b>103</b>) y ventas por tipo. Todo exportable a CSV para "
                 "abrirlo en Excel."],
                ["<b>Configuraciones</b>",
                 "Empresa, certificado, establecimientos, puntos de emisión y cuentas "
                 "bancarias."],
            ],
            [42 * mm, 144 * mm],
        ),
        Spacer(1, 4 * mm),
        aviso(
            "Atajo: Ctrl + K",
            "Abre un buscador de comandos desde cualquier pantalla. Escribe «factura», "
            "«retención» o «reportes» y te lleva ahí sin usar el menú.",
            AZUL, colors.HexColor("#eef4fc"),
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------------- reportes
    c += [
        Paragraph("6. Reportes: lo que necesitas para declarar", E["h1"]),
        Paragraph(
            "Cada mes hay que declarar al SRI. Estos reportes te dan las cifras ya "
            "sumadas, en la forma en que los formularios las piden.",
            E["texto"],
        ),
        Spacer(1, 2 * mm),
        Pantalla(
            "Reportes  —  IVA en ventas · Agosto 2026",
            ["Inicio", "Receptores", "Artículos", "Comprobantes", "Cotizaciones",
             "Guías de Remisión", "Retenciones", "Reportes"],
            [
                ("IVA 15%   —   base imponible", "$ 1.749,00", ""),
                ("IVA 0%    —   base imponible", "$ 9,25", ""),
                ("Total de IVA cobrado", "$ 262,35", "ok"),
                ("Exportar a CSV para Excel", "descargar", "aviso"),
            ],
            resaltar="Reportes",
        ),
        Spacer(1, 5 * mm),
        tabla(
            ["Reporte", "Para qué formulario", "Qué te da"],
            [
                ["<b>IVA en ventas</b>", "Formulario <b>104</b> (mensual)",
                 "Base imponible e IVA separados por tarifa. El 104 los pide en "
                 "casilleros distintos, por eso no se suman juntos."],
                ["<b>Retenciones</b>", "Formulario <b>103</b> (mensual)",
                 "Lo retenido por concepto, separando renta de IVA."],
                ["<b>Ventas</b>", "Control interno",
                 "Cuánto facturaste, en cuántos documentos y de qué tipo."],
            ],
            [34 * mm, 46 * mm, 106 * mm],
        ),
        Spacer(1, 5 * mm),
        aviso(
            "Las retenciones se agrupan por período fiscal, no por fecha",
            "Si emites el 2 de septiembre una retención del período 08/2026, aparece en "
            "el reporte de <b>agosto</b>. Es como el SRI las declara.",
            AZUL, colors.HexColor("#eef4fc"),
        ),
        Spacer(1, 4 * mm),
        aviso(
            "Verifica los porcentajes antes de usarlos en serio",
            "Los porcentajes de retención los fija el SRI por resolución y cambian. El "
            "sistema trae los de la <b>NAC-DGERCGC26-00000009</b> (vigente desde el "
            "1 de marzo de 2026) y los precarga al elegir el concepto, pero el campo es "
            "editable a propósito: si el SRI publica otros, los escribes y listo.",
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------------- whatsapp
    c += [
        Paragraph("7. Facturar por WhatsApp", E["h1"]),
        Paragraph(
            "Puedes emitir una factura escribiéndole al bot en lenguaje normal, sin "
            "abrir el navegador. Le dices qué vendiste y a quién, y él prepara el "
            "documento.",
            E["texto"],
        ),
        Spacer(1, 3 * mm),
        Flujo([
            ("Escribes", "«factura 2 laptops\na Juan Pérez»"),
            ("Entiende", "extrae cliente,\nartículos y precios"),
            ("Te resume", "muestra los totales\ny pide confirmación"),
            ("Confirmas", "respondes «sí»\ny se emite"),
        ], color=AZUL),
        Spacer(1, 5 * mm),
        aviso(
            "Nunca emite sin que tú confirmes",
            "Es la regla que gobierna todo el asistente. El modelo extrae los datos, "
            "pero <b>el sistema recalcula los totales</b> con su propio motor y te los "
            "enseña. Solo cuando respondes «sí» se transmite al SRI. Un asistente que "
            "factura sin confirmar convierte cualquier malentendido en un documento "
            "tributario que ya no se puede borrar.",
            VERDE, colors.HexColor("#eaf6ef"),
        ),
        Spacer(1, 4 * mm),
        Paragraph("Si algo no le cuadra, te pregunta", E["h2"]),
        tabla(
            ["Situación", "Qué hace el asistente"],
            [
                ["El cliente no está registrado",
                 "Lo crea si le das una cédula o RUC válidos; si falta la dirección, "
                 "te la pide (el SRI la exige)"],
                ["Falta el precio o la cantidad",
                 "Pregunta por lo que falta en vez de suponerlo"],
                ["La identificación no es válida",
                 "Lo dice y no continúa"],
                ["El SRI rechaza el documento",
                 "Te reenvía el motivo literal y deja la factura guardada para "
                 "reintentarla"],
            ],
            [58 * mm, 128 * mm],
        ),
        PageBreak(),
    ]

    # ------------------------------------------------------------- arrancar
    c += [
        Paragraph("8. Cómo arrancar el sistema", E["h1"]),
        Paragraph(
            "Son dos programas que se levantan por separado: el <b>servidor</b>, que "
            "hace el trabajo, y la <b>interfaz</b>, que es lo que ves en el navegador. "
            "Hacen falta los dos.",
            E["texto"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Servidor (una ventana de terminal)", E["h2"]),
        Paragraph(
            "cd backend<br/>"
            ".venv/Scripts/python -m uvicorn app.main:aplicacion --reload",
            E["codigo"],
        ),
        Spacer(1, 3 * mm),
        Paragraph("Interfaz (otra ventana)", E["h2"]),
        Paragraph("cd frontend<br/>npm run dev", E["codigo"]),
        Spacer(1, 4 * mm),
        tabla(
            ["Dirección", "Qué es"],
            [
                ["<b>http://localhost:5173</b>", "La aplicación. Es la que abres tú."],
                ["<b>http://localhost:8000/docs</b>",
                 "Documentación técnica del servidor, con todos sus endpoints. Útil solo "
                 "si vas a integrar otro programa."],
            ],
            [62 * mm, 124 * mm],
        ),
        Spacer(1, 5 * mm),
        aviso(
            "Si abres la interfaz sin el servidor",
            "No se rompe: muestra datos de ejemplo y avisa con un banner de que estás "
            "<b>sin conexión</b>. Los botones de guardar quedan deshabilitados, porque "
            "esos datos no existen en el servidor. La única excepción es Inicio y "
            "Reportes: ahí no se inventa nada, porque una cifra de ventas falsa no se "
            "distingue de una real de un vistazo.",
        ),
        Spacer(1, 5 * mm),
        Paragraph("9. Lo que todavía no hace", E["h1"]),
        tabla(
            ["Pendiente", "Qué significa para ti"],
            [
                ["<b>Certificado acreditado</b>",
                 "El sistema ya transmite al SRI y su ambiente de pruebas <b>acepta la "
                 "estructura</b> de los documentos. Lo único que falta para emitir con "
                 "validez legal es comprar un certificado .p12 a una entidad autorizada "
                 "y subirlo. No hace falta cambiar nada del programa."],
                ["<b>Envío por correo</b>",
                 "Hoy descargas el PDF y el XML y los envías tú. El envío automático al "
                 "cliente aún no está."],
                ["<b>Audio e imágenes en WhatsApp</b>",
                 "El asistente entiende texto. Notas de voz y fotos de facturas, todavía no."],
            ],
            [46 * mm, 140 * mm],
        ),
    ]

    documento.build(c, onFirstPage=pie_de_pagina, onLaterPages=pie_de_pagina)
    return ruta


if __name__ == "__main__":
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../docs/manual_de_uso.pdf")
    destino.parent.mkdir(parents=True, exist_ok=True)
    construir(destino)
    print(f"Manual generado en: {destino.resolve()}")
