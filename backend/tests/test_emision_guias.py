"""
Pruebas de la guía de remisión: XML y emisión.

La guía es el comprobante más distinto de todos —no lleva importes ni
impuestos— así que su XML se verifica aparte. La orquestación de la emisión
comparte código con `emision.py`, y aquí se comprueba que efectivamente lo
comparte: mismo certificado, mismo guardado previo del XML firmado.
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
    numero_autorizacion: str | None = "0987654321"
    fecha_autorizacion: str | None = "2026-08-08T11:00:00-05:00"
    comprobante: str | None = None
    mensajes: list = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


# --------------------------------------------------------------------------
# XML puro, sin base de datos
# --------------------------------------------------------------------------


def _modelo_guia():
    from app.sri.modelos import Emisor
    from app.sri.xml_guia_remision import Destinatario, GuiaRemision, ItemGuia

    return GuiaRemision(
        emisor=Emisor(
            ruc="1790016919001",
            razon_social="MI EMPRESA DEMO S.A.",
            nombre_comercial="DEMO",
            direccion_matriz="Av. Amazonas N21-147",
            direccion_establecimiento="Av. Amazonas N21-147",
            establecimiento="001",
            punto_emision="001",
            obligado_contabilidad=True,
        ),
        fecha_emision=date(2026, 8, 8),
        secuencial=7,
        transportista_tipo_identificacion="04",
        transportista_identificacion="0992339411001",
        transportista_razon_social="TRANSPORTES DEL SUR CIA. LTDA.",
        placa="PBA1234",
        direccion_partida="Bodega Norte, Quito",
        fecha_inicio=date(2026, 8, 8),
        fecha_fin=date(2026, 8, 9),
        destinatarios=[
            Destinatario(
                identificacion="0992339411001",
                razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
                direccion="Km 14.5 via Daule",
                motivo_traslado="Venta",
                items=[
                    ItemGuia(
                        codigo_interno="PROD-001",
                        descripcion="Laptop",
                        cantidad=Decimal("2"),
                    )
                ],
            )
        ],
        ambiente="1",
    )


def test_el_xml_tiene_la_estructura_de_la_ficha_tecnica():
    from app.sri.xml_guia_remision import generar_xml_guia_remision

    xml, clave = generar_xml_guia_remision(_modelo_guia(), "00000007")
    raiz = etree.fromstring(xml)

    assert raiz.tag == "guiaRemision"
    assert raiz.get("version") == "1.1.0"
    assert raiz.findtext("infoTributaria/codDoc") == "06"
    assert raiz.findtext("infoTributaria/claveAcceso") == clave
    assert raiz.findtext("infoTributaria/secuencial") == "000000007"

    info = raiz.find("infoGuiaRemision")
    assert info.findtext("dirPartida") == "Bodega Norte, Quito"
    assert info.findtext("placa") == "PBA1234"
    assert info.findtext("fechaIniTransporte") == "08/08/2026"
    assert info.findtext("fechaFinTransporte") == "09/08/2026"
    assert info.findtext("obligadoContabilidad") == "SI"

    # Un comprobante sin importes: nada de totales ni impuestos.
    assert raiz.find("infoFactura") is None
    assert raiz.find("totalConImpuestos") is None


def test_los_detalles_van_dentro_del_destinatario():
    """No cuelgan de la raíz como en la factura: el SRI los anida por entrega."""
    from app.sri.xml_guia_remision import generar_xml_guia_remision

    xml, _ = generar_xml_guia_remision(_modelo_guia(), "00000007")
    raiz = etree.fromstring(xml)

    assert raiz.find("detalles") is None

    destinatario = raiz.find("destinatarios/destinatario")
    assert destinatario.findtext("razonSocialDestinatario") == "PLASTICOS DEL LITORAL PLASTLIT S.A."
    assert destinatario.findtext("motivoTraslado") == "Venta"

    detalle = destinatario.find("detalles/detalle")
    assert detalle.findtext("codigoInterno") == "PROD-001"
    assert detalle.findtext("cantidad") == "2.000000"


def test_el_motivo_se_traduce_al_texto_del_sri():
    """La UI dice 'Traslado entre bodegas'; el SRI espera su propia redacción."""
    from app.sri.xml_guia_remision import generar_xml_guia_remision

    guia = _modelo_guia()
    guia.destinatarios[0].motivo_traslado = "Traslado entre bodegas"

    xml, _ = generar_xml_guia_remision(guia, "00000007")
    raiz = etree.fromstring(xml)

    assert (
        raiz.findtext("destinatarios/destinatario/motivoTraslado")
        == "Traslado entre establecimientos de una misma empresa"
    )


def test_la_clave_de_acceso_declara_guia_de_remision():
    from app.sri.xml_guia_remision import generar_xml_guia_remision

    _, clave = generar_xml_guia_remision(_modelo_guia(), "00000007")

    assert len(clave) == 49
    assert clave[8:10] == "06"  # tipo de comprobante
    assert clave[:8] == "08082026"


# --------------------------------------------------------------------------
# Emisión a través del API
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_guias") / "guias.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-guias"

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
def transportista_id(cliente):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "TRANSPORTES DEL SUR CIA. LTDA.",
            "direccion": "Av. Juan Tanca Marengo",
            "rol": "Transportista",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()["id"]


@pytest.fixture(scope="module")
def certificado(cliente, tmp_path_factory):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path_factory.mktemp("cert_guias") / "cert.p12"
    generar(ruta, "pruebas123")

    with open(ruta, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("cert.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _crear_guia(cliente, transportista_id):
    respuesta = cliente.post(
        "/api/guias",
        json={
            "establecimiento": "001",
            "punto_emision": "001",
            "fecha_inicio": "2026-08-08",
            "fecha_fin": "2026-08-09",
            "motivo_traslado": "Venta",
            "transportista_id": transportista_id,
            "placa": "pba1234",
            "direccion_partida": "Bodega Norte, Quito",
            "direccion_llegada": "Km 14.5 via Daule",
            "items": [{"codigo": "PROD-001", "descripcion": "Laptop", "cantidad": "2"}],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_sin_certificado_la_guia_no_se_emite(cliente, transportista_id):
    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.post(f"/api/guias/{guia['id']}/emitir")

    assert respuesta.status_code == 422
    assert "certificado" in respuesta.json()["detail"].lower()


def test_guia_autorizada(cliente, transportista_id, certificado, monkeypatch):
    import app.servicios.emision_guias as emision_guias

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.post(f"/api/guias/{guia['id']}/emitir")

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["estado_recepcion"] == "RECIBIDA"
    assert datos["guia"]["estado_sri"] == "Autorizado"
    assert datos["guia"]["numero_autorizacion"] == "0987654321"
    assert len(datos["guia"]["clave_acceso"]) == 49


def test_el_xml_firmado_de_la_guia_queda_guardado(
    cliente, transportista_id, certificado, monkeypatch
):
    import app.servicios.emision_guias as emision_guias
    from app.base_datos import SesionLocal
    from app.modelos_db import GuiaRemision

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = _crear_guia(cliente, transportista_id)
    cliente.post(f"/api/guias/{guia['id']}/emitir")

    sesion = SesionLocal()
    guardado = sesion.get(GuiaRemision, guia["id"]).xml_firmado
    sesion.close()

    assert "<guiaRemision" in guardado
    assert "ds:Signature" in guardado


def test_no_se_reenvia_una_guia_autorizada(cliente, transportista_id, certificado, monkeypatch):
    import app.servicios.emision_guias as emision_guias

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = _crear_guia(cliente, transportista_id)
    cliente.post(f"/api/guias/{guia['id']}/emitir")

    segunda = cliente.post(f"/api/guias/{guia['id']}/emitir")
    assert segunda.status_code == 422
    assert "ya está autorizada" in segunda.json()["detail"]


def test_guia_devuelta_guarda_los_mensajes(cliente, transportista_id, certificado, monkeypatch):
    import app.servicios.emision_guias as emision_guias

    mensajes = [
        {
            "identificador": "35",
            "mensaje": "PLACA INVALIDA",
            "informacion_adicional": "",
            "tipo": "ERROR",
        }
    ]
    monkeypatch.setattr(
        emision_guias,
        "transmitir_al_sri",
        lambda *_: (RecepcionFalsa(estado="DEVUELTA", mensajes=mensajes), None),
    )

    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.post(f"/api/guias/{guia['id']}/emitir")

    assert respuesta.status_code == 200
    assert respuesta.json()["guia"]["estado_sri"] == "Devuelto"
    assert respuesta.json()["mensajes"][0]["identificador"] == "35"


def test_fallo_de_red_deja_la_guia_firmada(cliente, transportista_id, certificado, monkeypatch):
    import app.servicios.emision_guias as emision_guias
    from app.base_datos import SesionLocal
    from app.modelos_db import GuiaRemision

    def explotar(*_):
        raise ConnectionError("timeout")

    monkeypatch.setattr(emision_guias, "transmitir_al_sri", explotar)

    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.post(f"/api/guias/{guia['id']}/emitir")

    assert respuesta.status_code == 422

    sesion = SesionLocal()
    guardada = sesion.get(GuiaRemision, guia["id"])
    assert guardada.estado_sri == "Error"
    assert guardada.xml_firmado is not None
    assert guardada.clave_acceso is not None
    sesion.close()


def test_una_guia_anulada_no_se_emite(cliente, transportista_id, certificado):
    guia = _crear_guia(cliente, transportista_id)
    cliente.post(f"/api/guias/{guia['id']}/anular")

    respuesta = cliente.post(f"/api/guias/{guia['id']}/emitir")
    assert respuesta.status_code == 422
    assert "Anulado" in respuesta.json()["detail"]


def test_el_secuencial_de_guias_es_independiente(cliente, transportista_id):
    """
    El SRI numera cada tipo de documento por separado: emitir facturas no debe
    mover el correlativo de las guías.
    """
    primera = _crear_guia(cliente, transportista_id)
    segunda = _crear_guia(cliente, transportista_id)

    numero_primera = int(primera["numero"].split("-")[-1])
    numero_segunda = int(segunda["numero"].split("-")[-1])

    assert numero_segunda == numero_primera + 1


# --------------------------------------------------------------------------
# RIDE, XML y reconsulta
# --------------------------------------------------------------------------


def test_el_ride_de_la_guia_sale_en_pdf(cliente, transportista_id):
    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.get(f"/api/guias/{guia['id']}/ride")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.headers["content-type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")


def test_el_ride_de_un_borrador_avisa_que_no_está_autorizado(cliente, transportista_id):
    """
    Un RIDE en borrador no debe parecer un comprobante válido: lleva la franja
    de pruebas y "PENDIENTE DE AUTORIZACIÓN" donde iría el número.
    """
    from pypdf import PdfReader
    import io as _io

    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.get(f"/api/guias/{guia['id']}/ride")

    texto = "".join(p.extract_text() for p in PdfReader(_io.BytesIO(respuesta.content)).pages)

    assert "GUÍA DE REMISIÓN" in texto
    assert "PENDIENTE DE AUTORIZACIÓN" in texto
    assert "SIN VALIDEZ TRIBUTARIA" in texto
    # Lo propio de la guía: transportista, placa y mercadería. Nada de totales.
    assert "PBA1234" in texto
    assert "Laptop" in texto
    assert "TOTAL" not in texto


def test_el_ride_autorizado_lleva_el_numero(cliente, transportista_id, certificado, monkeypatch):
    from pypdf import PdfReader
    import io as _io

    import app.servicios.emision_guias as emision_guias

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = _crear_guia(cliente, transportista_id)
    cliente.post(f"/api/guias/{guia['id']}/emitir")

    respuesta = cliente.get(f"/api/guias/{guia['id']}/ride")
    texto = "".join(p.extract_text() for p in PdfReader(_io.BytesIO(respuesta.content)).pages)

    assert "0987654321" in texto
    assert "PENDIENTE DE AUTORIZACIÓN" not in texto


def test_el_xml_de_un_borrador_se_genera_al_vuelo(cliente, transportista_id):
    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.get(f"/api/guias/{guia['id']}/xml")

    assert respuesta.status_code == 200
    assert b"<guiaRemision" in respuesta.content
    # Sin firmar todavía: aún no se ha emitido.
    assert b"ds:Signature" not in respuesta.content


def test_el_xml_de_una_emitida_es_el_firmado(cliente, transportista_id, certificado, monkeypatch):
    import app.servicios.emision_guias as emision_guias

    monkeypatch.setattr(
        emision_guias, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    guia = _crear_guia(cliente, transportista_id)
    cliente.post(f"/api/guias/{guia['id']}/emitir")

    respuesta = cliente.get(f"/api/guias/{guia['id']}/xml")

    assert b"ds:Signature" in respuesta.content
    # El archivo se nombra con la clave de acceso: es como se archiva ante el SRI.
    assert ".xml" in respuesta.headers["content-disposition"]


def test_consultar_sin_transmitir_falla(cliente, transportista_id):
    guia = _crear_guia(cliente, transportista_id)
    respuesta = cliente.post(f"/api/guias/{guia['id']}/consultar")

    assert respuesta.status_code == 422
    assert "aún no se ha transmitido" in respuesta.json()["detail"]


def test_consultar_autoriza_una_guia_pendiente(cliente, transportista_id, certificado, monkeypatch):
    """La autorización no es síncrona: puede llegar minutos después."""
    import app.servicios.emision_guias as emision_guias
    import app.sri.servicios as servicios_sri

    monkeypatch.setattr(
        emision_guias,
        "transmitir_al_sri",
        lambda *_: (
            RecepcionFalsa(),
            AutorizacionFalsa(estado="EN PROCESO", numero_autorizacion=None),
        ),
    )
    guia = _crear_guia(cliente, transportista_id)
    emitida = cliente.post(f"/api/guias/{guia['id']}/emitir")
    assert emitida.json()["guia"]["estado_sri"] == "Pendiente"

    monkeypatch.setattr(servicios_sri, "consultar_autorizacion", lambda *_: AutorizacionFalsa())
    respuesta = cliente.post(f"/api/guias/{guia['id']}/consultar")

    assert respuesta.status_code == 200
    assert respuesta.json()["guia"]["estado_sri"] == "Autorizado"
    assert respuesta.json()["guia"]["numero_autorizacion"] == "0987654321"
