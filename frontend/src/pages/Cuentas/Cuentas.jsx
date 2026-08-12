import { useCallback, useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  CalendarDays,
  FileText,
  Wallet,
  Clock3,
  AlertTriangle,
  BarChart3,
  Search,
  RefreshCw,
  Plus,
  Upload,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useReporte } from '../../hooks/useReporte';
import {
  agendaCuotasDesdeApi,
  anularRecibo,
  cargarAgendaCuotas,
  cargarHistorialContactos,
  cargarRecibosGenerados,
  cargarRotacionCuentas,
  cargarSaldosPendientes,
  historialContactosDesdeApi,
  modoValido,
  recibosGeneradosDesdeApi,
  registrarRecibo,
  rotacionCuentasDesdeApi,
  saldosPendientesDesdeApi,
  urlCsvCuentas,
} from '../../api/cuentas';
import { useTablaFiltrada } from '../../hooks/useTablaFiltrada';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { ErrorCarga, SinConexion, TablaCargando } from '../../components/ui/EstadoCarga';
import TarjetaReporte from './TarjetaReporte';
import styles from './Cuentas.module.css';

const TABS = [
  { id: 'inicio', label: 'Inicio', Icon: FileText },
  { id: 'recep', label: 'Receptores', Icon: Wallet },
  { id: 'gestion', label: 'Gestión mensual', Icon: CalendarDays },
  { id: 'historial', label: 'Historial', Icon: Clock3 },
  { id: 'vencidos', label: 'Vencidos', Icon: AlertTriangle },
  { id: 'reportes', label: 'Reportes', Icon: BarChart3 },
];

const MESES_L = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
];

/**
 * Qué pestañas necesitan cada reporte.
 *
 * Los cinco reportes se piden solo cuando la pestaña abierta va a enseñarlos:
 * traer los cinco mientras el usuario mira otra cosa es tráfico que nadie lee.
 * «Reportes» es la única pestaña que los usa todos; las demás, uno o dos.
 */
const PESTANAS_POR_REPORTE = {
  saldos: ['inicio', 'reportes'],
  agenda: ['inicio', 'gestion', 'vencidos', 'reportes'],
  recibos: ['inicio', 'historial', 'reportes'],
  historial: ['recep', 'reportes'],
  rotacion: ['reportes'],
};

// Vista previa de las tarjetas: unas pocas filas. El CSV se lleva todas, y una
// tabla de doscientas líneas dentro de una tarjeta no la lee nadie.
const FILAS_PREVISUALIZACION = 6;

// El color de cada tono lo pone el .module.css: en el JSX no hay colores.
const TONO = {
  acento: 'tonoAcento',
  neutro: 'tonoNeutro',
  error: 'tonoError',
  ok: 'tonoOk',
};

function mesLabel(date) {
  return `${MESES_L[date.getMonth()]} de ${date.getFullYear()}`;
}

/** Clave `AAAA-MM` de una fecha, para comparar con las que manda el API. */
function claveMes(date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}

/**
 * Tipo de identificación por su longitud.
 *
 * El SRI numera así: 13 dígitos es RUC y 10 es cédula. Antes esta columna decía
 * «RUC» de todo el mundo, que es un dato inventado con aspecto de dato.
 */
function tipoIdentificacion(identificacion) {
  const limpio = String(identificacion ?? '').trim();
  if (limpio.length === 13) return 'RUC';
  if (limpio.length === 10) return 'Cédula';
  return limpio ? 'Otro' : '—';
}

/** Carga, error o sin conexión de un reporte; si todo va bien, su contenido. */
function Estado({ reporte, columnas = 6, children }) {
  if (reporte.sinConexion) return <SinConexion onReintentar={reporte.recargar} />;
  if (reporte.error) return <ErrorCarga mensaje={reporte.error} onReintentar={reporte.recargar} />;
  if (reporte.cargando) return <TablaCargando columnas={columnas} />;
  return children;
}

/** Pie de la vista previa: cuántas filas se ven de las que hay. */
function PieVista({ mostradas, total }) {
  if (total <= mostradas) return null;
  return (
    <div className={styles.reporteNota}>
      Vista previa: {mostradas} de {total} filas. El CSV las trae todas.
    </div>
  );
}

