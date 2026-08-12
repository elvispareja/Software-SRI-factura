# Traspaso — dónde quedó el proyecto

Fecha del corte: **11 de agosto de 2026**

Este documento está escrito para quien recoge el proyecto sin haber estado en
las sesiones anteriores. Responde a tres preguntas en este orden: qué hay, qué
pasó con la bifurcación de ramas, y por dónde seguir.

Los otros documentos de entrada siguen siendo válidos:
[`lo_construido.md`](lo_construido.md) (qué hay hecho),
[`estado_del_proyecto.md`](estado_del_proyecto.md) (qué falta) y
[`auditoria_proyecto.md`](auditoria_proyecto.md) (índice de las tandas).

---

## 1. Estado en cifras

Contadas del repositorio, no de memoria. Los comandos están al final.

| Métrica | Valor |
|---|---|
| Endpoints | 118 |
| Modelos de base de datos | 24 |
| Pantallas | 17 |
| Código | 11.367 líneas Python · 15.753 líneas JS/JSX |
| Pruebas | **559** — 325 backend (pytest) · 234 frontend (vitest) |
| Commits | 25 |
| Secciones «Próximamente» | 6 |

El núcleo fiscal está terminado: los siete comprobantes del SRI se generan, se
firman con XAdES-BES, se envían y se consultan. En las pruebas contra el
ambiente del SRI la recepción fue aceptada; la autorización falló solo por la
cadena de confianza del certificado autofirmado (`error 39: FIRMA INVALIDA — no
existe certificado root registrado`). Falta un certificado de verdad, no código.

---

## 2. Hubo dos ramas y esto es lo que se hizo con ellas

El 9 de agosto, en el commit `4f9120f` («Manual de uso en PDF»), el proyecto se
bifurcó sin que ninguna de las dos partes lo supiera:

```
                         ┌── 15 commits ──► esta rama
4f9120f ─────────────────┤     rediseño Cloud Factur AI, egresos, anticipos,
(9 ago, punto común)     │     recurrentes, reportes ampliados, correo SMTP,
                         │     cuentas por cobrar, listas de configuración
                         └──  2 commits ──► rama sri-facturas
                               tandas 13 y 14: API cerrado con sesión,
                               compras y gastos, edición de catálogos
```

Se compararon las dos, área por área. **Cinco de seis áreas las gana esta rama;
una la pierde, y era la más importante.**

| Área | Resultado |
|---|---|
| **Cierre del API (seguridad)** | La otra rama era mejor — **se trajo** |
| Compras y gastos | Complementarias — pendiente de portar (§4) |
| Cuentas por cobrar | Esta rama: 2 tablas frente a un campo |
| Pruebas | Esta rama: 559 frente a 485 |
| Diseño del frontend | Esta rama: el rediseño es posterior y deliberado |
| Edición de catálogos | Esta rama: ya la tenía, con guardas 409 |

### Por qué no se hizo un `git merge`

Una fusión literal daba **20 archivos en conflicto de los 25 comunes**, y algo
peor: el `main.py` de la otra rama **no importa cuatro de los routers de esta**
—anticipos, cuentas, egresos y recurrentes—. Aceptar su versión de ese archivo
habría dejado 34 endpoints sin registrar, en silencio y sin que ninguna prueba
lo detectara.

Por eso se portaron las piezas valiosas una a una en lugar de fusionar. La rama
`sri-facturas` **no está fusionada** en el historial: está leída, comparada y
aprovechada.

---

## 3. Lo que cambió en esta sesión

### El API estaba abierto de par en par

Es el hallazgo grave. **112 de los 118 endpoints respondían sin credenciales.**
No era una hipótesis: se comprobó levantando el API y llamándolo sin cookie ni
token.

La causa: los doce `include_router` de `main.py` se declaraban sin
`dependencies`, y `usuario_actual` solo se usaba en `GET /api/auth/yo`. FastAPI
aplica autenticación si hay un `Depends` en la app, en el router o en la ruta;
no había en ninguno de los tres.

