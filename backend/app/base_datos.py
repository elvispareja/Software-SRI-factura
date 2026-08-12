"""
Conexión a la base de datos.

Arranca en SQLite para no bloquear el desarrollo; el cambio a PostgreSQL es
solo la variable de entorno `URL_BASE_DATOS`, porque todo el acceso pasa por
SQLAlchemy y no hay SQL específico de motor.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

URL_BASE_DATOS = os.getenv("URL_BASE_DATOS", "sqlite:///./facturacion.db")

# check_same_thread solo aplica a SQLite: FastAPI atiende peticiones en hilos
# distintos y sin esto SQLite se queja.
argumentos_conexion = {"check_same_thread": False} if URL_BASE_DATOS.startswith("sqlite") else {}

motor = create_engine(URL_BASE_DATOS, connect_args=argumentos_conexion, future=True)
SesionLocal = sessionmaker(bind=motor, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def obtener_sesion() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: abre una sesión por petición y la cierra siempre."""
    sesion = SesionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


def crear_tablas() -> None:
    from . import modelos_db  # noqa: F401 - registra los modelos en el metadata

    Base.metadata.create_all(bind=motor)
