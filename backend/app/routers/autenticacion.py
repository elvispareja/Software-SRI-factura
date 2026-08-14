"""Endpoints de autenticación."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..base_datos import obtener_sesion
from ..modelos_db import Usuario
from ..seguridad import (
    COOKIE_SAMESITE,
    COOKIE_SEGURA,
    HORAS_VIGENCIA_TOKEN,
    NOMBRE_COOKIE,
    administrador_actual,
    cifrar_contrasena,
    crear_token,
    esquema_oauth,
    usuario_actual,
    verificar_contrasena,
)

router = APIRouter(prefix="/auth", tags=["autenticación"])

LONGITUD_MINIMA_CONTRASENA = 8


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    nombre: str
    correo: str
    rol: str


class RegistroUsuario(BaseModel):
    correo: EmailStr
    nombre: str
    contrasena: str


class UsuarioSalida(BaseModel):
    id: int
    correo: str
    nombre: str
    rol: str

    model_config = {"from_attributes": True}


class ActualizacionPerfil(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    correo: EmailStr
    # La contraseña actual se exige siempre: es la prueba de que quien edita es
    # el dueño de la cuenta y no una sesión secuestrada.
    contrasena_actual: str
    # Opcional: solo si se quiere cambiar la clave.
    contrasena_nueva: str | None = None


@router.post("/registro", response_model=UsuarioSalida, status_code=201)
def registrar(
    datos: RegistroUsuario,
    peticion: Request,
    token: str | None = Depends(esquema_oauth),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Alta de usuario.

    El primero que se registra queda como administrador; los siguientes, como
    operadores. Así el sistema arranca sin necesidad de sembrar credenciales.

    **Solo el primero entra sin credenciales.** A partir de ahí el alta la hace
    un administrador. Dejarlo abierto anulaba el cierre del API: cualquiera que
    alcanzara el servidor se registraba, obtenía un token válido y pasaba todas
    las dependencias de sesión. Cerrar los routers y dejar esta puerta al lado
    es poner una cerradura y colgar la llave del pomo.

    La excepción del primer usuario no es un descuido: sin ella el sistema no
    podría arrancar, porque no habría administrador que autorizara el alta del
    administrador.
    """
    if len(datos.contrasena) < LONGITUD_MINIMA_CONTRASENA:
        raise HTTPException(
            422, f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres."
        )

    es_primero = (sesion.scalar(select(func.count()).select_from(Usuario)) or 0) == 0

    # Con usuarios ya en la base, el alta exige un administrador con sesión.
    # No se declara como dependencia del endpoint porque la condición depende
    # del estado de la base, y una dependencia se evalúa siempre. El token se
    # recibe por la vía normal (`esquema_oauth`) para que sirvan tanto la
    # cabecera Bearer como la cookie, igual que en el resto del API.
    #
    # Va ANTES de comprobar si el correo existe, y el orden importa: al revés,
    # un desconocido distinguía un 409 de un 401 y averiguaba así qué correos
    # están registrados. El login ya evita esa fuga a propósito (ver más
    # abajo); dejarla abierta aquí la habría hecho inútil.
    if not es_primero:
        administrador_actual(usuario_actual(peticion, token, sesion))

    correo = datos.correo.lower()
    if sesion.scalar(select(Usuario).where(Usuario.correo == correo)):
        raise HTTPException(409, "Ya existe una cuenta con ese correo.")

    usuario = Usuario(
        correo=correo,
        nombre=datos.nombre,
        contrasena_hash=cifrar_contrasena(datos.contrasena),
        rol="administrador" if es_primero else "operador",
    )
    sesion.add(usuario)
    sesion.commit()
    sesion.refresh(usuario)
    return usuario