Los tres peores no eran de lectura:

| Endpoint | Qué permitía |
|---|---|
| `POST /api/configuracion/firma` | subir un `.p12` con su contraseña |
| `POST /api/comprobantes/{id}/emitir` | transmitir al SRI con esa firma |
| `POST /api/whatsapp/simulador` | emitir facturas con dos peticiones |

Ese último era exclusivo de esta rama; lo introdujo el commit `0b76cab` del
rediseño. No pedía sesión ni verificaba la firma HMAC, y llamaba al orquestador
de forma síncrona, que emite comprobantes de verdad.

**Cómo quedó** (`commit 972d4f6`): el cierre se declara en el `include_router`,
no ruta por ruta, para que un endpoint nuevo herede la protección por el hecho
de vivir en su router. Marcar cada ruta a mano es exactamente como se llegó
hasta aquí.

Siguen abiertos a propósito: `autenticacion` —registro y login no pueden exigir
sesión previa— y el webhook de WhatsApp, que Meta autentica con la firma
HMAC-SHA256 de `X-Hub-Signature-256`. El simulador es la excepción dentro de ese
router y lleva su propio `Depends`.

**La pieza que ninguna de las dos ramas tenía**: `backend/tests/test_api_cerrado.py`,
23 pruebas que exigen 401 sin credenciales. Sin ella, quitar un
`dependencies=SESION_REQUERIDA` dejaba las 322 pruebas de entonces en verde. Se verificó que
detecta la regresión: al desproteger un router, se pone roja.

### El registro de usuarios estaba abierto, y anulaba el cierre

Cerrar los routers servía de poco mientras `POST /api/auth/registro` no exigiera
nada: cualquiera que alcanzara el servidor se daba de alta, recibía un token
válido y con él pasaba todas las dependencias de sesión. Es poner una cerradura
y colgar la llave del pomo.

Ahora **solo el primer usuario entra sin credenciales** —sin esa excepción el
sistema no podría arrancar, porque no habría administrador que autorizara el
alta del administrador—. A partir de ahí el alta la hace un administrador.

Con ello llegó `administrador_actual` en `seguridad.py`, **la primera
comprobación de rol del sistema**: hasta aquí el campo `rol` del usuario se
rellenaba y no se leía en ninguna parte. Devuelve 403 y no 401 a propósito: quien
llega hasta ahí está identificado, lo que falla es que no le corresponde.

Un detalle que apareció al ordenar el código: la comprobación de sesión va
**antes** que la de correo duplicado. Al revés, un desconocido distinguía un 409
de un 401 y averiguaba así qué correos tienen cuenta. El login ya evitaba esa
fuga a propósito; dejarla abierta en el registro la habría hecho inútil.

### Una factura cobrada seguía figurando como deuda

`commit aad3234`. `_recalcular_comprobante` sumaba solo `Cuota.cobrado`, pero
`crear_recibo` admite a propósito un recibo directo contra el comprobante cuando
no hay plan de cuotas — que es como se cobra una venta al contado. Ese recibo no
incrementa ninguna cuota, así que valía cero para el recálculo.

Resultado: cualquier factura sin cuotas se quedaba en «Por Cobrar» por mucho que
se cobrara. El caso más común, no uno raro.

No se detectó antes porque **el módulo movía dinero y no tenía ni una prueba de
backend**. Ahora tiene `backend/tests/test_cuentas.py`, con 7.

### Datos personales anonimizados

`commit 5b2b057`. El prototipo `Cloud World Office.dc.html` se exportó de una
cuenta real y salió con el nombre completo, RUC, correo, teléfono y dirección
domiciliaria del titular: 24 apariciones. De ahí se habían colado además a tres
valores por defecto del código, en `Configuraciones.jsx` y `Soporte.jsx`, que era
lo peor: esos literales viajaban en el bundle servido al navegador.

