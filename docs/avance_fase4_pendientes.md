# Fase 4 — Se cierran los pendientes y desaparecen los «Próximamente»

Fecha: 11 de agosto de 2026

Esta tanda no añade módulos nuevos: termina los que ya existían. El objetivo era
que dejara de haber pantallas que enseñan una estructura bonita sin datos
detrás. Se pasó de **17 secciones marcadas «Próximamente» a 6**, y las seis que
quedan son las que dependen de algo que no está en mi mano (hardware, roles
granulares, vídeo).

Por pedido expreso: **esta tanda no lleva tests**. Todo se verificó ejecutando la
aplicación —scripts contra el servidor levantado y Playwright contra la interfaz
real— y los tests se escribirán en la siguiente. Las suites que ya existían
siguen pasando enteras (292 backend, 234 frontend).

---

## 1. Reportes: las ocho pestañas con datos reales

Antes solo cuatro pestañas consultaban el backend. Ahora las ocho.

| Pestaña | Endpoint | Qué mide |
|---|---|---|
| Ventas | `/reportes/ventas` | (ya existía) |
| Compras | `/reportes/compras` | (ya existía) |
| Retenciones | `/reportes/retenciones` | (ya existía) |
| Impuestos | `/reportes/impuestos` | (ya existía) |
| Notas de venta y cotizaciones | `/reportes/notas-venta`, `/reportes/cotizaciones` | documentos que **no** son tributarios |
| Notas de crédito y débito | `/reportes/notas` | ajustes sobre facturas ya emitidas |
| Egresos | `/reportes/egresos` | salidas de caja agrupadas por tipo de gasto |
| Inventario | `/reportes/inventario` | existencias y su valor |
| Receptores | `/reportes/receptores` | padrón de clientes, proveedores y transportistas |

Dos decisiones que conviene tener escritas:

**El inventario se valora al costo, no al precio de venta.** El inventario es lo
que costó reponerlo, no lo que se espera cobrar por él. Valorarlo a precio de
venta infla el activo con un margen que todavía no se ha ganado.

**Las notas de venta y las cotizaciones van juntas y aparte del resto.** Ninguna
de las dos genera IVA ni entra en el formulario 104. Mezclarlas con las facturas
en la misma pestaña sería invitar a que alguien las declare.

Todas las pestañas descargan en CSV, que es lo que Excel abre directo. El PDF del
prototipo sigue pendiente.

Los reportes cuentan **solo comprobantes `Autorizado`**, igual que el resto del
sistema. Un documento en Borrador o Rechazado no existe para el SRI y no debe
existir para el reporte.

## 2. Envío del comprobante por correo

`backend/app/servicios/correo.py` — `enviar_comprobante()` adjunta el XML firmado
y el RIDE en PDF.

El XML viaja como `application/xml`, no como texto. Los clientes de correo
reescriben los finales de línea del texto plano, y un solo `\r\n` de más invalida
la firma XAdES: el receptor recibiría un archivo que el SRI ya no reconoce.

Si no hay `SMTP_SERVIDOR` configurado, la función levanta un `ErrorCorreo`
legible en lugar de fallar con un error de red a los treinta segundos.

Configuración en `.env`: `SMTP_SERVIDOR`, `SMTP_PUERTO`, `SMTP_USUARIO`,
`SMTP_CONTRASENA`, `SMTP_REMITENTE`, `SMTP_SSL`.

## 3. Cuentas por cobrar y por pagar

Modelos nuevos: `Cuota` y `Recibo`.

**Cuota y recibo son cosas distintas y por eso son tablas distintas.** La cuota es
lo que se debe y cuándo; el recibo es lo que efectivamente se cobró. Un cliente
puede abonar de a poco: tres recibos contra una misma cuota. Guardar solo un
campo «pagado» perdería esos tres movimientos de caja, que son justo los que hay
que poder explicar.

El saldo nunca se guarda, se calcula (`monto - cobrado`). Un saldo almacenado se
desincroniza en cuanto alguien anula un recibo.

Al dividir en cuotas, **el resto se acumula en la última**: 217,35 en tres cuotas
da 72,45 + 72,45 + 72,45 exacto, no 72,45 × 3 = 217,35 con un centavo bailando.

## 4. Facturación recurrente

`PlantillaRecurrente` + `LineaRecurrente`, con formulario de alta y edición.

`emitir_desde_plantilla()` genera un `Comprobante` normal en Borrador usando el
mismo `reservar_secuencial` que el resto: una factura recurrente no es un tipo
especial de factura, es una factura que alguien no tuvo que teclear.

