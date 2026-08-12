"""
Orquestador del asistente: une la extracción con IA y el motor de facturación.

Regla de diseño: **el modelo nunca emite un comprobante por su cuenta.** Extrae
datos, el sistema los valida contra el SRI y calcula los totales, y solo tras una
confirmación explícita del usuario se emite. Un LLM que factura sin confirmar
convierte una alucinación en un documento tributario.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..modelos_db import Comprobante, DetalleComprobante, Empresa, Establecimiento, PuntoEmision, Receptor
from ..servicios.emision import ErrorEmision, emitir_comprobante
from ..servicios.secuenciales import formatear_numero, reservar_secuencial
from ..sri.identificacion import validar_identificacion
from ..sri.modelos import Comprador, Detalle, Emisor, Factura
from .extraccion import ErrorExtraccion, extraer_factura, normalizar_detalles

registro = logging.getLogger(__name__)

# Cuánto vive una conversación sin actividad antes de olvidarse.
MINUTOS_VIGENCIA_CONVERSACION = 30

CONFIRMACIONES = {"si", "sí", "confirmo", "dale", "ok", "correcto", "emitir", "emite", "listo"}
CANCELACIONES = {"no", "cancelar", "cancela", "olvidalo", "olvídalo", "detente"}


@dataclass
class Conversacion:
    """Estado de un chat. En memoria por ahora; migrar a Redis al escalar."""

    telefono: str
    historial: list[dict] = field(default_factory=list)
    borrador: dict | None = None
    actualizada: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def expirada(self) -> bool:
        limite = timedelta(minutes=MINUTOS_VIGENCIA_CONVERSACION)
        return datetime.now(timezone.utc) - self.actualizada > limite


_conversaciones: dict[str, Conversacion] = {}


def obtener_conversacion(telefono: str) -> Conversacion:
    conversacion = _conversaciones.get(telefono)

    if conversacion is None or conversacion.expirada():
        conversacion = Conversacion(telefono=telefono)
        _conversaciones[telefono] = conversacion

    return conversacion


def _formatear_resumen(borrador: dict) -> str:
    lineas = [
        "Esto es lo que voy a emitir:",
        "",
        f"Cliente: {borrador['cliente_nombre']}",
        f"Identificación: {borrador['cliente_identificacion']}",
        "",
    ]

    for detalle in borrador["detalles"]:
        lineas.append(
            f"• {detalle['descripcion']} — {detalle['cantidad']} x ${detalle['precio_unitario']:.2f}"
        )

    lineas += [
        "",
        f"Subtotal: ${borrador['total_sin_impuestos']:.2f}",
        f"IVA: ${borrador['total_iva']:.2f}",
        f"TOTAL: ${borrador['importe_total']:.2f}",
        "",
        "¿Confirmo y la envío al SRI? Responde *sí* o *no*.",
    ]

    return "\n".join(lineas)


def _empresa(sesion: Session) -> Empresa | None:
    return sesion.scalars(select(Empresa).limit(1)).first()


def _buscar_o_crear_receptor(sesion: Session, cliente: dict) -> Receptor | None:
    """
    Busca el receptor por identificación; lo crea si no existe.

    No se crea sin dirección: el XML del SRI la exige, y un receptor a medias
    haría fallar la emisión más adelante con un error mucho menos claro.
    """
    identificacion = (cliente.get("identificacion") or "").strip()
    if not identificacion:
        return None

    existente = sesion.scalar(select(Receptor).where(Receptor.identificacion == identificacion))
    if existente:
        return existente

    tipo = cliente.get("tipo_identificacion") or "RUC"
    if not validar_identificacion(tipo, identificacion).es_valida:
        return None

    receptor = Receptor(
        tipo_identificacion=tipo,
        identificacion=identificacion,
        razon_social=(cliente.get("nombre") or "").strip().upper() or "SIN NOMBRE",
        correo=cliente.get("correo"),
        # Se marca explícitamente para que el usuario la complete antes de emitir.
        direccion="",
    )
    sesion.add(receptor)
    sesion.flush()
    return receptor


def _preparar_borrador(sesion: Session, extraccion, receptor: Receptor) -> dict | None:
    """Calcula los totales con el motor SRI, no con lo que dijo el modelo."""
    empresa = _empresa(sesion)
    if empresa is None:
        return None

    detalles = normalizar_detalles(
        {"detalles": [d for d in extraccion.detalles]}
    )
    if not detalles:
        return None

    lineas = [
        Detalle(
            codigo_principal="IA-001",
            descripcion=detalle["descripcion"],
            cantidad=detalle["cantidad"],
            precio_unitario=detalle["precio_unitario"],
            codigo_iva=detalle["codigo_iva"],
        )
        for detalle in detalles
    ]

    factura = Factura(
        emisor=Emisor(
            ruc=empresa.ruc,
            razon_social=empresa.razon_social,
            nombre_comercial=empresa.nombre_comercial or "",
            direccion_matriz=empresa.direccion_matriz,
            direccion_establecimiento=empresa.direccion_matriz,
            establecimiento="001",
            punto_emision="001",
        ),
        comprador=Comprador(
            tipo_identificacion="04",
            identificacion=receptor.identificacion,
            razon_social=receptor.razon_social,
            direccion=receptor.direccion or "S/N",
        ),
        fecha_emision=date.today(),
        secuencial=0,
        detalles=lineas,
    )

    return {
        "cliente_id": receptor.id,
        "cliente_nombre": receptor.razon_social,
        "cliente_identificacion": receptor.identificacion,
        "detalles": [
            {
                "descripcion": linea.descripcion,
                "cantidad": linea.cantidad,
                "precio_unitario": linea.precio_unitario,
                "codigo_iva": linea.codigo_iva,
            }
            for linea in lineas
        ],
        "total_sin_impuestos": factura.total_sin_impuestos,
        "total_descuento": factura.total_descuento,
        "total_iva": factura.total_iva,
        "importe_total": factura.importe_total,
    }


def _crear_comprobante(sesion: Session, empresa: Empresa, borrador: dict) -> Comprobante | None:
    """
    Persiste la factura confirmada.

    Numera con `reservar_secuencial`, el mismo camino que usa la pantalla de
    facturación: si el asistente llevara su propio contador, dos facturas del
    mismo punto de emisión podrían salir con el mismo número y el SRI las
    rechazaría.
    """
    punto = sesion.scalar(
        select(PuntoEmision)
        .join(Establecimiento)
        .where(Establecimiento.empresa_id == empresa.id)
        .with_for_update()
    )
    if punto is None:
        return None

    establecimiento = punto.establecimiento
    secuencial = reservar_secuencial(sesion, punto, "Factura")

    comprobante = Comprobante(
        tipo="Factura",
        numero=formatear_numero(establecimiento.codigo, punto.codigo, secuencial),
        establecimiento=establecimiento.codigo,
        punto_emision=punto.codigo,
        secuencial=secuencial,
        fecha_emision=date.today(),
        receptor_id=borrador["cliente_id"],
        receptor_razon_social=borrador["cliente_nombre"],
        receptor_identificacion=borrador["cliente_identificacion"],
        total_sin_impuestos=borrador["total_sin_impuestos"],
        total_descuento=borrador["total_descuento"],
        total_iva=borrador["total_iva"],
        importe_total=borrador["importe_total"],
        estado_sri="Borrador",
    )

    # Se recalcula línea a línea con el motor SRI en vez de multiplicar a mano:
    # así el IVA de cada detalle cuadra con el total que ya se le mostró al
    # usuario en el resumen.
    for detalle in borrador["detalles"]:
        linea = Detalle(
            codigo_principal="IA-001",
            descripcion=detalle["descripcion"],
            cantidad=detalle["cantidad"],
            precio_unitario=detalle["precio_unitario"],
            codigo_iva=detalle["codigo_iva"],
        )
        comprobante.detalles.append(
            DetalleComprobante(
                codigo_principal=linea.codigo_principal,
                descripcion=linea.descripcion,
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                codigo_iva=linea.codigo_iva,
                descuento=linea.descuento,
                base_imponible=linea.base_imponible,
                valor_iva=linea.valor_iva,
                total=linea.base_imponible + linea.valor_iva,
            )
        )

    sesion.add(comprobante)
    sesion.flush()
    return comprobante


def _emitir(sesion: Session, borrador: dict) -> str:
    """Crea la factura y la transmite al SRI. Devuelve el mensaje al usuario."""
    empresa = _empresa(sesion)
    if empresa is None:
        return "No hay empresa configurada. Complétala en Configuraciones antes de facturar."

    comprobante = _crear_comprobante(sesion, empresa, borrador)
    if comprobante is None:
        return "No hay puntos de emisión configurados. Créalos en Configuraciones."

    # El comprobante se guarda antes de intentar la transmisión: si el SRI no
    # responde, la factura ya existe y se puede reintentar desde el listado.
    sesion.commit()

    try:
        resultado = emitir_comprobante(sesion, comprobante)
        sesion.commit()
    except ErrorEmision as error:
        sesion.commit()  # Conserva el estado y los mensajes del fallo.
        return (
            f"Guardé la factura {comprobante.numero} por "
            f"${borrador['importe_total']:.2f}, pero no se pudo enviar al SRI:\n\n"
            f"{error}\n\n"
            "Queda pendiente; puedes reintentarlo desde el sistema."
        )

    encabezado = (
        f"Listo. Factura {comprobante.numero} por ${borrador['importe_total']:.2f}."
    )

    if resultado["estado"] == "Autorizado":
        return (
            f"{encabezado}\n\n"
            f"✅ Autorizada por el SRI.\n"
            f"Autorización: {resultado['numero_autorizacion']}"
        )

    if resultado["estado"] == "Pendiente":
        return (
            f"{encabezado}\n\n"
            "El SRI la recibió y aún la está procesando. "
            "Te confirmo la autorización en cuanto la consulte."
        )

    motivos = "\n".join(
        f"• {mensaje.get('mensaje', '')}" for mensaje in resultado.get("mensajes", [])
    )
    return (
        f"{encabezado}\n\n"
        f"⚠️ El SRI la marcó como {resultado['estado'].lower()}.\n"
        f"{motivos or 'Sin detalle del motivo.'}\n\n"
        "La factura quedó guardada; corrige lo indicado y reintenta."
    )


def atender_mensaje(
    telefono: str,
    texto: str,
    sesion: Session,
    es_audio: bool = False,
    es_imagen: bool = False,
) -> str:
    """
    Punto de entrada del asistente. Devuelve el texto a responder por WhatsApp.

    `es_audio`/`es_imagen` indica que el texto proviene de transcripción u OCR:
    se anota en el historial para que el modelo tenga contexto del origen sin
    alterar ESQUEMA_FACTURA ni la lógica de extracción.
    """
    conversacion = obtener_conversacion(telefono)
    normalizado = texto.strip().lower()

    # Si hay un borrador esperando confirmación, ese turno manda: no se vuelve
    # a llamar al modelo para interpretar un "sí".
    if conversacion.borrador is not None:
        if normalizado in CONFIRMACIONES:
            borrador = conversacion.borrador
            conversacion.borrador = None
            conversacion.historial.clear()
            return _emitir(sesion, borrador)

        if normalizado in CANCELACIONES:
            conversacion.borrador = None
            conversacion.historial.clear()
            return "Cancelado. No emití nada."

        conversacion.borrador = None  # Cualquier otra cosa reabre la conversación.

    # Anotar origen multimodal en el historial sin tocar ESQUEMA_FACTURA:
    # el modelo ve que el texto vino de audio/imagen por el prefijo.
    texto_para_modelo = texto
    if es_audio:
        texto_para_modelo = f"[Audio transcrito] {texto}"
    elif es_imagen:
        texto_para_modelo = f"[Imagen OCR] {texto}"

    try:
        extraccion = extraer_factura(texto_para_modelo, conversacion.historial)
    except ErrorExtraccion as error:
        registro.warning("Extracción fallida para %s: %s", telefono, error)
        return str(error)

    conversacion.historial += [
        {"role": "user", "content": texto_para_modelo},
        {"role": "assistant", "content": extraccion.respuesta_sugerida},
    ]
    # Limitar historial a 12 turnos para no exceder ventana del modelo
    if len(conversacion.historial) > 12:
        conversacion.historial = conversacion.historial[-12:]
    conversacion.actualizada = datetime.now(timezone.utc)

    if extraccion.intencion != "crear_factura":
        return extraccion.respuesta_sugerida

    if extraccion.advertencias:
        return extraccion.respuesta_sugerida + "\n\n⚠️ " + "\n⚠️ ".join(extraccion.advertencias)

    if extraccion.datos_faltantes or not extraccion.detalles:
        return extraccion.respuesta_sugerida

    receptor = _buscar_o_crear_receptor(sesion, extraccion.cliente or {})
    if receptor is None:
        return "Necesito una identificación válida del cliente (cédula o RUC) para continuar."
    if not receptor.direccion:
        return (
            f"Registré a {receptor.razon_social}, pero me falta su dirección. "
            "El SRI la exige en el comprobante. ¿Cuál es?"
        )

    borrador = _preparar_borrador(sesion, extraccion, receptor)
    if borrador is None:
        return "No pude preparar la factura. Revisa que la empresa esté configurada."

    sesion.commit()
    conversacion.borrador = borrador
    return _formatear_resumen(borrador)
