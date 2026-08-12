"""
Catálogo de conceptos de retención.

FUENTES
-------
- **Impuesto a la renta:** Resolución **NAC-DGERCGC26-00000009** del 27 de
  febrero de 2026, aplicable **desde el 1 de marzo de 2026**. Deroga la
  NAC-DGERCGC24-00000008. Cada concepto cita abajo su artículo y numeral.
- **IVA:** Resolución NAC-DGERCGC20-00000061 y sus reformas. Los porcentajes
  (0, 10, 20, 30, 70 y 100 %) siguen vigentes.

QUÉ ESTÁ VERIFICADO Y QUÉ NO
----------------------------
El campo `verificado` distingue dos cosas muy distintas:

- `True`  — el **porcentaje** se contrastó contra el texto de la resolución
            citada en `base_legal`.
- `False` — el concepto es de uso común pero su porcentaje no se pudo
            confirmar contra una fuente oficial.

El **código numérico** (`codigo_retencion`) es harina de otro costal: no lo fija
la resolución sino la ficha técnica de comprobantes electrónicos del SRI, que se
publica aparte. Por eso hay conceptos con `codigo_retencion` vacío: existen y su
porcentaje está confirmado, pero su código no se pudo verificar y **inventarlo
sería peor que dejarlo en blanco**. En la interfaz el código es un campo de
texto editable, precargado cuando se conoce.

El API **no valida contra esta tabla**: acepta cualquier código y cualquier
porcentaje entre 0 y 100. Quien valida de verdad es el SRI al recibir el XML.
Una tabla desactualizada aquí no debe impedir emitir una retención correcta.

CAMBIOS DE LA RESOLUCIÓN DE 2026
--------------------------------
- Se **elimina la tarifa del 2,75 %** (con ella, el concepto 332).
- Se **incorpora la tarifa del 5 %** para servicios profesionales y comisiones
  de sociedades residentes.
- Desaparece el tramo del 8 %: el arrendamiento de inmuebles y los servicios
  donde prevalece el intelecto suben al 10 %.
- La retención residual (pagos sin porcentaje específico, art. 3) pasa
  de 2,75 % a **3 %**.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

RESOLUCION_RENTA = "NAC-DGERCGC26-00000009 (vigente desde 01/03/2026)"
RESOLUCION_IVA = "NAC-DGERCGC20-00000061 y reformas"

# Tabla 20 de la ficha técnica: impuesto sobre el que se retiene.
IMPUESTOS = {
    "1": "Impuesto a la renta",
    "2": "IVA",
    "6": "ISD",
}


@dataclass(frozen=True)
class Concepto:
    codigo: str  # Vacío si no se pudo verificar contra la ficha técnica.
    descripcion: str
    porcentaje: Decimal
    base_legal: str
    verificado: bool = True


# --------------------------------------------------------------------------
# Impuesto a la renta — Resolución NAC-DGERCGC26-00000009
# --------------------------------------------------------------------------

CONCEPTOS_RENTA: list[Concepto] = [
    # --- 0 % ---
    Concepto(
        "332",
        "Otras compras de bienes y servicios no sujetas a retención",
        Decimal("0"),
        "Art. 2 num. 1",
    ),
    Concepto(
        "344",
        "Pagos con tarjeta de crédito o débito (no sujetos a retención)",
        Decimal("0"),
        "Art. 6 lit. c",
    ),
    Concepto(
        "332",
        "RIMPE negocios populares (con comprobante preimpreso)",
        Decimal("0"),
        "Art. 2 num. 1 lit. c",
    ),
    # --- 1 % ---
    Concepto(
        "310",
        "Transporte privado de pasajeros o transporte público o privado de carga",
        Decimal("1"),
        "Art. 2 num. 2 lit. a",
    ),
    Concepto(
        "312A",
        "Bienes agrícolas, avícolas, pecuarios y similares en estado natural, al productor",
        Decimal("1"),
        "Art. 2 num. 2 lit. b",
    ),
    Concepto(
        "343",
        "Adquisiciones a contribuyentes RIMPE emprendedores",
        Decimal("1"),
        "Art. 2 num. 2 lit. c",
    ),
    # --- 1,75 % ---
    Concepto(
        "312C",
        "Bienes agrícolas y similares en estado natural, a comercializadores no productores",
        Decimal("1.75"),
        "Art. 2 num. 3 lit. a",
    ),
    # --- 2 % ---
    Concepto(
        "312",
        "Transferencia de bienes muebles de naturaleza corporal",
        Decimal("2"),
        "Art. 2 num. 4 lit. i",
    ),
    Concepto(
        "319",
        "Arrendamiento mercantil (cuotas, incluida la opción de compra)",
        Decimal("2"),
        "Art. 2 num. 4 lit. g",
    ),
    Concepto(
        "322",
        "Seguros y reaseguros: primas y cesión de primas",
        Decimal("2"),
        "Art. 2 num. 4 lit. c",
    ),
    Concepto("343A", "Energía eléctrica", Decimal("2"), "Art. 2 num. 4 lit. a"),
    Concepto(
        "343B",
        "Construcción de obra material inmueble, urbanización o lotización",
        Decimal("2"),
        "Art. 2 num. 4 lit. h",
    ),
    Concepto(
        "312B",
        "Adquisición de sustancias minerales dentro del territorio nacional",
        Decimal("2"),
        "Art. 2 num. 4 lit. f",
    ),
    # --- 3 % ---
    Concepto(
        "307",
        "Servicios de personas naturales donde prevalece la mano de obra",
        Decimal("3"),
        "Art. 2 num. 5 lit. a",
    ),
    Concepto(
        "309",
        "Medios de comunicación y agencias de publicidad",
        Decimal("3"),
        "Art. 2 num. 5 lit. c",
    ),
    Concepto(
        "323",
        "Rendimientos financieros (intereses, descuentos, pólizas, depósitos)",
        Decimal("3"),
        "Art. 2 num. 5 lit. d",
    ),
    Concepto(
        "323A",
        "Intereses y comisiones por ventas a crédito",
        Decimal("3"),
        "Art. 2 num. 5 lit. e",
    ),
    Concepto(
        "340",
        "Pagos sin un porcentaje específico de retención (regla general)",
        Decimal("3"),
        "Art. 3",
    ),
    # --- 5 % (tarifa nueva) ---
    Concepto(
        "303A",
        "Servicios profesionales prestados por sociedades residentes",
        Decimal("5"),
        "Art. 2 num. 6 lit. a",
    ),
    Concepto(
        "303B",
        "Comisiones pagadas a sociedades residentes",
        Decimal("5"),
        "Art. 2 num. 6 lit. b",
    ),
    # --- 10 % ---
    Concepto(
        "303",
        "Honorarios y comisiones a personas naturales donde prevalece el intelecto",
        Decimal("10"),
        "Art. 2 num. 7 lit. a",
    ),
    Concepto(
        "304",
        "Servicios donde prevalece el intelecto, sin título profesional relacionado",
        Decimal("10"),
        "Art. 2 num. 7 lit. a",
    ),
    Concepto(
        "308",
        "Utilización o aprovechamiento de la imagen o renombre",
        Decimal("10"),
        "Art. 2 num. 7 lit. b",
    ),
    Concepto(
        "320",
        "Arrendamiento de bienes inmuebles",
        Decimal("10"),
        "Art. 2 num. 7 lit. g",
    ),
    Concepto("304E", "Servicios de docencia", Decimal("10"), "Art. 2 num. 7 lit. c"),
    Concepto(
        "314A",
        "Cánones, regalías y derechos de propiedad intelectual",
        Decimal("10"),
        "Art. 2 num. 7 lit. e",
    ),
    Concepto(
        "304C",
        "Deportistas, entrenadores, árbitros y artistas sin relación de dependencia",
        Decimal("10"),
        "Art. 2 num. 7 lit. h",
    ),
]

# --------------------------------------------------------------------------
# IVA — Resolución NAC-DGERCGC20-00000061 y reformas
#
# Los porcentajes y códigos (versión 1.0.0 del XML de retención) están
# verificados según el catálogo ATS.
# --------------------------------------------------------------------------

CONCEPTOS_IVA: list[Concepto] = [
    Concepto("721", "Retención 0 % de IVA", Decimal("0"), RESOLUCION_IVA, verificado=True),
    Concepto("723", "Retención 10 % de IVA", Decimal("10"), RESOLUCION_IVA, verificado=True),
    Concepto("725", "Retención 20 % de IVA", Decimal("20"), RESOLUCION_IVA, verificado=True),
    Concepto(
        "727",
        "Retención 30 % de IVA — transferencia de bienes",
        Decimal("30"),
        RESOLUCION_IVA,
        verificado=True,
    ),
    Concepto(
        "729",
        "Retención 70 % de IVA — servicios, comisiones y consultoría",
        Decimal("70"),
        RESOLUCION_IVA,
        verificado=True,
    ),
    Concepto(
        "731",
        "Retención 100 % de IVA — profesionales, arrendamiento a PN, dietas",
        Decimal("100"),
        RESOLUCION_IVA,
        verificado=True,
    ),
]

# --------------------------------------------------------------------------
# ISD
# --------------------------------------------------------------------------

CONCEPTOS_ISD: list[Concepto] = [
    Concepto(
        "4580",
        "Impuesto a la salida de divisas",
        Decimal("5"),
        "Ley Reformatoria para la Equidad Tributaria",
        verificado=False,
    ),
]

POR_IMPUESTO: dict[str, list[Concepto]] = {
    "1": CONCEPTOS_RENTA,
    "2": CONCEPTOS_IVA,
    "6": CONCEPTOS_ISD,
}


def catalogo() -> list[dict]:
    """Aplana las tablas en algo que la interfaz pueda pintar directamente."""
    filas = []
    for codigo_impuesto, conceptos in POR_IMPUESTO.items():
        for indice, concepto in enumerate(conceptos):
            filas.append(
                {
                    # Identificador estable para el desplegable: el código no
                    # sirve porque muchos conceptos no tienen uno.
                    "id": f"{codigo_impuesto}-{indice}",
                    "codigo_impuesto": codigo_impuesto,
                    "impuesto": IMPUESTOS[codigo_impuesto],
                    "codigo_retencion": concepto.codigo,
                    "descripcion": concepto.descripcion,
                    "porcentaje": str(concepto.porcentaje),
                    "base_legal": concepto.base_legal,
                    "verificado": concepto.verificado,
                }
            )
    return filas


def porcentaje_sugerido(codigo_impuesto: str, codigo_retencion: str) -> Decimal | None:
    """
    Porcentaje del concepto según su código, o None si no está en el catálogo.

    Solo encuentra conceptos con código conocido; los que lo tienen vacío se
    seleccionan por `id` desde la interfaz, no por código.
    """
    if not codigo_retencion:
        return None
    for concepto in POR_IMPUESTO.get(codigo_impuesto, []):
        if concepto.codigo == codigo_retencion:
            return concepto.porcentaje
    return None
