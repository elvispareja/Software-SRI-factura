"""Pruebas del API: catálogos, comprobantes, RIDE y XML."""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    """API sobre una base SQLite temporal, aislada de la de desarrollo."""
    base = tmp_path_factory.mktemp("bd") / "pruebas.db"
    import os

    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"

    # Se importa después de fijar la variable: el motor se crea al importar.
    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion
    from app.modelos_db import Empresa, Establecimiento, PuntoEmision

    crear_tablas()

    sesion = SesionLocal()
    empresa = Empresa(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        direccion_matriz="Av. Amazonas N21-147",
        ambiente="1",
    )
    establecimiento = Establecimiento(codigo="001", nombre="Matriz", direccion="Av. Amazonas")
    establecimiento.puntos_emision = [
        PuntoEmision(codigo="001", nombre="Caja", secuencial_factura=1)
    ]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


@pytest.fixture(scope="module")
def receptor_id(cliente):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "PLASTICOS DEL LITORAL PLASTLIT S.A.",
            "direccion": "Km 14.5 via Daule",
            "correo": "compras@plastlit.com",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


def test_salud(cliente):
    respuesta = cliente.get("/api/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ok"


# --------------------------------------------------------------------------
# Validación en el servidor
# --------------------------------------------------------------------------


def test_rechaza_ruc_con_verificador_invalido(cliente):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "1790016919002001",
            "razon_social": "INVALIDO",
            "direccion": "Alguna",
        },
    )
    assert respuesta.status_code == 422


def test_rechaza_receptor_sin_direccion(cliente):
    """La dirección es obligatoria: el XML del SRI la exige."""
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "Cédula",
            "identificacion": "0912345675",
            "razon_social": "SIN DIRECCION",
            "direccion": "",
        },
    )
    assert respuesta.status_code == 422


def test_rechaza_identificacion_duplicada(cliente, receptor_id):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "OTRA EMPRESA",
            "direccion": "Otra dirección",
        },
    )
    assert respuesta.status_code == 409


def test_rechaza_codigo_iva_desconocido(cliente):
    respuesta = cliente.post(
        "/api/articulos",
        json={"codigo": "X-999", "nombre": "Raro", "codigo_iva": "99"},
    )
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Catálogos
# --------------------------------------------------------------------------


def test_listar_receptores_devuelve_total_en_cabecera(cliente, receptor_id):
    respuesta = cliente.get("/api/receptores")
    assert respuesta.status_code == 200
    assert int(respuesta.headers["X-Total-Registros"]) >= 1


def test_busqueda_de_receptores_filtra(cliente, receptor_id):
    assert len(cliente.get("/api/receptores?buscar=plastlit").json()) == 1
    assert len(cliente.get("/api/receptores?buscar=inexistente").json()) == 0


def test_crear_y_listar_articulos(cliente):
    respuesta = cliente.post(
        "/api/articulos",
        json={
            "codigo": "PROD-001",
            "nombre": "Laptop Dell XPS 13",
            "tipo": "Producto",
            "codigo_iva": "4",
            "costo": "950.00",
            "precio": "1200.00",
            "stock": "15",
        },
    )
    assert respuesta.status_code == 201

    respuesta = cliente.post(
        "/api/articulos",
        json={"codigo": "PROD-003", "nombre": "Pan comun", "codigo_iva": "0", "precio": "1.85"},
    )
    assert respuesta.status_code == 201
    assert len(cliente.get("/api/articulos").json()) == 2


def test_desactivar_no_borra(cliente):
    creado = cliente.post(
        "/api/articulos", json={"codigo": "TEMP-1", "nombre": "Temporal"}
    ).json()
    assert cliente.delete(f"/api/articulos/{creado['id']}").status_code == 204
    assert cliente.get(f"/api/articulos/{creado['id']}").json()["estado"] == "Inactivo"


