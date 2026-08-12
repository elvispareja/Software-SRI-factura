"""
Exportación de reportes a PDF.

Hay un único generador para los doce reportes en vez de uno por reporte. La
razón es que un reporte, visto desde la impresora, siempre es lo mismo: una
cabecera con el emisor y el período, una tabla con cabeceras, filas y quizá una
línea de totales, y un pie. Escribir doce generadores casi idénticos garantiza
que dentro de seis meses nueve tengan el pie viejo y tres el nuevo.

Lo que cada reporte sí aporta es *qué* filas contiene, y eso se arma en
`routers/reportes.py`, compartido con la exportación a CSV para que ambos
formatos no se separen.
"""

from __future__ import annotations

import io
from datetime import date, datetime
from decimal import Decimal

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from ..sri.estilos_pdf import GRIS_BORDE, GRIS_FONDO, NARANJA, TEXTO_SUAVE, estilos, marco

# A partir de esta cantidad de columnas el A4 vertical obliga a partir palabras
# en cada celda; la hoja apaisada es más legible que una tabla ilegible.
COLUMNAS_PARA_APAISAR = 7

# Ancho mínimo de columna: por debajo de esto una fecha o un importe se parte.
ANCHO_MINIMO_MM = 14

# Cuántas filas se miden para repartir el ancho de las columnas. Un inventario
# de diez mil artículos no necesita medirse entero: las primeras filas ya dicen
# si una columna lleva códigos cortos o descripciones largas.
FILAS_MUESTREADAS = 300

# Tope de peso de una columna al repartir el ancho. Sin él, una sola
# descripción larguísima se lleva la hoja entera y deja el resto en un hilo.
PESO_MAXIMO = 45


def _texto(valor) -> str:
    """
    Convierte a texto un valor de celda.

    El dinero llega en `Decimal` y debe imprimirse con dos decimales: mostrar
    `1E+2` o `12.500000` en un reporte que alguien va a leer en papel es un
    error de presentación aunque el número sea exacto.
    """
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if isinstance(valor, Decimal):
        return f"{valor:.2f}"
    if isinstance(valor, float):
        return f"{valor:.2f}"
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


ALINEACIONES = {"D": TA_RIGHT, "C": TA_CENTER, "I": TA_LEFT}


def _alinear(base: ParagraphStyle, lado: str) -> ParagraphStyle:
    """
    Clona un estilo cambiándole la alineación.

    Hace falta clonar y no basta con la orden `ALIGN` de la tabla: `ALIGN`
    coloca el párrafo dentro de la celda, pero el párrafo ocupa la celda
    entera, así que el texto se queda pegado a la izquierda igualmente. Quien
    alinea el texto es el propio `ParagraphStyle`.
    """
    return ParagraphStyle(
        f"{base.name}-{lado}", parent=base, alignment=ALINEACIONES.get(lado, TA_LEFT)
    )


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float, Decimal)) and not isinstance(valor, bool)


def _alineacion_automatica(cabeceras: list[str], filas: list[list]) -> list[str]:
    """
    Deduce qué columnas van a la derecha.

    Una columna se alinea a la derecha si todo lo que contiene son números: es
    la única forma de que las unidades queden bajo las unidades y la columna se
    pueda sumar de un vistazo.
    """
    alineacion = []
    for indice in range(len(cabeceras)):
        valores = [
            fila[indice]
            for fila in filas[:FILAS_MUESTREADAS]
            if indice < len(fila) and fila[indice] not in (None, "")
        ]
        numerica = bool(valores) and all(_es_numero(valor) for valor in valores)
        alineacion.append("D" if numerica else "I")
    return alineacion


def _anchos(cabeceras: list[str], filas: list[list], ancho_disponible: float,
            tamano_letra: float) -> list[float]:
    """Reparte el ancho de la hoja entre las columnas según lo que contienen."""
    pesos = []
    for indice, cabecera in enumerate(cabeceras):
        ancho_texto = stringWidth(_texto(cabecera), "Helvetica-Bold", tamano_letra)
        for fila in filas[:FILAS_MUESTREADAS]:
            if indice < len(fila):
                ancho_texto = max(
                    ancho_texto, stringWidth(_texto(fila[indice]), "Helvetica", tamano_letra)
                )
        # En puntos por carácter aproximado; el tope evita que una descripción
        # larga se coma la hoja.
        pesos.append(min(ancho_texto / tamano_letra, PESO_MAXIMO) + 1)

    minimo = ANCHO_MINIMO_MM * mm
    holgura = ancho_disponible - minimo * len(pesos)
    if holgura <= 0:
        return [ancho_disponible / len(pesos)] * len(pesos)

    total = sum(pesos)
    return [minimo + holgura * peso / total for peso in pesos]


def _cabecera_empresa(empresa, estilo) -> list:
    """
    Bloque con los datos del emisor.

    Si la empresa no está configurada devuelve una lista vacía en lugar de
    fallar: un reporte de gestión no se transmite al SRI, así que negarle la
    descarga a quien todavía no ha llenado sus datos es estorbar sin motivo.
    """
    if empresa is None:
        return []

    lineas = [Paragraph(f"<b>{empresa.razon_social}</b>", estilo["titulo"])]
    if getattr(empresa, "nombre_comercial", None):
        lineas.append(Paragraph(empresa.nombre_comercial, estilo["suave"]))
    lineas.append(Paragraph(f"<b>RUC:</b> {empresa.ruc}", estilo["normal"]))
    if getattr(empresa, "direccion_matriz", None):
        lineas.append(Paragraph(empresa.direccion_matriz, estilo["suave"]))
    if getattr(empresa, "regimen", None):
        lineas.append(Paragraph(empresa.regimen, estilo["suave"]))
    return lineas


