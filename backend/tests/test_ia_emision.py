"""
Pruebas del tramo final del asistente: confirmar por WhatsApp emite de verdad.

Hasta la tanda 10 el orquestador solo dejaba la factura en borrador. Lo que se
verifica aquí es que ahora transmite, que numera por el mismo camino que la
pantalla de facturación —dos contadores distintos producirían números
repetidos— y que un fallo del SRI no pierde la factura.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pytest

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
    numero_autorizacion: str | None = "1122334455"
    fecha_autorizacion: str | None = "2026-08-08T13:00:00-05:00"
    comprobante: str | None = None
    mensajes: list = field(default_factory=list)

    @property
    def autorizada(self) -> bool:
        return self.estado == "AUTORIZADO"


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    base = tmp_path_factory.mktemp("bd_ia") / "ia.db"
    os.environ["URL_BASE_DATOS"] = f"sqlite:///{base}"
    os.environ["CLAVE_SECRETA"] = "clave-de-prueba-ia"

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    from app.main import aplicacion  # noqa: F401  (registra los modelos)
    from app.modelos_db import Empresa, Establecimiento, PuntoEmision, Receptor

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
        PuntoEmision(codigo="001", nombre="Caja", secuencial_factura=50)
    ]
    empresa.establecimientos = [establecimiento]
    sesion.add(empresa)

    receptor = Receptor(
        tipo_identificacion="RUC",
        identificacion="0992339411001",
        razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
        direccion="Km 14.5 via Daule",
    )
    sesion.add(receptor)
    sesion.commit()

    receptor_id = receptor.id
    sesion.close()

    # Certificado de pruebas, igual que en la emisión desde la pantalla.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from generar_certificado_pruebas import generar

    from fastapi.testclient import TestClient

    cliente = iniciar_sesion(TestClient(aplicacion))
    ruta = tmp_path_factory.mktemp("cert_ia") / "cert.p12"
    generar(ruta, "pruebas123")
    with open(ruta, "rb") as archivo:
        respuesta = cliente.post(
            "/api/configuracion/firma",
            files={"archivo": ("cert.p12", archivo, "application/x-pkcs12")},
            data={"contrasena": "pruebas123"},
        )
    assert respuesta.status_code == 201, respuesta.text

    return {"receptor_id": receptor_id, "SesionLocal": SesionLocal}


def _borrador(receptor_id):
    return {
        "cliente_id": receptor_id,
        "cliente_nombre": "PLASTICOS DEL LITORAL PLASTLIT S.A.",
        "cliente_identificacion": "0992339411001",
        "detalles": [
            {
                "descripcion": "Laptop",
                "cantidad": Decimal("1"),
                "precio_unitario": Decimal("1000.00"),
                "codigo_iva": "4",
            }
        ],
        "total_sin_impuestos": Decimal("1000.00"),
        "total_descuento": Decimal("0"),
        "total_iva": Decimal("150.00"),
        "importe_total": Decimal("1150.00"),
    }


def test_confirmar_emite_al_sri(entorno, monkeypatch):
    import app.ia.orquestador as orquestador
    import app.servicios.emision as emision

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    sesion = entorno["SesionLocal"]()
    mensaje = orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))
    sesion.close()

    assert "Autorizada por el SRI" in mensaje
    assert "1122334455" in mensaje


def test_el_iva_de_la_linea_queda_calculado(entorno, monkeypatch):
    """
    Antes se guardaba `total = base` sin IVA, así que la línea no cuadraba con
    el total que el propio asistente le había mostrado al usuario.
    """
    import app.ia.orquestador as orquestador
    import app.servicios.emision as emision
    from app.modelos_db import Comprobante
    from sqlalchemy import select

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    sesion = entorno["SesionLocal"]()
    orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))

    comprobante = sesion.scalars(
        select(Comprobante).order_by(Comprobante.id.desc()).limit(1)
    ).first()
    linea = comprobante.detalles[0]

    assert linea.base_imponible == Decimal("1000.00")
    assert linea.valor_iva == Decimal("150.00")
    assert linea.total == Decimal("1150.00")
    sesion.close()


def test_usa_el_mismo_contador_que_la_pantalla(entorno, monkeypatch):
    """
    Un contador propio del asistente daría números repetidos con los de la
    pantalla y el SRI los rechazaría.
    """
    import app.ia.orquestador as orquestador
    import app.servicios.emision as emision
    from app.modelos_db import Comprobante
    from sqlalchemy import select

    monkeypatch.setattr(
        emision, "transmitir_al_sri", lambda *_: (RecepcionFalsa(), AutorizacionFalsa())
    )

    sesion = entorno["SesionLocal"]()
    orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))
    orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))

    numeros = sesion.scalars(
        select(Comprobante.secuencial).order_by(Comprobante.id.desc()).limit(2)
    ).all()
    sesion.close()

    assert numeros[0] == numeros[1] + 1
    # El contador arrancó en el `secuencial_factura` configurado, no en 1.
    assert numeros[1] >= 50


def test_un_rechazo_del_sri_se_explica_y_conserva_la_factura(entorno, monkeypatch):
    import app.ia.orquestador as orquestador
    import app.servicios.emision as emision
    from app.modelos_db import Comprobante
    from sqlalchemy import select

    mensajes = [{"identificador": "39", "mensaje": "FIRMA INVALIDA", "tipo": "ERROR"}]
    monkeypatch.setattr(
        emision,
        "transmitir_al_sri",
        lambda *_: (RecepcionFalsa(estado="DEVUELTA", mensajes=mensajes), None),
    )

    sesion = entorno["SesionLocal"]()
    mensaje = orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))

    assert "FIRMA INVALIDA" in mensaje
    assert "quedó guardada" in mensaje

    comprobante = sesion.scalars(
        select(Comprobante).order_by(Comprobante.id.desc()).limit(1)
    ).first()
    assert comprobante.estado_sri == "Devuelto"
    sesion.close()


def test_un_fallo_de_red_no_pierde_la_factura(entorno, monkeypatch):
    import app.ia.orquestador as orquestador
    import app.servicios.emision as emision
    from app.modelos_db import Comprobante
    from sqlalchemy import select

    def explotar(*_):
        raise ConnectionError("timeout")

    monkeypatch.setattr(emision, "transmitir_al_sri", explotar)

    sesion = entorno["SesionLocal"]()
    mensaje = orquestador._emitir(sesion, _borrador(entorno["receptor_id"]))

    assert "no se pudo enviar al SRI" in mensaje
    assert "reintentarlo" in mensaje

    comprobante = sesion.scalars(
        select(Comprobante).order_by(Comprobante.id.desc()).limit(1)
    ).first()
    assert comprobante.estado_sri == "Error"
    # Firmada y guardada: el reintento no vuelve a firmar.
    assert comprobante.xml_firmado is not None
    sesion.close()


def test_sin_empresa_no_se_emite(tmp_path_factory, monkeypatch):
    base = tmp_path_factory.mktemp("bd_ia_vacia") / "vacia.db"
    monkeypatch.setenv("URL_BASE_DATOS", f"sqlite:///{base}")
    monkeypatch.setenv("CLAVE_SECRETA", "clave-de-prueba-ia-vacia")

    for modulo in list(sys.modules):
        if modulo.startswith("app"):
            del sys.modules[modulo]

    from app.base_datos import SesionLocal, crear_tablas
    import app.ia.orquestador as orquestador

    crear_tablas()

    sesion = SesionLocal()
    mensaje = orquestador._emitir(sesion, _borrador(1))
    sesion.close()

    assert "No hay empresa configurada" in mensaje
