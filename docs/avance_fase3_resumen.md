# Avance Fase 3 — Resumen (índice)

> Fase 3 deja el sistema desplegable en Postgres con edición en sitio y seguridad saneada, sin tocar SMTP ni certificado acreditado (Fase 4).

## Agentes y entregables

| Agente | Foco | Doc principal | Estado |
|---|---|---|---|
| **Fase 3-A — Infra, seguridad y edición** | Rutas `/receptores/:id/editar` + `/articulos/:id/editar`, PUT con 409, menú Editar/Desactivar, Postgres `psycopg` + `docker-compose.yml`, `CLAVE_SECRETA` obligatoria en prod | `docs/avance_fase3_infra_edicion.md` | ✅ Entregado |
| **Fase 3-B — Trazabilidad, WhatsApp multimodal y pulido** | `ComprobanteTraza` visor RIDE real + `routers/whatsapp.py` audio/imagen (STT/OCR) + Config banner `CLAVE_SECRETA`/vigencia | `docs/avance_fase3_trazabilidad_whatsapp.md` | ✅ Entregado |

## Fase 3-A — Detalle

- **Rutas y edición** — `App.jsx` con `receptores/:id/editar` y `articulos/:id/editar` (ranking React Router 7 no colisiona con `comprobantes/:id`).
- **ReceptoresForm** — modo crear/editar con `useParams().id`, precarga `GET /receptores/:id` con `AbortController`, `identidadBloqueada` desbloqueada en edición con banner "Corregir identidad", validación `validarIdentificacion`, `consultarSri` propaga 409, guardado `PUT` vs `POST` con manejo 409/422 y `navigate('/receptores')`.
- **ArticulosForm** — idem `GET/PUT /articulos/:id`, `codigo` disabled en edición ("El código no se cambia tras crear"), stock/puntoReorden ≥ 0, mapeo `articuloDesdeApi`/`articuloHaciaApi`.
- **Listados** — `MoreVertical` abre menú `Editar / Desactivar` (estado `menuOpenId`), `Editar → navigate`, `Desactivar → DELETE` soft + `recargar()`, respeta `TablaCWO` y modo demo.
- **Seguridad prod** — `seguridad.py` hace `raise RuntimeError` si `ES_CLAVE_DE_DESARROLLO` y `AMBIENTE=="2"` (al importar y en `ciclo_de_vida`); `main.py` valida `ORIGENES_PERMITIDOS` vacío con warning y filtra cadenas vacías.
- **Postgres/Docker** — `docker-compose.yml` (`db` postgres:16-alpine + `api` + `web`), `.env.example` con todas las vars + `URL_BASE_DATOS` pg, `psycopg[binary]==3.1.13`, `backend/Dockerfile` + `frontend/Dockerfile` multi-stage, `.gitignore` con `salida/` y `!.env.example`.

## Fase 3-B — Detalle

- **ComprobanteTraza** — visor 2-paneles `isTraza` (545-689) con `iframe urlRide(id)` + zoom 60-140% + acciones `emitir/consultar/xml/ride/anular` + `NC/ND` y 3 acordeones Pagos/NC/ND. Hook `GET /comprobantes/:id` con `AbortController` y `ESTADOS_EMITIBLES/CONSULTABLES`.
- **WhatsApp multimodal** — `routers/whatsapp.py` con `_descargar_media` Graph API + `_transcribir_audio` (openai Whisper / faster-whisper) + `_ocr_imagen` (anthropic Vision), fallback degradado si falta `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`, HMAC y `BackgroundTasks` intactos. `orquestador.py` añade prefijos `[Audio transcrito]`/`[Imagen OCR]` al historial.
- **Configuraciones** — banner `CLAVE_SECRETA → re-subir .p12` y avisos `valida_hasta <30` en rojo; `Reportes` sin cambios (Fase 2-A).

## Verificación Fase 3

- `npm run lint`: 1 warning heredado `esRutaComprobante`, 0 errores.
- `npm run build`: 2857 módulos, 1.1 MB → OK.
- Smoke `/receptores/:id/editar` y `/articulos/:id/editar` 409→`ayudaError`, `/comprobantes/:id` visor RIDE + `Emitir`/`Consultar`, `docker-compose up --build` con `URL_BASE_DATOS` pg y `GET /api/salud → ok`.

## Enlaces

- Avance 3-A: [`avance_fase3_infra_edicion.md`](avance_fase3_infra_edicion.md)
- Avance 3-B: [`avance_fase3_trazabilidad_whatsapp.md`](avance_fase3_trazabilidad_whatsapp.md) (cuando 3-B lo entregue)
- Avance Fase 2: [`avance_fase2_resumen.md`](avance_fase2_resumen.md)
