"""Pruebas de los tipos de documento: secuenciales, notas y guías."""

from __future__ import annotations

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_docs") / "docs.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"

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
        PuntoEmision(codigo="001", nombre="Caja", secuencial_factura=135)
    ]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


def _crear_receptor(cliente, identificacion, rol, direccion="Av. Siempre Viva 123"):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": identificacion,
            "razon_social": f"EMPRESA {identificacion}",
            "rol": rol,
            "direccion": direccion,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


@pytest.fixture(scope="module")
def cliente_id(cliente):
    return _crear_receptor(cliente, "1790016919001", "Cliente")


@pytest.fixture(scope="module")
def proveedor_id(cliente):
    return _crear_receptor(cliente, "0992339411001", "Proveedor")


@pytest.fixture(scope="module")
def transportista_id(cliente):
    return _crear_receptor(cliente, "1791287541001", "Transportista")


DETALLE = [
    {
        "codigo_principal": "PROD-001",
        "descripcion": "Producto de prueba",
        "cantidad": "2",
        "precio_unitario": "100.00",
        "codigo_iva": "4",
    }
]


def _crear(cliente, tipo, receptor_id, **extra):
    return cliente.post(
        "/api/comprobantes",
        json={
            "tipo": tipo,
            "receptor_id": receptor_id,
            "establecimiento": "001",
            "punto_emision": "001",
            "detalles": DETALLE,
            **extra,
        },
    )


# --------------------------------------------------------------------------
# Secuenciales por tipo
# --------------------------------------------------------------------------


def test_factura_arranca_en_el_secuencial_configurado(cliente, cliente_id):
    """El usuario configuró 135 en Configuraciones; la primera factura usa ese."""
    factura = _crear(cliente, "Factura", cliente_id).json()
    assert factura["secuencial"] == 135
    assert factura["numero"] == "001-001-000000135"


def test_cada_tipo_tiene_su_propia_numeracion(cliente, cliente_id):
    """
    El SRI exige secuencias independientes: la nota de venta empieza en 1
    aunque las facturas ya vayan por 136.
    """
    nota_venta = _crear(cliente, "Nota de Venta", cliente_id).json()
    assert nota_venta["secuencial"] == 1

    siguiente_factura = _crear(cliente, "Factura", cliente_id).json()
    assert siguiente_factura["secuencial"] == 136

    segunda_nota = _crear(cliente, "Nota de Venta", cliente_id).json()
    assert segunda_nota["secuencial"] == 2


def test_el_secuencial_no_se_reusa_dentro_de_un_tipo(cliente, cliente_id):
    primero = _crear(cliente, "Cotización", cliente_id).json()
    segundo = _crear(cliente, "Cotización", cliente_id).json()
    assert segundo["secuencial"] == primero["secuencial"] + 1


def test_rechaza_tipo_desconocido(cliente, cliente_id):
    respuesta = _crear(cliente, "Comprobante Inventado", cliente_id)
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Notas de crédito y débito
# --------------------------------------------------------------------------


def test_nota_credito_exige_referencia_al_documento_modificado(cliente, cliente_id):
    """Sin los tres campos de referencia, el SRI la rechazaría."""
    respuesta = _crear(cliente, "Nota de Crédito", cliente_id)
    assert respuesta.status_code == 422
    assert "num_doc_modificado" in respuesta.json()["detail"]


def test_nota_credito_valida_se_crea(cliente, cliente_id):
    respuesta = _crear(
        cliente,
        "Nota de Crédito",
        cliente_id,
        cod_doc_modificado="01",
        num_doc_modificado="001-001-000000135",
        fecha_doc_modificado="2026-08-01",
        motivo="Devolución de mercadería",
    )
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["num_doc_modificado"] == "001-001-000000135"
    assert datos["motivo"] == "Devolución de mercadería"


def test_nota_debito_tambien_exige_referencia(cliente, cliente_id):
    respuesta = _crear(cliente, "Nota de Débito", cliente_id, motivo="Intereses")
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Liquidación de compra
# --------------------------------------------------------------------------


def test_liquidacion_exige_proveedor(cliente, cliente_id):
    """Se emite por cuenta de un proveedor; contra un cliente no tiene sentido."""
    respuesta = _crear(cliente, "Liquidación de Compra", cliente_id)
    assert respuesta.status_code == 422
    assert "proveedor" in respuesta.json()["detail"].lower()


def test_liquidacion_contra_proveedor_se_crea(cliente, proveedor_id):
    respuesta = _crear(cliente, "Liquidación de Compra", proveedor_id)
    assert respuesta.status_code == 201


# --------------------------------------------------------------------------
# Dirección obligatoria
# --------------------------------------------------------------------------


def test_cotizacion_no_exige_direccion(cliente):
    """No es comprobante electrónico: no viaja al SRI, así que no la exige."""
    from app.base_datos import SesionLocal
    from app.modelos_db import Receptor

    sesion = SesionLocal()
    receptor = Receptor(
        tipo_identificacion="Cédula",
        identificacion="0912345675",
        razon_social="SIN DIRECCION",
        rol="Cliente",
        direccion="",
    )
    sesion.add(receptor)
    sesion.commit()
    receptor_id = receptor.id
    sesion.close()

    assert _crear(cliente, "Cotización", receptor_id).status_code == 201
    # Pero una factura contra el mismo receptor sí falla.
    assert _crear(cliente, "Factura", receptor_id).status_code == 422