export default function Cuentas() {
  const [searchParams, setSearchParams] = useSearchParams();
  const modo = modoValido(searchParams.get('tipo'));
  const modoCobrar = modo === 'cobrar';
  const W = modoCobrar ? 'Cliente' : 'Proveedor';
  const Wp = modoCobrar ? 'Clientes' : 'Proveedores';
  const accion = modoCobrar ? 'cobrar' : 'pagar';
  const badgeReporte = `Cuentas por ${accion} · CSV`;

  const [tab, setTab] = useState('inicio');
  const necesita = (clave) => PESTANAS_POR_REPORTE[clave].includes(tab);

  // El modo viaja en TODAS las consultas, no solo en las tarjetas: en `pagar`
  // el backend lee gastos, egresos y liquidaciones de compra, que son otros
  // documentos y otro dinero. Antes el interruptor solo cambiaba los rótulos.
  const traerSaldos = useCallback(
    ({ senal }) => cargarSaldosPendientes(modo, undefined, { senal }),
    [modo],
  );
  const traerAgenda = useCallback(
    ({ senal }) => cargarAgendaCuotas(modo, undefined, { senal }),
    [modo],
  );
  const traerRecibos = useCallback(
    ({ senal }) => cargarRecibosGenerados(modo, undefined, { senal }),
    [modo],
  );
  const traerRotacion = useCallback(
    ({ senal }) => cargarRotacionCuentas(modo, undefined, { senal }),
    [modo],
  );
  const traerHistorial = useCallback(
    ({ senal }) => cargarHistorialContactos(modo, { solo_con_saldo: true }, { senal }),
    [modo],
  );

  const reporteSaldos = useReporte(traerSaldos, { activo: necesita('saldos') });
  const reporteAgenda = useReporte(traerAgenda, { activo: necesita('agenda') });
  const reporteRecibos = useReporte(traerRecibos, { activo: necesita('recibos') });
  const reporteRotacion = useReporte(traerRotacion, { activo: necesita('rotacion') });
  const reporteHistorial = useReporte(traerHistorial, { activo: necesita('historial') });

  const saldos = useMemo(
    () => (reporteSaldos.datos ? saldosPendientesDesdeApi(reporteSaldos.datos) : null),
    [reporteSaldos.datos],
  );
  const agenda = useMemo(
    () => (reporteAgenda.datos ? agendaCuotasDesdeApi(reporteAgenda.datos) : null),
    [reporteAgenda.datos],
  );
  const recibos = useMemo(
    () => (reporteRecibos.datos ? recibosGeneradosDesdeApi(reporteRecibos.datos) : null),
    [reporteRecibos.datos],
  );
  const rotacion = useMemo(
    () => (reporteRotacion.datos ? rotacionCuentasDesdeApi(reporteRotacion.datos) : null),
    [reporteRotacion.datos],
  );
  const historial = useMemo(
    () => (reporteHistorial.datos ? historialContactosDesdeApi(reporteHistorial.datos) : null),
    [reporteHistorial.datos],
  );

  const cuotas = agenda?.cuotas ?? [];
  const movimientos = recibos?.recibos ?? [];
  const contactos = historial?.contactos ?? [];

  const [errorCobro, setErrorCobro] = useState(null);

  // Solo se recarga lo que la pestaña abierta enseña: al cambiar de pestaña,
  // `useReporte` vuelve a pedir el reporte que pasa a estar activo.
  const trasMoverDinero = () => {
    if (necesita('agenda')) reporteAgenda.recargar();
    if (necesita('recibos')) reporteRecibos.recargar();
    if (necesita('saldos')) reporteSaldos.recargar();
  };

  /**
   * Registrar el cobro de una cuota.
   *
   * Solo existe en modo Cobrar: el API de recibos registra dinero que ENTRA. Lo
   * que se le paga a un proveedor es un egreso y se registra desde Gastos, así
   * que aquí el botón no aparece en vez de fingir que hace algo.
   */
  const cobrar = async (cuota) => {
    setErrorCobro(null);
    try {
      await registrarRecibo({
        // Un documento sin plan de cuotas entra en la agenda como cuota única y
        // no tiene `cuotaId`: entonces el recibo va contra el comprobante.
        cuotaId: cuota.cuotaId,
        comprobanteId: cuota.cuotaId ? null : cuota.documentoId,
        monto: cuota.saldo,
      });
      trasMoverDinero();
    } catch (fallo) {
      setErrorCobro(fallo.message);
    }
  };

  const revertir = async (movimiento) => {
    setErrorCobro(null);
    try {
      await anularRecibo(movimiento.reciboId);
      trasMoverDinero();
    } catch (fallo) {
      setErrorCobro(fallo.message);
    }
  };

  // Vencidas: saldo pendiente y fecha ya pasada. `diasMora` lo calcula el
  // servidor con su propia fecha, que es la que manda.
  const cuotasVencidas = useMemo(
    () => cuotas.filter((c) => c.saldo > 0 && c.diasMora > 0),
    [cuotas],
  );
  const [mesDate, setMesDate] = useState(() => new Date());

  // Cuotas del mes que se está mirando en la pestaña de gestión.
  const cuotasDelMes = useMemo(() => {
    const clave = claveMes(mesDate);
    return cuotas.filter((c) => String(c.vence).startsWith(clave));
  }, [cuotas, mesDate]);

  const [recepQuery, setRecepQuery] = useState('');
  const [histQuery, setHistQuery] = useState('');
  const [vencQuery, setVencQuery] = useState('');
  const [saldoModal, setSaldoModal] = useState(false);
  const [cfgModal, setCfgModal] = useState(false);
  const [cfg, setCfg] = useState({ ocultarTotal: false, mostrarPorDoc: false });
  const [sCli, setSCli] = useState('');
  const [sFecha, setSFecha] = useState('');
  const [sDoc, setSDoc] = useState('');
  const [sMonto, setSMonto] = useState('0');
  const [sDetalle, setSDetalle] = useState('');
  const [saldosLocal, setSaldosLocal] = useState([]);

  // Saldos por receptor: los calcula el reporte de historial, que ya agrupa por
  // cliente o proveedor según el modo.
  const saldosReales = useMemo(
    () =>
      contactos.map((ficha, indice) => ({
        id: `${ficha.receptorId ?? 'sin-id'}-${indice}`,
        nombre: ficha.contacto || '—',
        tipo: tipoIdentificacion(ficha.identificacion),
        ident: ficha.identificacion || '—',
        saldo: ficha.saldo.toFixed(2),
      })),
    [contactos],
  );

  const saldosCombinados = useMemo(() => {
    // locales primero (registrados via modal), luego reales
    const locales = saldosLocal.map((r) => ({ ...r, esLocal: true }));
    return [...locales, ...saldosReales];
  }, [saldosLocal, saldosReales]);

  const saldosFiltrados = useMemo(() => {
    const q = recepQuery.trim().toLowerCase();
    if (!q) return saldosCombinados;
    return saldosCombinados.filter((r) => r.nombre.toLowerCase().includes(q) || r.ident.toLowerCase().includes(q));
  }, [saldosCombinados, recepQuery]);

  const tablaSaldos = useTablaFiltrada({ datos: saldosFiltrados, termino: '', camposBusqueda: [] });

  const cambiarTipo = (tipo) => {
    setSearchParams({ tipo });
  };

  const guardarSaldo = () => {
    if (!sCli || !sFecha || !sDetalle.trim()) return;
    const rec = {
      id: Date.now(),
      nombre: sCli,
      tipo: 'RUC',
      ident: '—',
      saldo: (parseFloat(sMonto) || 0).toFixed(2),
      esLocal: true,
    };
    setSaldosLocal((prev) => [rec, ...prev]);
    setSaldoModal(false);
    setSCli(''); setSFecha(''); setSDoc(''); setSMonto('0'); setSDetalle('');
  };

  // KPIs: el saldo global sale del reporte de saldos (deuda viva por documento)
  // y el desglose por vencimiento, de la agenda, que es lo único que conoce las
  // fechas de cada cuota.
  const kpis = useMemo(() => {
    const cargando = reporteSaldos.cargando || reporteAgenda.cargando || reporteRecibos.cargando;
    const sinDatos = '—';
    const esperando = cargando ? 'Cargando…' : 'Sin datos';

    const dentroDe30 = cuotas.filter((c) => {
      if (c.saldo <= 0) return false;
      const dias = -c.diasMora; // `diasMora` negativo son días que faltan.
      return dias >= 0 && dias <= 30;
    });
    const mesActual = claveMes(new Date());
    const movidoMes = movimientos
      .filter((m) => m.estado !== 'Anulado' && String(m.fecha).startsWith(mesActual))
      .reduce((total, m) => total + m.monto, 0);

    return [
      {
        label: modoCobrar ? 'Saldo por cobrar' : 'Saldo por pagar',
        value: saldos ? formatearMoneda(saldos.saldo) : sinDatos,
        sub: saldos
          ? `${saldos.totalDocumentos} ${saldos.totalDocumentos === 1 ? 'documento' : 'documentos'}`
          : esperando,
        tono: 'acento',
      },
      {
        label: 'En cuotas',
        value: agenda ? formatearMoneda(agenda.saldo) : sinDatos,
        sub: agenda
          ? `${agenda.totalCuotas} ${agenda.totalCuotas === 1 ? 'cuota pendiente' : 'cuotas pendientes'}`
          : esperando,
        tono: 'neutro',
      },
      {
        label: 'Vencidas',
        value: agenda ? formatearMoneda(agenda.saldoVencido) : sinDatos,
        sub: agenda ? `${agenda.vencidas} cuotas vencidas` : esperando,
        tono: 'error',
      },
      {
        label: 'Vencen en 30 días',
        value: agenda
          ? formatearMoneda(dentroDe30.reduce((total, c) => total + c.saldo, 0))
          : sinDatos,
        sub: recibos
          ? `${modoCobrar ? 'Cobrado' : 'Pagado'} este mes: ${formatearMoneda(movidoMes)}`
          : esperando,
        tono: 'ok',
      },
    ];
  }, [
    saldos,
    agenda,
    recibos,
    cuotas,
    movimientos,
    modoCobrar,
    reporteSaldos.cargando,
    reporteAgenda.cargando,
    reporteRecibos.cargando,
  ]);

  const titulo = modoCobrar ? 'Cuentas por Cobrar' : 'Cuentas por Pagar';

  // El corte seco solo en Inicio: en las demás pestañas cada panel enseña su
  // propio estado y dejar la navegación en pie vale más que un cartel único.
  if (tab === 'inicio' && reporteSaldos.sinConexion) {
    return (
      <div className={styles.page}>
        <header className={styles.topbar}><h1 className={styles.title}>{titulo}</h1></header>
        <SinConexion onReintentar={reporteSaldos.recargar} />
      </div>
    );
  }
  if (tab === 'inicio' && reporteSaldos.error) {
    return (
      <div className={styles.page}>
        <header className={styles.topbar}><h1 className={styles.title}>{titulo}</h1></header>
        <ErrorCarga mensaje={reporteSaldos.error} onReintentar={reporteSaldos.recargar} />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.topbar}>
        <h1 className={styles.title}>{titulo}</h1>
        <div className={styles.tipoSwitch}>
          <button className={`${styles.tipoBtn} ${modoCobrar ? styles.tipoActivo : ''}`} onClick={() => cambiarTipo('cobrar')}>Cobrar</button>
          <button className={`${styles.tipoBtn} ${!modoCobrar ? styles.tipoActivo : ''}`} onClick={() => cambiarTipo('pagar')}>Pagar</button>
        </div>
      </header>

      <div className={styles.bannerInfo}>
        {modoCobrar ? (
          <>
            Gestión de cobros pendientes. Las cuotas se generan desde una factura a crédito y cada cobro queda como un <strong>recibo</strong> aparte: un cliente puede abonar de a poco, y cada abono es un movimiento de caja que hay que poder explicar.
          </>
        ) : (
          <>
            Gestión de pagos pendientes. Aquí se ven los <strong>gastos</strong> que se saldan con egresos y las <strong>liquidaciones de compra</strong>, que son los dos documentos con los que se le debe dinero a un proveedor. El pago se registra desde Gastos.
          </>
        )}
      </div>

      <nav className={styles.tabs} aria-label="Secciones de cuentas">
        {TABS.map((t) => (
          <button key={t.id} className={`${styles.tab} ${tab === t.id ? styles.tabActivo : ''}`} onClick={() => setTab(t.id)}>
            <t.Icon size={16} /> {t.label}
          </button>
        ))}
        <Link to="/" className={styles.tabVolver}>Volver</Link>
      </nav>

      {tab === 'inicio' && (
        <div className={styles.inicioGrid}>
          <div className={styles.kpiCol}>
            {kpis.map((k) => (
              <div key={k.label} className={styles.kpi}>
                <span className={`${styles.kpiIcon} ${styles[TONO[k.tono]]}`}><Wallet size={16} /></span>
                <div><div className={styles.kpiLabel}>{k.label}</div><div className={`${styles.kpiValue} cifra`}>{k.value}</div><div className={styles.kpiSub}>{k.sub}</div></div>
              </div>
            ))}
          </div>
          <div className={styles.agendaCard}>
            <div className={styles.agendaHead}>Próximos vencimientos</div>
            <Estado reporte={reporteAgenda} columnas={4}>
              {cuotas.length === 0 ? (
                <div className={styles.emptyCenter}>
                  <CalendarDays size={52} strokeWidth={1.5} className={styles.emptyIcon} />
                  <div className={styles.emptyTitle}>Aún no hay {modoCobrar ? 'cobros' : 'pagos'} pendientes</div>
                  <div className={styles.emptyBody}>{modoCobrar ? 'Las ventas a crédito aparecerán aquí automáticamente. También puedes registrar saldos anteriores desde Clientes.' : 'Las compras y gastos a crédito aparecerán aquí automáticamente.'}</div>
                  <button className={styles.btnPrimario} onClick={() => setTab('recep')}>Revisar {Wp}</button>
                </div>
              ) : (
                <div className={styles.tableWrap}>
                  <table className={styles.table}>
                    <thead><tr><th>VENCE</th><th>DOCUMENTO</th><th>{W.toUpperCase()}</th><th>SALDO</th></tr></thead>
                    <tbody>
                      {cuotas.slice(0, FILAS_PREVISUALIZACION).map((c) => (
                        <tr key={`${c.origen}-${c.documentoId}-${c.numero}`}>
                          <td>{c.vence}</td>
                          <td>{c.documento}</td>
                          <td>{c.contacto}</td>
                          <td className="cifra">{formatearMoneda(c.saldo)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Estado>
          </div>
        </div>
      )}

      {tab === 'recep' && (
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className={styles.filtrosTitulo}><Search size={16} /> Filtros de búsqueda</div>
            <div className={styles.toolbar}>
              <div className={styles.searchWrap}>
                <Search size={15} className={styles.searchIcon} />
                <input className={styles.searchInput} placeholder={`Buscar ${W.toLowerCase()}`} value={recepQuery} onChange={(e) => setRecepQuery(e.target.value)} />
              </div>
              <button className={styles.btnIcon} onClick={reporteHistorial.recargar} title="Actualizar"><RefreshCw size={16} /></button>
              <select className={styles.select} value={tablaSaldos.tamanoPagina} onChange={(e) => tablaSaldos.setTamanoPagina(Number(e.target.value))}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select>
              <div className={styles.espaciador} />
              <button className={styles.btnPrimario} onClick={() => setSaldoModal(true)}><Plus size={15} /> Registrar Saldo Anterior</button>
              <button
                className={styles.btnSecundario}
                onClick={() => setTab('gestion')}
                title="Las cuotas se generan desde cada factura a crédito"
              >
                <Upload size={15} /> Ver cuotas
              </button>
            </div>
          </div>

          <Estado reporte={reporteHistorial} columnas={5}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>NOMBRE</th><th>TIPO</th><th>IDENTIFICACIÓN</th><th>SALDO PENDIENTE (USD)</th><th>ACCIONES</th></tr></thead>
                <tbody>
                  {tablaSaldos.visibles.length === 0 ? (
                    <tr><td colSpan={5} className={styles.emptyCell}>{modoCobrar ? 'Aún no hay clientes con saldo pendiente. Las ventas a crédito aparecerán aquí automáticamente.' : 'Aún no hay proveedores con saldo pendiente.'}</td></tr>
                  ) : tablaSaldos.visibles.map((r) => (
                    <tr key={r.id}><td className={styles.cellStrong}>{r.nombre} {r.esLocal && <span className={styles.badgeLocal}>local</span>}</td><td>{r.tipo}</td><td className="cifra">{r.ident}</td><td className={`cifra ${styles.cellFuerte}`}>{r.saldo}</td><td><button className={styles.btnMenu} title="Acciones">⋮</button></td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Estado>
          <div className={styles.paginacion}>
            <span className={styles.pagInfo}>Viendo {tablaSaldos.desde} a {tablaSaldos.hasta} de {tablaSaldos.total} entradas</span>
            <div className={styles.pagBtns}>
              <button className={styles.pagBtn} disabled={tablaSaldos.pagina <= 1} onClick={() => tablaSaldos.setPagina(tablaSaldos.pagina - 1)}>Atrás</button>
              <span className={styles.pagNum}>{tablaSaldos.pagina}</span>
              <button className={styles.pagBtn} disabled={tablaSaldos.pagina >= tablaSaldos.totalPaginas} onClick={() => tablaSaldos.setPagina(tablaSaldos.pagina + 1)}>Siguiente</button>
            </div>
          </div>
        </div>
      )}

      {tab === 'gestion' && (
        <div className={styles.panel}>
          <div className={styles.gestionHead}>
            <div>
              <div className={styles.gestionTitle}>
                Gestión mensual de {modoCobrar ? 'cobros' : 'pagos'}
              </div>
              <div className={styles.gestionSub}>
                {cuotasDelMes.length} {cuotasDelMes.length === 1 ? 'cuota' : 'cuotas'} ·{' '}
                {formatearMoneda(cuotasDelMes.reduce((t, c) => t + c.saldo, 0))} por {accion}
              </div>
            </div>
            <div className={styles.mesNav}>
              <button className={styles.iconBtn} onClick={() => setMesDate((d) => new Date(d.getFullYear(), d.getMonth() - 1, 1))}><ChevronLeft size={16} /></button>
              <button className={styles.btnChip} onClick={() => setMesDate(new Date())}>Hoy</button>
              <button className={styles.iconBtn} onClick={() => setMesDate((d) => new Date(d.getFullYear(), d.getMonth() + 1, 1))}><ChevronRight size={16} /></button>
            </div>
          </div>
          <div className={styles.mesLabelRow}>
            <div className={styles.mesLabel}>{mesLabel(mesDate)}</div>
            <span className={styles.badgeMes}><CalendarDays size={14} /> Mensual</span>
          </div>

          {errorCobro && <div className={styles.avisoError}>{errorCobro}</div>}

          <Estado reporte={reporteAgenda} columnas={8}>
            {cuotasDelMes.length === 0 ? (
              <div className={styles.emptyCenter}>
                <CalendarDays size={52} strokeWidth={1.5} className={styles.emptyIcon} />
                <div className={styles.emptyTitle}>
                  No hay {modoCobrar ? 'cobros' : 'pagos'} programados este mes
                </div>
                <div className={styles.emptyBody}>
                  {modoCobrar
                    ? 'Genera cuotas desde una factura a crédito y sus vencimientos aparecerán aquí.'
                    : 'Los gastos y las liquidaciones de compra pendientes aparecerán aquí el mes en que vencen.'}
                </div>
                <button className={styles.btnPrimario} onClick={() => setTab('recep')}>
                  Revisar {Wp}
                </button>
              </div>
            ) : (
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>DOCUMENTO</th><th>{W.toUpperCase()}</th><th>CUOTA</th>
                      <th>VENCE</th><th>MONTO</th><th>SALDO</th><th>ESTADO</th><th>ACCIONES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cuotasDelMes.map((cuota) => (
                      <tr key={`${cuota.origen}-${cuota.documentoId}-${cuota.numero}`}>
                        <td>{cuota.documento}</td>
                        <td>{cuota.contacto}</td>
                        <td>#{cuota.numero}</td>
                        <td>{cuota.vence}</td>
                        <td>{formatearMoneda(cuota.monto)}</td>
                        <td>{formatearMoneda(cuota.saldo)}</td>
                        <td>
                          <span className={cuota.estado === 'Saldado' ? styles.badgeOk : styles.badgeWarn}>
                            {cuota.estado}
                          </span>
                        </td>
                        <td>
                          {modoCobrar && cuota.saldo > 0 ? (
                            <button className={styles.btnPrimario} onClick={() => cobrar(cuota)}>
                              Cobrar {formatearMoneda(cuota.saldo)}
                            </button>
                          ) : (
                            <span className={styles.pistaAccion}>
                              {modoCobrar ? '—' : 'Se paga desde Gastos'}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Estado>
        </div>
      )}

      {tab === 'historial' && (
        <div className={styles.panel}>
          <div className={styles.histHead}>Historial de {modoCobrar ? 'cobros' : 'pagos'}</div>

          <div className={styles.tiles}>
            <div className={`${styles.tile} ${styles.tonoNeutro}`}>
              <div className={styles.tileLabel}>{modoCobrar ? 'Cobros' : 'Pagos'} registrados</div>
              <div className={styles.tileVal}>{recibos?.totalRecibos ?? 0}</div>
            </div>
            <div className={`${styles.tile} ${styles.tonoOk}`}>
              <div className={styles.tileLabel}>Monto aplicado</div>
              <div className={styles.tileVal}>{formatearMoneda(recibos?.aplicado ?? 0)}</div>
            </div>
            <div className={`${styles.tile} ${styles.tonoAcento}`}>
              <div className={styles.tileLabel}>Activos</div>
              <div className={styles.tileVal}>{(recibos?.totalRecibos ?? 0) - (recibos?.anulados ?? 0)}</div>
            </div>
            <div className={`${styles.tile} ${styles.tonoError}`}>
              <div className={styles.tileLabel}>Revertidos</div>
              <div className={styles.tileVal}>{recibos?.anulados ?? 0}</div>
            </div>
          </div>

          <div className={styles.toolbar}>
            <div className={`${styles.searchWrap} ${styles.searchAncho}`}>
              <Search size={15} className={styles.searchIcon} />
              <input className={styles.searchInput} placeholder={`Buscar por número, ${W.toLowerCase()} o referencia`} value={histQuery} onChange={(e) => setHistQuery(e.target.value)} />
            </div>
            <button className={styles.btnIcon} onClick={reporteRecibos.recargar} title="Actualizar"><RefreshCw size={16} /></button>
          </div>

          {errorCobro && <div className={styles.avisoError}>{errorCobro}</div>}

          <Estado reporte={reporteRecibos} columnas={8}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>NÚMERO</th><th>FECHA</th><th>{W.toUpperCase()}</th><th>DOCUMENTO</th>
                    <th>MONTO</th><th>MÉTODO</th><th>ESTADO</th><th>ACCIONES</th>
                  </tr>
                </thead>
                <tbody>
                  {movimientos.filter((m) =>
                    !histQuery ||
                    [m.numero, m.contacto, m.referencia, m.documento].some((v) =>
                      String(v).toLowerCase().includes(histQuery.toLowerCase()),
                    ),
                  ).map((movimiento) => (
                    <tr key={`${movimiento.origen}-${movimiento.reciboId}`}>
                      <td>{movimiento.numero}</td>
                      <td>{movimiento.fecha}</td>
                      <td>{movimiento.contacto || '—'}</td>
                      <td>{movimiento.documento || '—'}</td>
                      <td>{formatearMoneda(movimiento.monto)}</td>
                      <td>{movimiento.formaPago}</td>
                      <td>
                        <span className={movimiento.estado === 'Anulado' ? styles.badgeWarn : styles.badgeOk}>
                          {movimiento.estado}
                        </span>
                      </td>
                      <td>
                        {/* Anular es cosa del recibo; un egreso se revierte desde Gastos. */}
                        {movimiento.estado !== 'Anulado' && movimiento.origen === 'Recibo' && modoCobrar && (
                          <button className={styles.btnSecundario} onClick={() => revertir(movimiento)}>
                            Revertir
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {movimientos.length === 0 && (
                    <tr><td colSpan={8} className={styles.emptyCell}>Aún no se ha registrado ningún {modoCobrar ? 'cobro' : 'pago'}.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Estado>
        </div>
      )}

      {tab === 'vencidos' && (
        <div className={styles.panel}>
          <div className={styles.vencHead}>
            <div>
              <div className={styles.gestionTitle}>
                Vencimientos por {accion}
              </div>
              <div className={styles.gestionSub}>
                {cuotasVencidas.length === 0
                  ? `No hay ${Wp.toLowerCase()} con cuotas vencidas pendientes.`
                  : `${cuotasVencidas.length} ${cuotasVencidas.length === 1 ? 'cuota vencida' : 'cuotas vencidas'}.`}
              </div>
            </div>
            <span className={styles.badgeOk}>
              Saldo vencido: {formatearMoneda(agenda?.saldoVencido ?? 0)}
            </span>
            <span className={styles.badgeWarn}>Cuotas con atraso: {cuotasVencidas.length}</span>
            <span className={styles.badgeMuted}>
              Total pendiente: {formatearMoneda(agenda?.saldo ?? 0)}
            </span>
          </div>

          <div className={styles.toolbar}>
            <div className={`${styles.searchWrap} ${styles.searchAncho}`}>
              <Search size={15} className={styles.searchIcon} />
              <input className={styles.searchInput} placeholder={`Buscar ${W.toLowerCase()}, documento o cuota`} value={vencQuery} onChange={(e) => setVencQuery(e.target.value)} />
            </div>
            <button className={styles.btnIcon} onClick={reporteAgenda.recargar} title="Actualizar"><RefreshCw size={16} /></button>
          </div>

          {errorCobro && <div className={styles.avisoError}>{errorCobro}</div>}

          <Estado reporte={reporteAgenda} columnas={7}>
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>{W.toUpperCase()}</th><th>DOCUMENTO</th><th>CUOTA</th>
                    <th>VENCIMIENTO</th><th>DÍAS DE MORA</th><th>SALDO VENCIDO</th><th>ACCIONES</th>
                  </tr>
                </thead>
                <tbody>
                  {cuotasVencidas.filter((c) =>
                    !vencQuery ||
                    [c.contacto, c.documento].some((v) =>
                      String(v).toLowerCase().includes(vencQuery.toLowerCase()),
                    ),
                  ).map((cuota) => (
                    <tr key={`${cuota.origen}-${cuota.documentoId}-${cuota.numero}`}>
                      <td>{cuota.contacto}</td>
                      <td>{cuota.documento}</td>
                      <td>#{cuota.numero}</td>
                      <td>{cuota.vence}</td>
                      <td><span className={styles.badgeWarn}>{cuota.diasMora} días</span></td>
                      <td>{formatearMoneda(cuota.saldo)}</td>
                      <td>
                        {modoCobrar ? (
                          <button className={styles.btnPrimario} onClick={() => cobrar(cuota)}>
                            Cobrar
                          </button>
                        ) : (
                          <span className={styles.pistaAccion}>Se paga desde Gastos</span>
                        )}
                      </td>
                    </tr>
                  ))}
                  {cuotasVencidas.length === 0 && (
                    <tr><td colSpan={7} className={styles.emptyCell}>No hay {Wp.toLowerCase()} con cuotas vencidas pendientes.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </Estado>
        </div>
      )}

      {tab === 'reportes' && (
        <div className={styles.reportesGrid}>
          <div className={styles.centroReportes}><span className={styles.centroIcon}><BarChart3 size={20} /></span><div><div className={styles.centroLabel}>CENTRO DE REPORTES</div><div className={styles.centroTitle}>Reportes de cuentas pendientes</div><div className={styles.centroSub}>Saldos, cuotas, {modoCobrar ? 'recibos' : 'pagos'} e historial de {modoCobrar ? 'cobro' : 'pago'}, calculados en el servidor. Cada uno se descarga en CSV (separador «;» y BOM: Excel en español lo abre tal cual).</div></div></div>

          <TarjetaReporte
            titulo="Saldo pendiente por documento"
            descripcion={`${W}, moneda, vencimiento, total original y saldo restante de cada documento.`}
            badge={badgeReporte}
            csv={urlCsvCuentas('saldos', { modo })}
            reporte={reporteSaldos}
            columnas={6}
            hayDatos={(saldos?.documentos.length ?? 0) > 0}
            vacio={`No hay documentos con saldo por ${accion}.`}
          >
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>DOCUMENTO</th><th>{W.toUpperCase()}</th><th>VENCE</th><th>TOTAL</th><th>SALDO</th><th>ESTADO</th></tr></thead>
                <tbody>
                  {(saldos?.documentos ?? []).slice(0, FILAS_PREVISUALIZACION).map((d) => (
                    <tr key={`${d.origen}-${d.documentoId}`}>
                      <td className={styles.cellStrong}>{d.numero}</td>
                      <td>{d.contacto}</td>
                      <td>{d.vence}</td>
                      <td className="cifra">{formatearMoneda(d.total)}</td>
                      <td className="cifra">{formatearMoneda(d.saldo)}</td>
                      <td><span className={d.estado === 'Saldado' ? styles.badgeOk : styles.badgeWarn}>{d.estado}</span></td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={3}>TOTAL</td>
                    <td className="cifra">{formatearMoneda(saldos?.totalOriginal ?? 0)}</td>
                    <td className="cifra">{formatearMoneda(saldos?.saldo ?? 0)}</td>
                    <td />
                  </tr>
                </tbody>
              </table>
            </div>
            <PieVista mostradas={Math.min(FILAS_PREVISUALIZACION, saldos?.documentos.length ?? 0)} total={saldos?.documentos.length ?? 0} />
          </TarjetaReporte>

          <TarjetaReporte
            titulo="Agenda de cuotas"
            descripcion="Cuotas por fecha de vencimiento, con su documento, su contacto y los días de mora."
            badge={badgeReporte}
            csv={urlCsvCuentas('agenda', { modo })}
            reporte={reporteAgenda}
            columnas={6}
            hayDatos={cuotas.length > 0}
            vacio="No hay cuotas pendientes en agenda."
          >
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>VENCE</th><th>DOCUMENTO</th><th>CUOTA</th><th>{W.toUpperCase()}</th><th>MORA</th><th>SALDO</th></tr></thead>
                <tbody>
                  {cuotas.slice(0, FILAS_PREVISUALIZACION).map((c) => (
                    <tr key={`${c.origen}-${c.documentoId}-${c.numero}`}>
                      <td>{c.vence}</td>
                      <td className={styles.cellStrong}>{c.documento}</td>
                      <td>#{c.numero}</td>
                      <td>{c.contacto}</td>
                      <td>{c.diasMora > 0 ? `${c.diasMora} días` : '—'}</td>
                      <td className="cifra">{formatearMoneda(c.saldo)}</td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={5}>TOTAL ({agenda?.vencidas ?? 0} vencidas)</td>
                    <td className="cifra">{formatearMoneda(agenda?.saldo ?? 0)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <PieVista mostradas={Math.min(FILAS_PREVISUALIZACION, cuotas.length)} total={cuotas.length} />
          </TarjetaReporte>

          <TarjetaReporte
            titulo={modoCobrar ? 'Recibos generados' : 'Pagos aplicados'}
            descripcion={`Movimientos aplicados, su estado, su forma de pago y el documento al que fueron por ${Wp.toLowerCase()}.`}
            badge={badgeReporte}
            csv={urlCsvCuentas('recibos', { modo })}
            reporte={reporteRecibos}
            columnas={6}
            hayDatos={movimientos.length > 0}
            vacio={`Aún no se ha registrado ningún ${modoCobrar ? 'cobro' : 'pago'}.`}
          >
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>NÚMERO</th><th>FECHA</th><th>{W.toUpperCase()}</th><th>DOCUMENTO</th><th>MONTO</th><th>ESTADO</th></tr></thead>
                <tbody>
                  {movimientos.slice(0, FILAS_PREVISUALIZACION).map((m) => (
                    <tr key={`${m.origen}-${m.reciboId}`}>
                      <td className={styles.cellStrong}>{m.numero}</td>
                      <td>{m.fecha}</td>
                      <td>{m.contacto || '—'}</td>
                      <td>{m.documento || '—'}</td>
                      <td className="cifra">{formatearMoneda(m.monto)}</td>
                      <td><span className={m.estado === 'Anulado' ? styles.badgeWarn : styles.badgeOk}>{m.estado}</span></td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={4}>TOTAL APLICADO ({recibos?.anulados ?? 0} anulados)</td>
                    <td className="cifra">{formatearMoneda(recibos?.aplicado ?? 0)}</td>
                    <td />
                  </tr>
                </tbody>
              </table>
            </div>
            <PieVista mostradas={Math.min(FILAS_PREVISUALIZACION, movimientos.length)} total={movimientos.length} />
          </TarjetaReporte>

          <TarjetaReporte
            titulo="Rotación de cuentas"
            descripcion={`Volumen pendiente por tipo de documento en el año en curso, con el promedio por documento y los días de ${modoCobrar ? 'recuperación' : 'pago'}.`}
            badge={badgeReporte}
            csv={urlCsvCuentas('rotacion', { modo })}
            reporte={reporteRotacion}
            columnas={5}
            hayDatos={(rotacion?.porTipo.length ?? 0) > 0}
            vacio={`No hay documentos emitidos en el período para ${accion}.`}
          >
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>TIPO</th><th>DOCUMENTOS</th><th>PENDIENTE</th><th>PROMEDIO</th><th>DÍAS</th></tr></thead>
                <tbody>
                  {(rotacion?.porTipo ?? []).slice(0, FILAS_PREVISUALIZACION).map((fila) => (
                    <tr key={fila.grupo}>
                      <td className={styles.cellStrong}>{fila.grupo}</td>
                      <td className="cifra">{fila.documentos}</td>
                      <td className="cifra">{formatearMoneda(fila.pendiente)}</td>
                      <td className="cifra">{formatearMoneda(fila.promedio)}</td>
                      {/* Sin dinero movido no hay días que enseñar: un guion, no un cero. */}
                      <td className="cifra">{fila.diasRecuperacion === null ? '—' : fila.diasRecuperacion}</td>
                    </tr>
                  ))}
                  {rotacion?.totales && (
                    <tr className={styles.filaTotal}>
                      <td>TOTAL</td>
                      <td className="cifra">{rotacion.totales.documentos}</td>
                      <td className="cifra">{formatearMoneda(rotacion.totales.pendiente)}</td>
                      <td className="cifra">{formatearMoneda(rotacion.totales.promedio)}</td>
                      <td className="cifra">{rotacion.totales.diasRecuperacion === null ? '—' : rotacion.totales.diasRecuperacion}</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </TarjetaReporte>

          <TarjetaReporte
            titulo={`Historial por ${W.toLowerCase()}`}
            descripcion="Saldo actual, monto abonado, cuotas pendientes, vencidas y próxima fecha de pago."
            badge={badgeReporte}
            csv={urlCsvCuentas('historial', { modo, solo_con_saldo: true })}
            reporte={reporteHistorial}
            columnas={6}
            hayDatos={contactos.length > 0}
            vacio={`Ningún ${W.toLowerCase()} tiene saldo pendiente.`}
          >
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead><tr><th>{W.toUpperCase()}</th><th>DOCS.</th><th>ABONADO</th><th>SALDO</th><th>CUOTAS VENCIDAS</th><th>PRÓXIMO PAGO</th></tr></thead>
                <tbody>
                  {contactos.slice(0, FILAS_PREVISUALIZACION).map((ficha, indice) => (
                    <tr key={`${ficha.receptorId ?? ficha.contacto}-${indice}`}>
                      <td className={styles.cellStrong}>{ficha.contacto}</td>
                      <td className="cifra">{ficha.documentos}</td>
                      <td className="cifra">{formatearMoneda(ficha.abonado)}</td>
                      <td className="cifra">{formatearMoneda(ficha.saldo)}</td>
                      <td className="cifra">{ficha.cuotasVencidas}</td>
                      <td>{ficha.proximaFecha ?? '—'}</td>
                    </tr>
                  ))}
                  <tr className={styles.filaTotal}>
                    <td colSpan={2}>TOTAL</td>
                    <td className="cifra">{formatearMoneda(historial?.abonado ?? 0)}</td>
                    <td className="cifra">{formatearMoneda(historial?.saldo ?? 0)}</td>
                    <td colSpan={2} />
                  </tr>
                </tbody>
              </table>
            </div>
            <PieVista mostradas={Math.min(FILAS_PREVISUALIZACION, contactos.length)} total={contactos.length} />
          </TarjetaReporte>
        </div>
      )}

      {saldoModal && (
        <div className={styles.overlay} onClick={() => setSaldoModal(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <button className={styles.modalClose} onClick={() => setSaldoModal(false)}><X size={17} /></button>
            <h2 className={styles.modalTitle}>Registrar saldo por {accion}</h2>
            <div className={styles.modalBanner}>Registra aquí los saldos que {modoCobrar ? 'tus clientes te deben' : 'le debes a tus proveedores'}, aunque no vengan de un documento de Factoa. Si son varios, podrás cargarlos con Excel en Importar saldos.</div>
            <div className={styles.modalGrid}>
              <label className={styles.field}><span>{W}</span><input className={styles.input} placeholder={W} value={sCli} onChange={(e) => setSCli(e.target.value)} /></label>
              <label className={styles.field}><span>Fecha límite</span><input className={styles.input} type="date" value={sFecha} onChange={(e) => setSFecha(e.target.value)} /></label>
              <label className={styles.field}><span>Moneda</span><select className={styles.input}><option>Dólares</option></select></label>
              <label className={styles.field}><span>Número de documento</span><input className={styles.input} placeholder="Solo números" value={sDoc} onChange={(e) => setSDoc(e.target.value)} /></label>
              <label className={styles.field}><span>Saldo pendiente</span><input className={styles.input} value={sMonto} onChange={(e) => setSMonto(e.target.value)} /></label>
              <label className={`${styles.field} ${styles.campoAlto}`}><span>Detalle *</span><textarea className={styles.textarea} rows={4} placeholder="Detalle" value={sDetalle} onChange={(e) => setSDetalle(e.target.value)} /></label>
            </div>
            <div className={styles.modalActions}><button className={styles.btnSecundario} onClick={() => setSaldoModal(false)}>Cancelar</button><button className={styles.btnPrimario} onClick={guardarSaldo}>Guardar Saldo</button></div>
          </div>
        </div>
      )}

      {cfgModal && (
        <div className={styles.overlay} onClick={() => setCfgModal(false)}>
          <div className={styles.modalSm} onClick={(e) => e.stopPropagation()}>
            <h2 className={styles.modalTitle}>Configuración de recibos</h2>
            <p className={styles.modalSub}>Opciones de impresión de los recibos. Lo no configurado usa los valores por defecto.</p>
            <div className={styles.cfgOpts}>
              <label className={styles.cfgRow}><span className={styles.toggle} data-on={cfg.ocultarTotal} onClick={() => setCfg((c) => ({ ...c, ocultarTotal: !c.ocultarTotal }))}><span className={`${styles.knob} ${cfg.ocultarTotal ? styles.knobOn : ''}`} /></span> Ocultar la sección «Total Pendiente»<span className={styles.cfgDesc}>Por defecto se muestra el total pendiente del {W.toLowerCase()}.</span></label>
              <label className={styles.cfgRow}><span className={styles.toggle} data-on={cfg.mostrarPorDoc} onClick={() => setCfg((c) => ({ ...c, mostrarPorDoc: !c.mostrarPorDoc }))}><span className={`${styles.knob} ${cfg.mostrarPorDoc ? styles.knobOn : ''}`} /></span> Mostrar la sección «Pendiente por documento»<span className={styles.cfgDesc}>Actívala para imprimir el saldo pendiente completo de cada factura.</span></label>
            </div>
            <div className={styles.modalActions}><button className={styles.btnGhost} onClick={() => setCfgModal(false)}>Cancelar</button><button className={styles.btnPrimario} onClick={() => setCfgModal(false)}>Guardar</button></div>
          </div>
        </div>
      )}
    </div>
  );
}
