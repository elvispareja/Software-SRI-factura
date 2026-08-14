"""
Endpoints de documentos: factura, cotización, nota de venta, liquidación de
compra y notas de crédito/débito.

Todos comparten cabecera, receptor, detalle y totales, así que comparten
endpoint y se distinguen por `tipo`. Las validaciones propias de cada tipo
(referencia al documento modificado en las notas, rol del receptor en la
liquidación) se aplican en `_validar_por_tipo`.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..fecha_ec import hoy_ec
from ..seguridad import administrador_actual
from ..esquemas import (
    ComprobanteEntrada,
    ComprobanteSalida,
    EnvioCorreo,
    RespuestaEmision,
    RespuestaEnvio,
)
from ..modelos_db import (
    Comprobante,
    DetalleComprobante,
    Empresa,
    Establecimiento,
    Receptor,
    Usuario,
)
from ..servicios.emision import (
    ErrorEmision,
    consultar_autorizacion,
    emitir_comprobante,
)
from ..servicios.secuenciales import (
    buscar_punto_emision,
    formatear_numero,
    reservar_secuencial,
)
from ..sri.identificacion import codigo_sri
from ..sri.modelos import Comprador, Detalle, Emisor, Factura, Pago
from ..sri.ride import generar_ride
from ..sri.xml_factura import generar_xml_factura

router = APIRouter(prefix="/comprobantes", tags=["comprobantes"])

# Tipos que sí son comprobantes electrónicos y viajan al SRI.
TIPOS_ELECTRONICOS = {
    "Factura",
    "Nota de Crédito",
    "Nota de Débito",
    "Liquidación de Compra",
    "Nota de Venta",
}

TIPOS_NOTA = {"Nota de Crédito", "Nota de Débito"}

# Título que se imprime en el RIDE. Sin esto todos salían como "FACTURA", y
# una nota de crédito rotulada factura es un documento equivocado.
TITULO_RIDE = {
    "Factura": "FACTURA",
    "Nota de Crédito": "NOTA DE CRÉDITO",
    "Nota de Débito": "NOTA DE DÉBITO",
    "Liquidación de Compra": "LIQUIDACIÓN DE COMPRA",
    "Nota de Venta": "NOTA DE VENTA",
    "Cotización": "COTIZACIÓN",
}


def _empresa_actual(sesion: Session) -> Empresa:
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise HTTPException(409, "No hay empresa configurada. Configura los datos del emisor.")
    return empresa


def _validar_por_tipo(datos: ComprobanteEntrada, receptor: Receptor) -> None:
    """Reglas que solo aplican a ciertos tipos de documento."""
    if datos.tipo in TIPOS_NOTA:
        faltantes = [
            campo
            for campo, valor in (
                ("num_doc_modificado", datos.num_doc_modificado),
                ("fecha_doc_modificado", datos.fecha_doc_modificado),
                ("motivo", datos.motivo),
            )
            if not valor
        ]
        if faltantes:
            raise HTTPException(
                422,
                "Una nota de crédito o débito debe referenciar el documento que modifica. "
                f"Faltan: {', '.join(faltantes)}.",
            )

        # El número del documento modificado debe venir en el formato del SRI
        # (EEE-PPP-NNNNNNNNN); cualquier otro lo rechazaría al emitir.
        if not re.fullmatch(r"\d{3}-\d{3}-\d{9}", datos.num_doc_modificado or ""):
            raise HTTPException(
                422,
                "El número del documento modificado debe tener el formato "
                "EEE-PPP-NNNNNNNNN (p. ej. 001-001-000000135).",
            )

    if datos.tipo == "Liquidación de Compra" and receptor.rol != "Proveedor":
        raise HTTPException(
            422,
            "La liquidación de compra se emite contra un proveedor, "
            f"y {receptor.razon_social} está registrado como {receptor.rol}.",
        )

    # La dirección es obligatoria en el XML de todo comprobante electrónico.
    if datos.tipo in TIPOS_ELECTRONICOS and not receptor.direccion:
        raise HTTPException(
            422, "El receptor no tiene dirección, obligatoria para el XML del SRI."
        )


# codDocModificado (tabla 4 del SRI) → tipos internos que una nota puede
# referenciar. El "03" es ambiguo (nota de venta o liquidación), así que cubre
# ambos.
_TIPOS_POR_COD_MODIFICADO = {
    "01": ("Factura",),
    "03": ("Nota de Venta", "Liquidación de Compra"),
    "04": ("Nota de Crédito",),
    "05": ("Nota de Débito",),
}


def _validar_nota_contra_original(
    sesion: Session,
    datos: ComprobanteEntrada,
    receptor: Receptor,
    importe_nota,
) -> None:
    """
    Verificación cruzada, best-effort, de una nota contra su documento original.

    Solo se aplica cuando el documento referenciado consta en esta base y está
    **Autorizado**. Una nota puede referenciar legítimamente un documento
    externo (emitido por otro sistema o en papel) que aquí no existe; en ese
    caso no se bloquea, solo se omite la verificación cruzada. Cuando el
    original sí está y está autorizado, se exige que sea del mismo receptor y
    que la nota no lo exceda en importe.
    """
    if datos.tipo not in TIPOS_NOTA:
        return

    tipos_posibles = _TIPOS_POR_COD_MODIFICADO.get(datos.cod_doc_modificado or "")
    if not tipos_posibles:
        return

    original = sesion.scalar(
        select(Comprobante).where(
            Comprobante.numero == datos.num_doc_modificado,
            Comprobante.tipo.in_(tipos_posibles),
            Comprobante.estado_sri == "Autorizado",
        )
    )
    if original is None:
        # No consta autorizado aquí: puede ser un documento externo. No se
        # fuerza su existencia para no bloquear ese caso legítimo.
        return

    if original.receptor_identificacion != receptor.identificacion:
        raise HTTPException(
            422,
            "El documento que la nota modifica pertenece a otro receptor "
            f"({original.receptor_razon_social}).",
        )

    if importe_nota > original.importe_total:
        raise HTTPException(
            422,
            f"El importe de la nota ({importe_nota}) excede el del documento "
            f"modificado ({original.importe_total}).",
        )


def _construir_factura(sesion: Session, comprobante: Comprobante) -> Factura:
    """Traduce el registro de base de datos al modelo que entiende el motor SRI."""
    empresa = _empresa_actual(sesion)
    establecimiento = sesion.scalar(
        select(Establecimiento).where(
            Establecimiento.empresa_id == empresa.id,
            Establecimiento.codigo == comprobante.establecimiento,
        )
    )

    emisor = Emisor(
        ruc=empresa.ruc,
        razon_social=empresa.razon_social,
        nombre_comercial=empresa.nombre_comercial or "",
        direccion_matriz=empresa.direccion_matriz,
        direccion_establecimiento=(
            establecimiento.direccion if establecimiento else empresa.direccion_matriz
        ),
        establecimiento=comprobante.establecimiento,
        punto_emision=comprobante.punto_emision,
        obligado_contabilidad=empresa.obligado_contabilidad,
        contribuyente_especial=empresa.contribuyente_especial,
        agente_retencion=empresa.agente_retencion,
        contribuyente_rimpe=empresa.contribuyente_rimpe,
    )

    receptor = comprobante.receptor
    comprador = Comprador(
        tipo_identificacion=codigo_sri(
            receptor.tipo_identificacion if receptor else "Consumidor Final"
        ),
        identificacion=comprobante.receptor_identificacion,
        razon_social=comprobante.receptor_razon_social,
        direccion=receptor.direccion if receptor else "",
        correo=receptor.correo if receptor else None,
    )

    detalles = [
        Detalle(
            codigo_principal=detalle.codigo_principal,
            descripcion=detalle.descripcion,
            cantidad=detalle.cantidad,
            precio_unitario=detalle.precio_unitario,
            codigo_iva=detalle.codigo_iva,
            descuento_porcentaje=detalle.descuento_porcentaje,
            codigo_auxiliar=detalle.codigo_auxiliar,
        )
        for detalle in comprobante.detalles
    ]

    factura = Factura(
        emisor=emisor,
        comprador=comprador,
        fecha_emision=comprobante.fecha_emision,
        secuencial=comprobante.secuencial,
        detalles=detalles,
        ambiente=empresa.ambiente,
    )
    factura.pagos = [Pago(forma_pago=comprobante.forma_pago, total=factura.importe_total)]
    return factura


@router.get("", response_model=list[ComprobanteSalida])
def listar_comprobantes(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    tipo: str | None = None,
    estado_sri: str | None = None,
    estado_pago: str | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(20, ge=1, le=200),
):
    consulta = select(Comprobante).options(selectinload(Comprobante.detalles))

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Comprobante.numero).like(patron),
                func.lower(Comprobante.receptor_razon_social).like(patron),
            )
        )
    if tipo:
        consulta = consulta.where(Comprobante.tipo == tipo)
    if estado_sri:
        consulta = consulta.where(Comprobante.estado_sri == estado_sri)
    if estado_pago:
        consulta = consulta.where(Comprobante.estado_pago == estado_pago)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Comprobante.fecha_emision.desc(), Comprobante.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


@router.post("", response_model=ComprobanteSalida, status_code=201)
def crear_comprobante(datos: ComprobanteEntrada, sesion: Session = Depends(obtener_sesion)):
    """
    Crea el documento en estado Borrador y reserva su secuencial.

    El secuencial se toma y se incrementa en la misma transacción, y es propio
    de cada tipo: la factura 135 y la nota de crédito 135 conviven sin conflicto.
    """
    empresa = _empresa_actual(sesion)

    receptor = sesion.get(Receptor, datos.receptor_id)
    if receptor is None:
        raise HTTPException(404, "El receptor indicado no existe.")

    _validar_por_tipo(datos, receptor)

    hoy = hoy_ec()
    fecha_emision = datos.fecha_emision or hoy
    if fecha_emision > hoy:
        raise HTTPException(
            422,
            "La fecha de emisión no puede ser futura respecto a la fecha "
            f"actual en Ecuador ({hoy:%d/%m/%Y}).",
        )

    punto = buscar_punto_emision(
        sesion, empresa.id, datos.establecimiento, datos.punto_emision
    )
    secuencial = reservar_secuencial(sesion, punto, datos.tipo)

    comprobante = Comprobante(
        tipo=datos.tipo,
        numero=formatear_numero(datos.establecimiento, datos.punto_emision, secuencial),
        establecimiento=datos.establecimiento,
        punto_emision=datos.punto_emision,
        secuencial=secuencial,
        fecha_emision=fecha_emision,
        receptor_id=receptor.id,
        receptor_razon_social=receptor.razon_social,
        receptor_identificacion=receptor.identificacion,
        metodo=datos.metodo,
        forma_pago=datos.forma_pago,
        estado_sri="Borrador" if datos.tipo in TIPOS_ELECTRONICOS else "Pendiente",
        validez_dias=datos.validez_dias,
        cod_doc_modificado=datos.cod_doc_modificado,
        num_doc_modificado=datos.num_doc_modificado,
        fecha_doc_modificado=datos.fecha_doc_modificado,
        motivo=datos.motivo,
    )

    # Se calcula con el motor SRI para que la BD y el XML nunca discrepen.
    lineas = [
        Detalle(
            codigo_principal=d.codigo_principal,
            descripcion=d.descripcion,
            cantidad=d.cantidad,
            precio_unitario=d.precio_unitario,
            codigo_iva=d.codigo_iva,
            descuento_porcentaje=d.descuento_porcentaje,
            codigo_auxiliar=d.codigo_auxiliar,
        )
        for d in datos.detalles
    ]

    for entrada, calculado in zip(datos.detalles, lineas, strict=True):
        comprobante.detalles.append(
            DetalleComprobante(
                codigo_principal=entrada.codigo_principal,
                codigo_auxiliar=entrada.codigo_auxiliar,
                descripcion=entrada.descripcion,
                cantidad=calculado.cantidad,
                precio_unitario=calculado.precio_unitario,
                descuento_porcentaje=calculado.descuento_porcentaje,
                descuento=calculado.descuento,
                codigo_iva=calculado.codigo_iva,
                base_imponible=calculado.base_imponible,
                valor_iva=calculado.valor_iva,
                total=calculado.base_imponible + calculado.valor_iva,
            )
        )

    resumen = Factura(
        emisor=Emisor(
            ruc=empresa.ruc,
            razon_social=empresa.razon_social,
            nombre_comercial=empresa.nombre_comercial or "",
            direccion_matriz=empresa.direccion_matriz,
            direccion_establecimiento=empresa.direccion_matriz,
            establecimiento=datos.establecimiento,
            punto_emision=datos.punto_emision,
        ),
        comprador=Comprador(
            "04", receptor.identificacion, receptor.razon_social, receptor.direccion
        ),
        fecha_emision=comprobante.fecha_emision,
        secuencial=secuencial,
        detalles=lineas,
    )

    comprobante.total_sin_impuestos = resumen.total_sin_impuestos
    comprobante.total_descuento = resumen.total_descuento
    comprobante.total_iva = resumen.total_iva
    comprobante.importe_total = resumen.importe_total

    # Ya con el importe calculado se puede contrastar la nota contra su original.
    _validar_nota_contra_original(sesion, datos, receptor, resumen.importe_total)

    sesion.add(comprobante)
    sesion.commit()
    sesion.refresh(comprobante)
    return comprobante


@router.get("/{comprobante_id}", response_model=ComprobanteSalida)
def obtener_comprobante(comprobante_id: int, sesion: Session = Depends(obtener_sesion)):
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")
    return comprobante


@router.post("/{comprobante_id}/anular", response_model=ComprobanteSalida)
def anular_comprobante(
    comprobante_id: int,
    sesion: Session = Depends(obtener_sesion),
    _admin: Usuario = Depends(administrador_actual),
):
    """
    Anula un documento.

    Un comprobante ya autorizado por el SRI no se anula desde aquí: se corrige
    emitiendo una nota de crédito, que es lo que reconoce la administración
    tributaria.
    """
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    if comprobante.estado_sri == "Autorizado":
        raise HTTPException(
            409,
            "Un comprobante autorizado no se anula: emite una nota de crédito para revertirlo.",
        )

    # Un electrónico en "Pendiente" ya fue recibido por el SRI y puede
    # autorizarse minutos después: anularlo aquí dejaría la contabilidad y el
    # SRI en desacuerdo. Hay que consultar su estado primero.
    # (La cotización usa "Pendiente" como estado inicial sin pasar por el SRI,
    # por eso el bloqueo se limita a los tipos electrónicos.)
    if comprobante.estado_sri == "Pendiente" and comprobante.tipo in TIPOS_ELECTRONICOS:
        raise HTTPException(
            409,
            "El comprobante está Pendiente en el SRI y podría autorizarse. "
            "Consulta su estado antes de anularlo.",
        )

    comprobante.estado_sri = "Anulado"
    comprobante.estado_pago = "Anulado"
    sesion.commit()
    sesion.refresh(comprobante)
    return comprobante


@router.post("/{comprobante_id}/emitir", response_model=RespuestaEmision)
def emitir(comprobante_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Firma el comprobante con el certificado configurado y lo envía al SRI.

    Devuelve el comprobante actualizado junto con los mensajes que devolvió el
    SRI: cuando rechaza, el motivo viene ahí y es lo único que permite corregir.
    """
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    try:
        resultado = emitir_comprobante(sesion, comprobante)
    except ErrorEmision as error:
        # El comprobante pudo quedar marcado con el fallo; se conserva.
        sesion.commit()
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(comprobante)

    return RespuestaEmision(
        comprobante=comprobante,
        estado_recepcion=resultado.get("recepcion", ""),
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.post("/{comprobante_id}/consultar", response_model=RespuestaEmision)
def consultar_estado(comprobante_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Reconsulta la autorización.

    El SRI no autoriza de forma síncrona: un comprobante recibido puede quedar
    pendiente y autorizarse minutos más tarde.
    """
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    try:
        resultado = consultar_autorizacion(sesion, comprobante)
    except ErrorEmision as error:
        raise HTTPException(422, str(error)) from error

    sesion.commit()
    sesion.refresh(comprobante)

    return RespuestaEmision(
        comprobante=comprobante,
        estado_recepcion="RECIBIDA",
        estado_autorizacion=resultado.get("autorizacion"),
        mensajes=resultado.get("mensajes", []),
    )


@router.get("/{comprobante_id}/xml")
def descargar_xml(comprobante_id: int, sesion: Session = Depends(obtener_sesion)):
    """Devuelve el XML firmado si ya se emitió, o el XML sin firmar si es borrador."""
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")
    if comprobante.tipo not in TIPOS_ELECTRONICOS:
        raise HTTPException(422, f"Una {comprobante.tipo.lower()} no genera XML para el SRI.")

    if comprobante.xml_firmado:
        contenido = comprobante.xml_firmado.encode("utf-8")
        nombre = f"{comprobante.clave_acceso}.xml"
    else:
        factura = _construir_factura(sesion, comprobante)
        contenido, clave = generar_xml_factura(factura, str(comprobante.id).zfill(8))
        nombre = f"{clave}.xml"

    return Response(
        content=contenido,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{comprobante_id}/ride")
def descargar_ride(comprobante_id: int, sesion: Session = Depends(obtener_sesion)):
    """RIDE: la representación impresa del comprobante electrónico."""
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    empresa = _empresa_actual(sesion)
    factura = _construir_factura(sesion, comprobante)

    pdf = generar_ride(
        factura=factura,
        numero=comprobante.numero,
        clave_acceso=comprobante.clave_acceso or "",
        numero_autorizacion=comprobante.numero_autorizacion,
        fecha_autorizacion=comprobante.fecha_autorizacion,
        ambiente=empresa.ambiente,
        titulo=TITULO_RIDE.get(comprobante.tipo, comprobante.tipo.upper()),
    )

    return StreamingResponse(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="RIDE-{comprobante.numero}.pdf"'},
    )


@router.get("/correo/estado")
def estado_correo():
    """
    ¿Está configurado el envío por correo?

    La interfaz lo consulta para deshabilitar el botón con una explicación en
    vez de dejar que el usuario lo pulse y reciba un error de red.
    """
    from ..servicios.correo import configuracion, esta_configurado

    ajustes = configuracion()
    return {
        "configurado": esta_configurado(),
        "servidor": ajustes["servidor"],
        "remitente": ajustes["remitente"] or ajustes["usuario"],
    }


@router.post("/{comprobante_id}/enviar", response_model=RespuestaEnvio)
def enviar_por_correo(
    comprobante_id: int,
    datos: EnvioCorreo | None = None,
    sesion: Session = Depends(obtener_sesion),
):
    """
    Manda el comprobante al receptor con el XML y el RIDE adjuntos.

    Solo se envían comprobantes **autorizados**: mandar un borrador o un
    rechazado le entrega al cliente un documento que no existe ante el SRI.
    """
    from ..servicios.correo import ErrorCorreo, enviar_comprobante

    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    if comprobante.tipo not in TIPOS_ELECTRONICOS:
        raise HTTPException(422, f"Una {comprobante.tipo.lower()} no se envía como comprobante.")

    if comprobante.estado_sri != "Autorizado":
        raise HTTPException(
            422,
            f"El comprobante está en estado {comprobante.estado_sri}. Solo se envían "
            "los autorizados: mandar otro le entrega al cliente un documento que el "
            "SRI no reconoce.",
        )
    if not comprobante.xml_firmado:
        raise HTTPException(422, "El comprobante no tiene XML firmado guardado.")

    empresa = _empresa_actual(sesion)
    receptor = comprobante.receptor

    destinatario = (datos.destinatario if datos and datos.destinatario else None) or (
        receptor.correo if receptor else None
    )

    factura = _construir_factura(sesion, comprobante)
    pdf = generar_ride(
        factura=factura,
        numero=comprobante.numero,
        clave_acceso=comprobante.clave_acceso or "",
        numero_autorizacion=comprobante.numero_autorizacion,
        fecha_autorizacion=comprobante.fecha_autorizacion,
        ambiente=empresa.ambiente,
        titulo=TITULO_RIDE.get(comprobante.tipo, comprobante.tipo.upper()),
    )

    try:
        enviar_comprobante(
            destinatario=destinatario or "",
            razon_social=comprobante.receptor_razon_social,
            tipo=comprobante.tipo,
            numero=comprobante.numero,
            autorizacion=comprobante.numero_autorizacion,
            xml=comprobante.xml_firmado.encode("utf-8"),
            pdf=pdf.getvalue(),
            emisor=empresa.razon_social,
            copia=datos.copia if datos else None,
        )
    except ErrorCorreo as error:
        raise HTTPException(422, str(error)) from error

    return RespuestaEnvio(
        enviado=True,
        destinatario=destinatario or "",
        mensaje=f"Comprobante {comprobante.numero} enviado a {destinatario}.",
    )
