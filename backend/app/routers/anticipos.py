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
from ..esquemas import (
    AnticipoEntrada,
    AnticipoSalida,
    AplicarAnticipo,
    DevolucionAnticipoSalida,
    DevolverAnticipo,
)
from ..modelos_db import Anticipo, DevolucionAnticipo, Receptor
from ..sri.modelos import redondear

router = APIRouter(prefix="/anticipos", tags=["anticipos"])

# Estados posibles. "Pendiente" y "Parcial" siguen teniendo saldo disponible.
ESTADOS_CON_SALDO = ("Pendiente", "Parcial")


def _recalcular_estado(anticipo: Anticipo) -> None:
    # Anulado y Devuelto son estados finales: no vuelven a recalcularse a partir
    # de lo facturado, porque ya no representan saldo disponible.
    if anticipo.estado in ("Anulado", "Devuelto"):
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

    La lectura es **bloqueante** (`with_for_update`): serializa la carrera entre
    aplicar y devolver, que sin el bloqueo podrían leer el mismo saldo y gastarlo
    dos veces. No se puede aplicar más de lo que queda —el saldo llegaría a
    negativo— ni tocar un anticipo anulado o ya devuelto.
    """
    anticipo = sesion.scalar(
        select(Anticipo).where(Anticipo.id == anticipo_id).with_for_update()
    )
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    if anticipo.estado == "Anulado":
        raise HTTPException(409, "Este anticipo está anulado.")
    if anticipo.estado == "Devuelto":
        raise HTTPException(409, "Este anticipo ya se devolvió.")

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
    if anticipo.estado == "Devuelto":
        raise HTTPException(409, "Este anticipo ya se devolvió.")

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
    if anticipo.estado == "Devuelto":
        raise HTTPException(409, "No se puede borrar un anticipo devuelto.")
    if anticipo.facturado > 0:
        raise HTTPException(409, "No se puede borrar un anticipo ya aplicado.")

    sesion.delete(anticipo)
    sesion.commit()


@router.put("/{anticipo_id}", response_model=AnticipoSalida)
def corregir(
    anticipo_id: int, datos: AnticipoEntrada, sesion: Session = Depends(obtener_sesion)
):
    """
    Corrige un anticipo que todavía tiene saldo.

    Solo en estados con saldo (Pendiente/Parcial): un anticipo aplicado del todo,
    anulado o devuelto ya no admite corrección. La lectura es bloqueante. No se
    puede bajar el monto por debajo de lo ya facturado —dejaría un saldo
    negativo— ni cambiar el receptor o el tipo si ya se imputó algo, porque eso
    reescribiría una imputación que ya ocurrió.
    """
    anticipo = sesion.scalar(
        select(Anticipo).where(Anticipo.id == anticipo_id).with_for_update()
    )
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    if anticipo.estado not in ESTADOS_CON_SALDO:
        raise HTTPException(
            409,
            f"Solo se corrige un anticipo con saldo (Pendiente o Parcial); "
            f"este está «{anticipo.estado}».",
        )

    nuevo_monto = redondear(datos.monto)
    if nuevo_monto < anticipo.facturado:
        raise HTTPException(
            422,
            f"El monto no puede ser menor a lo ya facturado (${anticipo.facturado:.2f}).",
        )

    imputado = anticipo.facturado > 0
    if imputado and datos.receptor_id != anticipo.receptor_id:
        raise HTTPException(
            409, "No se puede cambiar el receptor de un anticipo ya imputado."
        )
    if imputado and datos.tipo != anticipo.tipo:
        raise HTTPException(
            409, "No se puede cambiar el tipo de un anticipo ya imputado."
        )

    # El receptor solo cambia si no hay nada imputado; se valida que exista.
    if datos.receptor_id != anticipo.receptor_id:
        receptor = sesion.get(Receptor, datos.receptor_id)
        if receptor is None:
            raise HTTPException(404, "El receptor indicado no existe.")
        anticipo.receptor_id = receptor.id
        anticipo.receptor_razon_social = receptor.razon_social

    anticipo.fecha = datos.fecha or anticipo.fecha
    anticipo.tipo = datos.tipo
    anticipo.detalle = datos.detalle
    anticipo.monto = nuevo_monto
    anticipo.forma_pago = datos.forma_pago
    _recalcular_estado(anticipo)

    sesion.commit()
    sesion.refresh(anticipo)
    return anticipo


@router.post(
    "/{anticipo_id}/devolver",
    response_model=DevolucionAnticipoSalida,
    status_code=201,
)
def devolver(
    anticipo_id: int,
    datos: DevolverAnticipo,
    sesion: Session = Depends(obtener_sesion),
):
    """
    Devuelve el saldo sobrante del anticipo y lo marca «Devuelto».

    El saldo lo calcula el servidor (`monto - facturado`): no se acepta un
    importe del cliente, para que la devolución no descuadre. La lectura es
    bloqueante para no chocar con `aplicar`. No se genera asiento contable
    —este sistema no lleva libro— ni se fuerza el saldo a cero: el registro de
    devolución es la prueba del movimiento.
    """
    anticipo = sesion.scalar(
        select(Anticipo).where(Anticipo.id == anticipo_id).with_for_update()
    )
    if anticipo is None:
        raise HTTPException(404, "Anticipo no encontrado.")
    if anticipo.estado == "Anulado":
        raise HTTPException(409, "Este anticipo está anulado.")
    if anticipo.estado == "Devuelto":
        raise HTTPException(409, "Este anticipo ya se devolvió.")

    saldo = redondear(anticipo.monto - anticipo.facturado)
    if saldo <= 0:
        raise HTTPException(422, "Este anticipo no tiene saldo por devolver.")

    devolucion = DevolucionAnticipo(
        anticipo_id=anticipo.id,
        fecha=datos.fecha or date.today(),
        monto=saldo,
        forma_pago=datos.forma_pago,
        observacion=datos.observacion,
    )
    sesion.add(devolucion)
    anticipo.estado = "Devuelto"

    sesion.commit()
    sesion.refresh(devolucion)
    return devolucion
