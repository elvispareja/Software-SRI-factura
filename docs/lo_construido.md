# Todo lo que se ha construido

Inventario completo del sistema al **11 de agosto de 2026**, contado del
repositorio. Este documento responde a «¿qué hay hecho?»; su complemento es
[`estado_del_proyecto.md`](estado_del_proyecto.md), que responde a «¿qué falta?».

---

## De un vistazo

Un sistema de **facturación electrónica para el SRI del Ecuador**: emite los
siete comprobantes electrónicos oficiales, los firma, los envía, gestiona el
inventario y los receptores, lleva las cuentas por cobrar y por pagar, saca los
reportes que hacen falta para declarar, y permite facturar escribiendo por
WhatsApp.

| | |
|---|---|
| Endpoints | 118 |
| Modelos de base de datos | 24 |
| Pantallas | 17 |
| Código | 11.325 líneas Python · 15.753 líneas JS/JSX |
| Pruebas | 526 — 292 backend (pytest) · 234 frontend (vitest) |
| Tandas de trabajo | 16 commits, del 08 al 11 de agosto de 2026 |

---

## 1. El motor del SRI

Es el corazón del sistema y lo más difícil de lo construido. Vive en
`backend/app/sri/`.

### Los siete comprobantes electrónicos

Cada uno con su generador de XML, su esquema y su RIDE:

| Documento | Código (tabla 3) | Archivo |
|---|---|---|
| Factura | `01` | `xml_factura.py` |
| Liquidación de compra | `03` | `xml_factura.py` |
| Nota de crédito | `04` | `xml_nota_credito.py` |
| Nota de débito | `05` | `xml_nota_debito.py` |
| Guía de remisión | `06` | `xml_guia_remision.py` |
| Comprobante de retención | `07` | `xml_retencion.py` |

Y dos documentos **no tributarios** —cotización y nota de venta— que el negocio
usa pero el SRI no recibe, y que por eso se llevan aparte de los demás.

### La clave de acceso

`clave_acceso.py` construye los 49 dígitos y calcula su dígito verificador con
módulo 11. Es lo que identifica el comprobante ante el SRI: si un solo dígito
está mal, el documento se rechaza antes de que nadie lo lea.

### La firma XAdES-BES

`firma.py`. Firma el XML con el certificado `.p12` del contribuyente, en el
formato exacto que el SRI valida. Es la parte donde más cosas pueden salir mal en
silencio, porque un XML mal firmado se ve idéntico a uno bien firmado.

### El envío y la consulta

`servicios.py` habla con los dos webservices SOAP del SRI: **recepción** (que
acepta o devuelve el comprobante) y **autorización** (que lo aprueba o lo
rechaza). Son dos pasos separados y con resultados distintos: que el SRI reciba
un comprobante no significa que lo haya autorizado.

Los estados que maneja el sistema son los de verdad: `Borrador`, `Firmado`,
`Recibido`, `Autorizado`, `Rechazado`, `Devuelto`, `Anulado`.

### El RIDE

`ride.py` genera con ReportLab la **Representación Impresa del Documento
Electrónico**: el PDF que se entrega al cliente. Lleva el número de autorización,
la clave de acceso, la fecha y el desglose de impuestos, porque sin eso no es un
RIDE válido.

### Los códigos de retención

`codigos_retencion.py` — contrastados con la resolución **NAC-DGERCGC26-00000009**
vigente desde el 01/03/2026. El único concepto que queda por confirmar (ISD) está
marcado con `verificado=False` en el propio archivo, para que nadie lo dé por
bueno sin mirarlo.

### La identificación

`identificacion.py` valida cédulas, RUC y pasaportes ecuatorianos con sus
algoritmos reales, no con una expresión regular de longitud.

---

## 2. Los datos: 24 modelos

`backend/app/modelos_db.py`. El dinero se guarda en `Numeric(14,6)`, nunca en
coma flotante.

**Identidad y configuración** — `Usuario`, `Empresa`, `Establecimiento`,
`PuntoEmision`, `CuentaBancaria`, `FirmaElectronica`, `SecuencialDocumento`,
`ListaAuxiliar`

**Catálogos** — `Receptor` (clientes, proveedores y transportistas en una sola
tabla, distinguidos por rol), `Articulo`

**Comprobantes** — `Comprobante`, `DetalleComprobante`, `GuiaRemision`,
`ItemGuiaRemision`, `Retencion`, `DetalleRetencion`

**Dinero que sale** — `TipoGasto`, `Gasto`, `Egreso`

**Dinero que entra** — `Anticipo`, `Cuota`, `Recibo`

**Automatización** — `PlantillaRecurrente`, `LineaRecurrente`

### Tres separaciones que parecen redundantes y no lo son

**Gasto ≠ Egreso.** El gasto es la obligación (llegó la factura del proveedor);
el egreso es la salida de caja (se pagó). Entre uno y otro pueden pasar treinta
días, y durante esos treinta días el gasto existe y el dinero sigue en la cuenta.

