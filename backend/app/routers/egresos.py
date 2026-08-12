"""
Endpoints de egresos: tipos de gasto, gastos y pagos.

Ninguno es un comprobante electrónico —el SRI no los recibe— pero sin ellos no
se sabe cuánto se gastó, y el formulario 104 declara también las compras.

La distinción entre **gasto** y **egreso** es deliberada y vale la pena
recordarla: el gasto es la obligación (llegó la factura del arriendo) y el
egreso es la salida de dinero (se pagó el arriendo). No coinciden en el tiempo
ni en el importe, así que se registran por separado.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..base_datos import obtener_sesion
from ..esquemas import (
    EgresoEntrada,
    EgresoSalida,
    GastoEntrada,
    GastoSalida,
    ResumenEgresos,
    TipoGastoEntrada,
    TipoGastoSalida,
)
from ..modelos_db import Egreso, Gasto, Receptor, TipoGasto
from ..sri.modelos import redondear

router = APIRouter(prefix="/egresos", tags=["egresos"])


# --------------------------------------------------------------------------
# Tipos de gasto
# --------------------------------------------------------------------------


@router.get("/tipos", response_model=list[TipoGastoSalida])
def listar_tipos(
    sesion: Session = Depends(obtener_sesion),
    incluir_inactivos: bool = False,
):
    consulta = select(TipoGasto).order_by(TipoGasto.nombre)
    if not incluir_inactivos:
        consulta = consulta.where(TipoGasto.estado == "Activo")
    return sesion.scalars(consulta).all()


@router.post("/tipos", response_model=TipoGastoSalida, status_code=201)
def crear_tipo(datos: TipoGastoEntrada, sesion: Session = Depends(obtener_sesion)):
    repetido = sesion.scalar(select(TipoGasto).where(TipoGasto.nombre == datos.nombre))
    if repetido:
        raise HTTPException(409, f"Ya existe un tipo de gasto llamado «{datos.nombre}».")

    tipo = TipoGasto(**datos.model_dump())
    sesion.add(tipo)
    sesion.commit()
    sesion.refresh(tipo)
    return tipo


@router.put("/tipos/{tipo_id}", response_model=TipoGastoSalida)
def actualizar_tipo(
    tipo_id: int, datos: TipoGastoEntrada, sesion: Session = Depends(obtener_sesion)
):
    tipo = sesion.get(TipoGasto, tipo_id)
    if tipo is None:
        raise HTTPException(404, "Tipo de gasto no encontrado.")

    repetido = sesion.scalar(
        select(TipoGasto).where(TipoGasto.nombre == datos.nombre, TipoGasto.id != tipo_id)
    )
    if repetido:
        raise HTTPException(409, f"Ya existe un tipo de gasto llamado «{datos.nombre}».")

    for campo, valor in datos.model_dump().items():
        setattr(tipo, campo, valor)

    sesion.commit()
    sesion.refresh(tipo)
    return tipo


@router.delete("/tipos/{tipo_id}", status_code=204)
def desactivar_tipo(tipo_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Se desactiva, no se borra.

    Los gastos ya registrados apuntan al tipo; borrarlo los dejaría sin
    categoría y descuadraría los reportes de meses ya cerrados.
    """
    tipo = sesion.get(TipoGasto, tipo_id)
    if tipo is None:
        raise HTTPException(404, "Tipo de gasto no encontrado.")

    tipo.estado = "Inactivo"
    sesion.commit()


# --------------------------------------------------------------------------
# Gastos
# --------------------------------------------------------------------------


@router.get("/gastos", response_model=list[GastoSalida])
def listar_gastos(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    tipo_id: int | None = None,
    estado_pago: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Gasto)

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Gasto.concepto).like(patron),
                func.lower(Gasto.proveedor_razon_social).like(patron),
                func.lower(Gasto.documento).like(patron),
            )
        )
    if tipo_id:
        consulta = consulta.where(Gasto.tipo_id == tipo_id)
    if estado_pago:
        consulta = consulta.where(Gasto.estado_pago == estado_pago)
    if desde:
        consulta = consulta.where(Gasto.fecha >= desde)
    if hasta:
        consulta = consulta.where(Gasto.fecha <= hasta)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Gasto.fecha.desc(), Gasto.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


def _validar_tipo(sesion: Session, tipo_id: int | None) -> TipoGasto | None:
    if tipo_id is None:
        return None
    tipo = sesion.get(TipoGasto, tipo_id)
    if tipo is None:
        raise HTTPException(404, "El tipo de gasto indicado no existe.")
    return tipo


