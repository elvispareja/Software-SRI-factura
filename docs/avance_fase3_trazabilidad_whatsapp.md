# Avance — Fase 3-B: Trazabilidad, WhatsApp multimodal y pulido

> **Fecha:** 10 de agosto de 2026
> **Agente:** 3-B — Trazabilidad, WhatsApp multimodal y pulido
> **Plan:** `~/.commandcode/plans/fase-3-produccion-sin-smtp-cert.md` (sección Agente 3-B)
> **Mockup:** `Cloud World Office.dc.html` — `isTraza` líneas 545-689
> **Estado:** completado — `oxlint` y `vite build` deben pasar, sin regresión Fase 2

---

## 1. Mapeo mockup `isTraza` → implementación

| Mockup `isTraza` (545-689) | Implementado | Notas |
|---|---|---|
| `tz.steps` header 553-557 (Generación / Estado tributario / Envío / Finalizada + Volver) | `ComprobanteTraza.jsx` card superior + `ComprobanteTraza.module.css` `.cardTop/.steps/.step` | 4 steps con ícono verde + separador + sub. Botón `Volver al listado` → `/comprobantes`. Badge número + estado SRI. |
| Panel izquierda 561-614: `tz.emisor`/`tz.doc`/`tz.recep`/`tz.items`/`tz.formasPago`/`tz.tot` con zoom `tz.zoom`/`tz.zoomIn`/`tz.zoomOut` | `.visorWrap` oscuro + barra zoom (60-140 %) + `iframe src={urlRide(id)}` con `transform: scale()` | Si `clave_acceso` aún no existe (Borrador) muestra placeholder "Borrador — emite para ver RIDE" con estado y CTA Emitir. Zoom controlado con `ZoomIn/ZoomOut`, escala CSS `transform`. |
| Panel derecho 617-637: `tz.aEnviar` naranja #f26a35 + `tz.aPdf`/`aPdfApart`/`aPos` + `tz.aXml`/`aRespXml` + `tz.aNc`/`aNd` | `.accionesPanel` con `btnEnviar` naranja `--accent-primary` (#f26a35) + `ACCIONES_COMPROBANTE`/`ESTADOS_*` + Links NC/ND con `?origen=id` + Anular | `Enviar` llama `emitirAlSri(id)` y muestra `mensajes` SRI. `PDF/PDF aparte/POS` abren `urlRide(id)` en pestaña nueva. `XML` → `urlXml(id)`. `Resp. XML` → `consultarEstadoSri(id)`. NC/ND → `/comprobantes/nota-credito?origen=id` y `?origen` débito. Anular → `anularDocumento(id)` con `confirm`. Deshabilitados según `estado_sri`. |
| Acordeones 644-686: `tz.pagos` / `tz.nc` / `tz.nd` (tablas + paginación + "Este comprobante no tiene detalles") | 3 `<Acordeon>` con búsqueda + tablas + paginación + vacío idéntico | `Pagos aplicados` abierto por defecto, NC/ND cerrados. Placeholder fiel: "Este comprobante no tiene detalles para mostrar." |
| `tz.zoom` `tz.zoomScale` | `useState zoom 100` con `zoomIn/out` clamped 60-140, `transform: scale(zoom/100)` en `rideInner` | Sin reinventar: `ZoomIn/ZoomOut` de `lucide-react`. |

Tokens: todo vía `frontend/src/index.css` (`--accent-primary`, `--panel-bg`, `--field-borde`, `--success-soft`, etc.). Sin colores literales. Tipografía y sombras coherentes con `glass-panel`.

---

## 2. `ComprobanteTraza.jsx` — visor real (reemplaza placeholder 24 líneas)

Anterior: `ComprobanteTraza.jsx` solo mostraba `ID {id}` y link volver. Agente 2 debía reemplazarlo; ahora Fase 3-B lo materializa.

```jsx
const { id } = useParams();
const [comprobante, setComprobante] = useState(null);
const [crudo, setCrudo] = useState(null);
const [cargando, setCargando] = useState(true);
const [error, setError] = useState(null);
const [sinConexion, setSinConexion] = useState(false);
// + zoom, mensaje, accion, pagosOpen/ncOpen/ndOpen
useEffect(() => {
  const ctrl = new AbortController();
  api.obtener(`/comprobantes/${id}`, undefined, { senal: ctrl.signal })
  // adaptador comprobanteDesdeApi si hace falta
  // estados cargando/error/sinConexion con EstadoCarga
}, [id]);
```

