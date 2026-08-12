"""Pruebas de autenticación: hashing, tokens y endpoints."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_auth") / "auth.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-solo-para-tests"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import crear_tablas
    from app.main import aplicacion

    crear_tablas()
    return TestClient(aplicacion)


# --------------------------------------------------------------------------
# Hashing de contraseñas
# --------------------------------------------------------------------------


def test_hash_no_contiene_la_contrasena(cliente):
    from app.seguridad import cifrar_contrasena

    hash_generado = cifrar_contrasena("MiClaveSegura123")
    assert "MiClaveSegura123" not in hash_generado
    assert hash_generado.startswith("pbkdf2_sha256$")


def test_dos_hashes_de_la_misma_clave_difieren(cliente):
    """Sal aleatoria por usuario: dos cuentas con igual clave no se delatan."""
    from app.seguridad import cifrar_contrasena, verificar_contrasena

    primero = cifrar_contrasena("MiClaveSegura123")
    segundo = cifrar_contrasena("MiClaveSegura123")

    assert primero != segundo
    assert verificar_contrasena("MiClaveSegura123", primero)
    assert verificar_contrasena("MiClaveSegura123", segundo)


def test_contrasena_incorrecta_no_verifica(cliente):
    from app.seguridad import cifrar_contrasena, verificar_contrasena

    almacenada = cifrar_contrasena("MiClaveSegura123")
    assert not verificar_contrasena("otraClave", almacenada)
    assert not verificar_contrasena("", almacenada)


def test_hash_corrupto_no_revienta(cliente):
    from app.seguridad import verificar_contrasena

    assert not verificar_contrasena("x", "basura")
    assert not verificar_contrasena("x", "")


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------


def test_token_ida_y_vuelta(cliente):
    from app.seguridad import crear_token, decodificar_token

    cuerpo = decodificar_token(crear_token("ana@empresa.ec", {"rol": "administrador"}))
    assert cuerpo["sub"] == "ana@empresa.ec"
    assert cuerpo["rol"] == "administrador"


def test_token_manipulado_es_rechazado(cliente):
    from app.seguridad import crear_token, decodificar_token

    token = crear_token("ana@empresa.ec")
    cabecera, cuerpo, firma = token.split(".")
    # Se altera el cuerpo manteniendo la firma original.
    alterado = f"{cabecera}.{cuerpo[:-4]}AAAA.{firma}"

    with pytest.raises(ValueError):
        decodificar_token(alterado)


def test_token_expirado_es_rechazado(cliente, monkeypatch):
    import app.seguridad as seguridad

    monkeypatch.setattr(seguridad, "HORAS_VIGENCIA_TOKEN", -1)
    token = seguridad.crear_token("ana@empresa.ec")

    with pytest.raises(ValueError, match="expiró"):
        seguridad.decodificar_token(token)


def test_token_de_otra_clave_es_rechazado(cliente, monkeypatch):
    import app.seguridad as seguridad

    token = seguridad.crear_token("ana@empresa.ec")
    monkeypatch.setattr(seguridad, "CLAVE_SECRETA", "otra-clave-distinta")

    with pytest.raises(ValueError, match="Firma"):
        seguridad.decodificar_token(token)


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


def test_primer_usuario_es_administrador(cliente):
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "Ana@Empresa.ec", "nombre": "Ana Salazar", "contrasena": "ClaveSegura123"},
    )
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["rol"] == "administrador"
    # El correo se normaliza a minúsculas.
    assert datos["correo"] == "ana@empresa.ec"


def _sesion_de(cliente, correo: str, contrasena: str) -> dict:
    """Devuelve la cabecera Authorization de ese usuario."""
    respuesta = cliente.post(
        "/api/auth/token", data={"username": correo, "password": contrasena}
    )
    assert respuesta.status_code == 200, respuesta.text
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_segundo_usuario_es_operador(cliente):
    """
    El alta a partir del segundo usuario la hace un administrador.

    Antes esta prueba llamaba al registro sin credenciales, que era el reflejo
    del agujero: con el API cerrado, cualquiera podía darse de alta y obtener
    un token válido con el que pasar todas las dependencias de sesión.
    """
    admin = _sesion_de(cliente, "ana@empresa.ec", "ClaveSegura123")
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "diego@empresa.ec", "nombre": "Diego Ruiz", "contrasena": "OtraClave456"},
        headers=admin,
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["rol"] == "operador"


def test_el_segundo_registro_sin_sesion_se_rechaza(cliente):
    """Con un usuario ya en la base, el registro deja de ser público."""
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "intruso@empresa.ec", "nombre": "Intruso", "contrasena": "ClaveSegura123"},
    )
    assert respuesta.status_code == 401


def test_un_operador_no_puede_dar_de_alta(cliente):
    """
    Tener sesión no basta: hace falta el rol.

    Es la primera comprobación de rol del sistema. Hasta aquí el campo `rol`
    del usuario se rellenaba y no se leía en ninguna parte, así que cualquier
    usuario autenticado podía hacer cualquier cosa.
    """
    operador = _sesion_de(cliente, "diego@empresa.ec", "OtraClave456")
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "otro@empresa.ec", "nombre": "Otro", "contrasena": "ClaveSegura123"},
        headers=operador,
    )
    assert respuesta.status_code == 403


def test_rechaza_contrasena_corta(cliente):
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "corta@empresa.ec", "nombre": "X", "contrasena": "1234"},
    )
    assert respuesta.status_code == 422


def test_rechaza_correo_duplicado(cliente):
    admin = _sesion_de(cliente, "ana@empresa.ec", "ClaveSegura123")
    respuesta = cliente.post(
        "/api/auth/registro",
        json={"correo": "ana@empresa.ec", "nombre": "Otra Ana", "contrasena": "ClaveSegura123"},
        headers=admin,
    )
    assert respuesta.status_code == 409


def test_un_desconocido_no_averigua_que_correos_existen(cliente):
    """
    Sin sesión, un correo registrado y uno inventado dan la misma respuesta.

    Si el 409 de «ya existe» se comprobara antes que la sesión, bastaría con
    probar correos para saber cuáles tienen cuenta. El login evita esa fuga
    devolviendo el mismo mensaje para usuario inexistente y contraseña
    incorrecta; aquí se evita con el orden de las comprobaciones.
    """
    existente = cliente.post(
        "/api/auth/registro",
        json={"correo": "ana@empresa.ec", "nombre": "X", "contrasena": "ClaveSegura123"},
    )
    inventado = cliente.post(
        "/api/auth/registro",
        json={"correo": "nadie@empresa.ec", "nombre": "X", "contrasena": "ClaveSegura123"},
    )
    assert existente.status_code == inventado.status_code == 401


def test_login_devuelve_token(cliente):
    respuesta = cliente.post(
        "/api/auth/token",
        data={"username": "ana@empresa.ec", "password": "ClaveSegura123"},
    )
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["token_type"] == "bearer"
    assert datos["nombre"] == "Ana Salazar"
    assert len(datos["access_token"].split(".")) == 3


def test_login_con_clave_incorrecta_falla(cliente):
    respuesta = cliente.post(
        "/api/auth/token", data={"username": "ana@empresa.ec", "password": "incorrecta"}
    )
    assert respuesta.status_code == 401


def test_mismo_mensaje_para_usuario_inexistente(cliente):
    """No debe poder deducirse qué correos están registrados."""
    sin_usuario = cliente.post(
        "/api/auth/token", data={"username": "nadie@empresa.ec", "password": "loquesea"}
    )
    clave_mala = cliente.post(
        "/api/auth/token", data={"username": "ana@empresa.ec", "password": "incorrecta"}
    )
    assert sin_usuario.status_code == clave_mala.status_code == 401
    assert sin_usuario.json()["detail"] == clave_mala.json()["detail"]


def test_perfil_requiere_token(cliente):
    assert cliente.get("/api/auth/yo").status_code == 401


def test_perfil_con_token_valido(cliente):
    token = cliente.post(
        "/api/auth/token", data={"username": "ana@empresa.ec", "password": "ClaveSegura123"}
    ).json()["access_token"]

    respuesta = cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == "ana@empresa.ec"


def test_perfil_con_token_basura(cliente):
    respuesta = cliente.get("/api/auth/yo", headers={"Authorization": "Bearer basura"})
    assert respuesta.status_code == 401
