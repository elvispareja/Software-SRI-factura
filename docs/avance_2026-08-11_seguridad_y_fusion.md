# Seguridad del API y cierre de la bifurcación de ramas

Fecha: 11 de agosto de 2026

Esta tanda no añade funcionalidad. Cierra un agujero de seguridad que llevaba
abierto desde el principio, arregla un fallo que afectaba al dinero, y resuelve
la bifurcación con la rama `sri-facturas`.

Se resume en una frase: **el sistema servía la contabilidad completa a cualquiera
que conociera la URL, y las 526 pruebas de entonces pasaban en verde.**

---

## 1. El API estaba abierto: 112 de 118 endpoints

### Cómo se encontró

Comparando esta rama con `sri-facturas`, cuya tanda 13 se llamaba «API cerrado
con sesión». Al mirar qué había cerrado exactamente, la pregunta se dio la
vuelta: ¿y aquí?

No se dio por buena la lectura del código. Se levantó el API y se llamó **sin
cookie y sin token**, como haría un desconocido:

```
 200  GET /api/configuracion/usuarios     el padrón de usuarios y sus correos
 200  GET /api/receptores                 clientes con cédula y RUC
 200  GET /api/comprobantes               todas las facturas emitidas
 200  GET /api/reportes/ventas            el total facturado
 200  GET /api/reportes/inventario/csv    descarga del inventario
 200  GET /api/cuentas/resumen            cuentas por cobrar
 401  GET /api/auth/yo                    ← el único cerrado del sistema
```

### La causa

Los doce `include_router` de `main.py` se declaraban sin `dependencies`, y
`usuario_actual` se usaba en un solo sitio: `GET /api/auth/yo`. FastAPI aplica
autenticación si hay un `Depends` en la aplicación, en el router o en la ruta.
No había en ninguno de los tres.

No fue un descuido puntual sino una omisión estructural: la pieza estaba escrita
—`seguridad.py` tenía cookie `HttpOnly`, respaldo por cabecera `Bearer`, JWT
HS256 y PBKDF2 con 260.000 iteraciones— y no se enchufó nunca.

Peor: esta rama **empeoró** el agujero respecto al punto de bifurcación. Pasó de
66 a 118 endpoints, todos abiertos, y el commit del rediseño (`0b76cab`) añadió
`POST /api/whatsapp/simulador`, que no pide sesión, no verifica la firma HMAC de
Meta y llama al orquestador de forma síncrona. Dos peticiones —una con los datos
y otra con el texto «si»— bastaban para **emitir una factura real firmada con el
certificado del contribuyente**.

### Cómo quedó

El cierre se declara en el `include_router`, no ruta por ruta:

```python
SESION_REQUERIDA = [Depends(usuario_actual)]
```

La razón está en el propio historial: un endpoint nuevo hereda la protección por
el hecho de vivir en su router, así que olvidarse deja de ser posible. Marcar
cada ruta a mano es exactamente como se llegó hasta aquí.

Siguen abiertos, a propósito y por motivos distintos:

| Router | Por qué |
|---|---|
| `autenticacion` | Registro y login no pueden exigir una sesión previa |
| `whatsapp` | Meta se autentica con la firma HMAC-SHA256 de `X-Hub-Signature-256`, no con una sesión |

El simulador es la excepción dentro de `whatsapp` y lleva su propio `Depends`:
no lo llama Meta, lo llama el frontend.

### El peaje

Al cerrar el API, las 16 suites de pruebas llamaban sin autenticarse: **178
pruebas en rojo de golpe**. Se resolvió trayendo `tests/conftest.py` de la rama
`sri-facturas`, que ya había pagado ese peaje y lo había depurado.

Un detalle suyo que merece la pena conservar escrito: `iniciar_sesion()` usa la
cabecera `Authorization` y no la cookie, porque la cookie de sesión se marca
`Secure` y el `TestClient` habla HTTP, así que su almacén de cookies la
descartaría y las pruebas darían 401 sin motivo real.

### La pieza que faltaba en las dos ramas

`backend/tests/test_api_cerrado.py`, 23 pruebas nuevas. La rama externa cerró el
API pero **no escribió ni una prueba que afirmara 401 en un endpoint de
negocio**: sus únicos asertos de 401 apuntaban a `/api/auth/yo`. Sin eso, quitar
un `dependencies=SESION_REQUERIDA` dejaba toda la suite en verde y el agujero
volvía en la siguiente tanda.

Se verificó que la prueba sirve: al desproteger el router de reportes a
propósito, se pusieron rojas sus tres rutas centinela. Una prueba de regresión
que no se ha visto fallar no es una prueba de regresión.

El archivo cubre también lo contrario —que lo que debe seguir abierto siga
abierto—, porque un cierre que rompe el registro o el webhook de Meta no sirve.

---

## 2. El registro de usuarios anulaba el cierre

Cerrar los routers servía de poco mientras `POST /api/auth/registro` no exigiera
nada: cualquiera se daba de alta, recibía un token válido y con él pasaba todas
las dependencias de sesión recién puestas.

