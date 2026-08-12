"""Modelos de dominio de un comprobante electrónico."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

# El SRI valida que los totales cuadren al centavo: todo el dinero se maneja en
# Decimal y se redondea a 2 con "half up", nunca con float.
CENTAVO = Decimal("0.01")


def redondear(valor: Decimal | float | str, decimales: int = 2) -> Decimal:
    cuantia = Decimal(1).scaleb(-decimales)
    return Decimal(str(valor)).quantize(cuantia, rounding=ROUND_HALF_UP)


# Tabla 17 de la ficha técnica: códigos de porcentaje del IVA (impuesto 2).
PORCENTAJES_IVA = {
    "0": Decimal("0"),
    "2": Decimal("12"),
    "3": Decimal("14"),
    "4": Decimal("15"),
    "5": Decimal("5"),
    "6": Decimal("0"),  # No objeto de impuesto
    "7": Decimal("0"),  # Exento
}

CODIGO_IMPUESTO_IVA = "2"


@dataclass
class Emisor:
    ruc: str
    razon_social: str
    nombre_comercial: str
    direccion_matriz: str
    direccion_establecimiento: str
    establecimiento: str
    punto_emision: str
    obligado_contabilidad: bool = True
    contribuyente_especial: str | None = None
    agente_retencion: str | None = None
    contribuyente_rimpe: str | None = None


@dataclass
class Comprador:
    tipo_identificacion: str  # 04 RUC, 05 cédula, 06 pasaporte, 07 consumidor final
    identificacion: str
    razon_social: str
    direccion: str
    correo: str | None = None
    telefono: str | None = None


@dataclass
class Detalle:
    codigo_principal: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    codigo_iva: str = "4"
    descuento_porcentaje: Decimal = Decimal("0")
    codigo_auxiliar: str | None = None

    @property
    def bruto(self) -> Decimal:
        return redondear(self.cantidad * self.precio_unitario)

    @property
    def descuento(self) -> Decimal:
        return redondear(self.bruto * self.descuento_porcentaje / Decimal("100"))

    @property
    def base_imponible(self) -> Decimal:
        """`precioTotalSinImpuesto` del XML."""
        return redondear(self.bruto - self.descuento)

    @property
    def tarifa(self) -> Decimal:
        return PORCENTAJES_IVA[self.codigo_iva]

    @property
    def valor_iva(self) -> Decimal:
        return redondear(self.base_imponible * self.tarifa / Decimal("100"))


@dataclass
class Pago:
    forma_pago: str = "01"  # 01 = sin utilización del sistema financiero
    total: Decimal = Decimal("0")
    plazo: int | None = None
    unidad_tiempo: str | None = None


@dataclass
class Factura:
    emisor: Emisor
    comprador: Comprador
    fecha_emision: date
    detalles: list[Detalle]
    secuencial: int
    ambiente: str = "1"
    tipo_emision: str = "1"
    moneda: str = "DOLAR"
    pagos: list[Pago] = field(default_factory=list)
    info_adicional: dict[str, str] = field(default_factory=dict)

    @property
    def total_sin_impuestos(self) -> Decimal:
        return redondear(sum((d.base_imponible for d in self.detalles), Decimal("0")))

    @property
    def total_descuento(self) -> Decimal:
        return redondear(sum((d.descuento for d in self.detalles), Decimal("0")))

    def impuestos_agrupados(self) -> list[dict[str, Decimal | str]]:
        """Agrupa por código de porcentaje: es lo que va en `totalConImpuestos`."""
        grupos: dict[str, dict[str, Decimal | str]] = {}

        for detalle in self.detalles:
            grupo = grupos.setdefault(
                detalle.codigo_iva,
                {
                    "codigo": CODIGO_IMPUESTO_IVA,
                    "codigo_porcentaje": detalle.codigo_iva,
                    "base_imponible": Decimal("0"),
                    "valor": Decimal("0"),
                    "tarifa": detalle.tarifa,
                },
            )
            grupo["base_imponible"] = redondear(grupo["base_imponible"] + detalle.base_imponible)
            grupo["valor"] = redondear(grupo["valor"] + detalle.valor_iva)

        # Orden estable por código, para que el XML sea reproducible.
        return [grupos[codigo] for codigo in sorted(grupos)]

    @property
    def total_iva(self) -> Decimal:
        return redondear(sum((g["valor"] for g in self.impuestos_agrupados()), Decimal("0")))

    @property
    def importe_total(self) -> Decimal:
        return redondear(self.total_sin_impuestos + self.total_iva)
