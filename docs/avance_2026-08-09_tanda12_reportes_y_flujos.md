# Avance — Tanda 12: reportes, nota de débito y pruebas de flujo completo

> **Fecha:** 9 de agosto de 2026
> **Estado:** completado y verificado — 467 pruebas (252 backend + 215 frontend), `oxlint` limpio, `npm run build` OK
> **Origen:** auditar qué faltaba y construirlo
> **Sigue diferido:** certificado acreditado y envío por correo (SMTP)

---

## 1. Lo que la auditoría encontró

Tres huecos que no se veían desde la interfaz, y dos defectos que ninguna prueba
existente podía detectar:

| Hallazgo | Por qué importaba |
|---|---|
| **No había reportes** | Sin ellos hay que sumar comprobantes a mano para declarar el 103 y el 104 |
| **El Dashboard inventaba sus cifras** | Derivaba todo de los datos de demostración: enseñaba las mismas ventas a todos |
| **La nota de débito no tenía XML** | Se podía capturar en pantalla y tenía su ruta, pero nunca llegaba al SRI |
| **La liquidación de compra viajaba como factura** | Salía con `codDoc` 01 en vez de 03: el SRI la registraría como venta, no como compra |
| **Todos los RIDE decían «FACTURA»** | Una nota de crédito impresa rotulada factura es un documento equivocado |

Los dos últimos aparecieron **al escribir las pruebas de flujo**, no antes.

---

## 2. Reportes

### Servicio (`app/servicios/reportes.py`)

Se calculan en SQL, no en la interfaz, por dos razones: los importes viven en
`Decimal` y traerlos al navegador para sumarlos los degrada a `float`, y un
negocio con miles de comprobantes no puede descargarlos todos para pintar una
tarjeta con el total del mes.

**La regla que gobierna todos:** solo cuentan los comprobantes **autorizados**.
Un borrador no es una venta y un anulado dejó de serlo. Mezclarlos daría cifras
que no cuadran con lo que el SRI tiene registrado, que es justo con lo que hay
que declarar.

La única excepción es `estado_sri`, cuyo propósito es precisamente enseñar
cuántos comprobantes quedaron a medias.

### Endpoints

```
GET /reportes/panel              todo lo que pinta el Dashboard, en una petición
GET /reportes/ventas             resumen del período
GET /reportes/ventas/por-tipo    desglose por tipo de comprobante
GET /reportes/ventas/por-mes     serie anual, con los doce meses siempre presentes
GET /reportes/clientes           quién factura más
GET /reportes/articulos          qué se vende más, por importe
GET /reportes/iva                base e IVA por tarifa — sustento del 104
GET /reportes/retenciones        retenciones por concepto — sustento del 103
GET /reportes/estado-sri         cuántos hay en cada estado
GET /reportes/{iva,retenciones,ventas}/csv
```

### Decisiones que vale la pena anotar

**El período se pide como año y mes sueltos, no como dos fechas.** Los reportes
tributarios son mensuales o anuales; aceptar rangos arbitrarios invitaría a
declarar un período que el SRI no reconoce. El reporte de IVA **exige** el mes:
el 104 es mensual y un acumulado anual no cabe en ningún casillero.

**Las retenciones se filtran por `periodo_fiscal`, no por fecha de emisión.** El
SRI declara por el período al que corresponde la retención, que puede no
coincidir con el día en que se emitió el comprobante.

**La serie mensual trae siempre los doce meses**, los vacíos en cero. Una
gráfica a la que le faltan meses se lee como «no hay datos», no como «no hubo
ventas».

**Cuentas por cobrar no se acota por período.** Una factura de hace tres meses
sigue debiéndose hoy; filtrarla por fecha escondería justo la deuda más vieja.

**El CSV se escribe con `;` y BOM.** El destino real de estos archivos es Excel
en español: con `,` mete todo en una columna, y sin BOM rompe las tildes.

**`extract` en vez de `strftime`** para agrupar por mes, para que la consulta
siga funcionando al migrar a PostgreSQL.

---

## 3. Nota de débito (`app/sri/xml_nota_debito.py`)

Existía la pantalla, la ruta y el tipo en la base de datos; faltaba el XML. Es
la contraria de la nota de crédito: en vez de disminuir el valor de un
comprobante anterior lo aumenta —intereses de mora, gastos de cobranza, un
recargo que no se facturó a tiempo—.

