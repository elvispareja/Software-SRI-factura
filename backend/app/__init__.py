"""
Carga el `.env` antes que cualquier otro módulo del paquete.

Tiene que estar aquí y no en `main.py`: `base_datos` y `seguridad` leen
`os.environ` en cuanto se los importa, así que para cuando `main` corre su
primera línea ya es tarde. `__init__.py` se ejecuta antes que ellos sin importar
por dónde se entre —uvicorn, los scripts de `scripts/` o las pruebas—.

`override=False` a propósito: una variable que ya esté en el entorno gana sobre
el archivo. De eso dependen las pruebas, que fijan `URL_BASE_DATOS` a un SQLite
temporal antes de importar, y docker-compose, que inyecta la suya apuntando al
contenedor `db` y no debe verse pisada por un `.env` que se haya colado en la
imagen.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# `backend/app/__init__.py`: parents[1] es `backend/`, y su padre la raíz del
# repositorio. Se miran los dos sitios, primero el más específico —con
# `override=False`, quien carga primero manda—. La raíz es donde vive el `.env`
# que también lee docker-compose; los dos están en el .gitignore.
_BACKEND = Path(__file__).resolve().parents[1]

for _ruta in (_BACKEND / ".env", _BACKEND.parent / ".env"):
    if _ruta.is_file():
        load_dotenv(_ruta, override=False)
