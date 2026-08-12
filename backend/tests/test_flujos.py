"""
Flujo completo de cada opción del sistema, de punta a punta.

Las pruebas que ya existían verifican piezas sueltas —que se crea, que numera,
que firma—. Éstas recorren el camino entero que hace un usuario real:

    crear → emitir → consultar → descargar el RIDE → descargar el XML

y lo hacen **para cada tipo de documento**, porque un tipo puede estar bien
creado y no llegar nunca al SRI. Así se descubrió que la nota de débito se
podía capturar en pantalla pero no tenía generador de XML.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from lxml import etree
from pypdf import PdfReader

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
    numero_autorizacion: str | None = "9988776655"
    fecha_autorizacion: str | None = "2026-08-09T09:00:00-05:00"
    comprobante: str | None = None
    mensajes: list = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_flujos") / "flujos.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-flujos"

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
def certificado(cliente, tmp_path_factory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("cert_flujos") / "cert.p12"
    generar(ruta, "pruebas123")

    with open(ruta, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("cert.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture(scope="module")
def cliente_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "PLASTICOS DEL LITORAL PLASTLIT S.A.",
            "direccion": "Km 14.5 via Daule",
            "rol": "Cliente",
        },
    ).json()["id"]


@pytest.fixture(scope="module")
def proveedor_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "Cédula",
            "identificacion": "1710034065",
            "razon_social": "JUAN PEREZ",
            "direccion": "Quito, Av. 6 de Diciembre",
            "rol": "Proveedor",
        },
    ).json()["id"]


@pytest.fixture(autouse=True)
def sri_simulado(monkeypatch):
    """El SRI responde autorizando; lo que se prueba es la orquestación."""
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )


LINEA = {
    "codigo_principal": "PROD-001",
    "descripcion": "Laptop Dell XPS 13",
    "cantidad": "2",
    "precio_unitario": "1000.00",
    "codigo_iva": "4",
}


def _crear(cliente, tipo, receptor_id, **extra):
    cuerpo = {
        "tipo": tipo,
        "receptor_id": receptor_id,
        "establecimiento": "001",
        "punto_emision": "001",
        "detalles": [LINEA],
        **extra,
    }
    respuesta = cliente.post("/api/comprobantes", json=cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


REFERENCIA_NOTA = {
    "cod_doc_modificado": "01",
    "num_doc_modificado": "001-001-000000001",
    "fecha_doc_modificado": "2026-08-01",
    "motivo": "Ajuste sobre la factura original",
}


# --------------------------------------------------------------------------
# Flujo completo por tipo electrónico
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "tipo,cod_doc,raiz_xml",
    [
        ("Factura", "01", "factura"),
        ("Nota de Crédito", "04", "notaCredito"),
        ("Nota de Débito", "05", "notaDebito"),
        ("Liquidación de Compra", "03", "factura"),
        ("Nota de Venta", "01", "factura"),
    ],
)
def test_flujo_completo(cliente, cliente_id, proveedor_id, certificado, tipo, cod_doc, raiz_xml):
    """
    Crear → emitir → RIDE → XML, para cada tipo que viaja al SRI.

    La liquidación de compra se emite contra un proveedor, no contra un
    cliente: documenta una compra a alguien que no puede facturar.
    """
    receptor = proveedor_id if tipo == "Liquidación de Compra" else cliente_id
    extra = REFERENCIA_NOTA if tipo in ("Nota de Crédito", "Nota de Débito") else {}

    documento = _crear(cliente, tipo, receptor, **extra)
    assert documento["estado_sri"] == "Borrador"

    # --- Emisión ---
    emision = cliente.post(f"/api/comprobantes/{documento['id']}/emitir")
    assert emision.status_code == 200, emision.text
    datos = emision.json()

    assert datos["comprobante"]["estado_sri"] == "Autorizado"
    assert datos["comprobante"]["numero_autorizacion"] == "9988776655"
    assert len(datos["comprobante"]["clave_acceso"]) == 49

    # El tipo de comprobante va codificado en la propia clave de acceso.
    assert datos["comprobante"]["clave_acceso"][8:10] == cod_doc

    # --- XML ---
    xml = cliente.get(f"/api/comprobantes/{documento['id']}/xml")
    assert xml.status_code == 200
    raiz = etree.fromstring(xml.content)
    assert raiz.tag == raiz_xml
    assert raiz.findtext("infoTributaria/codDoc") == cod_doc
    # Emitido significa firmado: el XML descargado lleva la firma.
    assert b"Signature" in xml.content

    # --- RIDE ---
    ride = cliente.get(f"/api/comprobantes/{documento['id']}/ride")
    assert ride.status_code == 200
    assert ride.headers["content-type"] == "application/pdf"

    texto = " ".join(
        (PdfReader(__import__("io").BytesIO(ride.content)).pages[0].extract_text() or "").split()
    )
    assert "9988776655" in texto
    assert "PLASTICOS" in texto or "JUAN PEREZ" in texto


def test_la_nota_de_debito_declara_motivos_y_no_detalles(cliente, cliente_id, certificado):
    """
    Es la diferencia estructural con la nota de crédito: lo que se cobra de
    más es un concepto, no mercadería.
    """
    nota = _crear(cliente, "Nota de Débito", cliente_id, **REFERENCIA_NOTA)
    cliente.post(f"/api/comprobantes/{nota['id']}/emitir")

    raiz = etree.fromstring(cliente.get(f"/api/comprobantes/{nota['id']}/xml").content)

    assert raiz.find("detalles") is None

    motivos = raiz.findall("motivos/motivo")
    assert len(motivos) == 1
    assert motivos[0].findtext("razon") == "Laptop Dell XPS 13"
    assert motivos[0].findtext("valor") == "2000.00"


def test_la_nota_de_debito_referencia_el_documento_modificado(cliente, cliente_id, certificado):
    nota = _crear(cliente, "Nota de Débito", cliente_id, **REFERENCIA_NOTA)
    cliente.post(f"/api/comprobantes/{nota['id']}/emitir")

    raiz = etree.fromstring(cliente.get(f"/api/comprobantes/{nota['id']}/xml").content)
    info = raiz.find("infoNotaDebito")

    assert info.findtext("codDocModificado") == "01"
    assert info.findtext("numDocModificado") == "001-001-000000001"
    assert info.findtext("fechaEmisionDocSustento") == "01/08/2026"
    assert info.findtext("valorTotal") == "2300.00"


def test_el_ride_rotula_cada_tipo_con_su_nombre(cliente, cliente_id, certificado):
    """
    Antes todos los RIDE decían "FACTURA". Una nota de crédito impresa como
    factura es un documento equivocado en manos del cliente.
    """
    import io

    for tipo, rotulo in [
        ("Factura", "FACTURA"),
        ("Nota de Crédito", "NOTA DE CRÉDITO"),
        ("Nota de Débito", "NOTA DE DÉBITO"),
    ]:
        extra = REFERENCIA_NOTA if tipo != "Factura" else {}
        documento = _crear(cliente, tipo, cliente_id, **extra)

        ride = cliente.get(f"/api/comprobantes/{documento['id']}/ride")
        texto = " ".join(
            (PdfReader(io.BytesIO(ride.content)).pages[0].extract_text() or "").split()
        )

        assert rotulo in texto, f"El RIDE de {tipo} no dice «{rotulo}»"


# --------------------------------------------------------------------------
# Cotización: el tipo que NO viaja al SRI
# --------------------------------------------------------------------------


def test_flujo_de_cotizacion(cliente, cliente_id):
    """
    Se crea y se imprime, pero no se transmite: una cotización no es un
    comprobante electrónico.
    """
    cotizacion = _crear(cliente, "Cotización", cliente_id, validez_dias=15)

    assert cotizacion["validez_dias"] == 15

    emision = cliente.post(f"/api/comprobantes/{cotizacion['id']}/emitir")
    assert emision.status_code == 422
    assert "no se transmite" in emision.json()["detail"]

    # El XML tampoco: no existe tal cosa para una cotización.
    assert cliente.get(f"/api/comprobantes/{cotizacion['id']}/xml").status_code == 422

    # El PDF sí, que es para lo que sirve.
    assert cliente.get(f"/api/comprobantes/{cotizacion['id']}/ride").status_code == 200


# --------------------------------------------------------------------------
# Flujo de guía de remisión
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def transportista_id(cliente):
    return cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "1790016919001",
            "razon_social": "TRANSPORTES DEL SUR CIA. LTDA.",
            "direccion": "Av. Juan Tanca Marengo",
            "rol": "Transportista",
        },
    ).json()["id"]


def test_flujo_completo_de_guia(cliente, transportista_id, certificado, monkeypatch):
    import io

    import app.servicios.emision_guias as emision_guias

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = cliente.post(
        "/api/guias",
        json={
            "establecimiento": "001",
            "punto_emision": "001",
            "fecha_inicio": "2026-08-09",
            "fecha_fin": "2026-08-10",
            "motivo_traslado": "Venta",
            "transportista_id": transportista_id,
            "placa": "pba1234",
            "direccion_partida": "Bodega Norte, Quito",
            "direccion_llegada": "Km 14.5 via Daule",
            "items": [{"codigo": "PROD-001", "descripcion": "Laptop", "cantidad": "2"}],
        },
    ).json()

    # La placa se normaliza a mayúsculas: el SRI la espera así.
    assert guia["placa"] == "PBA1234"

    emision = cliente.post(f"/api/guias/{guia['id']}/emitir")
    assert emision.status_code == 200, emision.text
    assert emision.json()["guia"]["estado_sri"] == "Autorizado"

    raiz = etree.fromstring(cliente.get(f"/api/guias/{guia['id']}/xml").content)
    assert raiz.tag == "guiaRemision"
    assert raiz.findtext("infoTributaria/codDoc") == "06"

    ride = cliente.get(f"/api/guias/{guia['id']}/ride")
    assert ride.status_code == 200
    texto = " ".join(
        (PdfReader(io.BytesIO(ride.content)).pages[0].extract_text() or "").split()
    )
    assert "PBA1234" in texto
    assert "TRANSPORTES DEL SUR" in texto


# --------------------------------------------------------------------------
# Flujo de retención
# --------------------------------------------------------------------------


def test_flujo_completo_de_retencion(cliente, proveedor_id, certificado, monkeypatch):
    import io

    import app.servicios.emision_retenciones as emision_ret

    monkeypatch.setattr(
        emision_ret, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    retencion = cliente.post(
        "/api/retenciones",
        json={
            "establecimiento": "001",
            "punto_emision": "001",
            "fecha_emision": "2026-08-09",
            "sujeto_id": proveedor_id,
            "num_doc_sustento": "001-001-000000123",
            "fecha_doc_sustento": "2026-08-05",
            "detalles": [
                {
                    "codigo_impuesto": "1",
                    "codigo_retencion": "312",
                    "base_imponible": "1000.00",
                    "porcentaje_retener": "2",
                }
            ],
        },
    )
    assert retencion.status_code == 201, retencion.text
    retencion = retencion.json()

    assert retencion["periodo_fiscal"] == "08/2026"

    emision = cliente.post(f"/api/retenciones/{retencion['id']}/emitir")
    assert emision.status_code == 200, emision.text
    assert emision.json()["retencion"]["estado_sri"] == "Autorizado"

    raiz = etree.fromstring(cliente.get(f"/api/retenciones/{retencion['id']}/xml").content)
    assert raiz.tag == "comprobanteRetencion"
    assert raiz.findtext("infoTributaria/codDoc") == "07"

    ride = cliente.get(f"/api/retenciones/{retencion['id']}/ride")
    texto = " ".join(
        (PdfReader(io.BytesIO(ride.content)).pages[0].extract_text() or "").split()
    )
    assert "JUAN PEREZ" in texto
    assert "08/2026" in texto


# --------------------------------------------------------------------------
# Flujo de datos maestros: crear, editar, desactivar
# --------------------------------------------------------------------------


def test_flujo_de_receptores(cliente):
    creado = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "Cédula",
            "identificacion": "0912345675",
            "razon_social": "MARIA LOPEZ",
            "direccion": "Guayaquil",
        },
    )
    assert creado.status_code == 201, creado.text
    receptor = creado.json()

    # Editar
    editado = cliente.put(
        f"/api/receptores/{receptor['id']}",
        json={**receptor, "razon_social": "MARIA LOPEZ VERA", "telefono1": "0991234567"},
    )
    assert editado.status_code == 200
    assert editado.json()["razon_social"] == "MARIA LOPEZ VERA"

    # Buscar
    encontrados = cliente.get("/api/receptores?buscar=lopez").json()
    assert any(r["id"] == receptor["id"] for r in encontrados)

    # Desactivar no borra: los comprobantes emitidos siguen apuntando a él.
    assert cliente.delete(f"/api/receptores/{receptor['id']}").status_code == 204
    assert cliente.get(f"/api/receptores/{receptor['id']}").json()["estado"] == "Inactivo"


def test_flujo_de_articulos(cliente):
    creado = cliente.post(
        "/api/articulos",
        json={
            "codigo": "FLUJO-001",
            "nombre": "Artículo de prueba",
            "precio": "100.00",
            "costo": "60.00",
            "codigo_iva": "4",
            "stock": "10",
        },
    )
    assert creado.status_code == 201, creado.text
    articulo = creado.json()

    editado = cliente.put(
        f"/api/articulos/{articulo['id']}",
        json={**articulo, "precio": "120.00"},
    )
    assert editado.status_code == 200
    assert editado.json()["precio"] == "120.000000"

    assert cliente.delete(f"/api/articulos/{articulo['id']}").status_code == 204
    assert cliente.get(f"/api/articulos/{articulo['id']}").json()["estado"] == "Inactivo"


def test_flujo_de_configuracion_de_empresa(cliente):
    empresa = cliente.get("/api/configuracion/empresa").json()

    guardada = cliente.put(
        "/api/configuracion/empresa",
        json={**empresa, "nombre_comercial": "DEMO COMERCIAL", "telefono": "022345678"},
    )
    assert guardada.status_code == 200
    assert guardada.json()["nombre_comercial"] == "DEMO COMERCIAL"


def test_flujo_de_cuentas_bancarias(cliente):
    creada = cliente.post(
        "/api/configuracion/cuentas",
        json={
            "banco": "Banco Pichincha",
            "tipo": "Corriente",
            "numero": "2100123456",
            "titular": "MI EMPRESA DEMO S.A.",
        },
    )
    assert creada.status_code == 201, creada.text

    assert any(c["banco"] == "Banco Pichincha" for c in cliente.get("/api/configuracion/cuentas").json())
    assert cliente.delete(f"/api/configuracion/cuentas/{creada.json()['id']}").status_code == 204


# --------------------------------------------------------------------------
# Los reportes reflejan lo que se emitió
# --------------------------------------------------------------------------


def test_lo_emitido_aparece_en_los_reportes(cliente, cliente_id, certificado):
    """
    Cierra el círculo: si un comprobante se autoriza, el reporte del período
    tiene que contarlo. Es lo que conecta la emisión con la declaración.
    """
    antes = cliente.get("/api/reportes/ventas?anio=2026").json()

    factura = _crear(cliente, "Factura", cliente_id)
    cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    despues = cliente.get("/api/reportes/ventas?anio=2026").json()

    assert despues["comprobantes"] == antes["comprobantes"] + 1
    assert float(despues["total"]) > float(antes["total"])
