# Sistema de Facturación Electrónica SRI — Ecuador

Facturación electrónica para Ecuador con integración nativa de WhatsApp e
inteligencia artificial: el usuario puede emitir una factura escribiéndole al
bot en lenguaje natural, sin abrir la interfaz web.

**Diseño:** la referencia visual es el prototipo `Cloud World Office.dc.html`
del repositorio — tema claro, barra lateral oscura, naranja `#f26a35` y
Plus Jakarta Sans.

**Estado:** el sistema genera, firma y transmite al SRI los siete comprobantes
electrónicos —factura, nota de crédito, nota de débito, liquidación de compra,
nota de venta, guía de remisión y retención—, tanto desde la interfaz como desde
WhatsApp. El único bloqueante para emitir con validez tributaria es un
certificado `.p12` de entidad acreditada — ver [Qué falta](#qué-falta).

---

## Arquitectura

```
frontend/          React 19 + Vite 8, CSS Modules, tema claro/oscuro
  src/lib/sri/       Motor de cálculo y validación de identificaciones
  src/api/           Cliente HTTP y adaptadores
  src/components/    Layout, formularios de documento, paleta de comandos
  src/pages/         Las 17 pantallas

backend/           Python 3.12 + FastAPI + SQLAlchemy
  app/sri/           Motor SRI: clave de acceso, XML, firma XAdES-BES, SOAP
  app/servicios/     Emisión, reportes, secuenciales, cifrado en reposo
  app/routers/       API REST
  app/ia/            Asistente de WhatsApp con Claude
```

El cálculo de impuestos existe **en los dos lados**: el frontend lo usa para dar
respuesta inmediata mientras se escribe, y el backend recalcula todo antes de
guardar. La base de datos y el XML nunca discrepan porque ambos salen del mismo
motor del servidor.

---

## Puesta en marcha

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/Mac

.venv/Scripts/python scripts/sembrar_datos.py    # datos de demostración
.venv/Scripts/python -m uvicorn app.main:aplicacion --reload
```

API en `http://localhost:8000` · documentación interactiva en `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Interfaz en `http://localhost:5173`.

> Sin el backend levantado la interfaz **sigue siendo navegable**: cae a datos de
> demostración y lo avisa con un banner. Los botones de guardar se deshabilitan,
> porque los identificadores del modo demo no existen en el servidor.

---

## Variables de entorno

| Variable | Para qué | Por defecto |
|---|---|---|
| `CLAVE_SECRETA` | Firma los tokens de sesión y deriva la clave que cifra la contraseña del `.p12` | Valor de desarrollo — **el servidor avisa al arrancar si no la defines** |
| `URL_BASE_DATOS` | Cadena de conexión | `sqlite:///./facturacion.db` |
| `ORIGENES_PERMITIDOS` | CORS del frontend | `http://localhost:5173` |
| `COOKIE_SEGURA` | `false` solo en desarrollo sobre HTTP | `true` |
| `COOKIE_SAMESITE` | `none` si frontend y API van a dominios distintos | `lax` |
| `GEMINI_API_KEY` | Extracción de datos del texto de WhatsApp | — |
| `MODELO_IA` | Modelo de extracción | `gemini-2.5-flash` |
| `ANTHROPIC_API_KEY` | OCR de las imágenes de WhatsApp | — |
| `SMTP_SERVIDOR`, `SMTP_PUERTO` | Envío del comprobante al receptor. Sin servidor, el botón se deshabilita y lo explica | — · `587` |
| `SMTP_USUARIO`, `SMTP_CONTRASENA` | Credenciales del servidor de correo | — |
| `SMTP_REMITENTE`, `SMTP_SSL` | Remitente visible y SSL directo (puerto 465) | `SMTP_USUARIO` · STARTTLS |
| `WHATSAPP_SECRETO_APP` | Verifica la firma HMAC del webhook de Meta | — |
| `WHATSAPP_TOKEN_ACCESO`, `WHATSAPP_ID_NUMERO` | Envío de mensajes | — |
| `WHATSAPP_TOKEN_VERIFICACION` | Handshake de registro del webhook | — |

> ⚠️ **Si `CLAVE_SECRETA` cambia, las contraseñas de certificado guardadas dejan
> de poder descifrarse** y hay que volver a subir el `.p12`. Defínela una vez y
> consérvala.

---

## Pruebas

**663 pruebas** en total: 410 de backend (pytest) y 253 de frontend (vitest).

```bash
cd backend  && .venv/Scripts/python -m pytest -q    # 410 pruebas
cd frontend && npm test                              # 253 pruebas
cd frontend && npm run lint && npm run build
```

Las del frontend cubren el motor de cálculo, la validación de cédulas y RUC,
markup contra margen, los adaptadores que arman el cuerpo que viaja al SRI, los
hooks de listado y reporte, la integridad de los datos de demostración y —montando
los componentes enteros— el Dashboard, la pantalla de Reportes y el formulario de
retención.

Las del backend incluyen el **contenido** de los PDF (se extrae el texto y se
verifica que el RIDE lleve su clave de acceso) y el **flujo completo de cada tipo
de documento**: crear → emitir → consultar → RIDE → XML.

> El entorno de pruebas por defecto es `node`; los dos archivos que necesitan
> DOM lo piden con `@vitest-environment happy-dom`. Las dependencias del
> entorno DOM se pre-empaquetan (`test.deps.optimizer`) porque el proyecto vive
> en una carpeta sincronizada, donde leer `node_modules` archivo a archivo
> tardaba más que el límite de arranque del worker de Vitest.

El motor SRI se puede ejercitar sin interfaz:

```bash
cd backend
.venv/Scripts/python scripts/generar_certificado_pruebas.py certificados/pruebas.p12 clave123
.venv/Scripts/python scripts/poc_factura.py --p12 certificados/pruebas.p12 --clave clave123
```

---

## Qué falta

**Un certificado `.p12` de entidad acreditada** (Banco Central del Ecuador,
Security Data, ANF o Uanataca). Es el único bloqueante real: en las pruebas
contra el ambiente del SRI, la recepción del comprobante fue **aceptada** y la
autorización falló únicamente en la cadena de confianza del certificado
autofirmado (`error 39: FIRMA INVALIDA — no existe certificado root registrado`).
Con el certificado acreditado, el mismo flujo debería autorizar sin cambios de
código: se carga en Configuraciones → Firma Electrónica.

**Secciones marcadas «Próximamente», ninguna por olvido**: impresoras y
terminales dependen de hardware; los permisos granulares por rol solo cubren
tres operaciones sensibles (editar empresa, subir/quitar firma, anular
comprobante) porque el usuario tiene un solo campo `rol` y el resto queda para
una revisión completa del API; y los vídeos de Soporte no están grabados. El
resto de módulos —reportes (con su exportación a PDF), egresos, recurrentes,
cuentas y listas de configuración— ya consultan datos reales (ver
[`docs/lo_construido.md`](docs/lo_construido.md)).

WhatsApp entiende texto, audio e imagen. El audio se transcribe con la API
Whisper de OpenAI (`OPENAI_API_KEY`, con `faster-whisper` como fallback local
opcional, no instalado por defecto) y la imagen con Claude Vision
(`ANTHROPIC_API_KEY`, ya requerida para el resto del asistente). Sin la clave
correspondiente, el mensaje se recibe y el bot lo dice en vez de fallar en
silencio.

Antes de producción: definir `CLAVE_SECRETA` (obligatoria si `AMBIENTE=2`),
migrar a PostgreSQL, mover el cifrado de la clave del `.p12` a un KMS y
contrastar el listado de cantones con la codificación oficial del INEC.

Los porcentajes y códigos de `backend/app/sri/codigos_retencion.py` están
contrastados con la resolución **NAC-DGERCGC26-00000009** (vigente desde el
01/03/2026). Queda por confirmar el único concepto de **ISD**, marcado con
`verificado=False` en el propio archivo.

---

## Producción sin SMTP/cert (Fase 3-A)

Edición en sitio (`/receptores/:id/editar` y `/articulos/:id/editar` con `PUT` y validación 409), Postgres y endurecimiento de secretos. SMTP y certificado `.p12` acreditado quedan para **Fase 4**.

### Despliegue con Docker (Postgres)

```bash
cp .env.example .env   # completa CLAVE_SECRETA si AMBIENTE=2
docker compose up --build
# API en http://localhost:8000  (GET /api/salud → ok)
# Web en http://localhost:5173
```

Variables clave: `URL_BASE_DATOS=postgresql+psycopg://factoa:factoa@db:5432/factoa`, `CLAVE_SECRETA` (falla al arrancar si `AMBIENTE=2` y es la de desarrollo), `ORIGENES_PERMITIDOS` (lista separada por comas). En desarrollo local sin Docker, `URL_BASE_DATOS` sigue funcionando con `sqlite:///./facturacion.db`.

Migración SQLite → Postgres: exporta con `pg_dump` lógico vía SQLAlchemy (sin SQL nativo) o re-sembra con `python scripts/sembrar_datos.py` apuntando `URL_BASE_DATOS` a Postgres. Ver `docs/avance_fase3_infra_edicion.md`.

### Fuera de Drive

El repo vive hoy en `Google Drive/Software SRI factura` (con `node_modules`). Para producción, clónalo fuera de Drive **o** respeta `.gitignore` (ignora `node_modules/.venv/dist/facturacion.db/salida/certificados/*.p12`) y excluye la carpeta de la sincronización de Drive, para que el watcher de Vite/Uvicorn no entre en bucle. Verifica con `git status` limpio y `npm run build` sin ruido.

### Seguridad en producción

- `CLAVE_SECRETA` obligatoria si `AMBIENTE=2` (`seguridad.py` hace `raise RuntimeError` al importar o en el ciclo de vida).
- `ORIGENES_PERMITIDOS` no puede quedar vacío; el backend hace `print` de aviso si lo está.
- `COOKIE_SEGURA=true` y `COOKIE_SAMESITE` según despliegue (ver tabla de variables arriba).


---

## Documentación

`docs/` lleva el registro completo del desarrollo:

| Documento | Contenido |
|---|---|
| [**traspaso.md**](docs/traspaso.md) | **Empieza por aquí si recoges el proyecto** — dónde quedó, qué pasó con la bifurcación de ramas, qué falta y cómo montar el entorno |
| [**manual_de_uso.pdf**](docs/manual_de_uso.pdf) | **Manual ilustrado para quien usa el sistema** — qué hace cada pantalla, los estados del SRI y cómo declarar. Se regenera con `python scripts/generar_manual.py` |
| [**lo_construido.md**](docs/lo_construido.md) | **Inventario completo de lo construido** — el motor del SRI, los 24 modelos, los 118 endpoints, las 17 pantallas y las decisiones detrás |
| [**estado_del_proyecto.md**](docs/estado_del_proyecto.md) | **Qué falta y en qué orden**, con cifras contadas del repositorio |
| [auditoria_proyecto.md](docs/auditoria_proyecto.md) | Auditoría inicial y **índice de todos los avances** |
| [sistema_facturacion_plan.md](docs/sistema_facturacion_plan.md) | Plan y alcance original |
| `avance_*.md` | Un documento por tanda de trabajo, con las decisiones y su porqué |
