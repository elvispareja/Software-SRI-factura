# Avance — Fase 2-A: Cuentas pendientes + Anticipos + Reportes avanzados

> **Fecha:** 10 de agosto de 2026
> **Agente:** Fase 2-A
> **Mockup:** `Cloud World Office.dc.html` (3618 líneas) — `isRepApp` (1611-1728), `isCuentas` (1729-2102), `isAnticipos` (2105-2317)
> **Plan:** `~/.commandcode/plans/cloud-world-frontend-adopcion.md` (fase 1 previa por Agente 1)
> **Estado:** completado — `oxlint` 2 warnings preexistentes, `vite build` OK

---

## 1. Qué se mapeó del mockup

### Cuentas (`isCuentas` / `cx.*` — líneas 1729-2102)

| Mockup | Implementado | Fuente |
|---|---|---|
| Tabs: Inicio / Recep / Gestión mensual / Historial / Vencidos / Reportes + Volver | 6 tabs en `Cuentas.jsx` (Inicio, Receptores, Gestión mensual, Historial, Vencidos, Reportes) + Link Volver | Estado local `tab` |
| Inicio: 4 KPIs + agenda semanal (mockup `cx.kpis`, `cx.agendaTitle`) | 4 KPIs derivados de `panel.por_cobrar` (saldo pendiente, vencidas, vencen hoy, próximos 7 días) | `GET /api/reportes/panel` → `panelDesdeApi().porCobrar` |
| Recep: filtros + tabla saldos (NOMBRE/TIPO/IDENTIFICACIÓN/SALDO/ACCIONES) + paginación + modales Saldo y Config | Tabla con `useRecurso('/comprobantes?estado_pago=Por Cobrar')` agrupada por receptor + `useTablaFiltrada` + modal Registrar Saldo Anterior (local) + modal Configuración Recibos | `GET /api/comprobantes?estado_pago=Por Cobrar` + saldos locales |
| Gestión: `mesLabel`, nav Hoy/prev/next, empty | `mesLabel` con `MESES_L`, nav mes, empty + banner Próximamente | Estado local `mesDate` |
| Historial: `histTiles` (4 tiles), search, filtros Estado, tabla 10 cols | 4 tiles + search + filtros + tabla + banner Próximamente | Placeholder (requiere tabla recibos) |
| Vencidos: badges saldo/vencen hoy, search, tabla | Badges + search + tabla + banner Próximamente | Placeholder (requiere vencimientos) |
| Reportes: 5 cards (Saldo pendiente, Agenda cuotas, Recibos, Rotación, Historial por cliente) | 5 cards con banner Próximamente + botón Descargar | Placeholder (requiere cuotas/recibos) |
| Modal Saldo: receptor/payOpts/fecha/monto/detalle | Modal local con validación mínima, persiste en `saldosLocal` | Estado local |
| Modal Config Recibos: toggles ocultarTotal/mostrarPorDoc | Modal con toggles `cfg.ocultarTotal` / `cfg.mostrarPorDoc` | Estado local |

**Sin tabla nueva.** Se usa `GET /api/comprobantes?estado_pago=Por Cobrar` y `GET /api/reportes/panel` (porCobrar). El resto es placeholder con banner `Próximamente` sin romper la vista — justificado: cuotas/recibos/vencimientos requieren modelo contable dedicado (cuota, vencimiento, recibo, asiento) que no existe en `modelos_db.py`.

### Anticipos (`isAnticipos` + `isAnticipoModal` — líneas 2105-2317)

| Mockup | Implementado |
|---|---|
| Filtros: estado/tipo/desde/hasta/query/pageSize | Selects Estado/Tipo, inputs date Desde/Hasta, search, pageSize — todo filtra `useTablaFiltrada` |
| Tabla 11 cols: #/FECHA/TIPO/RECEPTOR/DETALLE/MONTO/MONTO FACTURADO/SALDO/ESTADO/ASIENTO/ACCIONES | Tabla 11 cols idéntica, con `chipTipo` (ARD naranja / APP azul) y `chipEstado` |
| Menú Anular/Devolver/Corregir | 3 botones por fila: Anular (→ Anulado), Devolver (→ Devuelto), Corregir (→ Pendiente) — operan sobre array local |
| Info box: ARD/APP + acciones según estado | Info box igual al mockup |
| Modal Nuevo Anticipo: receptor/payOpts (PAGOS_SRI 8 opciones), toggle apertura, monto anticipado, cuenta | Modal con receptor (5 mock), switch Recibido/Pagado, obs, payOpts con monto, monto anticipado calculado, cuenta |