**Cuota ≠ Recibo.** La cuota es lo que se debe y cuándo; el recibo es lo que
efectivamente se cobró. Un cliente puede abonar de a poco: tres recibos contra
una misma cuota. Un solo campo «pagado» perdería esos tres movimientos de caja,
que son justo los que hay que poder explicar.

**El saldo nunca se guarda, se calcula.** `monto - cobrado`. Un saldo almacenado
se desincroniza en cuanto alguien anula un recibo.

---

## 3. Los 118 endpoints

| Router | Endpoints | Qué cubre |
|---|---|---|
| `reportes` | 22 | los ocho reportes y sus descargas en CSV |
| `configuracion` | 18 | empresa, establecimientos, puntos de emisión, cuentas, firma, listas |
| `egresos` | 14 | gastos, tipos de gasto y egresos |
| `catalogos` | 10 | receptores y artículos |
| `comprobantes` | 10 | facturas, notas de crédito y débito, liquidaciones, cotizaciones, notas de venta |
| `retenciones` | 9 | emisión, consulta y RIDE |
| `guias` | 8 | guías de remisión |
| `recurrentes` | 8 | plantillas y emisión automática |
| `anticipos` | 6 | anticipos de clientes |
| `cuentas` | 6 | cuotas y recibos |
| `autenticacion` | 4 | registro, login, sesión, logout |
| `whatsapp` | 3 | webhook de Meta y envío |

---

## 4. Las 17 pantallas

Diseñadas sobre el sistema visual **Cloud Factur AI**, extraído del prototipo que
dejaste en el repositorio: paleta naranja `#f26a35` con el degradado de marca,
barra lateral oscura, paneles de radio 18 px. Tema claro y oscuro.

**Entrada** — Login, Dashboard

**Catálogos** — Receptores, Artículos/Servicios

**Comprobantes** — Comprobantes (facturas, NC, ND), Cotizaciones, Notas de Venta,
Liquidaciones, Guías de remisión, Retenciones

**Dinero** — Egresos (con gastos), Anticipos, Cuentas por cobrar y por pagar

**Automatización** — Recurrentes

**Análisis** — Reportes

**Sistema** — Configuraciones, Soporte Técnico

---

## 5. Los ocho reportes

Todos con descarga en CSV, que es lo que Excel abre directo.

| Reporte | Para qué |
|---|---|
| Ventas | lo facturado, con su IVA |
| Compras | lo comprado |
| Retenciones | soporte del **formulario 103** |
| Impuestos | soporte del **formulario 104** |
| Notas de venta y cotizaciones | documentos que **no** son tributarios |
| Notas de crédito y débito | ajustes sobre facturas ya emitidas |
| Egresos | salidas de caja agrupadas por tipo de gasto |
| Inventario | existencias y su valor |
| Receptores | padrón de clientes, proveedores y transportistas |

### La regla que gobierna todos los reportes

**Solo cuentan los comprobantes `Autorizado`.** Un documento en Borrador o
Rechazado no existe para el SRI, y por tanto no debe existir para el reporte. Un
reporte que sume borradores lleva a declarar de más.

### Y dos decisiones más

**El inventario se valora al costo, no al precio de venta.** El inventario es lo
que costó reponerlo, no lo que se espera cobrar por él. Valorarlo a precio de
venta infla el activo con un margen que aún no se ha ganado.

**Las notas de venta y las cotizaciones van aparte.** Ninguna genera IVA ni entra
en el 104. Mezclarlas con las facturas sería invitar a que alguien las declare.

---

## 6. WhatsApp con IA

`backend/app/ia/` + `routers/whatsapp.py`.

Se escribe *«hazle una factura a Juan Pérez por 3 sillas a 45 dólares»* y el
sistema extrae los datos, encuentra al cliente y al artículo en los catálogos, y
deja la factura lista.

**Dos proveedores de IA, deliberadamente**: Gemini (`gemini-2.5-flash`) para
extraer datos del texto, y Anthropic para el OCR de las imágenes. Cada uno hace
lo que hace mejor.

El webhook verifica la **firma HMAC de Meta** antes de procesar nada, porque un
webhook sin verificar es una puerta abierta para que cualquiera emita facturas a
tu nombre.

---

## 7. Facturación recurrente

`PlantillaRecurrente` + `LineaRecurrente`, con su pantalla y su formulario.

`emitir_desde_plantilla()` genera un `Comprobante` normal en Borrador usando el
mismo `reservar_secuencial` que el resto: una factura recurrente no es un tipo
especial de factura, es una factura que alguien no tuvo que teclear.

El cálculo de la siguiente fecha tiene su detalle:

```python
def sumar_meses(desde: date, meses: int) -> date:
    """El 31 de enero más un mes es el 28 de febrero, no el 3 de marzo."""
```

---

## 8. Seguridad

