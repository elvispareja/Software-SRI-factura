"""Pruebas de cuentas bancarias, firma electrónica y sesión por cookie."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_cfg") / "cfg.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-configuracion"
    # En los tests el cliente no habla HTTPS.
    os.environ["COOKIE_SEGURA"] = "false"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion
    from app.modelos_db import Empresa

    crear_tablas()

    sesion = SesionLocal()
    sesion.add(
        Empresa(
            ruc="1790016919001",
            razon_social="MI EMPRESA DEMO S.A.",
            direccion_matriz="Av. Amazonas N21-147",
            ambiente="1",
        )
    )
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion), con_cabecera=False)


def _token_operador(cliente) -> str:
    """
    Registra (si no existe) y autentica a un operador, y devuelve su token.

    El `cliente` del módulo se autentica por cookie (`con_cabecera=False`), y
    `/auth/token` **siempre** manda `Set-Cookie` en la respuesta, sin importar
    de quién sea el login. Sin restaurarla, el login del operador pisaría la
    cookie del administrador en el mismo `TestClient` y las pruebas siguientes
    del módulo se quedarían autenticadas como operador sin que nada lo avise.
    """
    cookie_admin = dict(cliente.cookies)
    cliente.post(
        "/api/auth/registro",
        json={"correo": "operador.cfg@empresa.ec", "nombre": "Operador", "contrasena": "ClaveSegura123"},
    )
    respuesta = cliente.post(
        "/api/auth/token",
        data={"username": "operador.cfg@empresa.ec", "password": "ClaveSegura123"},
    )
    assert respuesta.status_code == 200, respuesta.text
    cliente.cookies.clear()
    cliente.cookies.update(cookie_admin)
    return respuesta.json()["access_token"]


@pytest.fixture(scope="module")
def p12(tmp_path_factory):
    """Certificado autofirmado para probar la carga."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("cert") / "pruebas.p12"
    generar(ruta, "pruebas123")
    return ruta


# --------------------------------------------------------------------------
# Cifrado en reposo
# --------------------------------------------------------------------------


def test_cifrado_ida_y_vuelta(cliente):
    from app.servicios.cifrado import cifrar, descifrar

    secreto = "contraseña-del-certificado"
    cifrado = cifrar(secreto)

    assert secreto not in cifrado
    assert descifrar(cifrado) == secreto


def test_dos_cifrados_del_mismo_texto_difieren(cliente):
    """Fernet incluye un IV aleatorio: el mismo texto no produce el mismo token."""
    from app.servicios.cifrado import cifrar, descifrar

    primero, segundo = cifrar("misma clave"), cifrar("misma clave")
    assert primero != segundo
    assert descifrar(primero) == descifrar(segundo) == "misma clave"


def test_texto_manipulado_no_descifra(cliente):
    from app.servicios.cifrado import ErrorCifrado, cifrar, descifrar

    cifrado = cifrar("secreto")
    with pytest.raises(ErrorCifrado):
        descifrar(cifrado[:-4] + "AAAA")


# --------------------------------------------------------------------------
# Cuentas bancarias
# --------------------------------------------------------------------------


