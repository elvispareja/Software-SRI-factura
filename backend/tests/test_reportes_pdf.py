"""
Pruebas de la exportación de reportes a PDF.

Lo que se vigila aquí no es el diseño —eso se ve mirando el archivo— sino las
tres cosas que se rompen en silencio: que el navegador reciba realmente un PDF,
que un reporte de miles de filas se pagine con su cabecera repetida en lugar de
salir cortado, y que la falta de datos de la empresa no impida la descarga.
"""

from __future__ import annotations

import io
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.conftest import iniciar_sesion  # noqa: E402

ANIO = 2026

# Suficientes para desbordar la hoja: el objetivo de estas pruebas es
# justamente el reporte que no cabe en una página.
ARTICULOS = 250
RECEPTORES = 150

# Los diez reportes que se pueden imprimir, con los parámetros mínimos que
# exige cada uno.
RUTAS_PDF = [
    f"/api/reportes/iva/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/retenciones/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/ventas/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/egresos/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/notas/pdf?anio={ANIO}&mes=8",
    "/api/reportes/inventario/pdf",
    "/api/reportes/receptores/pdf",
    f"/api/reportes/notas-venta/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/cotizaciones/pdf?anio={ANIO}&mes=8",
    f"/api/reportes/estado-sri/pdf?anio={ANIO}&mes=8",
]


def _importar_app(ruta_bd: Path, clave: str):
    """Levanta una instancia limpia del API contra la base indicada."""
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{ruta_bd}"
    os.environ["CLAVE_SECRETA"] = clave

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion

    crear_tablas()
    return aplicacion, SesionLocal


def _poblar_articulos_y_receptores(sesion, Articulo, Receptor) -> None:
    """Carga lo que hace largos a los dos reportes que se paginan."""
    for indice in range(ARTICULOS):
        sesion.add(
            Articulo(
                codigo=f"ART-{indice:04d}",
                nombre=f"Artículo de prueba número {indice:04d} con nombre largo",
                tipo="Producto",
                categoria="General",
                unidad="Unidad",
                costo=Decimal("10.500000"),
                precio=Decimal("15.000000"),
                stock=Decimal("7.000000"),
                stock_minimo=Decimal("2.000000"),
            )
        )

    for indice in range(RECEPTORES):
        sesion.add(
            Receptor(
                razon_social=f"CLIENTE DE PRUEBA {indice:04d} S.A.",
                tipo_identificacion="04",
                identificacion=f"17900169{indice:05d}",
                rol="Cliente",
                correo=f"cliente{indice}@ejemplo.ec",
                telefono1="0999999999",
            )
        )


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    """API con empresa configurada y datos en todos los reportes."""
    base = tmp_path_factory.mktemp("bd_reportes_pdf") / "reportes_pdf.db"
    aplicacion, SesionLocal = _importar_app(base, "clave-de-prueba-reportes-pdf")

    from app.modelos_db import (
        Articulo,
        Comprobante,
        DetalleComprobante,
        DetalleRetencion,
        Empresa,
        Establecimiento,
        Gasto,
        PuntoEmision,
        Receptor,
        Retencion,
        TipoGasto,
    )

    sesion = SesionLocal()

    empresa = Empresa(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        nombre_comercial="DEMO",
        direccion_matriz="Av. Amazonas N21-147",
        ambiente="1",
    )
    establecimiento = Establecimiento(codigo="001", nombre="Matriz", direccion="Av. Amazonas")
    establecimiento.puntos_emision = [PuntoEmision(codigo="001", nombre="Caja")]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)

    def comprobante(numero, tipo, total, estado="Autorizado", **extra):
        return Comprobante(
            tipo=tipo,
            numero=numero,
            establecimiento="001",
            punto_emision="001",
            secuencial=int(numero[-3:]),
            fecha_emision=date(ANIO, 8, 5),
            receptor_razon_social="ACME S.A.",
            receptor_identificacion="1790016919001",
            total_sin_impuestos=Decimal(total),
            total_descuento=Decimal("0"),
            total_iva=Decimal("0"),
            importe_total=Decimal(total),
            estado_sri=estado,
            **extra,
        )

    factura = comprobante("001-001-000000001", "Factura", "1000.00")
    factura.total_iva = Decimal("150.00")
    factura.importe_total = Decimal("1150.00")
    factura.detalles = [
        DetalleComprobante(
            codigo_principal="ART-0001",
            descripcion="Artículo de prueba",
            cantidad=Decimal("1"),
            precio_unitario=Decimal("1000"),
            codigo_iva="4",
            base_imponible=Decimal("1000.00"),
            valor_iva=Decimal("150.00"),
            total=Decimal("1150.00"),
        )
    ]

    sesion.add_all(
        [
            factura,
            comprobante("001-001-000000002", "Nota de Venta", "80.00"),
            comprobante("001-001-000000003", "Cotización", "500.00", estado="Borrador"),
            comprobante(
                "001-001-000000004",
                "Nota de Crédito",
                "50.00",
                num_doc_modificado="001-001-000000001",
                motivo="Devolución parcial",
            ),
            comprobante(
                "001-001-000000005",
                "Nota de Débito",
                "20.00",
                num_doc_modificado="001-001-000000001",
                motivo="Interés por mora",
            ),
            # Uno sin autorizar, para que el reporte de estado tenga dos filas.
            comprobante("001-001-000000006", "Factura", "77.00", estado="Rechazado"),
        ]
    )

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
        total_retenido=Decimal("17.50"),
        estado_sri="Autorizado",
    )
    retencion.detalles = [
        DetalleRetencion(
            codigo_impuesto="1",
            codigo_retencion="312",
            base_imponible=Decimal("1000.00"),
            porcentaje_retener=Decimal("1.75"),
            valor_retenido=Decimal("17.50"),
        )
    ]
    sesion.add(retencion)

    tipo_gasto = TipoGasto(nombre="Suministros", deducible=True)
    sesion.add(tipo_gasto)
    sesion.flush()
    sesion.add(
        Gasto(
            fecha=date(ANIO, 8, 9),
            tipo_id=tipo_gasto.id,
            concepto="Resmas de papel",
            proveedor_razon_social="PAPELERÍA S.A.",
            subtotal=Decimal("100.00"),
            iva=Decimal("15.00"),
            total=Decimal("115.00"),
        )
    )

    _poblar_articulos_y_receptores(sesion, Articulo, Receptor)

    sesion.commit()
    sesion.close()

    return SimpleNamespace(cliente=iniciar_sesion(TestClient(aplicacion)))


