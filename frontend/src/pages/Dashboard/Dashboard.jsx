import { useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  DollarSign,
  FileText,
  Receipt,
  CalendarRange,
  FilePlus2,
  UserPlus,
  PackagePlus,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { cargarPanel, panelDesdeApi } from '../../api/reportes';
import { useReporte } from '../../hooks/useReporte';
import { useSesion } from '../../auth/useSesion';
import { saludoCompleto } from '../../lib/saludo';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { ErrorCarga, SinConexion } from '../../components/ui/EstadoCarga';
import styles from './Dashboard.module.css';

/**
 * Colores de dato, no de tema.
 *
 * Cada porción de la dona identifica un tipo de documento y el usuario la lee
 * contra la leyenda: si el color cambiara entre el tema claro y el oscuro, la
 * misma serie sería de dos colores distintos según la hora del día. Por eso
 * estos cinco no pasan por los tokens. Son tonos medios, elegidos para que
 * contrasten tanto con el panel blanco del tema claro como con el `#111f37`
 * del oscuro.
 */
const COLORES_DONUT = ['#f26a35', '#2aa9d6', '#16a34a', '#e11d48', '#8a99ad'];

// Misma razón que la dona: la serie de facturación mensual es un dato. El
// degradado va del azul del logotipo al cian del "AI" y se mantiene fijo.
const AREA_RELLENO = '#7fb2e6';
const LINEA_INICIO = '#3b6fd4';
const LINEA_FIN = '#2aa9d6';

const ACCIONES = [
  { to: '/configuraciones', titulo: 'Conexión Tributaria', Icono: ShieldCheck, tono: 'cian' },
  { to: '/receptores/nuevo', titulo: 'Crear Receptor', Icono: UserPlus, tono: 'cian' },
  { to: '/articulos/nuevo', titulo: 'Crear Inventario', Icono: PackagePlus, tono: 'naranja' },
  { to: '/comprobantes/nuevo', titulo: 'Crear Factura', Icono: FilePlus2, tono: 'naranja' },
];

export default function Dashboard() {
  const { usuario } = useSesion();
  const cargar = useCallback(({ senal }) => cargarPanel({ senal }), []);
  const reporte = useReporte(cargar);
  const panel = useMemo(() => (reporte.datos ? panelDesdeApi(reporte.datos) : null), [reporte.datos]);
  const saludo = saludoCompleto(usuario?.nombre);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
          <h1 className={styles.title}>{saludo}</h1>
          <p className={styles.subtitle}>Aquí tienes un resumen de tu negocio hoy.</p>
        </motion.div>
      </header>

      {reporte.sinConexion && <SinConexion onReintentar={reporte.recargar} />}
      {reporte.error && <ErrorCarga mensaje={reporte.error} onReintentar={reporte.recargar} />}
      {reporte.cargando && !panel && <PanelCargando />}

      {/* Fila superior: acciones + KPIs a la izquierda, estado a la derecha.
          Las acciones se pintan siempre, tenga o no datos el panel: son
          navegación, y si el servidor no responde es cuando más falta hace
          poder llegar a Configuraciones. */}
      <div className={styles.topRow}>
        <div className={styles.leftCol}>
          <div className={styles.accionesGrid}>
            {ACCIONES.map((accion, indice) => (
              <motion.div key={accion.to} initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: indice * 0.05 }}>
                <Link to={accion.to} className={styles.accionCard}>
                  <div className={`${styles.accionIcono} ${accion.tono === 'cian' ? styles.iconoCian : styles.iconoNaranja}`}>
                    <accion.Icono size={28} />
                  </div>
                  <span className={styles.accionLabel}>{accion.titulo}</span>
                </Link>
              </motion.div>
            ))}
          </div>

          {panel && (
            <div className={styles.kpiGrid}>
              <TarjetaKpi titulo="Facturado este mes" valor={formatearMoneda(panel.mes.total)} Icono={DollarSign} />
              <TarjetaKpi titulo="Documentos del mes" valor={String(panel.mes.comprobantes)} Icono={FileText} />
              <TarjetaKpi titulo="Ticket promedio" valor={formatearMoneda(panel.mes.ticketPromedio)} Icono={Receipt} />
              <TarjetaKpi titulo="Documentos del año" valor={String(panel.anio.comprobantes)} Icono={CalendarRange} />
            </div>
          )}
        </div>
        {panel && <EstadoSriCard panel={panel} />}
      </div>

      {panel && (
        <>

          {panel.estadoSri.requierenAtencion > 0 && (
            <motion.section className={styles.avisoPanel} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <AlertTriangle size={22} />
              <div>
                <h3 className={styles.avisoTitulo}>
                  {panel.estadoSri.requierenAtencion} {panel.estadoSri.requierenAtencion === 1 ? 'comprobante requiere atención' : 'comprobantes requieren atención'}
                </h3>
                <p className={styles.avisoDetalle}>Están en borrador, pendientes o fueron rechazados por el SRI.</p>
              </div>
              <Link to="/comprobantes" className={styles.avisoAccion}>Revisar</Link>
            </motion.section>
          )}

          <div className={styles.chartsRow}>
            <motion.div className={styles.chartCard} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <div className={styles.chartHeader}>
                <div>
                  <h3 className={styles.chartTitle}>Facturación mensual</h3>
                  <span className={styles.chartSub}>PANTALLA DE INICIO</span>
                </div>
                <div className={styles.chartActions}>
                  <button className={styles.chartBtn} onClick={reporte.recargar} title="Actualizar"><RefreshCw size={16} /></button>
                </div>
              </div>
              <div className={styles.chartWrapper}>
                {panel.anio.comprobantes > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={panel.serieMensual} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="cwoArea" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={AREA_RELLENO} stopOpacity={0.42} />
                          <stop offset="100%" stopColor={AREA_RELLENO} stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="cwoLine" x1="0" y1="0" x2="1" y2="0">
                          <stop offset="0%" stopColor={LINEA_INICIO} />
                          <stop offset="100%" stopColor={LINEA_FIN} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" vertical={false} />
                      <XAxis dataKey="etiqueta" stroke="var(--text-muted)" tickLine={false} axisLine={false} tick={{ fontSize: 12 }} />
                      <YAxis stroke="var(--text-muted)" tickLine={false} axisLine={false} tickFormatter={(v) => (v >= 1000 ? `$${Math.round(v / 1000)}k` : `$${v}`)} tick={{ fontSize: 12 }} />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--glass-border)', borderRadius: '8px', color: 'var(--text-primary)' }} formatter={(valor) => [formatearMoneda(valor), 'Facturado']} />
                      <Area type="monotone" dataKey="total" stroke="url(#cwoLine)" strokeWidth={3} fill="url(#cwoArea)" dot={false} activeDot={{ r: 5, className: styles.puntoActivo }} />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <PanelVacio mensaje="Aún no hay comprobantes autorizados este año." />
                )}
              </div>
              <div className={styles.chartFooter}>
                <span className={styles.chartSub}>PANTALLA DE INICIO</span>
                <span className={styles.chartFooterText}>Última Facturación: <strong>{panel.hoy ?? '-'}</strong></span>
              </div>
            </motion.div>

            <motion.div className={styles.donutCard} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <h3 className={styles.chartTitle}>Distribución por tipo de documento</h3>
              {/* El vacío se anuncia una sola vez para toda la tarjeta: repetirlo
                  en la dona y en la leyenda parece un fallo de pintado. */}
              {panel.porTipo.length === 0 ? (
                <PanelVacio mensaje="Sin documentos autorizados todavía." />
              ) : (
                <div className={styles.donutBody}>
                  <div className={styles.donutChart}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={panel.porTipo} dataKey="cantidad" nameKey="tipo" innerRadius="55%" outerRadius="80%" paddingAngle={3} stroke="none">
                          {panel.porTipo.map((entrada, indice) => (
                            <Cell key={entrada.tipo} fill={COLORES_DONUT[indice % COLORES_DONUT.length]} />
                          ))}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: 'var(--bg-tertiary)', borderColor: 'var(--glass-border)', borderRadius: '8px', color: 'var(--text-primary)' }} formatter={(valor, nombre) => [`${valor} documentos`, nombre]} />
                      </PieChart>
                    </ResponsiveContainer>
                    <div className={styles.donutCenter}>
                      <span className={styles.donutNum}>{panel.anio.comprobantes}</span>
                      <span className={styles.donutLabel}>Documentos</span>
                    </div>
                  </div>
                  <div className={styles.donutLegend}>
                    {panel.porTipo.map((fila, i) => (
                      <div key={fila.tipo} className={styles.legendRow}>
                        <span className={styles.legendDot} style={{ background: COLORES_DONUT[i % COLORES_DONUT.length] }} />
                        <div>
                          <div className={styles.legendLabel}>{fila.tipo}</div>
                          <div className={styles.legendVal}>{fila.cantidad}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          </div>

          {/* Listas destacadas */}
          <div className={styles.listasGrid}>
            <ListaDestacados titulo="Clientes que más facturan" filas={panel.topClientes.map((c) => ({ clave: c.identificacion, principal: c.razonSocial, secundario: `${c.comprobantes} ${c.comprobantes === 1 ? 'documento' : 'documentos'}`, valor: formatearMoneda(c.total) }))} enlace="/receptores" />
            <ListaDestacados titulo="Artículos más vendidos" filas={panel.topArticulos.map((a) => ({ clave: a.codigo, principal: a.descripcion, secundario: `${a.cantidad} vendidos`, valor: formatearMoneda(a.total) }))} enlace="/articulos" />
          </div>
        </>
      )}
    </div>
  );
}

