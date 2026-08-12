"""
Cuentas por cobrar: cuotas, recibos y el estado de pago del comprobante.

Este módulo movía dinero y no tenía ni una prueba. El fallo que documentan los
dos primeros casos —una factura cobrada al 100 % que seguía diciendo «Por
Cobrar»— estuvo en producción hasta que se buscó a propósito: las verificaciones
manuales de su tanda probaron el reparto en cuotas, que es el camino que sí
funcionaba, y nadie cobró una factura al contado.
"""

from __future__ import annotations

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
    base = tmp_path_factory.mktemp("bd") / "cuentas.db"
    import os

    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion
    from app.modelos_db import Empresa, Establecimiento, PuntoEmision, Receptor

    crear_tablas()

    sesion = SesionLocal()
    empresa = Empresa(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        direccion_matriz="Av. Amazonas N21-147",
        ambiente="1",
    )
    est = Establecimiento(codigo="001", nombre="Matriz", direccion="Av. Amazonas")
    est.puntos_emision = [PuntoEmision(codigo="001", nombre="Caja", secuencial_factura=1)]
    empresa.establecimientos = [est]
    sesion.add(empresa)
    sesion.add(
        Receptor(
            tipo_identificacion="RUC",
            identificacion="0992339411001",
            razon_social="CLIENTE DEMO S.A.",
            rol="Cliente",
        )
    )
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


def _factura(total: str, numero: str):
    """Crea una factura autorizada directamente en la base."""
    from app.base_datos import SesionLocal
    from app.modelos_db import Comprobante, Receptor

    sesion = SesionLocal()
    receptor = sesion.query(Receptor).first()
    comp = Comprobante(
        tipo="Factura",
        numero=numero,
        establecimiento="001",
        punto_emision="001",
        secuencial=int(numero.split("-")[-1]),
        fecha_emision=date(2026, 8, 1),
        receptor_id=receptor.id,
        receptor_identificacion=receptor.identificacion,
        receptor_razon_social=receptor.razon_social,
        total_sin_impuestos=Decimal(total),
        importe_total=Decimal(total),
        estado_sri="Autorizado",
    )
    sesion.add(comp)
    sesion.commit()
    identificador = comp.id
    sesion.close()
    return identificador


def _estado_pago(comprobante_id: int) -> str:
    from app.base_datos import SesionLocal
    from app.modelos_db import Comprobante

    sesion = SesionLocal()
    estado = sesion.get(Comprobante, comprobante_id).estado_pago
    sesion.close()
    return estado


# ---------------------------------------------------------------------------
# El fallo que motivó este archivo
# ---------------------------------------------------------------------------


def test_un_recibo_sin_cuotas_deja_la_factura_pagada(cliente):
    """
    Una venta al contado se cobra de una vez, sin plan de cuotas.

    `_recalcular_comprobante` sumaba solo `Cuota.cobrado`, así que este recibo
    valía cero para el estado y la factura se quedaba «Por Cobrar» para siempre.
    """
    comp = _factura("100.00", "001-001-000000001")
    assert _estado_pago(comp) == "Por Cobrar"

    respuesta = cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 100.00, "forma_pago": "Efectivo"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _estado_pago(comp) == "Pagado"


def test_un_recibo_parcial_sin_cuotas_deja_la_factura_en_parcial(cliente):
    comp = _factura("100.00", "001-001-000000002")

    cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 40.00, "forma_pago": "Efectivo"},
    )
    assert _estado_pago(comp) == "Parcial"

    cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 60.00, "forma_pago": "Efectivo"},
    )
    assert _estado_pago(comp) == "Pagado"


def test_anular_un_recibo_directo_devuelve_la_factura_a_por_cobrar(cliente):
    """Anular es la forma de deshacer un cobro: no puede seguir contando."""
    comp = _factura("50.00", "001-001-000000003")

    recibo = cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 50.00, "forma_pago": "Efectivo"},
    ).json()
    assert _estado_pago(comp) == "Pagado"

    anulacion = cliente.post(f"/api/cuentas/recibos/{recibo['id']}/anular")
    assert anulacion.status_code == 200, anulacion.text
    assert _estado_pago(comp) == "Por Cobrar"


# ---------------------------------------------------------------------------
# El reparto en cuotas: la regla del centavo
# ---------------------------------------------------------------------------


def test_el_resto_del_reparto_se_acumula_en_la_ultima_cuota(cliente):
    """217,35 en tres no da tres cuotas iguales. El resto va a la última."""
    comp = _factura("217.35", "001-001-000000004")

    respuesta = cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 3, "dias_entre_cuotas": 30},
    )
    assert respuesta.status_code == 200, respuesta.text

    montos = [Decimal(str(c["monto"])) for c in respuesta.json()]
    assert len(montos) == 3
    assert sum(montos) == Decimal("217.35"), "las cuotas deben sumar el total exacto"
    assert montos[0] == montos[1], "las primeras cuotas son iguales entre sí"
    assert montos[-1] >= montos[0], "el resto se acumula en la última"