@pytest.fixture(scope="module")
def entorno_sin_empresa(tmp_path_factory):
    """
    API sobre una base en la que nadie ha configurado todavía la empresa.

    Es el estado real de una instalación recién puesta en marcha, y un reporte
    de gestión tiene que poder imprimirse igualmente.
    """
    base = tmp_path_factory.mktemp("bd_reportes_pdf_vacio") / "sin_empresa.db"
    aplicacion, SesionLocal = _importar_app(base, "clave-de-prueba-reportes-pdf-vacio")

    from app.modelos_db import Articulo, Receptor

    sesion = SesionLocal()
    _poblar_articulos_y_receptores(sesion, Articulo, Receptor)
    sesion.commit()
    sesion.close()

    return SimpleNamespace(cliente=iniciar_sesion(TestClient(aplicacion)))


def _texto(contenido: bytes, pagina: int) -> str:
    """Texto de una página, sin espacios: el extractor los coloca a su gusto."""
    lectura = PdfReader(io.BytesIO(contenido))
    return "".join(lectura.pages[pagina].extract_text().split())


def _paginas(contenido: bytes) -> int:
    return len(PdfReader(io.BytesIO(contenido)).pages)


# --------------------------------------------------------------------------
# Lo mínimo: que sea un PDF
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", RUTAS_PDF)
def test_todos_los_reportes_se_descargan_en_pdf(entorno, ruta):
    respuesta = entorno.cliente.get(ruta)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    assert ".pdf" in respuesta.headers["content-disposition"]


def test_el_nombre_del_archivo_lleva_el_periodo(entorno):
    respuesta = entorno.cliente.get(f"/api/reportes/iva/pdf?anio={ANIO}&mes=8")

    assert 'filename="iva-ventas-08-2026.pdf"' in respuesta.headers["content-disposition"]


def test_el_pdf_exige_sesion(entorno):
    """El API está cerrado: sin token no se descarga nada."""
    sin_token = TestClient(entorno.cliente.app)
    respuesta = sin_token.get("/api/reportes/inventario/pdf")

    assert respuesta.status_code == 401


# --------------------------------------------------------------------------
# Cabecera, pie y paginación
# --------------------------------------------------------------------------


def test_la_cabecera_lleva_los_datos_de_la_empresa(entorno):
    contenido = entorno.cliente.get(f"/api/reportes/ventas/pdf?anio={ANIO}&mes=8").content
    texto = _texto(contenido, 0)

    assert "MIEMPRESADEMOS.A." in texto
    assert "1790016919001" in texto