def _validar_proveedor(sesion: Session, proveedor_id: int | None) -> Receptor | None:
    if proveedor_id is None:
        return None
    proveedor = sesion.get(Receptor, proveedor_id)
    if proveedor is None:
        raise HTTPException(404, "El proveedor indicado no existe.")
    # Nada impedía registrar un gasto contra un cliente: el desplegable del
    # formulario lista todos los receptores, no solo los que tienen ese rol.
    if proveedor.rol != "Proveedor":
        raise HTTPException(
            422,
            f"{proveedor.razon_social} está registrado como {proveedor.rol}, no "
            "como Proveedor. Cambia su rol en Receptores o elige otro.",
        )
    return proveedor


@router.post("/gastos", response_model=GastoSalida, status_code=201)
def crear_gasto(datos: GastoEntrada, sesion: Session = Depends(obtener_sesion)):
    _validar_tipo(sesion, datos.tipo_id)
    proveedor = _validar_proveedor(sesion, datos.proveedor_id)

    gasto = Gasto(
        fecha=datos.fecha or date.today(),
        concepto=datos.concepto,
        tipo_id=datos.tipo_id,
        proveedor_id=datos.proveedor_id,
        # Se copia el nombre además del id: si mañana se desactiva el
        # proveedor, el gasto histórico sigue diciendo a quién se le pagó.
        proveedor_razon_social=proveedor.razon_social if proveedor else "",
        proveedor_identificacion=proveedor.identificacion if proveedor else "",
        documento=datos.documento,
        fecha_documento=datos.fecha_documento,
        autorizacion_proveedor=datos.autorizacion_proveedor,
        subtotal=datos.subtotal,
        iva=datos.iva,
        codigo_iva=datos.codigo_iva,
        total=redondear(datos.subtotal + datos.iva),
        estado_pago=datos.estado_pago,
        observacion=datos.observacion,
    )

    sesion.add(gasto)
    sesion.commit()
    sesion.refresh(gasto)
    return gasto


@router.get("/gastos/{gasto_id}", response_model=GastoSalida)
def obtener_gasto(gasto_id: int, sesion: Session = Depends(obtener_sesion)):
    gasto = sesion.get(Gasto, gasto_id)
    if gasto is None:
        raise HTTPException(404, "Gasto no encontrado.")
    return gasto


@router.put("/gastos/{gasto_id}", response_model=GastoSalida)
def actualizar_gasto(
    gasto_id: int, datos: GastoEntrada, sesion: Session = Depends(obtener_sesion)
):
    gasto = sesion.get(Gasto, gasto_id)
    if gasto is None:
        raise HTTPException(404, "Gasto no encontrado.")

    _validar_tipo(sesion, datos.tipo_id)
    proveedor = _validar_proveedor(sesion, datos.proveedor_id)

    gasto.fecha = datos.fecha or gasto.fecha
    gasto.concepto = datos.concepto
    gasto.tipo_id = datos.tipo_id
    gasto.proveedor_id = datos.proveedor_id
    gasto.proveedor_razon_social = proveedor.razon_social if proveedor else ""
    gasto.proveedor_identificacion = proveedor.identificacion if proveedor else ""
    gasto.documento = datos.documento
    gasto.fecha_documento = datos.fecha_documento
    gasto.autorizacion_proveedor = datos.autorizacion_proveedor
    gasto.subtotal = datos.subtotal
    gasto.iva = datos.iva
    gasto.codigo_iva = datos.codigo_iva
    gasto.total = redondear(datos.subtotal + datos.iva)
    gasto.estado_pago = datos.estado_pago
    gasto.observacion = datos.observacion

    sesion.commit()
    sesion.refresh(gasto)
    return gasto


@router.delete("/gastos/{gasto_id}", status_code=204)
def eliminar_gasto(gasto_id: int, sesion: Session = Depends(obtener_sesion)):
    gasto = sesion.get(Gasto, gasto_id)
    if gasto is None:
        raise HTTPException(404, "Gasto no encontrado.")

    pagado = sesion.scalar(select(func.count(Egreso.id)).where(Egreso.gasto_id == gasto_id))
    if pagado:
        raise HTTPException(
            409,
            "Este gasto tiene pagos registrados. Anula primero los egresos "
            "asociados para no dejar la caja descuadrada.",
        )

    sesion.delete(gasto)
    sesion.commit()


# --------------------------------------------------------------------------
# Egresos (pagos)
# --------------------------------------------------------------------------


@router.get("", response_model=list[EgresoSalida])
def listar_egresos(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    forma_pago: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Egreso)

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Egreso.concepto).like(patron),
                func.lower(Egreso.beneficiario).like(patron),
                func.lower(func.coalesce(Egreso.referencia, "")).like(patron),
            )
        )
    if forma_pago:
        consulta = consulta.where(Egreso.forma_pago == forma_pago)
    if estado:
        consulta = consulta.where(Egreso.estado == estado)
    if desde:
        consulta = consulta.where(Egreso.fecha >= desde)
    if hasta:
        consulta = consulta.where(Egreso.fecha <= hasta)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Egreso.fecha.desc(), Egreso.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.post("", response_model=EgresoSalida, status_code=201)