**Backend:** no hay `GET /api/anticipos`. UI 100% local en `frontend/src/data/anticipos.js` (5 registros mock) + banner `Gestión de anticipos — funcionalidad en desarrollo` y CTA que abre modal local. Ver contrato propuesto abajo.

### Reportes avanzados (`isRepApp` / `ra.*` — líneas 1611-1728)

| Mockup | Implementado | Endpoint real |
|---|---|---|
| 8 tabs: comprobantes/notasVenta/egresos/cotizaciones/ncnd/inventario/receptores (+ volver) | 7 tabs top (`TABS_TOP`) + contenido por tab | — |
| Hero: CENTRO DE REPORTES + title/subtitle + icon | `heroAvanzado` con icon + eyebrow + title/sub + selectors anio/mes | — |
| Card: radios Excel/PDF + fields search/select/date/usuarios + toggle + btn Descargar | Radios Excel/PDF globales + toggle "Filtrar por rango de fechas" + 8 tabs con contenido específico | — |
| — | Tab **Comprobantes**: 3 sub-pestañas IVA/Retenciones/Ventas (existentes) + CSV + `PanelEstadoSri` | `GET /reportes/iva`, `/retenciones`, `/ventas`, `/ventas/por-tipo`, `/estado-sri`, `urlCsv()` |
| `inventario` | Tab **Inventario**: top artículos por importe | `GET /reportes/articulos` (nuevo `cargarArticulos`) |
| `receptores` | Tab **Receptores**: top clientes | `GET /reportes/clientes` (nuevo `cargarClientes`) |
| `notasVenta`, `egresos`, `cotizaciones`, `ncnd` | Tabs placeholder con 4 fields disabled + banner Próximamente + botón Descargar (alert) | Sin endpoint — documentado |

**API ampliada:** `frontend/src/api/reportes.js` añade `cargarClientes`, `cargarArticulos`, `cargarVentasPorMes` (por si se necesita serie anual en el futuro).

**CSS:** `Reportes.module.css` añade bloque `Reportes Avanzados (isRepApp)`: `heroAvanzado`, `tabsTop`, `cardAvanzadoHeader`, `radiosRow`, `toggleRow`, `bannerProx`, `placeholderFields`.

---

## 2. Endpoints usados

| Endpoint | Uso |
|---|---|
| `GET /api/reportes/panel` | KPIs Cuentas (porCobrar) |
| `GET /api/comprobantes?estado_pago=Por Cobrar&tamano=200` | Saldos por receptor en Cuentas |
| `GET /api/reportes/iva?anio&mes` + `/iva/csv` | Reportes → Comprobantes → IVA |
| `GET /api/reportes/retenciones?anio&mes` + `/retenciones/csv` | Reportes → Comprobantes → Retenciones |
| `GET /api/reportes/ventas?anio&mes` + `/ventas/por-tipo` + `/ventas/csv` | Reportes → Comprobantes → Ventas |
| `GET /api/reportes/estado-sri?anio&mes` | Reportes → Estado SRI |
| `GET /api/reportes/clientes?anio&mes&limite=10` | Reportes → Receptores |
| `GET /api/reportes/articulos?anio&mes&limite=10` | Reportes → Inventario |
| `GET /api/reportes/ventas/por-mes?anio` | Reservado (serie anual) |

---

## 3. Qué quedó placeholder y por qué

| Área | Por qué placeholder |
|---|---|
| Cuentas — Gestión mensual por cuotas, Historial de recibos, Vencidos con mora, Reportes de cuentas | Requieren tablas `cuota`, `recibo`, `vencimiento` y lógica contable (cuotas por documento, recibos globales vs por cuota, mora, asiento). No se inventó tabla: se muestra banner `Próximamente` con descripción de lo que requiere. |
| Cuentas — Modal Saldo: persistencia | Guarda en `saldosLocal` (memoria). Cuando exista `POST /api/cuentas/saldos`, se cambia a `api.crear('/cuentas/saldos', ...)` sin tocar el markup. |
| Anticipos — todo | No hay tabla `anticipo` ni router. Datos en `data/anticipos.js`. Ver contrato propuesto. |
| Reportes — tabs notasVenta/egresos/cotizaciones/ncnd | No hay `GET /reportes/notas-venta` ni similares. Se deja card placeholder con fields disabled + banner. El día que existan, se añade un `cargarNotasVenta` en `api/reportes.js` y un `ReporteNotasVenta` como los existentes. |
| Reportes — PDF | `urlCsv` solo genera CSV. El mockup ofrece Excel/PDF; hoy `Excel` descarga CSV (con `;` y BOM) y `PDF` avisa `próximamente`. Generar PDF requiere `GET /reportes/:reporte/pdf` en el backend. |

