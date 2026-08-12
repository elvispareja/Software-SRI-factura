# Avance — Tandas 3 a 6: del prototipo al sistema completo

> **Fecha:** 8 de agosto de 2026
> **Estado:** completado y verificado — 86 tests de backend, lint limpio, build OK

Cuatro tandas seguidas que cierran el alcance del plan: se completó el frontend,
se construyó el backend real con persistencia, se ampliaron los comprobantes del
SRI y se implementó la *killer feature* — facturación por WhatsApp con IA.

---

## Tanda 3 — Frontend faltante

### Motor de precios (`frontend/src/lib/precios.js`)

Arregla un **bug conceptual** de la auditoría: el formulario calculaba
`costo + costo × %` y lo llamaba "utilidad". Eso es *markup* (porcentaje sobre
el costo), no *margen* (porcentaje sobre la venta). Con costo 10 y 50%:

| Base | Fórmula | Precio |
|---|---|---|
| Markup (sobre el costo) | `costo × (1 + p/100)` | **15.00** |
| Margen (sobre la venta) | `costo ÷ (1 − p/100)` | **20.00** |

El formulario ahora obliga a elegir la base en vez de asumirla. 17 aserciones
verifican ambas fórmulas, la ida y vuelta, y los bordes (margen 100% no explota,
costo 0 no divide por cero).

### ArticulosForm completo

Grilla de 6 niveles de precio con **edición bidireccional**: escribir un % calcula
el precio, escribir un precio recalcula el %, y cada fila indica si su valor es
`Calculado` o `Manual`. Más unidad de medida, tipo de codificación, detalle,
bodega y ubicación física, ICE, y control de inventario con semáforo
(agotado / bajo mínimo / toca reponer / suficiente).

### Dashboard según el plan

Sustituye las métricas inventadas por las que pedía el plan, **derivadas de los
datos** en vez de escritas a mano: facturado del mes, documentos del mes, ticket
promedio, documentos del año. Más saludo según la hora, cuatro acciones rápidas,
barra de progreso del plan contratado con aviso al 85%, gráfico de facturación
mensual, **donut de distribución por tipo de documento** y contadores de
clientes/productos/servicios.

### Cotización y Nota de Venta

En vez de duplicar FacturaForm se extrajo
`components/documentos/DocumentoVentaForm.jsx`, parametrizado por tipo de
documento. Las tres pantallas quedaron como envoltorios de ~20 líneas.

**Nota de Venta (RIMPE Negocio Popular) fuerza tarifa 0% y oculta la columna de
IVA**: el régimen no traslada IVA, y dejar elegir una tarifa que no admite solo
produciría comprobantes rechazados.

---

## Tanda 4 — Backend real

### API FastAPI con persistencia

SQLAlchemy 2.0 sobre SQLite (cambiar a PostgreSQL es solo la variable
`URL_BASE_DATOS`). Modelos: `Empresa`, `Establecimiento`, `PuntoEmision`,
`Receptor`, `Articulo`, `Comprobante`, `DetalleComprobante`.

**El dinero se guarda en `Numeric(14,6)`, nunca en `Float`.** El SRI valida los
totales al centavo y un float acumula error al sumar líneas.

**El secuencial se toma con `SELECT … FOR UPDATE` dentro de la transacción.** Si
dos peticiones llegan a la vez, la segunda espera y obtiene el siguiente; un
secuencial repetido hace que el SRI rechace el comprobante. Hay un test que lo
verifica.

Los totales del comprobante **se calculan con el motor SRI**, no con lo que envía
el cliente: así la base de datos y el XML nunca discrepan.

### RIDE (PDF)

`app/sri/ride.py` con ReportLab. Incluye lo que el SRI exige para que un tercero
pueda verificar el comprobante: clave de acceso, número y fecha de autorización,
ambiente. En ambiente de pruebas imprime una franja de advertencia — un RIDE de
pruebas que parezca real es un problema legal.

### Nota de Crédito y Retención

