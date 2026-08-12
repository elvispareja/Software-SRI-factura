"""
Facturación recurrente: arriendos, suscripciones, igualas mensuales.

Lo que se guarda es la **plantilla**, no las facturas. Al emitir se crea un
`Comprobante` normal y corriente, porque una factura recurrente autorizada es
una factura como cualquier otra ante el SRI: mismo XML, misma numeración, misma
firma. Aquí no hay ningún atajo.

La emisión **no es automática**. El sistema calcula qué plantillas tocan y las
deja listas, pero la orden la da una persona. Una factura emitida sola contra
un cliente que ya canceló el servicio es un documento que hay que anular con
nota de crédito, y eso cuesta más que pulsar un botón cada mes.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Comprobante, DetalleComprobante, Empresa, PlantillaRecurrente
from ..sri.modelos import Detalle, redondear
from .secuenciales import buscar_punto_emision, formatear_numero, reservar_secuencial

PERIODICIDADES = ("Semanal", "Quincenal", "Mensual", "Bimestral", "Trimestral", "Anual")

_DIAS = {"Semanal": 7, "Quincenal": 15}
_MESES = {"Mensual": 1, "Bimestral": 2, "Trimestral": 3, "Anual": 12}


class ErrorRecurrente(Exception):
    """El mensaje es apto para mostrárselo al usuario."""


def sumar_meses(desde: date, meses: int) -> date:
    """
    Avanza `meses` conservando el día cuando existe.

    El 31 de enero más un mes es el 28 de febrero, no el 3 de marzo: una
    suscripción que se cobra a fin de mes debe seguir cobrándose a fin de mes.
    """
    total = desde.month - 1 + meses
    anio = desde.year + total // 12
    mes = total % 12 + 1
    dia = min(desde.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def siguiente_fecha(desde: date, periodicidad: str) -> date:
    if periodicidad in _DIAS:
        return desde + timedelta(days=_DIAS[periodicidad])
    if periodicidad in _MESES:
        return sumar_meses(desde, _MESES[periodicidad])
    raise ErrorRecurrente(f"Periodicidad desconocida: {periodicidad}")


def total_de(plantilla: PlantillaRecurrente) -> Decimal:
    """Importe de la plantilla, calculado con el motor y no a mano."""
    lineas = [
        Detalle(
            codigo_principal=linea.codigo_principal,
            descripcion=linea.descripcion,
            cantidad=linea.cantidad,
            precio_unitario=linea.precio_unitario,
            codigo_iva=linea.codigo_iva,
            descuento_porcentaje=linea.descuento_porcentaje,
        )
        for linea in plantilla.lineas
    ]
    return redondear(
        sum((linea.base_imponible + linea.valor_iva for linea in lineas), Decimal("0"))
    )


def vencidas(sesion: Session, hasta: date) -> list[PlantillaRecurrente]:
    """Plantillas activas cuya próxima emisión ya llegó."""
    return list(
        sesion.scalars(
            select(PlantillaRecurrente)
            .where(
                PlantillaRecurrente.activa.is_(True),
                PlantillaRecurrente.proxima_emision <= hasta,
            )
            .order_by(PlantillaRecurrente.proxima_emision)
        ).all()
    )


def emitir_desde_plantilla(
    sesion: Session, plantilla: PlantillaRecurrente, hoy: date | None = None
) -> Comprobante:
    """
    Crea el comprobante en borrador y adelanta la plantilla.

    Devuelve el comprobante **sin transmitir**: quien llama decide si lo manda
    al SRI. Así el usuario puede revisarlo antes, que es lo que hace falta
    cuando el importe cambió o el cliente se dio de baja.
    """
    hoy = hoy or date.today()

    if not plantilla.activa:
        raise ErrorRecurrente(f"La plantilla «{plantilla.nombre}» está desactivada.")
    if plantilla.receptor is None:
        raise ErrorRecurrente(
            f"La plantilla «{plantilla.nombre}» no tiene cliente: fue eliminado."
        )
    if not plantilla.receptor.direccion:
        raise ErrorRecurrente(
            f"{plantilla.receptor.razon_social} no tiene dirección, y el SRI la exige."
        )
    if plantilla.hasta and plantilla.proxima_emision > plantilla.hasta:
        raise ErrorRecurrente(
            f"La plantilla «{plantilla.nombre}» terminó el "
            f"{plantilla.hasta:%d/%m/%Y}."
        )

    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorRecurrente("No hay empresa configurada.")

    punto = buscar_punto_emision(
        sesion, empresa.id, plantilla.establecimiento, plantilla.punto_emision
    )
    secuencial = reservar_secuencial(sesion, punto, "Factura")

    comprobante = Comprobante(
        tipo="Factura",
        numero=formatear_numero(plantilla.establecimiento, plantilla.punto_emision, secuencial),
        establecimiento=plantilla.establecimiento,
        punto_emision=plantilla.punto_emision,
        secuencial=secuencial,
        fecha_emision=plantilla.proxima_emision,
        receptor_id=plantilla.receptor_id,
        receptor_razon_social=plantilla.receptor.razon_social,
        receptor_identificacion=plantilla.receptor.identificacion,
        forma_pago=plantilla.forma_pago,
        estado_sri="Borrador",
    )

    total_sin_impuestos = Decimal("0")
    total_descuento = Decimal("0")
    total_iva = Decimal("0")

    for origen in plantilla.lineas:
        linea = Detalle(
            codigo_principal=origen.codigo_principal,
            descripcion=origen.descripcion,
            cantidad=origen.cantidad,
            precio_unitario=origen.precio_unitario,
            codigo_iva=origen.codigo_iva,
            descuento_porcentaje=origen.descuento_porcentaje,
        )
        comprobante.detalles.append(
            DetalleComprobante(
                codigo_principal=linea.codigo_principal,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                descuento_porcentaje=linea.descuento_porcentaje,
                descuento=linea.descuento,
                codigo_iva=linea.codigo_iva,
                base_imponible=linea.base_imponible,
                valor_iva=linea.valor_iva,
                total=linea.base_imponible + linea.valor_iva,
            )
        )
        total_sin_impuestos += linea.base_imponible
        total_descuento += linea.descuento
        total_iva += linea.valor_iva

    comprobante.total_sin_impuestos = redondear(total_sin_impuestos)
    comprobante.total_descuento = redondear(total_descuento)
    comprobante.total_iva = redondear(total_iva)
    comprobante.importe_total = redondear(total_sin_impuestos + total_iva)

    sesion.add(comprobante)

    # La plantilla avanza aunque el comprobante siga en borrador: si no, el
    # siguiente ciclo volvería a proponer el mismo período.
    plantilla.ultima_emision = plantilla.proxima_emision
    plantilla.proxima_emision = siguiente_fecha(
        plantilla.proxima_emision, plantilla.periodicidad
    )
    plantilla.emitidas += 1
    plantilla.total = comprobante.importe_total

    # Una plantilla que pasó su fecha de fin se apaga sola.
    if plantilla.hasta and plantilla.proxima_emision > plantilla.hasta:
        plantilla.activa = False

    sesion.flush()
    return comprobante
