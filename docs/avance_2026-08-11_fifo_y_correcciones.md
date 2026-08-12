# FIFO, IVA por línea en el gasto y tres correcciones de la otra rama

Fecha: **11 de agosto de 2026**

Esta tanda cierra tres de los cuatro pendientes que dejó
[`traspaso.md`](traspaso.md): el criterio contable sin decidir de Cuentas
(§4.4), tres de las cinco piezas identificadas en la rama `sri-facturas` (§4.3),
y los dos pines rotos de `requirements.txt` (§5). Queda pendiente la validación
completa contra Python 3.13/Linux, que no se pudo ejercitar en este entorno.

Verificado con la suite completa: **651 pruebas en verde** — 399 backend
(9 nuevas en `test_cuentas.py`), 252 frontend (1 nueva en `adaptadores.test.js`).

---

## 1. El abono suelto ahora se reparte, y el criterio es una decisión, no un hallazgo

`backend/app/routers/cuentas.py` — `crear_recibo`.

El problema documentado en `traspaso.md`: un recibo contra `comprobante_id`
directo —así se cobra una venta al contado— no bajaba ninguna cuota si ese
mismo comprobante además tenía un plan de cuotas. La agenda, que suma cuotas,
seguía mostrando pendiente lo que en caja ya se había cobrado.

**Se asume el criterio más común de cobranza: FIFO.** El abono se reparte
primero contra la cuota más próxima a vencer, y sigue con las siguientes hasta
agotarse. Si sobra después de cubrir todas, el resto queda como recibo suelto
contra el comprobante —igual que antes, para el caso sin cuotas o de
sobrepago—.

Es una asunción, no una certeza: el criterio contable correcto depende de cada
negocio (podría ser LIFO, o proporcional entre cuotas, o requerir que el
usuario elija). **Queda marcado como tal en el docstring del endpoint** para
que sea fácil de encontrar y de cuestionar.

Dos pruebas nuevas verifican el reparto y el caso de sobrepago:

```python
def test_un_abono_suelto_se_reparte_fifo_entre_las_cuotas(cliente):
    # 90.00 en 3 cuotas de 30.00; un abono de 45.00 satura la primera y
    # deja la segunda en 15.00 cobrados, la tercera intacta.
    ...

def test_un_abono_suelto_que_sobra_a_las_cuotas_queda_como_recibo_directo(cliente):
    # 50.00 en 2 cuotas; un abono de 70.00 las salda todas sin inventar
    # una tercera cuota para el sobrante.
    ...
```

---

## 2. IVA por línea en el gasto

`Gasto` solo guardaba `subtotal` e `iva` como dos montos sueltos, sin decir a
qué tarifa correspondían. El **formulario 104** no acepta eso: separa el
crédito tributario por tarifa —15 %, 5 %, 0 %, no objeto, exento—, no en un
total único.

Se agregó `codigo_iva` a `Gasto`, con los mismos códigos de la tabla 17 que ya
usa `Articulo` (`4`=15%, `5`=5%, `0`=0%, `6`=No objeto, `7`=Exento), validado
con el mismo catálogo `PORCENTAJES_IVA`:

```python
codigo_iva: Mapped[str] = mapped_column(String(2), default="4")
```

No se creó una tabla de líneas (`DetalleGasto`): un gasto es un solo documento
del proveedor, no una factura propia con renglones. Un código de tarifa por
gasto es proporcional al problema real; una tabla de líneas habría sido
construir para un caso que el sistema no tiene hoy.

En el formulario de gasto (`frontend/src/pages/Egresos/Egresos.jsx`) se agregó
el selector de tarifa, reutilizando el catálogo `TARIFAS_IVA` que ya existía en
`lib/sri/impuestos.js` para artículos —un solo catálogo de tarifas, no dos que
puedan desincronizarse.

## 3. Autorización del proveedor en el gasto

Se agregó `autorizacion_proveedor` a `Gasto`: la clave de acceso del
comprobante que el proveedor emitió, autorizada por el SRI a su nombre. Es dato
del ATS y sostiene el gasto como crédito tributario; sin un campo para
guardarla, no había dónde ponerla.

