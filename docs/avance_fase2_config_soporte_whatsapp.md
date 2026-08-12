# Avance Fase 2-B — Configuraciones + Soporte + WhatsApp AI Assistant

> Agente Fase 2-B. Workspace: `C:\Users\d4bic\Desktop\Google Drive\Software SRI factura`. Mockup: `Cloud World Office.dc.html` (3618 líneas). Plan fase 1: `~/.commandcode/plans/cloud-world-frontend-adopcion.md`.

## 1. Mapeo mockup → implementación

| Mockup | Líneas | Implementación |
|---|---|---|
| `isConfig` (`cfg.*`) 2320-2680 | `frontend/src/pages/Configuraciones/Configuraciones.jsx` + `Configuraciones.module.css` | Sidebar 2-panel fiel: 13 secciones `cfg.secs` (perfil/empresa/bancos/impuestos/pdf/impresoras/permisos/usuarios/zonas/vendedores/banner/leyendas/conexiones). Vistas: `cfg.isPerfil` (perfilFields + copias facMailBg + toggle), `cfg.isList` (tabla genérica cols/rows + búsqueda + paginación), `cfg.isPdf` (pdfFields/pdfColors/posFields + tabs pdf/pos), `isImpresoras`, `isBanner`, `isConex` (certFields .p12). |
| `isSopApp` 1508-1557 + `isSopModal` 1560-1608 (`sop.*`) | `frontend/src/pages/Soporte/Soporte.jsx` + `Soporte.module.css` | Sub-app con topBar (FACTOA + pill usuario), tabs `Mis casos / Base de conocimiento` (`sop.tabs`), hero naranja con CTA `Nuevo Caso` (`sop.nuevo`), filtros `Todos/Abiertos/Esperando/Resueltos` (`sop.filters`), búsqueda, empty + lista de tickets, footer mail. Modal `isSopModal`: asunto/categoría/textarea + upload imágenes (hasta 3) + video (50 MB, mp4/webm/mov) + toggle mail (`sop.mailBg/mailBd/mailOpacity`). |
| Header WhatsApp 188-198 (`assistant`, `onAssistantInput`, `onAssistantKey`, `onAssistantSend`, `cwoPulse`) | `frontend/src/components/Layout/Layout.jsx` + `Layout.module.css` + `frontend/src/api/cliente.js` | Input `whatsappBox` en `headerGlass` (no rompe responsive: `flex:1 1 100%` en <1024px). `onAssistantSend` cableado: si hay sesión intenta `POST /api/whatsapp/asistir`, fallback toast + `CustomEvent(cwo:assistant)`. Botón con `cwoPulse` y estado `assistantEnviando`. |

Tokens: todos vía `frontend/src/index.css` (no colores literales). Tipografía `Plus Jakarta Sans`.

## 2. Endpoints usados

### Configuraciones — backend real

| Método | Ruta | Uso |
|---|---|---|
| `GET /api/configuracion/empresa` | `api/configuracion.js: empresaDesdeApi` | Carga empresa al montar (via `useRecurso`) |
| `PUT /api/configuracion/empresa` | `guardarEmpresa` | Guardar desde pestaña Empresa (incluye establecimientos) |
| `GET /api/configuracion/establecimientos` | `establecimientoDesdeApi` | Lista establecimientos + puntos |
| `POST /api/configuracion/establecimientos` | `crearEstablecimiento` | Crear (ids locales >1000) |
| `PUT /api/configuracion/establecimientos/{id}` | `actualizarEstablecimiento` | Actualizar existente (id <1000) |
| `DELETE /api/configuracion/establecimientos/{id}` | `eliminarEstablecimientoApi` | Eliminar |
| `GET /api/configuracion/cuentas` | `cuentaDesdeApi` | Lista bancos |
| `POST /api/configuracion/cuentas` | `crearCuenta` | Crear cuenta (modal) |
| `DELETE /api/configuracion/cuentas/{id}` | `eliminarCuenta` | Soft-delete (activa=false) |
| `GET /api/configuracion/firma` | `firmaDesdeApi` | Metadatos .p12 (sección Conexiones) |
| `POST /api/configuracion/firma` | `subirFirma` (multipart .p12 + contraseña, 5 MB) | Validación `cargar_p12` antes de guardar; solo .p12/.pfx |
| `DELETE /api/configuracion/firma` | `quitarFirma` | Desactivar |
| `GET /api/auth/yo` | `SesionProvider.jsx` + perfil en `Configuraciones` | Nombre/correo para header y perfil |