Sustituidos por datos de ejemplo. Los RUC de los clientes del prototipo se
revisaron y son ficticios: no había datos de terceros.

---

## 4. Lo que falta, por orden

### 4.1. El certificado `.p12` acreditado — el único bloqueante real

Sin él nada de lo que se firme tiene validez ante el SRI. Se compra a una
entidad acreditada (Security Data, ANF, Uanataca o el Banco Central), cuesta
entre 30 y 80 USD al año y tarda días en emitirse. Se carga en Configuraciones →
Firma Electrónica. **No depende del desarrollo.**

### 4.2. Permisos por rol: hay uno, faltan los demás

El alta de usuarios ya exige rol de administrador (§3), y con ella llegó
`administrador_actual`, la primera comprobación de rol del sistema. Pero es la
única: en el resto del API, tener sesión sigue equivaliendo a poder hacer
cualquier cosa, incluido borrar el certificado de firma.

La dependencia ya está escrita y probada, así que aplicarla a las operaciones
sensibles —la firma electrónica, la configuración de la empresa, la anulación de
comprobantes— es trabajo mecánico. Lo que no es mecánico es decidir **qué roles
existen** más allá de administrador y operador; eso es rediseñar la
autorización, y es el punto donde el prototipo prometía «permisos granulares».

### 4.3. Piezas de la otra rama que aún convendría portar

Están identificadas y verificadas contra su código:

| Pieza | Dónde está en `sri-facturas` | Por qué |
|---|---|---|
| IVA por línea en el gasto | `modelos_db.py` (DetalleComprobante) | Es lo único que esta rama no puede representar y el formulario 104 exige: separar adquisiciones al 15 % de las del 0 % |
| `autorizacion_proveedor` en `Gasto` | `modelos_db.py` | La clave de acceso del documento recibido es dato del ATS y aquí no hay dónde guardarla |
| Validar que el proveedor tenga `rol == 'Proveedor'` | `comprobantes.py` | Hoy un gasto se puede registrar contra un cliente sin que nada lo impida |
| Bloqueo de la identificación al editar | `ReceptoresForm.jsx` | La identificación ata el comprobante autorizado al receptor; hoy se puede reescribir el RUC de un cliente con facturas emitidas |
| Prueba de ida y vuelta del adaptador | `adaptadores.test.js` | Delata el borrado silencioso de campos al guardar un receptor sin tocar nada |

### 4.4. Deuda menor — los cuatro puntos de esta lista ya están hechos

Se cerraron el 11 de agosto y quedan aquí anotados porque explican por qué el
código tiene la forma que tiene. El detalle, en
[`avance_2026-08-11_pendientes_visibles.md`](avance_2026-08-11_pendientes_visibles.md).

- ✅ Las cinco tarjetas de **Reportes de Cuentas** consultan el backend.
- ✅ El interruptor **Cobrar/Pagar** lee tablas distintas en cada modo: en Pagar,
  `Gasto`/`Egreso` y liquidaciones de compra, no ventas rebautizadas.
- ✅ **Exportación a PDF** de los reportes, con paginación y numeración.
- ✅ **Los colores del JSX pasaron de 232 a 13**, y los 13 restantes están
  justificados uno a uno.

Lo que sigue pendiente en esta pantalla:

- La **agenda suma cuotas, no documentos**: un abono suelto contra un
  comprobante que además tiene plan de cuotas no rebaja ninguna cuota, así que
  su saldo puede quedar por encima del que da el reporte de saldos. Imputar
  esos abonos a las cuotas más antiguas es un criterio contable que nadie ha
  decidido todavía, y por eso no se inventó.

### 4.5. Antes de producción

- Definir `CLAVE_SECRETA`. **Si cambia, las contraseñas de certificado guardadas
  dejan de poder descifrarse** y hay que volver a subir el `.p12`.