Ahora **solo el primer usuario entra sin credenciales**. Esa excepción no es un
descuido: sin ella el sistema no podría arrancar, porque no habría administrador
que autorizara el alta del administrador.

Con esto llega `administrador_actual()` a `seguridad.py`, que es **la primera
comprobación de rol del sistema**. Hasta aquí, el campo `rol` del usuario se
rellenaba y no se leía en ninguna parte: tener sesión equivalía a poder hacer
cualquier cosa.

Devuelve **403 y no 401** a propósito. Quien llega ahí está identificado; lo que
falla es que no le corresponde. Un 401 le diría que vuelva a iniciar sesión, que
no arreglaría nada.

### El orden de las comprobaciones importa

La verificación de sesión va **antes** que la de correo duplicado. Al revés, un
desconocido distinguía un `409 Ya existe una cuenta` de un `401`, y probando
correos averiguaba cuáles tienen cuenta.

El login ya evitaba esa fuga a propósito —devuelve el mismo mensaje para usuario
inexistente y contraseña incorrecta— y dejarla abierta en el registro la habría
hecho inútil. Hay una prueba que lo fija: un correo registrado y uno inventado
tienen que dar exactamente la misma respuesta.

---

## 3. Una factura cobrada seguía figurando como deuda

`_recalcular_comprobante` sumaba solo `Cuota.cobrado`. Pero `crear_recibo`
admite a propósito dos caminos: recibo contra una cuota, o recibo directo contra
el comprobante cuando no hay plan de pagos — que es como se cobra una venta al
contado.

Ese segundo recibo se guardaba bien, aparecía en el listado y sumaba en caja,
pero no incrementaba ninguna cuota. Para el recálculo valía cero.

**Consecuencia**: cualquier factura sin cuotas se quedaba en «Por Cobrar» por
mucho que se cobrara, y figuraba como deuda pendiente en la pantalla de Cuentas.
El caso más común, no uno raro.

Reproducido antes de tocar nada —factura de 100,00 cobrada entera, `estado_pago`
seguía en «Por Cobrar»— y comprobado después.

### Por qué no se detectó antes

El módulo movía dinero y **no tenía ni una prueba de backend**. Las
verificaciones manuales de su tanda probaron el reparto en cuotas, que es el
camino que sí funcionaba. Nadie cobró una factura al contado.

Ahora tiene `backend/tests/test_cuentas.py`, con 7 pruebas: las tres del fallo,
el reparto de centavos con el resto en la última cuota, el rechazo del
sobrepago, los abonos parciales contra una misma cuota, y que el saldo se
calcula en vez de guardarse.

---

## 4. La bifurcación con `sri-facturas`

El 9 de agosto, en el commit `4f9120f`, el proyecto se bifurcó sin que ninguna
de las dos partes lo supiera. Se compararon las dos ramas área por área, cada
comparación con un verificador que la contrastaba contra el código real.

| Área | Resultado |
|---|---|
| **Cierre del API** | La otra rama era mejor — se trajo |
| Compras y gastos | Complementarias |
| Cuentas por cobrar | Esta rama: dos tablas frente a un campo |
| Pruebas | Esta rama: 559 frente a 485 |
| Diseño del frontend | Esta rama: el rediseño es posterior y deliberado |
| Edición de catálogos | Esta rama: ya la tenía, con guardas 409 |

### Por qué no se hizo `git merge`

Una fusión literal daba **20 archivos en conflicto de los 25 comunes**. Pero el
motivo de fondo es otro: el `main.py` de la otra rama **no importa cuatro de los
routers de esta** —anticipos, cuentas, egresos y recurrentes—. Aceptar su
versión de ese archivo habría dejado 34 endpoints sin registrar, en silencio, y
ninguna prueba lo habría detectado.

Por eso se portaron las piezas valiosas una a una. La rama `sri-facturas` no
está fusionada en el historial: está leída, comparada y aprovechada. Lo que aún
convendría traer queda listado en [`traspaso.md`](traspaso.md) §4.3, con ruta y
motivo.

---

## Cifras

| | Antes | Después |
|---|---:|---:|
| Endpoints sin autenticación | 112 | **0** |
| Comprobaciones de rol | 0 | 1 |
| Pruebas de backend | 292 | **325** |
| Pruebas de frontend | 234 | 234 |
| **Total** | 526 | **559** |

---

## Lo que queda pendiente de esta tanda

- **Aplicar `administrador_actual` al resto de operaciones sensibles.** Hoy solo
  protege el alta de usuarios. Borrar el certificado de firma sigue al alcance
  de cualquier usuario autenticado.
- **Decidir qué roles existen** más allá de administrador y operador. Eso ya no
  es mecánico: es el rediseño de la autorización que el prototipo prometía como
  «permisos granulares».
- **Revisar el resto de endpoints abiertos por diseño.** El webhook de WhatsApp
  confía en la firma HMAC de Meta; conviene comprobar que `WHATSAPP_SECRETO_APP`
  está definido en producción, porque sin él la verificación no puede hacerse.