function TarjetaKpi({ titulo, valor, Icono }) {
  return (
    <div className={styles.kpiCard}>
      <div>
        <div className={styles.kpiLabel}>{titulo}</div>
        <div className={`${styles.kpiValue} cifra`}>{valor}</div>
      </div>
      <div className={styles.kpiIcon}><Icono size={20} /></div>
    </div>
  );
}

/**
 * Tarjeta de estado, en el hueco que el prototipo reserva a "Plan state".
 *
 * El prototipo la usa para la suscripción del producto, pero aquí no hay
 * módulo de facturación del SaaS: rellenarla con un plan inventado enseñaría
 * cifras creíbles y falsas, que es peor que no enseñar ninguna. Se conserva su
 * diseño —título, barra de progreso, dos líneas de detalle— y se llena con lo
 * que sí existe y el usuario necesita vigilar: cuántos comprobantes llegaron a
 * autorizarse y en qué ambiente se está emitiendo.
 */
function EstadoSriCard({ panel }) {
  const total = panel.estadoSri.total;
  const autorizados = total - panel.estadoSri.requierenAtencion;
  const pct = total === 0 ? 0 : Math.round((autorizados / total) * 100);
  const enPruebas = panel.ambiente !== '2';

  return (
    <div className={styles.planCard}>
      <div className={styles.planTitle}>Estado ante el SRI</div>

      <div className={styles.planUso}>
        AUTORIZADOS: <span className="cifra">{autorizados} de {total}</span>
      </div>
      <div className={styles.planBar}>
        <div className={styles.planFill} style={{ width: `${pct}%` }} />
      </div>

      <div className={styles.planNombre}>
        {enPruebas ? 'Ambiente de pruebas' : 'Ambiente de producción'}
      </div>

      <div className={styles.planMeta}>
        <div>
          Requieren atención:{' '}
          <span className="cifra">{panel.estadoSri.requierenAtencion}</span>
        </div>
        <div>
          Por cobrar: <span className="cifra">{formatearMoneda(panel.porCobrar.total)}</span>
        </div>
      </div>

      {/* Un aviso, no un adorno: emitir en pruebas creyendo que es producción
          no se nota hasta que hay que declarar. */}
      {enPruebas && (
        <div className={styles.planAviso}>Los documentos no tienen validez tributaria.</div>
      )}

      <div className={styles.planDots} aria-hidden>
        {/* El relleno de los puntos lo pone `.planDots circle` en la hoja de
            estilos: un atributo `fill` no admite var(), y aquí hace falta que
            siga al tema. */}
        <svg width="150" height="70" viewBox="0 0 150 70" opacity="0.12">
          <circle cx="20" cy="20" r="2" />
          <circle cx="40" cy="15" r="2" />
          <circle cx="60" cy="25" r="2" />
          <circle cx="80" cy="18" r="2" />
          <circle cx="100" cy="30" r="2" />
          <circle cx="120" cy="22" r="2" />
        </svg>
      </div>
    </div>
  );
}

function ListaDestacados({ titulo, filas, enlace }) {
  return (
    <section className={`${styles.listaPanel} glass-panel`}>
      <div className={styles.listaCabecera}>
        <h3 className={styles.chartTitle}>{titulo}</h3>
        <Link to={enlace} className={styles.listaEnlace}>Ver todos</Link>
      </div>
      {filas.length === 0 ? <PanelVacio mensaje="Sin datos en el período." /> : (
        <ul className={styles.lista}>
          {filas.map((fila) => (
            <li key={fila.clave} className={styles.listaFila}>
              <div className={styles.listaTexto}>
                <span className={styles.listaPrincipal}>{fila.principal}</span>
                <span className={styles.listaSecundario}>{fila.secundario}</span>
              </div>
              <span className={`${styles.listaValor} cifra`}>{fila.valor}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PanelVacio({ mensaje }) { return <div className={styles.vacio}><p>{mensaje}</p></div>; }

function PanelCargando() {
  return (
    <div className={styles.kpiGrid} aria-busy="true" aria-label="Cargando el panel">
      {[0, 1, 2, 3].map((i) => <div key={i} className={`${styles.kpiCard} ${styles.esqueleto}`} />)}
    </div>
  );
}
