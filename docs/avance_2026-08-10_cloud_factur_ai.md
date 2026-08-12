# Avance — Rediseño Cloud Factur AI y módulos que faltaban

> **Fecha:** 10 de agosto de 2026
> **Estado:** 526 pruebas (292 backend + 234 frontend), `oxlint` limpio, `npm run build` OK
> **Origen:** el prototipo `Cloud World Office.dc.html` estaba en el repositorio desde el primer día y no se había usado

---

## 1. Qué pasó

La auditoría inicial anotó el conflicto —*"dirección de diseño distinta a la del React… hay que decidir cuál manda antes de escribir más CSS"*— pero el desarrollo siguió sobre la dirección visual del React sin que la decisión se tomara. El resultado fue un sistema funcional con **otra cara** y sin siete de los módulos que el prototipo cubre.

Esta tanda corrige ambas cosas.

---

## 2. Sistema de diseño

Los tokens salen del prototipo, extraídos de él y no inventados:

| Token | Valor | De dónde |
|---|---|---|
| Naranja de marca | `#f26a35` | El color más usado del prototipo (226 apariciones) |
| Cian de marca | `#2aa9d6` → `#1f6fd0` | Degradado del logotipo |
| Fondo de página | `#e9edf3` | `body` del prototipo |
| Barra lateral | `linear-gradient(180deg, #111f37, #0a1424)` | `sidebarBase` |
| Texto | `#0f1e33` · `#5b6b82` · `#8a99ad` | Jerarquía del prototipo |
| Tarjeta | blanco, radio 18px, sombra `0 10px 26px rgba(16,31,54,.05)` | Patrón repetido |
| Tipografía | Plus Jakarta Sans | `<link>` del prototipo |

**`.glass-panel` conserva el nombre** aunque ya no sea glassmorphism. Renombrarla habría tocado cuarenta archivos sin cambiar nada de fondo; lo que cambió es a qué apunta.

El **tema oscuro** se deriva del claro: conserva el naranja y el cian —son la identidad— y traslada los grises a la familia azulada del `#0f1e33`, para que no parezca otro producto.

---

## 3. Lo que se encontró al mirar la pantalla en el navegador

No se descubrió leyendo código, sino abriendo la aplicación con Playwright y mirándola:

**El panel «Plan state» mostraba datos inventados.** Etiquetaba el saldo por cobrar como *"último pago"* y la fecha de hoy como *"vence"*. Eso es peor que un dato obviamente falso: parece creíble. Como no hay módulo de facturación del SaaS, el hueco se rellenó con lo que sí existe y el usuario necesita vigilar — cuántos comprobantes llegaron a autorizarse y en qué ambiente se emite, con aviso explícito de que en pruebas los documentos no tienen validez tributaria.

**Las acciones rápidas desaparecían si el API fallaba**, que es justo cuando más falta hace poder llegar a Configuraciones.

**El mensaje de «sin documentos» se pintaba dos veces** en la misma tarjeta, lo que se lee como un fallo de pintado.

**Cinco enlaces del menú no tenían pantalla** (`/gastos`, `/egresos`, `/recurrentes`, `/compras`, `/notas`): el catch-all rebotaba a Inicio sin explicar nada.

Y un identificador con caracteres cirílicos colado en `Layout.jsx`.

---

## 4. La migración de IA estaba a medias

`extraccion.py` se había migrado de Anthropic a Gemini pero **nunca llegó a ejecutarse**: `Part.from_text()` exige argumento con nombre en `google-genai` 2.x, así que las siete pruebas del asistente fallaban.

Además se había perdido el manejo de dos casos que las pruebas protegían: el **rechazo por seguridad** y la **respuesta truncada**. Ambos llegan con el texto vacío, y sin distinguirlos el usuario solo ve *"no devolvió contenido"* — cuando uno se arregla reformulando el mensaje y el otro acortándolo.

`requirements.txt` no declaraba `google-genai` y `.env.example` no tenía `GEMINI_API_KEY`. El sistema usa **dos proveedores a propósito**: Gemini extrae los datos de facturación y Anthropic hace el OCR de las imágenes de WhatsApp.

---

## 5. Módulos nuevos

### Egresos

La distinción entre **gasto** y **egreso** gobierna el diseño: el gasto es la obligación (llegó la factura del arriendo), el egreso es la salida de dinero (se pagó). No coinciden ni en fecha ni en importe —un gasto puede pagarse en varios egresos y un egreso saldar varios gastos—, así que son dos tablas.

- **Tipos de gasto**: catálogo editable, porque cada negocio agrupa sus gastos a su manera y el reporte solo sirve si las categorías son las suyas. Se desactivan en vez de borrarse.
- Un gasto con pagos **no se borra**, y un pago **se anula** en vez de borrarse: la caja tiene que poder explicar cada movimiento, incluidos los deshechos.
- El estado del gasto se recalcula sobre la **suma de todos sus pagos vigentes**, no sobre el último.

### Anticipos

Existía la pantalla, funcionando solo con `ANTICIPOS_MOCK` y una lista de receptores escrita a mano. Ahora tiene backend.

El **saldo no se guarda**: se calcula como `monto − facturado`. Un tercer número almacenado es un número que puede dejar de cuadrar con los otros dos. No se puede aplicar más de lo disponible ni anular uno ya aplicado — eso dejaría facturas apoyadas en dinero inexistente.

### Facturación recurrente

Guarda la **plantilla**, no las facturas. Al emitir crea un `Comprobante` normal con el mismo contador de secuencia que los demás, porque ante el SRI no existe la "factura recurrente": es una factura y ya.

**La emisión no es automática.** El sistema dice qué toca y la persona confirma. Una factura emitida sola contra un cliente que ya canceló hay que anularla con nota de crédito, y eso cuesta más que pulsar un botón al mes.

La fecha **respeta el fin de mes**: 31 de enero más un mes es 28 de febrero, no 3 de marzo. Una suscripción que se cobra a fin de mes sigue cobrándose a fin de mes.

---

## 6. Dos fallos que aparecieron al probar

**Al anular un pago**, el estado del gasto se recalculaba antes de volcar la anulación a la base, así que la consulta seguía contando ese pago como vigente y el gasto se quedaba en «Pagado».

**El adaptador de tipos de gasto** convertía `undefined` en `false` con `Boolean()`, invirtiendo el valor por defecto del backend y marcando como no deducible un gasto que nadie había tocado.

---

## 7. Verificación

| Chequeo | Antes | Ahora |
|---|---|---|
| Backend (pytest) | 253 | **292** |
| Frontend (vitest) | 216 | **234** |
| **Total** | 469 | **526** |
| `oxlint` | limpio | limpio |
| `npm run build` | OK | OK |

---

## 8. Qué queda del prototipo

1. **Trazabilidad de factura** y **Cuentas por cobrar/pagar** tienen pantalla, pero las partes que exigen un modelo contable dedicado (cuotas, vencimientos, recibos) están marcadas como *Próximamente* en vez de fingirse.
2. **Formulario de alta de plantilla recurrente**: hoy se crean por API; la pantalla lista, emite, pausa y borra.
3. Los pendientes de siempre: **certificado acreditado** y **envío por correo**.
