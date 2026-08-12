"""
Copia los datos de una base SQLite (la que usaba el proyecto antes de que
PostgreSQL fuera el único motor soportado) a la base PostgreSQL de destino.

    python scripts/migrar_sqlite_a_postgres.py [ruta/al/facturacion.db]

Usa `URL_BASE_DATOS` (definida en el entorno, igual que el resto del backend)
como destino y crea ahí las tablas que falten. Respeta el orden de
dependencias entre tablas (`Base.metadata.sorted_tables`) para que las
llaves foráneas no fallen, copia todas las columnas con su tipo real
(Decimal, datetime con zona horaria, booleanos, binarios) y al final
reajusta las secuencias de los `id` autoincrementales para que el próximo
insert en PostgreSQL no choque con un id ya copiado.

Se niega a correr si el destino ya tiene datos, para no duplicar filas si
se ejecuta dos veces por error.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Integer, create_engine, select, text  # noqa: E402

from app.base_datos import Base, crear_tablas, motor  # noqa: E402


def migrar(ruta_sqlite: Path) -> None:
    if not ruta_sqlite.exists():
        raise SystemExit(f"No existe {ruta_sqlite}")

    from app import modelos_db  # noqa: F401 - registra los modelos en el metadata

    origen = create_engine(f"sqlite:///{ruta_sqlite}", future=True)

    crear_tablas()

    with motor.begin() as destino:
        for tabla in Base.metadata.sorted_tables:
            (n_existentes,) = destino.execute(
                text(f'SELECT COUNT(*) FROM "{tabla.name}"')
            ).one()
            if n_existentes:
                raise SystemExit(
                    f"'{tabla.name}' ya tiene {n_existentes} fila(s) en destino. "
                    "Aborto para no duplicar datos; vacía la base de destino primero "
                    "si de verdad quieres repetir la migración."
                )

        with origen.connect() as conexion_origen:
            for tabla in Base.metadata.sorted_tables:
                filas = conexion_origen.execute(select(tabla)).mappings().all()
                if not filas:
                    print(f"  {tabla.name}: 0 filas")
                    continue
                destino.execute(tabla.insert(), [dict(fila) for fila in filas])
                print(f"  {tabla.name}: {len(filas)} fila(s)")

        for tabla in Base.metadata.sorted_tables:
            columnas_pk = list(tabla.primary_key.columns)
            if len(columnas_pk) != 1 or not isinstance(columnas_pk[0].type, Integer):
                continue
            columna = columnas_pk[0].name
            destino.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{tabla.name}', '{columna}'), "
                    f"COALESCE((SELECT MAX({columna}) FROM {tabla.name}), 1), "
                    f"(SELECT MAX({columna}) FROM {tabla.name}) IS NOT NULL)"
                )
            )

    print("Migración completa.")


if __name__ == "__main__":
    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "facturacion.db"
    migrar(ruta)
