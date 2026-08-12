"""
Agrega a `gastos` el código de IVA y la autorización del proveedor.

    python scripts/migrar_gastos_iva.py

`crear_tablas()` solo crea tablas que no existen; no altera las que ya están,
así que una base anterior a esta tanda se queda sin estas dos columnas y el
API falla al leerla. Es idempotente: si ya están, no hace nada.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.base_datos import motor  # noqa: E402

COLUMNAS = {
    "autorizacion_proveedor": "VARCHAR(60)",
    "codigo_iva": "VARCHAR(2) DEFAULT '4'",
}


def migrar() -> None:
    existentes = {c["name"] for c in inspect(motor).get_columns("gastos")}
    faltantes = {n: t for n, t in COLUMNAS.items() if n not in existentes}

    if not faltantes:
        print("La base ya está al día. No se hace nada.")
        return

    with motor.begin() as conexion:
        for nombre, tipo in faltantes.items():
            conexion.execute(text(f"ALTER TABLE gastos ADD COLUMN {nombre} {tipo}"))
            print(f"  + gastos.{nombre}")

    print(f"Listo: {len(faltantes)} columna(s) agregada(s).")


if __name__ == "__main__":
    migrar()
