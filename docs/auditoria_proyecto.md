# Auditoría del Proyecto: Sistema de Facturación SRI

> **Fecha:** 8 de agosto de 2026
> **Alcance:** Revisión completa de documentación, código frontend, mockups y estado general del proyecto.
> **Referencias:** [Plan de Arquitectura](./sistema_facturacion_plan.md) · [Prompt de Frontend](./claude_frontend_prompt.md)

---

## 1. Qué hay en el proyecto

| Carpeta | Contenido | Estado |
|---|---|---|
| `docs/` | Plan de arquitectura, prompt de frontend, FACTURA.pdf de referencia | Completo y muy bien especificado |
| `frontend/` | React 19 + Vite 8, ~3.100 líneas, 7 pantallas | Maqueta visual funcional, **sin lógica** |
| `Cloud World Office.dc.html` | Mockup HTML de 576 KB (+ backup v1) | Dirección de diseño **distinta** a la del React |
| `SRI Facturacion Videos de ejemplo/` | 13 videos del sistema de referencia (Factoa) | Material de referencia |
| Backend | — | **No existe** |

No es un repositorio git. Las dependencias del frontend ya están instaladas (08/08/2026). La carpeta vive en una ruta de Google Drive, pero **su sincronización está desactivada**, así que `node_modules` no representa un problema.

---

## 2. Frontend: lo que está construido

Stack exactamente como pedía `docs/claude_frontend_prompt.md`: React 19, Vite 8, CSS Modules (sin Tailwind), Framer Motion, Lucide, Recharts, React Router 7.

Siete rutas en `frontend/src/App.jsx`:

- `components/Layout/Layout.jsx` — sidebar colapsable animado, header, glassmorphism
- `pages/Dashboard/Dashboard.jsx` — 4 tarjetas de métricas + area chart
- Receptores: `pages/Receptores/ReceptoresList.jsx` + `ReceptoresForm.jsx` (3 tabs)
- Artículos: `pages/Articulos/ArticulosList.jsx` + `ArticulosForm.jsx` (3 tabs)
- Comprobantes: `pages/Comprobantes/ComprobantesList.jsx` + `FacturaForm.jsx`

El sistema de diseño en `src/index.css` está bien planteado: variables CSS, dark mode, acento naranja `#ef6c00`, utilidad `.glass-panel`. El CSS de las páginas es sólido (~1.400 líneas en los tres `.module.css`).

**La calidad visual es buena. El problema es que debajo no hay nada.**

---

## 3. Problemas concretos encontrados

### 3.1. Datos y estado (crítico)

- **Todo es `MOCK_DATA` hardcodeado.** No existe `src/api/`, `src/services/`, `src/hooks/` ni contexto global. Cero llamadas de red.
- **Los buscadores no buscan.** En `ReceptoresList.jsx:56` y `ComprobantesList.jsx:81`, `searchTerm` se guarda en estado pero nunca filtra el array. Los botones "Filtros Avanzados", "Descargar" e "Importar" no tienen `onClick`.

### 3.2. FacturaForm — los cálculos están mal

Es la pantalla más crítica del sistema y tiene tres fallos que impedirían emitir una factura real:

1. **El IVA se aplica a todo el subtotal al 15%** (`FacturaForm.jsx:20`), ignorando el campo `iva` de cada ítem. Un producto con IVA 0% o exento facturaría mal — y el SRI rechaza el XML si `totalConImpuestos` no cuadra.
2. **Los inputs de la grilla usan `defaultValue`**, no están controlados (`FacturaForm.jsx:106-108`). Se puede escribir cantidad 50 y el total sigue diciendo $1.200,00.
3. **`setItems` nunca se llama.** No se pueden agregar filas (el buscador de productos es decorativo) ni eliminarlas (el botón de papelera no hace nada). El descuento por línea tampoco entra en el cálculo.

### 3.3. ArticulosForm — misma raíz

El `% Utilidad` es `defaultValue` no controlado (`ArticulosForm.jsx:170`), así que cambiar el porcentaje no recalcula el precio; solo reacciona al costo. Además la fórmula `costo + costo*util/100` es **markup sobre costo**, no margen de utilidad — dos cosas distintas que suelen confundirse y descuadran los precios.

### 3.4. Desvíos respecto al plan

