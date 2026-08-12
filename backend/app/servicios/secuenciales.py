"""
Reserva de secuenciales por punto de emisión y tipo de documento.

Un secuencial repetido hace que el SRI rechace el comprobante, así que la
reserva se hace con bloqueo dentro de la transacción del llamador: si dos
peticiones llegan a la vez, la segunda espera y obtiene el siguiente número.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Establecimiento, PuntoEmision, SecuencialDocumento

# Tipos que llevan numeración propia ante el SRI.
TIPOS_DOCUMENTO = (
    "Factura",
    "Nota de Crédito",
    "Nota de Débito",
    "Liquidación de Compra",
    "Nota de Venta",
    "Guía de Remisión",
    "Retención",
    "Cotización",
)


def buscar_punto_emision(
    sesion: Session, empresa_id: int, establecimiento: str, punto_emision: str
) -> PuntoEmision:
    punto = sesion.scalar(
        select(PuntoEmision)
        .join(Establecimiento)
        .where(
            Establecimiento.empresa_id == empresa_id,
            Establecimiento.codigo == establecimiento,
            PuntoEmision.codigo == punto_emision,
        )
        .with_for_update()
    )

    if punto is None:
        raise HTTPException(
            404, f"No existe el punto de emisión {establecimiento}-{punto_emision}."
        )
    return punto


def reservar_secuencial(sesion: Session, punto: PuntoEmision, tipo: str) -> int:
    """
    Devuelve el número a usar y avanza el contador.

    La primera vez que se emite un tipo en un punto se crea su contador. Para
    facturas arranca en el valor que el usuario configuró; el resto empieza en 1.
    """
    if tipo not in TIPOS_DOCUMENTO:
        raise HTTPException(422, f"Tipo de documento no soportado: {tipo}")

    contador = sesion.scalar(
        select(SecuencialDocumento)
        .where(
            SecuencialDocumento.punto_emision_id == punto.id,
            SecuencialDocumento.tipo == tipo,
        )
        .with_for_update()
    )

    if contador is None:
        inicial = punto.secuencial_factura if tipo == "Factura" else 1
        contador = SecuencialDocumento(
            punto_emision_id=punto.id, tipo=tipo, siguiente=max(inicial, 1)
        )
        sesion.add(contador)
        sesion.flush()

    numero = contador.siguiente
    contador.siguiente = numero + 1

    # Se mantiene sincronizado para que Configuraciones muestre el próximo real.
    if tipo == "Factura":
        punto.secuencial_factura = contador.siguiente

    return numero


def formatear_numero(establecimiento: str, punto_emision: str, secuencial: int) -> str:
    """Número legible del comprobante, p. ej. 001-002-000000135."""
    return f"{establecimiento}-{punto_emision}-{str(secuencial).zfill(9)}"
