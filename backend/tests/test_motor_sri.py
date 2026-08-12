"""Pruebas del motor SRI: clave de acceso, XML y firma XAdES-BES."""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sri.clave_acceso import (  # noqa: E402
    DatosClaveAcceso,
    descomponer_clave_acceso,
    digito_verificador_modulo11,
    generar_clave_acceso,
    validar_clave_acceso,
)
from app.sri.firma import cargar_p12, firmar_xml, verificar_firma  # noqa: E402
from app.sri.modelos import Comprador, Detalle, Emisor, Factura  # noqa: E402
from app.sri.xml_factura import generar_xml_factura  # noqa: E402

NS_DS = "http://www.w3.org/2000/09/xmldsig#"


@pytest.fixture
def datos_clave() -> DatosClaveAcceso:
    return DatosClaveAcceso(
        fecha_emision=date(2026, 8, 8),
        tipo_comprobante="01",
        ruc="1790016919001",
        ambiente="1",
        establecimiento="001",
        punto_emision="002",
        secuencial=135,
        codigo_numerico="12345678",
    )


@pytest.fixture
def factura() -> Factura:
    emisor = Emisor(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        nombre_comercial="DEMO",
        direccion_matriz="Av. Amazonas N21-147 y Roca",
        direccion_establecimiento="Av. Amazonas N21-147 y Roca",
        establecimiento="001",
        punto_emision="002",
    )
    comprador = Comprador(
        tipo_identificacion="04",
        identificacion="0992339411001",
        razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
        direccion="Km 14.5 via Daule",
        correo="compras@plastlit.com",
    )
    return Factura(
        emisor=emisor,
        comprador=comprador,
        fecha_emision=date(2026, 8, 8),
        secuencial=135,
        detalles=[
            Detalle("PROD-001", "Laptop Dell XPS 13", Decimal("1"), Decimal("1200.00"), "4"),
            Detalle("PROD-003", "Pan comun 500g", Decimal("10"), Decimal("1.85"), "0"),
        ],
    )


# --------------------------------------------------------------------------
# Clave de acceso
# --------------------------------------------------------------------------


def test_clave_acceso_tiene_49_digitos(datos_clave):
    clave = generar_clave_acceso(datos_clave)
    assert len(clave) == 49
    assert clave.isdigit()


def test_clave_acceso_es_autoconsistente(datos_clave):
    assert validar_clave_acceso(generar_clave_acceso(datos_clave))


def test_clave_acceso_contiene_los_campos_en_orden(datos_clave):
    partes = descomponer_clave_acceso(generar_clave_acceso(datos_clave))
    assert partes["fecha_emision"] == "08082026"
    assert partes["tipo_comprobante"] == "01"
    assert partes["ruc"] == "1790016919001"
    assert partes["ambiente"] == "1"
    assert partes["serie"] == "001002"
    assert partes["secuencial"] == "000000135"
    assert partes["codigo_numerico"] == "12345678"
    assert partes["tipo_emision"] == "1"


def test_un_digito_alterado_invalida_la_clave(datos_clave):
    clave = generar_clave_acceso(datos_clave)
    alterada = clave[:20] + ("0" if clave[20] != "0" else "1") + clave[21:]
    assert not validar_clave_acceso(alterada)


def test_modulo11_casos_especiales():
    # residuo 0 -> verificador 11 -> se convierte en 0
    assert digito_verificador_modulo11("0" * 48) == 0
    assert digito_verificador_modulo11("1" * 48) in range(10)


def test_clave_acceso_rechaza_ruc_invalido(datos_clave):
    with pytest.raises(ValueError):
        DatosClaveAcceso(**{**datos_clave.__dict__, "ruc": "123"})


# --------------------------------------------------------------------------
# XML
# --------------------------------------------------------------------------


def test_xml_bien_formado_y_con_id_comprobante(factura):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)
    assert raiz.tag == "factura"
    assert raiz.get("id") == "comprobante"
    assert raiz.get("version") == "1.1.0"


def test_xml_agrupa_impuestos_por_tarifa(factura):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)

    grupos = raiz.findall("infoFactura/totalConImpuestos/totalImpuesto")
    resumen = {
        g.findtext("codigoPorcentaje"): (g.findtext("baseImponible"), g.findtext("valor"))
        for g in grupos
    }

    # IVA 0% sobre 18.50 y IVA 15% sobre 1200.00
    assert resumen["0"] == ("18.50", "0.00")
    assert resumen["4"] == ("1200.00", "180.00")