- Contraseñas con hash, nunca en claro.
- La contraseña del certificado `.p12` se **cifra** con una clave derivada de
  `CLAVE_SECRETA` (`servicios/cifrado.py`). Si `CLAVE_SECRETA` cambia, esas
  contraseñas dejan de poder descifrarse y hay que volver a subir el `.p12` — por
  eso el README lo advierte en un recuadro.
- Sesión por **cookie HttpOnly**, no por token en `localStorage`, que es
  accesible desde cualquier script inyectado.
- CORS restringido por `ORIGENES_PERMITIDOS`.
- El servidor **avisa al arrancar** si `CLAVE_SECRETA` sigue en el valor de
  desarrollo, y la exige en producción (`AMBIENTE=2`).
- Firma HMAC verificada en el webhook de WhatsApp.

---

## 9. Envío por correo

`servicios/correo.py` — `enviar_comprobante()` adjunta el XML firmado y el RIDE.

El XML viaja como `application/xml`, **no como texto**. Los clientes de correo
reescriben los finales de línea del texto plano, y un solo `\r\n` de más invalida
la firma XAdES: el receptor recibiría un archivo que el SRI ya no reconoce.

Sin `SMTP_SERVIDOR` configurado, la función levanta un error legible en lugar de
fallar con un timeout de red a los treinta segundos.

---

## 10. Las 526 pruebas

**Backend — 292 pruebas** en 16 archivos: motor del SRI, emisión, guías,
retenciones, RIDE, documentos, reportes, egresos, recurrentes, autenticación,
configuración y seguridad, IA de WhatsApp, y flujos completos de punta a punta.

**Frontend — 234 pruebas** en 18 archivos: cálculo de comprobantes, impuestos,
identificación, precios, adaptadores de API, hooks y tres pantallas.

---

## 11. Herramientas de apoyo

`backend/scripts/`:

| Script | Qué hace |
|---|---|
| `sembrar_datos.py` | Puebla la base con datos de demostración para poder probar |
| `generar_certificado_pruebas.py` | Crea un `.p12` autofirmado para desarrollo |
| `generar_manual.py` | Regenera `docs/manual_de_uso.pdf` |
| `poc_factura.py` | Prueba de concepto del flujo completo contra el SRI |

El manual se dibuja con primitivas de ReportLab en lugar de incrustar capturas de
pantalla, para que se regenere solo cuando la interfaz cambie.

---

## 12. La documentación

23 documentos en `docs/`, uno por tanda de trabajo, cada uno con las decisiones
tomadas **y su porqué** — que es la parte que no se puede reconstruir leyendo el
código después.

Los cuatro de entrada:

| Documento | Contenido |
|---|---|
| [manual_de_uso.pdf](manual_de_uso.pdf) | Manual ilustrado para quien usa el sistema |
| [estado_del_proyecto.md](estado_del_proyecto.md) | Qué falta y en qué orden |
| [lo_construido.md](lo_construido.md) | Este documento |
| [auditoria_proyecto.md](auditoria_proyecto.md) | Índice de todos los avances |

---

## Cómo se llegó hasta aquí

Dieciséis tandas de trabajo, del 8 al 11 de agosto de 2026:

| Tanda | Qué trajo |
|---|---|
| Cimientos | Estructura, modelos, autenticación |
| Motor SRI | Clave de acceso, XML, firma, envío |
| Cálculo | Motor de impuestos y totales |
| Persistencia | Base de datos y secuenciales |
| Cableado | Frontend conectado al backend |
| Emisión | Flujo completo de factura |
| Guías y retenciones | Los dos comprobantes que faltaban |
| RIDE y reconsulta | PDF y consulta de estado |
| Reportes y flujos | Los primeros reportes, nota de débito |
| Pruebas de frontend | 158 pruebas nuevas con vitest |
| Manual en PDF | Tutorial ilustrado |
| **Rediseño Cloud Factur AI** | Sistema visual del prototipo |
| Módulos del prototipo | Egresos, anticipos, recurrentes |
| Reportes ampliados | Notas de venta, cotizaciones, NC/ND, egresos |
| Correo y recurrentes | SMTP y formulario de plantillas |
| Cuentas y configuración | Cuotas, recibos y listas auxiliares |
| Inventario y receptores | Los dos últimos reportes |

**Un momento del camino que conviene tener escrito**: en la tanda del rediseño se
construyó una dirección visual propia en lugar de partir del prototipo
`Cloud World Office.dc.html` que ya estaba en el repositorio. Se corrigió
extrayendo el sistema de diseño real del prototipo y construyendo además los
siete módulos que este cubría y no existían. Lo que había que hacer estaba en el
repositorio desde el principio.

---

## Cómo verificar estas cifras

```bash
grep -rhoE '@router\.(get|post|put|patch|delete)' backend/app/routers/*.py | wc -l   # 118
grep -rhcE '^class [A-Z]' backend/app/modelos_db.py                                   # 24
ls frontend/src/pages | wc -l                                                         # 17
cd backend && .venv/Scripts/python -m pytest -q                                       # 292
cd frontend && npx vitest run                                                         # 234
```
