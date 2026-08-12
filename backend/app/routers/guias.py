"""Endpoints de guías de remisión."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..esquemas import GuiaEntrada, GuiaSalida, RespuestaEmisionGuia
from ..modelos_db import Empresa, GuiaRemision, ItemGuiaRemision, Receptor
from ..servicios.emision import ErrorEmision, consultar_autorizacion
from ..servicios.emision_guias import construir_modelo, construir_xml, emitir_guia
from ..servicios.secuenciales import (
    buscar_punto_emision,
    formatear_numero,
    reservar_secuencial,
)

from ..sri.ride import generar_ride_guia

router = APIRouter(prefix="/guias", tags=["guías de remisión"])

TIPO = "Guía de Remisión"


@router.get("", response_model=list[GuiaSalida])
def listar_guias(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    estado_sri: str | None = None,
    motivo_traslado: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(GuiaRemision).options(selectinload(GuiaRemision.items))

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(GuiaRemision.numero).like(patron),
                func.lower(GuiaRemision.transportista_razon_social).like(patron),
                func.lower(GuiaRemision.placa).like(patron),
            )
        )
    if estado_sri:
        consulta = consulta.where(GuiaRemision.estado_sri == estado_sri)
    if motivo_traslado:
        consulta = consulta.where(GuiaRemision.motivo_traslado == motivo_traslado)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(GuiaRemision.fecha_inicio.desc(), GuiaRemision.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.post("", response_model=GuiaSalida, status_code=201)
def crear_guia(datos: GuiaEntrada, sesion: Session = Depends(obtener_sesion)):
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise HTTPException(409, "No hay empresa configurada.")

    transportista = sesion.get(Receptor, datos.transportista_id)
    if transportista is None:
        raise HTTPException(404, "El transportista indicado no existe.")

    # El SRI identifica al transportista en el XML; un cliente en ese campo
    # produce una guía que no corresponde a quien realmente traslada.
    if transportista.rol != "Transportista":
        raise HTTPException(
            422,
            f"{transportista.razon_social} está registrado como {transportista.rol}, "
            "no como transportista.",
        )

    punto = buscar_punto_emision(
        sesion, empresa.id, datos.establecimiento, datos.punto_emision
    )
    secuencial = reservar_secuencial(sesion, punto, TIPO)

    guia = GuiaRemision(
        numero=formatear_numero(datos.establecimiento, datos.punto_emision, secuencial),
        establecimiento=datos.establecimiento,
        punto_emision=datos.punto_emision,
        secuencial=secuencial,
        fecha_inicio=datos.fecha_inicio,
        fecha_fin=datos.fecha_fin,
        motivo_traslado=datos.motivo_traslado,
        ruta=datos.ruta,
        tipo_transporte=datos.tipo_transporte,
        documento_aduanero=datos.documento_aduanero,
        transportista_id=transportista.id,
        transportista_razon_social=transportista.razon_social,
        transportista_identificacion=transportista.identificacion,
        placa=datos.placa.upper(),
        provincia_partida=datos.provincia_partida,
        canton_partida=datos.canton_partida,
        direccion_partida=datos.direccion_partida,
        provincia_llegada=datos.provincia_llegada,
        canton_llegada=datos.canton_llegada,
        direccion_llegada=datos.direccion_llegada,
    )

    for item in datos.items:
        guia.items.append(
            ItemGuiaRemision(
                codigo=item.codigo,
                descripcion=item.descripcion,
                cantidad=item.cantidad,
            )
        )

    sesion.add(guia)
    sesion.commit()
    sesion.refresh(guia)
    return guia


@router.get("/{guia_id}", response_model=GuiaSalida)
def obtener_guia(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")
    return guia


@router.post("/{guia_id}/anular", response_model=GuiaSalida)
def anular_guia(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")

    if guia.estado_sri == "Autorizado":
        raise HTTPException(409, "Una guía autorizada no se puede anular desde aquí.")

    guia.estado_sri = "Anulado"
    sesion.commit()
    sesion.refresh(guia)
    return guia


@router.post("/{guia_id}/emitir", response_model=RespuestaEmisionGuia)
def emitir(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    """Firma la guía con el certificado configurado y la envía al SRI."""
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")

    try:
        resultado = emitir_guia(sesion, guia)
    except ErrorEmision as error:
        # La guía pudo quedar marcada con el fallo; se conserva.
        sesion.commit()
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(guia)

    return RespuestaEmisionGuia(
        guia=guia,
        estado_recepcion=resultado.get("recepcion", ""),
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.post("/{guia_id}/consultar", response_model=RespuestaEmisionGuia)
def consultar_estado(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Reconsulta la autorización.

    El SRI no autoriza de forma síncrona: una guía recibida puede quedar
    pendiente y autorizarse minutos más tarde.
    """
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")

    try:
        resultado = consultar_autorizacion(sesion, guia)
    except ErrorEmision as error:
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(guia)

    return RespuestaEmisionGuia(
        guia=guia,
        estado_recepcion="RECIBIDA",
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.get("/{guia_id}/xml")
def descargar_xml(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    """XML firmado si ya se emitió; si sigue en borrador, el XML sin firmar."""
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")

    if guia.xml_firmado:
        contenido = guia.xml_firmado.encode("utf-8")
        nombre = f"{guia.clave_acceso}.xml"
    else:
        try:
            contenido, clave = construir_xml(sesion, guia)
        except ErrorEmision as error:
            raise HTTPException(422, str(error)) from error
        nombre = f"{clave}.xml"

    return Response(
        content=contenido,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{guia_id}/ride")
def descargar_ride(guia_id: int, sesion: Session = Depends(obtener_sesion)):
    """RIDE de la guía: sin totales, porque documenta un traslado y no una venta."""
    guia = sesion.get(GuiaRemision, guia_id)
    if guia is None:
        raise HTTPException(404, "Guía de remisión no encontrada.")

    try:
        modelo = construir_modelo(sesion, guia)
    except ErrorEmision as error:
        raise HTTPException(422, str(error)) from error

    pdf = generar_ride_guia(
        guia=modelo,
        numero=guia.numero,
        clave_acceso=guia.clave_acceso or "",
        numero_autorizacion=guia.numero_autorizacion,
        fecha_autorizacion=guia.fecha_autorizacion,
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="RIDE-{guia.numero}.pdf"'},
    )
