# Permisos sobre operaciones sensibles, prueba de artículos y verificación de los pines

Fecha: **12 de agosto de 2026**

Continúa directamente de
[`avance_2026-08-11_fifo_y_correcciones.md`](avance_2026-08-11_fifo_y_correcciones.md)
y cierra los puntos que quedaban de [`traspaso.md`](traspaso.md) §4.2 y §4.3, más
la verificación pendiente de §5.

---

## 1. Los pines de `requirements.txt`, verificados sin poder ejecutar

La tanda anterior relajó `pydantic[email]` y `psycopg[binary]`, pero solo se
había probado en Windows/Python 3.12 —donde el problema original no
existe—. Este entorno no tiene Linux real (ni WSL con una distribución
instalada, ni Docker), así que no se pudo correr la suite en Python 3.13.

Lo que sí se pudo hacer: pedirle a `pip` que resuelva las dependencias **para
esa plataforma sin instalarlas**, con `--platform manylinux2014_x86_64
--python-version 313 --implementation cp --abi cp313`. Es una verificación de
instalabilidad, no de ejecución, pero confirma lo que hacía falta confirmar:

```
psycopg_binary-3.3.4-cp313-cp313-manylinux2014_x86_64...whl   (existe)
cryptography-50.0.0-cp311-abi3-manylinux2014_x86_64...whl     (existe, abi3)
lxml-6.1.1-cp313-cp313-manylinux2014_x86_64...whl              (existe)
pydantic-2.13.4-py3-none-any.whl                                (universal)
google_genai-2.17.0-py3-none-any.whl                            (universal)
email_validator-2.3.0-py3-none-any.whl                          (universal)
```

Todas las dependencias con extensión nativa tienen wheel publicada para
Python 3.13/manylinux. **Sigue sin probarse si el código en sí corre sin
errores en ese entorno** —eso solo lo confirma ejecutar la suite ahí—.

## 2. El criterio FIFO, confirmado por el negocio

La tanda anterior implementó el reparto de abonos sueltos como una asunción
explícita, documentada como tal en el docstring de `crear_recibo` porque era
una decisión contable, no técnica. **Se preguntó y se confirmó: FIFO es el
criterio correcto.** No se tocó código; queda anotado aquí porque cierra un
pendiente real, no uno técnico.

## 3. Prueba de ida y vuelta del adaptador de artículos

`traspaso.md` §4.3 señalaba la de receptores porque ahí estaba el fallo
concreto («9 de 20 campos», heredado de la rama `sri-facturas`). Faltaba
comprobar si `articuloDesdeApi`/`articuloHaciaApi` tenían el mismo problema.

**No lo tenían** —ambos adaptadores ya cubrían los 18 campos—, pero tampoco
había ninguna prueba que lo garantizara hacia adelante. La nueva prueba pasa
un registro completo por los dos adaptadores en cadena y comprueba que vuelve
igual, con una salvedad documentada en el propio test: `precio`, `costo` y
`stock` cruzan como número en vez de como texto porque así los usa la
interfaz para calcular, y eso es deliberado, no una pérdida de dato.

## 4. Permisos por rol en las tres operaciones más sensibles

`traspaso.md` §4.2 decía que aplicar `administrador_actual` a operaciones
sensibles era «trabajo mecánico» porque la dependencia ya existía y estaba
probada. Se aplicó a las tres que el propio documento nombraba:

| Endpoint | Router | Por qué es sensible |
|---|---|---|
| `PUT /configuracion/empresa` | `configuracion.py` | Cambia el RUC y la razón social con la que se factura |
| `POST /configuracion/firma` | `configuracion.py` | Sube el certificado `.p12`: la llave con la que se firma en nombre de la empresa |
| `DELETE /configuracion/firma` | `configuracion.py` | Desactiva esa misma llave |
| `POST /comprobantes/{id}/anular` | `comprobantes.py` | Operación irreversible sobre la contabilidad |

No se tocó nada más: ni establecimientos, ni cuentas bancarias, ni las
listas auxiliares. `traspaso.md` nombraba estas tres explícitamente como
ejemplo; el resto de operaciones sensibles del sistema —hay más, seguramente—
sigue sin diferenciar roles y queda para una revisión aparte, no para esta
tanda de aplicación mecánica.

### Una prueba que no probaba nada, y el porqué

Las 399 pruebas de antes de este cambio **seguían pasando sin ningún
ajuste** después de agregar la comprobación de rol. No porque el cambio
fuera inofensivo, sino porque **el usuario de pruebas de cada módulo es
siempre el primero de su base de datos aislada**, y el primero es
automáticamente administrador. Ninguna prueba existente verificaba el caso de
un operador sin ese rol.

Se agregaron tres pruebas nuevas que registran un segundo usuario (operador,
por construcción) y confirman el 403:

```python
def test_un_operador_no_puede_editar_la_empresa(cliente): ...
def test_un_operador_no_puede_subir_ni_quitar_la_firma(cliente, p12): ...
def test_un_operador_no_puede_anular(cliente, cliente_id): ...
```

### El efecto secundario que casi pasa desapercibido

La primera versión de estas pruebas fallaba en cascada —nueve pruebas del
mismo archivo, ninguna relacionada a simple vista—. La causa: el módulo de
`test_configuracion_seguridad.py` autentica su `cliente` **por cookie**, y
`POST /auth/token` manda `Set-Cookie` en la respuesta sin importar de quién
sea el login. Iniciar sesión como operador para probar el 403 **pisaba la
cookie del administrador** en el mismo `TestClient`, y todas las pruebas
posteriores del módulo quedaban autenticadas como operador sin que nada lo
avisara —hasta que empezaron a fallar por 403 donde se esperaba 200 o 201—.

Se corrigió guardando la cookie del administrador antes del login del
operador y restaurándola después:

```python
cookie_admin = dict(cliente.cookies)
respuesta = cliente.post("/api/auth/token", data={...})  # pisa la cookie
cliente.cookies.clear()
cliente.cookies.update(cookie_admin)                      # se restaura
```

Es el mismo tipo de fallo silencioso que motivó escribir pruebas para este
sistema en primer lugar: nada en el mensaje de error decía «tu prueba cambió
de usuario a mitad de módulo». Solo se encontró porque las nueve pruebas que
fallaron no tenían ninguna relación aparente entre sí, lo que en este
proyecto siempre ha sido la señal de un estado compartido roto, no de nueve
fallos independientes.

---

## Verificación

**655 pruebas en verde** — 402 backend (3 nuevas: los tres 403 de rol), 253
frontend (1 nueva: ida y vuelta de artículos).

```bash
cd backend  && .venv/Scripts/python -m pytest -q     # 402
cd frontend && npx vitest run                          # 253
```

---

## Lo que sigue pendiente

- **El resto de operaciones sensibles sin diferenciar rol.** Se protegieron
  tres como aplicación mecánica de lo que `traspaso.md` ya señalaba; no se
  hizo un barrido del API completo buscando cuáles otras deberían protegerse
  del mismo modo (por ejemplo: crear/editar establecimientos y puntos de
  emisión, que reservan secuenciales; desactivar cuentas bancarias).
- **La suite de Python 3.13/Linux, sin ejecutar todavía.** Solo se verificó
  que las dependencias se pueden instalar ahí; falta comprobar que el código
  corre.
- El certificado `.p12` acreditado sigue siendo el único bloqueante que no
  depende del desarrollo.
