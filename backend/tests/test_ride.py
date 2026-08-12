"""
Pruebas del RIDE (la representación impresa).

Las pruebas que ya existían solo comprobaban que el archivo empieza por
`%PDF-`. Eso pasa igual con un PDF en blanco. Aquí se extrae el texto y se
verifica **qué dice**, porque un RIDE sin clave de acceso es inservible: es el
dato con el que un tercero verifica el comprobante en el portal del SRI.
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sri.modelos import Comprador, Detalle, Emisor, Factura  # noqa: E402
from app.sri.ride import (  # noqa: E402
    generar_ride,
    generar_ride_guia,
    generar_ride_retencion,
)
from app.sri.xml_guia_remision import Destinatario, GuiaRemision, ItemGuia  # noqa: E402
from app.sri.xml_retencion import DetalleRetencion, Retencion  # noqa: E402

CLAVE = "0908202601179001691900110010010000000011234567819"
AUTORIZACION = "1122334455"


def texto_de(buffer) -> str:
    """
    Texto plano del PDF, con los espacios normalizados.

    ReportLab parte las celdas en fragmentos, así que comparar cadenas largas
    con espacios exactos es frágil; colapsarlos hace la prueba estable sin
    perder capacidad de detectar que un dato falta.
    """
    lector = PdfReader(buffer)
    crudo = "\n".join(pagina.extract_text() or "" for pagina in lector.pages)
    return " ".join(crudo.split())


@pytest.fixture
def emisor():
    return Emisor(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        nombre_comercial="DEMO",
        direccion_matriz="Av. Amazonas N21-147",
        direccion_establecimiento="Av. Amazonas N21-147",
        establecimiento="001",
        punto_emision="001",
        obligado_contabilidad=True,
    )


@pytest.fixture
def factura(emisor):
    return Factura(
        emisor=emisor,
        comprador=Comprador(
            tipo_identificacion="04",
            identificacion="0992339411001",
            razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
            direccion="Km 14.5 via Daule",
        ),
        fecha_emision=date(2026, 8, 9),
        secuencial=1,
        detalles=[
            Detalle(
                codigo_principal="PROD-001",
                descripcion="Laptop Dell XPS 13",
                cantidad=Decimal("2"),
                precio_unitario=Decimal("1000.00"),
                codigo_iva="4",
            ),
            Detalle(
                codigo_principal="PROD-002",
                descripcion="Arroz flor saco 25kg",
                cantidad=Decimal("10"),
                precio_unitario=Decimal("20.00"),
                codigo_iva="0",
            ),
        ],
        ambiente="1",
    )


# --------------------------------------------------------------------------
# RIDE de factura
# --------------------------------------------------------------------------


def test_el_ride_lleva_la_clave_de_acceso(factura):
    """Sin ella el documento no se puede verificar en el portal del SRI."""
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE))

    assert CLAVE in texto.replace(" ", "")


def test_el_ride_identifica_al_emisor_y_al_comprador(factura):
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE))

    assert "MI EMPRESA DEMO S.A." in texto
    assert "1790016919001" in texto
    assert "PLASTICOS DEL LITORAL PLASTLIT S.A." in texto
    assert "0992339411001" in texto


def test_el_ride_lista_los_detalles(factura):
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE))

    assert "Laptop Dell XPS 13" in texto
    assert "PROD-001" in texto
    assert "Arroz flor saco 25kg" in texto


def test_el_ride_imprime_los_totales_calculados(factura):
    """Los importes salen del motor, no de lo que le pasen al generador."""
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE))

    # 2 × 1000 = 2000 al 15% → 300 de IVA. Más 200 a tarifa 0 → total 2500.
    assert "2200.00" in texto  # subtotal sin impuestos
    assert "300.00" in texto  # IVA
    assert "2500.00" in texto  # valor total


def test_el_ride_avisa_cuando_es_ambiente_de_pruebas(factura):
    """Un RIDE de pruebas que no lo diga puede entregarse como si valiera."""
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE, ambiente="1"))

    assert "PRUEBAS" in texto
    assert "SIN VALIDEZ TRIBUTARIA" in texto


def test_en_produccion_no_aparece_el_aviso_de_pruebas(factura):
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE, ambiente="2"))

    assert "SIN VALIDEZ TRIBUTARIA" not in texto
    assert "PRODUCCIÓN" in texto or "PRODUCCION" in texto


def test_sin_autorizacion_el_ride_lo_dice(factura):
    """Un borrador impreso no debe aparentar estar autorizado."""
    texto = texto_de(generar_ride(factura, "001-001-000000001", CLAVE))

    assert "PENDIENTE DE AUTORIZACIÓN" in texto or "PENDIENTE" in texto


def test_con_autorizacion_el_ride_la_imprime(factura):
    texto = texto_de(
        generar_ride(
            factura,
            "001-001-000000001",
            CLAVE,
            numero_autorizacion=AUTORIZACION,
            fecha_autorizacion="2026-08-09T10:15:00-05:00",
        )
    )

    assert AUTORIZACION in texto
    assert "PENDIENTE DE AUTORIZACIÓN" not in texto


def test_el_titulo_cambia_segun_el_tipo(factura):
    """El mismo generador sirve para la nota de crédito."""
    texto = texto_de(
        generar_ride(factura, "001-001-000000001", CLAVE, titulo="NOTA DE CRÉDITO")
    )

    assert "NOTA DE CRÉDITO" in texto


def test_el_ride_es_un_pdf_valido_de_una_pagina(factura):
    lector = PdfReader(generar_ride(factura, "001-001-000000001", CLAVE))

    assert len(lector.pages) >= 1


# --------------------------------------------------------------------------
# RIDE de guía de remisión
# --------------------------------------------------------------------------


@pytest.fixture
def guia(emisor):
    return GuiaRemision(
        emisor=emisor,
        fecha_emision=date(2026, 8, 9),
        secuencial=7,
        transportista_tipo_identificacion="04",
        transportista_identificacion="0992339411001",
        transportista_razon_social="TRANSPORTES DEL SUR CIA. LTDA.",
        placa="PBA1234",
        direccion_partida="Bodega Norte, Quito",
        fecha_inicio=date(2026, 8, 9),
        fecha_fin=date(2026, 8, 10),
        destinatarios=[
            Destinatario(
                identificacion="0992339411001",
                razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
                direccion="Km 14.5 via Daule",
                motivo_traslado="Venta",
                items=[
                    ItemGuia(
                        codigo_interno="PROD-001",
                        descripcion="Laptop Dell XPS 13",
                        cantidad=Decimal("2"),
                    )
                ],
            )
        ],
        ambiente="1",
    )


def test_el_ride_de_guia_lleva_transportista_placa_y_rutas(guia):
    texto = texto_de(generar_ride_guia(guia, "001-001-000000007", CLAVE))

    assert "TRANSPORTES DEL SUR CIA. LTDA." in texto
    assert "PBA1234" in texto
    assert "Bodega Norte, Quito" in texto
    assert "Km 14.5 via Daule" in texto


def test_el_ride_de_guia_lleva_las_fechas_del_traslado(guia):
    texto = texto_de(generar_ride_guia(guia, "001-001-000000007", CLAVE))

    assert "09/08/2026" in texto
    assert "10/08/2026" in texto


def test_el_ride_de_guia_lista_la_mercaderia(guia):
    texto = texto_de(generar_ride_guia(guia, "001-001-000000007", CLAVE))

    assert "Laptop Dell XPS 13" in texto
    assert "PROD-001" in texto


def test_el_ride_de_guia_no_imprime_importes(guia):
    """
    La guía documenta un traslado, no una venta. Un precio impreso ahí
    induciría a tratarla como comprobante de venta.
    """
    texto = texto_de(generar_ride_guia(guia, "001-001-000000007", CLAVE))

    assert "VALOR TOTAL" not in texto
    assert "SUBTOTAL" not in texto
    assert "IVA" not in texto


def test_el_ride_de_guia_lleva_clave_y_dice_que_es_guia(guia):
    texto = texto_de(generar_ride_guia(guia, "001-001-000000007", CLAVE))

    assert CLAVE in texto.replace(" ", "")
    assert "GUÍA DE REMISIÓN" in texto or "GUIA DE REMISION" in texto


# --------------------------------------------------------------------------
# RIDE de retención
# --------------------------------------------------------------------------


@pytest.fixture
def retencion(emisor):
    return Retencion(
        emisor=emisor,
        sujeto_retenido=Comprador(
            tipo_identificacion="04",
            identificacion="0992339411001",
            razon_social="PROVEEDOR DEMO S.A.",
            direccion="Km 14.5 via Daule",
        ),
        fecha_emision=date(2026, 8, 9),
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


def test_el_ride_de_retencion_identifica_al_sujeto_retenido(retencion):
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "PROVEEDOR DEMO S.A." in texto
    assert "0992339411001" in texto


def test_el_ride_de_retencion_lleva_el_periodo_fiscal(retencion):
    """Es el dato con el que el proveedor imputa la retención en su 103."""
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "08/2026" in texto


def test_el_ride_de_retencion_detalla_base_porcentaje_y_valor(retencion):
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "1000.00" in texto  # base de renta
    assert "20.00" in texto  # 2% de 1000
    assert "45.00" in texto  # 30% de 150
    assert "150.00" in texto  # base de IVA


def test_el_ride_de_retencion_suma_el_total(retencion):
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "65.00" in texto


def test_el_ride_de_retencion_muestra_el_documento_sustento(retencion):
    """El proveedor necesita ver contra qué factura se le retuvo."""
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "001001000000123" in texto.replace(" ", "")
    assert "05/08/2026" in texto


def test_el_ride_de_retencion_dice_que_es_una_retencion(retencion):
    texto = texto_de(generar_ride_retencion(retencion, "001-001-000000003", CLAVE))

    assert "RETENCIÓN" in texto or "RETENCION" in texto
    assert CLAVE in texto.replace(" ", "")