## 4. Un gasto ya no se puede registrar contra un cliente

`_validar_proveedor` en `egresos.py` solo comprobaba que el receptor existiera,
no que fuera proveedor. El desplegable del formulario ya filtra por rol, pero
esa es una barrera de interfaz: nada impedía a otro cliente del API —o a un
error de datos— registrar un gasto contra alguien marcado como `Cliente`.
Ahora el backend lo rechaza con 422 y dice qué rol tiene en realidad.

## 5. La identificación de un receptor vuelve a estar protegida al editar

`ReceptoresForm.jsx` tenía el candado invertido: el formulario nacía
**desbloqueado** al editar y **bloqueado** al crear. En modo edición se podía
reescribir el RUC o la cédula de un cliente que ya tiene facturas autorizadas
sin ninguna fricción —el banner de aviso aparecía, pero como si el usuario ya
hubiera pedido desbloquearlo, no como una protección activa—.

```js
// Antes: useState(!esEdicion ? true : false)  → bloqueado al CREAR
// Ahora: useState(esEdicion)                   → bloqueado al EDITAR
```

Al crear no hay ninguna identidad previa que proteger, así que el campo nace
editable. Al editar, el candado exige el toggle «Corregir identidad» a
propósito, que es donde ya vivía la advertencia sobre el 409.

## 6. Prueba de ida y vuelta del adaptador de receptores

`adaptadores.test.js`. Los dos adaptadores (`receptorDesdeApi` /
`receptorHaciaApi`) ya estaban completos —el fallo de «9 de 20 campos» que
documenta `traspaso.md` era de la otra rama, no de esta—, pero no había ninguna
prueba que lo garantizara hacia adelante. La nueva prueba pasa un registro con
los 20 campos por los dos adaptadores en cadena y comprueba que vuelve idéntico
al original. Si algún día se agrega un campo a uno de los dos y se olvida el
otro, esta prueba lo delata sin tener que levantar el backend.

## 7. Los pines rotos de `requirements.txt`

Documentados en `traspaso.md` §5 y **todavía sin corregir en el repositorio**
hasta ahora:

| Pin | Problema | Corregido a |
|---|---|---|
| `pydantic[email]==2.11.9` | `google-genai` exige `>=2.12.5`; conflicto real | `pydantic[email]>=2.12.5` |
| `psycopg[binary]==3.1.13` | Sin wheel para Python ≥3.13 | `psycopg[binary]>=3.2.2` |

Verificado con `pip install --dry-run` que la instalación resuelve limpia, y
reinstalado de verdad en el entorno de desarrollo: `psycopg` subió a 3.3.4 sin
romper ninguna prueba.

Esto **no se probó en Linux/Python 3.13**, que es donde el problema original
apareció; solo se confirma que el `.venv` de Windows/Python 3.12 sigue sano con
los pines relajados. Sigue pendiente la migración a `python3.13 -m venv` en
Linux que describe `traspaso.md`.

---

## Migración de base de datos

`backend/scripts/migrar_gastos_iva.py` — agrega `codigo_iva` y
`autorizacion_proveedor` a `gastos`. Es idempotente, igual que
`migrar_compras_gastos.py` de la otra rama: `crear_tablas()` solo crea tablas
que no existen, no columnas nuevas en las que ya están.

```bash
cd backend
.venv/Scripts/python scripts/migrar_gastos_iva.py
```

---

## Lo que sigue pendiente

De las cinco piezas de `traspaso.md` §4.3, quedan **una sin portar**:

- Prueba de ida y vuelta del adaptador de **artículos** — se hizo la de
  receptores porque era la que el documento señalaba con el fallo real de
  «9 de 20 campos»; no se verificó si el adaptador de artículos tiene el mismo
  problema.

Y de §4.4, el resto de la lista que no se tocó en esta tanda: el certificado
`.p12` (§4.1) y los permisos por rol más allá de administrador (§4.2).

Con el criterio FIFO de este documento decidido y en producción, conviene que
alguien con conocimiento contable del negocio lo revise: si el negocio real
usa un criterio distinto, es cuestión de cambiar el `order_by` de
`cuotas_pendientes` en `crear_recibo`.