---

## 4. Cómo probar

```bash
cd frontend
npm run lint   # 2 warnings preexistentes (EstacionComprobante fast-refresh, Store sin uso)
npm run build  # OK

# Smoke en navegador (con backend en 8000):
# /cuentas            -> tabs Inicio/Recep/Gestión/Historial/Vencidos/Reportes; en Recep: saldos reales si hay comprobantes Por Cobrar, modal Registrar Saldo
# /cuentas?tipo=pagar -> modo Pagar
# /anticipos          -> 5 anticipos mock, filtros, Crear Anticipo (modal local), Anular/Devolver/Corregir
# /reportes           -> hero + 7 tabs top + radios Excel/PDF + toggle rango
#   -> Comprobantes -> sub-tabs IVA/Retenciones/Ventas + Estado SRI (conectado)
#   -> Inventario    -> top artículos (conectado)
#   -> Receptores    -> top clientes (conectado)
#   -> resto         -> placeholder Próximamente
```

Sin backend, `useRecurso` cae a `[]` y `useReporte` muestra `SinConexion` — no se rompe la vista.

---

## 5. Contrato propuesto para anticipos

Para cuando exista el backend. Documenta la forma esperada para que el frontend solo cambie `data/anticipos.js` → `useRecurso('/anticipos')`.

### Modelo `Anticipo` (SQLAlchemy sugerido en `backend/app/modelos_db.py`)

```python
class Anticipo(Base):
    __tablename__ = "anticipos"
    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(String(3))  # ARD | APP
    receptor_id: Mapped[int | None] = mapped_column(ForeignKey("receptores.id", ondelete="SET NULL"))
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")
    receptor_identificacion: Mapped[str] = mapped_column(String(20), default="")
    detalle: Mapped[str] = mapped_column(String(300), default="")
    monto: Mapped[Decimal] = mapped_column(DINERO)
    facturado: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    # saldo = monto - facturado (calculado, no columna)
    estado: Mapped[str] = mapped_column(String(30), default="Pendiente")  # Pendiente | Aplicado | Anulado | Residuo pendiente | Devuelto
    asiento: Mapped[str | None] = mapped_column(String(20), default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
    # Relación con pagos (formas de pago del anticipo)
    pagos: Mapped[list[PagoAnticipo]] = relationship(back_populates="anticipo", cascade="all, delete-orphan")

class PagoAnticipo(Base):
    __tablename__ = "pagos_anticipo"
    id: Mapped[int] = mapped_column(primary_key=True)
    anticipo_id: Mapped[int] = mapped_column(ForeignKey("anticipos.id", ondelete="CASCADE"))
    metodo: Mapped[str] = mapped_column(String(60))  # Efectivo | Transferencia | ...
    monto: Mapped[Decimal] = mapped_column(DINERO)
    anticipo: Mapped[Anticipo] = relationship(back_populates="pagos")
```

### Endpoints `backend/app/routers/anticipos.py` (prefijo `/anticipos`)

| Método | Ruta | Query | Descripción |
|---|---|---|---|
| `GET` | `/anticipos` | `?estado=&tipo=&desde=&hasta=&buscar=&pagina=&tamano=` | Lista paginada, filtra por estado/tipo/rango/búsqueda; devuelve lista + `X-Total-Registros` |
| `POST` | `/anticipos` | body `AnticipoEntrada` | Crea anticipo + pagos, genera asiento |
| `GET` | `/anticipos/{id}` | — | Detalle |
| `POST` | `/anticipos/{id}/anular` | — | Solo si `estado==Pendiente`; revierte asiento |
| `POST` | `/anticipos/{id}/devolver` | — | Solo si `estado==Residuo pendiente`; asiento por saldo |
| `POST` | `/anticipos/{id}/corregir` | body parcial | Solo si `Pendiente`; reversa y regenera asiento |

### Esquemas `backend/app/esquemas.py`

