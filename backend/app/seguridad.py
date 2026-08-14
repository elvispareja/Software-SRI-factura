"""
Autenticación por JWT.

Las contraseñas se guardan con PBKDF2-HMAC-SHA256 y sal por usuario, usando
`hashlib` de la librería estándar para no añadir dependencias. No se guarda
nunca la contraseña en claro ni un hash sin sal.

La clave de firma del token viene de `CLAVE_SECRETA`. En producción es
obligatorio definirla: si se deja la de desarrollo, cualquiera que conozca el
código puede emitir tokens válidos.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .base_datos import obtener_sesion
from .modelos_db import TokenRevocado, Usuario

CLAVE_SECRETA = os.getenv("CLAVE_SECRETA", "desarrollo-no-usar-en-produccion")
ES_CLAVE_DE_DESARROLLO = CLAVE_SECRETA == "desarrollo-no-usar-en-produccion"

# En producción es obligatorio definir una CLAVE_SECRETA propia. Se considera
# "producción" tanto AMBIENTE == "2" como COOKIE_SEGURA activo (esta última solo
# se enciende detrás de HTTPS real): cualquiera de las dos señales, usando la
# clave de ejemplo, aborta el arranque. En desarrollo (AMBIENTE=1 y cookie no
# segura) no cambia nada. Se valida al importar (fallo temprano si el proceso
# arranca mal configurado) y vía función para el ciclo de vida de FastAPI.
def _es_entorno_produccion() -> bool:
    return (
        os.getenv("AMBIENTE") == "2"
        or os.getenv("COOKIE_SEGURA", "").lower() == "true"
    )


if ES_CLAVE_DE_DESARROLLO and _es_entorno_produccion():
    raise RuntimeError("CLAVE_SECRETA obligatoria en producción")


def validar_seguridad_produccion() -> None:
    """Llamar desde el ciclo de vida del API para fallar rápido en prod sin clave."""
    if ES_CLAVE_DE_DESARROLLO and _es_entorno_produccion():
        raise RuntimeError("CLAVE_SECRETA obligatoria en producción")

HORAS_VIGENCIA_TOKEN = int(os.getenv("HORAS_VIGENCIA_TOKEN", "12"))
ITERACIONES_PBKDF2 = 260_000

# El token viaja en una cookie HttpOnly: así el JavaScript de la página no
# puede leerlo, y un XSS no se lleva la sesión. `Secure` se desactiva solo en
# desarrollo, donde el frontend corre sobre http://localhost.
NOMBRE_COOKIE = "factoa_sesion"
COOKIE_SEGURA = os.getenv("COOKIE_SEGURA", "true").lower() != "false"
# SameSite=lax basta mientras frontend y API compartan sitio. Si se despliegan
# en dominios distintos hay que pasar a "none" (que exige Secure) y revisar CORS.
COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax")

# auto_error=False: la cabecera Authorization sigue aceptándose (para curl,
# scripts y el propio Swagger), pero su ausencia no es un error si hay cookie.
esquema_oauth = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


# --------------------------------------------------------------------------
# Contraseñas
# --------------------------------------------------------------------------


def cifrar_contrasena(contrasena: str) -> str:
    """Devuelve `pbkdf2_sha256$iteraciones$sal$hash`, todo en base64 seguro."""
    sal = secrets.token_bytes(16)
    derivada = hashlib.pbkdf2_hmac(
        "sha256", contrasena.encode(), sal, ITERACIONES_PBKDF2
    )
    return "$".join(
        [
            "pbkdf2_sha256",
            str(ITERACIONES_PBKDF2),
            base64.b64encode(sal).decode(),
            base64.b64encode(derivada).decode(),
        ]
    )


def verificar_contrasena(contrasena: str, almacenada: str) -> bool:
    try:
        algoritmo, iteraciones, sal_b64, hash_b64 = almacenada.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False

        derivada = hashlib.pbkdf2_hmac(
            "sha256", contrasena.encode(), base64.b64decode(sal_b64), int(iteraciones)
        )
        # compare_digest evita filtrar información por el tiempo de comparación.
        return hmac.compare_digest(derivada, base64.b64decode(hash_b64))
    except (ValueError, TypeError):
        return False


# --------------------------------------------------------------------------
# Tokens JWT (HS256, implementados sobre hmac para no añadir dependencias)
# --------------------------------------------------------------------------


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def _des_b64(texto: str) -> bytes:
    relleno = "=" * (-len(texto) % 4)
    return base64.urlsafe_b64decode(texto + relleno)


def crear_token(asunto: str, datos_extra: dict | None = None) -> str:
    cabecera = {"alg": "HS256", "typ": "JWT"}
    expira = datetime.now(timezone.utc) + timedelta(hours=HORAS_VIGENCIA_TOKEN)

    cuerpo = {
        "sub": asunto,
        "exp": int(expira.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
        # `jti`: identificador único del token. Permite revocarlo en el logout
        # (ver TokenRevocado y usuario_actual). Sin él, cerrar sesión solo
        # borraría la cookie y el token seguiría válido hasta expirar.
        "jti": secrets.token_hex(16),
        **(datos_extra or {}),
    }

    sin_firma = f"{_b64(json.dumps(cabecera, separators=(',', ':')).encode())}." \
                f"{_b64(json.dumps(cuerpo, separators=(',', ':')).encode())}"
    firma = hmac.new(CLAVE_SECRETA.encode(), sin_firma.encode(), hashlib.sha256).digest()

    return f"{sin_firma}.{_b64(firma)}"


def decodificar_token(token: str) -> dict:
    try:
        cabecera_b64, cuerpo_b64, firma_b64 = token.split(".")
    except ValueError as error:
        raise ValueError("Token mal formado.") from error

    sin_firma = f"{cabecera_b64}.{cuerpo_b64}"
    esperada = hmac.new(CLAVE_SECRETA.encode(), sin_firma.encode(), hashlib.sha256).digest()

    if not hmac.compare_digest(esperada, _des_b64(firma_b64)):
        raise ValueError("Firma del token inválida.")

    cuerpo = json.loads(_des_b64(cuerpo_b64))

    if cuerpo.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        raise ValueError("El token expiró.")

    return cuerpo


# --------------------------------------------------------------------------
# Dependencia de FastAPI
# --------------------------------------------------------------------------


def usuario_actual(
    request: Request,
    token: str | None = Depends(esquema_oauth),
    sesion: Session = Depends(obtener_sesion),
) -> Usuario:
    error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # La cookie es el camino del navegador; la cabecera queda para clientes
    # que no la manejan (curl, scripts, Swagger).
    token = token or request.cookies.get(NOMBRE_COOKIE)
    if not token:
        raise error

    try:
        cuerpo = decodificar_token(token)
    except ValueError as fallo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(fallo),
            headers={"WWW-Authenticate": "Bearer"},
        ) from fallo

    # Token revocado en un logout: aunque la firma sea válida y no haya expirado,
    # si su `jti` está en la lista de revocación no vale. Los tokens antiguos sin
    # `jti` (emitidos antes de esta mejora) no se pueden revocar; se dejan pasar
    # para no invalidar sesiones en curso al desplegar.
    jti = cuerpo.get("jti")
    if jti and sesion.scalar(select(TokenRevocado).where(TokenRevocado.jti == jti)):
        raise error

    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == cuerpo.get("sub")))
    if usuario is None or not usuario.activo:
        raise error

    return usuario


def administrador_actual(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """
    Como `usuario_actual`, pero además exige el rol de administrador.

    Es la primera comprobación de rol del sistema. Hasta aquí, tener sesión
    equivalía a poder hacer cualquier cosa; el campo `rol` del usuario se
    rellenaba y no se leía en ninguna parte.

    El 403 —y no un 401— es deliberado: quien llega hasta aquí está
    identificado, lo que falla es que no le corresponde. Devolver 401 le diría
    que vuelva a iniciar sesión, que no arreglaría nada.
    """
    if usuario.rol != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hace falta ser administrador para esta operación.",
        )
    return usuario