| Documento | Versión | Particularidad |
|---|---|---|
| Nota de Crédito | 1.1.0 | Exige `codDocModificado`, `numDocModificado` y `fechaEmisionDocSustento`; sin ellos el SRI la rechaza. `valorModificacion` incluye IVA |
| Retención | 1.0.0 | Cada línea lleva impuesto, código de retención, base, porcentaje y documento sustento |

Ambas reutilizan la clave de acceso y el firmador XAdES-BES, y **ambas se firman
y verifican correctamente** en los tests.

---

## Tanda 5 — Integración

### Capa de API en el frontend

| Archivo | Rol |
|---|---|
| `src/api/cliente.js` | Fetch centralizado: URL base, token, traducción de errores de FastAPI a texto legible |
| `src/api/adaptadores.js` | Traducción snake_case ↔ camelCase en un solo sitio |
| `src/hooks/useRecurso.js` | Carga con estados de cargando/error, cancelando peticiones obsoletas |
| `src/components/ui/EstadoCarga.jsx` | Esqueletos, error con reintento, aviso de modo demo |

**Si el backend no responde, la interfaz cae a los datos de demostración y lo
avisa con un banner visible.** La app sigue siendo navegable sin backend, pero
nunca finge que los datos son reales.

Las peticiones obsoletas se cancelan con `AbortController`: sin eso, una
respuesta lenta puede pisar a otra más reciente al teclear en el buscador.

### Liquidación de Compra y Guía de Remisión

La liquidación reutiliza `DocumentoVentaForm` filtrando receptores por rol
**Proveedor** (la emite el comprador por cuenta de quien no puede facturar), con
botones de importar XML y PDF/foto.

La Guía de Remisión es una pantalla propia: no lleva precios ni impuestos, sino
fechas, motivo, transportista, placa, y puntos de partida y llegada con
provincia/cantón encadenados. Valida que la fecha fin no sea anterior a la de
inicio.

### Autenticación

JWT firmado con HMAC-SHA256 y contraseñas con **PBKDF2-HMAC-SHA256 con sal por
usuario** (260 000 iteraciones), todo con la librería estándar — sin dependencias
extra.

Detalles que los tests verifican:
- Dos hashes de la misma contraseña **difieren** (sal aleatoria), así dos cuentas con igual clave no se delatan.
- Un token manipulado o firmado con otra clave se rechaza.
- **Login con usuario inexistente y con contraseña incorrecta devuelven el mismo mensaje**: distinguirlos permitiría averiguar qué correos están registrados.
- El primer usuario que se registra queda como administrador; los siguientes, operadores.

El servidor **avisa ruidosamente al arrancar** si `CLAVE_SECRETA` no está
definida: con la clave por defecto, cualquiera que conozca el código puede firmar
tokens válidos.

> **Nota de seguridad:** el token se guarda en `localStorage`, suficiente para
> esta etapa pero expuesto a XSS. Antes de producción conviene pasar a una cookie
> `HttpOnly` emitida por el backend.

---

## Tanda 6 — WhatsApp + IA (la killer feature)

### Extracción con Claude (`app/ia/extraccion.py`)

Usa el SDK oficial de Anthropic sobre **`claude-opus-5`** con **structured
outputs** (`output_config.format`): el modelo queda obligado por un JSON Schema,
así que no hay que parsear texto libre ni reintentar cuando devuelve markdown
alrededor del JSON.

**El principio de diseño es que el LLM propone y el sistema dispone.** Nada de lo
que devuelve el modelo se da por bueno:

| Riesgo | Mitigación |
|---|---|
| Inventa un RUC | Se valida con el algoritmo módulo 10/11 del SRI |
| Inventa un precio de cero | Se detecta y se pide corrección |
| Da un precio "con IVA incluido" | Se despeja la base imponible: 115 con IVA 15% → 100.00 |
| Los totales del modelo no cuadran | Se **recalculan** con el motor SRI, se ignoran los suyos |
| El clasificador de seguridad declina | Se comprueba `stop_reason == "refusal"` **antes** de leer `content`, que en ese caso viene vacío |

### Orquestador (`app/ia/orquestador.py`)

