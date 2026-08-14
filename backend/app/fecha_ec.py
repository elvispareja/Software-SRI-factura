"""
Fecha y hora en la zona horaria de Ecuador (America/Guayaquil, UTC-5 fija).

El contenedor corre en UTC. Si una factura se fecha con `date.today()` del
proceso, una emisión después de las 19:00 hora de Ecuador cae en el día
siguiente en UTC: esa fecha entra en la clave de acceso y en `fechaEmision`, y
el SRI la rechaza por extemporánea además de mandar el IVA al periodo equivocado
del formulario 104. Por eso la fecha de emisión SIEMPRE se toma de aquí.

Requiere la base de datos de zonas horarias. En la imagen `python:3.12-slim`
puede no venir incluida, así que `tzdata` está en requirements.txt.
"""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_EC = ZoneInfo("America/Guayaquil")


def ahora_ec() -> datetime:
    """Instante actual como datetime *aware* en hora de Ecuador."""
    return datetime.now(ZONA_EC)


def hoy_ec() -> date:
    """Fecha civil de hoy en Ecuador, para usar como fecha de emisión."""
    return ahora_ec().date()