- **La Dirección está en el tab equivocado.** El plan la lista como obligatoria (es requisito del XML del SRI), pero está en "Datos Adicionales" (`ReceptoresForm.jsx:132`).
- **El tab "Configuración Comercial" está incompleto:** tiene 3 campos, el plan pide 7 (método cancelación, vendedor, lista de precios, zona, % descuento, código, crédito máximo). Faltan también teléfono 2 y correos 2/3.
- **El Dashboard no es el del plan.** Muestra Ventas/Compras/Gastos/Utilidad; el plan pide Facturado del mes, Documentos del mes, Ticket promedio, Documentos del año, **barra de estado del plan** (21/30 documentos), **Quick Actions** y un **donut de distribución por tipo de documento**. Nada de eso está.
- **No es mobile-first**, pese a ser requisito explícito. `Layout.module.css` no tiene una sola media query: `height: 100vh`, `overflow: hidden` y sidebar fijo. En un celular el sidebar se come la pantalla y las tablas se desbordan.

### 3.5. Detalles de arranque

- `src/App.css` es residuo del template de Vite (`.counter`, `.hero`) y ni siquiera se importa — se puede borrar.
- `frontend/README.md` sigue siendo el del template.
- `index.html:7`: `<title>frontend</title>`, `lang="en"`, y **la fuente Inter nunca se carga** (está declarada en el CSS pero no hay `<link>` a Google Fonts, así que se ve con la fuente del sistema).
- El botón de Configuraciones del sidebar (`Layout.jsx:83`) no navega a ningún lado.
- No hay rutas de edición (`/receptores/:id`), solo `/nuevo`.

---

## 4. Conflicto de diseño a resolver

Los dos `.dc.html` son un mockup **muy completo** de una dirección visual totalmente distinta:

| | React actual | Mockup `.dc.html` |
|---|---|---|
| Tema | Oscuro `#0f111a` | Claro |
| Acento | Naranja `#ef6c00` | Azul `#2563b0` |
| Tipografía | Inter (no cargada) | Plus Jakarta Sans |

Y el mockup cubre pantallas que el React **no tiene**: WhatsApp AI Assistant, Cotizaciones, Proveedores, Notas de Venta, Notas de Crédito/Débito, Guía de Remisión, Configuraciones.

**Hay que decidir cuál manda antes de escribir más CSS, o se duplicará trabajo.**

---

## 5. Cobertura real vs. alcance aprobado

| Módulo del plan | Estado |
|---|---|
| Dashboard | 🟡 Parcial (faltan quick actions, donut, estado del plan, KPIs correctos) |
| Receptores | 🟡 UI sin lógica, campos incompletos, sin Proveedores/Transportistas |
| Artículos | 🟡 UI sin lógica, faltan unidad de medida, ubicación/bodega, stock |
| Facturas | 🟡 UI con cálculos rotos |
| Configuraciones (empresa, firma .p12) | 🟡 UI completa, falta persistencia |
| Cotizaciones / Notas de Venta | 🔴 No existe |
| Liquidación de Compra / Guía Remisión / NC-ND / Retenciones | 🔴 No existe |
| Soporte Técnico | 🔴 No existe |
| **Motor SRI** (clave acceso, XML, firma XAdES-BES, SOAP) | 🟢 **Funcionando, 18 tests** |
| Motor SRI: envío real al ambiente de pruebas | 🟡 Falta certificado acreditado |
| Motor SRI: RIDE (PDF) y demás tipos de comprobante | 🔴 No existe |
| **WhatsApp + IA** (la killer feature) | 🔴 No existe |

> Estado actualizado tras las tandas 1 y 2 (ver §8). El Motor SRI —el mayor
> riesgo del proyecto— ya genera, firma y autoverifica comprobantes; falta un
> certificado `.p12` de entidad acreditada para el envío real.

---

## 6. Recomendación de próximos pasos

El riesgo real del proyecto no está en la UI, está en el **Motor SRI** (Fase 2): generar el XML según ficha técnica, firmarlo con XAdES-BES desde un `.p12`, y sobrevivir a los WebServices de recepción/autorización. Eso es lo que hunde proyectos de facturación electrónica, y es lo único que aún no se ha tocado. La UI bonita sin motor no factura.

Orden propuesto:

1. **Decidir stack de backend y dirección visual** (las dos decisiones bloqueantes).
2. **Convertir el repo en git** y sacar `node_modules` de la ruta de Google Drive.
3. **Prueba de concepto del Motor SRI**: un script que arme, firme y envíe una factura al ambiente de PRUEBAS del SRI y reciba autorización. Sin UI. Si eso funciona, el proyecto es viable.
4. **En paralelo, arreglar FacturaForm**: motor de cálculo con IVA por línea y descuentos, inputs controlados, agregar/eliminar filas. Es la pieza de UI que el resto reutiliza (Cotización, Nota de Venta y Liquidación son la misma pantalla con otra cabecera).
5. **Capa de datos** (`src/api` + hooks) y recién ahí conectar los listados.

