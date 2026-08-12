"""Utilidades compartidas por las pruebas del API."""

from __future__ import annotations

CORREO_PRUEBA = "pruebas@empresa.ec"
CONTRASENA_PRUEBA = "pruebas1234"


def iniciar_sesion(cliente, con_cabecera: bool = True):
    """
    Deja el `TestClient` autenticado y lo devuelve.

    Todo el API de negocio exige sesión (ver `app.main`, `SESION_REQUERIDA`),
    así que cada fixture que crea un cliente pasa por aquí.

    Por defecto fija la cabecera `Authorization` y no la cookie: la cookie de
    sesión se marca `Secure`, y el `TestClient` habla por HTTP, así que su
    almacén de cookies la descartaría y las pruebas darían 401 sin motivo real.

    `con_cabecera=False` deja solo la cookie, para los módulos que prueban la
    sesión en sí y necesitan que al limpiar las cookies la respuesta sea 401.
    """
    cliente.post(
        "/api/auth/registro",
        json={
            "correo": CORREO_PRUEBA,
            "nombre": "Usuario de Pruebas",
            "contrasena": CONTRASENA_PRUEBA,
        },
    )
    respuesta = cliente.post(
        "/api/auth/token",
        data={"username": CORREO_PRUEBA, "password": CONTRASENA_PRUEBA},
    )
    assert respuesta.status_code == 200, respuesta.text

    if con_cabecera:
        cliente.headers["Authorization"] = f"Bearer {respuesta.json()['access_token']}"
    return cliente
