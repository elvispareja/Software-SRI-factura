# Avance — Tanda 11: RIDE y reconsulta para guías y retenciones, y la tabla de retención al día

> **Fecha:** 9 de agosto de 2026
> **Estado:** completado y verificado — 189 tests de backend, `oxlint` limpio, `npm run build` OK
> **Alcance:** los tres comprobantes electrónicos ya tienen el ciclo completo (RIDE · XML · emitir · consultar), y los porcentajes de retención se contrastaron contra la resolución vigente

---

## 1. La tabla de retenciones estaba desactualizada

Al contrastar `app/sri/codigos_retencion.py` con la fuente oficial apareció que
la tabla venía de la resolución **anterior**. La vigente es la
**NAC-DGERCGC26-00000009**, del 27 de febrero de 2026, aplicable **desde el 1 de
marzo de 2026**, que deroga la NAC-DGERCGC24-00000008.

### Qué cambió

| Concepto | Código | Antes | Ahora | Base legal |
|---|---|---|---|---|
| Transferencia de bienes muebles corporales | 312 | 1,75 % | **2 %** | Art. 2 num. 4 lit. i |
| Servicios con predominio de mano de obra | 307 | 2 % | **3 %** | Art. 2 num. 5 lit. a |
| Medios de comunicación y agencias de publicidad | 309 | 1,75 % | **3 %** | Art. 2 num. 5 lit. c |
| Arrendamiento de bienes inmuebles | 320 | 8 % | **10 %** | Art. 2 num. 7 lit. g |
| Servicios con predominio del intelecto sin título | 304 | 8 % | **10 %** | Art. 2 num. 7 lit. a |
| Seguros y reaseguros | 322 | 1,75 % | **2 %** | Art. 2 num. 4 lit. c |
| Arrendamiento mercantil | 319 | 1,75 % | **2 %** | Art. 2 num. 4 lit. g |
| Rendimientos financieros | 323 | 2 % | **3 %** | Art. 2 num. 5 lit. d |
| Otras retenciones (residual) | 332 | 2,75 % | **derogado → 3 %** | Art. 3 |

Además:

- **Desaparece el tramo del 8 %.** Los dos conceptos que lo usaban suben al 10 %.
- **Se elimina la tarifa del 2,75 %** y con ella el concepto 332. La regla
  residual —pagos sin porcentaje específico— pasa a **3 %** (art. 3).
- **Entra la tarifa del 5 %**: servicios profesionales prestados por sociedades
  residentes y comisiones pagadas a sociedades (art. 2 num. 6).
- Se añadieron conceptos que faltaban: energía eléctrica, construcción de obra
  inmueble, sustancias minerales, RIMPE emprendedores y negocios populares,
  docencia, regalías de propiedad intelectual, deportistas y artistas.

Los porcentajes de renta pasaron de 14 conceptos a 27.

### El límite honesto: los códigos numéricos

La resolución fija **conceptos y porcentajes**, no los códigos numéricos. Esos
los publica la **ficha técnica de comprobantes electrónicos**, que es un
documento aparte al que no se pudo acceder para verificarlos.

En consecuencia, el catálogo distingue ahora dos cosas:

- El **porcentaje** está contrastado contra el texto de la resolución, y cada
  concepto cita su artículo y numeral en `base_legal`.
- El **código** solo aparece cuando es de uso establecido y verificable. Los
  conceptos nuevos van con el código en blanco.

**Inventar un código produciría un rechazo del SRI difícil de diagnosticar**, así
que se dejan vacíos a propósito y la interfaz pide escribirlos. Los códigos de
IVA se vaciaron todos: además de no estar verificados, **difieren entre la
versión 1.0.0 y la 2.0.0 del XML de retención**, y este sistema emite la 1.0.0.

En el formulario, el desplegable de concepto ahora se indexa por un `id` del
catálogo (muchos conceptos ya no tienen código) y **el código pasó a ser un
campo de texto editable** que se precarga cuando se conoce. Si el concepto
elegido no trae código, la línea lo señala y el pie del panel cuenta cuántas
líneas están incompletas.

> El API sigue sin validar contra esta tabla, a propósito. Acepta cualquier
> código y cualquier porcentaje entre 0 y 100: quien valida de verdad es el SRI,
> y una tabla desactualizada aquí no debe impedir emitir una retención correcta.

---

## 2. RIDE de guías y retenciones

El generador de RIDE solo sabía imprimir facturas. Se refactorizó en tres
piezas: `_bloque_emisor` (izquierda), `_bloque_documento` (derecha, con el
título parametrizado) y `_armar`, que monta la página y **coloca el aviso de
ambiente de pruebas**. Ese aviso vive en la parte común y no en cada generador:
olvidarlo en uno solo produciría un documento que parece válido y no lo es.

**RIDE de guía de remisión** — sin bloque de totales, porque no documenta una
venta. Imprime transportista, placa, fechas y punto de partida; después, por
cada destinatario, sus datos, el motivo y su tabla de mercadería.

