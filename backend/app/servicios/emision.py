"""
Emisión de comprobantes electrónicos al SRI.

Une lo que hasta ahora estaba suelto: el motor de XML, el firmador XAdES-BES,
el certificado guardado en Configuraciones y los WebServices del SRI.

El flujo completo es:

    Borrador → XML → firma con el .p12 → recepción → autorización

Dos decisiones que gobiernan el diseño:

1. **La clave de acceso se calcula una sola vez y se guarda.** Es el
   identificador con el que se consulta la autorización; si se recalculara en
   cada intento con un código numérico distinto, un reintento consultaría una
   clave que el SRI nunca recibió.

2. **Un comprobante autorizado no se vuelve a enviar.** Reenviarlo produce
   "CLAVE ACCESO REGISTRADA" y, si el estado local se pisara, se perdería el
   número de autorización ya obtenido.
"""

from __future__ import annotations

import json
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Comprobante, Empresa, Establecimiento, FirmaElectronica
from ..sri.firma import ErrorFirma, cargar_p12, firmar_xml
from ..sri.identificacion import codigo_sri
from ..sri.modelos import Comprador, Detalle, Emisor, Factura, Pago
from ..sri.servicios import emitir as transmitir_al_sri
from ..sri.xml_factura import generar_xml_factura
from ..sri.xml_nota_credito import NotaCredito, generar_xml_nota_credito
from ..sri.xml_nota_debito import MotivoDebito, NotaDebito, generar_xml_nota_debito
from .cifrado import ErrorCifrado, descifrar

registro = logging.getLogger(__name__)

# Estados desde los que tiene sentido (re)intentar la emisión.
ESTADOS_EMITIBLES = {"Borrador", "Rechazado", "Devuelto", "Error"}

TIPOS_CON_XML = {
    "Factura",
    "Nota de Crédito",
    "Nota de Débito",
    "Liquidación de Compra",
    "Nota de Venta",
}

# Tipo de comprobante del SRI (tabla 3) para los que comparten la estructura
# de la factura. La liquidación de compra es el `03`: emitirla como `01` la
# registraría como una venta en vez de una compra.
COD_DOC_POR_TIPO = {
    "Factura": "01",
    "Liquidación de Compra": "03",
    "Nota de Venta": "01",
}


class ErrorEmision(Exception):
    """La emisión no se pudo completar. El mensaje es apto para el usuario."""


def _firma_activa(sesion: Session, empresa: Empresa) -> FirmaElectronica:
    firma = sesion.scalar(
        select(FirmaElectronica).where(
            FirmaElectronica.empresa_id == empresa.id, FirmaElectronica.activa.is_(True)
        )
    )
    if firma is None:
        raise ErrorEmision(
            "No hay certificado de firma configurado. "
            "Cárgalo en Configuraciones → Firma Electrónica."
        )

    if firma.valida_hasta < date.today():
        raise ErrorEmision(
            f"El certificado expiró el {firma.valida_hasta:%d/%m/%Y}. "
            "Renuévalo antes de emitir."
        )
    if firma.valida_desde > date.today():
        raise ErrorEmision(
            f"El certificado aún no es válido; empieza a regir el {firma.valida_desde:%d/%m/%Y}."
        )

    return firma


def abrir_certificado(sesion: Session, empresa: Empresa):
    """
    Descifra la contraseña y abre el certificado activo.

    Compartido con la emisión de guías. El `.p12` se escribe a un temporal
    porque `cargar_p12` lee de disco, y se borra en el `finally`: el
    certificado no debe quedar en el sistema de archivos.
    """
    firma = _firma_activa(sesion, empresa)

    try:
        contrasena = descifrar(firma.contrasena_cifrada)
    except ErrorCifrado as error:
        raise ErrorEmision(str(error)) from error

    import os
    import tempfile

    ruta_temporal = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as temporal:
            temporal.write(firma.contenido)
            ruta_temporal = temporal.name
        return cargar_p12(ruta_temporal, contrasena)
    except ErrorFirma as error:
        raise ErrorEmision(f"No se pudo abrir el certificado: {error}") from error
    finally:
        if ruta_temporal:
            os.unlink(ruta_temporal)


