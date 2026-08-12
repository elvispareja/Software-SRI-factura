"""
Extracción de datos de facturación desde lenguaje natural.

El usuario escribe por WhatsApp algo como:

    "Hazle una factura de 50 dólares a Juan Pérez, RUC 1790016919001,
     por servicios de consultoría"

y de ahí hay que sacar entidades estructuradas. Se usa **salida estructurada**
(`response_schema`) en vez de pedir JSON en el prompt: el modelo queda obligado
por el esquema, así que no hace falta parsear texto libre ni reintentar cuando
devuelve markdown alrededor del JSON.

PROVEEDOR: Gemini (`google-genai`). El OCR de imágenes de `routers/whatsapp.py`
sigue usando Anthropic, así que el sistema declara ambas dependencias.

Nada de lo que extrae el modelo se da por bueno: la identificación se valida con
el algoritmo del SRI y los importes se recalculan con el motor de cálculo. El
LLM propone, el sistema dispone.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Optional, List, Literal

from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from ..sri.identificacion import validar_identificacion
from ..sri.modelos import PORCENTAJES_IVA

# `MODELO_CLAUDE` se acepta todavía porque es el nombre que quedó en los
# despliegues anteriores a la migración; el nombre bueno es `MODELO_IA`.
MODELO = os.getenv("MODELO_IA") or os.getenv("MODELO_CLAUDE", "gemini-2.5-flash")

class DetalleExtraccion(BaseModel):
    descripcion: str
    cantidad: str = Field(description="Número como texto, p. ej. '2' o '1.5'. Si no se indica, '1'.")
    precio_unitario: str = Field(description="Precio por unidad SIN IVA, como texto. Sin símbolo de moneda.")
    precio_incluye_iva: bool = Field(description="true si el usuario dio un precio que ya incluye IVA.")
    codigo_iva: Literal["4", "5", "0", "6", "7"] = Field(description="4=IVA 15%, 5=IVA 5%, 0=IVA 0%, 6=No objeto, 7=Exento. Usa 4 si no se especifica.")

class ClienteExtraccion(BaseModel):
    identificacion: Optional[str] = Field(None, description="Cédula (10 dígitos) o RUC (13 dígitos), solo números.")
    tipo_identificacion: Optional[Literal["RUC", "Cédula", "Pasaporte", "Consumidor Final"]] = None
    nombre: Optional[str] = Field(None, description="Razón social o nombre completo tal como lo dijo el usuario.")
    correo: Optional[str] = None

class ResultadoExtraccionEstructura(BaseModel):
    intencion: Literal["crear_factura", "crear_receptor", "consultar_estado", "saludo", "otro"] = Field(description="Qué quiere hacer el usuario con este mensaje.")
    cliente: Optional[ClienteExtraccion] = None
    detalles: List[DetalleExtraccion] = Field(description="Ítems a facturar. Vacío si el mensaje no describe ninguno.")
    forma_pago: Optional[Literal["contado", "credito"]] = None
    datos_faltantes: List[Literal["identificacion_cliente", "nombre_cliente", "correo_cliente", "direccion_cliente", "descripcion_items", "precio_items"]] = Field(description="Qué falta para poder emitir. Vacío si no falta nada.")
    respuesta_sugerida: str = Field(description="Mensaje breve y natural para responderle al usuario por WhatsApp.")

INSTRUCCIONES = """\
Eres el asistente de facturación electrónica de una empresa ecuatoriana. Los \
usuarios te escriben por WhatsApp en lenguaje coloquial y tu trabajo es extraer \
los datos necesarios para emitir un comprobante ante el SRI.

Contexto tributario del Ecuador:
- La tarifa general del IVA es 15%. Úsala salvo que el mensaje indique otra cosa.
- Una cédula tiene 10 dígitos; un RUC tiene 13 y termina en 001.
- "Consumidor final" corresponde a la identificación 9999999999999.
- Los productos de primera necesidad suelen tener IVA 0%.

Cómo interpretar los mensajes:
- Si el usuario da un precio "con IVA incluido", marca precio_incluye_iva y deja \
el precio tal como lo dijo; el sistema hará la conversión.
- Extrae solo lo que el mensaje dice. No inventes identificaciones, montos ni \
correos: si un dato no está, déjalo nulo y anótalo en datos_faltantes.
- La identificación va solo con dígitos, sin guiones ni espacios.