def crear_egreso(datos: EgresoEntrada, sesion: Session = Depends(obtener_sesion)):
    gasto = None
    if datos.gasto_id is not None:
        gasto = sesion.get(Gasto, datos.gasto_id)
        if gasto is None:
            raise HTTPException(404, "El gasto indicado no existe.")

    egreso = Egreso(
        fecha=datos.fecha or date.today(),
        concepto=datos.concepto,
        beneficiario=datos.beneficiario,
        monto=datos.monto,
        forma_pago=datos.forma_pago,
        cuenta_id=datos.cuenta_id,
        referencia=datos.referencia,
        gasto_id=datos.gasto_id,
        observacion=datos.observacion,
    )
    sesion.add(egreso)

    # Si el pago cubre el gasto entero, este deja de estar pendiente. Se
    # compara contra la suma de todos sus pagos, no solo contra este.
    if gasto is not None:
        pagado = sesion.scalar(
            select(func.coalesce(func.sum(Egreso.monto), 0)).where(
                Egreso.gasto_id == gasto.id, Egreso.estado != "Anulado"
            )
        )
        if redondear(pagado or 0) + datos.monto >= gasto.total:
            gasto.estado_pago = "Pagado"
        else:
            gasto.estado_pago = "Parcial"

    sesion.commit()
    sesion.refresh(egreso)
    return egreso


@router.get("/{egreso_id}", response_model=EgresoSalida)
def obtener_egreso(egreso_id: int, sesion: Session = Depends(obtener_sesion)):
    egreso = sesion.get(Egreso, egreso_id)
    if egreso is None:
        raise HTTPException(404, "Egreso no encontrado.")
    return egreso


@router.post("/{egreso_id}/anular", response_model=EgresoSalida)
def anular_egreso(egreso_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Se anula, no se borra: la caja tiene que poder explicar cada movimiento,
    incluidos los que se deshicieron.
    """
    egreso = sesion.get(Egreso, egreso_id)
    if egreso is None:
        raise HTTPException(404, "Egreso no encontrado.")
    if egreso.estado == "Anulado":
        raise HTTPException(409, "Este egreso ya está anulado.")

    egreso.estado = "Anulado"
    # Se vuelca antes de recalcular: la consulta de abajo excluye los anulados,
    # y sin esto seguiría contando este pago como vigente.
    sesion.flush()

    # El gasto vuelve a quedar pendiente si el pago que lo saldaba se anuló.
    if egreso.gasto_id:
        gasto = sesion.get(Gasto, egreso.gasto_id)
        if gasto is not None:
            pagado = sesion.scalar(
                select(func.coalesce(func.sum(Egreso.monto), 0)).where(
                    Egreso.gasto_id == gasto.id, Egreso.estado != "Anulado"
                )
            )
            pagado = redondear(pagado or 0)
            if pagado <= 0:
                gasto.estado_pago = "Por Pagar"
            elif pagado < gasto.total:
                gasto.estado_pago = "Parcial"

    sesion.commit()
    sesion.refresh(egreso)
    return egreso


# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------


@router.get("/resumen/periodo", response_model=ResumenEgresos)
def resumen(
    sesion: Session = Depends(obtener_sesion),
    desde: date | None = None,
    hasta: date | None = None,
):
    """Cuánto se gastó y cuánto se pagó en el período, y qué queda debiendo."""
    gastos = select(func.count(Gasto.id), func.coalesce(func.sum(Gasto.total), 0))
    pagos = select(func.coalesce(func.sum(Egreso.monto), 0)).where(Egreso.estado != "Anulado")

    if desde:
        gastos = gastos.where(Gasto.fecha >= desde)
        pagos = pagos.where(Egreso.fecha >= desde)
    if hasta:
        gastos = gastos.where(Gasto.fecha <= hasta)
        pagos = pagos.where(Egreso.fecha <= hasta)

    cantidad, total_gastos = sesion.execute(gastos).one()
    total_pagos = sesion.scalar(pagos)

    # Lo pendiente no se acota por período: una factura de hace meses sigue
    # debiéndose hoy, y filtrarla escondería justo la deuda más vieja.
    pendiente = sesion.scalar(
        select(func.coalesce(func.sum(Gasto.total), 0)).where(Gasto.estado_pago != "Pagado")
    )

    return ResumenEgresos(
        gastos=cantidad or 0,
        total_gastos=redondear(total_gastos or 0),
        total_pagos=redondear(total_pagos or 0),
        pendiente=redondear(pendiente or 0),
    )
