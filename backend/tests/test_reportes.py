"""
Pruebas de los reportes.

Lo que más importa aquí es la regla que gobierna todos: **solo cuentan los
comprobantes autorizados**. Un reporte que sume borradores da una cifra que no
cuadra con lo que el SRI tiene registrado, y eso se descubre al declarar.
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

ANIO = 2026


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_reportes") / "reportes.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-reportes"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion
    from app.modelos_db import (
        Comprobante,
        DetalleComprobante,
        DetalleRetencion,
        Empresa,
        Establecimiento,
        PuntoEmision,
        Retencion,
    )

    crear_tablas()
    sesion = SesionLocal()

    empresa = Empresa(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        direccion_matriz="Av. Amazonas N21-147",
        ambiente="1",
        agente_retencion="1",
    )
    establecimiento = Establecimiento(codigo="001", nombre="Matriz", direccion="Av. Amazonas")
    establecimiento.puntos_emision = [PuntoEmision(codigo="001", nombre="Caja")]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)

    def factura(numero, dia, mes, total_base, iva, estado, cliente, tipo="Factura"):
        comprobante = Comprobante(
            tipo=tipo,
            numero=numero,
            establecimiento="001",
            punto_emision="001",
            secuencial=int(numero[-3:]),
            fecha_emision=date(ANIO, mes, dia),
            receptor_razon_social=cliente[0],
            receptor_identificacion=cliente[1],
            total_sin_impuestos=Decimal(total_base),
            total_descuento=Decimal("0"),
            total_iva=Decimal(iva),
            importe_total=Decimal(total_base) + Decimal(iva),
            estado_sri=estado,
            estado_pago="Pagado" if estado == "Autorizado" else "Por Cobrar",
        )
        return comprobante

    ACME = ("ACME S.A.", "1790016919001")
    BETA = ("BETA CIA. LTDA.", "0992339411001")

    # --- Autorizadas: son las únicas que deben contar ---
    f1 = factura("001-001-000000001", 5, 8, "1000.00", "150.00", "Autorizado", ACME)
    f1.detalles = [
        DetalleComprobante(
            codigo_principal="PROD-001",
            descripcion="Laptop",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            codigo_iva="4",
            base_imponible=Decimal("1000.00"),
            valor_iva=Decimal("150.00"),
            total=Decimal("1150.00"),
        )
    ]

    f2 = factura("001-001-000000002", 10, 8, "500.00", "75.00", "Autorizado", BETA)
    f2.detalles = [
        DetalleComprobante(
            codigo_principal="PROD-001",
            descripcion="Laptop",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("500"),
            codigo_iva="4",
            base_imponible=Decimal("500.00"),
            valor_iva=Decimal("75.00"),
            total=Decimal("575.00"),
        ),
        DetalleComprobante(
            codigo_principal="PROD-002",
            descripcion="Arroz",
            cantidad=Decimal("10"),
            precio_unitario=Decimal("20"),
            codigo_iva="0",
            base_imponible=Decimal("200.00"),
            valor_iva=Decimal("0"),
            total=Decimal("200.00"),
        ),
    ]
    # El comprobante lleva también la línea de tarifa 0.
    f2.total_sin_impuestos = Decimal("700.00")
    f2.importe_total = Decimal("775.00")

    # De otro mes: no debe aparecer en el reporte de agosto.
    f3 = factura("001-001-000000003", 15, 7, "300.00", "45.00", "Autorizado", ACME)

    # --- No autorizadas: NO deben contar en ningún reporte tributario ---
    borrador = factura("001-001-000000004", 20, 8, "9999.00", "1499.85", "Borrador", ACME)
    anulado = factura("001-001-000000005", 21, 8, "8888.00", "1333.20", "Anulado", BETA)
    rechazado = factura("001-001-000000006", 22, 8, "7777.00", "1166.55", "Rechazado", ACME)

    # Una factura a crédito sin cobrar, para cuentas por cobrar.
    credito = factura("001-001-000000007", 25, 8, "400.00", "60.00", "Autorizado", BETA)
    credito.metodo = "Crédito"
    credito.estado_pago = "Por Cobrar"

    sesion.add_all([f1, f2, f3, borrador, anulado, rechazado, credito])

    # --- Retenciones ---
    retencion = Retencion(
        numero="001-001-000000001",
        establecimiento="001",
        punto_emision="001",
        secuencial=1,
        fecha_emision=date(ANIO, 8, 12),
        periodo_fiscal="08/2026",
        sujeto_razon_social="PROVEEDOR S.A.",
        sujeto_identificacion="0992339411001",
        num_doc_sustento="001-001-000000123",
        total_retenido=Decimal("62.50"),
        estado_sri="Autorizado",
    )
    retencion.detalles = [
        DetalleRetencion(
            codigo_impuesto="1",
            codigo_retencion="312",
            base_imponible=Decimal("1000.00"),
            porcentaje_retener=Decimal("1.75"),
            valor_retenido=Decimal("17.50"),
        ),
        DetalleRetencion(
            codigo_impuesto="2",
            codigo_retencion="1",
            base_imponible=Decimal("150.00"),
            porcentaje_retener=Decimal("30"),
            valor_retenido=Decimal("45.00"),
        ),
    ]

    # Retención sin autorizar: tampoco cuenta.
    borrador_ret = Retencion(
        numero="001-001-000000002",
        establecimiento="001",
        punto_emision="001",
        secuencial=2,
        fecha_emision=date(ANIO, 8, 13),
        periodo_fiscal="08/2026",
        sujeto_razon_social="OTRO PROVEEDOR",
        sujeto_identificacion="1790016919001",
        num_doc_sustento="001-001-000000999",
        total_retenido=Decimal("999.00"),
        estado_sri="Borrador",
    )
    borrador_ret.detalles = [
        DetalleRetencion(
            codigo_impuesto="1",
            codigo_retencion="303",
            base_imponible=Decimal("9990.00"),
            porcentaje_retener=Decimal("10"),
            valor_retenido=Decimal("999.00"),
        )
    ]

    sesion.add_all([retencion, borrador_ret])
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


# --------------------------------------------------------------------------
# Ventas
# --------------------------------------------------------------------------


def test_resumen_solo_cuenta_autorizados(entorno):
    """Borradores, anulados y rechazados quedan fuera: no son ventas."""
    datos = entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=8").json()

    # f1 (1150) + f2 (775) + credito (460) = 2385. Nada de los 9999/8888/7777.
    assert datos["comprobantes"] == 3
    assert Decimal(datos["total"]) == Decimal("2385.00")
    assert Decimal(datos["iva"]) == Decimal("285.00")


def test_el_resumen_respeta_el_mes_pedido(entorno):
    julio = entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=7").json()

    assert julio["comprobantes"] == 1
    assert Decimal(julio["total"]) == Decimal("345.00")


def test_sin_mes_el_resumen_es_anual(entorno):
    anual = entorno.get(f"/api/reportes/ventas?anio={ANIO}").json()

    assert anual["comprobantes"] == 4  # los tres de agosto más el de julio
    assert Decimal(anual["total"]) == Decimal("2730.00")


def test_ticket_promedio(entorno):
    datos = entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=8").json()

    assert Decimal(datos["ticket_promedio"]) == Decimal("795.00")


def test_un_periodo_sin_ventas_devuelve_ceros_y_no_falla(entorno):
    """Dividir entre cero comprobantes no debe reventar el ticket promedio."""
    datos = entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=1").json()

    assert datos["comprobantes"] == 0
    assert Decimal(datos["total"]) == Decimal("0")
    assert Decimal(datos["ticket_promedio"]) == Decimal("0")


def test_la_serie_mensual_trae_los_doce_meses(entorno):
    """Un mes ausente en la gráfica se lee como "no hay datos"."""
    serie = entorno.get(f"/api/reportes/ventas/por-mes?anio={ANIO}").json()

    assert len(serie) == 12
    assert [fila["mes"] for fila in serie] == list(range(1, 13))

    agosto = next(fila for fila in serie if fila["mes"] == 8)
    assert Decimal(agosto["total"]) == Decimal("2385.00")

    enero = next(fila for fila in serie if fila["mes"] == 1)
    assert Decimal(enero["total"]) == Decimal("0")


def test_top_clientes_ordena_por_importe(entorno):
    clientes = entorno.get(f"/api/reportes/clientes?anio={ANIO}&mes=8").json()

    # BETA suma f2 (775) + crédito (460) = 1235; ACME solo f1 (1150).
    assert [c["razon_social"] for c in clientes] == ["BETA CIA. LTDA.", "ACME S.A."]
    assert Decimal(clientes[0]["total"]) == Decimal("1235.00")
    assert Decimal(clientes[1]["total"]) == Decimal("1150.00")

    # Y agrupa: BETA aparece una vez pese a tener dos comprobantes.
    assert clientes[0]["comprobantes"] == 2


def test_top_articulos_agrupa_por_codigo(entorno):
    articulos = entorno.get(f"/api/reportes/articulos?anio={ANIO}&mes=8").json()

    laptop = next(a for a in articulos if a["codigo"] == "PROD-001")
    # 1000 de f1 + 500 de f2.
    assert Decimal(laptop["total"]) == Decimal("1500.00")
    assert Decimal(laptop["cantidad"]) == Decimal("2")


def test_el_limite_de_los_tops_se_respeta(entorno):
    clientes = entorno.get(f"/api/reportes/clientes?anio={ANIO}&limite=1").json()
    assert len(clientes) == 1


# --------------------------------------------------------------------------
# IVA — formulario 104
# --------------------------------------------------------------------------


def test_iva_separa_las_tarifas(entorno):
    """
    El 104 lleva las ventas con tarifa y las de tarifa cero en casilleros
    distintos: sumarlas juntas no sirve para declarar.
    """
    reporte = entorno.get(f"/api/reportes/iva?anio={ANIO}&mes=8").json()

    assert reporte["periodo_fiscal"] == "08/2026"

    por_codigo = {t["codigo_iva"]: t for t in reporte["tarifas"]}

    assert Decimal(por_codigo["4"]["base_imponible"]) == Decimal("1500.00")
    assert Decimal(por_codigo["4"]["valor_iva"]) == Decimal("225.00")
    assert Decimal(por_codigo["4"]["porcentaje"]) == Decimal("15")

    assert Decimal(por_codigo["0"]["base_imponible"]) == Decimal("200.00")
    assert Decimal(por_codigo["0"]["valor_iva"]) == Decimal("0")


def test_el_iva_ordena_de_mayor_a_menor_tarifa(entorno):
    reporte = entorno.get(f"/api/reportes/iva?anio={ANIO}&mes=8").json()
    porcentajes = [Decimal(t["porcentaje"]) for t in reporte["tarifas"]]

    assert porcentajes == sorted(porcentajes, reverse=True)


def test_el_iva_exige_el_mes(entorno):
    """El 104 es mensual; un acumulado anual no cabe en ningún casillero."""
    respuesta = entorno.get(f"/api/reportes/iva?anio={ANIO}")
    assert respuesta.status_code == 422


# --------------------------------------------------------------------------
# Retenciones — formulario 103
# --------------------------------------------------------------------------


def test_retenciones_agrupa_por_concepto(entorno):
    reporte = entorno.get(f"/api/reportes/retenciones?anio={ANIO}&mes=8").json()

    assert reporte["periodo_fiscal"] == "08/2026"
    assert reporte["comprobantes"] == 1

    assert Decimal(reporte["total_renta"]) == Decimal("17.50")
    assert Decimal(reporte["total_iva"]) == Decimal("45.00")
    assert Decimal(reporte["total_retenido"]) == Decimal("62.50")


def test_las_retenciones_sin_autorizar_no_cuentan(entorno):
    """La retención en borrador vale 999 y no debe aparecer por ningún lado."""
    reporte = entorno.get(f"/api/reportes/retenciones?anio={ANIO}&mes=8").json()

    conceptos = {c["codigo_retencion"] for c in reporte["conceptos"]}
    assert "303" not in conceptos
    assert Decimal(reporte["total_retenido"]) < Decimal("999")


def test_las_retenciones_se_filtran_por_periodo_fiscal(entorno):
    """
    No por fecha de emisión: el SRI declara por el período al que corresponde
    la retención, que puede no ser el día en que se emitió.
    """
    septiembre = entorno.get(f"/api/reportes/retenciones?anio={ANIO}&mes=9").json()

    assert septiembre["comprobantes"] == 0
    assert Decimal(septiembre["total_retenido"]) == Decimal("0")


# --------------------------------------------------------------------------
# Estado ante el SRI
# --------------------------------------------------------------------------


def test_estado_sri_si_incluye_los_no_autorizados(entorno):
    """Es el único reporte que debe enseñarlos: para eso existe."""
    reporte = entorno.get(f"/api/reportes/estado-sri?anio={ANIO}&mes=8").json()

    estados = {fila["estado"]: fila["cantidad"] for fila in reporte["por_estado"]}

    assert estados["Autorizado"] == 3
    assert estados["Borrador"] == 1
    assert estados["Anulado"] == 1
    assert estados["Rechazado"] == 1
    assert reporte["total"] == 6


def test_estado_sri_cuenta_los_que_requieren_atencion(entorno):
    """Borrador y rechazado sí; anulado no, que es una decisión tomada."""
    reporte = entorno.get(f"/api/reportes/estado-sri?anio={ANIO}&mes=8").json()

    assert reporte["requieren_atencion"] == 2


# --------------------------------------------------------------------------
# Panel del Dashboard
# --------------------------------------------------------------------------


def test_el_panel_trae_todo_lo_que_pinta_el_dashboard(entorno):
    panel = entorno.get("/api/reportes/panel").json()

    for clave in (
        "hoy",
        "mes",
        "anio",
        "por_tipo",
        "serie_mensual",
        "top_clientes",
        "top_articulos",
        "estado_sri",
        "por_cobrar",
    ):
        assert clave in panel, f"falta {clave} en el panel"

    assert len(panel["serie_mensual"]) == 12


def test_cuentas_por_cobrar_no_se_acota_por_periodo(entorno):
    """
    Una factura de hace meses sigue debiéndose hoy; filtrarla por fecha
    escondería justo la deuda más vieja.
    """
    panel = entorno.get("/api/reportes/panel").json()

    assert panel["por_cobrar"]["comprobantes"] == 1
    assert Decimal(panel["por_cobrar"]["total"]) == Decimal("460.00")
    assert Decimal(panel["por_cobrar"]["a_credito"]) == Decimal("460.00")


# --------------------------------------------------------------------------
# Exportación a CSV
# --------------------------------------------------------------------------


def test_el_csv_de_iva_se_descarga(entorno):
    respuesta = entorno.get(f"/api/reportes/iva/csv?anio={ANIO}&mes=8")

    assert respuesta.status_code == 200
    assert "text/csv" in respuesta.headers["content-type"]
    assert "iva-ventas-08-2026.csv" in respuesta.headers["content-disposition"]


def test_el_csv_lleva_BOM_y_punto_y_coma(entorno):
    """
    Sin BOM, Excel en español rompe las tildes; con coma, mete todo en una
    sola columna. El destino real de estos archivos es Excel.
    """
    texto = entorno.get(f"/api/reportes/iva/csv?anio={ANIO}&mes=8").content.decode("utf-8")

    assert texto.startswith("﻿")
    assert ";" in texto.splitlines()[0]
    assert "Base imponible" in texto


def test_el_csv_de_iva_cuadra_con_el_reporte(entorno):
    reporte = entorno.get(f"/api/reportes/iva?anio={ANIO}&mes=8").json()
    texto = entorno.get(f"/api/reportes/iva/csv?anio={ANIO}&mes=8").content.decode("utf-8")

    assert str(reporte["iva_total"]) in texto
    assert "TOTAL" in texto


def test_el_csv_de_retenciones_se_descarga(entorno):
    respuesta = entorno.get(f"/api/reportes/retenciones/csv?anio={ANIO}&mes=8")

    assert respuesta.status_code == 200
    assert "retenciones-08-2026.csv" in respuesta.headers["content-disposition"]
    assert "62.50" in respuesta.content.decode("utf-8")


def test_el_csv_de_ventas_se_descarga(entorno):
    respuesta = entorno.get(f"/api/reportes/ventas/csv?anio={ANIO}&mes=8")

    assert respuesta.status_code == 200
    texto = respuesta.content.decode("utf-8")
    assert "Tipo de comprobante" in texto
    assert "TOTAL" in texto


# --------------------------------------------------------------------------
# Validación de parámetros
# --------------------------------------------------------------------------


def test_un_mes_fuera_de_rango_se_rechaza(entorno):
    assert entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=13").status_code == 422
    assert entorno.get(f"/api/reportes/ventas?anio={ANIO}&mes=0").status_code == 422


def test_un_anio_absurdo_se_rechaza(entorno):
    respuesta = entorno.get("/api/reportes/ventas?anio=1990")

    assert respuesta.status_code == 422
    assert "fuera de rango" in respuesta.json()["detail"]