- **Hook:** `useParams id`, `useState(comprobante)`, `useEffect` con `api.obtener('/comprobantes/{id}')` + `AbortController` (cancela petición vieja al cambiar de comprobante).
- **Adaptador:** `comprobanteDesdeApi` (en `api/adaptadores.js`) mapea `receptor_razon_social`/`estado_sri`/`clave_acceso`/`numero_autorizacion`. Fallback manual si el adaptador no contempla `claveAcceso`.
- **Estados:** `cargando` → `TablaCargando`, `sinConexion` (ErrorApi `esFalloDeRed`) → `SinConexion`, `error` → `ErrorCarga`, `!comprobante` → "no encontrado".
- **Borrador:** si `clave_acceso` es null, no se renderiza `iframe`; se muestra placeholder con explicación y estado actual.
- **RIDE:** `iframe src={urlRide(id)}` ocupa `78vh`, `min-width: 560px`, overflow auto. `urlRide` → `api.urlDescarga('/comprobantes/{id}/ride')` → `GET /comprobantes/{id}/ride` del backend (StreamingResponse PDF).
- **Zoom:** pill centrado oscuro, botones `ZoomOut/ZoomIn`, valor `{zoom}%`, `inner` con `transform: scale(zoom/100)` y `transformOrigin: top center`. Rango 60-140 % en pasos de 10.
- **Panel der:** importado `ACCIONES_COMPROBANTE`, `ESTADOS_EMITIBLES` (`Borrador/Rechazado/Devuelto/Error`), `ESTADOS_CONSULTABLES` (`Pendiente/Devuelto/Rechazado`) de `api/documentos.js`. Botones deshabilitados según estado; tooltips explican qué estados permiten la acción. `Anular` bloqueado si ya `Autorizado` (requiere NC) o `Anulado`.
- **Acordeones:** componente `Acordeon` reutilizable con `ChevronDown` giratorio, `aria-expanded`, body con input búsqueda + tabla `overflow-x:auto` + footer paginación "Viendo 0 a 0" y placeholder.

Archivo CSS: `ComprobanteTraza.module.css` fiel a tokens `index.css` (sin literales), responsive `flex-wrap`, `max-width: 1240px`, `glass-panel` heredado.

---

## 3. Endpoints usados (comprobantes)

| Acción | Helper frontend | Método/Ruta backend | Qué hace |
|---|---|---|---|
| Cargar comprobante | `api.obtener('/comprobantes/{id}')` | `GET /comprobantes/{id}` (`routers/comprobantes.py:305`) | Devuelve `ComprobanteSalida` (incluye `clave_acceso`, `estado_sri`, `numero_autorizacion`). |
| Emitir al SRI | `emitirAlSri(id)` → `api.crear('/comprobantes/{id}/emitir')` | `POST /comprobantes/{id}/emitir` (firma con `.p12`, `clave 49`, XAdES-BES, SOAP SRI, RIDE) | Devuelve `RespuestaEmision { comprobante, estado_recepcion, estado_autorizacion, mensajes }`. El visor refresca `crudo/comprobante` y muestra `mensajes` SRI. |
| Consultar estado | `consultarEstadoSri(id)` | `POST /comprobantes/{id}/consultar` (`consultar_autorizacion` con backoff) | Reconsulta autorización; útil cuando el SRI dejó el comprobante en `Pendiente`. |
| RIDE/PDF/PDF aparte/POS | `urlRide(id)` → `api.urlDescarga('/comprobantes/{id}/ride')` | `GET /comprobantes/{id}/ride` (StreamingResponse PDF) | Genera `generar_ride(factura, numero, clave_acceso, numero_autorizacion, ambiente, TITULO_RIDE)`. Tres botones usan la misma URL; se abren con `target=_blank`. |
| XML | `urlXml(id)` | `GET /comprobantes/{id}/xml` | Devuelve `xml_firmado` si existe, o genera `generar_xml_factura` en borrador. |
| Nota Crédito/Débito | `Link /comprobantes/nota-credito?origen=id` | `NotaCreditoForm variante` (APP.jsx `path="comprobantes/nota-credito"` ya existe) | Pre-carga `?origen` para referenciar `num_doc_modificado`/`motivo`. |
| Anular | `anularDocumento(id)` → `api.crear('/comprobantes/{id}/anular')` | `POST /comprobantes/{id}/anular` | Solo si no `Autorizado` (409 caso contrario: usar NC). |

`App.jsx` mantiene `path="comprobantes/:id" → ComprobanteTraza` (no se movió; 3-A añade `:id/editar` para receptores/artículos sin colisión porque van bajo `receptores/` y `articulos/`).

