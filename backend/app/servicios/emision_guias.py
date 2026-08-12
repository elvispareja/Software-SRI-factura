"""
Emisión de guías de remisión al SRI.

Comparte con `emision.py` el certificado, el firmador y los WebServices; lo que
cambia es cómo se arma el XML, porque la guía no lleva importes. Para no
duplicar la parte delicada, la carga del certificado y la interpretación de la
respuesta del SRI se reutilizan desde allí.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Empresa, Establecimiento, GuiaRemision as GuiaEnBase
from ..sri.firma import ErrorFirma, firmar_xml
from ..sri.identificacion import codigo_sri
from ..sri.modelos import Emisor
from ..sri.servicios import emitir as transmitir_al_sri
from ..sri.xml_guia_remision import Destinatario, GuiaRemision, ItemGuia, generar_xml_guia_remision
from .emision import ESTADOS_EMITIBLES, ErrorEmision, abrir_certificado

registro = logging.getLogger(__name__)


def _emisor(sesion: Session, empresa: Empresa, guia: GuiaEnBase) -> Emisor:
    establecimiento = sesion.scalar(
        select(Establecimiento).where(
            Establecimiento.empresa_id == empresa.id,
            Establecimiento.codigo == guia.establecimiento,
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
        establecimiento=guia.establecimiento,
        punto_emision=guia.punto_emision,
        obligado_contabilidad=empresa.obligado_contabilidad,
        contribuyente_especial=empresa.contribuyente_especial,
    )


def construir_modelo(sesion: Session, guia: GuiaEnBase) -> GuiaRemision:
    """
    Traduce la fila de base de datos al modelo del motor SRI.

    Separado de `construir_xml` porque el RIDE necesita el mismo modelo sin
    llegar a generar XML: así la impresión y lo que se transmite no pueden
    divergir.
    """
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    transportista = guia.transportista
    if transportista is None:
        raise ErrorEmision("La guía no tiene transportista asignado.")

    # El SRI exige fecha fin; si no se indicó, el traslado es de un solo día.
    fecha_fin = guia.fecha_fin or guia.fecha_inicio

    destinatario = Destinatario(
        identificacion=transportista.identificacion,
        razon_social=transportista.razon_social,
        direccion=guia.direccion_llegada,
        motivo_traslado=guia.motivo_traslado,
        ruta=guia.ruta,
        documento_aduanero=guia.documento_aduanero,
        items=[
            ItemGuia(
                codigo_interno=item.codigo or "SIN-COD",
                descripcion=item.descripcion,
                cantidad=item.cantidad,
            )
            for item in guia.items
        ],
    )

    return GuiaRemision(
        emisor=_emisor(sesion, empresa, guia),
        fecha_emision=guia.fecha_inicio,
        secuencial=guia.secuencial,
        transportista_tipo_identificacion=codigo_sri(transportista.tipo_identificacion),
        transportista_identificacion=transportista.identificacion,
        transportista_razon_social=transportista.razon_social,
        placa=guia.placa,
        direccion_partida=guia.direccion_partida,
        fecha_inicio=guia.fecha_inicio,
        fecha_fin=fecha_fin,
        destinatarios=[destinatario],
        ambiente=empresa.ambiente,
    )


def construir_xml(sesion: Session, guia: GuiaEnBase) -> tuple[bytes, str]:
    modelo = construir_modelo(sesion, guia)
    return generar_xml_guia_remision(modelo, str(guia.id).zfill(8))


def emitir_guia(sesion: Session, guia: GuiaEnBase) -> dict:
    """Firma y transmite la guía. El llamador hace el commit."""
    if guia.estado_sri == "Autorizado":
        raise ErrorEmision(
            f"La guía {guia.numero} ya está autorizada ({guia.numero_autorizacion})."
        )
    if guia.estado_sri not in ESTADOS_EMITIBLES:
        raise ErrorEmision(f"La guía está en estado {guia.estado_sri} y no se puede emitir.")

    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    firmante = abrir_certificado(sesion, empresa)
    xml, clave_acceso = construir_xml(sesion, guia)

    try:
        xml_firmado = firmar_xml(xml, firmante, identificador=guia.id)
    except ErrorFirma as error:
        guia.estado_sri = "Error"
        guia.mensajes_sri = json.dumps([{"mensaje": str(error)}], ensure_ascii=False)
        raise ErrorEmision(f"No se pudo firmar la guía: {error}") from error

    # Igual que en los comprobantes: se guarda antes de transmitir.
    guia.clave_acceso = clave_acceso
    guia.xml_firmado = xml_firmado.decode("utf-8")

    try:
        recepcion, autorizacion = transmitir_al_sri(xml_firmado, clave_acceso, empresa.ambiente)
    except Exception as error:  # noqa: BLE001
        registro.exception("Fallo transmitiendo la guía %s", guia.numero)
        guia.estado_sri = "Error"
        guia.mensajes_sri = json.dumps(
            [{"mensaje": f"No se pudo contactar al SRI: {error}"}], ensure_ascii=False
        )
        raise ErrorEmision(
            "No se pudo contactar con los servidores del SRI. "
            "La guía quedó firmada; vuelve a intentarlo."
        ) from error

    mensajes = list(recepcion.mensajes)

    if not recepcion.recibida:
        guia.estado_sri = "Devuelto"
        guia.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)
        return {"estado": guia.estado_sri, "recepcion": recepcion.estado, "mensajes": mensajes}

    mensajes += list(autorizacion.mensajes) if autorizacion else []

    if autorizacion and autorizacion.autorizada:
        guia.estado_sri = "Autorizado"
        guia.numero_autorizacion = autorizacion.numero_autorizacion
        guia.fecha_autorizacion = autorizacion.fecha_autorizacion
    elif autorizacion:
        guia.estado_sri = "Rechazado" if autorizacion.estado == "NO AUTORIZADO" else "Pendiente"
    else:
        guia.estado_sri = "Pendiente"

    guia.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)

    return {
        "estado": guia.estado_sri,
        "recepcion": recepcion.estado,
        "autorizacion": autorizacion.estado if autorizacion else None,
        "numero_autorizacion": guia.numero_autorizacion,
        "mensajes": mensajes,
    }
