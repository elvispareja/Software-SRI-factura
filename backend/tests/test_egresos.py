"""
Pruebas de egresos, anticipos y facturación recurrente.

Lo que más se vigila aquí son las reglas que impiden descuadrar la caja: que un
gasto con pagos no se borre, que un anticipo no se aplique por más de su saldo,
y que una plantilla recurrente no emita dos veces el mismo período.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_egresos") / "egresos.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-egresos"

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
    establecimiento.puntos_emision = [PuntoEmision(codigo="001", nombre="Caja")]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


@pytest.fixture(scope="module")
def proveedor_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "PROVEEDOR DEMO S.A.",
            "direccion": "Km 14.5 via Daule",
            "rol": "Proveedor",
        },
    ).json()["id"]


@pytest.fixture(scope="module")
def cliente_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "Cédula",
            "identificacion": "1710034065",
            "razon_social": "JUAN PEREZ",
            "direccion": "Quito, Av. 6 de Diciembre",
            "rol": "Cliente",
        },
    ).json()["id"]


@pytest.fixture(scope="module")
def tipo_id(cliente):
    respuesta = cliente.post(
        "/api/egresos/tipos", json={"nombre": "Servicios básicos", "deducible": True}
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


# --------------------------------------------------------------------------
# Tipos de gasto
# --------------------------------------------------------------------------


def test_no_se_repite_el_nombre_de_un_tipo(cliente, tipo_id):
    """Dos categorías iguales parten el reporte en dos filas que suman lo mismo."""
    respuesta = cliente.post("/api/egresos/tipos", json={"nombre": "Servicios básicos"})

    assert respuesta.status_code == 409
    assert "Ya existe" in respuesta.json()["detail"]


def test_el_tipo_se_desactiva_pero_no_se_borra(cliente):
    """Borrarlo dejaría sin categoría los gastos de meses ya cerrados."""
    creado = cliente.post("/api/egresos/tipos", json={"nombre": "Temporal"}).json()

    assert cliente.delete(f"/api/egresos/tipos/{creado['id']}").status_code == 204

    activos = cliente.get("/api/egresos/tipos").json()
    assert all(t["id"] != creado["id"] for t in activos)

    todos = cliente.get("/api/egresos/tipos?incluir_inactivos=true").json()
    inactivo = next(t for t in todos if t["id"] == creado["id"])
    assert inactivo["estado"] == "Inactivo"


# --------------------------------------------------------------------------
# Gastos
# --------------------------------------------------------------------------


def _crear_gasto(cliente, tipo_id, proveedor_id, **extra):
    cuerpo = {
        "fecha": "2026-08-05",
        "concepto": "Planilla de luz",
        "tipo_id": tipo_id,
        "proveedor_id": proveedor_id,
        "documento": "001-001-000000777",
        "fecha_documento": "2026-08-01",
        "subtotal": "100.00",
        "iva": "15.00",
        **extra,
    }
    return cliente.post("/api/egresos/gastos", json=cuerpo)


def test_el_gasto_suma_su_total(cliente, tipo_id, proveedor_id):
    respuesta = _crear_gasto(cliente, tipo_id, proveedor_id)

    assert respuesta.status_code == 201, respuesta.text
    gasto = respuesta.json()

    assert Decimal(gasto["total"]) == Decimal("115.00")
    assert gasto["estado_pago"] == "Por Pagar"
    # Se copia el nombre del proveedor, no solo su id.
    assert gasto["proveedor_razon_social"] == "PROVEEDOR DEMO S.A."


def test_el_gasto_rechaza_importes_negativos(cliente, tipo_id, proveedor_id):
    respuesta = _crear_gasto(cliente, tipo_id, proveedor_id, subtotal="-10")

    assert respuesta.status_code == 422
    assert "negativos" in respuesta.text


def test_el_gasto_rechaza_un_tipo_inexistente(cliente, proveedor_id):
    respuesta = _crear_gasto(cliente, 9999, proveedor_id)

    assert respuesta.status_code == 404
    assert "tipo de gasto" in respuesta.json()["detail"]


def test_los_gastos_se_filtran_por_tipo_y_fecha(cliente, tipo_id, proveedor_id):
    _crear_gasto(cliente, tipo_id, proveedor_id, fecha="2026-01-15", concepto="Enero")

    agosto = cliente.get("/api/egresos/gastos?desde=2026-08-01&hasta=2026-08-31").json()
    assert all(g["fecha"].startswith("2026-08") for g in agosto)

    por_tipo = cliente.get(f"/api/egresos/gastos?tipo_id={tipo_id}").json()
    assert all(g["tipo_id"] == tipo_id for g in por_tipo)


def test_buscar_gastos_por_documento(cliente, tipo_id, proveedor_id):
    _crear_gasto(cliente, tipo_id, proveedor_id, documento="001-001-000000999")

    encontrados = cliente.get("/api/egresos/gastos?buscar=000000999").json()
    assert any(g["documento"] == "001-001-000000999" for g in encontrados)


# --------------------------------------------------------------------------
# Egresos (pagos)
# --------------------------------------------------------------------------


def test_pagar_un_gasto_entero_lo_marca_pagado(cliente, tipo_id, proveedor_id):
    gasto = _crear_gasto(cliente, tipo_id, proveedor_id).json()

    pago = cliente.post(
        "/api/egresos",
        json={
            "fecha": "2026-08-10",
            "concepto": "Pago planilla de luz",
            "beneficiario": "PROVEEDOR DEMO S.A.",
            "monto": "115.00",
            "forma_pago": "Transferencia",
            "gasto_id": gasto["id"],
        },
    )
    assert pago.status_code == 201, pago.text

    assert cliente.get(f"/api/egresos/gastos/{gasto['id']}").json()["estado_pago"] == "Pagado"


def test_un_pago_parcial_deja_el_gasto_en_parcial(cliente, tipo_id, proveedor_id):
    gasto = _crear_gasto(cliente, tipo_id, proveedor_id).json()

    cliente.post(
        "/api/egresos",
        json={"concepto": "Abono", "monto": "50.00", "gasto_id": gasto["id"]},
    )

    assert cliente.get(f"/api/egresos/gastos/{gasto['id']}").json()["estado_pago"] == "Parcial"


def test_dos_pagos_parciales_saldan_el_gasto(cliente, tipo_id, proveedor_id):
    """Se compara contra la suma de todos los pagos, no solo contra el último."""
    gasto = _crear_gasto(cliente, tipo_id, proveedor_id).json()

    cliente.post("/api/egresos", json={"concepto": "1/2", "monto": "60.00", "gasto_id": gasto["id"]})
    cliente.post("/api/egresos", json={"concepto": "2/2", "monto": "55.00", "gasto_id": gasto["id"]})

    assert cliente.get(f"/api/egresos/gastos/{gasto['id']}").json()["estado_pago"] == "Pagado"


def test_un_pago_de_cero_se_rechaza(cliente):
    respuesta = cliente.post("/api/egresos", json={"concepto": "Nada", "monto": "0"})

    assert respuesta.status_code == 422
    assert "mayor que cero" in respuesta.text


def test_anular_el_pago_devuelve_el_gasto_a_pendiente(cliente, tipo_id, proveedor_id):
    gasto = _crear_gasto(cliente, tipo_id, proveedor_id).json()
    pago = cliente.post(
        "/api/egresos",
        json={"concepto": "Pago", "monto": "115.00", "gasto_id": gasto["id"]},
    ).json()

    assert cliente.get(f"/api/egresos/gastos/{gasto['id']}").json()["estado_pago"] == "Pagado"

    anulado = cliente.post(f"/api/egresos/{pago['id']}/anular")
    assert anulado.status_code == 200
    assert anulado.json()["estado"] == "Anulado"

    assert cliente.get(f"/api/egresos/gastos/{gasto['id']}").json()["estado_pago"] == "Por Pagar"


def test_no_se_anula_dos_veces(cliente):
    pago = cliente.post("/api/egresos", json={"concepto": "X", "monto": "10"}).json()

    cliente.post(f"/api/egresos/{pago['id']}/anular")
    segunda = cliente.post(f"/api/egresos/{pago['id']}/anular")

    assert segunda.status_code == 409


def test_no_se_borra_un_gasto_con_pagos(cliente, tipo_id, proveedor_id):
    """Borrarlo dejaría el egreso apuntando a nada y la caja sin explicar."""
    gasto = _crear_gasto(cliente, tipo_id, proveedor_id).json()
    cliente.post("/api/egresos", json={"concepto": "Pago", "monto": "20", "gasto_id": gasto["id"]})

    respuesta = cliente.delete(f"/api/egresos/gastos/{gasto['id']}")

    assert respuesta.status_code == 409
    assert "pagos registrados" in respuesta.json()["detail"]


def test_el_resumen_separa_gastado_de_pagado(cliente):
    resumen = cliente.get("/api/egresos/resumen/periodo?desde=2026-08-01&hasta=2026-08-31").json()

    for clave in ("gastos", "total_gastos", "total_pagos", "pendiente"):
        assert clave in resumen

    assert Decimal(resumen["total_gastos"]) > 0


# --------------------------------------------------------------------------
# Anticipos
# --------------------------------------------------------------------------


def test_crear_anticipo(cliente, cliente_id):
    respuesta = cliente.post(
        "/api/anticipos",
        json={
            "fecha": "2026-08-01",
            "tipo": "ARD",
            "receptor_id": cliente_id,
            "detalle": "Anticipo proyecto fase 1",
            "monto": "1000.00",
        },
    )

    assert respuesta.status_code == 201, respuesta.text
    anticipo = respuesta.json()

    assert Decimal(anticipo["saldo"]) == Decimal("1000.00")
    assert anticipo["estado"] == "Pendiente"
    assert anticipo["receptor_razon_social"] == "JUAN PEREZ"


def test_el_tipo_de_anticipo_se_valida(cliente, cliente_id):
    respuesta = cliente.post(
        "/api/anticipos",
        json={"receptor_id": cliente_id, "tipo": "XXX", "monto": "10"},
    )

    assert respuesta.status_code == 422
    assert "ARD" in respuesta.text


def test_aplicar_parte_del_anticipo_deja_saldo(cliente, cliente_id):
    anticipo = cliente.post(
        "/api/anticipos",
        json={"receptor_id": cliente_id, "monto": "500.00", "detalle": "Abono"},
    ).json()

    aplicado = cliente.post(
        f"/api/anticipos/{anticipo['id']}/aplicar", json={"monto": "200.00"}
    )

    assert aplicado.status_code == 200
    datos = aplicado.json()
    assert Decimal(datos["facturado"]) == Decimal("200.00")
    assert Decimal(datos["saldo"]) == Decimal("300.00")
    assert datos["estado"] == "Parcial"


def test_aplicarlo_entero_lo_marca_aplicado(cliente, cliente_id):
    anticipo = cliente.post(
        "/api/anticipos", json={"receptor_id": cliente_id, "monto": "300.00"}
    ).json()

    datos = cliente.post(
        f"/api/anticipos/{anticipo['id']}/aplicar", json={"monto": "300.00"}
    ).json()

    assert Decimal(datos["saldo"]) == Decimal("0")
    assert datos["estado"] == "Aplicado"


def test_no_se_aplica_mas_de_lo_que_queda(cliente, cliente_id):
    """El saldo llegaría a negativo, y un anticipo que debe dinero no significa nada."""
    anticipo = cliente.post(
        "/api/anticipos", json={"receptor_id": cliente_id, "monto": "100.00"}
    ).json()

    respuesta = cliente.post(
        f"/api/anticipos/{anticipo['id']}/aplicar", json={"monto": "150.00"}
    )

    assert respuesta.status_code == 422
    assert "disponibles" in respuesta.json()["detail"]


def test_no_se_anula_un_anticipo_ya_aplicado(cliente, cliente_id):
    anticipo = cliente.post(
        "/api/anticipos", json={"receptor_id": cliente_id, "monto": "80.00"}
    ).json()
    cliente.post(f"/api/anticipos/{anticipo['id']}/aplicar", json={"monto": "40.00"})

    respuesta = cliente.post(f"/api/anticipos/{anticipo['id']}/anular")

    assert respuesta.status_code == 409
    assert "nota de crédito" in respuesta.json()["detail"]


def test_los_anticipos_se_filtran_por_estado(cliente, cliente_id):
    pendientes = cliente.get("/api/anticipos?estado=Pendiente").json()
    assert all(a["estado"] == "Pendiente" for a in pendientes)
