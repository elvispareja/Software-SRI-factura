# Avance — Tanda 7: Persistencia de todos los documentos

> **Fecha:** 8 de agosto de 2026
> **Estado:** completado y verificado — 108 tests de backend, 24 verificaciones de punta a punta contra el servidor real

Cierra la brecha que quedaba: las pantallas que tenían UI pero no guardaban nada
ahora persisten, y se añade el tipo de documento que faltaba (notas de crédito y
débito).

---

## 1. Un modelo para todos los documentos de venta

Factura, cotización, nota de venta, liquidación de compra y notas de
crédito/débito comparten cabecera, receptor, detalle y totales, así que
comparten tabla y endpoint, y se distinguen por `tipo`. Separarlos en cinco
tablas casi idénticas habría obligado a duplicar el listado, el cálculo y la
emisión.

Los campos propios de cada tipo van como columnas opcionales documentadas:

| Campo | Tipo que lo usa |
|---|---|
| `validez_dias` | Cotización |
| `cod_doc_modificado`, `num_doc_modificado`, `fecha_doc_modificado`, `motivo` | Notas de crédito y débito |

**La guía de remisión sí tiene tabla propia** (`GuiaRemision` + `ItemGuiaRemision`):
no lleva importes ni impuestos, sino fechas, transportista, placa y direcciones
de partida y llegada.

### Validaciones por tipo

| Regla | Por qué |
|---|---|
| Una nota de crédito/débito exige los tres campos de referencia | Sin ellos el SRI la rechaza. El error nombra exactamente cuáles faltan |
| La liquidación de compra exige un receptor con rol **Proveedor** | Se emite por cuenta de quien no puede facturar; contra un cliente no tiene sentido |
| La guía exige un receptor con rol **Transportista** | El XML identifica a quien traslada; un cliente ahí produce una guía incorrecta |
| La dirección es obligatoria solo en comprobantes electrónicos | Una cotización no viaja al SRI, así que no la necesita |
| La fecha fin de la guía no puede ser anterior al inicio | El SRI lo valida |

---

## 2. Secuenciales por tipo de documento

**Este era el cambio estructural de la tanda.** El SRI exige series
independientes: la factura 000000135 y la nota de crédito 000000135 coexisten
sin conflicto. Antes solo existía `secuencial_factura`, una columna.

Se añadió la tabla `SecuencialDocumento`, con clave única por
`(punto_emision, tipo)`. Una tabla en vez de una columna por tipo evita migrar
el esquema cada vez que se soporte un comprobante más.

La reserva vive en `app/servicios/secuenciales.py` y se hace **con bloqueo dentro
de la transacción del llamador**: si dos peticiones llegan a la vez, la segunda
espera y obtiene el siguiente número. Un secuencial repetido hace que el SRI
rechace el comprobante.

`PuntoEmision.secuencial_factura` sigue existiendo como el valor inicial que el
usuario configura en pantalla; a partir de la primera emisión el contador vivo es
la tabla, y ambos se mantienen sincronizados para que Configuraciones muestre el
próximo número real.

Verificado contra el servidor real:

```
factura        001-001-000000135   (arranca en el configurado)
nota de venta  001-001-000000001   (serie propia, arranca en 1)
cotización     001-001-000000001   (serie propia)
guía           001-001-000000001   (serie propia)
factura        001-001-000000136   (no se reusa)
```

---

## 3. Frontend conectado

Ya no queda ninguna pantalla con datos inventados como única fuente:

| Pantalla | Antes | Ahora |
|---|---|---|
| Cotizaciones | Mock local | `GET /comprobantes?tipo=Cotización` |
| Notas de Venta | Mock local | `GET /comprobantes?tipo=Nota de Venta` |
| Liquidaciones | Mock local | `GET /comprobantes?tipo=Liquidación de Compra` |
| Guías de Remisión | Mock local | `GET /guias` |
| Configuraciones | Estado local | `GET`/`PUT /configuracion/empresa` + `GET /configuracion/establecimientos` |

Todas heredan el comportamiento ya establecido: esqueleto de carga, error con
reintento, y **caída a datos de demostración con banner visible** si el backend
no responde. Configuraciones además muestra el resultado del guardado y
deshabilita el botón mientras el RUC no sea válido.

Se añadieron `src/api/documentos.js` y `src/api/configuracion.js` con los
adaptadores en ambos sentidos, siguiendo el patrón que ya usaban Receptores,
Artículos y Comprobantes.

---

## 4. Notas de Crédito y Débito

Nueva pantalla `NotaCreditoForm`, parametrizada por variante:

- **Nota de crédito** — devuelve o anula valor (devoluciones, descuentos posteriores, anulación).
- **Nota de débito** — aumenta el valor (intereses por mora, gastos no facturados).

El formulario pide la referencia al documento original **antes que nada** y el
banner cambia de aviso a informativo solo cuando está completa, porque sin ella
el SRI rechaza el comprobante. Reutiliza `DocumentoVentaForm`, así que hereda el
buscador de receptores, la grilla de ítems y el motor de cálculo.

Accesible desde el listado de Comprobantes y desde la paleta de comandos, que
ahora cubre las 10 secciones y 9 acciones de creación.

### Anulación

Nuevo endpoint `POST /comprobantes/{id}/anular`, con una regla que importa:
**un comprobante ya autorizado por el SRI no se anula desde aquí.** Se corrige
emitiendo una nota de crédito, que es lo que reconoce la administración
tributaria. El endpoint devuelve 409 explicándolo.

---

## 5. Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **108/108** (86 previos + 22 nuevos) |
| **Verificación de punta a punta contra el servidor real** | **24/24** |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |

Los 22 tests nuevos cubren: series independientes por tipo, referencia
obligatoria en notas, rol del receptor en liquidaciones y guías, dirección
obligatoria solo en comprobantes electrónicos, anulación y sus límites, filtros
del listado, y validación de fechas e ítems de la guía.

La verificación de punta a punta arrancó el servidor de verdad, sembró la base y
comprobó cada regla contra HTTP real, incluyendo que el RIDE devuelva un PDF y
que una cotización no genere XML del SRI.

---

## 6. Qué queda

1. **El certificado `.p12` de entidad acreditada** — el único bloqueante para emitir de verdad *(dejado para el final por decisión del usuario)*.
2. **Formularios que aún no envían al API.** Los listados ya leen del backend, pero los formularios de creación (factura, cotización, nota de venta, liquidación, guía, nota de crédito) todavía calculan en memoria sin hacer `POST`. Los endpoints y los adaptadores ya existen: falta cablear el botón de guardar.
3. **Persistencia de cuentas bancarias y firma electrónica** en Configuraciones — el resto de la pantalla ya guarda.
4. **Antes de producción:** definir `CLAVE_SECRETA`, mover el token a cookie `HttpOnly`, migrar a PostgreSQL, y contrastar los cantones con la codificación del INEC.