**Diferencia estructural:** no lleva `<detalles>`. Donde la nota de crédito
enumera los artículos que se devuelven, ésta declara `<motivos>`: una lista de
razones con su importe. Lo que se cobra de más es un concepto, no mercadería.
Por eso su XML no se puede derivar del de la factura cambiando etiquetas, y vive
en su propio módulo.

---

## 4. Dashboard conectado

Antes importaba `COMPROBANTES`, `CATALOGO_RECEPTORES` y `CATALOGO_ARTICULOS` de
`data/` y calculaba sobre ellos, con el mes fijado a `'2026-08'` en el código y
el usuario a `'Juan'`. Ahora consume `/reportes/panel` y saluda con el nombre de
la sesión.

Se quitó el panel de «Plan Emprendedor»: mostraba una cuota inventada que no
respaldaba nada. En su lugar hay un aviso **accionable**: cuántos comprobantes
están en borrador, pendientes o rechazados, con enlace a resolverlos.

**Sin servidor, el panel no cae a datos de demostración.** Los listados sí lo
hacen —para que la interfaz siga siendo navegable—, pero en un reporte de ventas
enseñar cifras inventadas es peor que no enseñar ninguna: nadie distingue un
total falso de uno real de un vistazo. De ahí el hook `useReporte`, separado de
`useRecurso` precisamente por eso.

---

## 5. Pantalla de Reportes

Tres pestañas —IVA en ventas, Retenciones, Ventas— con selector de año y mes y
exportación a CSV en cada una. El listado de retenciones separa lo retenido de
renta de lo retenido de IVA, que es como se declaran.

---

## 6. Verificación

| Chequeo | Antes | Ahora |
|---|---|---|
| **Backend** (pytest) | 189 | **252** |
| **Frontend** (vitest) | 158 | **215** |
| **Total** | 347 | **467** |
| `oxlint` | limpio | limpio |
| `npm run build` | OK | OK |

### Las 120 pruebas nuevas

- **Reportes (26)** — que solo cuenten autorizados, el período pedido, la serie
  de doce meses, los tops agrupados, el IVA separado por tarifa, las retenciones
  por período fiscal, el CSV con BOM y `;`, y los parámetros fuera de rango.
- **Contenido de los PDF (21)** — las que había solo comprobaban que el archivo
  empieza por `%PDF-`, lo cual pasa igual con un PDF en blanco. Ahora se extrae
  el texto y se verifica **qué dice**: la clave de acceso, el emisor, los
  totales, el aviso de ambiente de pruebas, y que el RIDE de la guía **no**
  imprima importes.
- **Flujos completos (16)** — crear → emitir → consultar → RIDE → XML para cada
  tipo, más los datos maestros (crear, editar, desactivar) y la comprobación de
  que lo emitido aparece en los reportes.
- **Frontend (57)** — adaptadores de reportes, el hook `useReporte`, y las
  primeras **pruebas de componentes** del proyecto: la pantalla de Reportes y el
  Dashboard se montan enteros y se comprueba lo que vería el usuario, incluido
  el formulario de retención (validaciones, cálculo, precarga del porcentaje).

### Tres expectativas mías que estaban mal

Se corrigieron en la prueba, no en el código:

1. El orden de `top_clientes` — BETA suma más que ACME; el orden era correcto.
2. El catálogo de conceptos de retención lleva un `id` por fila, porque muchos
   conceptos de la resolución no tienen código en la ficha técnica.
3. El aviso del formulario cita la resolución con el texto partido entre
   elementos.

### Un obstáculo del entorno

El proyecto vive en una carpeta sincronizada. Montar componentes con `recharts`
tardaba 66 s solo en importar, y Vitest aborta el worker a los 60 s (límite fijo
en su código, no configurable). Se resolvió pre-empaquetando las dependencias
pesadas con `test.deps.optimizer`: de 66 s a 10 s.

---

## 7. Qué queda

1. **El certificado `.p12` de entidad acreditada** — sigue siendo lo único que separa al sistema de una autorización real. No requiere cambios de código.
2. **Envío por correo del comprobante autorizado** (XML + RIDE adjuntos).
3. **Procesamiento de audio e imagen en WhatsApp.**
4. **Antes de producción:** `CLAVE_SECRETA`, PostgreSQL, `COOKIE_SAMESITE` si los dominios difieren, cifrado de la clave del `.p12` en un KMS, y contrastar los cantones con el INEC.
