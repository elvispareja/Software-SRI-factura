"""
Endpoints de anticipos.

Un anticipo es dinero que se movió antes de que exista la factura. Mientras no
se factura, es un pasivo: el cliente pagó algo que todavía no se le entregó.

`saldo` nunca se guarda, se calcula como `monto - facturado`. Un tercer número
almacenado es un número que puede dejar de cuadrar con los otros dos.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..base_datos import obtener_sesion
from ..esquemas import AnticipoEntrada, AnticipoSalida, AplicarAnticipo
from ..modelos_db import Anticipo, Receptor
from ..sri.modelos import redondear

router = APIRouter(prefix="/anticipos", tags=["anticipos"])

# Estados posibles. "Pendiente" y "Parcial" siguen teniendo saldo disponible.
ESTADOS_CON_SALDO = ("Pendiente", "Parcial")


def _recalcular_estado(anticipo: Anticipo) -> None:
    if anticipo.estado == "Anulado":
        return
    if anticipo.facturado <= 0:
        anticipo.estado = "Pendiente"
    elif anticipo.facturado >= anticipo.monto:
        anticipo.estado = "Aplicado"
    else:
        anticipo.estado = "Parcial"


@router.get("", response_model=list[AnticipoSalida])
def listar(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Anticipo)

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Anticipo.receptor_razon_social).like(patron),
                func.lower(Anticipo.detalle).like(patron),
            )
        )
    if tipo:
        consulta = consulta.where(Anticipo.tipo == tipo)
    if estado:
        consulta = consulta.where(Anticipo.estado == estado)
    if desde:
        consulta = consulta.where(Anticipo.fecha >= desde)
    if hasta:
        consulta = consulta.where(Anticipo.fecha <= hasta)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Anticipo.fecha.desc(), Anticipo.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.post("", response_model=AnticipoSalida, status_code=201)
def crear(datos: AnticipoEntrada, sesion: Session = Depends(obtener_sesion)):
    receptor = sesion.get(Receptor, datos.receptor_id)
    if receptor is None:
        raise HTTPException(404, "El receptor indicado no existe.")

    anticipo = Anticipo(
        fecha=datos.fecha or date.today(),
        tipo=datos.tipo,
        receptor_id=receptor.id,
        # Se copia el nombre: si el receptor se desactiva, el histórico sigue
        # diciendo de quién era el anticipo.
        receptor_razon_social=receptor.razon_social,
        detalle=datos.detalle,
        monto=datos.monto,
        forma_pago=datos.forma_pago,
        estado="Pendiente",
    )

    sesion.add(anticipo)
    sesion.commit()
    sesion.refresh(anticipo)
    return anticipo


@router.get("/{anticipo_id}", response_model=AnticipoSalida)
def obtener(anticipo_id: int, sesion: Session = Depends(obtener_sesion)):
    anticipo = sesion.get(Anticipo, anticipo_id)
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    return anticipo


@router.post("/{anticipo_id}/aplicar", response_model=AnticipoSalida)
def aplicar(
    anticipo_id: int, datos: AplicarAnticipo, sesion: Session = Depends(obtener_sesion)
):
    """
    Imputa parte del anticipo a una factura.

    No se puede aplicar más de lo que queda: el saldo llegaría a negativo y el
    anticipo pasaría a deber dinero, que no significa nada.
    """
    anticipo = sesion.get(Anticipo, anticipo_id)
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    if anticipo.estado == "Anulado":
        raise HTTPException(409, "Este anticipo está anulado.")

    disponible = anticipo.monto - anticipo.facturado
    if datos.monto > disponible:
        raise HTTPException(
            422,
            f"El anticipo solo tiene ${disponible:.2f} disponibles y se intentó "
            f"aplicar ${datos.monto:.2f}.",
        )

    anticipo.facturado = redondear(anticipo.facturado + datos.monto)
    _recalcular_estado(anticipo)

    sesion.commit()
    sesion.refresh(anticipo)
    return anticipo


@router.post("/{anticipo_id}/anular", response_model=AnticipoSalida)
def anular(anticipo_id: int, sesion: Session = Depends(obtener_sesion)):
    anticipo = sesion.get(Anticipo, anticipo_id)
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")

    # Anular uno ya imputado dejaría facturas apoyadas en dinero inexistente.
    if anticipo.facturado > 0:
        raise HTTPException(
            409,
            "Este anticipo ya se aplicó a facturas. Emite una nota de crédito "
            "en vez de anularlo.",
        )

    anticipo.estado = "Anulado"
    sesion.commit()
    sesion.refresh(anticipo)
    return anticipo


@router.delete("/{anticipo_id}", status_code=204)
def eliminar(anticipo_id: int, sesion: Session = Depends(obtener_sesion)):
    anticipo = sesion.get(Anticipo, anticipo_id)
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    if anticipo.facturado > 0:
        raise HTTPException(409, "No se puede borrar un anticipo ya aplicado.")

    sesion.delete(anticipo)
    sesion.commit()