### WhatsApp AI — backend real

| Método | Ruta | Descripción |
|---|---|---|
| `GET /api/whatsapp` | `routers/whatsapp.py: verificar_webhook` | Handshake Meta (`hub.challenge`) |
| `POST /api/whatsapp` | `recibir_webhook` | HMAC `X-Hub-Signature-256` + `BackgroundTasks` → `orquestador.atender_mensaje` → Graph API v21.0 `/{ID_NUMERO}/messages` |
| — | `ia/orquestador.py: atender_mensaje` + `ia/extraccion.py` | Claude extrae `crear_factura`, valida identificación SRI, calcula totales con motor `sri/modelos.py`, borrador → confirmación `sí/no` → `emitir_comprobante` |

Header intenta `POST /api/whatsapp/asistir` (endpoint de asistencia web, opcional). Si 404, muestra toast informativo y emite `CustomEvent('cwo:assistant')` para que vistas futuras lo capturen. En modo demo, toast directo: “Escribe al bot de WhatsApp”.

### Soporte — sin backend

No existe `POST /api/soporte/casos` en `backend/app/routers/`. Se deja UI 100% local.

## 3. Placeholders y por qué

| Sección | Estado | Motivo |
|---|---|---|
| Configuraciones: Impuestos, Permisos, Usuarios, Zonas, Vendedores, Leyendas | Tabla genérica + banner “Próximamente” naranja, sin romper. Botón “Agregar” muestra toast “Próximamente”. | No hay endpoints. `PLACEHOLDER_LISTS` replica `CFG_LISTS` del mockup (cols/empty/addLabel) sin inventar esquema. |
| Configuraciones: Impresoras (Factoa Print) | Card informativa + empty “No hay terminales” + banner próximamente. Botones simulan toast. | Sin endpoint de terminales/impresoras. |
| Configuraciones: Banner Publicitario | Preview local (ObjectURL) + nombre, validación 2 MB, sin persistencia. | Sin endpoint de banner. |
| Configuraciones: PDF/Impresiones | Campos y colores estáticos (fiel a `pdfFields/pdfColors/posFields`), guardado solo toast. | Sin endpoint de preferencias PDF. |
| Soporte: Tickets | `localStorage('soporte_casos')` + semilla `CASOS_SEMILLA`. | Sin backend. |
| Soporte: Videotutoriales | Botones con toast “próximamente”. | Contenido futuro. |

## 4. Contratos propuestos (futuro)

### Soporte — `POST /api/soporte/casos`

```http
POST /api/soporte/casos
Content-Type: multipart/form-data
Authorization: Cookie sri_factura (HttpOnly)

asunto: string (requerido, 3-120)
categoria: "Técnico" | "Facturación" | "Cuenta" | "Otro"
descripcion: string (requerido, 10-5000)
imagenes: File[] (0-3, image/*, ≤5 MB c/u)
video: File | null (video/mp4, video/webm, video/quicktime, ≤50 MB, retención 30 días)
quiere_mail: boolean

201 { id: "TK-000125", estado: "Abierto", fecha: "2026-08-10", ... }
422 validación, 413 payload demasiado grande
```

Listado/filtros:

```http
GET /api/soporte/casos?estado=Abierto|Respondido|Cerrado&q=&tamano=20&pagina=1
GET /api/soporte/casos/{id}
POST /api/soporte/casos/{id}/mensajes { texto }
```

