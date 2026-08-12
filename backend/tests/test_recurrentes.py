"""
Pruebas de la facturación recurrente.

Lo que se vigila: que la fecha avance bien (fin de mes incluido), que la
plantilla no emita dos veces el mismo período, y que la factura resultante sea
una factura normal —numerada por el mismo contador que las demás—, porque ante
el SRI no hay tal cosa como una "factura recurrente".
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
    base = tmp_path_factory.mktemp("bd_recurrentes") / "recurrentes.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-recurrentes"

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
def receptor_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "ARRENDATARIO S.A.",
            "direccion": "Av. República 1234",
            "rol": "Cliente",
        },
    ).json()["id"]


def _crear(cliente, receptor_id, **extra):
    cuerpo = {
        "nombre": "Arriendo local comercial",
        "receptor_id": receptor_id,
        "periodicidad": "Mensual",
        "proxima_emision": "2026-08-01",
        "lineas": [
            {
                "codigo_principal": "ARR-001",
                "descripcion": "Arriendo mensual",
                "cantidad": "1",
                "precio_unitario": "800.00",
                "codigo_iva": "4",
            }
        ],
        **extra,
    }
    return cliente.post("/api/recurrentes", json=cuerpo)


# --------------------------------------------------------------------------
# Cálculo de fechas
# --------------------------------------------------------------------------


def test_sumar_meses_respeta_el_fin_de_mes():
    """
    El 31 de enero más un mes es el 28 de febrero, no el 3 de marzo: una
    suscripción que se cobra a fin de mes debe seguir cobrándose a fin de mes.
    """
    from app.servicios.recurrentes import sumar_meses

    assert sumar_meses(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert sumar_meses(date(2026, 3, 31), 1) == date(2026, 4, 30)
    assert sumar_meses(date(2026, 1, 15), 1) == date(2026, 2, 15)
    # 2028 es bisiesto.
    assert sumar_meses(date(2028, 1, 31), 1) == date(2028, 2, 29)


def test_sumar_meses_cruza_el_año():
    from app.servicios.recurrentes import sumar_meses

    assert sumar_meses(date(2026, 12, 10), 1) == date(2027, 1, 10)
    assert sumar_meses(date(2026, 6, 30), 12) == date(2027, 6, 30)


def test_cada_periodicidad_avanza_lo_suyo():
    from app.servicios.recurrentes import siguiente_fecha

    origen = date(2026, 8, 1)

    assert siguiente_fecha(origen, "Semanal") == date(2026, 8, 8)
    assert siguiente_fecha(origen, "Quincenal") == date(2026, 8, 16)
    assert siguiente_fecha(origen, "Mensual") == date(2026, 9, 1)
    assert siguiente_fecha(origen, "Bimestral") == date(2026, 10, 1)
    assert siguiente_fecha(origen, "Trimestral") == date(2026, 11, 1)
    assert siguiente_fecha(origen, "Anual") == date(2027, 8, 1)


# --------------------------------------------------------------------------
# Plantillas
# --------------------------------------------------------------------------


def test_crear_plantilla_calcula_su_total(cliente, receptor_id):
    respuesta = _crear(cliente, receptor_id)

    assert respuesta.status_code == 201, respuesta.text
    plantilla = respuesta.json()

    # 800 + 15% de IVA.
    assert Decimal(plantilla["total"]) == Decimal("920.00")
    assert plantilla["emitidas"] == 0
    assert plantilla["activa"] is True


def test_una_periodicidad_desconocida_se_rechaza(cliente, receptor_id):
    respuesta = _crear(cliente, receptor_id, periodicidad="Cada luna llena")

    assert respuesta.status_code == 422
    assert "Periodicidad desconocida" in respuesta.text


def test_la_fecha_de_fin_no_puede_ser_anterior(cliente, receptor_id):
    respuesta = _crear(cliente, receptor_id, hasta="2026-07-01")

    assert respuesta.status_code == 422
    assert "anterior" in respuesta.text


def test_una_plantilla_exige_al_menos_una_linea(cliente, receptor_id):
    respuesta = _crear(cliente, receptor_id, lineas=[])

    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Emisión
# --------------------------------------------------------------------------


def test_emitir_genera_una_factura_en_borrador(cliente, receptor_id):
    plantilla = _crear(cliente, receptor_id).json()

    respuesta = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir")

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    comprobante = datos["comprobante"]
    assert comprobante["tipo"] == "Factura"
    # Queda en borrador a propósito: quien la revise decide si se transmite.
    assert comprobante["estado_sri"] == "Borrador"
    assert Decimal(comprobante["importe_total"]) == Decimal("920.00")
    assert comprobante["receptor_razon_social"] == "ARRENDATARIO S.A."


def test_emitir_adelanta_la_plantilla(cliente, receptor_id):
    plantilla = _crear(cliente, receptor_id, proxima_emision="2026-08-01").json()

    datos = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir").json()

    assert datos["plantilla"]["ultima_emision"] == "2026-08-01"
    assert datos["plantilla"]["proxima_emision"] == "2026-09-01"
    assert datos["plantilla"]["emitidas"] == 1


def test_no_se_repite_el_mismo_periodo(cliente, receptor_id):
    """
    La plantilla avanza aunque la factura siga en borrador; si no, el siguiente
    ciclo volvería a proponer el período ya emitido.
    """
    plantilla = _crear(cliente, receptor_id, proxima_emision="2026-08-01").json()

    primera = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir").json()
    segunda = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir").json()

    assert primera["comprobante"]["fecha_emision"] == "2026-08-01"
    assert segunda["comprobante"]["fecha_emision"] == "2026-09-01"


def test_la_factura_usa_el_contador_normal(cliente, receptor_id):
    """Ante el SRI no existe la "factura recurrente": es una factura y ya."""
    plantilla = _crear(cliente, receptor_id).json()

    numero_recurrente = cliente.post(
        f"/api/recurrentes/{plantilla['id']}/emitir"
    ).json()["comprobante"]["secuencial"]

    manual = cliente.post(
        "/api/comprobantes",
        json={
            "tipo": "Factura",
            "receptor_id": receptor_id,
            "detalles": [
                {"codigo_principal": "X", "descripcion": "Suelta", "cantidad": "1",
                 "precio_unitario": "10"}
            ],
        },
    ).json()

    assert manual["secuencial"] == numero_recurrente + 1


def test_una_plantilla_pausada_no_emite(cliente, receptor_id):
    plantilla = _crear(cliente, receptor_id).json()
    cliente.post(f"/api/recurrentes/{plantilla['id']}/pausar")

    respuesta = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir")

    assert respuesta.status_code == 422
    assert "desactivada" in respuesta.json()["detail"]


def test_al_pasar_su_fecha_de_fin_la_plantilla_se_apaga(cliente, receptor_id):
    plantilla = _crear(
        cliente, receptor_id, proxima_emision="2026-08-01", hasta="2026-08-15"
    ).json()

    datos = cliente.post(f"/api/recurrentes/{plantilla['id']}/emitir").json()

    # La siguiente sería el 01/09, más allá del 15/08: se apaga sola.
    assert datos["plantilla"]["activa"] is False


def test_vencidas_lista_lo_que_toca(cliente, receptor_id):
    _crear(cliente, receptor_id, nombre="Vencida", proxima_emision="2026-01-01")

    vencidas = cliente.get("/api/recurrentes/vencidas?hasta=2026-06-30").json()

    assert any(p["nombre"] == "Vencida" for p in vencidas)
    assert all(p["proxima_emision"] <= "2026-06-30" for p in vencidas)
    assert all(p["activa"] for p in vencidas)


def test_pausar_alterna(cliente, receptor_id):
    plantilla = _crear(cliente, receptor_id).json()

    assert cliente.post(f"/api/recurrentes/{plantilla['id']}/pausar").json()["activa"] is False
    assert cliente.post(f"/api/recurrentes/{plantilla['id']}/pausar").json()["activa"] is True


def test_editar_recalcula_el_total(cliente, receptor_id):
    plantilla = _crear(cliente, receptor_id).json()

    actualizada = cliente.put(
        f"/api/recurrentes/{plantilla['id']}",
        json={
            "nombre": "Arriendo actualizado",
            "receptor_id": receptor_id,
            "periodicidad": "Mensual",
            "proxima_emision": "2026-09-01",
            "lineas": [
                {
                    "codigo_principal": "ARR-001",
                    "descripcion": "Arriendo mensual",
                    "cantidad": "1",
                    "precio_unitario": "1000.00",
                    "codigo_iva": "4",
                }
            ],
        },
    )

    assert actualizada.status_code == 200
    assert Decimal(actualizada.json()["total"]) == Decimal("1150.00")
    assert len(actualizada.json()["lineas"]) == 1


def test_borrar_la_plantilla_no_borra_lo_emitido(cliente, receptor_id):
    """Las facturas ya emitidas son documentos tributarios y viven por su cuenta."""
    plantilla = _crear(cliente, receptor_id).json()
    comprobante = cliente.post(
        f"/api/recurrentes/{plantilla['id']}/emitir"
    ).json()["comprobante"]

    assert cliente.delete(f"/api/recurrentes/{plantilla['id']}").status_code == 204
    assert cliente.get(f"/api/recurrentes/{plantilla['id']}").status_code == 404

    assert cliente.get(f"/api/comprobantes/{comprobante['id']}").status_code == 200