La respuesta_sugerida es lo que el usuario leerá en WhatsApp. Escríbela en \
español, breve y directa: confirma lo que entendiste y pide únicamente lo que \
falta. Si no falta nada, resume la factura y pide confirmación antes de emitir.\
"""


class ErrorExtraccion(Exception):
    """La extracción no se pudo completar."""


@dataclass
class ResultadoExtraccion:
    intencion: str
    cliente: dict | None
    detalles: list[dict]
    forma_pago: str | None
    datos_faltantes: list[str]
    respuesta_sugerida: str
    advertencias: list[str] = field(default_factory=list)

    @property
    def listo_para_emitir(self) -> bool:
        return (
            self.intencion == "crear_factura"
            and not self.datos_faltantes
            and not self.advertencias
            and bool(self.detalles)
        )


def _a_decimal(valor: str | None, por_defecto: str = "0") -> Decimal:
    try:
        return Decimal(str(valor).strip().replace(",", ".") or por_defecto)
    except (InvalidOperation, AttributeError):
        return Decimal(por_defecto)


def _precio_sin_iva(precio: Decimal, codigo_iva: str, incluye_iva: bool) -> Decimal:
    """Si el usuario dio el precio con IVA, se despeja la base imponible."""
    if not incluye_iva:
        return precio

    tarifa = PORCENTAJES_IVA.get(codigo_iva, Decimal("0"))
    if tarifa == 0:
        return precio
    return precio / (1 + tarifa / Decimal("100"))


def _verificar(datos: dict) -> list[str]:
    """
    Revisa lo que devolvió el modelo contra las reglas del SRI.

    Cualquier cosa que el modelo pudo haber alucinado —una identificación
    inventada, un precio de cero— se detecta aquí y no llega al comprobante.
    """
    advertencias: list[str] = []
    cliente = datos.get("cliente") or {}

    identificacion = cliente.get("identificacion")
    tipo = cliente.get("tipo_identificacion")
    if identificacion and tipo:
        resultado = validar_identificacion(tipo, identificacion)
        if not resultado.es_valida:
            advertencias.append(
                f"La identificación {identificacion} no es válida: {resultado.error}"
            )

    for indice, detalle in enumerate(datos.get("detalles") or [], start=1):
        if _a_decimal(detalle.get("cantidad"), "1") <= 0:
            advertencias.append(f"El ítem {indice} tiene cantidad cero o negativa.")
        if _a_decimal(detalle.get("precio_unitario")) <= 0:
            advertencias.append(f"El ítem {indice} no tiene precio.")

    return advertencias


def normalizar_detalles(datos: dict) -> list[dict]:
    """Convierte los detalles del modelo al formato del motor de cálculo."""
    normalizados = []

    for detalle in datos.get("detalles") or []:
        codigo_iva = detalle.get("codigo_iva", "4")
        precio = _precio_sin_iva(
            _a_decimal(detalle.get("precio_unitario")),
            codigo_iva,
            bool(detalle.get("precio_incluye_iva")),
        )
        normalizados.append(
            {
                "descripcion": detalle.get("descripcion", "").strip(),
                "cantidad": _a_decimal(detalle.get("cantidad"), "1"),
                "precio_unitario": precio,
                "codigo_iva": codigo_iva,
            }
        )

    return normalizados


def _motivo_de_parada(respuesta) -> str:
    """
    `finish_reason` del primer candidato, como texto.

    Se lee a la defensiva porque llega como enum, como cadena o ausente según
    la versión del SDK, y un `AttributeError` aquí enmascararía el motivo real.
    """
    candidatos = getattr(respuesta, "candidates", None) or []
    if not candidatos:
        return ""
    motivo = getattr(candidatos[0], "finish_reason", None)
    if motivo is None:
        return ""
    return getattr(motivo, "name", None) or str(motivo).rsplit(".", 1)[-1]


def extraer_factura(
    mensaje: str,
    historial: list[dict] | None = None,
    cliente_ai=None,
) -> ResultadoExtraccion:
    """
    Extrae los datos de facturación de un mensaje.

    `historial` son los turnos previos de la conversación de WhatsApp, para que
    el usuario pueda completar datos en varios mensajes ("el RUC es 179...").
    """
    cliente = cliente_ai or genai.Client()

    gemini_contents = []
    for msg in (historial or []):
        role = "user" if msg["role"] == "user" else "model"
        gemini_contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    gemini_contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=mensaje)]
        )
    )

    try:
        respuesta = cliente.models.generate_content(
            model=MODELO,
            contents=gemini_contents,
            config=types.GenerateContentConfig(
                system_instruction=INSTRUCCIONES,
                response_mime_type="application/json",
                response_schema=ResultadoExtraccionEstructura,
                temperature=0.0,
            ),
        )
    except Exception as error:
        raise ErrorExtraccion(f"No se pudo consultar al modelo: {error}") from error

    # Por qué paró el modelo importa tanto como lo que devolvió: un rechazo de
    # seguridad y una respuesta cortada llegan ambos con el texto vacío, y sin
    # distinguirlos el usuario solo ve "no devolvió contenido".
    motivo = _motivo_de_parada(respuesta)
    if motivo in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"):
        raise ErrorExtraccion(
            "El modelo declinó procesar este mensaje. Reformúlalo o captura la "
            "factura desde el sistema."
        )
    if motivo == "MAX_TOKENS":
        raise ErrorExtraccion(
            "La respuesta se cortó por longitud. Divide el pedido en mensajes "
            "más cortos."
        )

    texto = respuesta.text
    if not texto:
        raise ErrorExtraccion("El modelo no devolvió contenido.")

    try:
        datos = json.loads(texto)
    except (json.JSONDecodeError, TypeError) as error:
        raise ErrorExtraccion(f"El modelo devolvió algo que no es JSON: {error}") from error

    return ResultadoExtraccion(
        intencion=datos["intencion"],
        cliente=datos.get("cliente"),
        detalles=datos.get("detalles") or [],
        forma_pago=datos.get("forma_pago"),
        datos_faltantes=datos.get("datos_faltantes") or [],
        respuesta_sugerida=datos["respuesta_sugerida"],
        advertencias=_verificar(datos),
    )
