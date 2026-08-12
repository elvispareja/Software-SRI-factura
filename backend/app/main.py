"""
API del sistema de facturación electrónica SRI.

Arranque:
    uvicorn app.main:aplicacion --reload
    # documentación interactiva en http://localhost:8000/docs
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .base_datos import crear_tablas
from .routers import (
    anticipos,
    autenticacion,
    catalogos,
    comprobantes,
    configuracion,
    cuentas,
    egresos,
    guias,
    recurrentes,
    reportes,
    retenciones,
    whatsapp,
)
from .seguridad import ES_CLAVE_DE_DESARROLLO, usuario_actual, validar_seguridad_produccion

# Orígenes del frontend en desarrollo. En producción se pasa por variable de entorno.
_ORIGENES_CRUDO = os.getenv("ORIGENES_PERMITIDOS", "http://localhost:5173,http://127.0.0.1:5173")
ORIGENES_PERMITIDOS = [o.strip() for o in _ORIGENES_CRUDO.split(",") if o.strip()]


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    crear_tablas()

    # En producción, CLAVE_SECRETA es obligatoria: fallar rápido en vez de
    # arrancar con la de desarrollo.
    validar_seguridad_produccion()

    if not ORIGENES_PERMITIDOS:
        print(
            "\n  AVISO: ORIGENES_PERMITIDOS está vacío; no hay orígenes CORS permitidos.\n"
            "  Define ORIGENES_PERMITIDOS con la URL del frontend.\n"
        )

    # Aviso ruidoso a propósito: con la clave por defecto cualquiera que
    # conozca el código puede firmar tokens válidos.
    if ES_CLAVE_DE_DESARROLLO:
        print(
            "\n  AVISO: CLAVE_SECRETA no está definida; se usa la de desarrollo.\n"
            "  Define la variable de entorno CLAVE_SECRETA antes de exponer el API.\n"
        )

    yield


aplicacion = FastAPI(
    title="Facturación Electrónica SRI",
    description="API del sistema de facturación electrónica para Ecuador.",
    version="0.3.0",
    lifespan=ciclo_de_vida,
)

aplicacion.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES_PERMITIDOS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sin esto el navegador no deja leer el total de registros de los listados.
    expose_headers=["X-Total-Registros"],
)

# El cierre se declara aquí, en el include_router, y no endpoint por endpoint.
# La razón es que un endpoint nuevo hereda la protección por el hecho de vivir
# en su router: olvidarse de protegerlo deja de ser posible. Al revés —marcar
# cada ruta a mano— el descuido es cuestión de tiempo, y así fue como estos
# routers acabaron sirviendo la contabilidad entera sin pedir credenciales.
SESION_REQUERIDA = [Depends(usuario_actual)]

# Abierto a propósito: registro, login y cierre de sesión son justamente los
# que no pueden exigir una sesión previa.
aplicacion.include_router(autenticacion.router, prefix="/api")

# El webhook de WhatsApp tampoco lleva sesión: Meta no la tiene. Se autentica
# con la firma HMAC-SHA256 de la cabecera X-Hub-Signature-256, que el propio
# router verifica antes de procesar nada.
aplicacion.include_router(whatsapp.router, prefix="/api")

# Todo lo demás exige sesión.
aplicacion.include_router(catalogos.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(comprobantes.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(configuracion.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(guias.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(anticipos.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(cuentas.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(egresos.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(recurrentes.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(reportes.router, prefix="/api", dependencies=SESION_REQUERIDA)
aplicacion.include_router(retenciones.router, prefix="/api", dependencies=SESION_REQUERIDA)


@aplicacion.get("/api/salud", tags=["sistema"])
def salud():
    return {"estado": "ok", "version": aplicacion.version}
