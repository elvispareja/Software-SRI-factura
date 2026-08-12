"""
Envío del comprobante autorizado al receptor.

El SRI no obliga a mandar nada por correo, pero el cliente necesita **dos
archivos**: el XML firmado —que es el documento legal, el único que vale ante
el SRI— y el RIDE en PDF, que es lo que una persona puede leer. Se adjuntan
siempre los dos; mandar solo el PDF deja al receptor sin el documento válido.

CONFIGURACIÓN
-------------
Sin `SMTP_SERVIDOR` el envío queda deshabilitado y el endpoint lo dice con
claridad en vez de fallar con un error de red. Es deliberado: un sistema recién
instalado no tiene servidor de correo, y eso no debe parecer una avería.
"""

from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

registro = logging.getLogger(__name__)


class ErrorCorreo(Exception):
    """El mensaje es apto para mostrárselo al usuario."""


def configuracion() -> dict:
    """Lee la configuración SMTP del entorno."""
    return {
        "servidor": os.getenv("SMTP_SERVIDOR", ""),
        "puerto": int(os.getenv("SMTP_PUERTO", "587")),
        "usuario": os.getenv("SMTP_USUARIO", ""),
        "contrasena": os.getenv("SMTP_CONTRASENA", ""),
        "remitente": os.getenv("SMTP_REMITENTE", ""),
        # STARTTLS en el 587, SSL directo en el 465.
        "usar_ssl": os.getenv("SMTP_SSL", "").lower() in ("1", "true", "si", "sí"),
    }


def esta_configurado() -> bool:
    return bool(configuracion()["servidor"])


def _cuerpo(razon_social: str, tipo: str, numero: str, autorizacion: str | None) -> str:
    lineas = [
        f"Estimado/a {razon_social}:",
        "",
        f"Adjuntamos su {tipo.lower()} electrónica número {numero}.",
    ]
    if autorizacion:
        lineas.append(f"Autorización del SRI: {autorizacion}")
    lineas += [
        "",
        "Se adjuntan dos archivos:",
        "  · El XML firmado, que es el documento con validez tributaria.",
        "  · El RIDE en PDF, que es su representación impresa.",
        "",
        "Conserve ambos: ante el SRI, el que vale es el XML.",
        "",
        "Este mensaje se generó automáticamente; no hace falta responderlo.",
    ]
    return "\n".join(lineas)


def enviar_comprobante(
    *,
    destinatario: str,
    razon_social: str,
    tipo: str,
    numero: str,
    autorizacion: str | None,
    xml: bytes,
    pdf: bytes,
    emisor: str,
    copia: str | None = None,
) -> None:
    """
    Manda el comprobante con sus dos adjuntos.

    Lanza `ErrorCorreo` con un mensaje legible ante cualquier fallo: quien lo
    lee es el usuario del sistema, no un administrador de servidores.
    """
    ajustes = configuracion()

    if not ajustes["servidor"]:
        raise ErrorCorreo(
            "El envío por correo no está configurado. Define SMTP_SERVIDOR, "
            "SMTP_USUARIO y SMTP_CONTRASENA en las variables de entorno."
        )
    if not destinatario:
        raise ErrorCorreo(
            f"{razon_social} no tiene correo registrado. Añádelo en Receptores."
        )

    remitente = ajustes["remitente"] or ajustes["usuario"]

    mensaje = EmailMessage()
    mensaje["Subject"] = f"{tipo} electrónica {numero} — {emisor}"
    mensaje["From"] = formataddr((emisor, remitente))
    mensaje["To"] = destinatario
    if copia:
        mensaje["Cc"] = copia
    mensaje.set_content(_cuerpo(razon_social, tipo, numero, autorizacion))

    # El XML va como `application/xml` y no como texto: algunos clientes de
    # correo reescriben los saltos de línea del texto plano, y eso invalidaría
    # la firma del documento.
    mensaje.add_attachment(
        xml, maintype="application", subtype="xml", filename=f"{numero}.xml"
    )
    mensaje.add_attachment(
        pdf, maintype="application", subtype="pdf", filename=f"RIDE-{numero}.pdf"
    )

    contexto = ssl.create_default_context()

    try:
        if ajustes["usar_ssl"]:
            with smtplib.SMTP_SSL(
                ajustes["servidor"], ajustes["puerto"], context=contexto, timeout=20
            ) as servidor:
                if ajustes["usuario"]:
                    servidor.login(ajustes["usuario"], ajustes["contrasena"])
                servidor.send_message(mensaje)
        else:
            with smtplib.SMTP(ajustes["servidor"], ajustes["puerto"], timeout=20) as servidor:
                servidor.starttls(context=contexto)
                if ajustes["usuario"]:
                    servidor.login(ajustes["usuario"], ajustes["contrasena"])
                servidor.send_message(mensaje)

    except smtplib.SMTPAuthenticationError as error:
        raise ErrorCorreo(
            "El servidor de correo rechazó el usuario o la contraseña. "
            "Si usas Gmail, hace falta una contraseña de aplicación."
        ) from error
    except smtplib.SMTPRecipientsRefused as error:
        raise ErrorCorreo(f"El servidor rechazó la dirección {destinatario}.") from error
    except (smtplib.SMTPException, OSError) as error:
        registro.exception("Fallo enviando el comprobante %s", numero)
        raise ErrorCorreo(f"No se pudo enviar el correo: {error}") from error