---

## 7. Checklist de decisiones

- [x] **Stack de backend: Python + FastAPI** *(decidido 08/08/2026)*
- [x] **Dirección visual: tema dual claro/oscuro con selector** *(decidido 08/08/2026)*
- [x] **Sincronización de Google Drive desactivada en esta carpeta** *(08/08/2026 — ya no hay riesgo con `node_modules`)*
- [ ] Base de datos concreta (PostgreSQL / Supabase)
- [ ] Inicializar git
- [ ] Proveedor de WhatsApp Business API (Meta Graph directo vs. intermediario)
- [ ] Librería de firmado XAdES-BES en Python (`signxml` / `xmlsec`)

---

## 8. Registro de avances

| Fecha | Avance | Resuelve | Detalle |
|---|---|---|---|
| 08/08/2026 | Motor de cálculo de comprobantes | §3.2 y parte de §3.1 | [avance_2026-08-08_motor_calculo.md](./avance_2026-08-08_motor_calculo.md) |
| 08/08/2026 | Tanda 1 — Cimientos: tema dual, responsive, listados funcionales | §3.1, §3.4 (responsive), §3.5 | [avance_2026-08-08_tanda1_cimientos.md](./avance_2026-08-08_tanda1_cimientos.md) |
| 08/08/2026 | Tanda 2 — Configuraciones, Receptores completo y **Motor SRI** (Python) | §3.4, §5 (Configuraciones, Motor SRI) | [avance_2026-08-08_tanda2_motor_sri.md](./avance_2026-08-08_tanda2_motor_sri.md) |
| 08/08/2026 | Tandas 3–6 — Frontend completo, API con persistencia, RIDE, NC/Retención, autenticación y **WhatsApp + IA** | §3.3, §5 (todo el alcance restante) | [avance_2026-08-08_tandas3-6.md](./avance_2026-08-08_tandas3-6.md) |
| 08/08/2026 | Tanda 7 — Persistencia de todos los documentos, secuenciales por tipo y Notas de Crédito/Débito | §5 (Fase 5 completa) | [avance_2026-08-08_tanda7_persistencia.md](./avance_2026-08-08_tanda7_persistencia.md) |
| 08/08/2026 | Tanda 8 — Formularios conectados al API, firma `.p12` persistida y sesión en cookie `HttpOnly` | §5, deuda de seguridad de la §7 | [avance_2026-08-08_tanda8_cableado.md](./avance_2026-08-08_tanda8_cableado.md) |
| 08/08/2026 | Tanda 9 — **Emisión real al SRI**: firma con el certificado guardado, transmisión y reconsulta | §5 (Fase 2 completa) | [avance_2026-08-08_tanda9_emision.md](./avance_2026-08-08_tanda9_emision.md) |
| 08/08/2026 | Tanda 10 — Control de versiones, **guías y retenciones al SRI** y WhatsApp emitiendo de verdad | §5 (todos los comprobantes transmiten), §7 (repositorio) | [avance_2026-08-08_tanda10_guias_retenciones.md](./avance_2026-08-08_tanda10_guias_retenciones.md) |
| 09/08/2026 | Tanda 11 — RIDE y reconsulta de guías y retenciones; tabla de retención al día con la **resolución NAC-DGERCGC26-00000009** | §5 (ciclo completo en los tres comprobantes) | [avance_2026-08-09_tanda11_ride_reconsulta_retenciones.md](./avance_2026-08-09_tanda11_ride_reconsulta_retenciones.md) |
| 09/08/2026 | Tanda 12 — **Reportes** (103, 104, ventas), Dashboard conectado al API, XML de **nota de débito** y pruebas de flujo completo | §5, §6 (reportes, que faltaban por completo) | [avance_2026-08-09_tanda12_reportes_y_flujos.md](./avance_2026-08-09_tanda12_reportes_y_flujos.md) |
| 10/08/2026 | **Rediseño Cloud Factur AI** sobre el prototipo del repositorio, y los módulos que faltaban: egresos, anticipos y facturación recurrente | §4 (el conflicto de diseño que quedó sin resolver), §5 | [avance_2026-08-10_cloud_factur_ai.md](./avance_2026-08-10_cloud_factur_ai.md) |

> Los documentos de avance llevan el detalle completo. Esta auditoría se mantiene como el estado general del proyecto.
