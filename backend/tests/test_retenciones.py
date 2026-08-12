"""
Pruebas de los comprobantes de retención.

Lo que se vigila aquí, además del XML, son las dos reglas que el SRI castiga:
solo un agente de retención puede emitirlas, y siempre contra un proveedor.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402


@dataclass
class RecepcionFalsa:
    estado: str = "RECIBIDA"
    mensajes: list = field(default_factory=list)

    @property
    def recibida(self) -> bool:
        return self.estado == "RECIBIDA"


@dataclass
class AutorizacionFalsa:
    estado: str = "AUTORIZADO"
    numero_autorizacion: str | None = "5566778899"
    fecha_autorizacion: str | None = "2026-08-08T12:00:00-05:00"
    comprobante: str | None = None
    mensajes: list = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


# --------------------------------------------------------------------------
# XML y cálculo, sin base de datos
# --------------------------------------------------------------------------


def _modelo_retencion():
    from app.sri.modelos import Comprador, Emisor
    from app.sri.xml_retencion import DetalleRetencion, Retencion

    return Retencion(
        emisor=Emisor(
            ruc="1790016919001",
            razon_social="MI EMPRESA DEMO S.A.",
            nombre_comercial="DEMO",
            direccion_matriz="Av. Amazonas N21-147",
            direccion_establecimiento="Av. Amazonas N21-147",
            establecimiento="001",
            punto_emision="001",
            obligado_contabilidad=True,
            agente_retencion="1",
        ),
        sujeto_retenido=Comprador(
            tipo_identificacion="04",
            identificacion="0992339411001",
            razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
            direccion="Km 14.5 via Daule",
        ),
        fecha_emision=date(2026, 8, 8),
        secuencial=3,
        periodo_fiscal="08/2026",
        detalles=[
            DetalleRetencion(
                codigo_impuesto="1",
                codigo_retencion="312",
                base_imponible=Decimal("1000.00"),
                porcentaje_retener=Decimal("2"),
                num_doc_sustento="001001000000123",
                fecha_emision_doc_sustento=date(2026, 8, 5),
            ),
            DetalleRetencion(
                codigo_impuesto="2",
                codigo_retencion="1",
                base_imponible=Decimal("150.00"),
                porcentaje_retener=Decimal("30"),
                num_doc_sustento="001001000000123",
                fecha_emision_doc_sustento=date(2026, 8, 5),
            ),
        ],
        ambiente="1",
    )


def test_el_valor_retenido_sale_de_la_base_y_el_porcentaje():
    retencion = _modelo_retencion()

    assert retencion.detalles[0].valor_retenido == Decimal("20.00")
    assert retencion.detalles[1].valor_retenido == Decimal("45.00")
    assert retencion.total_retenido == Decimal("65.00")


def test_el_xml_declara_retencion():
    from app.sri.xml_retencion import generar_xml_retencion

    xml, clave = generar_xml_retencion(_modelo_retencion(), "00000003")
    raiz = etree.fromstring(xml)

    assert raiz.tag == "comprobanteRetencion"
    assert raiz.findtext("infoTributaria/codDoc") == "07"
    assert raiz.findtext("infoTributaria/claveAcceso") == clave
    assert clave[8:10] == "07"

    info = raiz.find("infoCompRetencion")
    assert info.findtext("periodoFiscal") == "08/2026"
    assert info.findtext("identificacionSujetoRetenido") == "0992339411001"
    assert info.findtext("tipoIdentificacionSujetoRetenido") == "04"


def test_cada_impuesto_lleva_su_documento_sustento():
    """En la versión 1.0.0 el sustento se repite dentro de cada <impuesto>."""
    from app.sri.xml_retencion import generar_xml_retencion

    xml, _ = generar_xml_retencion(_modelo_retencion(), "00000003")
    raiz = etree.fromstring(xml)

    impuestos = raiz.findall("impuestos/impuesto")
    assert len(impuestos) == 2

    renta = impuestos[0]
    assert renta.findtext("codigo") == "1"
    assert renta.findtext("codigoRetencion") == "312"
    assert renta.findtext("valorRetenido") == "20.00"
    assert renta.findtext("numDocSustento") == "001001000000123"
    assert renta.findtext("fechaEmisionDocSustento") == "05/08/2026"

    assert impuestos[1].findtext("codigo") == "2"
    assert impuestos[1].findtext("valorRetenido") == "45.00"


def test_el_catalogo_refleja_la_resolucion_vigente():
    """
    Porcentajes contrastados con la NAC-DGERCGC26-00000009, vigente desde el
    1 de marzo de 2026. Si el SRI publica otra resolución, esta prueba es el
    primer sitio donde debe verse el cambio.
    """
    from app.sri.codigos_retencion import catalogo, porcentaje_sugerido

    assert porcentaje_sugerido("1", "303") == Decimal("10")  # honorarios
    assert porcentaje_sugerido("1", "312") == Decimal("2")   # bienes: era 1,75 %
    assert porcentaje_sugerido("1", "307") == Decimal("3")   # mano de obra: era 2 %
    assert porcentaje_sugerido("1", "320") == Decimal("10")  # inmuebles: era 8 %
    assert porcentaje_sugerido("1", "309") == Decimal("3")   # publicidad: era 1,75 %
    assert porcentaje_sugerido("1", "303A") == Decimal("5")  # servicios profesionales (sociedades)
    assert porcentaje_sugerido("1", "340") == Decimal("3")   # regla general
    
    assert porcentaje_sugerido("2", "727") == Decimal("30")  # 30% IVA

    # Un concepto que no está en la tabla no rompe: simplemente no sugiere.
    assert porcentaje_sugerido("1", "999") is None
    assert porcentaje_sugerido("1", "") is None

    filas = catalogo()
    assert all(
        {"id", "codigo_impuesto", "codigo_retencion", "porcentaje", "base_legal", "verificado"}
        <= set(f)
        for f in filas
    )


def test_la_tarifa_derogada_del_275_ya_no_existe():
    """La resolución de 2026 eliminó el 2,75 %; el código 332 se reutiliza para RIMPE NP al 0 %."""
    from app.sri.codigos_retencion import CONCEPTOS_RENTA

    assert not any(c.porcentaje == Decimal("2.75") for c in CONCEPTOS_RENTA)
    # 332 ahora es RIMPE Negocios Populares o compras no sujetas al 0%
    assert any(c.codigo == "332" and c.porcentaje == Decimal("0") for c in CONCEPTOS_RENTA)
    # Y entró la del 5 % para sociedades.
    assert any(c.porcentaje == Decimal("5") for c in CONCEPTOS_RENTA)


def test_todos_los_conceptos_tienen_codigo_y_estan_verificados():
    """
    Todos los conceptos de renta e IVA deben tener su código ATS asignado
    y estar marcados como verificados (con su base legal en el caso de renta).
    """
    from app.sri.codigos_retencion import CONCEPTOS_IVA, CONCEPTOS_RENTA

    for concepto in CONCEPTOS_RENTA:
        assert concepto.codigo != ""
        assert concepto.base_legal.startswith("Art.")
        assert concepto.verificado

    for concepto in CONCEPTOS_IVA:
        assert concepto.codigo != ""
        assert concepto.verificado


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_retenciones") / "retenciones.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-retenciones"

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
        agente_retencion="1",
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
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "PLASTICOS DEL LITORAL PLASTLIT S.A.",
            "direccion": "Km 14.5 via Daule",
            "rol": "Proveedor",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


@pytest.fixture(scope="module")
def cliente_id(cliente):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "Cédula",
            "identificacion": "1710034065",
            "razon_social": "JUAN PEREZ",
            "direccion": "Quito",
            "rol": "Cliente",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


@pytest.fixture(scope="module")
def certificado(cliente, tmp_path_factory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("cert_ret") / "cert.p12"
    generar(ruta, "pruebas123")

    with open(ruta, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("cert.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_retencion(cliente, proveedor_id, **cambios):
    cuerpo = {
        "establecimiento": "001",
        "punto_emision": "001",
        "fecha_emision": "2026-08-08",
        "sujeto_id": proveedor_id,
        "num_doc_sustento": "001001000000123",
        "fecha_doc_sustento": "2026-08-05",
        "detalles": [
            {
                "codigo_impuesto": "1",
                "codigo_retencion": "312",
                "base_imponible": "1000.00",
                "porcentaje_retener": "2",
            },
            {
                "codigo_impuesto": "2",
                "codigo_retencion": "1",
                "base_imponible": "150.00",
                "porcentaje_retener": "30",
            },
        ],
    }
    cuerpo.update(cambios)
    return cliente.post("/api/retenciones", json=cuerpo)


def test_crear_retencion_calcula_los_valores(cliente, proveedor_id):
    respuesta = _crear_retencion(cliente, proveedor_id)

    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()

    # La columna guarda 6 decimales (convención de `DINERO`); se compara el valor.
    assert Decimal(datos["total_retenido"]) == Decimal("65.00")
    assert [Decimal(d["valor_retenido"]) for d in datos["detalles"]] == [
        Decimal("20.00"),
        Decimal("45.00"),
    ]
    # Si no se envía, el período se deduce de la fecha de emisión.
    assert datos["periodo_fiscal"] == "08/2026"


def test_no_se_retiene_a_un_cliente(cliente, cliente_id):
    respuesta = _crear_retencion(cliente, cliente_id)

    assert respuesta.status_code == 422
    assert "se emite a un proveedor" in respuesta.json()["detail"]


def test_el_periodo_fiscal_exige_formato_sri(cliente, proveedor_id):
    respuesta = _crear_retencion(cliente, proveedor_id, periodo_fiscal="2026-08")

    assert respuesta.status_code == 422
    assert "MM/AAAA" in respuesta.text


def test_un_impuesto_desconocido_se_rechaza(cliente, proveedor_id):
    respuesta = _crear_retencion(
        cliente,
        proveedor_id,
        detalles=[
            {
                "codigo_impuesto": "9",
                "codigo_retencion": "312",
                "base_imponible": "100",
                "porcentaje_retener": "1",
            }
        ],
    )

    assert respuesta.status_code == 422
    assert "desconocido" in respuesta.text


def test_el_catalogo_se_expone(cliente):
    respuesta = cliente.get("/api/retenciones/codigos")

    assert respuesta.status_code == 200
    codigos = {fila["codigo_retencion"] for fila in respuesta.json()}
    assert "303" in codigos


def test_una_empresa_que_no_es_agente_no_retiene(cliente, proveedor_id):
    from app.base_datos import SesionLocal
    from app.modelos_db import Empresa
    from sqlalchemy import select

    sesion = SesionLocal()
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    empresa.agente_retencion = None
    sesion.commit()
    sesion.close()

    respuesta = _crear_retencion(cliente, proveedor_id)
    assert respuesta.status_code == 422
    assert "agente de retención" in respuesta.json()["detail"]

    sesion = SesionLocal()
    empresa = sesion.scalars(select(Empresa).limit(1)).first()
    empresa.agente_retencion = "1"
    sesion.commit()
    sesion.close()


def test_retencion_autorizada(cliente, proveedor_id, certificado, monkeypatch):
    import app.servicios.emision_retenciones as emision_ret

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = _crear_retencion(cliente, proveedor_id).json()
    respuesta = cliente.post(f"/api/retenciones/{retencion['id']}/emitir")

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["retencion"]["estado_sri"] == "Autorizado"
    assert datos["retencion"]["numero_autorizacion"] == "5566778899"
    assert len(datos["retencion"]["clave_acceso"]) == 49


def test_el_xml_firmado_de_la_retencion_queda_guardado(
    cliente, proveedor_id, certificado, monkeypatch
):
    import app.servicios.emision_retenciones as emision_ret
    from app.base_datos import SesionLocal
    from app.modelos_db import Retencion

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = _crear_retencion(cliente, proveedor_id).json()
    cliente.post(f"/api/retenciones/{retencion['id']}/emitir")

    sesion = SesionLocal()
    guardado = sesion.get(Retencion, retencion["id"]).xml_firmado
    sesion.close()

    assert "<comprobanteRetencion" in guardado
    assert "ds:Signature" in guardado


def test_no_se_reenvia_una_retencion_autorizada(
    cliente, proveedor_id, certificado, monkeypatch
):
    import app.servicios.emision_retenciones as emision_ret

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = _crear_retencion(cliente, proveedor_id).json()
    cliente.post(f"/api/retenciones/{retencion['id']}/emitir")

    segunda = cliente.post(f"/api/retenciones/{retencion['id']}/emitir")
    assert segunda.status_code == 422
    assert "ya está autorizada" in segunda.json()["detail"]


def test_el_secuencial_de_retenciones_es_independiente(cliente, proveedor_id):
    primera = _crear_retencion(cliente, proveedor_id).json()
    segunda = _crear_retencion(cliente, proveedor_id).json()

    assert int(segunda["numero"].split("-")[-1]) == int(primera["numero"].split("-")[-1]) + 1


# --------------------------------------------------------------------------
# RIDE, XML y reconsulta
# --------------------------------------------------------------------------


def test_el_ride_de_la_retencion_muestra_lo_retenido(cliente, proveedor_id):
    """
    El proveedor necesita ver contra qué documento se le retuvo y cuánto: sin
    eso no puede cruzar la retención con su propia contabilidad.
    """
    from pypdf import PdfReader
    import io as _io

    retencion = _crear_retencion(cliente, proveedor_id).json()
    respuesta = cliente.get(f"/api/retenciones/{retencion['id']}/ride")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.content.startswith(b"%PDF")

    texto = "".join(p.extract_text() for p in PdfReader(_io.BytesIO(respuesta.content)).pages)

    assert "COMPROBANTE DE RETENCIÓN" in texto
    assert "08/2026" in texto                       # período fiscal
    assert "001001000000123" in texto               # documento sustento
    assert "RENTA" in texto and "IVA" in texto      # los dos impuestos
    assert "65.00" in texto                         # total retenido
    assert "SIN VALIDEZ TRIBUTARIA" in texto        # ambiente de pruebas


def test_el_ride_autorizado_lleva_el_numero(cliente, proveedor_id, certificado, monkeypatch):
    from pypdf import PdfReader
    import io as _io

    import app.servicios.emision_retenciones as emision_ret

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = _crear_retencion(cliente, proveedor_id).json()
    cliente.post(f"/api/retenciones/{retencion['id']}/emitir")

    respuesta = cliente.get(f"/api/retenciones/{retencion['id']}/ride")
    texto = "".join(p.extract_text() for p in PdfReader(_io.BytesIO(respuesta.content)).pages)

    assert "5566778899" in texto
    assert "PENDIENTE DE AUTORIZACIÓN" not in texto


def test_el_xml_de_un_borrador_se_genera_al_vuelo(cliente, proveedor_id):
    retencion = _crear_retencion(cliente, proveedor_id).json()
    respuesta = cliente.get(f"/api/retenciones/{retencion['id']}/xml")

    assert respuesta.status_code == 200
    assert b"<comprobanteRetencion" in respuesta.content
    assert b"ds:Signature" not in respuesta.content


def test_el_xml_de_una_emitida_es_el_firmado(cliente, proveedor_id, certificado, monkeypatch):
    import app.servicios.emision_retenciones as emision_ret

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = _crear_retencion(cliente, proveedor_id).json()
    cliente.post(f"/api/retenciones/{retencion['id']}/emitir")

    respuesta = cliente.get(f"/api/retenciones/{retencion['id']}/xml")
    assert b"ds:Signature" in respuesta.content


def test_consultar_sin_transmitir_falla(cliente, proveedor_id):
    retencion = _crear_retencion(cliente, proveedor_id).json()
    respuesta = cliente.post(f"/api/retenciones/{retencion['id']}/consultar")

    assert respuesta.status_code == 422
    assert "aún no se ha transmitido" in respuesta.json()["detail"]


def test_consultar_autoriza_una_pendiente(cliente, proveedor_id, certificado, monkeypatch):
    import app.servicios.emision_retenciones as emision_ret
    import app.sri.servicios as servicios_sri

    monkeypatch.setattr(
        emision_ret,
        "transmitir_al_sri",
        lambda *_: (
            RecepcionFalsa(),
            AutorizacionFalsa(estado="EN PROCESO", numero_autorizacion=None),
        ),
    )
    retencion = _crear_retencion(cliente, proveedor_id).json()
    emitida = cliente.post(f"/api/retenciones/{retencion['id']}/emitir")
    assert emitida.json()["retencion"]["estado_sri"] == "Pendiente"

    monkeypatch.setattr(servicios_sri, "consultar_autorizacion", lambda *_: AutorizacionFalsa())
    respuesta = cliente.post(f"/api/retenciones/{retencion['id']}/consultar")

    assert respuesta.status_code == 200
    assert respuesta.json()["retencion"]["estado_sri"] == "Autorizado"
    assert respuesta.json()["retencion"]["numero_autorizacion"] == "5566778899"
