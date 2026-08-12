"""Endpoints CRUD de receptores y artículos."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..base_datos import obtener_sesion
from ..esquemas import ArticuloEntrada, ArticuloSalida, ReceptorEntrada, ReceptorSalida
from ..modelos_db import Articulo, Receptor

router = APIRouter(tags=["catálogos"])


def _aplicar_busqueda(consulta, termino: str | None, columnas):
    if not termino:
        return consulta
    patron = f"%{termino.lower()}%"
    return consulta.where(or_(*[func.lower(columna).like(patron) for columna in columnas]))


# --------------------------------------------------------------------------
# Receptores
# --------------------------------------------------------------------------


@router.get("/receptores", response_model=list[ReceptorSalida])
def listar_receptores(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    rol: str | None = None,
    estado: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Receptor)
    consulta = _aplicar_busqueda(
        consulta, buscar, [Receptor.razon_social, Receptor.identificacion, Receptor.nombre_comercial]
    )
    if rol:
        consulta = consulta.where(Receptor.rol == rol)
    if estado:
        consulta = consulta.where(Receptor.estado == estado)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    # El total va en cabecera para que el cliente pagine sin una segunda llamada.
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = consulta.order_by(Receptor.razon_social).offset((pagina - 1) * tamano).limit(tamano)
    return sesion.scalars(consulta).all()


@router.post("/receptores", response_model=ReceptorSalida, status_code=201)
def crear_receptor(datos: ReceptorEntrada, sesion: Session = Depends(obtener_sesion)):
    existente = sesion.scalar(
        select(Receptor).where(Receptor.identificacion == datos.identificacion)
    )
    if existente:
        raise HTTPException(409, f"Ya existe un receptor con la identificación {datos.identificacion}.")

    receptor = Receptor(**datos.model_dump())
    sesion.add(receptor)
    sesion.commit()
    sesion.refresh(receptor)
    return receptor


@router.get("/receptores/{receptor_id}", response_model=ReceptorSalida)
def obtener_receptor(receptor_id: int, sesion: Session = Depends(obtener_sesion)):
    receptor = sesion.get(Receptor, receptor_id)
    if receptor is None:
        raise HTTPException(404, "Receptor no encontrado.")
    return receptor


@router.put("/receptores/{receptor_id}", response_model=ReceptorSalida)
def actualizar_receptor(
    receptor_id: int, datos: ReceptorEntrada, sesion: Session = Depends(obtener_sesion)
):
    receptor = sesion.get(Receptor, receptor_id)
    if receptor is None:
        raise HTTPException(404, "Receptor no encontrado.")

    # No permitir colisión de identificación con otro receptor.
    duplicado = sesion.scalar(
        select(Receptor).where(Receptor.identificacion == datos.identificacion, Receptor.id != receptor_id)
    )
    if duplicado:
        raise HTTPException(409, f"Ya existe otro receptor con la identificación {datos.identificacion}.")

    for campo, valor in datos.model_dump().items():
        setattr(receptor, campo, valor)
    sesion.commit()
    sesion.refresh(receptor)
    return receptor


@router.delete("/receptores/{receptor_id}", status_code=204)
def desactivar_receptor(receptor_id: int, sesion: Session = Depends(obtener_sesion)):
    """No se borra: los comprobantes emitidos deben conservar a su receptor."""
    receptor = sesion.get(Receptor, receptor_id)
    if receptor is None:
        raise HTTPException(404, "Receptor no encontrado.")
    receptor.estado = "Inactivo"
    sesion.commit()


# --------------------------------------------------------------------------
# Artículos
# --------------------------------------------------------------------------


@router.get("/articulos", response_model=list[ArticuloSalida])
def listar_articulos(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    tipo: str | None = None,
    estado: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Articulo)
    consulta = _aplicar_busqueda(
        consulta, buscar, [Articulo.nombre, Articulo.codigo, Articulo.categoria]
    )
    if tipo:
        consulta = consulta.where(Articulo.tipo == tipo)
    if estado:
        consulta = consulta.where(Articulo.estado == estado)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = consulta.order_by(Articulo.codigo).offset((pagina - 1) * tamano).limit(tamano)
    return sesion.scalars(consulta).all()


@router.post("/articulos", response_model=ArticuloSalida, status_code=201)
def crear_articulo(datos: ArticuloEntrada, sesion: Session = Depends(obtener_sesion)):
    existente = sesion.scalar(select(Articulo).where(Articulo.codigo == datos.codigo))
    if existente:
        raise HTTPException(409, f"Ya existe un artículo con el código {datos.codigo}.")

    articulo = Articulo(**datos.model_dump())
    sesion.add(articulo)
    sesion.commit()
    sesion.refresh(articulo)
    return articulo


@router.get("/articulos/{articulo_id}", response_model=ArticuloSalida)
def obtener_articulo(articulo_id: int, sesion: Session = Depends(obtener_sesion)):
    articulo = sesion.get(Articulo, articulo_id)
    if articulo is None:
        raise HTTPException(404, "Artículo no encontrado.")
    return articulo


@router.put("/articulos/{articulo_id}", response_model=ArticuloSalida)
def actualizar_articulo(
    articulo_id: int, datos: ArticuloEntrada, sesion: Session = Depends(obtener_sesion)
):
    articulo = sesion.get(Articulo, articulo_id)
    if articulo is None:
        raise HTTPException(404, "Artículo no encontrado.")

    duplicado = sesion.scalar(
        select(Articulo).where(Articulo.codigo == datos.codigo, Articulo.id != articulo_id)
    )
    if duplicado:
        raise HTTPException(409, f"Ya existe otro artículo con el código {datos.codigo}.")

    for campo, valor in datos.model_dump().items():
        setattr(articulo, campo, valor)
    sesion.commit()
    sesion.refresh(articulo)
    return articulo


@router.delete("/articulos/{articulo_id}", status_code=204)
def desactivar_articulo(articulo_id: int, sesion: Session = Depends(obtener_sesion)):
    articulo = sesion.get(Articulo, articulo_id)
    if articulo is None:
        raise HTTPException(404, "Artículo no encontrado.")
    articulo.estado = "Inactivo"
    sesion.commit()
