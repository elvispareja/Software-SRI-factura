"""Endpoints de comprobantes de retención."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..esquemas import RespuestaEmisionRetencion, RetencionEntrada, RetencionSalida
from ..modelos_db import DetalleRetencion, Empresa, Receptor, Retencion
from ..servicios.emision import ErrorEmision, consultar_autorizacion
from ..servicios.emision_retenciones import (
    construir_modelo,
    construir_xml,
    emitir_retencion,
)
from ..servicios.secuenciales import (
    buscar_punto_emision,
    formatear_numero,
    reservar_secuencial,
)
from ..sri.codigos_retencion import catalogo
from ..sri.modelos import redondear
from ..sri.ride import generar_ride_retencion

router = APIRouter(prefix="/retenciones", tags=["retenciones"])

TIPO = "Retención"


@router.get("/codigos", response_model=list[dict])
def codigos_de_retencion():
    """
    Catálogo de conceptos con su porcentaje habitual.

    Es una ayuda para la interfaz: al crear una retención se acepta cualquier
    código, porque quien valida los porcentajes vigentes es el SRI.
    """
    return catalogo()


@router.get("", response_model=list[RetencionSalida])
def listar_retenciones(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    estado_sri: str | None = None,
    periodo_fiscal: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Retencion).options(selectinload(Retencion.detalles))

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Retencion.numero).like(patron),
                func.lower(Retencion.sujeto_razon_social).like(patron),
                func.lower(Retencion.sujeto_identificacion).like(patron),
                func.lower(Retencion.num_doc_sustento).like(patron),
            )
        )
    if estado_sri:
        consulta = consulta.where(Retencion.estado_sri == estado_sri)
    if periodo_fiscal:
        consulta = consulta.where(Retencion.periodo_fiscal == periodo_fiscal)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Retencion.fecha_emision.desc(), Retencion.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.post("", response_model=RetencionSalida, status_code=201)
def crear_retencion(datos: RetencionEntrada, sesion: Session = Depends(obtener_sesion)):
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise HTTPException(409, "No hay empresa configurada.")

    # Retener sin ser agente de retención es una infracción tributaria, no un
    # detalle de formato; se avisa aquí y no cuando el SRI lo rechace.
    if not (empresa.agente_retencion or empresa.contribuyente_especial):
        raise HTTPException(
            422,
            "La empresa no está marcada como agente de retención ni como contribuyente "
            "especial. Complétalo en Configuraciones antes de emitir retenciones.",
        )

    sujeto = sesion.get(Receptor, datos.sujeto_id)
    if sujeto is None:
        raise HTTPException(404, "El sujeto retenido indicado no existe.")

    # Se retiene a quien nos vende, no a quien nos compra.
    if sujeto.rol != "Proveedor":
        raise HTTPException(
            422,
            f"{sujeto.razon_social} está registrado como {sujeto.rol}. "
            "La retención se emite a un proveedor.",
        )

    fecha_emision = datos.fecha_emision or date.today()
    periodo = datos.periodo_fiscal or f"{fecha_emision:%m/%Y}"

    punto = buscar_punto_emision(
        sesion, empresa.id, datos.establecimiento, datos.punto_emision
    )
    secuencial = reservar_secuencial(sesion, punto, TIPO)

    retencion = Retencion(
        numero=formatear_numero(datos.establecimiento, datos.punto_emision, secuencial),
        establecimiento=datos.establecimiento,
        punto_emision=datos.punto_emision,
        secuencial=secuencial,
        fecha_emision=fecha_emision,
        periodo_fiscal=periodo,
        sujeto_id=sujeto.id,
        sujeto_razon_social=sujeto.razon_social,
        sujeto_identificacion=sujeto.identificacion,
        sujeto_tipo_identificacion=sujeto.tipo_identificacion,
        cod_doc_sustento=datos.cod_doc_sustento,
        num_doc_sustento=datos.num_doc_sustento,
        fecha_doc_sustento=datos.fecha_doc_sustento or fecha_emision,
    )

    total = redondear(0)
    for detalle in datos.detalles:
        valor = redondear(detalle.base_imponible * detalle.porcentaje_retener / 100)
        total += valor
        retencion.detalles.append(
            DetalleRetencion(
                codigo_impuesto=detalle.codigo_impuesto,
                codigo_retencion=detalle.codigo_retencion,
                base_imponible=detalle.base_imponible,
                porcentaje_retener=detalle.porcentaje_retener,
                valor_retenido=valor,
            )
        )
    retencion.total_retenido = redondear(total)

    sesion.add(retencion)
    sesion.commit()
    sesion.refresh(retencion)
    return retencion


@router.get("/{retencion_id}", response_model=RetencionSalida)
def obtener_retencion(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")
    return retencion


@router.post("/{retencion_id}/anular", response_model=RetencionSalida)
def anular_retencion(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")

    if retencion.estado_sri == "Autorizado":
        raise HTTPException(
            409, "Una retención autorizada se anula ante el SRI, no desde aquí."
        )

    retencion.estado_sri = "Anulado"
    sesion.commit()
    sesion.refresh(retencion)
    return retencion


@router.post("/{retencion_id}/emitir", response_model=RespuestaEmisionRetencion)
def emitir(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    """Firma la retención con el certificado configurado y la envía al SRI."""
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")

    try:
        resultado = emitir_retencion(sesion, retencion)
    except ErrorEmision as error:
        # Se conserva lo que quedó grabado (XML firmado, mensajes del fallo).
        sesion.commit()
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(retencion)

    return RespuestaEmisionRetencion(
        retencion=retencion,
        estado_recepcion=resultado.get("recepcion", ""),
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.post("/{retencion_id}/consultar", response_model=RespuestaEmisionRetencion)
def consultar_estado(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Reconsulta la autorización.

    El SRI no autoriza de forma síncrona: una retención recibida puede quedar
    pendiente y autorizarse minutos más tarde.
    """
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")

    try:
        resultado = consultar_autorizacion(sesion, retencion)
    except ErrorEmision as error:
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(retencion)

    return RespuestaEmisionRetencion(
        retencion=retencion,
        estado_recepcion="RECIBIDA",
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.get("/{retencion_id}/xml")
def descargar_xml(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    """XML firmado si ya se emitió; si sigue en borrador, el XML sin firmar."""
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")

    if retencion.xml_firmado:
        contenido = retencion.xml_firmado.encode("utf-8")
        nombre = f"{retencion.clave_acceso}.xml"
    else:
        try:
            contenido, clave = construir_xml(sesion, retencion)
        except ErrorEmision as error:
            raise HTTPException(422, str(error)) from error
        nombre = f"{clave}.xml"

    return Response(
        content=contenido,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{retencion_id}/ride")
def descargar_ride(retencion_id: int, sesion: Session = Depends(obtener_sesion)):
    """RIDE de la retención: el proveedor necesita ver contra qué documento se le retuvo."""
    retencion = sesion.get(Retencion, retencion_id)
    if retencion is None:
        raise HTTPException(404, "Retención no encontrada.")

    try:
        modelo = construir_modelo(sesion, retencion)
    except ErrorEmision as error:
        raise HTTPException(422, str(error)) from error

    pdf = generar_ride_retencion(
        retencion=modelo,
        numero=retencion.numero,
        clave_acceso=retencion.clave_acceso or "",
        numero_autorizacion=retencion.numero_autorizacion,
        fecha_autorizacion=retencion.fecha_autorizacion,
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="RIDE-{retencion.numero}.pdf"'},
    )
