"""
Conexión a la base de datos.

Solo PostgreSQL: `URL_BASE_DATOS` es obligatoria, no hay valor por defecto
que oculte una configuración faltante en producción.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

URL_BASE_DATOS = os.environ["URL_BASE_DATOS"]

# check_same_thread solo aplica si algo (p.ej. las pruebas) usa una URL sqlite;
# en producción URL_BASE_DATOS siempre es PostgreSQL y esto no tiene efecto.
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