- Migrar de SQLite a PostgreSQL.
- Mover el cifrado de la clave del `.p12` a un KMS.
- Confirmar el concepto de **ISD**, marcado `verificado=False` en
  [`codigos_retencion.py`](../backend/app/sri/codigos_retencion.py). El resto está
  contrastado con la resolución NAC-DGERCGC26-00000009.

---

## 5. Montar el entorno

El proyecto se desarrolló en Windows y se trabajó después en Linux. Hay tres
cosas que hacen tropezar la primera vez.

### `requirements.txt` no se puede instalar tal cual

Dos pines rotos, **todavía sin corregir en el repositorio**:

| Pin | Problema |
|---|---|
| `pydantic[email]==2.11.9` | `google-genai==2.17.0` exige `pydantic>=2.12.5`. Conflicto real, independiente de la versión de Python |
| `psycopg[binary]==3.1.13` | No hay wheel para Python ≥3.13; la mínima publicada es 3.2.2 |

Se instaló con ambos relajados (`pydantic 2.13.4`, `psycopg 3.3.4`) y las
pruebas pasan igual. Se dejó sin tocar porque cambiar pines es decisión del
dueño del proyecto, pero **hay que corregirlo**.

### El venv y `node_modules` son de Windows

`backend/.venv/` contiene ejecutables `.exe`. En Linux hay que crear otro.
`frontend/node_modules` traía los binarios nativos de Windows y `vitest` ni
arrancaba (`Cannot find native binding` de rolldown): hay que reinstalar.

```bash
# Backend  (Python 3.13; con 3.14 no hay wheels para varias dependencias)
cd backend
python3.13 -m venv .venv-linux
.venv-linux/bin/pip install -r requirements.txt   # ver los pines de arriba
.venv-linux/bin/python -m pytest -q               # 325 pruebas

# Frontend
cd frontend
rm -rf node_modules package-lock.json && npm install
npx vitest run                                    # 234 pruebas
```

### Las pruebas ahora necesitan sesión

Desde el cierre del API, cualquier prueba nueva que llame al API tiene que pasar
su `TestClient` por `iniciar_sesion()` de
[`backend/tests/conftest.py`](../backend/tests/conftest.py). Si una prueba nueva
devuelve 401 en bloque, es esto.

Usa la cabecera `Authorization` y no la cookie a propósito: la cookie de sesión
se marca `Secure` y el `TestClient` habla HTTP, así que su almacén de cookies la
descartaría.

---

## 6. Cómo rehacer las cifras

```bash
grep -rhoE '@router\.(get|post|put|patch|delete)' backend/app/routers/*.py | wc -l   # 118
grep -cE '^class [A-Z]' backend/app/modelos_db.py                                    # 24
ls frontend/src/pages | wc -l                                                        # 17
cd backend && .venv-linux/bin/python -m pytest -q                                    # 325
cd frontend && npx vitest run                                                        # 234
grep -c 'dependencies=SESION_REQUERIDA' backend/app/main.py                          # 10
grep -ro 'Próximamente' frontend/src/pages/*/*.jsx | wc -l                           # 6
```

---

## 7. Convenciones que conviene no romper

Están detrás de decisiones que ya se tomaron y que no se pueden reconstruir
leyendo el código:

- **Todo en español**: nombres de variables, funciones y comentarios.
- **El dinero se guarda en `Numeric(14,6)`**, nunca en coma flotante.
- **El saldo no se guarda, se calcula** (`monto - cobrado`). Un saldo almacenado
  se desincroniza en cuanto alguien anula un recibo.
- **Los reportes cuentan solo comprobantes `Autorizado`.** Un borrador no existe
  para el SRI y no debe existir para el reporte: sumarlo lleva a declarar de más.
- **Gasto ≠ Egreso** y **Cuota ≠ Recibo**: la obligación y el movimiento de caja
  son cosas distintas, y entre una y otro pueden pasar treinta días.
- **El inventario se valora al costo**, no al precio de venta.
- **Los comentarios explican el porqué**, no el qué.