def test_crear_y_listar_cuentas(cliente):
    respuesta = cliente.post(
        "/api/configuracion/cuentas",
        json={
            "banco": "Banco Pichincha",
            "tipo": "Corriente",
            "numero": "2100123456",
            "titular": "MI EMPRESA DEMO S.A.",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    assert cliente.get("/api/configuracion/cuentas").json()[0]["banco"] == "Banco Pichincha"


def test_rechaza_cuenta_duplicada(cliente):
    cuerpo = {
        "banco": "Banco del Pacífico",
        "numero": "1045887711",
        "titular": "MI EMPRESA DEMO S.A.",
    }
    assert cliente.post("/api/configuracion/cuentas", json=cuerpo).status_code == 201
    assert cliente.post("/api/configuracion/cuentas", json=cuerpo).status_code == 409


def test_desactivar_no_borra(cliente):
    """Los RIDE ya emitidos mencionan la cuenta."""
    creada = cliente.post(
        "/api/configuracion/cuentas",
        json={"banco": "Banco Guayaquil", "numero": "9999", "titular": "X"},
    ).json()

    assert cliente.delete(f"/api/configuracion/cuentas/{creada['id']}").status_code == 204
    numeros = [c["numero"] for c in cliente.get("/api/configuracion/cuentas").json()]
    assert "9999" not in numeros


# --------------------------------------------------------------------------
# Firma electrónica
# --------------------------------------------------------------------------


def test_un_operador_no_puede_editar_la_empresa(cliente):
    """
    Tener sesión no basta: cambiar el RUC o la razón social es cosa del
    administrador. Antes de esto, cualquier usuario autenticado podía hacerlo.
    """
    token = _token_operador(cliente)
    respuesta = cliente.put(
        "/api/configuracion/empresa",
        json={
            "ruc": "1790016919001",
            "razon_social": "OTRA RAZON SOCIAL S.A.",
            "direccion_matriz": "Otra dirección",
            "ambiente": "1",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 403


def test_sin_firma_devuelve_nulo(cliente):
    assert cliente.get("/api/configuracion/firma").json() is None


def test_subir_firma_extrae_los_metadatos(cliente, p12):
    """Los datos del certificado salen del propio archivo, no del usuario."""
    with open(p12, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("pruebas.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["nombre_archivo"] == "pruebas.p12"
    assert "MI EMPRESA DEMO" in datos["propietario"]
    assert datos["valida_hasta"] > datos["valida_desde"]


def test_un_operador_no_puede_subir_ni_quitar_la_firma(cliente, p12):
    """
    Subir el certificado es literalmente entregar la llave con la que se
    firma en nombre de la empresa; no puede depender solo de tener sesión.
    """
    token = _token_operador(cliente)
    cabecera = {"Authorization": f"Bearer {token}"}

    with open(p12, "rb") as archivo:
        subida = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("pruebas.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
            headers=cabecera,
        )
    assert subida.status_code == 403

    assert cliente.delete("/api/configuracion/firma", headers=cabecera).status_code == 403


def test_la_firma_nunca_expone_archivo_ni_contrasena(cliente):
    """El .p12 y su clave no salen del servidor por ningún endpoint."""
    datos = cliente.get("/api/configuracion/firma").json()
    assert "contenido" not in datos
    assert "contrasena_cifrada" not in datos
    assert "pruebas123" not in str(datos)


def test_contrasena_incorrecta_se_rechaza_al_subir(cliente, p12):
    """Mucho mejor descubrirlo aquí que al firmar el primer comprobante."""
    with open(p12, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("pruebas.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "incorrecta"},
        )
    assert respuesta.status_code == 422


def test_rechaza_archivo_que_no_es_p12(cliente):
    respuesta = cliente.post(
        "/api/configuracion/firma",
        files={"archivo": ("documento.pdf", b"%PDF-1.4", "application/pdf")},
        data={"contrasena": "x"},
    )
    assert respuesta.status_code == 422


def test_la_contrasena_queda_cifrada_en_la_base(cliente):
    from app.base_datos import SesionLocal
    from app.modelos_db import FirmaElectronica
    from app.servicios.cifrado import descifrar
    from sqlalchemy import select

    sesion = SesionLocal()
    firma = sesion.scalar(select(FirmaElectronica).where(FirmaElectronica.activa.is_(True)))
    almacenada = firma.contrasena_cifrada
    sesion.close()

    assert "pruebas123" not in almacenada
    assert descifrar(almacenada) == "pruebas123"


def test_subir_otra_firma_desactiva_la_anterior(cliente, p12):
    """Solo un certificado activo: el que se usa para firmar."""
    from app.base_datos import SesionLocal
    from app.modelos_db import FirmaElectronica
    from sqlalchemy import func, select

    with open(p12, "rb") as archivo:
        cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("nueva.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )

    sesion = SesionLocal()
    activas = sesion.scalar(
        select(func.count())
        .select_from(FirmaElectronica)
        .where(FirmaElectronica.activa.is_(True))
    )
    sesion.close()

    assert activas == 1
    assert cliente.get("/api/configuracion/firma").json()["nombre_archivo"] == "nueva.p12"


# --------------------------------------------------------------------------
# Sesión por cookie
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def credenciales():
    return {"username": "ana@empresa.ec", "password": "ClaveSegura123"}


def test_login_emite_cookie_httponly(cliente, credenciales):
    cliente.post(
        "/api/auth/registro",
        json={"correo": "ana@empresa.ec", "nombre": "Ana", "contrasena": "ClaveSegura123"},
    )

    respuesta = cliente.post("/api/auth/token", data=credenciales)
    assert respuesta.status_code == 200

    cabecera = respuesta.headers.get("set-cookie", "")
    assert "factoa_sesion=" in cabecera
    # HttpOnly es lo que impide que un XSS lea el token.
    assert "HttpOnly" in cabecera
    assert "Path=/" in cabecera


def test_la_cookie_autentica_sin_cabecera(cliente):
    """El navegador no envía Authorization; la cookie debe bastar."""
    respuesta = cliente.get("/api/auth/yo")
    assert respuesta.status_code == 200
    assert respuesta.json()["correo"] == "ana@empresa.ec"


def test_salir_borra_la_cookie(cliente, credenciales):
    respuesta = cliente.post("/api/auth/salir")
    assert respuesta.status_code == 204

    cliente.cookies.clear()
    assert cliente.get("/api/auth/yo").status_code == 401


def test_la_cabecera_sigue_funcionando(cliente, credenciales):
    """Scripts y curl no manejan cookies: el Bearer debe seguir aceptándose."""
    token = cliente.post("/api/auth/token", data=credenciales).json()["access_token"]
    cliente.cookies.clear()

    respuesta = cliente.get("/api/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.status_code == 200


def test_sin_cookie_ni_cabecera_es_401(cliente):
    cliente.cookies.clear()
    assert cliente.get("/api/auth/yo").status_code == 401