```python
class PagoAnticipoEntrada(BaseModel): metodo: str; monto: Decimal
class AnticipoEntrada(BaseModel):
    fecha: date; tipo: Literal["ARD","APP"]; receptor_id: int
    detalle: str = ""; pagos: list[PagoAnticipoEntrada]
class AnticipoSalida(BaseModel):
    id: int; fecha: date; tipo: str; receptor_razon_social: str
    detalle: str; monto: Decimal; facturado: Decimal; saldo: Decimal
    estado: str; asiento: str | None; pagos: list[PagoAnticipoEntrada]
```

### Adaptador frontend `frontend/src/api/adaptadores.js`

```js
export const anticipoDesdeApi = (r) => ({
  id: r.id, fecha: r.fecha, tipo: r.tipo,
  receptor: r.receptor_razon_social, detalle: r.detalle,
  monto: Number(r.monto), facturado: Number(r.facturado),
  saldo: Number(r.saldo), estado: r.estado, asiento: r.asiento ?? '—',
});
```

### Migración del componente

```diff
- import { ANTICIPOS_MOCK } from '../../data/anticipos';
- const [anticipos, setAnticipos] = useState(ANTICIPOS_MOCK);
+ import { useRecurso } from '../../hooks/useRecurso';
+ import { anticipoDesdeApi } from '../../api/adaptadores';
+ const recurso = useRecurso('/anticipos', { parametros: { tamano: 100 } });
+ const anticipos = recurso.datos.map(anticipoDesdeApi);
```

Y `guardarAnticipo` pasa de `setAnticipos([rec, ...prev])` a `api.crear('/anticipos', payload)`.

---

## 6. Archivos tocados / creados

| Archivo | Acción |
|---|---|
| `frontend/src/data/anticipos.js` | **Creado** — mock local + constantes |
| `frontend/src/pages/Cuentas/Cuentas.jsx` | **Creado** — 6 tabs, KPIs porCobrar, saldos reales, modales, placeholders |
| `frontend/src/pages/Cuentas/Cuentas.module.css` | **Creado** — estilos fieles al mockup (kpis, agenda, filtros, tablas, modales, tabs) |
| `frontend/src/pages/Anticipos/Anticipos.jsx` | **Creado** — filtros, tabla 11 cols, infoBox, modal con payOpts |
| `frontend/src/pages/Anticipos/Anticipos.module.css` | **Creado** — card, filtros, tabla, overlay modal, kindCards |
| `frontend/src/pages/Reportes/Reportes.jsx` | **Expandido** — 7 tabs top + hero + radios/toggle + TabComprobantes (3 sub-tabs) + TabInventario + TabReceptores + TabPlaceholder×4 + PanelEstadoSri |
| `frontend/src/pages/Reportes/Reportes.module.css` | **Expandido** — heroAvanzado, tabsTop, cardAvanzadoHeader, bannerProx, placeholderFields |
| `frontend/src/api/reportes.js` | **Ampliado** — `cargarClientes`, `cargarArticulos`, `cargarVentasPorMes` |
| `frontend/src/App.jsx` | **Ampliado** — rutas `cuentas` y `anticipos` |
| `docs/avance_fase2_cuentas_anticipos_reportes.md` | **Este archivo** |

No se tocó backend salvo documentación. `frontend/src/components/Layout/Layout.jsx` ya tenía `Cuentas`/`Anticipos`/`Reportes` en el sidebar (fase 1).

---

## 7. Decisiones de diseño

- **No inventar tablas.** Saldos por cobrar se agrupan desde `comprobantes` existentes; cuotas/recibos/anticipos se simulan localmente. Evita deuda de migración y mantiene `modelos_db.py` coherente.
- **Tablas con `TablaCWO` vs nativa.** `Cuentas` usa tabla nativa (estructura del mockup con THEAD específico y paginación propia vía `useTablaFiltrada`); `Anticipos` igual. `Reportes` mantiene tablas existentes para IVA/Retenciones/Ventas y añade dos más para inventario/receptores.
- **Download CSV vs Excel/PDF.** El backend solo expone CSV (`;` + BOM). El mockup ofrece Excel/PDF: se respeta el selector pero hoy ambos descargan CSV; PDF queda como `Próximamente` con TODO en este doc.
- **`urlCsv` parametrizado por `anio`/`mes`:** los nuevos tabs Inventario/Receptores reutilizan `urlCsv('ventas', anio, mes)` como descarga provisional — no tienen CSV propio hasta que se añada `GET /reportes/{inventario,receptores}/csv`.