def test_un_sobrepago_contra_una_cuota_se_rechaza(cliente):
    comp = _factura("90.00", "001-001-000000005")
    cuotas = cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 3, "dias_entre_cuotas": 30},
    ).json()

    primera = cuotas[0]
    respuesta = cliente.post(
        "/api/cuentas/recibos",
        json={"cuota_id": primera["id"], "monto": 999.00, "forma_pago": "Efectivo"},
    )
    assert respuesta.status_code == 422
    assert "cuota debe" in respuesta.text.lower()


def test_dos_abonos_contra_la_misma_cuota_la_saldan(cliente):
    """
    Un cliente puede abonar de a poco: dos recibos contra una misma cuota.

    Es la razón de que cuota y recibo sean tablas distintas; un solo campo
    «pagado» perdería estos dos movimientos de caja.
    """
    comp = _factura("60.00", "001-001-000000006")
    cuotas = cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 2, "dias_entre_cuotas": 30},
    ).json()
    cuota = cuotas[0]
    monto = Decimal(str(cuota["monto"]))

    cliente.post(
        "/api/cuentas/recibos",
        json={"cuota_id": cuota["id"], "monto": float(monto / 2), "forma_pago": "Efectivo"},
    )
    cliente.post(
        "/api/cuentas/recibos",
        json={"cuota_id": cuota["id"], "monto": float(monto / 2), "forma_pago": "Efectivo"},
    )

    listado = cliente.get("/api/cuentas/cuotas").json()
    actualizada = next(c for c in listado if c["id"] == cuota["id"])
    assert Decimal(str(actualizada["saldo"])) == Decimal("0.00")
    assert actualizada["estado"] == "Cobrada"


# ---------------------------------------------------------------------------
# El abono suelto contra un comprobante con cuotas: el criterio FIFO
# ---------------------------------------------------------------------------


def test_un_abono_suelto_se_reparte_fifo_entre_las_cuotas(cliente):
    """
    Antes, un recibo contra `comprobante_id` sin `cuota_id` no bajaba ninguna
    cuota: la agenda seguía mostrando pendiente lo que en caja ya se había
    cobrado. Ahora se reparte contra las cuotas más próximas a vencer primero.
    """
    comp = _factura("90.00", "001-001-000000008")
    cuotas = cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 3, "dias_entre_cuotas": 30},
    ).json()
    cuotas.sort(key=lambda c: c["numero"])

    respuesta = cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 45.00, "forma_pago": "Efectivo"},
    )
    assert respuesta.status_code == 201, respuesta.text

    listado = {c["id"]: c for c in cliente.get("/api/cuentas/cuotas").json()}
    primera, segunda, tercera = (listado[c["id"]] for c in cuotas)
    assert primera["estado"] == "Cobrada"
    assert Decimal(str(segunda["cobrado"])) == Decimal("15.00")
    assert Decimal(str(tercera["cobrado"])) == Decimal("0.00")
    assert _estado_pago(comp) == "Parcial"


def test_un_abono_suelto_que_sobra_a_las_cuotas_queda_como_recibo_directo(cliente):
    """Si el abono cubre todas las cuotas y sobra, el resto no se inventa una cuota nueva."""
    comp = _factura("50.00", "001-001-000000009")
    cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 2, "dias_entre_cuotas": 30},
    )

    respuesta = cliente.post(
        "/api/cuentas/recibos",
        json={"comprobante_id": comp, "monto": 70.00, "forma_pago": "Efectivo"},
    )
    assert respuesta.status_code == 201, respuesta.text
    assert _estado_pago(comp) == "Pagado"

    listado = cliente.get("/api/cuentas/cuotas").json()
    for cuota in listado:
        if cuota.get("comprobante_id") == comp:
            assert cuota["estado"] == "Cobrada"


def test_el_saldo_se_calcula_y_no_se_guarda(cliente):
    """`saldo` es `monto - cobrado`: un saldo almacenado se desincroniza."""
    comp = _factura("80.00", "001-001-000000007")
    cuotas = cliente.post(
        f"/api/cuentas/comprobantes/{comp}/cuotas",
        json={"cuotas": 2, "dias_entre_cuotas": 15},
    ).json()

    for cuota in cuotas:
        assert Decimal(str(cuota["saldo"])) == Decimal(str(cuota["monto"])) - Decimal(
            str(cuota["cobrado"])
        )
