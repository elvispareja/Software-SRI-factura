# Avance Fase 3-A — Infra, seguridad y edición

> **Taste:** fase 3-A entrega infra + edición por agente dedicado. Cada tarea queda en este .md (contrato del plan § Entregables).

## 1) Mapeo edición (frontend)

| Pantalla | Ruta | Modo | Precarga | Guardado | Validación especial |
|---|---|---|---|---|---|
| Receptores | `/receptores/nuevo` | crear | — | `POST /receptores` | `validarIdentificacion` + 422 del backend |
| Receptores | `/receptores/:id/editar` | editar | `GET /receptores/:id` con `AbortController` | `PUT /receptores/:id` | 409 si identificación colisiona con otro receptor |
| Artículos | `/articulos/nuevo` | crear | — | `POST /articulos` | stock/puntoReorden ≥ 0 |
| Artículos | `/articulos/:id/editar` | editar | `GET /articulos/:id` | `PUT /articulos/:id` | `codigo` bloqueado (disabled + ayuda "El código no se cambia tras crear"), 409 si código colisiona |

- **App.jsx:** `receptores/:id/editar → ReceptoresForm` y `articulos/:id/editar → ArticulosForm`. React Router 7 ordena por ranking, así que no colisiona con `comprobantes/:id` (segmentos estáticos `nuevo`/`editar` pesan más que `:id`).
- **ReceptoresForm.jsx:** `useParams().id` decide el modo; `identidadBloqueada` inicia `true` en crear y `false` en editar con banner "Corregir identidad" y detalle de 409. `consultarSri` mantiene su comportamiento actual (simulado) y no oculta errores.
- **ArticulosForm.jsx:** idem; `codigo` solo es editable al crear. `stockActual`, `stockMinimo`, `puntoReorden`, `stockMaximo` validados ≥ 0 en cliente; el backend valida vía Pydantic y retorna 422 si no.
- **Adaptadores:** `receptorDesdeApi`/`receptorHaciaApi` y `articuloDesdeApi`/`articuloHaciaApi` ampliados a mapeo completo (incluye `telefono1/2`, `correo2`, `descuento`, `creditoMaximo`, `provincia/canton`, `stockMinimo/puntoReorden/stockMaximo`, `codigoIce`, etc.).

## 2) Endpoints PUT usados

- `GET /receptores/{id}` y `PUT /receptores/{id}` — `ReceptorEntrada` con validador SRI; 409 si `identificacion` ya existe en otro registro.
- `GET /articulos/{id}` y `PUT /articulos/{id}` — `ArticuloEntrada` con `codigo_iva` validado; 409 si `codigo` ya existe en otro registro.
- Reutilizan `routers/catalogos.py` sin migrar `modelos_db.py` (plan § Qué NO se hace).

## 3) Validación 409

- Backend: `actualizar_receptor` y `actualizar_articulo` buscan duplicado con `id != receptor_id/articulo_id` y lanzan `HTTPException(409, ...)`.
- Frontend: ambos formularios capturan `ErrorApi` con `estado === 409` y lo muestran como `ayudaError` (banner rojo), igual que 422. Navegación a `/receptores` o `/articulos` solo al éxito. `consultarSri` no traga el 409.

## 4) Listados — menú Editar / Desactivar

- **ReceptoresList.jsx** y **ArticulosList.jsx:** el `MoreVertical` ya existente abre un menú local (`menuOpenId`, cierra al navegar o al hacer click fuera con overlay `fixed inset-0`).
  - *Editar* → `navigate('/receptores/:id/editar' | '/articulos/:id/editar')`, cierra el menú.
  - *Desactivar* → `DELETE /receptores/:id` o `/articulos/:id` (soft: pone `estado = Inactivo`) + `recurso.recargar()`. En modo demo el botón está deshabilitado. No se rompe `TablaCWO` ni sus columnas/paginación.

## 5) Seguridad prod

