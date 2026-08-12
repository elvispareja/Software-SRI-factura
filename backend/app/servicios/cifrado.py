"""
Cifrado simétrico para secretos en reposo (la contraseña del certificado .p12).

Se usa Fernet (AES-128-CBC + HMAC-SHA256) de `cryptography`, que ya es
dependencia del motor de firma. La clave se deriva de `CLAVE_SECRETA` con
PBKDF2, así que no hay un segundo secreto que gestionar.

Consecuencia que conviene tener presente: **si `CLAVE_SECRETA` cambia, las
contraseñas guardadas dejan de poder descifrarse** y hay que volver a subir el
certificado. Es el precio de no introducir un gestor de claves todavía; cuando
el sistema llegue a producción, lo correcto es mover esto a un KMS o a Vault.
"""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from ..seguridad import CLAVE_SECRETA

# Sal fija: la clave debe ser reproducible entre reinicios del proceso. La
# protección real la da CLAVE_SECRETA, no la sal.
SAL_DERIVACION = b"factoa-cifrado-en-reposo-v1"
ITERACIONES = 390_000


class ErrorCifrado(Exception):
    """No se pudo cifrar o descifrar el secreto."""


def _clave_fernet() -> bytes:
    derivador = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=SAL_DERIVACION,
        iterations=ITERACIONES,
    )
    return base64.urlsafe_b64encode(derivador.derive(CLAVE_SECRETA.encode()))


def cifrar(texto: str) -> str:
    return Fernet(_clave_fernet()).encrypt(texto.encode()).decode()


def descifrar(texto_cifrado: str) -> str:
    try:
        return Fernet(_clave_fernet()).decrypt(texto_cifrado.encode()).decode()
    except InvalidToken as error:
        raise ErrorCifrado(
            "No se pudo descifrar el secreto. Es probable que CLAVE_SECRETA haya "
            "cambiado desde que se guardó; vuelve a subir el certificado."
        ) from error
