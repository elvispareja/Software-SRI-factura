"""
Endpoints de facturación recurrente.

La emisión **no es automática**: `GET /recurrentes/vencidas` dice qué toca y
`POST /recurrentes/{id}/emitir` lo genera, pero la orden la da una persona. Una
factura emitida sola contra un cliente que ya canceló el servicio hay que
anularla con nota de crédito, y eso cuesta más que pulsar un botón al mes.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..esquemas import (
    ComprobanteSalida,
    PlantillaRecurrenteEntrada,
    PlantillaRecurrenteSalida,
    RespuestaEmisionRecurrente,
)
from ..modelos_db import LineaRecurrente, PlantillaRecurrente, Receptor
from ..servicios.recurrentes import (
    ErrorRecurrente,
    emitir_desde_plantilla,
    total_de,
    vencidas,
)

router = APIRouter(prefix="/recurrentes", tags=["facturación recurrente"])


def _con_lineas():
    return select(PlantillaRecurrente).options(selectinload(PlantillaRecurrente.lineas))


@router.get("", response_model=list[PlantillaRecurrenteSalida])
def listar(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    periodicidad: str | None = None,
    activa: bool | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = _con_lineas()

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(PlantillaRecurrente.nombre).like(patron),
                func.lower(PlantillaRecurrente.receptor_razon_social).like(patron),
            )
        )
    if periodicidad:
        consulta = consulta.where(PlantillaRecurrente.periodicidad == periodicidad)
    if activa is not None:
        consulta = consulta.where(PlantillaRecurrente.activa.is_(activa))

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(PlantillaRecurrente.proxima_emision)
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.get("/vencidas", response_model=list[PlantillaRecurrenteSalida])
def listar_vencidas(sesion: Session = Depends(obtener_sesion), hasta: date | None = None):
    """Plantillas activas cuya próxima emisión ya llegó."""
    return vencidas(sesion, hasta or date.today())


def _aplicar(sesion: Session, plantilla: PlantillaRecurrente, datos: PlantillaRecurrenteEntrada):
    receptor = sesion.get(Receptor, datos.receptor_id)
    if receptor is None:
        raise HTTPException(404, "El cliente indicado no existe.")

    plantilla.nombre = datos.nombre
    plantilla.receptor_id = receptor.id
    plantilla.receptor_razon_social = receptor.razon_social
    plantilla.periodicidad = datos.periodicidad
    plantilla.proxima_emision = datos.proxima_emision
    plantilla.hasta = datos.hasta
    plantilla.establecimiento = datos.establecimiento
    plantilla.punto_emision = datos.punto_emision
    plantilla.forma_pago = datos.forma_pago
    plantilla.activa = datos.activa

    plantilla.lineas.clear()
    for linea in datos.lineas:
        plantilla.lineas.append(LineaRecurrente(**linea.model_dump()))

    sesion.flush()
    plantilla.total = total_de(plantilla)


@router.post("", response_model=PlantillaRecurrenteSalida, status_code=201)
def crear(datos: PlantillaRecurrenteEntrada, sesion: Session = Depends(obtener_sesion)):
    plantilla = PlantillaRecurrente(proxima_emision=datos.proxima_emision)
    _aplicar(sesion, plantilla, datos)

    sesion.add(plantilla)
    sesion.commit()
    sesion.refresh(plantilla)
    return plantilla


@router.get("/{plantilla_id}", response_model=PlantillaRecurrenteSalida)
def obtener(plantilla_id: int, sesion: Session = Depends(obtener_sesion)):
    plantilla = sesion.get(PlantillaRecurrente, plantilla_id)
    if plantilla is None:
        raise HTTPException(404, "Plantilla no encontrada.")
    return plantilla


@router.put("/{plantilla_id}", response_model=PlantillaRecurrenteSalida)
def actualizar(
    plantilla_id: int,
    datos: PlantillaRecurrenteEntrada,
    sesion: Session = Depends(obtener_sesion),
):
    plantilla = sesion.get(PlantillaRecurrente, plantilla_id)
    if plantilla is None:
        raise HTTPException(404, "Plantilla no encontrada.")

    _aplicar(sesion, plantilla, datos)
    sesion.commit()
    sesion.refresh(plantilla)
    return plantilla


@router.post("/{plantilla_id}/pausar", response_model=PlantillaRecurrenteSalida)
def pausar(plantilla_id: int, sesion: Session = Depends(obtener_sesion)):
    plantilla = sesion.get(PlantillaRecurrente, plantilla_id)
    if plantilla is None:
        raise HTTPException(404, "Plantilla no encontrada.")

    plantilla.activa = not plantilla.activa
    sesion.commit()
    sesion.refresh(plantilla)
    return plantilla


@router.post("/{plantilla_id}/emitir", response_model=RespuestaEmisionRecurrente)
def emitir(plantilla_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Genera la factura del período y adelanta la plantilla.

    El comprobante queda en **borrador**: quien lo revise decide si se
    transmite al SRI, desde el listado de comprobantes como cualquier otro.
    """
    plantilla = sesion.get(PlantillaRecurrente, plantilla_id)
    if plantilla is None:
        raise HTTPException(404, "Plantilla no encontrada.")

    try:
        comprobante = emitir_desde_plantilla(sesion, plantilla)
    except ErrorRecurrente as error:
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(plantilla)
    sesion.refresh(comprobante)

    return RespuestaEmisionRecurrente(
        plantilla=PlantillaRecurrenteSalida.model_validate(plantilla),
        comprobante=ComprobanteSalida.model_validate(comprobante),
    )


@router.delete("/{plantilla_id}", status_code=204)
def eliminar(plantilla_id: int, sesion: Session = Depends(obtener_sesion)):
    plantilla = sesion.get(PlantillaRecurrente, plantilla_id)
    if plantilla is None:
        raise HTTPException(404, "Plantilla no encontrada.")

    # Borrar la plantilla no borra las facturas ya emitidas: son documentos
    # tributarios y viven por su cuenta.
    sesion.delete(plantilla)
    sesion.commit()