- `backend/app/seguridad.py`: si `ES_CLAVE_DE_DESARROLLO` y `AMBIENTE == "2"`, `raise RuntimeError("CLAVE_SECRETA obligatoria en producción")` al importar **y** vía `validar_seguridad_produccion()` para el ciclo de vida. No se cambia el valor de `CLAVE_SECRETA`.
- `backend/app/main.py`: `ORIGENES_PERMITIDOS` ahora filtra vacíos (`[o.strip() for ... if o.strip()]`) y el `ciclo_de_vida` llama a `validar_seguridad_produccion()` y hace warning si `ORIGENES_PERMITIDOS` queda vacío. No cambia comportamiento en desarrollo.

## 6) Postgres + docker-compose

- `docker-compose.yml` (raíz) con servicios `db` (`postgres:16-alpine`, `POSTGRES_USER/DB/PASSWORD`, healthcheck, volumen `db_data`), `api` (build `backend`, `URL_BASE_DATOS=postgresql+psycopg://...`, `CLAVE_SECRETA`, `ORIGENES_PERMITIDOS`, `WHATSAPP_*`), `web` (build `frontend` con `VITE_URL_API`).
- `backend/requirements.txt`: añadido `psycopg[binary]==3.1.13` compatible con SQLAlchemy 2.0 (sin SQL nativo; `base_datos.py` ya abstrae el motor).
- `backend/Dockerfile` y `frontend/Dockerfile` (multi-stage `node:20 + nginx` con fallback SPA).
- `.env.example` con todas las vars del README + `URL_BASE_DATOS` pg + `POSTGRES_*` + `VITE_URL_API` + placeholders Fase 4.
- `.gitignore` raíz verificado: ignora `node_modules`, `.venv`, `dist`, `facturacion.db`, `salida/`, `certificados/*.p12`; añadida excepción `!.env.example`.

## 7) Drive → Git

- El repo ya es git en la raíz. Esta fase no mueve el repo fuera de Drive por decisión del plan (requiere coordinación), pero deja `.gitignore` efectivos (`/.gitignore` raíz + `backend/.gitignore` + `frontend/.gitignore`) para que `git status` no pise `node_modules/.venv/dist/salida/certificados`.

## 8) Cómo probar

```bash
# Backend local SQLite (dev)
cd backend && .venv/Scripts/python -m uvicorn app.main:aplicacion --reload

# Postgres vía Docker
copy .env.example .env        # completa CLAVE_SECRETA si AMBIENTE=2
docker compose up --build
# GET http://localhost:8000/api/salud → {"estado":"ok"}

# Edición
# 1) /receptores/nuevo → crear receptor RUC válido → debe ir a /receptores
# 2) /receptores/:id/editar → precarga, cambia razón social → Actualizar → vuelve a /receptores
# 3) En editar, cambia identificación a una ya usada por otro receptor → banner 409
# 4) /articulos/:id/editar → código deshabilitado + "El código no se cambia tras crear"; cambia nombre/precio → Actualizar
# 5) Listados: MoreVertical → Editar navega, Desactivar hace soft delete y recarga

# Lint/build
cd frontend && npm run lint && npm run build
```

## 9) Archivos tocados (fase 3-A)

- `backend/app/seguridad.py`, `backend/app/main.py`, `backend/app/routers/catalogos.py`, `backend/requirements.txt`, `backend/Dockerfile`
- `frontend/src/App.jsx`, `frontend/src/api/adaptadores.js`, `frontend/src/pages/Receptores/ReceptoresForm.jsx`, `frontend/src/pages/Receptores/ReceptoresList.jsx`, `frontend/src/pages/Articulos/ArticulosForm.jsx`, `frontend/src/pages/Articulos/ArticulosList.jsx`, `frontend/Dockerfile`, `frontend/.gitignore`
- `docker-compose.yml`, `.env.example`, `.gitignore`, `docs/avance_fase3_infra_edicion.md`, `docs/avance_fase3_resumen.md`, `README.md`

## 10) Fuera de alcance (no tocado, queda Fase 4)

- SMTP (`POST /comprobantes/:id/enviar`), certificado `.p12` acreditado, tablas contables (`cuota/recibo/anticipo/asiento`), `frontend/src/pages/Comprobantes/ComprobanteTraza.jsx` (lo hace 3-B), WhatsApp audio/imagen (3-B).
