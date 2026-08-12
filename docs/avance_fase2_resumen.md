# Avance Fase 2 — Resumen (índice)

> Índice de la Fase 2. Cada agente documenta aquí su entregable y verificación.

## Agentes y entregables

| Agente | Foco | Doc principal | Estado |
|---|---|---|---|
| **Fase 2-A — Cuentas + Anticipos + Reportes** | 6 tabs Cuentas (`cx.*`), Anticipos 11 cols + modal (`an.*`/`am.*`), Reportes 7 tabs hero + CSV (`ra.*`) | `docs/avance_fase2_cuentas_anticipos_reportes.md` | ✅ Entregado |
| **Fase 2-B — Configuraciones + Soporte + WhatsApp AI** | Sidebar 13 secciones (`cfg.*`), firma .p12 real, Soporte sub-app + modal (`sop.*`), WhatsApp AI header (`assistant`/`cwoPulse`) | `docs/avance_fase2_config_soporte_whatsapp.md` | ✅ Entregado |

## Fase 2-A — Detalle

- **Cuentas pendientes** — `frontend/src/pages/Cuentas/Cuentas.jsx` (`isCuentas` 1729-2102)
  - 6 tabs (Inicio con 4 KPIs `porCobrar` + agenda / Receptores con saldos reales `GET /comprobantes?estado_pago=Por Cobrar` / Gestión mensual `mesLabel` / Historial `histTiles` / Vencidos / Reportes 5 cards) + modales Saldo y Config Recibos. Sin tabla nueva; banner Próximamente en lo contable.
- **Anticipos** — `frontend/src/pages/Anticipos/Anticipos.jsx` + `data/anticipos.js` (`isAnticipos` 2105-2317)
  - Tabla 11 cols + filtros estado/tipo/desde/hasta + info box ARD/APP + modal Recibido/Pagado. Datos mock locales (contrato `POST /api/anticipos` propuesto en doc 2-A).
- **Reportes avanzados** — `frontend/src/pages/Reportes/Reportes.jsx` (`isRepApp` 1611-1728)
  - Hero + 7 tabs + radios Excel/PDF + toggle rango. Tab Comprobantes con 3 sub-pestañas IVA/Retenciones/Ventas reales + Estado SRI + CSV; Inventario y Receptores con `cargarArticulos`/`cargarClientes` reales; resto placeholder Próximamente.

## Verificación Fase 2-A

- `npm run lint` / `npm run build` OK. `api/reportes.js` ampliado (`cargarArticulos`, `cargarClientes`). Sin backend nuevo.

## Fase 2-B — Detalle

- **Configuraciones** — `frontend/src/pages/Configuraciones/Configuraciones.jsx` + `Configuraciones.module.css`
  - Sidebar 2-panel fiel a `isConfig` 2320-2680 (perfil/empresa/bancos/impuestos/pdf/impresoras/permisos/usuarios/zonas/vendedores/banner/leyendas/conexiones). Vistas: `isPerfil`, `isList`, `isPdf` (pdf/pos), `isImpresoras`, `isBanner`, `isConex`.
  - Backend real: `GET/PUT /api/configuracion/empresa`, `CRUD /configuracion/establecimientos`, `/configuracion/cuentas`, `GET/POST/DELETE /configuracion/firma` (multipart .p12, 5 MB), `GET /api/auth/yo`. Firma con validación `cargar_p12` y banner de vigencia.
  - Placeholders (impuestos/permisos/usuarios/zonas/vendedores/leyendas/impresoras/banner/pdf) con banner “Próximamente” naranja, sin romper.

- **Soporte** — `frontend/src/pages/Soporte/Soporte.jsx` + `Soporte.module.css`
  - Sub-app fiel a `isSopApp` 1508-1557 + `isSopModal` 1560-1608: topBar, tabs `Mis casos/Base`, hero naranja, filtros `Todos/Abiertos/Esperando/Resueltos`, búsqueda, lista vacía/llena, footer mail. Modal: asunto/categoría/textarea + imágenes (≤3) + video (≤50 MB, mp4/webm/mov) + toggle mail.
  - Sin endpoint: datos mock en `localStorage('soporte_casos')` + validación local. Banner “Soporte — canal en desarrollo”. Contrato propuesto: `POST /api/soporte/casos` (multipart, ver doc 2-B).

- **WhatsApp AI Assistant** — `frontend/src/components/Layout/Layout.jsx` + `Layout.module.css`
  - Header `whatsappBox` (líneas 188-198) cableado: `onAssistantInput/onAssistantKey/onAssistantSend` + `cwoPulse`. Con sesión: `POST /api/whatsapp/asistir` (opcional) con fallback 404 → toast + `CustomEvent('cwo:assistant')`. Sin sesión/modo demo: toast + evento. Responsive intacto (`flex:1 1 100%` en <1024px).
  - Backend real: `GET /api/whatsapp` (handshake), `POST /api/whatsapp` (HMAC + BackgroundTasks → `orquestador.atender_mensaje` → Graph API v21.0), `ia/orquestador.py` + `extraccion.py` (Claude).

## Verificación Fase 2-B

- `cd frontend && npm run lint` — debe pasar (oxlint).
- `cd frontend && npm run build` — debe pasar (vite build).
- No rompe Fase 1. Tokens `index.css` y `Plus Jakarta Sans` preservados.

## Docs

- `docs/avance_fase2_config_soporte_whatsapp.md` — mapeo mockup→impl, endpoints, placeholders, contratos propuestos y cómo probar.
- `docs/avance_fase2_resumen.md` — este índice.
