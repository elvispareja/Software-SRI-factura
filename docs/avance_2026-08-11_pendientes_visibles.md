# Los cuatro pendientes que se veían en pantalla

Fecha: 11 de agosto de 2026

Cuatro cosas que un usuario notaba al usar el sistema: dos que **mentían** y dos
que faltaban. El hilo común es ese: una interfaz que promete algo y entrega otra
cosa hace más daño que una que no lo promete.

---

## 1. Cinco tarjetas que decían «Próximamente» y no lo eran

La pestaña Reportes de Cuentas pintaba cinco tarjetas con este cartel:

> *Próximamente. Este reporte requiere cuotas y recibos. Se generará en
> Excel/PDF cuando el módulo contable esté disponible.*

El texto era **falso desde hacía tandas**: `Cuota` y `Recibo` existían, con su
router, sus vencimientos y su reparto de centavos. El cartel se quedó escrito
cuando aún era cierto y nadie volvió a mirarlo.

Ahora las cinco consultan el backend: saldo por documento, agenda de cuotas,
recibos generados, rotación de cuentas e historial por contacto. Cada una con su
`GET` y su `GET /csv` — diez endpoints en `/api/cuentas/reportes/`.

Los badges decían «· Excel» y ahora dicen «· CSV». Lo que se genera es CSV con
`;` y BOM, que es justo lo que Excel en español abre bien. Prometer Excel y
entregar CSV era otra mentira pequeña.

## 2. El interruptor Cobrar/Pagar solo cambiaba rótulos

Es el peor de los cuatro, porque no era una carencia sino **un dato falso**. En
modo Pagar la pantalla seguía listando las cuotas y los recibos de las **ventas**,
con la etiqueta cambiada a «Proveedor». Quien mirase esa pantalla creería que
debe a sus proveedores exactamente lo que sus clientes le deben a él.

### Qué alimenta cada modo, y por qué

Esta era la única decisión de fondo del encargo, y no se impuso desde fuera: se
tomó leyendo los modelos.

**Cobrar** — dinero que entra. La deuda es el `Comprobante` de venta (`Factura`,
`Nota de Venta`, `Nota de Débito`) y el abono es el `Recibo`, que el propio
modelo define como «un cobro recibido».

**Pagar** — dinero que sale. Tiene **dos** orígenes y hacen falta los dos:

1. **`Gasto` saldado con `Egreso`.** Es la vía normal de una compra. Estos
   documentos no pasan por el SRI, así que no tienen `estado_sri` y cuentan
   todos.
2. **`Comprobante` de tipo `Liquidación de Compra`.** Es comprobante electrónico
   pero de compra: lo emite el comprador por el proveedor que no puede facturar,
   y deja una deuda con ese proveedor. Sus abonos van por `Cuota`/`Recibo`,
   porque es lo único que el módulo sabe crear contra un comprobante; ignorarlos
   la dejaría pendiente para siempre.

`Nota de Crédito` no entra en ninguno de los dos: no es una deuda, es la
anulación de otra. `Cotización` tampoco: no obliga a nadie.

### Cómo se comprobó

No con el resumen del código, sino ejecutándolo. Se crearon datos de los dos
lados —una factura de 300,00 en tres cuotas con una cobrada, y un gasto de
500,00 con 200,00 pagados— y se llamó a los cinco reportes en ambos modos:

```
REPORTE      MODO COBRAR                      MODO PAGAR
saldos        2 filas · Cliente   · FAVORITA   2 filas · Proveedor · PLASTLIT
agenda        4 filas · Cliente   · FAVORITA   2 filas · Proveedor · PLASTLIT
recibos       2 filas · Cliente   · FAVORITA   2 filas · Proveedor · PLASTLIT
rotacion      1 fila  · Cliente               1 fila  · Proveedor
historial     1 fila  · Cliente   · FAVORITA   1 fila  · Proveedor · PLASTLIT

>>> 5 de 5 reportes devuelven datos DISTINTOS en cada modo.
```

Y después en pantalla, con un navegador de verdad: la columna pasa de Cliente a
Proveedor con sus importes propios, y el cartel «Próximamente» ya no aparece.

### Tres trampas que se evitaron

**Doble conteo.** `crear_recibo` rellena `Recibo.comprobante_id` *también* cuando
hay cuota. Sumar `Cuota.cobrado` más todos los recibos del comprobante contaría
el mismo dinero dos veces. Lo abonado es `Cuota.cobrado` + los recibos **sin
cuota** y no anulados — la misma regla que aplica `_recalcular_comprobante`.

