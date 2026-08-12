# Avance — Tanda 9: Emisión real al SRI

> **Fecha:** 8 de agosto de 2026
> **Estado:** completado y verificado — 142 tests de backend, 12 verificaciones de punta a punta
> **Hito:** el sistema transmitió un comprobante a los servidores reales del SRI y obtuvo respuesta

---

## 1. El hallazgo de esta tanda

La verificación de punta a punta no simuló el SRI: envió el comprobante a
`celcer.sri.gob.ec`, el ambiente de pruebas real. La respuesta:

```
Estado: Rechazado
Mensaje 39: FIRMA INVALIDA
  "La validacion de la cadena de confianza ha fallado: No existen un
   certificado root registrado para la entidad certificadora:
   CERTIFICADO DE PRUEBAS - NO VALIDO"
```

Leído con cuidado, esto confirma más de lo que rechaza:

| Etapa | Resultado |
|---|---|
| Clave de acceso de 49 dígitos | Aceptada |
| Estructura del XML (esquema del SRI) | **Aceptada** — la recepción fue exitosa |
| Firma XAdES-BES | Parseada correctamente |
| Transmisión SOAP | Correcta |
| Cadena de confianza del certificado | **Rechazada** — es autofirmado |

Si la estructura del XML tuviera un error, el SRI habría devuelto el
comprobante en la **recepción**, antes de llegar a la autorización. Que llegara
a autorizarse y fallara solo en la cadena de confianza significa que **lo único
que falta es el certificado de una entidad acreditada**.

---

## 2. Emisión (`app/servicios/emision.py`)

Une lo que estaba suelto: motor de XML, firmador XAdES-BES, certificado
guardado en Configuraciones y WebServices del SRI.

```
Borrador → XML → firma con el .p12 → recepción → autorización
```

### Decisiones que gobiernan el diseño

**La clave de acceso se calcula una sola vez y se guarda.** El código numérico
se deriva del `id` del comprobante, así que un reintento genera exactamente la
misma clave. Si se recalculara al azar, el reintento consultaría la autorización
de una clave que el SRI nunca recibió.

**El XML firmado se guarda antes de transmitir.** Si la red falla, no se pierde
y el reintento no tiene que volver a firmar.

**Un comprobante autorizado no se reenvía.** Devolvería "CLAVE ACCESO
REGISTRADA" y, si el estado local se pisara, se perdería el número de
autorización ya obtenido. El error sugiere emitir una nota de crédito.

### Precondiciones que se verifican antes de firmar

| Comprobación | Mensaje |
|---|---|
| Hay certificado activo | Orienta a Configuraciones → Firma Electrónica |
| El certificado no expiró | Da la fecha exacta de expiración |
| El certificado ya rige | Da la fecha desde la que será válido |
| El tipo se transmite al SRI | Una cotización no viaja |
| El estado permite emitir | Solo Borrador, Rechazado, Devuelto o Error |

### Interpretación de la respuesta

El SRI no autoriza de forma síncrona, así que los estados no se colapsan:

- Recepción `DEVUELTA` → **Devuelto**, con los mensajes guardados (es lo único que permite corregir).
- Autorización `AUTORIZADO` → **Autorizado**, con número y fecha.
- Autorización `NO AUTORIZADO` → **Rechazado**.
- Cualquier otro estado (`EN PROCESO`) → **Pendiente**, no un rechazo.
- Fallo de red → **Error**, con el comprobante ya firmado para reintentar.

Endpoint `POST /comprobantes/{id}/consultar` reconsulta la autorización de un
pendiente: puede autorizarse minutos después.

---

## 3. Establecimientos y puntos de emisión

Nuevo `PUT /configuracion/establecimientos/{id}`, con dos cuidados:

**Los puntos se emparejan por su código, no por posición.** Renombrar o
reordenar en pantalla no debe reasignar secuenciales entre cajas distintas —
sería la forma más silenciosa de romper la numeración.

**El secuencial solo puede adelantarse.** Retrocederlo produciría números
repetidos y el SRI rechazaría los comprobantes. El error dice de qué valor a
cuál se intentó retroceder.

En el frontend, los establecimientos se guardan con el mismo botón que la
empresa: el usuario los edita en la misma pantalla y espera un solo guardado.

---

## 4. Acciones del listado

Nuevo `AccionesComprobante`: el botón "Ver PDF" que no hacía nada se sustituyó
por acciones reales, **condicionadas al estado ante el SRI**:

| Acción | Cuándo aparece |
|---|---|
| RIDE (PDF) | Siempre — en borrador sale con la franja de pruebas |
| XML | Siempre — firmado si ya se emitió |
| Emitir / Reintentar | Borrador, Rechazado, Devuelto o Error |
| Consultar | Pendiente, Devuelto o Rechazado, y con clave de acceso |
| N.º de autorización | Cuando está autorizado |

Mostrar botones que van a fallar es peor que no mostrarlos. Los mensajes del
SRI se despliegan bajo la fila con su identificador e información adicional:
cuando rechaza, ese texto es lo único que permite corregir.

---

## 5. Un bug que atrapó el linter

Al conectar el guardado de establecimientos, `oxlint` avisó de un import sin
usar. La causa no era un import sobrante: el componente ya tenía una función
local `actualizarEstablecimiento` (el editor de estado en memoria) que
**sombreaba al import del API**. La llamada de guardado invocaba a la local con
argumentos equivocados y **nunca llegaba al servidor**, sin error visible.

Se corrigió importando con alias (`actualizarEstablecimientoApi`). Vale la pena
anotarlo: era un fallo silencioso que ninguna prueba de backend habría detectado.

---

## 6. Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **142/142** (126 previos + 16 nuevos) |
| **Punta a punta contra el servidor real** | **12/12** |
| **Transmisión al SRI real** | Recepción aceptada; autorización rechaza solo la cadena de confianza |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |

Los 16 tests nuevos cubren: emisión sin certificado, certificado expirado,
cotización que no se transmite, emisión autorizada, XML firmado persistido, no
reenviar un autorizado, mensajes de un devuelto, reintento tras devolución,
**clave de acceso estable entre reintentos**, fallo de red que deja el
comprobante firmado, estado pendiente, reconsulta que autoriza, y las reglas de
establecimientos.

---

## 7. Qué queda

1. **El certificado `.p12` de entidad acreditada.** Ya está demostrado que es lo único que falta: con él, el mismo flujo debería autorizar. Se carga en Configuraciones → Firma Electrónica y no requiere ningún cambio de código.
2. **Envío del comprobante autorizado por correo** al receptor (XML + RIDE adjuntos).
3. **Retenciones y guías al SRI**: el XML de retención existe desde la Tanda 4 y la guía se persiste desde la Tanda 7, pero ninguna se transmite todavía — solo factura, nota de crédito, liquidación y nota de venta.
4. **Antes de producción:** `CLAVE_SECRETA`, PostgreSQL, `COOKIE_SAMESITE` si los dominios difieren, cifrado de la clave del `.p12` en un KMS, y contrastar los cantones con el INEC.
