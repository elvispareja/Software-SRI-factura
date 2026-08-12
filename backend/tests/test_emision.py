"""
Pruebas de la emisión al SRI.

Los WebServices se sustituyen por dobles: lo que se prueba es la orquestación
—firmar con el certificado guardado, guardar la clave antes de transmitir,
interpretar la respuesta— no que el SRI responda.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
    numero_autorizacion: str | None = "1234567890"
    fecha_autorizacion: str | None = "2026-08-08T10:15:00-05:00"
    comprobante: str | None = None
    mensajes: list = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


@pytest.fixture(scope="module")
def cliente(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_emision") / "emision.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-emision"

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
    establecimiento.puntos_emision = [
        PuntoEmision(codigo="001", nombre="Caja", secuencial_factura=1)
    ]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)
    sesion.commit()
    sesion.close()

    return iniciar_sesion(TestClient(aplicacion))


@pytest.fixture(scope="module")
def receptor_id(cliente):
    respuesta = cliente.post(
        "/api/receptores",
        json={
            "tipo_identificacion": "RUC",
            "identificacion": "0992339411001",
            "razon_social": "PLASTICOS DEL LITORAL PLASTLIT S.A.",
            "direccion": "Km 14.5 via Daule",
        },
    )
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


def _crear_factura(cliente, receptor_id):
    return cliente.post(
        "/api/comprobantes",
        json={
            "tipo": "Factura",
            "receptor_id": receptor_id,
            "establecimiento": "001",
            "punto_emision": "001",
            "detalles": [
                {
                    "codigo_principal": "PROD-001",
                    "descripcion": "Laptop",
                    "cantidad": "1",
                    "precio_unitario": "1200.00",
                    "codigo_iva": "4",
                }
            ],
        },
    ).json()


def _subir_certificado(cliente, tmp_path, contrasena="pruebas123", dias_validez=730):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    ruta = tmp_path / "cert.p12"
    generar(ruta, contrasena)

    with open(ruta, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("cert.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": contrasena},
        )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


# --------------------------------------------------------------------------
# Precondiciones
# --------------------------------------------------------------------------


def test_sin_certificado_no_se_emite(cliente, receptor_id):
    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.status_code == 422
    assert "certificado" in respuesta.json()["detail"].lower()


def test_certificado_expirado_no_emite(cliente, receptor_id, tmp_path, monkeypatch):
    _subir_certificado(cliente, tmp_path)

    from app.base_datos import SesionLocal
    from app.modelos_db import FirmaElectronica
    from sqlalchemy import select

    sesion = SesionLocal()
    firma = sesion.scalar(select(FirmaElectronica).where(FirmaElectronica.activa.is_(True)))
    firma.valida_hasta = date.today() - timedelta(days=1)
    sesion.commit()
    sesion.close()

    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.status_code == 422
    assert "expiró" in respuesta.json()["detail"]

    # Se restaura para el resto de las pruebas.
    sesion = SesionLocal()
    firma = sesion.scalar(select(FirmaElectronica).where(FirmaElectronica.activa.is_(True)))
    firma.valida_hasta = date.today() + timedelta(days=365)
    sesion.commit()
    sesion.close()


def test_cotizacion_no_se_transmite(cliente, receptor_id):
    cotizacion = cliente.post(
        "/api/comprobantes",
        json={
            "tipo": "Cotización",
            "receptor_id": receptor_id,
            "establecimiento": "001",
            "punto_emision": "001",
            "detalles": [
                {
                    "codigo_principal": "X",
                    "descripcion": "Item",
                    "cantidad": "1",
                    "precio_unitario": "10",
                }
            ],
        },
    ).json()

    respuesta = cliente.post(f"/api/comprobantes/{cotizacion['id']}/emitir")
    assert respuesta.status_code == 422
    assert "no se transmite" in respuesta.json()["detail"]


# --------------------------------------------------------------------------
# Emisión con el SRI simulado
# --------------------------------------------------------------------------


def test_emision_autorizada(cliente, receptor_id, monkeypatch):
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()

    assert datos["estado_recepcion"] == "RECIBIDA"
    assert datos["estado_autorizacion"] == "AUTORIZADO"
    assert datos["comprobante"]["estado_sri"] == "Autorizado"
    assert datos["comprobante"]["numero_autorizacion"] == "1234567890"
    # La clave de acceso se guarda: es con lo que se reconsulta después.
    assert len(datos["comprobante"]["clave_acceso"]) == 49


def test_el_xml_firmado_queda_guardado(cliente, receptor_id, monkeypatch):
    import app.servicios.emision as emision
    from app.base_datos import SesionLocal
    from app.modelos_db import Comprobante

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    factura = _crear_factura(cliente, receptor_id)
    cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    sesion = SesionLocal()
    guardado = sesion.get(Comprobante, factura["id"]).xml_firmado
    sesion.close()

    assert "<factura" in guardado
    assert "ds:Signature" in guardado


def test_no_se_reenvia_un_autorizado(cliente, receptor_id, monkeypatch):
    """Reenviarlo daría CLAVE ACCESO REGISTRADA y perdería la autorización."""
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    factura = _crear_factura(cliente, receptor_id)
    cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    segunda = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")
    assert segunda.status_code == 422
    assert "ya está autorizado" in segunda.json()["detail"]


def test_devuelto_guarda_los_mensajes(cliente, receptor_id, monkeypatch):
    """Cuando el SRI devuelve, el motivo es lo único que permite corregir."""
    import app.servicios.emision as emision

    mensajes = [
        {
            "identificador": "45",
            "mensaje": "ERROR EN DIÁLOGO CON BASE DE DATOS",
            "informacion_adicional": "Revise el RUC del emisor",
            "tipo": "ERROR",
        }
    ]
    monkeypatch.setattr(
        emision,
        "transmitir_al_sri",
        lambda *_: (RecepcionFalsa(estado="DEVUELTA", mensajes=mensajes), None),
    )

    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["comprobante"]["estado_sri"] == "Devuelto"
    assert datos["mensajes"][0]["identificador"] == "45"


def test_devuelto_se_puede_reintentar(cliente, receptor_id, monkeypatch):
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(estado="DEVUELTA"), None)
    )
    factura = _crear_factura(cliente, receptor_id)
    cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )
    reintento = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert reintento.status_code == 200
    assert reintento.json()["comprobante"]["estado_sri"] == "Autorizado"


def test_la_clave_de_acceso_es_estable_entre_reintentos(cliente, receptor_id, monkeypatch):
    """
    Un reintento debe consultar la misma clave; si cambiara, se preguntaría por
    un comprobante que el SRI nunca recibió.
    """
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(estado="DEVUELTA"), None)
    )

    factura = _crear_factura(cliente, receptor_id)
    primera = cliente.post(f"/api/comprobantes/{factura['id']}/emitir").json()
    segunda = cliente.post(f"/api/comprobantes/{factura['id']}/emitir").json()

    assert primera["comprobante"]["clave_acceso"] == segunda["comprobante"]["clave_acceso"]


def test_fallo_de_red_deja_el_comprobante_firmado(cliente, receptor_id, monkeypatch):
    """El XML firmado no se pierde: el reintento no vuelve a firmar."""
    import app.servicios.emision as emision
    from app.base_datos import SesionLocal
    from app.modelos_db import Comprobante

    def explotar(*_):
        raise ConnectionError("timeout")

    monkeypatch.setattr(emision, "transmitir_al_sri", explotar)

    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.status_code == 422
    assert "no se pudo contactar" in respuesta.json()["detail"].lower()

    sesion = SesionLocal()
    comprobante = sesion.get(Comprobante, factura["id"])
    assert comprobante.estado_sri == "Error"
    assert comprobante.xml_firmado is not None
    assert comprobante.clave_acceso is not None
    sesion.close()


def test_pendiente_cuando_el_sri_aun_procesa(cliente, receptor_id, monkeypatch):
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision,
        "transmitir_al_sri",
        lambda *_: (RecepcionFalsa(), AutorizacionFalsa(estado="EN PROCESO", numero_autorizacion=None)),
    )

    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    assert respuesta.json()["comprobante"]["estado_sri"] == "Pendiente"


# --------------------------------------------------------------------------
# Reconsulta
# --------------------------------------------------------------------------


def test_consultar_sin_transmitir_falla(cliente, receptor_id):
    factura = _crear_factura(cliente, receptor_id)
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/consultar")

    assert respuesta.status_code == 422
    assert "aún no se ha transmitido" in respuesta.json()["detail"]


def test_consultar_autoriza_un_pendiente(cliente, receptor_id, monkeypatch):
    """La autorización no es síncrona: puede llegar minutos después."""
    import app.servicios.emision as emision
    import app.sri.servicios as servicios_sri

    monkeypatch.setattr(
        emision,
        "transmitir_al_sri",
        lambda *_: (RecepcionFalsa(), AutorizacionFalsa(estado="EN PROCESO", numero_autorizacion=None)),
    )
    factura = _crear_factura(cliente, receptor_id)
    cliente.post(f"/api/comprobantes/{factura['id']}/emitir")

    monkeypatch.setattr(servicios_sri, "consultar_autorizacion", lambda *_: AutorizacionFalsa())
    respuesta = cliente.post(f"/api/comprobantes/{factura['id']}/consultar")

    assert respuesta.status_code == 200
    assert respuesta.json()["comprobante"]["estado_sri"] == "Autorizado"
    assert respuesta.json()["comprobante"]["numero_autorizacion"] == "1234567890"


# --------------------------------------------------------------------------
# Establecimientos y puntos de emisión
# --------------------------------------------------------------------------


def test_actualizar_establecimiento(cliente):
    establecimiento = cliente.get("/api/configuracion/establecimientos").json()[0]

    respuesta = cliente.put(
        f"/api/configuracion/establecimientos/{establecimiento['id']}",
        json={
            "codigo": "001",
            "nombre": "Matriz Renombrada",
            "direccion": "Nueva dirección 123",
            "puntos_emision": [
                {"codigo": "001", "nombre": "Caja principal", "secuencial_factura": 500},
                {"codigo": "002", "nombre": "Caja nueva", "secuencial_factura": 1},
            ],
        },
    )

    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    assert datos["nombre"] == "Matriz Renombrada"
    assert len(datos["puntos_emision"]) == 2


def test_el_secuencial_no_puede_retroceder(cliente):
    """Retrocederlo produciría números repetidos y el SRI los rechazaría."""
    establecimiento = cliente.get("/api/configuracion/establecimientos").json()[0]

    respuesta = cliente.put(
        f"/api/configuracion/establecimientos/{establecimiento['id']}",
        json={
            "codigo": "001",
            "nombre": "Matriz",
            "direccion": "Av. Amazonas",
            "puntos_emision": [
                {"codigo": "001", "nombre": "Caja", "secuencial_factura": 10},
            ],
        },
    )

    assert respuesta.status_code == 422
    assert "retroceder" in respuesta.json()["detail"]


def test_quitar_un_punto_de_emision(cliente):
    establecimiento = cliente.get("/api/configuracion/establecimientos").json()[0]

    respuesta = cliente.put(
        f"/api/configuracion/establecimientos/{establecimiento['id']}",
        json={
            "codigo": "001",
            "nombre": "Matriz",
            "direccion": "Av. Amazonas",
            "puntos_emision": [
                {"codigo": "001", "nombre": "Caja principal", "secuencial_factura": 500},
            ],
        },
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()["puntos_emision"]) == 1