@router.post("/token", response_model=Token)
def iniciar_sesion(
    respuesta: Response,
    formulario: OAuth2PasswordRequestForm = Depends(),
    sesion: Session = Depends(obtener_sesion),
):
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == formulario.username.lower()))

    # Mismo mensaje para usuario inexistente y contraseña incorrecta: distinguir
    # ambos casos permitiría averiguar qué correos están registrados.
    if usuario is None or not verificar_contrasena(formulario.password, usuario.contrasena_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not usuario.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "La cuenta está desactivada.")

    token = crear_token(usuario.correo, {"rol": usuario.rol, "nombre": usuario.nombre})

    # La cookie HttpOnly es lo que usa el navegador; el token también va en el
    # cuerpo para clientes que no manejan cookies (scripts, apps móviles).
    respuesta.set_cookie(
        key=NOMBRE_COOKIE,
        value=token,
        httponly=True,
        secure=COOKIE_SEGURA,
        samesite=COOKIE_SAMESITE,
        max_age=HORAS_VIGENCIA_TOKEN * 3600,
        path="/",
    )

    return Token(
        access_token=token,
        nombre=usuario.nombre,
        correo=usuario.correo,
        rol=usuario.rol,
    )


@router.post("/salir", status_code=204)
def cerrar_sesion(respuesta: Response):
    """Borra la cookie. El token sigue siendo válido hasta expirar."""
    respuesta.delete_cookie(
        key=NOMBRE_COOKIE,
        httponly=True,
        secure=COOKIE_SEGURA,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


@router.get("/yo", response_model=UsuarioSalida)
def perfil(usuario: Usuario = Depends(usuario_actual)):
    return usuario


@router.put("/perfil", response_model=UsuarioSalida)
def actualizar_perfil(
    datos: ActualizacionPerfil,
    respuesta: Response,
    usuario: Usuario = Depends(usuario_actual),
    sesion: Session = Depends(obtener_sesion),
):
    """
    Edita el nombre, el correo y —opcionalmente— la contraseña del usuario.

    La contraseña actual se verifica siempre: sin ella no se toca nada, aunque
    haya sesión. Cambiar el correo obliga a reemitir la cookie, porque el `sub`
    del token es justamente el correo y el viejo dejaría de resolver al usuario.
    """
    if not verificar_contrasena(datos.contrasena_actual, usuario.contrasena_hash):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "La contraseña actual no es correcta."
        )

    correo_nuevo = datos.correo.lower()
    correo_cambia = correo_nuevo != usuario.correo

    # El índice único de `correo` protege contra la carrera; esta comprobación
    # da un 409 legible en el caso normal en vez de esperar al IntegrityError.
    if correo_cambia:
        ocupado = sesion.scalar(
            select(Usuario).where(
                Usuario.correo == correo_nuevo, Usuario.id != usuario.id
            )
        )
        if ocupado is not None:
            raise HTTPException(409, "Ya existe una cuenta con ese correo.")

    if datos.contrasena_nueva is not None:
        if len(datos.contrasena_nueva) < LONGITUD_MINIMA_CONTRASENA:
            raise HTTPException(
                422,
                f"La contraseña debe tener al menos {LONGITUD_MINIMA_CONTRASENA} caracteres.",
            )
        usuario.contrasena_hash = cifrar_contrasena(datos.contrasena_nueva)

    usuario.nombre = datos.nombre
    usuario.correo = correo_nuevo

    try:
        sesion.commit()
    except IntegrityError as error:
        sesion.rollback()
        raise HTTPException(409, "Ya existe una cuenta con ese correo.") from error
    sesion.refresh(usuario)

    if correo_cambia:
        token = crear_token(usuario.correo, {"rol": usuario.rol, "nombre": usuario.nombre})
        respuesta.set_cookie(
            key=NOMBRE_COOKIE,
            value=token,
            httponly=True,
            secure=COOKIE_SEGURA,
            samesite=COOKIE_SAMESITE,
            max_age=HORAS_VIGENCIA_TOKEN * 3600,
            path="/",
        )

    return usuario