Se verificó **por mutación**: al quitar el filtro `cuota_id IS NULL` del
servicio, dos pruebas se ponen rojas. Una prueba que no se ha visto fallar no
prueba nada.

**Saldos históricos.** `Cuota.cobrado` es un acumulado a hoy y no sabe *cuándo*
entró el dinero. La rotación reconstruye el saldo con la fecha de los
`Recibo`/`Egreso`, que sí la tienen.

**Denominador cero.** Si en el período no se movió dinero, los días de
recuperación son `null`, no `0`. Un cero diría «se cobra al contado», que es lo
contrario de la verdad.

## 3. Exportación a PDF

La pantalla ya ofrecía un selector Excel/PDF, pero el PDF no existía. El pie lo
decía: *«PDF (próximamente — hoy CSV)»*. Era honesto, y por eso había que
quitarlo al construirlo: dejarlo ahora sería mentir al revés.

Un generador **genérico** en `servicios/reportes_pdf.py`, para no escribir uno
por reporte. Los estilos ReportLab que vivían dentro de `sri/ride.py` se
extrajeron a `sri/estilos_pdf.py`, así que el RIDE del comprobante y el PDF del
reporte comparten tipografía y acento en vez de divergir con el tiempo. El PDF
que genera `ride.py` no cambió, y sus pruebas lo siguen comprobando.

Dos detalles que costaron:

- **Paginación.** Inventario y receptores pueden traer miles de filas: se usa
  `LongTable` con `repeatRows` para que la cabecera se repita en cada página.
- **«Página N de M» necesita dos pasadas**, porque en la primera ReportLab no
  sabe el total. Se resuelve con una subclase de `canvas.Canvas` que acumula los
  estados de página y los pinta al guardar.

Si la empresa no está configurada, el PDF **no falla**: degrada a una cabecera
sin datos del emisor. Un reporte de gestión no se transmite al SRI, y bloquear
la descarga por eso es más molesto que útil.

Las filas del PDF y las del CSV salen de las mismas funciones. Escribirlas por
separado habría dejado el PDF desactualizado en silencio el día que alguien
añadiera una columna al CSV.

## 4. Los colores del JSX: de 232 a 13

El proyecto hizo un rediseño completo con tokens CSS y tema claro/oscuro, pero
quedaron **232 colores en hexadecimal escritos a mano dentro del JSX**, que no
participaban del tema.

No era solo suciedad. `ArticulosList.jsx` escribía `#0f1e33` sobre un panel cuyo
fondo en tema oscuro es `#111f37`: ese texto era **ilegible**. Un hex fijo
acierta en un tema y falla en el otro.

Cada sustitución se comprobó en **los dos temas**, que es la única forma de no
reproducir el mismo fallo con otro valor.

### Los 13 que quedan, quedan a propósito

Y por eso van con nombre y con su porqué en un comentario:

- `COLOR_PDF_FONDO` y `COLOR_PDF_TEXTO` en `Configuraciones.jsx`. No son colores
  de interfaz sino un ajuste del **documento que se imprime**: el PDF sale igual
  en papel tenga el usuario el tema que tenga, así que no pueden seguir al tema.
- Los colores de las gráficas y de los estados de comprobante, donde el color es
  **significado** —verde autorizado, rojo rechazado— y no decoración.

**Un color con significado no es un color de tema.**

---

## Cifras

| | Antes | Después |
|---|---:|---:|
| Pruebas de backend | 325 | **397** |
| Pruebas de frontend | 234 | **251** |
| **Total** | 559 | **648** |
| Hex en el JSX | 232 | **13** |
| Tarjetas de reporte muertas | 5 | **0** |

## Lo que sigue pendiente en esta zona

**La agenda suma cuotas, no documentos.** Un abono suelto contra un comprobante
que además tiene plan de cuotas no rebaja ninguna cuota, así que el saldo de la
agenda puede quedar por encima del que da el reporte de saldos. Imputar esos
abonos a las cuotas más antiguas es un criterio contable que nadie ha decidido
todavía, y por eso no se inventó: está documentado en el servicio para que quien
lo decida sepa dónde tocar.

**El reporte de saldos no filtra por período**, a propósito: una factura de hace
tres meses sigue debiéndose hoy, y acotarla por fecha escondería la deuda más
vieja, que es justo la que hay que ver.