Sobre el cálculo de la siguiente fecha:

```python
def sumar_meses(desde: date, meses: int) -> date:
    """El 31 de enero más un mes es el 28 de febrero, no el 3 de marzo."""
```

## 5. Listas de configuración

Cinco de las seis listas del prototipo ya tienen datos: zonas, vendedores,
leyendas, usuarios e impuestos. Las tres primeras las define el negocio y se
editan desde la pantalla.

Las otras dos son de solo lectura, cada una por su motivo:

- **Usuarios**: el alta pasa por el registro, que es donde se aplica el hash de
  la contraseña. Un alta directa desde aquí se saltaría ese paso.
- **Impuestos**: sus códigos viajan literalmente en el XML. Cambiar el código de
  IVA 15 % de `4` a otra cosa hace que el SRI rechace todos los comprobantes.

**Permisos** sigue sin backend: el sistema todavía no tiene roles granulares,
solo el campo `rol` del usuario. El banner ahora lo dice con esas palabras, en
lugar del genérico «aún no tiene endpoint».

## 6. Egresos y gastos

`TipoGasto`, `Gasto` y `Egreso`, con su pantalla.

**El gasto y el egreso no son lo mismo y por eso son tablas separadas.** El gasto
es la obligación (llegó la factura del proveedor); el egreso es la salida de caja
(se pagó). Entre uno y otro pueden pasar treinta días, y durante esos treinta
días el gasto existe y el dinero todavía está en la cuenta.

Un detalle que costó encontrar: al anular un pago, el gasto seguía marcado como
«Pagado» porque el estado se recalculaba antes de que la anulación llegara a la
base. Se resolvió con un `sesion.flush()` antes del recálculo.

## 7. Detalles de la interfaz

- **El Dashboard ya no inventa datos.** La tarjeta «Plan» mostraba cifras que no
  salían de ninguna parte; se sustituyó por `EstadoSriCard`, que muestra
  autorizados sobre total y el ambiente, y avisa cuando se está en pruebas —donde
  los documentos no tienen validez tributaria—. Un número falso pero creíble hace
  más daño que uno obviamente falso.
- Las acciones rápidas ya no desaparecían al no haber panel cargado.
- `useRecurso` reventaba con `datos.length` cuando el recurso no es una lista.
  `/configuracion/empresa` y `/configuracion/firma` devuelven un objeto, o `null`
  si no se han configurado; ahí «cuántos hay» es uno o ninguno, no `.length`.
- Se corrigió un identificador que tenía caracteres cirílicos mezclados
  (`isВосEstacion` → `enEstacionComprobante`). Compilaba, pero era imposible de
  teclear.
- El adaptador ponía `deducible` en falso por `Boolean(undefined)`, invirtiendo
  el valor por defecto del backend. Ahora `tipo.deducible ?? true`.
- Se separaron constantes a sus propios archivos (`estaciones.js`,
  `lib/saludo.js`, `Configuraciones/listas.js`) para que Fast Refresh no se
  queje al exportarlas junto a componentes.

---

## Lo que sigue sin estar

**Seis secciones «Próximamente»**, y ninguna es olvido:

| Sección | Por qué no está |
|---|---|
| Impresoras, terminales | Depende de hardware que no tengo delante |
| Permisos granulares | El modelo de usuario tiene un solo campo `rol` |
| Vídeos de Soporte | No hay vídeos grabados |
| Exportar a PDF | El CSV funciona hoy; el PDF es cosmética |

**El bloqueante de siempre**: el certificado `.p12` acreditado. Hay que comprarlo
a una entidad certificadora (Security Data, ANF, Banco Central). Sin él se puede
probar todo el flujo, pero lo que se firme no tiene validez ante el SRI.

**Los tests de esta tanda**, por pedido explícito. Sin cubrir todavía: los cuatro
grupos de reportes nuevos, inventario, receptores, SMTP, cuotas y recibos, y las
listas de configuración.

## Cómo se verificó

Sin tests, la comprobación fue ejecutar de verdad:

- Scripts contra el servidor levantado: las cuotas parten al centavo, un sobrepago
  se rechaza, el estado de la factura se recalcula, el CRUD de listas responde,
  inventario y receptores devuelven las cifras esperadas y sus CSV bajan.
- Playwright contra la interfaz, en modo claro y con un escuchador de errores de
  consola. Así aparecieron el `mesDate` usado antes de declararse, el mensaje de
  vacío duplicado y el fallo de `useRecurso` descrito arriba. Leer el código no
  los habría encontrado.