def test_xml_totales_cuadran(factura):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)

    total_sin = Decimal(raiz.findtext("infoFactura/totalSinImpuestos"))
    importe = Decimal(raiz.findtext("infoFactura/importeTotal"))
    iva = sum(
        Decimal(g.findtext("valor"))
        for g in raiz.findall("infoFactura/totalConImpuestos/totalImpuesto")
    )

    assert total_sin == Decimal("1218.50")
    assert iva == Decimal("180.00")
    assert importe == total_sin + iva


def test_xml_respeta_el_orden_del_esquema(factura):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)
    assert [hijo.tag for hijo in raiz] == ["infoTributaria", "infoFactura", "detalles"]

    info = raiz.find("infoTributaria")
    assert [hijo.tag for hijo in info][:6] == [
        "ambiente",
        "tipoEmision",
        "razonSocial",
        "nombreComercial",
        "ruc",
        "claveAcceso",
    ]


def test_clave_acceso_del_xml_coincide_con_la_devuelta(factura):
    xml, clave = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)
    assert raiz.findtext("infoTributaria/claveAcceso") == clave
    assert validar_clave_acceso(clave)


def test_detalle_aplica_descuento_a_la_base(factura):
    factura.detalles = [
        Detalle("X", "Con descuento", Decimal("2"), Decimal("25.50"), "4", Decimal("10"))
    ]
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(xml)

    detalle = raiz.find("detalles/detalle")
    assert detalle.findtext("descuento") == "5.10"
    assert detalle.findtext("precioTotalSinImpuesto") == "45.90"
    # 45.90 * 0.15 = 6.885 -> 6.89 con redondeo half-up
    assert detalle.findtext("impuestos/impuesto/valor") == "6.89"


# --------------------------------------------------------------------------
# Firma XAdES-BES
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def firmante(tmp_path_factory):
    """Certificado autofirmado: valida la mecánica, no la aceptación del SRI."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("certificados") / "pruebas.p12"
    generar(ruta, "pruebas123")
    return cargar_p12(str(ruta), "pruebas123")


def test_firma_produce_xml_valido(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    firmado = firmar_xml(xml, firmante)

    raiz = etree.fromstring(firmado)
    assert raiz.find(f"{{{NS_DS}}}Signature") is not None


def test_firma_tiene_las_tres_referencias(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(firmar_xml(xml, firmante))

    referencias = raiz.findall(f"{{{NS_DS}}}Signature/{{{NS_DS}}}SignedInfo/{{{NS_DS}}}Reference")
    assert len(referencias) == 3

    uris = [ref.get("URI") for ref in referencias]
    assert "#comprobante" in uris
    assert any(uri.endswith("SignedProperties1") for uri in uris)
    assert "#Certificate1" in uris


def test_referencia_al_documento_usa_enveloped_signature(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(firmar_xml(xml, firmante))

    referencia = next(
        ref
        for ref in raiz.findall(
            f"{{{NS_DS}}}Signature/{{{NS_DS}}}SignedInfo/{{{NS_DS}}}Reference"
        )
        if ref.get("URI") == "#comprobante"
    )
    transformada = referencia.find(f"{{{NS_DS}}}Transforms/{{{NS_DS}}}Transform")
    assert transformada.get("Algorithm") == "http://www.w3.org/2000/09/xmldsig#enveloped-signature"


def test_todos_los_digests_y_la_firma_rsa_verifican(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    resultado = verificar_firma(firmar_xml(xml, firmante))

    assert resultado == {
        "digest_signed_properties": True,
        "digest_key_info": True,
        "digest_documento": True,
        "firma_rsa": True,
    }


def test_alterar_el_comprobante_rompe_la_verificacion(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    firmado = firmar_xml(xml, firmante)

    # Se cambia el importe total: es el ataque que la firma debe detectar.
    alterado = firmado.replace(b"<importeTotal>1398.50</importeTotal>",
                               b"<importeTotal>1.00</importeTotal>")
    assert alterado != firmado

    resultado = verificar_firma(alterado)
    assert resultado["digest_documento"] is False


def test_firma_incluye_certificado_y_datos_del_emisor(factura, firmante):
    xml, _ = generar_xml_factura(factura, "12345678")
    raiz = etree.fromstring(firmar_xml(xml, firmante))

    certificado = raiz.findtext(
        f"{{{NS_DS}}}Signature/{{{NS_DS}}}KeyInfo/{{{NS_DS}}}X509Data/{{{NS_DS}}}X509Certificate"
    )
    assert certificado and len(certificado) > 100

    serie = raiz.find(
        f".//{{{NS_DS}}}X509SerialNumber"
    )
    assert serie is not None and serie.text.isdigit()
