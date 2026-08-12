"""
Paleta y estilos ReportLab compartidos por todo lo que este sistema imprime.

Vivían dentro de `ride.py`, pero el RIDE dejó de ser el único PDF: los reportes
de gestión también se exportan. Duplicar allí los colores y los estilos habría
garantizado que, al primer retoque de marca, el RIDE y los reportes salieran de
dos empresas distintas. Aquí hay una sola definición y ambos la importan.

La salida del RIDE no cambia: `estilos()` y `marco()` son literalmente las
funciones que estaban en `ride.py`, movidas de sitio.
"""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import TableStyle

GRIS_BORDE = colors.HexColor("#c8cdd8")
GRIS_FONDO = colors.HexColor("#eef1f6")
NARANJA = colors.HexColor("#d95f00")
TEXTO = colors.HexColor("#101423")
TEXTO_SUAVE = colors.HexColor("#4a5568")


def estilos() -> dict[str, ParagraphStyle]:
    """
    Estilos de párrafo del documento.

    Se construye uno nuevo en cada llamada y no un diccionario de módulo porque
    ReportLab muta los `ParagraphStyle` al maquetar; compartir la instancia
    entre dos documentos generados a la vez los contaminaría entre sí.
    """
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "titulo", parent=base["Heading1"], fontSize=14, textColor=TEXTO, spaceAfter=2
        ),
        "normal": ParagraphStyle(
            "normal", parent=base["Normal"], fontSize=8, textColor=TEXTO, leading=11
        ),
        "suave": ParagraphStyle(
            "suave", parent=base["Normal"], fontSize=7.5, textColor=TEXTO_SUAVE, leading=10
        ),
        "clave": ParagraphStyle(
            "clave",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=7.5,
            textColor=TEXTO,
            leading=10,
        ),
        "etiqueta": ParagraphStyle(
            "etiqueta",
            parent=base["Normal"],
            fontSize=7,
            textColor=TEXTO_SUAVE,
            leading=9,
        ),
    }


def marco(relleno: int = 6) -> TableStyle:
    """Recuadro con relleno uniforme, para los bloques de cabecera."""
    return TableStyle(
        [
            ("BOX", (0, 0), (-1, -1), 0.6, GRIS_BORDE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), relleno),
            ("RIGHTPADDING", (0, 0), (-1, -1), relleno),
            ("TOPPADDING", (0, 0), (-1, -1), relleno),
            ("BOTTOMPADDING", (0, 0), (-1, -1), relleno),
        ]
    )
