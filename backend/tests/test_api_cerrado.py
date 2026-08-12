"""
El API de negocio no responde a quien no ha iniciado sesión.

Esta prueba existe por una razón concreta: hasta que se añadió
`SESION_REQUERIDA` en `app.main`, 112 endpoints servían la contabilidad
completa —el padrón de clientes, las facturas, los reportes en CSV, y hasta la
subida del certificado `.p12` con su contraseña— a cualquiera que conociera la
URL. Las 292 pruebas de entonces pasaban en verde, porque ninguna comprobaba
que hiciera falta credencial.

El valor de este archivo no está en lo que prueba hoy, sino en lo que impide
mañana: si alguien quita un `dependencies=SESION_REQUERIDA` de un
`include_router`, o añade un router nuevo sin él, aquí se pone rojo. Sin esta
prueba, ese descuido vuelve a pasar desapercibido.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def cliente_anonimo(tmp_path_factory):
    """Un `TestClient` sin sesión: ni cookie, ni cabecera. Un desconocido."""
    base = tmp_path_factory.mktemp("bd") / "cerrado.db"
    import os

    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import crear_tablas
    from app.main import aplicacion

    crear_tablas()
    return TestClient(aplicacion)


# Una ruta por router de negocio. No hace falta la lista entera: la protección
# se declara por router, así que basta un centinela de cada uno para detectar
# que a ese router se le cayó la dependencia.
RUTAS_PROTEGIDAS = [
    ("GET", "/api/receptores", "padrón de clientes con cédula y RUC"),
    ("GET", "/api/articulos", "catálogo de artículos"),
    ("GET", "/api/comprobantes", "facturas emitidas"),
    ("GET", "/api/configuracion/empresa", "datos fiscales de la empresa"),
    ("GET", "/api/configuracion/firma", "certificado .p12 del contribuyente"),
    ("GET", "/api/configuracion/usuarios", "correos de los usuarios"),
    ("GET", "/api/guias", "guías de remisión"),
    ("GET", "/api/retenciones", "comprobantes de retención"),
    ("GET", "/api/anticipos", "anticipos de clientes"),
    ("GET", "/api/cuentas/resumen", "cuentas por cobrar"),
    ("GET", "/api/egresos", "salidas de caja"),
    ("GET", "/api/recurrentes", "plantillas de facturación recurrente"),
    ("GET", "/api/reportes/panel", "panel de indicadores"),
    ("GET", "/api/reportes/ventas", "total facturado"),
    ("GET", "/api/reportes/inventario/csv", "descarga del inventario"),
]


@pytest.mark.parametrize("metodo,ruta,que_expone", RUTAS_PROTEGIDAS)
def test_sin_sesion_responde_401(cliente_anonimo, metodo, ruta, que_expone):
    respuesta = cliente_anonimo.request(metodo, ruta)
    assert respuesta.status_code == 401, (
        f"{metodo} {ruta} respondió {respuesta.status_code} sin credenciales. "
        f"Expone: {que_expone}."
    )


# Los que escriben o transmiten. Un 401 aquí importa más todavía: no leen datos,
# los crean, y en dos casos comprometen el certificado o emiten ante el SRI.
RUTAS_ESCRITURA = [
    ("POST", "/api/receptores", "alta de clientes"),
    ("POST", "/api/comprobantes", "creación de facturas"),
    ("POST", "/api/comprobantes/1/emitir", "transmisión al SRI con la firma del contribuyente"),
    ("DELETE", "/api/configuracion/firma", "borrado del certificado .p12"),
    ("POST", "/api/cuentas/recibos", "registro de cobros"),
    ("POST", "/api/whatsapp/simulador", "emisión de comprobantes por el asistente"),
]


@pytest.mark.parametrize("metodo,ruta,que_permite", RUTAS_ESCRITURA)
def test_sin_sesion_no_se_puede_escribir(cliente_anonimo, metodo, ruta, que_permite):
    respuesta = cliente_anonimo.request(metodo, ruta, json={})
    assert respuesta.status_code == 401, (
        f"{metodo} {ruta} respondió {respuesta.status_code} sin credenciales. "
        f"Permite: {que_permite}."
    )


def test_el_simulador_de_whatsapp_exige_sesion(cliente_anonimo):
    """
    Aparte, porque es el peor de todos y no vive en un router protegido.

    El router de WhatsApp queda fuera del cierre global a propósito: Meta se
    autentica con la firma HMAC de su webhook, no con una sesión. Pero el
    simulador no lo llama Meta, lo llama el frontend, y termina en el
    orquestador, que emite comprobantes de verdad firmados con el certificado.
    Dos peticiones bastaban: una con los datos y otra con el texto "si".
    """
    respuesta = cliente_anonimo.post(
        "/api/whatsapp/simulador",
        json={"telefono": "0999000111", "texto": "hazle una factura a Juan por 3 sillas a 45"},
    )
    assert respuesta.status_code == 401, (
        f"El simulador respondió {respuesta.status_code}: se pueden emitir "
        f"comprobantes sin haber iniciado sesión."
    )


def test_lo_que_debe_seguir_abierto_sigue_abierto(cliente_anonimo):
    """
    El cierre no puede llevarse por delante lo que tiene que ser público.

    Si estos empezaran a pedir sesión, nadie podría registrarse ni entrar, y el
    webhook de Meta dejaría de funcionar. Se comprueba que NO devuelven 401;
    el código concreto da igual.
    """
    assert cliente_anonimo.get("/api/salud").status_code == 200

    # Un login con credenciales falsas debe fallar por credenciales (401 del
    # propio login), nunca por falta de sesión previa. Se distingue mirando que
    # el registro —que no exige nada— responda algo distinto de 401.
    registro = cliente_anonimo.post(
        "/api/auth/registro",
        json={"correo": "abierto@empresa.ec", "nombre": "Prueba", "contrasena": "clave12345"},
    )
    assert registro.status_code != 401, "El registro no puede exigir una sesión previa."

    # El webhook de Meta: sin firma HMAC válida rechaza, pero con 403, no con
    # 401 de sesión. Lo que importa es que no entre en el cierre global.
    webhook = cliente_anonimo.get("/api/whatsapp")
    assert webhook.status_code != 401, "El webhook de Meta no puede exigir sesión."
