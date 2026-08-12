"""Pruebas de nota de crédito y comprobante de retención."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sri.clave_acceso import descomponer_clave_acceso, validar_clave_acceso  # noqa: E402
from app.sri.firma import cargar_p12, firmar_xml, verificar_firma  # noqa: E402
from app.sri.modelos import Comprador, Detalle, Emisor  # noqa: E402
from app.sri.xml_nota_credito import NotaCredito, generar_xml_nota_credito  # noqa: E402
from app.sri.xml_retencion import (  # noqa: E402
    DetalleRetencion,
    Retencion,
    generar_xml_retencion,
)


@pytest.fixture
def emisor() -> Emisor:
    return Emisor(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        nombre_comercial="DEMO",
        direccion_matriz="Av. Amazonas N21-147",
        direccion_establecimiento="Av. Amazonas N21-147",
        establecimiento="001",
        punto_emision="001",
    )


@pytest.fixture
def contraparte() -> Comprador:
    return Comprador(
        tipo_identificacion="04",
        identificacion="0992339411001",
        razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
        direccion="Km 14.5 via Daule",
    )


@pytest.fixture(scope="module")
def firmante(tmp_path_factory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("certificados") / "pruebas.p12"
    generar(ruta, "pruebas123")
    return cargar_p12(str(ruta), "pruebas123")


# --------------------------------------------------------------------------
# Nota de crédito
# --------------------------------------------------------------------------


@pytest.fixture
def nota(emisor, contraparte) -> NotaCredito:
    return NotaCredito(
        emisor=emisor,
        comprador=contraparte,
        fecha_emision=date(2026, 8, 8),
        secuencial=45,
        detalles=[
            Detalle("PROD-001", "Laptop devuelta", Decimal("1"), Decimal("1200.00"), "4")
        ],
        motivo="Devolución de mercadería por defecto de fábrica",
        cod_doc_modificado="01",
        num_doc_modificado="001-001-000000123",
        fecha_emision_doc_sustento=date(2026, 8, 1),
    )


def test_nota_credito_usa_coddoc_04(nota):
    xml, clave = generar_xml_nota_credito(nota, "12345678")
    raiz = etree.fromstring(xml)

    assert raiz.tag == "notaCredito"
    assert raiz.findtext("infoTributaria/codDoc") == "04"
    assert descomponer_clave_acceso(clave)["tipo_comprobante"] == "04"


def test_nota_credito_referencia_el_documento_modificado(nota):
    """Sin estos tres campos el SRI rechaza la nota."""
    xml, _ = generar_xml_nota_credito(nota, "12345678")
    info = etree.fromstring(xml).find("infoNotaCredito")

    assert info.findtext("codDocModificado") == "01"
    assert info.findtext("numDocModificado") == "001-001-000000123"
    assert info.findtext("fechaEmisionDocSustento") == "01/08/2026"


def test_valor_modificacion_incluye_iva(nota):
    xml, _ = generar_xml_nota_credito(nota, "12345678")
    info = etree.fromstring(xml).find("infoNotaCredito")

    assert info.findtext("totalSinImpuestos") == "1200.00"
    # 1200 + 15% = 1380
    assert info.findtext("valorModificacion") == "1380.00"


def test_nota_credito_exige_motivo(nota):
    xml, _ = generar_xml_nota_credito(nota, "12345678")
    motivo = etree.fromstring(xml).findtext("infoNotaCredito/motivo")
    assert motivo == "Devolución de mercadería por defecto de fábrica"


def test_nota_credito_se_firma_y_verifica(nota, firmante):
    xml, _ = generar_xml_nota_credito(nota, "12345678")
    resultado = verificar_firma(firmar_xml(xml, firmante))
    assert all(resultado.values())


# --------------------------------------------------------------------------
# Retención
# --------------------------------------------------------------------------


@pytest.fixture
def retencion(emisor, contraparte) -> Retencion:
    return Retencion(
        emisor=emisor,
        sujeto_retenido=contraparte,
        fecha_emision=date(2026, 8, 8),
        secuencial=12,
        periodo_fiscal="08/2026",
        detalles=[
            DetalleRetencion(
                codigo_impuesto="1",
                codigo_retencion="303",
                base_imponible=Decimal("1000.00"),
                porcentaje_retener=Decimal("10"),
                num_doc_sustento="001-001-000000123",
                fecha_emision_doc_sustento=date(2026, 8, 1),
            ),
            DetalleRetencion(
                codigo_impuesto="2",
                codigo_retencion="9",
                base_imponible=Decimal("150.00"),
                porcentaje_retener=Decimal("30"),
                num_doc_sustento="001-001-000000123",
                fecha_emision_doc_sustento=date(2026, 8, 1),
            ),
        ],
    )


def test_retencion_usa_coddoc_07(retencion):
    xml, clave = generar_xml_retencion(retencion, "12345678")
    raiz = etree.fromstring(xml)

    assert raiz.tag == "comprobanteRetencion"
    assert raiz.findtext("infoTributaria/codDoc") == "07"
    assert validar_clave_acceso(clave)


def test_retencion_calcula_valor_retenido_por_linea(retencion):
    xml, _ = generar_xml_retencion(retencion, "12345678")
    impuestos = etree.fromstring(xml).findall("impuestos/impuesto")

    assert len(impuestos) == 2
    # Renta: 10% de 1000
    assert impuestos[0].findtext("valorRetenido") == "100.00"
    # IVA: 30% de 150
    assert impuestos[1].findtext("valorRetenido") == "45.00"


def test_retencion_total(retencion):
    assert retencion.total_retenido == Decimal("145.00")


def test_retencion_referencia_documento_sustento(retencion):
    xml, _ = generar_xml_retencion(retencion, "12345678")
    impuesto = etree.fromstring(xml).find("impuestos/impuesto")

    assert impuesto.findtext("codDocSustento") == "01"
    assert impuesto.findtext("numDocSustento") == "001-001-000000123"
    assert impuesto.findtext("fechaEmisionDocSustento") == "01/08/2026"


def test_retencion_declara_periodo_fiscal(retencion):
    xml, _ = generar_xml_retencion(retencion, "12345678")
    assert etree.fromstring(xml).findtext("infoCompRetencion/periodoFiscal") == "08/2026"


def test_retencion_se_firma_y_verifica(retencion, firmante):
    xml, _ = generar_xml_retencion(retencion, "12345678")
    resultado = verificar_firma(firmar_xml(xml, firmante))
    assert all(resultado.values())