def test_el_titulo_y_el_periodo_van_en_la_cabecera(entorno):
    contenido = entorno.cliente.get(f"/api/reportes/ventas/pdf?anio={ANIO}&mes=8").content
    texto = _texto(contenido, 0)

    assert "Ventasportipodecomprobante" in texto
    assert "Del01/08/2026al31/08/2026" in texto


def test_un_reporte_largo_ocupa_varias_paginas(entorno):
    """250 artículos no caben en una hoja; si cupieran, algo se está cortando."""
    contenido = entorno.cliente.get("/api/reportes/inventario/pdf").content

    assert _paginas(contenido) > 1


def test_los_receptores_tambien_se_paginan(entorno):
    contenido = entorno.cliente.get("/api/reportes/receptores/pdf").content

    assert _paginas(contenido) > 1


def test_la_cabecera_de_la_tabla_se_repite_en_cada_pagina(entorno):
    """
    Sin `repeatRows` la página 4 es una lista de números sin nombre.

    Se mira la segunda página justamente porque es donde falla: en la primera
    la cabecera está siempre.
    """
    contenido = entorno.cliente.get("/api/reportes/inventario/pdf").content
    texto = _texto(contenido, 1)

    assert "Código" in texto
    assert "Valoralcosto" in texto


def test_el_pie_numera_las_paginas_con_el_total(entorno):
    """
    "Página 1 de 8" solo se puede escribir en una segunda pasada.

    Si el total se resolviera mal, la primera página diría "de 1".
    """
    contenido = entorno.cliente.get("/api/reportes/inventario/pdf").content
    total = _paginas(contenido)

    assert total > 1
    assert f"Página1de{total}" in _texto(contenido, 0)
    assert f"Página{total}de{total}" in _texto(contenido, total - 1)


# --------------------------------------------------------------------------
# CSV y PDF salen de la misma fuente
# --------------------------------------------------------------------------


def test_el_pdf_y_el_csv_comparten_las_columnas(entorno):
    """
    Las cabeceras del PDF son las del CSV, no una copia escrita aparte.

    Si alguien añade una columna al CSV y el PDF no la trae, es que volvieron a
    duplicarse las filas y esta prueba es la que debe avisar.
    """
    csv = entorno.cliente.get(f"/api/reportes/iva/csv?anio={ANIO}&mes=8").content.decode("utf-8")
    columnas = csv.lstrip("﻿").splitlines()[0].split(";")

    texto = _texto(entorno.cliente.get(f"/api/reportes/iva/pdf?anio={ANIO}&mes=8").content, 0)

    for columna in columnas:
        assert "".join(columna.split()) in texto


def test_el_total_del_csv_aparece_en_el_pdf(entorno):
    csv = entorno.cliente.get("/api/reportes/inventario/csv").content.decode("utf-8")
    valor_inventario = csv.rstrip().splitlines()[-1].split(";")[8]

    contenido = entorno.cliente.get("/api/reportes/inventario/pdf").content
    texto = _texto(contenido, _paginas(contenido) - 1)

    assert f"{Decimal(valor_inventario):.2f}" in texto


# --------------------------------------------------------------------------
# Empresa sin configurar
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ruta", RUTAS_PDF)
def test_sin_empresa_configurada_el_pdf_se_genera_igual(entorno_sin_empresa, ruta):
    """
    Un reporte de gestión no se transmite al SRI.

    Bloquear la descarga con un 409 porque falten los datos del emisor —como sí
    hace la emisión de comprobantes— sería estorbar sin ganar nada.
    """
    respuesta = entorno_sin_empresa.cliente.get(ruta)

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.content.startswith(b"%PDF")


def test_sin_empresa_la_cabecera_no_finge_datos(entorno_sin_empresa):
    contenido = entorno_sin_empresa.cliente.get("/api/reportes/inventario/pdf").content
    texto = _texto(contenido, 0)

    assert "Inventario" in texto
    assert "RUC" not in texto


def test_el_generador_acepta_empresa_nula_y_tabla_vacia():
    """El caso límite: ni empresa, ni filas. Debe salir un PDF, no una excepción."""
    from app.servicios.reportes_pdf import generar_pdf_reporte

    contenido = generar_pdf_reporte(
        empresa=None,
        titulo="Reporte vacío",
        subtitulo="Sin datos",
        cabeceras=["Concepto", "Valor"],
        filas=[],
    )

    assert contenido.startswith(b"%PDF")