# --------------------------------------------------------------------------
# Comprobantes
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def comprobante(cliente, receptor_id):
    respuesta = cliente.post(
        "/api/comprobantes",
        json={
            "receptor_id": receptor_id,
            "establecimiento": "001",
            "punto_emision": "001",
            "detalles": [
                {
                    "codigo_principal": "PROD-001",
                    "descripcion": "Laptop Dell XPS 13",
                    "cantidad": "1",
                    "precio_unitario": "1200.00",
                    "codigo_iva": "4",
                },
                {
                    "codigo_principal": "PROD-003",
                    "descripcion": "Pan comun 500g",
                    "cantidad": "10",
                    "precio_unitario": "1.85",
                    "codigo_iva": "0",
                },
            ],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_comprobante_calcula_totales_con_iva_mixto(comprobante):
    assert Decimal(comprobante["total_sin_impuestos"]) == Decimal("1218.500000")
    assert Decimal(comprobante["total_iva"]) == Decimal("180.000000")
    assert Decimal(comprobante["importe_total"]) == Decimal("1398.500000")


def test_comprobante_toma_el_secuencial_del_punto_de_emision(comprobante):
    assert comprobante["numero"] == "001-001-000000001"


def test_el_secuencial_no_se_reusa(cliente, receptor_id):
    """Dos comprobantes seguidos nunca comparten número."""
    cuerpo = {
        "receptor_id": receptor_id,
        "establecimiento": "001",
        "punto_emision": "001",
        "detalles": [
            {
                "codigo_principal": "X",
                "descripcion": "Item",
                "cantidad": "1",
                "precio_unitario": "10.00",
                "codigo_iva": "4",
            }
        ],
    }
    primero = cliente.post("/api/comprobantes", json=cuerpo).json()
    segundo = cliente.post("/api/comprobantes", json=cuerpo).json()
    assert primero["numero"] != segundo["numero"]
    assert segundo["secuencial"] if "secuencial" in segundo else True


def test_rechaza_punto_de_emision_inexistente(cliente, receptor_id):
    respuesta = cliente.post(
        "/api/comprobantes",
        json={
            "receptor_id": receptor_id,
            "establecimiento": "099",
            "punto_emision": "099",
            "detalles": [
                {
                    "codigo_principal": "X",
                    "descripcion": "Item",
                    "cantidad": "1",
                    "precio_unitario": "1.00",
                }
            ],
        },
    )
    assert respuesta.status_code == 404


def test_rechaza_comprobante_sin_detalles(cliente, receptor_id):
    respuesta = cliente.post(
        "/api/comprobantes",
        json={"receptor_id": receptor_id, "establecimiento": "001", "punto_emision": "001", "detalles": []},
    )
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# XML y RIDE
# --------------------------------------------------------------------------


def test_descarga_xml_bien_formado(cliente, comprobante):
    respuesta = cliente.get(f"/api/comprobantes/{comprobante['id']}/xml")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("application/xml")

    from lxml import etree

    raiz = etree.fromstring(respuesta.content)
    assert raiz.tag == "factura"
    assert raiz.findtext("infoFactura/importeTotal") == "1398.50"


def test_ride_genera_un_pdf(cliente, comprobante):
    respuesta = cliente.get(f"/api/comprobantes/{comprobante['id']}/ride")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/pdf"
    # Firma del formato PDF.
    assert respuesta.content[:5] == b"%PDF-"
    assert len(respuesta.content) > 1500


# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------


def test_obtener_empresa(cliente):
    respuesta = cliente.get("/api/configuracion/empresa")
    assert respuesta.status_code == 200
    assert respuesta.json()["ruc"] == "1790016919001"


def test_guardar_empresa_rechaza_ruc_invalido(cliente):
    respuesta = cliente.put(
        "/api/configuracion/empresa",
        json={
            "ruc": "1234567890123",
            "razon_social": "X",
            "direccion_matriz": "Y",
        },
    )
    assert respuesta.status_code == 422


def test_listar_establecimientos_con_puntos(cliente):
    respuesta = cliente.get("/api/configuracion/establecimientos")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["puntos_emision"][0]["codigo"] == "001"