**RIDE de retención** — sujeto retenido, período fiscal y una tabla con una fila
por impuesto: documento sustento, número, fecha, impuesto, código, base,
porcentaje y valor retenido, más el total. El sustento va por línea porque en la
versión 1.0.0 del XML cada impuesto lleva el suyo, y el proveedor necesita ver
contra qué factura se le retuvo para cruzarlo con su contabilidad.

Para que la impresión y lo que se transmite no puedan divergir, se separó
`construir_modelo()` de `construir_xml()` en ambos servicios de emisión: el
RIDE usa exactamente el mismo modelo que se firma.

---

## 3. Reconsulta

`consultar_autorizacion()` estaba tipada contra `Comprobante`. Ahora acepta
cualquier documento con `clave_acceso`, `estado_sri`, `numero_autorizacion`,
`fecha_autorizacion` y `mensajes_sri` —que los tres tienen— y la comparten los
tres routers. Duplicarla habría triplicado la interpretación de la respuesta del
SRI, que es justo la parte fácil de equivocar.

Se añadió la columna `fecha_autorizacion` a guías y retenciones: el RIDE la
imprime, y hasta ahora solo la guardaban los comprobantes.

### Endpoints nuevos

```
POST /guias/{id}/consultar          GET /guias/{id}/xml          GET /guias/{id}/ride
POST /retenciones/{id}/consultar    GET /retenciones/{id}/xml    GET /retenciones/{id}/ride
```

El XML se devuelve firmado si ya se emitió; si sigue en borrador, se genera al
vuelo para poder revisarlo antes de transmitir.

---

## 4. Un componente de acciones para los tres

`AccionesComprobante` tenía las rutas del API incrustadas. Como los tres
documentos exponen exactamente el mismo juego —RIDE, XML, emitir, consultar—, se
renombró a **`AccionesDocumento`** y recibe el juego de rutas en `acciones`
(`ACCIONES_COMPROBANTE`, `ACCIONES_GUIA`, `ACCIONES_RETENCION`). Los listados de
guías y retenciones ya tienen su columna de acciones, con la misma regla de
siempre: los botones aparecen solo cuando el estado ante el SRI los permite, y
se ocultan enteros en modo demo porque esos identificadores no existen en el
servidor.

---

## 5. Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **189/189** (174 previos + 15 nuevos) |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |

Los 15 tests nuevos:

- **Catálogo (3)** — los porcentajes coinciden con la resolución vigente, la
  tarifa derogada del 2,75 % ya no existe y entró la del 5 %, y los conceptos
  sin código verificado lo declaran en vez de inventarlo.
- **Guías (7)** — el RIDE sale en PDF; el de un borrador lleva la franja de
  pruebas y "PENDIENTE DE AUTORIZACIÓN" y **no imprime totales**; el autorizado
  lleva el número; el XML de un borrador se genera al vuelo sin firma y el de
  una emitida es el firmado; consultar sin transmitir falla; y una reconsulta
  autoriza una guía pendiente.
- **Retenciones (5)** — el RIDE muestra período, documento sustento, ambos
  impuestos y el total; el autorizado lleva el número; los dos casos del XML;
  y la reconsulta de una pendiente.

Se añadió `pypdf` a `requirements.txt`: las pruebas de RIDE leen el texto del
PDF generado en lugar de conformarse con comprobar que empieza por `%PDF`.

---

## 6. Qué queda

1. **El certificado `.p12` de entidad acreditada.** Sigue siendo el único bloqueante real.
2. **Envío por correo del comprobante autorizado** (XML + RIDE adjuntos) — diferido por el usuario.
3. **Verificar los códigos numéricos** contra la ficha técnica de comprobantes electrónicos del SRI y completarlos en `codigos_retencion.py`. Los porcentajes ya están al día; faltan los códigos de los conceptos nuevos y de todo el bloque de IVA.
4. **Procesamiento de audio e imagen en WhatsApp**, y edición de registros existentes (hoy solo se crean).
5. **Antes de producción:** `CLAVE_SECRETA`, PostgreSQL, `COOKIE_SAMESITE` si los dominios difieren, cifrado de la clave del `.p12` en un KMS, y contrastar los cantones con el INEC.

---

## Fuentes

- [Resolución NAC-DGERCGC26-00000009 — Porcentajes de retención en la fuente de impuesto a la renta (SRI)](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/272ca6a9-d679-4b4e-8da0-fb4671cf5f8f/NAC-DGERCGC26-00000009_Ret_IR.pdf)
- [Boletín 014 — El SRI estableció nuevos porcentajes de retención (SRI)](https://www.sri.gob.ec/o/sri-portlet-biblioteca-alfresco-internet/descargar/9e68337d-5108-45c9-a21d-d412d5a8c6a4/BOLETI%CC%81N%20014-%20EL%20SRI%20ESTABLECIO%CC%81%20NUEVOS%20PORCENTAJES%20DE%20RETENCIO%CC%81N%20Y%20CALIFICO%CC%81%20A%20NUEVOS%20AGENTES%20DE%20RETENCIO%CC%81N.pdf)