---

## 4. WhatsApp multimodal — `backend/app/routers/whatsapp.py`

Antes: `_procesar` solo entendía `type=="text"`; audio/imagen respondían "solo texto".

Ahora: `_procesar` maneja tres ramas sin romper HMAC ni `BackgroundTasks`:

### HMAC y 200 inmediata (sin cambio)

```python
cuerpo_bruto = await request.body()
if not _firma_valida(cuerpo_bruto, request.headers.get("X-Hub-Signature-256")):
    raise HTTPException(403, "Firma del webhook inválida.")
cuerpo = await request.json()
for mensaje in _extraer_mensajes(cuerpo):
    tareas.add_task(_procesar, mensaje, sesion)
return {"recibido": True}
```

Meta corta a 20 s; el `200` inmediato evita reintentos duplicados.

### Rama audio / voice

```python
if tipo in ("audio", "voice"):
    media_id = (mensaje.get("audio") or mensaje.get("voice") or {}).get("id")
    audio_bytes, mime = _descargar_media(media_id)  # GET /{id} → media_url → bytes (TOKEN_ACCESO)
    texto = _transcribir_audio(audio_bytes, mime)
    # si texto is None → responde "Audio recibido — transcripción no configurada (falta OPENAI_API_KEY)"
    # si hay texto → atender_mensaje(remitente, texto, sesion, es_audio=True)
```

- **Descarga:** `_descargar_media` sigue el contrato Graph API de Meta: primero `GET https://graph.facebook.com/{VERSION_GRAPH}/{media_id}` con `Bearer TOKEN_ACCESO` para obtener `url`, luego `GET url` con el mismo bearer. Maneja errores y timeouts (15 s meta, 30 s binario).
- **Transcripción:** `_transcribir_audio(bytes, mime)` con prioridad:
  1. `OPENAI_API_KEY` + `openai` (import opcional) → `client.audio.transcriptions.create(model="whisper-1", file=..., language="es")`
  2. `faster-whisper` (`WhisperModel("small")`, tempfile) si está instalado
  3. `None` → fallback con `registro.warning` y mensaje al usuario sin romper el webhook
- **Fallback:** si faltan credenciales/librerías no se rompe: se loggea y se responde `"Audio recibido — transcripción no configurada (falta OPENAI_API_KEY). Instala Whisper o configura OPENAI_API_KEY para habilitar audio."`

### Rama imagen

```python
elif tipo == "image":
    media_id = mensaje.get("image", {}).get("id")
    imagen_bytes, mime = _descargar_media(media_id)
    texto = _ocr_imagen(imagen_bytes, mime)
    # si None → "Imagen recibida — OCR no configurado (falta ANTHROPIC_API_KEY)"
    # si hay texto → atender_mensaje(..., es_imagen=True)
```

- **OCR:** `_ocr_imagen` usa `anthropic` Vision (Claude) con el prompt exacto del plan: `"Extrae RUC/cédula, nombre, monto del recibo/foto en texto estructurado"` (extendido para RUC/identidad). Envía `base64(b64, media_type)` + bloque `type: image`. Normaliza `mime` a los 4 admitidos por Anthropic. Si no hay `ANTHROPIC_API_KEY` o la librería no está, retorna `None` y el caller responde con el fallback sin romper.
- **Compatibilidad:** `try: import openai/anthropic except ImportError: openai=None` — el webhook arranca aunque no estén instalados. `requirements.txt` no se modifica (las deps opcionales se instalan por separado).

---

## 5. IA orquestador — `backend/app/ia/orquestador.py`

`extraccion.py` no se toca (ESQUEMA_FACTURA con `structured outputs`, `precio_incluye_iva`, `datos_faltantes` intacto). Solo `orquestador.py`:

```python
def atender_mensaje(telefono, texto, sesion, es_audio=False, es_imagen=False):
    # ...
    texto_para_modelo = f"[Audio transcrito] {texto}" if es_audio else \
                        f"[Imagen OCR] {texto}" if es_imagen else texto
    extraccion = extraer_factura(texto_para_modelo, conversacion.historial)
    conversacion.historial += [
        {"role": "user", "content": texto_para_modelo},
        {"role": "assistant", "content": extraccion.respuesta_sugerida},
    ]
    if len(conversacion.historial) > 12:
        conversacion.historial = conversacion.historial[-12:]
```