def _lienzo_paginado(pie_izquierdo: str):
    """
    Fabrica el lienzo que numera las páginas.

    "Página 1 de 7" no se puede escribir mientras se dibuja la página 1: en ese
    momento ReportLab todavía no sabe cuántas habrá. La solución es guardar el
    estado de cada página y pintar el pie en una segunda pasada, al guardar,
    cuando el total ya es conocido.
    """

    class LienzoPaginado(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._paginas: list[dict] = []

        def showPage(self):  # noqa: N802  (lo define ReportLab)
            self._paginas.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._paginas)
            for estado in self._paginas:
                self.__dict__.update(estado)
                self._pie(total)
                super().showPage()
            super().save()

        def _pie(self, total: int) -> None:
            ancho, _ = self._pagesize
            self.setFont("Helvetica", 7)
            self.setFillColor(TEXTO_SUAVE)
            self.setStrokeColor(GRIS_BORDE)
            self.setLineWidth(0.4)
            self.line(12 * mm, 13 * mm, ancho - 12 * mm, 13 * mm)
            if pie_izquierdo:
                self.drawString(12 * mm, 9 * mm, pie_izquierdo)
            self.drawRightString(
                ancho - 12 * mm, 9 * mm, f"Página {self._pageNumber} de {total}"
            )

    return LienzoPaginado


def generar_pdf_reporte(
    *,
    empresa,
    titulo: str,
    subtitulo: str,
    cabeceras: list[str],
    filas: list[list],
    totales: list | None = None,
    alineacion: list[str] | None = None,
    nota: str | None = None,
) -> bytes:
    """
    Devuelve el PDF de un reporte tabular.

    `empresa` puede ser `None`. `alineacion` es una letra por columna —"I"
    izquierda, "D" derecha, "C" centro—; si no se indica, se deduce de los
    datos. `totales` es la fila destacada del pie de la tabla.
    """
    estilo = estilos()
    apaisada = len(cabeceras) >= COLUMNAS_PARA_APAISAR
    tamano_pagina = landscape(A4) if apaisada else A4
    tamano_letra = 7 if apaisada else 8

    buffer = io.BytesIO()
    documento = SimpleDocTemplate(
        buffer,
        pagesize=tamano_pagina,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        # Deja sitio para el pie, que se dibuja fuera del marco de contenido.
        bottomMargin=18 * mm,
        title=titulo,
        author=(empresa.razon_social if empresa is not None else "SRI"),
    )

    bloque_titulo = [
        Paragraph(f"<b>{titulo}</b>", estilo["titulo"]),
        Paragraph(subtitulo, estilo["suave"]),
        Paragraph(f"Generado el {date.today():%d/%m/%Y}", estilo["etiqueta"]),
    ]

    datos_empresa = _cabecera_empresa(empresa, estilo)
    mitad = documento.width / 2

    if datos_empresa:
        cabecera = Table(
            [[datos_empresa, bloque_titulo]],
            colWidths=[mitad, mitad],
            style=marco(),
        )
    else:
        cabecera = Table([[bloque_titulo]], colWidths=[documento.width], style=marco())

    elementos = [cabecera, Spacer(1, 5 * mm)]

    if alineacion is None:
        alineacion = _alineacion_automatica(cabeceras, filas)

    # Una tabla sin filas es un dato en sí mismo: se dice, no se deja en blanco.
    cuerpo = filas or [["Sin datos en el período."] + [""] * (len(cabeceras) - 1)]

    # Un estilo por columna, ya alineado: es la única forma de que los importes
    # queden a la derecha (ver `_alinear`).
    lados = [alineacion[i] if i < len(alineacion) else "I" for i in range(len(cabeceras))]
    estilo_celda = estilo["suave"] if apaisada else estilo["normal"]
    columnas = [_alinear(estilo_celda, lado) for lado in lados]
    titulares = [_alinear(estilo["etiqueta"], lado) for lado in lados]

    def _fila(valores, estilos_columna, negrita=False):
        return [
            Paragraph(
                f"<b>{_texto(valor)}</b>" if negrita else _texto(valor),
                estilos_columna[indice] if indice < len(estilos_columna) else estilo_celda,
            )
            for indice, valor in enumerate(valores)
        ]

    datos = [_fila(cabeceras, titulares, negrita=True)]
    for fila in cuerpo:
        datos.append(_fila(fila, columnas))
    if totales:
        datos.append(_fila(totales, columnas, negrita=True))

    anchos = _anchos(cabeceras, cuerpo, documento.width, tamano_letra)

    ordenes = [
        ("BACKGROUND", (0, 0), (-1, 0), GRIS_FONDO),
        ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for indice, lado in enumerate(alineacion[: len(cabeceras)]):
        ordenes.append(
            ("ALIGN", (indice, 0), (indice, -1), {"D": "RIGHT", "C": "CENTER"}.get(lado, "LEFT"))
        )
    if totales:
        ordenes += [
            ("BACKGROUND", (0, -1), (-1, -1), GRIS_FONDO),
            ("TEXTCOLOR", (0, -1), (-1, -1), NARANJA),
        ]

    # LongTable y no Table: el inventario y los receptores pueden traer miles de
    # filas, y `Table` maqueta todo el bloque de una vez. `repeatRows=1` repite
    # la cabecera en cada página, sin lo cual la página 4 es una lista de
    # números sin nombre.
    tabla = LongTable(datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle(ordenes))
    elementos.append(tabla)

    if nota:
        elementos += [Spacer(1, 4 * mm), Paragraph(nota, estilo["suave"])]

    pie = f"{empresa.razon_social} — RUC {empresa.ruc}" if empresa is not None else titulo
    documento.build(elementos, canvasmaker=_lienzo_paginado(pie))

    return buffer.getvalue()
