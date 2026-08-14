import { useCallback, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Download,
  Percent,
  Receipt,
  SearchX,
  TrendingUp,
  FileText,
  FileSpreadsheet,
  Package,
  Users,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import {
  MESES,
  cargarIva,
  cargarResumenVentas,
  cargarRetenciones,
  cargarVentasPorTipo,
  cargarEstadoSri,
  cargarNotasVenta,
  cargarCotizaciones,
  cargarNotas,
  cargarEgresos,
  cargarInventario,
  cargarReceptores,
  inventarioDesdeApi,
  receptoresDesdeApi,
  porReceptorDesdeApi,
  notasDesdeApi,
  egresosDesdeApi,
  ivaDesdeApi,
  resumenDesdeApi,
  retencionesDesdeApi,
  urlCsv,
  urlPdf,
} from '../../api/reportes';
import { useReporte } from '../../hooks/useReporte';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { ErrorCarga, SinConexion, TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './Reportes.module.css';

/**
 * Reportes Avanzados — mockup isRepApp (líneas 1611-1728) mapeado a endpoints reales.
 *
 * 8 tabs del mockup (ra.tabs): comprobantes / notasVenta / egresos / cotizaciones
 * / ncnd / inventario / receptores (+ volver). Cada card tiene radios Excel/PDF,
 * fields search/select/date/usuarios y toggle "Filtrar por rango de fechas".
 *
 * Endpoints reales disponibles (backend/app/routers/reportes.py):
 *  - GET /reportes/iva?anio&mes (104) + /iva/csv
 *  - GET /reportes/retenciones?anio&mes (103) + /retenciones/csv
 *  - GET /reportes/ventas?anio&mes + /ventas/por-tipo + /ventas/csv
 *  - GET /reportes/clientes?anio&mes (top clientes) — sin CSV dedicado
 *  - GET /reportes/articulos?anio&mes (top artículos) — sin CSV dedicado
 *  - GET /reportes/estado-sri + /reportes/panel (porCobrar)
 *
 * Las ocho pestañas tienen datos reales y el selector de formato descarga de
 * verdad: CSV (lo que Excel abre directo) o PDF, según lo elegido.
 */

// `sinCsv` marca las secciones que el backend solo sirve en PDF: ahí no hay
// endpoint /csv que ofrecer, así que la opción Excel se deshabilita en vez de
// dejar un enlace que devolvería 404.
const TABS_TOP = [
  { id: 'comprobantes', label: 'Comprobantes', Icon: FileText },
  { id: 'notasventa', label: 'Notas de Venta', Icon: Receipt, sinCsv: true },
  { id: 'egresos', label: 'Egresos', Icon: TrendingDown },
  { id: 'cotizaciones', label: 'Cotizaciones', Icon: FileSpreadsheet, sinCsv: true },
  { id: 'ncnd', label: 'Notas Débito / Crédito', Icon: FileText },
  { id: 'inventario', label: 'Inventario', Icon: Package },
  { id: 'receptores', label: 'Receptores', Icon: Users },
];

const PESTANAS_COMPROBANTES = [
  { id: 'iva', etiqueta: 'IVA en ventas', Icon: Percent },
  { id: 'retenciones', etiqueta: 'Retenciones', Icon: Receipt },
  { id: 'ventas', etiqueta: 'Ventas', Icon: TrendingUp },
];

const ANIO_ACTUAL = new Date().getFullYear();
const ANIOS = Array.from({ length: 6 }, (_, i) => ANIO_ACTUAL - i);

export default function Reportes() {
  const [topTab, setTopTab] = useState('comprobantes');
  const [anio, setAnio] = useState(ANIO_ACTUAL);
  const [mes, setMes] = useState(new Date().getMonth() + 1);
  const [formato, setFormato] = useState('Excel');

  const hayCsv = !TABS_TOP.find((t) => t.id === topTab)?.sinCsv;

  // Al entrar en una sección que solo existe en PDF se cambia el formato en
  // lugar de dejarlo en un Excel imposible: el botón de la tarjeta descargaría
  // un enlace roto.
  const cambiarTab = (id) => {
    setTopTab(id);
    if (TABS_TOP.find((t) => t.id === id)?.sinCsv) setFormato('PDF');
  };

  const hero = useMemo(() => {
    const map = {
      comprobantes: { title: 'Reportes de facturación', subtitle: 'Consulta ventas, productos, utilidad y desglose de comprobantes.' },
      notasventa: { title: 'Reportes de notas de venta', subtitle: 'Consulta notas de venta, productos y desglose de documentos.' },
      egresos: { title: 'Reportes de egresos', subtitle: 'Consulta compras, gastos, productos y desglose de documentos.' },
      cotizaciones: { title: 'Reportes de cotizaciones', subtitle: 'Revisa cotizaciones, productos y documentos convertidos.' },
      ncnd: { title: 'Reportes de notas', subtitle: 'Consulta notas de crédito y débito con sus movimientos relacionados.' },
      inventario: { title: 'Reportes de inventario', subtitle: 'Consulta existencias, movimientos y comportamiento del inventario.' },
      receptores: { title: 'Reportes de clientes y proveedores', subtitle: 'Exporta la información de tus receptores con los filtros necesarios.' },
    };
    return map[topTab] || map.comprobantes;
  }, [topTab]);

  return (
    <div className={styles.container}>
      <div className={styles.heroAvanzado}>
        <div className={styles.heroIcon}><FileText size={20} /></div>
        <div className={styles.heroText}>
          <div className={styles.heroEyebrow}>CENTRO DE REPORTES</div>
          <div className={styles.heroTitle}>{hero.title}</div>
          <div className={styles.heroSub}>{hero.subtitle}</div>
        </div>
        <div className={styles.periodo}>
          <div className={styles.campo}>
            <label htmlFor="anio">Año</label>
            <select id="anio" className={styles.select} value={anio} onChange={(e) => setAnio(Number(e.target.value))}>
              {ANIOS.map((v) => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className={styles.campo}>
            <label htmlFor="mes">Mes</label>
            <select id="mes" className={styles.select} value={mes} onChange={(e) => setMes(Number(e.target.value))}>
              {MESES.map((n, i) => <option key={n} value={i + 1}>{n}</option>)}
            </select>
          </div>
        </div>
      </div>

      <nav className={styles.tabsTop} aria-label="Secciones de reportes">
        {TABS_TOP.map((t) => (
          <button
            key={t.id}
            className={`${styles.tabTop} ${topTab === t.id ? styles.tabTopActivo : ''}`}
            onClick={() => cambiarTab(t.id)}
          >
            <t.Icon size={16} /> {t.label}
          </button>
        ))}
      </nav>

      {/* Radios globales (Excel/PDF) + toggle rango — fiel a ra.cards */}
      <div className={styles.cardAvanzadoHeader}>
        <div className={styles.radiosRow} role="radiogroup" aria-label="Formato de descarga">
          {['Excel', 'PDF'].map((fmt) => {
            const deshabilitado = fmt === 'Excel' && !hayCsv;
            return (
              <button
                key={fmt}
                type="button"
                role="radio"
                aria-checked={formato === fmt}
                disabled={deshabilitado}
                title={deshabilitado ? 'Este reporte solo se exporta en PDF' : undefined}
                className={styles.radioLabel}
                style={{ background: 'none', border: 'none', padding: 0, font: 'inherit', opacity: deshabilitado ? 0.45 : 1, cursor: deshabilitado ? 'not-allowed' : 'pointer' }}
                onClick={() => setFormato(fmt)}
              >
                <span className={styles.radioOuter} style={{ borderColor: formato === fmt ? '#f26a35' : '#cbd5e1' }}>
                  <span className={styles.radioDot} style={{ background: formato === fmt ? '#f26a35' : 'transparent' }} />
                </span>
                {fmt}
              </button>
            );
          })}
        </div>
      </div>

      {topTab === 'comprobantes' && <TabComprobantes anio={anio} mes={mes} formato={formato} />}
      {topTab === 'inventario' && <TabInventarioReal formato={formato} />}
      {topTab === 'receptores' && <TabReceptoresReal formato={formato} />}
      {topTab === 'notasventa' && <TabPorReceptor anio={anio} mes={mes} tipo="notasventa" formato={formato} />}
      {topTab === 'egresos' && <TabEgresos anio={anio} mes={mes} formato={formato} />}
      {topTab === 'cotizaciones' && <TabPorReceptor anio={anio} mes={mes} tipo="cotizaciones" formato={formato} />}
      {topTab === 'ncnd' && <TabNotas anio={anio} mes={mes} formato={formato} />}
    </div>
  );
}

function TabComprobantes({ anio, mes, formato }) {
  const [pestana, setPestana] = useState('iva');
  return (
    <div>
      <nav className={styles.pestanas} aria-label="Tipo de reporte">
        {PESTANAS_COMPROBANTES.map((e) => (
          <button
            key={e.id}
            className={`${styles.pestana} ${pestana === e.id ? styles.pestanaActiva : ''}`}
            onClick={() => setPestana(e.id)}
            aria-current={pestana === e.id ? 'page' : undefined}
          >
            <e.Icon size={16} /> {e.etiqueta}
          </button>
        ))}
      </nav>
      {pestana === 'iva' && <ReporteIva anio={anio} mes={mes} formato={formato} />}
      {pestana === 'retenciones' && <ReporteRetenciones anio={anio} mes={mes} formato={formato} />}
      {pestana === 'ventas' && <ReporteVentas anio={anio} mes={mes} formato={formato} />}
      <div className={styles.notaFormato}>
        <AlertCircle size={14} /> {formato === 'PDF'
          ? 'Descarga en PDF (tabla paginada, con la cabecera de la empresa)'
          : 'Descarga en Excel/CSV (delimitado ; con BOM para Excel ES)'} — ver <code>{formato === 'PDF' ? 'urlPdf()' : 'urlCsv()'}</code> en <code>api/reportes.js</code>.
      </div>
      <PanelEstadoSri anio={anio} mes={mes} formato={formato} />
    </div>
  );
}

function PanelEstadoSri({ anio, mes, formato }) {
  const cargar = useCallback(({ senal }) => cargarEstadoSri(anio, mes, { senal }), [anio, mes]);
  const reporte = useReporte(cargar);
  const datos = reporte.datos;
  if (reporte.sinConexion || reporte.error || reporte.cargando || !datos) return null;
  return (
    <motion.section className={`${styles.panel} glass-panel`} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: 16 }}>
      <div className={styles.panelCabecera}>
        <div>
          <h2 className={styles.panelTitulo}>Estado ante el SRI — {MESES[mes - 1]} {anio}</h2>
          <p className={styles.panelNota}>Cuántos comprobantes hay en cada estado (incluye borradores y rechazados). Fuente: GET /reportes/estado-sri.</p>
        </div>
        {/* Este reporte solo existe en PDF, así que el botón lo dice en vez de
            seguir al selector de formato y prometer un CSV que no hay. */}
        {formato === 'PDF' && (
          <a className={styles.btnExportar} href={urlPdf('estado-sri', anio, mes)} download>
            <Download size={16} /> Exportar PDF
          </a>
        )}
      </div>
      <div className={styles.tablaWrapper}>
        <table className={styles.tabla}>
          <thead><tr><th>Estado SRI</th><th className={styles.numero}>Cantidad</th></tr></thead>
          <tbody>
            {(datos.por_estado ?? []).map((r) => (
              <tr key={r.estado}><td className={styles.etiqueta}>{r.estado}</td><td className={styles.numero}>{r.cantidad}</td></tr>
            ))}
            <tr className={styles.filaTotal}><td>Total</td><td className={styles.numero}>{datos.total}</td></tr>
            <tr className={styles.filaTotal}><td>Requieren atención</td><td className={styles.numero}>{datos.requieren_atencion}</td></tr>
          </tbody>
        </table>
      </div>
    </motion.section>
  );
}

/**
 * Envoltorio común: carga, error, sin conexión y botón de exportar.
 *
 * El botón sigue al selector de formato de la cabecera. Si el reporte no tiene
 * CSV (`csv` sin valor) se exporta en PDF pase lo que pase: es preferible dar
 * el único formato que existe a mostrar un enlace muerto.
 */
function Panel({ titulo, nota, csv, pdf, formato, reporte, columnas, children }) {
  if (reporte.sinConexion) return <SinConexion onReintentar={reporte.recargar} />;
  if (reporte.error) return <ErrorCarga mensaje={reporte.error} onReintentar={reporte.recargar} />;
  const enPdf = formato === 'PDF' || !csv;
  return (
    <motion.section className={`${styles.panel} glass-panel`} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div className={styles.panelCabecera}>
        <div>
          <h2 className={styles.panelTitulo}>{titulo}</h2>
          {nota && <p className={styles.panelNota}>{nota}</p>}
        </div>
        <a className={styles.btnExportar} href={enPdf ? pdf : csv} download>
          <Download size={16} /> Exportar {enPdf ? 'PDF' : 'CSV'}
        </a>
      </div>
      {reporte.cargando ? <TablaCargando columnas={columnas} filas={4} /> : children}
    </motion.section>
  );
}

function Vacio({ mensaje, detalle }) {
  return <div className={styles.vacio}><SearchX size={32} /><p>{mensaje}</p>{detalle && <span>{detalle}</span>}</div>;
}

function ReporteIva({ anio, mes, formato }) {
  const cargar = useCallback(({ senal }) => cargarIva(anio, mes, { senal }), [anio, mes]);
  const reporte = useReporte(cargar);
  const datos = useMemo(() => (reporte.datos ? ivaDesdeApi(reporte.datos) : null), [reporte.datos]);
  return (
    <Panel titulo={`IVA en ventas — ${MESES[mes - 1]} ${anio}`} nota="Base imponible e IVA por tarifa, solo de comprobantes autorizados. Es lo que se traslada al formulario 104." csv={urlCsv('iva', anio, mes)} pdf={urlPdf('iva', anio, mes)} formato={formato} reporte={reporte} columnas={4}>
      {datos && datos.tarifas.length === 0 ? (
        <Vacio mensaje="No hay ventas autorizadas en este período." detalle="Solo se cuentan los comprobantes que el SRI autorizó." />
      ) : datos && (
        <div className={styles.tablaWrapper}>
          <table className={styles.tabla}>
            <thead><tr><th>Tarifa</th><th>Código SRI</th><th className={styles.numero}>Base imponible</th><th className={styles.numero}>IVA</th></tr></thead>
            <tbody>
              {datos.tarifas.map((t) => (
                <tr key={t.codigoIva}><td className={styles.etiqueta}>{t.porcentaje}%</td><td className={styles.codigo}>{t.codigoIva}</td><td className={styles.numero}>{formatearMoneda(t.baseImponible)}</td><td className={styles.numero}>{formatearMoneda(t.valorIva)}</td></tr>
              ))}
              <tr className={styles.filaTotal}><td colSpan={2}>Total</td><td className={styles.numero}>{formatearMoneda(datos.baseTotal)}</td><td className={styles.numero}>{formatearMoneda(datos.ivaTotal)}</td></tr>
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}

const NOMBRE_IMPUESTO = { 1: 'Renta', 2: 'IVA', 6: 'ISD' };

function ReporteRetenciones({ anio, mes, formato }) {
  const cargar = useCallback(({ senal }) => cargarRetenciones(anio, mes, { senal }), [anio, mes]);
  const reporte = useReporte(cargar);
  const datos = useMemo(() => (reporte.datos ? retencionesDesdeApi(reporte.datos) : null), [reporte.datos]);
  return (
    <Panel titulo={`Retenciones emitidas — ${MESES[mes - 1]} ${anio}`} nota="Agrupadas por concepto, filtradas por período fiscal. Sustento del formulario 103." csv={urlCsv('retenciones', anio, mes)} pdf={urlPdf('retenciones', anio, mes)} formato={formato} reporte={reporte} columnas={5}>
      {datos && datos.conceptos.length === 0 ? (
        <Vacio mensaje="No hay retenciones autorizadas en este período fiscal." detalle="El filtro es el período declarado, no la fecha de emisión." />
      ) : datos && (
        <>
          <div className={styles.tablaWrapper}>
            <table className={styles.tabla}>
              <thead><tr><th>Impuesto</th><th>Concepto</th><th className={styles.numero}>Líneas</th><th className={styles.numero}>Base imponible</th><th className={styles.numero}>Retenido</th></tr></thead>
              <tbody>
                {datos.conceptos.map((c) => (
                  <tr key={`${c.codigoImpuesto}-${c.codigoRetencion}`}><td className={styles.etiqueta}>{NOMBRE_IMPUESTO[c.codigoImpuesto] ?? c.codigoImpuesto}</td><td className={styles.codigo}>{c.codigoRetencion}</td><td className={styles.numero}>{c.lineas}</td><td className={styles.numero}>{formatearMoneda(c.baseImponible)}</td><td className={styles.numero}>{formatearMoneda(c.valorRetenido)}</td></tr>
                ))}
                <tr className={styles.filaTotal}><td colSpan={4}>Total retenido</td><td className={styles.numero}>{formatearMoneda(datos.totalRetenido)}</td></tr>
              </tbody>
            </table>
          </div>
          <div className={styles.panelCabecera}>
            <div className={styles.totales} style={{ width: '100%' }}>
              <Tarjeta etiqueta="Comprobantes" valor={datos.comprobantes} />
              <Tarjeta etiqueta="Retenido de renta" valor={formatearMoneda(datos.totalRenta)} />
              <Tarjeta etiqueta="Retenido de IVA" valor={formatearMoneda(datos.totalIva)} />
            </div>
          </div>
        </>
      )}
    </Panel>
  );
}

function ReporteVentas({ anio, mes, formato }) {
  const cargarTipos = useCallback(({ senal }) => cargarVentasPorTipo(anio, mes, { senal }), [anio, mes]);
  const cargarResumen = useCallback(({ senal }) => cargarResumenVentas(anio, mes, { senal }), [anio, mes]);
  const tipos = useReporte(cargarTipos);
  const resumenBruto = useReporte(cargarResumen);
  const resumen = useMemo(() => (resumenBruto.datos ? resumenDesdeApi(resumenBruto.datos) : null), [resumenBruto.datos]);
  const filas = tipos.datos ?? [];
  return (
    <>
      {resumen && (
        <div className={styles.totales} style={{ marginBottom: 20 }}>
          <Tarjeta etiqueta="Facturado" valor={formatearMoneda(resumen.total)} acento />
          <Tarjeta etiqueta="Comprobantes" valor={resumen.comprobantes} />
          <Tarjeta etiqueta="Subtotal" valor={formatearMoneda(resumen.subtotal)} />
          <Tarjeta etiqueta="IVA" valor={formatearMoneda(resumen.iva)} />
          <Tarjeta etiqueta="Ticket promedio" valor={formatearMoneda(resumen.ticketPromedio)} />
        </div>
      )}
      <Panel titulo={`Ventas por tipo de documento — ${MESES[mes - 1]} ${anio}`} nota="Solo comprobantes autorizados por el SRI." csv={urlCsv('ventas', anio, mes)} pdf={urlPdf('ventas', anio, mes)} formato={formato} reporte={tipos} columnas={3}>
        {filas.length === 0 ? <Vacio mensaje="No hay ventas autorizadas en este período." /> : (
          <div className={styles.tablaWrapper}>
            <table className={styles.tabla}>
              <thead><tr><th>Tipo de documento</th><th className={styles.numero}>Cantidad</th><th className={styles.numero}>Total</th></tr></thead>
              <tbody>{filas.map((f) => <tr key={f.tipo}><td className={styles.etiqueta}>{f.tipo}</td><td className={styles.numero}>{f.cantidad}</td><td className={styles.numero}>{formatearMoneda(f.total)}</td></tr>)}</tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}

function Tarjeta({ etiqueta, valor, acento }) {
  return <div className={`${styles.tarjeta} glass-panel ${acento ? styles.tarjetaAcento : ''}`}><span className={styles.tarjetaEtiqueta}>{etiqueta}</span><span className={styles.tarjetaValor}>{valor}</span></div>;
}


// --------------------------------------------------------------------------
// Notas de venta y cotizaciones: mismo desglose por receptor
// --------------------------------------------------------------------------

// `endpoint` es el nombre que usa el backend en la ruta de descarga. Ninguno de
// los dos tiene /csv: solo se exportan en PDF.
const POR_RECEPTOR = {
  notasventa: {
    titulo: 'Notas de venta',
    nota: 'Notas de venta autorizadas del período, agrupadas por receptor.',
    cargar: cargarNotasVenta,
    endpoint: 'notas-venta',
  },
  cotizaciones: {
    titulo: 'Cotizaciones',
    // Una cotización nunca se transmite al SRI, así que no se filtra por
    // autorizada: exigirlo daría siempre cero.
    nota: 'Cotizaciones del período. No pasan por el SRI, así que cuentan todas.',
    cargar: cargarCotizaciones,
    endpoint: 'cotizaciones',
  },
};

function TabPorReceptor({ anio, mes, tipo }) {
  const config = POR_RECEPTOR[tipo];
  const cargar = useCallback(
    ({ senal }) => config.cargar(anio, mes, { senal }),
    [config, anio, mes],
  );
  const reporte = useReporte(cargar);

  const datos = useMemo(
    () => (reporte.datos ? porReceptorDesdeApi(reporte.datos) : null),
    [reporte.datos],
  );

  const esCotizacion = tipo === 'cotizaciones';

  return (
    <>
      {datos && (
        <div className={styles.totales} style={{ marginBottom: 18 }}>
          <Tarjeta etiqueta="Documentos" valor={String(datos.comprobantes)} />
          <Tarjeta etiqueta="Total" valor={formatearMoneda(datos.total)} acento />
          {esCotizacion && (
            <Tarjeta
              etiqueta="Receptores que facturaron"
              valor={String(datos.receptoresConFactura)}
            />
          )}
        </div>
      )}

      <Panel
        titulo={`${config.titulo} — ${MESES[mes - 1]} ${anio}`}
        nota={config.nota}
        pdf={urlPdf(config.endpoint, anio, mes)}
        reporte={reporte}
        columnas={4}
      >
        {datos && datos.receptores.length === 0 ? (
          <Vacio mensaje={`No hay ${config.titulo.toLowerCase()} en este período.`} />
        ) : (
          datos && (
            <div className={styles.tablaWrapper}>
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Receptor</th>
                    <th>Identificación</th>
                    <th className={styles.numero}>Documentos</th>
                    {esCotizacion && <th>¿Facturó?</th>}
                    <th className={styles.numero}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.receptores.map((fila) => (
                    <tr key={fila.identificacion}>
                      <td className={styles.etiqueta}>{fila.razonSocial}</td>
                      <td className={styles.codigo}>{fila.identificacion}</td>
                      <td className={styles.numero}>{fila.comprobantes}</td>
                      {esCotizacion && (
                        <td className={styles.codigo}>{fila.conFactura ? 'Sí' : '—'}</td>
                      )}
                      <td className={styles.numero}>{formatearMoneda(fila.total)}</td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={esCotizacion ? 4 : 3}>Total</td>
                    <td className={styles.numero}>{formatearMoneda(datos.total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )
        )}
      </Panel>
    </>
  );
}

// --------------------------------------------------------------------------
// Notas de crédito y débito
// --------------------------------------------------------------------------

function TabNotas({ anio, mes, formato }) {
  const cargar = useCallback(({ senal }) => cargarNotas(anio, mes, { senal }), [anio, mes]);
  const reporte = useReporte(cargar);

  const datos = useMemo(
    () => (reporte.datos ? notasDesdeApi(reporte.datos) : null),
    [reporte.datos],
  );

  return (
    <>
      {datos && (
        <div className={styles.totales} style={{ marginBottom: 18 }}>
          <Tarjeta
            etiqueta={`Notas de crédito (${datos.notasCredito})`}
            valor={formatearMoneda(datos.totalCredito)}
          />
          <Tarjeta
            etiqueta={`Notas de débito (${datos.notasDebito})`}
            valor={formatearMoneda(datos.totalDebito)}
          />
          <Tarjeta etiqueta="Efecto neto" valor={formatearMoneda(datos.neto)} acento />
        </div>
      )}

      <Panel
        titulo={`Notas de crédito y débito — ${MESES[mes - 1]} ${anio}`}
        nota="Nunca se suman entre sí: la de crédito resta valor y la de débito lo aumenta. El efecto neto ya viene calculado."
        csv={urlCsv('notas', anio, mes)}
        pdf={urlPdf('notas', anio, mes)}
        formato={formato}
        reporte={reporte}
        columnas={6}
      >
        {datos && datos.documentos.length === 0 ? (
          <Vacio mensaje="No se emitieron notas en este período." />
        ) : (
          datos && (
            <div className={styles.tablaWrapper}>
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Número</th>
                    <th>Tipo</th>
                    <th>Fecha</th>
                    <th>Receptor</th>
                    <th>Modifica</th>
                    <th className={styles.numero}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.documentos.map((nota) => (
                    <tr key={nota.numero}>
                      <td className={styles.codigo}>{nota.numero}</td>
                      <td className={styles.etiqueta}>{nota.tipo}</td>
                      <td className={styles.codigo}>{nota.fecha}</td>
                      <td>{nota.receptor}</td>
                      <td className={styles.codigo}>{nota.documentoModificado || '—'}</td>
                      <td className={styles.numero}>{formatearMoneda(nota.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Panel>
    </>
  );
}

// --------------------------------------------------------------------------
// Egresos
// --------------------------------------------------------------------------

function TabEgresos({ anio, mes, formato }) {
  const cargar = useCallback(({ senal }) => cargarEgresos(anio, mes, { senal }), [anio, mes]);
  const reporte = useReporte(cargar);

  const datos = useMemo(
    () => (reporte.datos ? egresosDesdeApi(reporte.datos) : null),
    [reporte.datos],
  );

  return (
    <>
      {datos && (
        <div className={styles.totales} style={{ marginBottom: 18 }}>
          <Tarjeta etiqueta="Total gastado" valor={formatearMoneda(datos.total)} acento />
          <Tarjeta etiqueta="Deducible" valor={formatearMoneda(datos.totalDeducible)} />
          <Tarjeta etiqueta="IVA soportado" valor={formatearMoneda(datos.ivaSoportado)} />
          <Tarjeta etiqueta="Pagado" valor={formatearMoneda(datos.totalPagado)} />
        </div>
      )}

      <Panel
        titulo={`Egresos por tipo de gasto — ${MESES[mes - 1]} ${anio}`}
        nota="Los gastos no son comprobantes electrónicos: aquí cuenta lo registrado, no lo autorizado. Solo lo deducible baja el impuesto a la renta."
        csv={urlCsv('egresos', anio, mes)}
        pdf={urlPdf('egresos', anio, mes)}
        formato={formato}
        reporte={reporte}
        columnas={6}
      >
        {datos && datos.tipos.length === 0 ? (
          <Vacio
            mensaje="No hay gastos registrados en este período."
            detalle="Se registran en Egresos → Gastos."
          />
        ) : (
          datos && (
            <div className={styles.tablaWrapper}>
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Tipo de gasto</th>
                    <th>Deducible</th>
                    <th className={styles.numero}>Gastos</th>
                    <th className={styles.numero}>Subtotal</th>
                    <th className={styles.numero}>IVA</th>
                    <th className={styles.numero}>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.tipos.map((fila) => (
                    <tr key={fila.tipo}>
                      <td className={styles.etiqueta}>{fila.tipo}</td>
                      <td className={styles.codigo}>{fila.deducible ? 'Sí' : 'No'}</td>
                      <td className={styles.numero}>{fila.gastos}</td>
                      <td className={styles.numero}>{formatearMoneda(fila.subtotal)}</td>
                      <td className={styles.numero}>{formatearMoneda(fila.iva)}</td>
                      <td className={styles.numero}>{formatearMoneda(fila.total)}</td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={4}>Total</td>
                    <td className={styles.numero}>{formatearMoneda(datos.ivaSoportado)}</td>
                    <td className={styles.numero}>{formatearMoneda(datos.total)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          )
        )}
      </Panel>
    </>
  );
}


// --------------------------------------------------------------------------
// Inventario y receptores: fotos del estado actual, sin período
// --------------------------------------------------------------------------

function TabInventarioReal({ formato }) {
  const cargar = useCallback(({ senal }) => cargarInventario({ senal }), []);
  const reporte = useReporte(cargar);

  const datos = useMemo(
    () => (reporte.datos ? inventarioDesdeApi(reporte.datos) : null),
    [reporte.datos],
  );

  return (
    <>
      {datos && (
        <div className={styles.totales} style={{ marginBottom: 18 }}>
          <Tarjeta
            etiqueta="Valor al costo"
            valor={formatearMoneda(datos.valorInventario)}
            acento
          />
          <Tarjeta etiqueta="Productos" valor={String(datos.productos)} />
          <Tarjeta etiqueta="Servicios" valor={String(datos.servicios)} />
          <Tarjeta etiqueta="Bajo mínimo" valor={String(datos.bajoMinimo)} />
        </div>
      )}

      <Panel
        titulo="Inventario"
        nota="El valor se calcula al costo, no al precio de venta: el inventario es lo que costó reponerlo, no lo que se espera cobrar."
        csv={urlCsv('inventario')}
        pdf={urlPdf('inventario')}
        formato={formato}
        reporte={reporte}
        columnas={6}
      >
        {datos && datos.articulos.length === 0 ? (
          <Vacio mensaje="No hay artículos activos." />
        ) : (
          datos && (
            <div className={styles.tablaWrapper}>
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Artículo</th>
                    <th>Categoría</th>
                    <th className={styles.numero}>Stock</th>
                    <th className={styles.numero}>Costo</th>
                    <th className={styles.numero}>Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.articulos.map((articulo) => (
                    <tr key={articulo.codigo}>
                      <td className={styles.codigo}>{articulo.codigo}</td>
                      <td className={styles.etiqueta}>
                        {articulo.nombre}
                        {articulo.bajoMinimo && ' ⚠'}
                      </td>
                      <td className={styles.codigo}>{articulo.categoria}</td>
                      <td className={styles.numero}>
                        {articulo.stock === null ? '—' : articulo.stock}
                      </td>
                      <td className={styles.numero}>{formatearMoneda(articulo.costo)}</td>
                      <td className={styles.numero}>{formatearMoneda(articulo.valor)}</td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={5}>Valor del inventario</td>
                    <td className={styles.numero}>
                      {formatearMoneda(datos.valorInventario)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )
        )}
      </Panel>
    </>
  );
}

function TabReceptoresReal({ formato }) {
  const [rol, setRol] = useState('');
  const cargar = useCallback(({ senal }) => cargarReceptores(rol || undefined, { senal }), [rol]);
  const reporte = useReporte(cargar);

  const datos = useMemo(
    () => (reporte.datos ? receptoresDesdeApi(reporte.datos) : null),
    [reporte.datos],
  );

  return (
    <>
      {datos && (
        <div className={styles.totales} style={{ marginBottom: 18 }}>
          <Tarjeta etiqueta="Registrados" valor={String(datos.total)} acento />
          <Tarjeta etiqueta="Clientes" valor={String(datos.clientes)} />
          <Tarjeta etiqueta="Proveedores" valor={String(datos.proveedores)} />
          <Tarjeta etiqueta="Transportistas" valor={String(datos.transportistas)} />
        </div>
      )}

      <div className={styles.campo} style={{ marginBottom: 14 }}>
        <label htmlFor="rol-receptor">Filtrar por rol</label>
        <select
          id="rol-receptor"
          className={styles.select}
          value={rol}
          onChange={(e) => setRol(e.target.value)}
        >
          <option value="">Todos</option>
          <option value="Cliente">Clientes</option>
          <option value="Proveedor">Proveedores</option>
          <option value="Transportista">Transportistas</option>
        </select>
      </div>

      <Panel
        titulo="Clientes y proveedores"
        nota="Lo facturado cuenta solo comprobantes autorizados, como en el resto de reportes."
        csv={urlCsv('receptores')}
        pdf={urlPdf('receptores')}
        formato={formato}
        reporte={reporte}
        columnas={5}
      >
        {datos && datos.receptores.length === 0 ? (
          <Vacio mensaje="No hay receptores con ese rol." />
        ) : (
          datos && (
            <div className={styles.tablaWrapper}>
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Razón social</th>
                    <th>Identificación</th>
                    <th>Rol</th>
                    <th>Correo</th>
                    <th className={styles.numero}>Facturado</th>
                  </tr>
                </thead>
                <tbody>
                  {datos.receptores.map((receptor) => (
                    <tr key={receptor.identificacion}>
                      <td className={styles.etiqueta}>{receptor.razonSocial}</td>
                      <td className={styles.codigo}>{receptor.identificacion}</td>
                      <td className={styles.codigo}>{receptor.rol}</td>
                      <td className={styles.codigo}>{receptor.correo || '—'}</td>
                      <td className={styles.numero}>{formatearMoneda(receptor.facturado)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Panel>
    </>
  );
}