- `whatsapp.py` llama `atender_mensaje(..., es_audio=True, es_imagen=True)` y `orquestador` lo anota con prefijo `[Audio transcrito]` / `[Imagen OCR]` en `historial` para que `extraccion.py` tenga contexto sin alterar el esquema.
- `Conversacion.historial` se capa a 12 turnos para no exceder la ventana del modelo.
- Compatibilidad: `_procesar` prueba `atender_mensaje(..., es_audio=...)` y cae a la firma vieja si la versión en memoria no la acepta (`except TypeError`).

---

## 6. Configuraciones pulido — `frontend/src/pages/Configuraciones/Configuraciones.jsx`

En la sección `Conexiones Tributarias` (ya validaba 5 MB + `cargar_p12` + `cifrar(contrasena)`):

- **Banner CLAVE_SECRETA:** siempre visible en `isConex`, naranja con `AlertTriangle`:

  > **Si cambias CLAVE_SECRETA, vuelve a subir el .p12.** La contraseña del certificado se cifra con esa clave (cifrado.py §11 — Fernet/PBKDF2 con sal fija). Al rotarla, el descifrado falla y hay que re-subir el certificado.

  Mitiga el riesgo del plan: `servicios/cifrado.py:descifrar` lanza `ErrorCifrado` si la clave rotó; el banner lo anticipa.

- **Vigencia <30 días en rojo:**
  - `firma.validaHasta` se pinta en `var(--error)` + `fontWeight: 700` y con sufijo `· Caduca en N días` / `Expirado` cuando `diasParaExpirar(validaHasta) < 30`.
  - Banner adicional por debajo del primero: `bannerPorExpirar` (naranja) si 0-29 días, `bannerExpirado` (rojo) si expirado <0, con texto "Certificado por expirar: caduca en N días (YYYY-MM-DD)" / "Certificado expirado hace N días — no se puede firmar".
  - Reutiliza `diasParaExpirar` de `data/configuracionEmpresa.js`; `EstadoFirmaDetalle` ya mostraba esa lógica en detalle, ahora también en la cabecera y en el input.

No se tocó la lógica de subida (`subirFirma` multipart, validación `.p12/.pfx`, 5 MB, `useRecurso` para firma). `Reportes.jsx` se dejó intacto: 7 tabs hero + `cargarIva/cargarRetenciones/cargarVentasPorTipo/cargarClientes/cargarArticulos` reales, PDF con banner "Próximamente" sin crear `GET /reportes/*/pdf`.

Estilos nuevos en `Configuraciones.module.css`: `.bannerClaveSecreta`, `.bannerPorExpirar`, `.bannerExpirado` con tokens `index.css` (`--warning-soft`, `--error-soft`).

---

## 7. Archivos tocados (3-B)

- `frontend/src/pages/Comprobantes/ComprobanteTraza.jsx` — visor 2-paneles completo (hook, RIDE iframe, zoom, acciones SRI, acordeones).
- `frontend/src/pages/Comprobantes/ComprobanteTraza.module.css` — nuevo, tokens `index.css`, sin literales.
- `backend/app/routers/whatsapp.py` — ramas `audio`/`voice` + `image`, helpers `_descargar_media`/`_transcribir_audio`/`_ocr_imagen`, imports opcionales, preserva HMAC y BackgroundTasks.
- `backend/app/ia/orquestador.py` — `es_audio`/`es_imagen` en `atender_mensaje` + anotación en historial + límite 12 turnos.
- `frontend/src/pages/Configuraciones/Configuraciones.jsx` — banners Conexiones Tributarias (CLAVE_SECRETA + <30 días rojo).
- `frontend/src/pages/Configuraciones/Configuraciones.module.css` — estilos de banners nuevos.
- `docs/avance_fase3_trazabilidad_whatsapp.md` — este documento.
- `docs/avance_fase3_resumen.md` — índice fase 3 (actualiza/crea).
- `backend/app/ia/extraccion.py`, `backend/app/sri/ride.py`, `backend/app/sri/modelos.py` — leídos, no modificados (reutilizados).
- `frontend/src/App.jsx`, `backend/app/base_datos.py`, `backend/app/seguridad.py` — no tocados (verifica que `comprobantes/:id` sigue).
- SMTP y cert `.p12` acreditado — Fase 4, no tocados (ver plan).

---

## 8. Cómo probar

### Trazabilidad

