"""
Carga datos de demostración: empresa, establecimientos, receptores y artículos.

    python scripts/sembrar_datos.py

Es idempotente: si ya hay una empresa, no duplica nada.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.base_datos import SesionLocal, crear_tablas  # noqa: E402
from app.modelos_db import (  # noqa: E402
    Articulo,
    Empresa,
    Establecimiento,
    PuntoEmision,
    Receptor,
)

RECEPTORES = [
    ("RUC", "1790016919001", "CORPORACIÓN FAVORITA C.A.", "SUPERMAXI", "Jurídica", "Cliente", "Av. General Enríquez S/N, Sangolquí"),
    ("Cédula", "0912345675", "JUAN PÉREZ", "TIENDA JUANITO", "Natural", "Cliente", "Av. 9 de Octubre 1234, Guayaquil"),
    ("Consumidor Final", "9999999999999", "CONSUMIDOR FINAL", "", "Natural", "Cliente", "S/N"),
    ("RUC", "0992339411001", "PLÁSTICOS DEL LITORAL PLASTLIT S.A.", "PLASTLIT", "Jurídica", "Proveedor", "Km 14.5 vía Daule, Guayaquil"),
    ("RUC", "1791287541001", "TRANSPORTES ANDINOS CÍA. LTDA.", "TRANSANDINOS", "Jurídica", "Transportista", "Av. Maldonado S12-45, Quito"),
    ("Cédula", "1712345675", "MARÍA ANDRADE", "", "Natural", "Cliente", "Av. Shyris N34-120, Quito"),
    ("RUC", "0190001946001", "IMPORTADORA AUSTRAL S.A.", "AUSTRAL", "Jurídica", "Proveedor", "Av. España 4-52, Cuenca"),
    ("Cédula", "0604567891", "CARLOS VILLACÍS", "FERRETERÍA EL TORNILLO", "Natural", "Cliente", "Av. Daniel León Borja 22-10, Riobamba"),
]

ARTICULOS = [
    ("PROD-001", "Laptop Dell XPS 13", "Producto", "Tecnología", "Unidad", "4", "950.00", "1200.00", "15"),
    ("SERV-001", "Mantenimiento Preventivo", "Servicio", "Soporte", "Servicio", "4", "20.00", "45.00", None),
    ("PROD-002", "Mouse Inalámbrico Logitech", "Producto", "Tecnología", "Unidad", "4", "16.00", "25.50", "40"),
    ("PROD-003", "Pan común - funda 500g", "Producto", "Alimentos", "Unidad", "0", "1.20", "1.85", "120"),
    ("SERV-002", "Consultoría contable mensual", "Servicio", "Profesional", "Servicio", "4", "90.00", "180.00", None),
    ("PROD-004", "Teclado mecánico retroiluminado", "Producto", "Tecnología", "Unidad", "4", "42.00", "62.90", "18"),
    ("PROD-005", 'Monitor LED 24"', "Producto", "Tecnología", "Unidad", "4", "140.00", "189.00", "7"),
    ("PROD-006", "Resma de papel bond A4", "Producto", "Oficina", "Unidad", "4", "3.40", "4.75", "240"),
]


def sembrar() -> None:
    crear_tablas()
    sesion = SesionLocal()

    try:
        if sesion.scalars(select(Empresa).limit(1)).first():
            print("Ya hay datos sembrados. No se hace nada.")
            return

        empresa = Empresa(
            ruc="1790016919001",
            razon_social="MI EMPRESA DEMO S.A.",
            nombre_comercial="DEMO",
            direccion_matriz="Av. Amazonas N21-147 y Roca, Quito",
            provincia="Pichincha",
            canton="Quito",
            telefono="022345678",
            correo="facturacion@miempresa.ec",
            regimen="Régimen General",
            obligado_contabilidad=True,
            ambiente="1",
        )

        matriz = Establecimiento(
            codigo="001", nombre="Matriz", direccion="Av. Amazonas N21-147 y Roca, Quito"
        )
        matriz.puntos_emision = [
            PuntoEmision(codigo="001", nombre="Caja principal", secuencial_factura=135),
            PuntoEmision(codigo="002", nombre="Ventas en línea", secuencial_factura=42),
        ]

        sucursal = Establecimiento(
            codigo="002", nombre="Sucursal Norte", direccion="Av. Eloy Alfaro N45-120, Quito"
        )
        sucursal.puntos_emision = [
            PuntoEmision(codigo="001", nombre="Caja sucursal", secuencial_factura=8)
        ]

        empresa.establecimientos = [matriz, sucursal]
        sesion.add(empresa)

        for tipo, identificacion, razon, comercial, persona, rol, direccion in RECEPTORES:
            sesion.add(
                Receptor(
                    tipo_identificacion=tipo,
                    identificacion=identificacion,
                    razon_social=razon,
                    nombre_comercial=comercial or None,
                    tipo_persona=persona,
                    rol=rol,
                    direccion=direccion,
                    correo=f"{identificacion}@ejemplo.ec",
                )
            )

        for codigo, nombre, tipo, categoria, unidad, iva, costo, precio, stock in ARTICULOS:
            sesion.add(
                Articulo(
                    codigo=codigo,
                    nombre=nombre,
                    tipo=tipo,
                    categoria=categoria,
                    unidad=unidad,
                    codigo_iva=iva,
                    costo=Decimal(costo),
                    precio=Decimal(precio),
                    stock=Decimal(stock) if stock else None,
                    stock_minimo=Decimal("5"),
                    punto_reorden=Decimal("10"),
                    stock_maximo=Decimal("200"),
                )
            )

        sesion.commit()
        print("Datos sembrados:")
        print(f"  1 empresa, 2 establecimientos, 3 puntos de emisión")
        print(f"  {len(RECEPTORES)} receptores")
        print(f"  {len(ARTICULOS)} artículos")
    finally:
        sesion.close()


if __name__ == "__main__":
    sembrar()
