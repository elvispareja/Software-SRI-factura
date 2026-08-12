# Avance — Tanda 10: control de versiones, guías y retenciones al SRI, WhatsApp emitiendo

> **Fecha:** 8 de agosto de 2026
> **Estado:** completado y verificado — 174 tests de backend, `oxlint` limpio, `npm run build` OK
> **Alcance:** los tres comprobantes que quedaban sin transmitir ya viajan al SRI, y el asistente de WhatsApp emite de verdad
> **Diferido a petición del usuario:** el envío por correo (SMTP) y el certificado de entidad acreditada

---

## 1. Control de versiones

El proyecto no estaba versionado. Se inicializó el repositorio con:

- **`.gitignore`** — excluye `node_modules/`, `.venv/`, `dist/`, `*.p12`, `*.pfx`,
  `certificados/`, `.env`, `*.db`, `backend/salida/`, `uploads/` y los vídeos de
  ejemplo. Los tres primeros patrones de certificado importan más que el resto:
  un `.p12` en el historial de git es una clave privada publicada, y borrarla
  después no la borra del historial.
- **`README.md` raíz** — arquitectura, instalación de las dos mitades, tabla de
  variables de entorno, cómo correr las pruebas, qué falta e índice de la
  documentación.
- **Primer commit:** `b8a2c1a`, 148 archivos.

---

## 2. Guías de remisión al SRI

Hasta ahora la guía se guardaba en base de datos (Tanda 7) pero no se transmitía.

### `app/sri/xml_guia_remision.py` — XML versión 1.1.0

Es el comprobante más distinto de todos: **no lleva importes ni impuestos**. Lo
que declara es quién traslada, desde dónde, hasta dónde y qué se mueve.

Dos particularidades estructurales frente a la factura:

- Los detalles **no cuelgan de la raíz**: van anidados dentro de cada
  `destinatario`, porque el SRI permite una guía con varias entregas. Aquí se
  emite un único destinatario —el caso habitual—; ampliarlo es añadir elementos
  a esa lista sin tocar nada más.
- El motivo de traslado se traduce: la interfaz dice *"Traslado entre bodegas"*
  y el SRI espera *"Traslado entre establecimientos de una misma empresa"*. El
  diccionario `MOTIVOS_SRI` hace de puente para que el usuario no tenga que
  escribir la redacción oficial.

### Refactor: `abrir_certificado()`

La carga del `.p12` —descifrar la contraseña, escribirlo a un temporal porque
`cargar_p12` lee de disco, abrirlo, y borrar el temporal en el `finally`— estaba
embebida dentro de `emitir_comprobante`. Se extrajo a
`emision.abrir_certificado(sesion, empresa)` y ahora la comparten los tres
caminos de emisión. Es la parte delicada del sistema: duplicarla tres veces era
garantizar que una de las copias se quedara atrás.

### `app/servicios/emision_guias.py` y `POST /guias/{id}/emitir`

Misma orquestación que los comprobantes, con las mismas garantías:

- El XML firmado se guarda **antes** de transmitir (nuevas columnas
  `xml_firmado` y `mensajes_sri` en `guias_remision`), así un fallo de red no lo
  pierde y el reintento no vuelve a firmar.
- Una guía autorizada no se reenvía.
- Los mensajes del SRI se conservan: cuando rechaza, ese texto es lo único que
  permite corregir.

En el frontend, el botón "Emitir al SRI" del formulario de guía **ahora emite**;
antes solo creaba el borrador pese a lo que decía la etiqueta. Si la creación
funciona pero la transmisión falla, se avisa sin perder la guía.

---

## 3. Retenciones de punta a punta

El XML de retención existía desde la Tanda 4, pero no había ni tabla, ni API, ni
pantalla. Se construyó todo.

### Tabla propia, no un `Comprobante` más

`Retencion` y `DetalleRetencion` son tablas nuevas. Meter la retención en la
tabla de comprobantes obligaría a dejar en blanco casi todas sus columnas: no
tiene líneas de producto, ni IVA que cobrar, ni forma de pago. Lo que tiene son
porcentajes retenidos al proveedor sobre el documento que sustenta el pago.

### Dos reglas que el SRI castiga, verificadas antes de crear

| Regla | Por qué se comprueba aquí |
|---|---|
| La empresa debe ser agente de retención o contribuyente especial | Retener sin serlo es una infracción tributaria, no un error de formato |
| El sujeto retenido debe tener rol `Proveedor` | Se retiene a quien nos vende, no a quien nos compra |

Ambas producen un mensaje explicando qué falta y dónde arreglarlo, en lugar de
dejar que el SRI devuelva un código.

### El catálogo de códigos, y por qué el API no valida contra él

`app/sri/codigos_retencion.py` recoge los conceptos de uso más común de las
tablas 20, 21 y 22 con su porcentaje habitual, y se expone en
`GET /retenciones/codigos`.

