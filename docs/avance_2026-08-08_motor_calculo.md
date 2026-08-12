# Avance: Motor de cálculo de comprobantes

> **Fecha:** 8 de agosto de 2026
> **Resuelve:** puntos 3.2 y parte del 3.1 de la [Auditoría del Proyecto](./auditoria_proyecto.md)
> **Estado:** completado y verificado

---

## 1. Decisiones que enmarcan este avance

| Decisión | Elegido |
|---|---|
| Stack de backend | **Python + FastAPI** (incluido el firmado XAdES-BES) |
| Dirección visual | **Tema dual claro/oscuro con selector** |
| Primer paso de implementación | **Motor de cálculo de la factura** |

---

## 2. Qué se construyó

### 2.1. Capa de cálculo pura (sin React)

Separada de la UI a propósito: la reutilizarán Cotización, Nota de Venta y Liquidación de Compra, y es la misma fuente de verdad que después replicará el backend en Python para armar el XML.

| Archivo | Rol |
|---|---|
| `frontend/src/lib/sri/impuestos.js` | Catálogo de tarifas IVA con los códigos de la tabla 17 de la ficha técnica del SRI (`4`=15%, `5`=5%, `0`=0%, `6`=No objeto, `7`=Exento) |
| `frontend/src/lib/sri/calculoComprobante.js` | `redondear`, `aNumero`, `calcularLinea`, `calcularComprobante`, `validarComprobante`, `formatearMoneda` |
| `frontend/src/data/catalogoArticulos.js` | Catálogo mock compartido + `buscarArticulos` (ignora tildes y mayúsculas) |

`ArticulosList.jsx` ahora lee de ese catálogo compartido, en vez de tener su propio `MOCK_DATA`. Así no quedan dos listas que se desincronicen.

### 2.2. Correcciones en `FacturaForm.jsx`

Los tres bugs reportados en la auditoría, resueltos:

1. **IVA por línea.** Se calcula según la tarifa de cada ítem y se agrupa por `codigoPorcentaje`, tal como exige `totalConImpuestos` en el XML. Antes aplicaba 15% ciego a todo el subtotal.
2. **IVA sobre la base imponible** (bruto − descuento), no sobre el bruto.
3. **Inputs controlados.** Cantidad, precio unitario, % descuento y tarifa de IVA recalculan el total al instante.
4. **Agregar y eliminar filas funciona.** Buscador con resultados en vivo (Enter agrega el primero, Escape limpia), botón de "línea libre", y el ícono de papelera elimina de verdad. Si el artículo ya está en la grilla, suma una unidad en vez de duplicar la fila.

Mejoras que salieron de paso:

- El resumen lista **solo las tarifas realmente usadas**, en lugar de un "Subtotal 15% / Subtotal 0%" fijo.
- `validarComprobante` **deshabilita "Emitir al SRI"** y explica por qué (sin ítems, cantidad en cero, total en cero).
- Estado vacío cuando no hay ítems.
- El panel de totales deja de ser sticky bajo 1100px (primer paso hacia el responsive pendiente).

---

## 3. Detalles técnicos que conviene recordar

**Redondeo.** Usa notación exponencial en vez de `Math.round(valor * 100) / 100`, porque el escalado binario falla en los casos de frontera: `Math.round(1.005 * 100)` devuelve `100` (→ 1.00) cuando el SRI espera 1.01. El redondeo se aplica en cada paso, no solo al final, porque el XML declara los valores ya redondeados y el SRI valida que cuadren.

**Campos numéricos como texto.** Cantidad, precio y descuento se guardan como string en el estado y los interpreta el motor. Así el usuario puede borrar el campo o escribir `1.` sin que el input le pelee. También acepta coma decimal (`2,5`).

**Entradas basura acotadas.** Descuento fuera de 0–100 se recorta, cantidades y precios negativos van a 0, y un código de IVA desconocido cae en la tarifa por defecto. El motor nunca devuelve `NaN`.

**Orden 1:1.** `calcularComprobante` conserva el orden de las líneas, así que la grilla itera sobre el estado crudo y toma el cálculo por índice — sin búsquedas O(n²) dentro del render.

---

## 4. Verificación

| Chequeo | Resultado |
|---|---|
| Aserciones del motor (redondeo de frontera, descuentos, tarifas mixtas, entradas basura) | 28/28 OK |
| `npm run build` | OK |
| `oxlint` | Sin hallazgos |
| Dev server | Levanta y sirve correctamente |

**Caso de regresión concreto:** una factura con 1 laptop a $1.200 (IVA 15%) + 10 panes a $1,85 (IVA 0%):

| | Antes | Ahora |
|---|---|---|
| IVA | $182,78 ❌ | **$180,00** ✅ |
| Total | $1.401,28 ❌ | **$1.398,50** ✅ |

---

## 5. Pendiente en esta pantalla

- El receptor sigue siendo estático (`CONSUMIDOR FINAL` hardcodeado). Se conecta cuando exista el API.
- La forma de pago no alimenta el cálculo todavía.
- Falta el responsive completo de la grilla en móvil.

---

## 6. Siguiente paso propuesto

**PoC del Motor SRI en Python:** un script aislado, sin UI, que arme el XML de una factura, lo firme con un `.p12` y lo envíe al ambiente de PRUEBAS del SRI hasta recibir autorización. Es el mayor riesgo del proyecto y ahora el stack ya está decidido.

Alternativa si se prefiere seguir en el frontend: aplicar los tokens del tema dual claro/oscuro mientras el CSS está fresco.
