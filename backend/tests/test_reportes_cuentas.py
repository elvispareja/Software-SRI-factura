"""
Los cinco reportes de la pestaña «Reportes» de cuentas pendientes.

Dos cosas se prueban aquí porque ya fallaron una vez en este proyecto:

1. **El doble conteo.** `crear_recibo` rellena `Recibo.comprobante_id` también
   cuando el recibo va contra una cuota. Sumar `Cuota.cobrado` y además todos
   los recibos del comprobante duplica el dinero, y una factura de 300 con un
   abono de 100 aparecería abonada al 66 %.
2. **El interruptor Cobrar/Pagar.** Hasta ahora solo cambiaba rótulos: en modo
   Pagar seguía enseñando las cuotas y los recibos de las VENTAS bajo la
   etiqueta «Proveedor». Aquí se exige que los dos modos devuelvan documentos
   distintos de verdad.
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

BASE = "/api/cuentas/reportes"

# Fechas fijas: un reporte que dependa del día en que se ejecutan las pruebas
# es un reporte que un día se pondrá rojo solo.
JUNIO = date(2026, 6, 10)
AGOSTO = date(2026, 8, 1)


def _dec(valor) -> Decimal:
    return Decimal(str(valor))


@pytest.fixture(scope="module")
def datos(tmp_path_factory):
    """
    Una base con las dos caras del negocio.

    Cobrar: tres facturas autorizadas (una con plan de cuotas, una al contado,
    una con el cobro anulado), un borrador que no debe salir en ningún reporte y
    una nota de crédito, que no es deuda de nadie.

    Pagar: un gasto pagado a medias con un egreso y una liquidación de compra.
    """
    base = tmp_path_factory.mktemp("bd") / "reportes_cuentas.db"
    import os

    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion
    from app.modelos_db import Comprobante, Empresa, Establecimiento, PuntoEmision, Receptor

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

    cliente_a = Receptor(
        tipo_identificacion="RUC",
        identificacion="0992339411001",
        razon_social="CLIENTE UNO S.A.",
        rol="Cliente",
        correo="uno@cliente.ec",
        telefono1="0999111111",
    )
    cliente_b = Receptor(
        tipo_identificacion="RUC",
        identificacion="0993456789001",
        razon_social="CLIENTE DOS S.A.",
        rol="Cliente",
    )
    proveedor = Receptor(
        tipo_identificacion="RUC",
        identificacion="1791234567001",
        razon_social="PROVEEDOR ÚNICO CÍA. LTDA.",
        rol="Proveedor",
        correo="pagos@proveedor.ec",
        telefono1="0988222222",
    )
    sesion.add_all([cliente_a, cliente_b, proveedor])
    sesion.commit()

    def _comprobante(tipo, numero, total, fecha, receptor, estado="Autorizado"):
        comprobante = Comprobante(
            tipo=tipo,
            numero=numero,
            establecimiento="001",
            punto_emision="001",
            secuencial=int(numero.split("-")[-1]),
            fecha_emision=fecha,
            receptor_id=receptor.id,
            receptor_identificacion=receptor.identificacion,
            receptor_razon_social=receptor.razon_social,
            total_sin_impuestos=_dec(total),
            importe_total=_dec(total),
            estado_sri=estado,
        )
        sesion.add(comprobante)
        sesion.commit()
        return comprobante.id

    identificadores = {
        # A crédito: 300 en tres cuotas, con la primera cobrada entera.
        "f_cuotas": _comprobante("Factura", "001-001-000000001", "300.00", AGOSTO, cliente_a),
        # Al contado: se abona 40 sin plan de cuotas.
        "f_contado": _comprobante(
            "Factura", "001-001-000000002", "100.00", date(2026, 8, 2), cliente_b
        ),
        # Borrador: no es una venta todavía. No puede salir en ningún reporte.
        "f_borrador": _comprobante(
            "Factura", "001-001-000000003", "999.00", date(2026, 8, 3), cliente_a, "Borrador"
        ),
        # El cobro se anula: la factura vuelve a deberse entera.
        "f_anulada": _comprobante(
            "Factura", "001-001-000000004", "50.00", date(2026, 8, 4), cliente_b
        ),
        # Junio: emitida y nunca cobrada. Es el denominador cero de la rotación.
        "f_junio": _comprobante("Factura", "001-001-000000005", "120.00", JUNIO, cliente_a),
        # Una nota de crédito no es una deuda: es la anulación de otra.
        "nota_credito": _comprobante(
            "Nota de Crédito", "001-001-000000006", "30.00", date(2026, 8, 5), cliente_a
        ),
        # Compra: comprobante electrónico, pero de los que se PAGAN.
        "liquidacion": _comprobante(
            "Liquidación de Compra", "001-001-000000007", "250.00",
            date(2026, 8, 5), proveedor,
        ),
    }
    identificadores["cliente_a"] = cliente_a.id
    identificadores["cliente_b"] = cliente_b.id
    identificadores["proveedor"] = proveedor.id
    sesion.close()

    cliente = iniciar_sesion(TestClient(aplicacion))

    # --- Cobros (modo cobrar) ---
    cuotas = cliente.post(
        f"/api/cuentas/comprobantes/{identificadores['f_cuotas']}/cuotas",
        json={"cuotas": 3, "dias_entre_cuotas": 30, "primera_fecha": "2026-08-01"},
    ).json()
    assert len(cuotas) == 3
    identificadores["cuotas"] = [c["id"] for c in cuotas]

    # Este es el recibo que destapa el doble conteo: sube `Cuota.cobrado` Y
    # queda con `comprobante_id` relleno.
    cliente.post(
        "/api/cuentas/recibos",
        json={
            "cuota_id": cuotas[0]["id"],
            "monto": 100.00,
            "fecha": "2026-08-05",
            "forma_pago": "Transferencia",
        },
    )
    cliente.post(
        "/api/cuentas/recibos",
        json={
            "comprobante_id": identificadores["f_contado"],
            "monto": 40.00,
            "fecha": "2026-08-06",
            "forma_pago": "Efectivo",
        },
    )
    anulable = cliente.post(
        "/api/cuentas/recibos",
        json={
            "comprobante_id": identificadores["f_anulada"],
            "monto": 50.00,
            "fecha": "2026-08-07",
            "forma_pago": "Efectivo",
        },
    ).json()
    cliente.post(f"/api/cuentas/recibos/{anulable['id']}/anular")
    identificadores["recibo_anulado"] = anulable["numero"]

    # --- Pagos (modo pagar) ---
    gasto = cliente.post(
        "/api/egresos/gastos",
        json={
            "fecha": "2026-08-04",
            "concepto": "Arriendo de bodega",
            "proveedor_id": identificadores["proveedor"],
            "documento": "002-003-000000123",
            "subtotal": 500.00,
            "iva": 0,
        },
    )
    assert gasto.status_code == 201, gasto.text
    identificadores["gasto"] = gasto.json()["id"]

    pago = cliente.post(
        "/api/egresos",
        json={
            "fecha": "2026-08-08",
            "concepto": "Abono de arriendo",
            "monto": 200.00,
            "forma_pago": "Transferencia",
            "gasto_id": identificadores["gasto"],
        },
    )
    assert pago.status_code == 201, pago.text

    return cliente, identificadores


@pytest.fixture(scope="module")
def cliente(datos):
    return datos[0]


@pytest.fixture(scope="module")
def ids(datos):
    return datos[1]


def _saldos(cliente, modo="cobrar", **extra):
    respuesta = cliente.get(f"{BASE}/saldos", params={"modo": modo, **extra})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _documento(reporte, numero):
    return next(d for d in reporte["documentos"] if d["numero"] == numero)


# ---------------------------------------------------------------------------
# 1. Saldo pendiente por documento
# ---------------------------------------------------------------------------


def test_el_abono_con_cuota_no_se_cuenta_dos_veces(cliente):
    """
    300 en tres cuotas, una cobrada: abonado 100 y saldo 200.

    Si se sumara `Cuota.cobrado` MÁS los recibos del comprobante, el abono
    saldría 200 y el saldo 100. El recibo lleva `comprobante_id` relleno a
    propósito, así que el reporte tiene que descartar los que ya van imputados
    a una cuota.
    """
    reporte = _saldos(cliente)
    factura = _documento(reporte, "001-001-000000001")

    assert _dec(factura["total"]) == _dec("300.00")
    assert _dec(factura["abonado"]) == _dec("100.00")
    assert _dec(factura["saldo"]) == _dec("200.00")
    assert factura["estado"] == "Parcial"


def test_el_abono_suelto_sin_cuota_si_cuenta(cliente):
    """La otra mitad de la regla: el recibo sin cuota es el único que se suma."""
    factura = _documento(_saldos(cliente), "001-001-000000002")

    assert _dec(factura["abonado"]) == _dec("40.00")
    assert _dec(factura["saldo"]) == _dec("60.00")


def test_un_recibo_anulado_deja_el_documento_debiendo_entero(cliente):
    factura = _documento(_saldos(cliente), "001-001-000000004")

    assert _dec(factura["abonado"]) == _dec("0.00")
    assert _dec(factura["saldo"]) == _dec("50.00")
    assert factura["estado"] == "Pendiente"


def test_un_borrador_no_aparece_en_ningun_reporte(cliente):
    """Un borrador no es una venta. La regla vale para los cinco reportes."""
    numero = "001-001-000000003"

    assert numero not in [d["numero"] for d in _saldos(cliente)["documentos"]]

    agenda = cliente.get(f"{BASE}/agenda", params={"modo": "cobrar"}).json()
    assert numero not in [c["documento"] for c in agenda["cuotas"]]

    rotacion = cliente.get(
        f"{BASE}/rotacion", params={"modo": "cobrar", "anio": 2026, "mes": 8}
    ).json()
    # 999 es un importe imposible de confundir: si el borrador contara, el
    # total del período lo delataría.
    assert _dec(rotacion["totales"]["total"]) == _dec("450.00")


def test_la_nota_de_credito_no_es_una_deuda(cliente):
    numeros = [d["numero"] for d in _saldos(cliente, incluir_saldados=True)["documentos"]]
    assert "001-001-000000006" not in numeros


def test_el_saldo_se_calcula_y_no_se_guarda(cliente):
    for documento in _saldos(cliente, incluir_saldados=True)["documentos"]:
        assert _dec(documento["saldo"]) == _dec(documento["total"]) - _dec(
            documento["abonado"]
        )


# ---------------------------------------------------------------------------
# El interruptor Cobrar / Pagar
# ---------------------------------------------------------------------------


def test_modo_pagar_devuelve_documentos_distintos_de_modo_cobrar(cliente):
    """
    El interruptor tiene que leer otras tablas, no cambiar el rótulo.

    En pagar salen el gasto y la liquidación de compra; en cobrar, las facturas.
    Ni un solo documento en común.
    """
    cobrar = {d["numero"] for d in _saldos(cliente, "cobrar")["documentos"]}
    pagar = {d["numero"] for d in _saldos(cliente, "pagar")["documentos"]}

    assert cobrar and pagar
    assert not (cobrar & pagar), "un documento no puede cobrarse y pagarse a la vez"
    assert "002-003-000000123" in pagar, "el gasto del proveedor"
    assert "001-001-000000007" in pagar, "la liquidación de compra"
    assert "001-001-000000001" in cobrar


def test_el_rotulo_del_contacto_cambia_con_el_modo(cliente):
    assert _saldos(cliente, "cobrar")["etiqueta_contacto"] == "Cliente"
    assert _saldos(cliente, "pagar")["etiqueta_contacto"] == "Proveedor"


def test_el_gasto_pagado_a_medias_deja_su_saldo(cliente):
    gasto = _documento(_saldos(cliente, "pagar"), "002-003-000000123")

    assert _dec(gasto["total"]) == _dec("500.00")
    assert _dec(gasto["abonado"]) == _dec("200.00")
    assert _dec(gasto["saldo"]) == _dec("300.00")
    assert gasto["tipo"] == "Gasto"


def test_un_modo_inventado_se_rechaza(cliente):
    respuesta = cliente.get(f"{BASE}/saldos", params={"modo": "regalar"})
    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 2. Agenda de cuotas
# ---------------------------------------------------------------------------


def test_la_agenda_de_cobrar_lista_las_cuotas_del_plan(cliente):
    agenda = cliente.get(f"{BASE}/agenda", params={"modo": "cobrar"}).json()
    cuotas = [c for c in agenda["cuotas"] if c["documento"] == "001-001-000000001"]

    # La primera está cobrada: con `solo_pendientes` quedan las otras dos.
    assert len(cuotas) == 2
    assert _dec(agenda["saldo"]) >= _dec("200.00")
    assert all(_dec(c["saldo"]) > 0 for c in agenda["cuotas"])


def test_la_agenda_lleva_el_contacto_del_documento(cliente):
    agenda = cliente.get(f"{BASE}/agenda", params={"modo": "cobrar"}).json()
    cuota = next(c for c in agenda["cuotas"] if c["documento"] == "001-001-000000001")

    assert cuota["contacto"] == "CLIENTE UNO S.A."
    assert cuota["correo"] == "uno@cliente.ec"
    assert cuota["telefono"] == "0999111111"


def test_la_agenda_de_pagar_no_trae_ni_una_cuota_de_venta(cliente):
    """El fallo que se corrige: en Pagar salían las cuotas de las facturas."""
    agenda = cliente.get(f"{BASE}/agenda", params={"modo": "pagar"}).json()
    documentos = {c["documento"] for c in agenda["cuotas"]}

    assert "001-001-000000001" not in documentos
    assert documentos == {"002-003-000000123", "001-001-000000007"}
    assert agenda["etiqueta_contacto"] == "Proveedor"


def test_un_gasto_sin_plan_de_cuotas_entra_como_cuota_unica(cliente):
    """Si no entrara, la agenda de pagos saldría vacía y volvería a mentir."""
    agenda = cliente.get(f"{BASE}/agenda", params={"modo": "pagar"}).json()
    gasto = next(c for c in agenda["cuotas"] if c["documento"] == "002-003-000000123")

    assert gasto["cuota_id"] is None
    assert gasto["numero"] == 1
    assert gasto["vence"] == "2026-08-04"
    assert _dec(gasto["saldo"]) == _dec("300.00")


def test_solo_vencidas_no_devuelve_nada_en_plazo(cliente):
    agenda = cliente.get(
        f"{BASE}/agenda", params={"modo": "cobrar", "solo_vencidas": True}
    ).json()
    hoy = date.fromisoformat(agenda["hoy"])

    assert agenda["cuotas"], "hay cuotas de agosto de 2026 ya vencidas"
    for cuota in agenda["cuotas"]:
        assert date.fromisoformat(cuota["vence"]) < hoy
        assert _dec(cuota["saldo"]) > 0


def test_la_agenda_filtra_por_fecha(cliente):
    agenda = cliente.get(
        f"{BASE}/agenda",
        params={"modo": "cobrar", "desde": "2026-09-01", "hasta": "2026-09-30"},
    ).json()

    assert agenda["cuotas"]
    for cuota in agenda["cuotas"]:
        assert cuota["vence"].startswith("2026-09")


# ---------------------------------------------------------------------------
# 3. Recibos generados
# ---------------------------------------------------------------------------


def test_los_recibos_de_cobrar_son_recibos_y_los_de_pagar_egresos(cliente):
    cobrar = cliente.get(f"{BASE}/recibos", params={"modo": "cobrar"}).json()
    pagar = cliente.get(f"{BASE}/recibos", params={"modo": "pagar"}).json()

    assert {r["origen"] for r in cobrar["recibos"]} == {"Recibo"}
    assert "Egreso" in {r["origen"] for r in pagar["recibos"]}
    assert not ({r["numero"] for r in cobrar["recibos"]} & {r["numero"] for r in pagar["recibos"]})


def test_lo_aplicado_descarta_los_recibos_anulados(cliente, ids):
    reporte = cliente.get(f"{BASE}/recibos", params={"modo": "cobrar"}).json()
    anulado = next(r for r in reporte["recibos"] if r["numero"] == ids["recibo_anulado"])

    # El anulado se sigue enseñando —el reporte promete el estado del recibo—
    # pero no suma: 100 + 40, y los 50 anulados fuera.
    assert anulado["estado"] == "Anulado"
    assert reporte["anulados"] == 1
    assert _dec(reporte["aplicado"]) == _dec("140.00")
    assert _dec(reporte["monto_anulado"]) == _dec("50.00")


def test_el_recibo_arrastra_su_documento_y_su_forma_de_pago(cliente):
    reporte = cliente.get(f"{BASE}/recibos", params={"modo": "cobrar"}).json()
    recibo = next(r for r in reporte["recibos"] if r["documento"] == "001-001-000000001")

    assert recibo["forma_pago"] == "Transferencia"
    assert recibo["cuota_id"] is not None, "trazabilidad hasta la cuota"


def test_los_recibos_se_filtran_por_fecha(cliente):
    reporte = cliente.get(
        f"{BASE}/recibos",
        params={"modo": "cobrar", "desde": "2026-08-06", "hasta": "2026-08-06"},
    ).json()

    assert reporte["total_recibos"] == 1
    assert _dec(reporte["aplicado"]) == _dec("40.00")


# ---------------------------------------------------------------------------
# 4. Rotación de cuentas
# ---------------------------------------------------------------------------


def test_la_rotacion_reparte_por_tipo_y_por_receptor(cliente):
    reporte = cliente.get(
        f"{BASE}/rotacion", params={"modo": "cobrar", "anio": 2026, "mes": 8}
    ).json()

    assert [f["grupo"] for f in reporte["por_tipo"]] == ["Factura"]
    assert reporte["totales"]["documentos"] == 3
    assert _dec(reporte["totales"]["total"]) == _dec("450.00")
    assert _dec(reporte["totales"]["cobrado"]) == _dec("140.00")
    assert _dec(reporte["totales"]["pendiente"]) == _dec("310.00")
    assert _dec(reporte["totales"]["promedio"]) == _dec("150.00")

    contactos = {f["grupo"]: f for f in reporte["por_contacto"]}
    assert set(contactos) == {"CLIENTE UNO S.A.", "CLIENTE DOS S.A."}


def test_los_dias_de_recuperacion_se_ponderan_por_dinero(cliente):
    """100 cobrados a los 4 días y 40 cobrados a los 4 días: 4 días."""
    reporte = cliente.get(
        f"{BASE}/rotacion", params={"modo": "cobrar", "anio": 2026, "mes": 8}
    ).json()

    assert _dec(reporte["totales"]["dias_recuperacion"]) == _dec("4.0")


def test_sin_cobros_en_el_periodo_los_dias_son_nulos_y_no_cero(cliente):
    """
    Junio: se emitió y no entró un dólar.

    Devolver 0 diría «se cobra al contado», que es justo lo contrario de lo que
    pasó. Nulo, y que la interfaz pinte un guion.
    """
    reporte = cliente.get(
        f"{BASE}/rotacion", params={"modo": "cobrar", "anio": 2026, "mes": 6}
    ).json()

    assert reporte["totales"]["documentos"] == 1
    assert _dec(reporte["totales"]["cobrado"]) == _dec("0.00")
    assert _dec(reporte["totales"]["pendiente"]) == _dec("120.00")
    assert reporte["totales"]["dias_recuperacion"] is None


def test_la_rotacion_de_pagar_mira_gastos_y_liquidaciones(cliente):
    reporte = cliente.get(
        f"{BASE}/rotacion", params={"modo": "pagar", "anio": 2026, "mes": 8}
    ).json()

    assert set(f["grupo"] for f in reporte["por_tipo"]) == {"Gasto", "Liquidación de Compra"}
    assert _dec(reporte["totales"]["total"]) == _dec("750.00")
    assert _dec(reporte["totales"]["cobrado"]) == _dec("200.00")
    assert _dec(reporte["totales"]["pendiente"]) == _dec("550.00")


def test_un_anio_imposible_se_rechaza(cliente):
    respuesta = cliente.get(f"{BASE}/rotacion", params={"modo": "cobrar", "anio": 1999})
    assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# 5. Historial por cliente / proveedor
# ---------------------------------------------------------------------------


def test_el_historial_resume_saldo_abonos_y_cuotas(cliente):
    reporte = cliente.get(f"{BASE}/historial", params={"modo": "cobrar"}).json()
    uno = next(c for c in reporte["contactos"] if c["contacto"] == "CLIENTE UNO S.A.")

    # 300 de la factura a crédito + 120 de la de junio.
    assert _dec(uno["total"]) == _dec("420.00")
    assert _dec(uno["abonado"]) == _dec("100.00")
    assert _dec(uno["saldo"]) == _dec("320.00")
    # Dos cuotas vivas del plan + la de junio, que va como cuota única.
    assert uno["cuotas_pendientes"] == 3
    assert uno["proxima_fecha"] == "2026-06-10"
    assert uno["ultimo_movimiento"] == "2026-08-05"


def test_el_historial_de_pagar_habla_de_proveedores(cliente):
    reporte = cliente.get(f"{BASE}/historial", params={"modo": "pagar"}).json()

    assert reporte["etiqueta_contacto"] == "Proveedor"
    assert [c["contacto"] for c in reporte["contactos"]] == ["PROVEEDOR ÚNICO CÍA. LTDA."]

    proveedor = reporte["contactos"][0]
    assert _dec(proveedor["total"]) == _dec("750.00")
    assert _dec(proveedor["abonado"]) == _dec("200.00")
    assert _dec(proveedor["saldo"]) == _dec("550.00")


def test_el_historial_puede_dejar_fuera_a_quien_no_debe_nada(cliente):
    reporte = cliente.get(
        f"{BASE}/historial", params={"modo": "cobrar", "solo_con_saldo": True}
    ).json()

    assert all(_dec(c["saldo"]) > 0 for c in reporte["contactos"])


# ---------------------------------------------------------------------------
# Los diez CSV
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ruta,parametros",
    [
        ("saldos", {}),
        ("agenda", {}),
        ("recibos", {}),
        ("rotacion", {"anio": 2026, "mes": 8}),
        ("historial", {}),
    ],
)
@pytest.mark.parametrize("modo", ["cobrar", "pagar"])
def test_los_cinco_csv_responden_en_los_dos_modos(cliente, ruta, parametros, modo):
    respuesta = cliente.get(f"{BASE}/{ruta}/csv", params={"modo": modo, **parametros})

    assert respuesta.status_code == 200, respuesta.text
    assert "text/csv" in respuesta.headers["content-type"]
    assert "attachment" in respuesta.headers["content-disposition"]

    contenido = respuesta.content.decode("utf-8")
    # BOM y `;`: el destino real de estos archivos es Excel en español.
    assert contenido.startswith("﻿")
    assert ";" in contenido.splitlines()[0]


def test_el_csv_de_saldos_lleva_los_importes_del_json(cliente):
    contenido = cliente.get(
        f"{BASE}/saldos/csv", params={"modo": "cobrar"}
    ).content.decode("utf-8")

    assert "001-001-000000001" in contenido
    assert "200.00" in contenido
    assert "001-001-000000003" not in contenido, "el borrador tampoco sale en el CSV"


def test_el_csv_de_rotacion_pinta_un_guion_cuando_no_hay_dias(cliente):
    contenido = cliente.get(
        f"{BASE}/rotacion/csv", params={"modo": "cobrar", "anio": 2026, "mes": 6}
    ).content.decode("utf-8")

    assert "—" in contenido