**Deliberadamente, el API acepta cualquier `codigo_retencion` y cualquier
porcentaje entre 0 y 100.** Los porcentajes los fija el SRI por resolución y
cambian; una tabla desactualizada en este repositorio no debe impedir emitir una
retención correcta. El catálogo es una ayuda de la interfaz —precarga el
porcentaje al elegir el concepto, y el campo queda editable—, y quien valida de
verdad es el SRI al recibir el XML.

> **Antes de producción:** contrastar los porcentajes de `codigos_retencion.py`
> con la resolución vigente. Es un diccionario plano justamente para que
> editarlo no requiera tocar nada más. La pantalla lo advierte al usuario.

### Endpoints y pantalla

```
GET    /retenciones            listado con filtros por estado y período fiscal
GET    /retenciones/codigos    catálogo de conceptos
POST   /retenciones            crea y calcula los valores retenidos
GET    /retenciones/{id}
POST   /retenciones/{id}/anular
POST   /retenciones/{id}/emitir
```

En el frontend: ruta `/retenciones`, entrada en la barra lateral y dos comandos
en la paleta (Ctrl+K). El listado suma **lo filtrado, no solo la página** —esa es
la cifra que se concilia con el formulario 103/104—. El formulario reutiliza la
hoja de estilos del de guías vía `composes`, y solo define lo suyo: la tabla de
líneas, el total y la advertencia del catálogo.

El período fiscal se valida como `MM/AAAA` en los dos lados: el SRI lo quiere
así, no como fecha.

---

## 4. WhatsApp emite de verdad

El orquestador del asistente creaba la factura en estado `Borrador` y respondía
*"se enviará al SRI en cuanto la firma electrónica esté configurada"*. Ahora,
tras la confirmación explícita del usuario, transmite.

Se corrigieron dos cosas de paso:

**Numeraba con su propio contador.** Leía `punto.secuencial_factura` y lo
incrementaba a mano, en lugar de usar `reservar_secuencial()` como la pantalla de
facturación. Dos contadores sobre el mismo punto de emisión producen números
repetidos, y el SRI los rechaza. Ahora ambos caminos pasan por el mismo sitio.

**El IVA de cada línea no se calculaba.** Guardaba `total = cantidad × precio`,
sin impuesto, así que el detalle no cuadraba con el total que el propio asistente
le había mostrado al usuario en el resumen. Ahora cada línea se recalcula con el
motor SRI.

La regla de diseño no cambió: **el modelo nunca emite por su cuenta.** Extrae
datos, el sistema calcula y valida, y solo tras un "sí" explícito se transmite.

Las respuestas ahora distinguen los cuatro desenlaces reales: autorizada (con el
número), pendiente (el SRI aún procesa), rechazada (con los motivos del SRI), y
fallo de red (guardada y firmada, lista para reintentar).

---

## 5. Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **174/174** (142 previos + 32 nuevos) |
| `oxlint` frontend | Limpio |
| `npm run build` | OK — 2 843 módulos |

Los 32 tests nuevos, por área:

- **Guías (12)** — estructura del XML según la ficha técnica, detalles anidados
  en el destinatario, traducción del motivo, clave de acceso con tipo `06`,
  emisión autorizada, XML firmado persistido, no reenviar una autorizada,
  mensajes de una devuelta, fallo de red que deja la guía firmada, guía anulada
  que no se emite, y secuencial independiente.
- **Retenciones (14)** — cálculo del valor retenido, XML con tipo `07`, documento
  sustento repetido en cada `<impuesto>` (así lo exige la versión 1.0.0),
  catálogo y porcentaje sugerido, creación con cálculo de totales, rechazo al
  retener a un cliente, formato del período fiscal, impuesto desconocido,
  empresa que no es agente de retención, emisión autorizada, XML firmado
  persistido, no reenviar una autorizada y secuencial independiente.
- **WhatsApp (6)** — la confirmación emite y devuelve el número de autorización,
  el IVA de la línea queda calculado, usa el mismo contador que la pantalla, un
  rechazo se explica conservando la factura, un fallo de red la deja firmada, y
  sin empresa configurada no se emite.

---

## 6. Qué queda

1. **El certificado `.p12` de entidad acreditada.** Sigue siendo lo único que separa al sistema de una autorización real; la Tanda 9 lo demostró contra los servidores del SRI. No requiere cambios de código.
2. **Envío por correo del comprobante autorizado** (XML + RIDE adjuntos) — diferido por el usuario en esta tanda.
3. **RIDE de guías y retenciones.** El de factura y nota de crédito ya existe; estos dos comprobantes se emiten pero todavía no tienen representación impresa.
4. **Reconsulta de guías y retenciones pendientes.** Los comprobantes tienen `POST /{id}/consultar`; estos dos aún no.
5. **Contrastar `codigos_retencion.py` con la resolución vigente** del SRI.
6. **Antes de producción:** `CLAVE_SECRETA`, PostgreSQL, `COOKIE_SAMESITE` si los dominios difieren, cifrado de la clave del `.p12` en un KMS, y contrastar los cantones con el INEC.