def _emisor(sesion: Session, empresa: Empresa, comprobante: Comprobante) -> Emisor:
    establecimiento = sesion.scalar(
        select(Establecimiento).where(
            Establecimiento.empresa_id == empresa.id,
            Establecimiento.codigo == comprobante.establecimiento,
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
        establecimiento=comprobante.establecimiento,
        punto_emision=comprobante.punto_emision,
        obligado_contabilidad=empresa.obligado_contabilidad,
        contribuyente_especial=empresa.contribuyente_especial,
        agente_retencion=empresa.agente_retencion,
        contribuyente_rimpe=empresa.contribuyente_rimpe,
    )


def _comprador(comprobante: Comprobante) -> Comprador:
    receptor = comprobante.receptor
    return Comprador(
        tipo_identificacion=codigo_sri(
            receptor.tipo_identificacion if receptor else "Consumidor Final"
        ),
        identificacion=comprobante.receptor_identificacion,
        razon_social=comprobante.receptor_razon_social,
        direccion=receptor.direccion if receptor else "",
        correo=receptor.correo if receptor else None,
    )


def _detalles(comprobante: Comprobante) -> list[Detalle]:
    return [
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


def _codigo_numerico(comprobante: Comprobante) -> str:
    """
    Ocho dígitos estables para este comprobante.

    Se deriva del id, así que un reintento genera exactamente la misma clave de
    acceso y consulta la autorización correcta.
    """
    return str(comprobante.id).zfill(8)


def construir_xml(sesion: Session, comprobante: Comprobante) -> tuple[bytes, str]:
    """Genera el XML sin firmar y su clave de acceso, según el tipo."""
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    emisor = _emisor(sesion, empresa, comprobante)
    comprador = _comprador(comprobante)
    detalles = _detalles(comprobante)
    codigo = _codigo_numerico(comprobante)

    if comprobante.tipo == "Nota de Crédito":
        nota = NotaCredito(
            emisor=emisor,
            comprador=comprador,
            fecha_emision=comprobante.fecha_emision,
            secuencial=comprobante.secuencial,
            detalles=detalles,
            motivo=comprobante.motivo or "Modificación de comprobante",
            cod_doc_modificado=comprobante.cod_doc_modificado or "01",
            num_doc_modificado=comprobante.num_doc_modificado or "",
            fecha_emision_doc_sustento=(
                comprobante.fecha_doc_modificado or comprobante.fecha_emision
            ),
            ambiente=empresa.ambiente,
        )
        return generar_xml_nota_credito(nota, codigo)

    if comprobante.tipo == "Nota de Débito":
        # La nota de débito no lleva detalles sino motivos: lo que se cobra de
        # más es un concepto, no mercadería. Cada línea capturada en la
        # pantalla se traduce a un motivo con su importe.
        nota_debito = NotaDebito(
            emisor=emisor,
            comprador=comprador,
            fecha_emision=comprobante.fecha_emision,
            secuencial=comprobante.secuencial,
            motivos=[
                MotivoDebito(razon=linea.descripcion, valor=linea.base_imponible)
                for linea in detalles
            ],
            cod_doc_modificado=comprobante.cod_doc_modificado or "01",
            num_doc_modificado=comprobante.num_doc_modificado or "",
            fecha_emision_doc_sustento=(
                comprobante.fecha_doc_modificado or comprobante.fecha_emision
            ),
            # Todas las líneas comparten tarifa en el XML de la nota de débito;
            # se toma la de la primera, que es la que la pantalla aplica.
            codigo_iva=detalles[0].codigo_iva if detalles else "4",
            ambiente=empresa.ambiente,
        )
        return generar_xml_nota_debito(nota_debito, codigo)

    factura = Factura(
        emisor=emisor,
        comprador=comprador,
        fecha_emision=comprobante.fecha_emision,
        secuencial=comprobante.secuencial,
        detalles=detalles,
        ambiente=empresa.ambiente,
    )
    factura.pagos = [Pago(forma_pago=comprobante.forma_pago, total=factura.importe_total)]

    # La liquidación de compra usa la misma estructura que la factura pero es
    # el tipo 03. Emitirla como 01 la registraría ante el SRI como una venta
    # en vez de una compra.
    return generar_xml_factura(factura, codigo, COD_DOC_POR_TIPO.get(comprobante.tipo, "01"))


def emitir_comprobante(sesion: Session, comprobante: Comprobante) -> dict:
    """
    Firma y transmite el comprobante al SRI.

    Devuelve un resumen de lo ocurrido; el comprobante queda actualizado en la
    sesión (el llamador hace el commit).
    """
    if comprobante.tipo not in TIPOS_CON_XML:
        raise ErrorEmision(f"Una {comprobante.tipo.lower()} no se transmite al SRI.")

    if comprobante.estado_sri == "Autorizado":
        raise ErrorEmision(
            f"El comprobante {comprobante.numero} ya está autorizado "
            f"({comprobante.numero_autorizacion}). Para revertirlo, emite una nota de crédito."
        )
    if comprobante.estado_sri not in ESTADOS_EMITIBLES:
        raise ErrorEmision(
            f"El comprobante está en estado {comprobante.estado_sri} y no se puede emitir."
        )

    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    firmante = abrir_certificado(sesion, empresa)
    xml, clave_acceso = construir_xml(sesion, comprobante)

    try:
        xml_firmado = firmar_xml(xml, firmante, identificador=comprobante.id)
    except ErrorFirma as error:
        comprobante.estado_sri = "Error"
        comprobante.mensajes_sri = json.dumps([{"mensaje": str(error)}], ensure_ascii=False)
        raise ErrorEmision(f"No se pudo firmar el comprobante: {error}") from error

    # Se guarda antes de transmitir: si la red falla, el XML firmado no se
    # pierde y el reintento no tiene que volver a firmar.
    comprobante.clave_acceso = clave_acceso
    comprobante.xml_firmado = xml_firmado.decode("utf-8")

    try:
        recepcion, autorizacion = transmitir_al_sri(xml_firmado, clave_acceso, empresa.ambiente)
    except Exception as error:  # noqa: BLE001 - la red falla de muchas formas
        registro.exception("Fallo transmitiendo el comprobante %s", comprobante.numero)
        comprobante.estado_sri = "Error"
        comprobante.mensajes_sri = json.dumps(
            [{"mensaje": f"No se pudo contactar al SRI: {error}"}], ensure_ascii=False
        )
        raise ErrorEmision(
            "No se pudo contactar con los servidores del SRI. "
            "El comprobante quedó firmado; vuelve a intentarlo."
        ) from error

    mensajes = list(recepcion.mensajes)

    if not recepcion.recibida:
        comprobante.estado_sri = "Devuelto"
        comprobante.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)
        return {
            "estado": comprobante.estado_sri,
            "recepcion": recepcion.estado,
            "autorizacion": None,
            "mensajes": mensajes,
        }

    mensajes += list(autorizacion.mensajes) if autorizacion else []

    if autorizacion and autorizacion.autorizada:
        comprobante.estado_sri = "Autorizado"
        comprobante.numero_autorizacion = autorizacion.numero_autorizacion
        comprobante.fecha_autorizacion = autorizacion.fecha_autorizacion
    elif autorizacion:
        # El SRI puede tardar: "EN PROCESO" no es un rechazo.
        comprobante.estado_sri = (
            "Rechazado" if autorizacion.estado == "NO AUTORIZADO" else "Pendiente"
        )
    else:
        comprobante.estado_sri = "Pendiente"

    comprobante.mensajes_sri = json.dumps(mensajes, ensure_ascii=False)

    return {
        "estado": comprobante.estado_sri,
        "recepcion": recepcion.estado,
        "autorizacion": autorizacion.estado if autorizacion else None,
        "numero_autorizacion": comprobante.numero_autorizacion,
        "mensajes": mensajes,
    }


def consultar_autorizacion(sesion: Session, documento) -> dict:
    """
    Reconsulta el estado de un documento ya recibido por el SRI.

    Necesario porque la autorización no es síncrona: un comprobante puede
    quedar "Pendiente" y autorizarse minutos después.

    Sirve igual para comprobantes, guías y retenciones: lo único que necesita
    del documento son `clave_acceso`, `estado_sri`, `numero_autorizacion`,
    `fecha_autorizacion` y `mensajes_sri`, que los tres tienen. Duplicar esta
    función por tipo habría triplicado la interpretación de la respuesta, que
    es justo la parte fácil de equivocar.
    """
    if not documento.clave_acceso:
        raise ErrorEmision("El documento aún no se ha transmitido al SRI.")

    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    if empresa is None:
        raise ErrorEmision("No hay empresa configurada.")

    from ..sri.servicios import consultar_autorizacion as consultar

    try:
        respuesta = consultar(documento.clave_acceso, empresa.ambiente)
    except Exception as error:  # noqa: BLE001
        raise ErrorEmision(f"No se pudo consultar al SRI: {error}") from error

    if respuesta.autorizada:
        documento.estado_sri = "Autorizado"
        documento.numero_autorizacion = respuesta.numero_autorizacion
        documento.fecha_autorizacion = respuesta.fecha_autorizacion
    elif respuesta.estado == "NO AUTORIZADO":
        documento.estado_sri = "Rechazado"

    documento.mensajes_sri = json.dumps(respuesta.mensajes, ensure_ascii=False)

    return {
        "estado": documento.estado_sri,
        "autorizacion": respuesta.estado,
        "numero_autorizacion": documento.numero_autorizacion,
        "mensajes": respuesta.mensajes,
    }