**El modelo nunca emite un comprobante por su cuenta.** El flujo es: extraer →
validar → calcular → mostrar resumen → **esperar confirmación explícita** →
emitir. Un LLM que factura sin confirmar convierte una alucinación en un
documento tributario.

La conversación mantiene contexto 30 minutos, así el usuario puede completar
datos en varios mensajes. Cuando hay un borrador esperando confirmación, un "sí"
se interpreta directamente sin volver a llamar al modelo.

### Webhook (`app/routers/whatsapp.py`)

- **Verifica la firma HMAC-SHA256** de `X-Hub-Signature-256`. Sin esto, cualquiera que conozca la URL podría inyectar mensajes y hacer que el sistema facture. Si el secreto no está configurado, **rechaza** en lugar de aceptar a ciegas.
- Responde 200 de inmediato y procesa en segundo plano: Meta corta a los 20 segundos y reintenta, lo que duplicaría el procesamiento.
- Handshake `hub.challenge` para el registro de la URL en Meta.

### Soporte Técnico y paleta de comandos

Soporte con preguntas frecuentes buscables (centradas en los errores reales del
SRI: clave de acceso, firma inválida, dirección obligatoria, IVA mixto),
videotutoriales, formulario de ticket e historial.

**Paleta de comandos con `Ctrl/Cmd + K`** — el "Command Palette estilo Spotlight"
que pedía el plan: navegación a las 10 secciones, 5 acciones de creación y cambio
de tema, con navegación por flechas y búsqueda que ignora tildes.

---

## Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **86/86 pasando** |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |
| Motor de precios (markup vs margen, bordes) | 17/17 |
| Cálculo de comprobantes | 28/28 |
| Motor SRI (clave, XML, firma XAdES-BES) | 18/18 |
| API (validación, secuenciales, XML, RIDE) | 19/19 |
| Nota de Crédito y Retención | 11/11 |
| Autenticación (hashing, tokens, endpoints) | 18/18 |
| IA y WhatsApp (extracción, firma del webhook) | 20/20 |

---

## Estado del alcance del plan

| Módulo | Estado |
|---|---|
| Dashboard | 🟢 Completo según el plan |
| Receptores | 🟢 Completo, conectado al API |
| Artículos / Servicios | 🟢 Completo, conectado al API |
| Facturas | 🟢 Completo, conectado al API |
| Cotizaciones | 🟢 UI completa |
| Notas de Venta (RIMPE) | 🟢 UI completa |
| Liquidación de Compra | 🟢 UI completa |
| Guía de Remisión | 🟢 UI completa |
| Configuraciones | 🟢 UI completa + API |
| Soporte Técnico | 🟢 Completo |
| **Motor SRI** | 🟢 Clave, XML, firma, SOAP, RIDE, NC y retención |
| **WhatsApp + IA** | 🟢 Extracción, validación, orquestación, webhook |
| Envío real al SRI | 🟡 Falta certificado `.p12` acreditado |
| Notas de Crédito/Débito (UI) | 🔴 Backend listo, falta pantalla |

---

## Lo que queda

1. **Certificado `.p12` de entidad acreditada** — es el único bloqueante para emitir de verdad. Todo lo demás está construido y probado.
2. **Persistencia de las pantallas nuevas** (Configuraciones, Cotizaciones, Notas de Venta, Liquidaciones, Guías): la UI está completa; falta conectarlas al API como ya lo están Receptores, Artículos y Comprobantes.
3. **Antes de producción:**
   - Definir `CLAVE_SECRETA` (el servidor avisa si falta).
   - Mover el token de `localStorage` a cookie `HttpOnly`.
   - Migrar de SQLite a PostgreSQL (solo cambia `URL_BASE_DATOS`).
   - Contrastar la lista de cantones con la codificación oficial del INEC.
   - Definir el proveedor de WhatsApp Business API y configurar `WHATSAPP_SECRETO_APP`, `WHATSAPP_TOKEN_ACCESO` y `WHATSAPP_ID_NUMERO`.
4. **Multimodal en WhatsApp**: audio (Whisper) y foto de RUC/recibo (visión). El webhook ya distingue el tipo de mensaje y responde que aún no está disponible.