# --------------------------------------------------------------------------
# Anulación
# --------------------------------------------------------------------------


def test_anular_borrador(cliente, cliente_id):
    creado = _crear(cliente, "Factura", cliente_id).json()
    respuesta = cliente.post(f"/api/comprobantes/{creado['id']}/anular")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado_sri"] == "Anulado"


def test_un_operador_no_puede_anular(cliente, cliente_id):
    """Anular es una operación irreversible sobre la contabilidad: no basta con tener sesión."""
    creado = _crear(cliente, "Factura", cliente_id).json()

    cliente.post(
        "/api/auth/registro",
        json={"correo": "operador.doc@empresa.ec", "nombre": "Operador", "contrasena": "ClaveSegura123"},
    )
    token = cliente.post(
        "/api/auth/token",
        data={"username": "operador.doc@empresa.ec", "password": "ClaveSegura123"},
    ).json()["access_token"]

    respuesta = cliente.post(
        f"/api/comprobantes/{creado['id']}/anular",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert respuesta.status_code == 403


def test_no_se_anula_un_comprobante_autorizado(cliente, cliente_id):
    """Un autorizado se revierte con nota de crédito, no anulándolo."""
    from app.base_datos import SesionLocal
    from app.modelos_db import Comprobante

    creado = _crear(cliente, "Factura", cliente_id).json()

    sesion = SesionLocal()
    comprobante = sesion.get(Comprobante, creado["id"])
    comprobante.estado_sri = "Autorizado"
    sesion.commit()
    sesion.close()

    respuesta = cliente.post(f"/api/comprobantes/{creado['id']}/anular")
    assert respuesta.status_code == 409
    assert "nota de crédito" in respuesta.json()["detail"].lower()


# --------------------------------------------------------------------------
# Filtros del listado
# --------------------------------------------------------------------------


def test_listado_filtra_por_tipo(cliente):
    respuesta = cliente.get("/api/comprobantes?tipo=Nota de Venta")
    assert respuesta.status_code == 200
    assert all(item["tipo"] == "Nota de Venta" for item in respuesta.json())


def test_xml_solo_para_comprobantes_electronicos(cliente, cliente_id):
    cotizacion = _crear(cliente, "Cotización", cliente_id).json()
    respuesta = cliente.get(f"/api/comprobantes/{cotizacion['id']}/xml")
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Guías de remisión
# --------------------------------------------------------------------------


def _guia(transportista_id, **extra):
    return {
        "establecimiento": "001",
        "punto_emision": "001",
        "fecha_inicio": str(date.today()),
        "fecha_fin": str(date.today() + timedelta(days=1)),
        "motivo_traslado": "Venta",
        "tipo_transporte": "Privado",
        "transportista_id": transportista_id,
        "placa": "pba-1234",
        "direccion_partida": "Av. Amazonas N21-147, Quito",
        "direccion_llegada": "Km 14.5 vía Daule, Guayaquil",
        "items": [{"codigo": "PROD-001", "descripcion": "Laptop", "cantidad": "3"}],
        **extra,
    }


def test_crear_guia(cliente, transportista_id):
    respuesta = cliente.post("/api/guias", json=_guia(transportista_id))
    assert respuesta.status_code == 201, respuesta.text

    datos = respuesta.json()
    assert datos["numero"] == "001-001-000000001"
    assert datos["placa"] == "PBA-1234"  # se normaliza a mayúsculas
    assert len(datos["items"]) == 1


def test_guia_exige_transportista(cliente, cliente_id):
    """Un cliente en el campo del transportista produce una guía incorrecta."""
    respuesta = cliente.post("/api/guias", json=_guia(cliente_id))
    assert respuesta.status_code == 422
    assert "transportista" in respuesta.json()["detail"].lower()


def test_guia_rechaza_fecha_fin_anterior(cliente, transportista_id):
    respuesta = cliente.post(
        "/api/guias",
        json=_guia(
            transportista_id,
            fecha_inicio=str(date.today()),
            fecha_fin=str(date.today() - timedelta(days=1)),
        ),
    )
    assert respuesta.status_code == 422


def test_guia_exige_al_menos_un_item(cliente, transportista_id):
    respuesta = cliente.post("/api/guias", json=_guia(transportista_id, items=[]))
    assert respuesta.status_code == 422


def test_guia_exige_direcciones(cliente, transportista_id):
    respuesta = cliente.post("/api/guias", json=_guia(transportista_id, direccion_llegada=""))
    assert respuesta.status_code == 422


def test_guias_tienen_su_propia_numeracion(cliente, transportista_id):
    """No comparten serie con las facturas."""
    segunda = cliente.post("/api/guias", json=_guia(transportista_id)).json()
    assert segunda["secuencial"] if "secuencial" in segunda else True
    assert segunda["numero"] == "001-001-000000002"


def test_listar_y_filtrar_guias(cliente, transportista_id):
    respuesta = cliente.get("/api/guias?buscar=pba")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) >= 1
    assert int(respuesta.headers["X-Total-Registros"]) >= 1


def test_anular_guia(cliente, transportista_id):
    creada = cliente.post("/api/guias", json=_guia(transportista_id)).json()
    respuesta = cliente.post(f"/api/guias/{creada['id']}/anular")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado_sri"] == "Anulado"