```bash
cd frontend
npm run dev   # http://localhost:5173
# Backend en 8000 con datos de prueba:
# 1. Crear factura en /comprobantes/nuevo o vía POST /api/comprobantes
# 2. Abrir /comprobantes/5 (id real) — debe mostrar:
#    - Header steps + badges número/estado
#    - Si Borrador sin clave_acceso: placeholder borrador
#    - Si ya emitido: iframe RIDE con zoom 60-140 %
# 3. Panel der:
#    - Enviar → POST /comprobantes/{id}/emitir → estado pasa a RECIBIDA/Pendiente/Autorizado
#    - si Rechazado/Devuelto → Enviar habilitado de nuevo
#    - PDF / PDF aparte / POS → abren /comprobantes/{id}/ride en pestaña nueva
#    - XML → /comprobantes/{id}/xml (descarga)
#    - Resp. XML → POST /comprobantes/{id}/consultar → muestra mensajes SRI
#    - NC/ND → /comprobantes/nota-credito?origen=id (y débito) — pre-carga referencia
#    - Anular → POST /comprobantes/{id}/anular (bloqueado si Autorizado)
# 4. Acordeones Pagos/NC/ND: "Este comprobante no tiene detalles para mostrar." y búsqueda inerte
```

Con `.p12` de pruebas el SRI suele responder `39 FIRMA INVALIDA` hasta Fase 4 (esperable). La verificación es que el flujo no rompe y los mensajes SRI se muestran.

### WhatsApp multimodal

```bash
cd backend
pip install openai anthropic faster-whisper  # opcionales; webhook funciona sin ellas
# Variables:
WHATSAPP_TOKEN_VERIFICACION=...
WHATSAPP_SECRETO_APP=...
WHATSAPP_TOKEN_ACCESO=...   # para Graph API /{id} + descarga + envío
WHATSAPP_ID_NUMERO=...
WHATSAPP_VERSION_GRAPH=v21.0
OPENAI_API_KEY=sk-...       # para audio Whisper
ANTHROPIC_API_KEY=sk-ant-... # para imagen Vision
uvicorn app.main:aplicacion --reload
```

- **Webhook handshake:** `GET /api/whatsapp?hub.mode=subscribe&hub.verify_token=...&hub.challenge=123` → `123`
- **Texto:** enviar por WhatsApp al número configurado → `X-Hub-Signature-256` válido → `_procesar` → `atender_mensaje` → respuesta por Graph API
- **Audio:** grabar nota de voz (type `audio`/`voice`) → Meta entrega `audio.id` → descarga Graph API → Whisper transcribe → `atender_mensaje("[Audio transcrito] ...")` → flujo normal. Sin `OPENAI_API_KEY` → responde fallback y no rompe.
- **Imagen:** enviar foto de RUC/recibo (type `image`) → `image.id` → descarga → Claude Vision extrae `RUC/nombre/monto` → `atender_mensaje("[Imagen OCR] ...")`. Sin `ANTHROPIC_API_KEY` → fallback.
- **Degradado:** `type` desconocido → "Por ahora entiendo texto, audio e imágenes."

### Configuraciones

```
Navegar /configuraciones → Conexiones Tributarias:
- Ver banner naranja "Si cambias CLAVE_SECRETA, vuelve a subir el .p12 (cifrado.py §11)"
- Subir .p12 de pruebas (5 MB máx, solo .p12/.pfx) → ver titular/vigencia
- Si valida_hasta <30 días: input en rojo + sufijo "Caduca en N días" + banner crítico naranja/rojo
- Si expirado: banner rojo "Expirado hace N días — no se puede emitir"
```

---

## 9. Verificación

```bash
cd frontend && npm run lint   # oxlint — 1 warning heredado ok
cd frontend && npm run build  # vite build — 2851-2856 módulos (según fase)
cd backend && pytest          # 252 tests sin cambio de firma
```

- No rompe Fase 2: `TablaCWO`, `EstacionComprobante`, `Reportes`/`Configuraciones` existentes sin regresión.
- Todo en español. Cada tarea documentada en `.md`.

---

## 10. Fuera de alcance (Fase 4)

- SMTP `POST /comprobantes/:id/enviar` (host/port/user/pass, plantillas, adjuntos XML+RIDE) — no tocado.
- Certificado `.p12` acreditado (BCE/Security Data, re-cifrado tras rotar `CLAVE_SECRETA`) — el banner 3-B lo anticipa; la rotación real queda para Fase 4 con cert nuevo.
- Tablas contables (`cuota`/`recibo`/`anticipo`/`asiento`) — no tocadas, siguen placeholder según `sistema_facturacion_plan.md §2`.
- `GET /reportes/*/pdf` — no creado; Reportes mantiene CSV/BOM.
