"""
Emisión de comprobantes de retención al SRI.

Mismo esqueleto que `emision.py` y `emision_guias.py` —certificado, firma,
recepción, autorización— sobre el XML de retención versión 1.0.0.

Una particularidad: en la 1.0.0 el documento sustento va repetido dentro de
cada `<impuesto>`, no una sola vez. Como en la práctica una retención se emite
contra un único documento, aquí se guarda una vez en la cabecera y se replica
al construir el XML.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Empresa, Establecimiento, Retencion as RetencionEnBase
from ..sri.firma import ErrorFirma, firmar_xml
from ..sri.identificacion import codigo_sri
from ..sri.modelos import Comprador, Emisor
from ..sri.servicios import emitir as transmitir_al_sri
from ..sri.xml_retencion import DetalleRetencion, Retencion, generar_xml_retencion
from .emision import ESTADOS_EMITIBLES, ErrorEmision, abrir_certificado

registro = logging.getLogger(__name__)


def _emisor(sesion: Session, empresa: Empresa, retencion: RetencionEnBase) -> Emisor:
    establecimiento = sesion.scalar(
        select(Establecimiento).where(
            Establecimiento.empresa_id == empresa.id,
            Establecimiento.codigo == retencion.establecimiento,
        )
    )

    return Emisor(
        ruc=empresa.ruc,
        razon_social=empresa.razon_social,
        nombre_comercial=empresa.nombre_comercial or "",
        direccion_matriz=empresa.direccion_matriz,
        direccion_establecimiento=(
            establecimiento.direccion if establecimiento else empresa.direccion_matriz
        ),
        establecimiento=retencion.establecimiento,
        punto_emision=retencion.punto_emision,
        obligado_contabilidad=empresa.obligado_contabilidad,
        contribuyente_especial=empresa.contribuyente_especial,
        agente_retencion=empresa.agente_retencion,
        contribuyente_rimpe=empresa.contribuyente_rimpe,
    )


def construir_modelo(sesion: Session, retencion: RetencionEnBase) -> Retencion:
    """
    Traduce la fila de base de datos al modelo del motor SRI.

    Separado de `construir_xml` porque el RIDE necesita el mismo modelo sin
    llegar a generar XML: así la impresión y lo que se transmite no pueden
    divergir.
    """
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    sujeto = Comprador(
        tipo_identificacion=codigo_sri(retencion.sujeto_tipo_identificacion),
        identificacion=retencion.sujeto_identificacion,
        razon_social=retencion.sujeto_razon_social,
        direccion=retencion.sujeto.direccion if retencion.sujeto else "",
        correo=retencion.sujeto.correo if retencion.sujeto else None,
    )

    return Retencion(
        emisor=_emisor(sesion, empresa, retencion),
        sujeto_retenido=sujeto,
        fecha_emision=retencion.fecha_emision,
        secuencial=retencion.secuencial,
        periodo_fiscal=retencion.periodo_fiscal,
        detalles=[
            DetalleRetencion(
                codigo_impuesto=detalle.codigo_impuesto,
                codigo_retencion=detalle.codigo_retencion,
                base_imponible=detalle.base_imponible,
                porcentaje_retener=detalle.porcentaje_retener,
                cod_doc_sustento=retencion.cod_doc_sustento,
                num_doc_sustento=retencion.num_doc_sustento,
                fecha_emision_doc_sustento=retencion.fecha_doc_sustento,
            )
            for detalle in retencion.detalles
        ],
        ambiente=empresa.ambiente,
    )


def construir_xml(sesion: Session, retencion: RetencionEnBase) -> tuple[bytes, str]:
    modelo = construir_modelo(sesion, retencion)
    return generar_xml_retencion(modelo, str(retencion.id).zfill(8))


def emitir_retencion(sesion: Session, retencion: RetencionEnBase) -> dict:
    """Firma y transmite la retención. El llamador hace el commit."""
    if retencion.estado_sri == "Autorizado":
        raise ErrorEmision(
            f"La retención {retencion.numero} ya está autorizada "
            f"({retencion.numero_autorizacion})."
        )
    if retencion.estado_sri not in ESTADOS_EMITIBLES:
        raise ErrorEmision(
            f"La retención está en estado {retencion.estado_sri} y no se puede emitir."
        )

    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    firmante = abrir_certificado(sesion, empresa)
    xml, clave_acceso = construir_xml(sesion, retencion)

    try:
        xml_firmado = firmar_xml(xml, firmante, identificador=retencion.id)
    except ErrorFirma as error:
        retencion.estado_sri = "Error"
        retencion.mensajes_sri = json.dumps([{"mensaje": str(error)}], ensure_ascii=False)
        raise ErrorEmision(f"No se pudo firmar la retención: {error}") from error

    retencion.clave_acceso = clave_acceso
    retencion.xml_firmado = xml_firmado.decode("utf-8")

    try:
        recepcion, autorizacion = transmitir_al_sri(xml_firmado, clave_acceso, empresa.ambiente)
    except Exception as error:  # noqa: BLE001
        registro.exception("Fallo transmitiendo la retención %s", retencion.numero)
        retencion.estado_sri = "Error"
        retencion.mensajes_sri = json.dumps(
            [{"mensaje": f"No se pudo contactar al SRI: {error}"}], ensure_ascii=False
        )
        raise ErrorEmision(
            "No se pudo contactar con los servidores del SRI. "
            "La retención quedó firmada; vuelve a intentarlo."
        ) from error

    mensajes = list(recepcion.mensajes)

    if not recepcion.recibida:
        retencion.estado_sri = "Devuelto"
        retencion.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)
        return {
            "estado": retencion.estado_sri,
            "recepcion": recepcion.estado,
            "mensajes": mensajes,
        }

    mensajes += list(autorizacion.mensajes) if autorizacion else []

    if autorizacion and autorizacion.autorizada:
        retencion.estado_sri = "Autorizado"
        retencion.numero_autorizacion = autorizacion.numero_autorizacion
        retencion.fecha_autorizacion = autorizacion.fecha_autorizacion
    elif autorizacion:
        retencion.estado_sri = (
            "Rechazado" if autorizacion.estado == "NO AUTORIZADO" else "Pendiente"
        )
    else:
        retencion.estado_sri = "Pendiente"

    retencion.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)

    return {
        "estado": retencion.estado_sri,
        "recepcion": recepcion.estado,
        "autorizacion": autorizacion.estado if autorizacion else None,
        "numero_autorizacion": retencion.numero_autorizacion,
        "mensajes": mensajes,
    }