Frontend ya deja preparado: estado local con `useCasosLocales`, filtros `Todos/Abiertos/Esperando/Resueltos` mapean a `Abierto/Respondido/Cerrado`, persistencia lista para sustituir por `useRecurso('/soporte/casos')`.

### WhatsApp web assist — `POST /api/whatsapp/asistir` (opcional, para el header)

```http
POST /api/whatsapp/asistir
Content-Type: application/json
Cookie: sri_factura

{ "texto": "Crear Factura para Juan..." }

200 { "respuesta": "Esto es lo que voy a emitir: ..." }
401 no autenticado, 422 texto vacío
```

Si no se implementa, el header ya funciona en modo degradado (toast + evento). El flujo real sigue siendo el webhook `POST /api/whatsapp` desde Meta.

### Anticipos — si aplica (fuera de Fase 2-B)

No se tocó. Queda como placeholder en Fase 1.

## 5. Cómo probar

```bash
# Frontend
cd frontend
npm run lint
npm run build
npm run dev   # http://localhost:5173

# Backend
cd backend
uvicorn app.main:aplicacion --reload  # http://localhost:8000/docs
```

- **Configuraciones**: `/configuraciones` → navegar las 13 secciones del sidebar. `Empresa`: editar RUC/razón/dirección/provincia/cantón y guardar (requiere backend). `Cuentas Bancarias`: crear con modal (banco + número + tipo). `Conexiones Tributarias`: subir .p12 (validación real, 5 MB, solo .p12/.pfx) y ver vigencia. Secciones placeholder muestran banner naranja y tabla vacía sin error.
- **Soporte**: `/soporte` → tabs `Mis casos` / `Base de conocimiento`. `Mis casos`: filtros + búsqueda + `Nuevo Caso` (modal con validación, imágenes y video). Los casos persisten en `localStorage`. `Base`: FAQ con búsqueda + acordeón + videotutoriales.
- **WhatsApp AI**: header `WhatsApp AI Assistant` → escribir “ej., Crear Factura para Juan...” y Enter o botón. Sin sesión: toast “Escribe al bot de WhatsApp”. Con sesión: intenta `POST /api/whatsapp/asistir`; si 404, toast con link a este doc. Responsive: en <1024px el box ocupa 100% del header sin romper layout. Flujo real: enviar mensaje al número de WhatsApp configurado (`WHATSAPP_ID_NUMERO`) → webhook → `orquestador.atender_mensaje` → respuesta por WhatsApp.

Variables WhatsApp: `WHATSAPP_TOKEN_VERIFICACION`, `WHATSAPP_SECRETO_APP`, `WHATSAPP_TOKEN_ACCESO`, `WHATSAPP_ID_NUMERO`, `WHATSAPP_VERSION_GRAPH=v21.0`.

## 6. Archivos tocados

- `frontend/src/pages/Configuraciones/Configuraciones.jsx` — sidebar 13 ítems, 7 vistas, backend real + modales
- `frontend/src/pages/Configuraciones/Configuraciones.module.css` — layout 2-panel, cards, tablas, modal, firma
- `frontend/src/pages/Soporte/Soporte.jsx` — sub-app + modal fiel mockup, datos mock locales
- `frontend/src/pages/Soporte/Soporte.module.css` — topBar/tabs/hero/filtros/modal
- `frontend/src/components/Layout/Layout.jsx` — `onAssistantSend` cableado, `URL_API`, toast, `assistantEnviando`
- `frontend/src/components/Layout/Layout.module.css` — `whatsappToast`, `cwoToast`, `whatsappSend:disabled`

Backend no modificado (solo docs).

## 7. Verificación

- `npm run lint` y `npm run build` deben pasar.
- Plus Jakarta Sans, tokens `index.css`, responsive header intacto, Fase 1 sin regresión.
