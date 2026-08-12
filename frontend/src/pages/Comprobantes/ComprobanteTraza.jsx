import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ZoomIn,
  ZoomOut,
  Check,
  Download,
  FileText,
  ExternalLink,
  Printer,
  Search,
  ChevronDown,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { api, ErrorApi } from '../../api/cliente';
import {
  urlRide,
  urlXml,
  emitirAlSri,
  consultarEstadoSri,
  anularDocumento,
  ESTADOS_EMITIBLES,
  ESTADOS_CONSULTABLES,
} from '../../api/documentos';
import { comprobanteDesdeApi } from '../../api/adaptadores';
import { ErrorCarga, SinConexion, TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './ComprobanteTraza.module.css';

const STEPS = [
  { label: 'Generación', sub: 'Borrador creado' },
  { label: 'Estado tributario', sub: 'Validación SRI' },
  { label: 'Envío', sub: 'Entrega al receptor' },
  { label: 'Finalizada', sub: 'Autorizado y archivado' },
];

function adaptador(registro) {
  try {
    return comprobanteDesdeApi(registro);
  } catch {
    return {
      id: registro.id,
      numero: registro.numero,
      claveAcceso: registro.clave_acceso,
      numeroAutorizacion: registro.numero_autorizacion,
      estadoSRI: registro.estado_sri,
      estadoPago: registro.estado_pago,
      fecha: registro.fecha_emision,
      total: Number(registro.importe_total ?? 0),
    };
  }
}

export default function ComprobanteTraza() {
  const { id } = useParams();
  const [comprobante, setComprobante] = useState(null);
  const [crudo, setCrudo] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);
  const [sinConexion, setSinConexion] = useState(false);
  const [zoom, setZoom] = useState(100);
  const [mensaje, setMensaje] = useState(null);
  const [accion, setAccion] = useState(null);
  const [pagosOpen, setPagosOpen] = useState(true);
  const [ncOpen, setNcOpen] = useState(false);
  const [ndOpen, setNdOpen] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    async function cargar() {
      setCargando(true);
      setError(null);
      setSinConexion(false);
      try {
        const { datos } = await api.obtener(`/comprobantes/${id}`, undefined, {
          senal: ctrl.signal,
        });
        if (ctrl.signal.aborted) return;
        setCrudo(datos);
        setComprobante(adaptador(datos));
      } catch (e) {
        if (e.name === 'AbortError') return;
        if (e instanceof ErrorApi && e.esFalloDeRed) {
          setSinConexion(true);
        } else {
          setError(e.message ?? 'No se pudo cargar el comprobante.');
        }
      } finally {
        if (!ctrl.signal.aborted) setCargando(false);
      }
    }
    cargar();
    return () => ctrl.abort();
  }, [id]);

  const claveAcceso = crudo?.clave_acceso ?? comprobante?.claveAcceso ?? null;
  const estadoSRI = crudo?.estado_sri ?? comprobante?.estadoSRI ?? '—';
  const numero = crudo?.numero ?? comprobante?.numero ?? `ID ${id}`;
  const puedeEmitir = ESTADOS_EMITIBLES.has(estadoSRI);
  const puedeConsultar = ESTADOS_CONSULTABLES.has(estadoSRI);
  const esAutorizado = estadoSRI === 'Autorizado';
  const esAnulado = estadoSRI === 'Anulado';

  const zoomIn = () => setZoom((z) => Math.min(140, z + 10));
  const zoomOut = () => setZoom((z) => Math.max(60, z - 10));

  async function handleEmitir() {
    setAccion('emitir');
    setMensaje(null);
    try {
      const { datos } = await emitirAlSri(id);
      // RespuestaEmision: { comprobante, estado_recepcion, estado_autorizacion, mensajes }
      const actualizado = datos?.comprobante ?? datos;
      if (actualizado) {
        setCrudo(actualizado);
        setComprobante(adaptador(actualizado));
      }
      const msgs = datos?.mensajes ?? [];
      const texto =
        msgs.length > 0
          ? msgs.map((m) => m.mensaje ?? JSON.stringify(m)).join(' · ')
          : `Estado: ${datos?.estado_autorizacion ?? datos?.estado_recepcion ?? 'Recibido'}`;
      setMensaje({ tono: 'ok', texto: `Emitido. ${texto}` });
    } catch (e) {
      setMensaje({ tono: 'error', texto: e.message });
    } finally {
      setAccion(null);
    }
  }

  async function handleConsultar() {
    setAccion('consultar');
    setMensaje(null);
    try {
      const { datos } = await consultarEstadoSri(id);
      const actualizado = datos?.comprobante ?? datos;
      if (actualizado) {
        setCrudo(actualizado);
        setComprobante(adaptador(actualizado));
      }
      const msgs = datos?.mensajes ?? [];
      const texto =
        msgs.length > 0
          ? msgs.map((m) => m.mensaje ?? JSON.stringify(m)).join(' · ')
          : `Autorización: ${datos?.estado_autorizacion ?? '—'}`;
      setMensaje({ tono: 'ok', texto: `Consulta SRI: ${texto}` });
    } catch (e) {
      setMensaje({ tono: 'error', texto: e.message });
    } finally {
      setAccion(null);
    }
  }

  async function handleAnular() {
    if (!confirm('¿Anular este comprobante? No se puede anular un comprobante Autorizado (usa Nota de Crédito).')) return;
    setAccion('anular');
    setMensaje(null);
    try {
      const { datos } = await anularDocumento(id);
      const actualizado = datos ?? null;
      if (actualizado) {
        setCrudo(actualizado);
        setComprobante(adaptador(actualizado));
      }
      setMensaje({ tono: 'ok', texto: 'Comprobante anulado.' });
    } catch (e) {
      setMensaje({ tono: 'error', texto: e.message });
    } finally {
      setAccion(null);
    }
  }

  if (cargando) return <TablaCargando filas={6} columnas={4} />;
  if (sinConexion) return <SinConexion onReintentar={() => window.location.reload()} />;
  if (error) return <ErrorCarga mensaje={error} onReintentar={() => window.location.reload()} />;
  if (!comprobante) return <ErrorCarga mensaje="Comprobante no encontrado." />;

  return (
    <div className={styles.container}>
      {/* Card superior: header + steps */}
      <div className={styles.cardTop}>
        <div className={styles.topBar}>
          <Link to="/comprobantes" className={styles.btnVolver}>
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 12H5M11 6l-6 6 6 6" />
            </svg>
            Volver al listado
          </Link>
          <span className={styles.sep} />
          <span className={styles.topTitle}>Seguimiento del comprobante</span>
          <span className={styles.badgeNumero}>{numero}</span>
          <span className={styles.badgeEstado} data-estado={estadoSRI}>
            {estadoSRI}
          </span>
        </div>
        <div className={styles.steps}>
          {STEPS.map((st) => (
            <div key={st.label} className={styles.step}>
              <span className={styles.stepIcon}>
                <Check size={15} />
              </span>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span className={styles.stepLabel}>{st.label}</span>
                  <span style={{ flex: 1, height: 1, background: 'var(--field-borde)', minWidth: 14 }} />
                </div>
                <div className={styles.stepSub}>{st.sub}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Fila principal: visor + acciones */}
      <div className={styles.mainRow}>
        {/* Panel izquierdo: visor RIDE */}
        <div className={styles.visorWrap}>
          <div className={styles.zoomBar}>
            <div>
              <button type="button" className={styles.zoomBtn} onClick={zoomOut} title="Reducir" aria-label="Reducir zoom">
                <ZoomOut size={17} />
              </button>
              <span className={styles.zoomVal}>{zoom}%</span>
              <button type="button" className={styles.zoomBtn} onClick={zoomIn} title="Ampliar" aria-label="Ampliar zoom">
                <ZoomIn size={17} />
              </button>
            </div>
          </div>

          <div className={styles.rideBox}>
            {!claveAcceso ? (
              <div className={styles.borradorPlaceholder}>
                <FileText size={36} style={{ opacity: 0.5 }} />
                <div className={styles.borradorTitle}>Borrador — emite para ver RIDE</div>
                <div className={styles.borradorSub}>
                  Este comprobante aún no tiene <code>clave_acceso</code>. Pulsa <strong>Enviar al SRI</strong> para generar el XML, firmarlo y habilitar el RIDE/PDF.
                </div>
                <div className={styles.borradorMeta}>
                  Estado actual: <strong>{estadoSRI}</strong> · Número: <span className="cifra">{numero}</span>
                </div>
              </div>
            ) : (
              <div
                className={styles.rideInner}
                style={{ transform: `scale(${zoom / 100})`, transformOrigin: 'top center' }}
              >
                <iframe
                  title={`RIDE ${numero}`}
                  src={urlRide(id)}
                  className={styles.rideFrame}
                  loading="lazy"
                />
              </div>
            )}
          </div>
        </div>

        {/* Panel derecho: gestionar comprobante */}
        <div className={styles.accionesPanel}>
          <div className={styles.accionesLabel}>Acciones principales</div>
          <div className={styles.accionesTitle}>Gestionar comprobante</div>

          {mensaje && (
            <div className={mensaje.tono === 'ok' ? styles.msgOk : styles.msgError} role="status">
              {mensaje.texto}
            </div>
          )}

          <button
            type="button"
            className={styles.btnEnviar}
            onClick={handleEmitir}
            disabled={!puedeEmitir || accion === 'emitir' || esAnulado}
            title={
              !puedeEmitir ? `No se puede emitir en estado ${estadoSRI} (emitibles: ${[...ESTADOS_EMITIBLES].join(', ')})` : undefined
            }
          >
            {accion === 'emitir' ? <Loader2 size={16} className={styles.girando} /> : null}
            {accion === 'emitir' ? 'Enviando…' : 'Enviar al SRI'}
          </button>
          <div className={styles.accionesHint}>El correo incluye el PDF como archivo adjunto.</div>

          <div className={styles.btnStack}>
            <a href={urlRide(id)} target="_blank" rel="noreferrer" className={styles.btnSec}>
              <Download size={15} /> PDF
            </a>
            <a href={urlRide(id)} target="_blank" rel="noreferrer" className={styles.btnAlt}>
              <ExternalLink size={15} /> PDF aparte
            </a>
            <a href={urlRide(id)} target="_blank" rel="noreferrer" className={styles.btnSec}>
              <Printer size={15} /> POS
            </a>
          </div>

          <div className={styles.accionesLabel} style={{ marginTop: 18 }}>
            Archivos fiscales
          </div>
          <div className={styles.btnStack}>
            <a href={urlXml(id)} target="_blank" rel="noreferrer" className={styles.btnSec}>
              <FileText size={15} /> XML
            </a>
            <button
              type="button"
              className={styles.btnSec}
              onClick={handleConsultar}
              disabled={!puedeConsultar || accion === 'consultar'}
              title={
                !puedeConsultar ? `Consulta habilitada en: ${[...ESTADOS_CONSULTABLES].join(', ')}` : undefined
              }
            >
              {accion === 'consultar' ? <Loader2 size={15} className={styles.girando} /> : <Search size={15} />}
              Resp. XML / Consultar SRI
            </button>
          </div>

          <div className={styles.accionesLabel} style={{ marginTop: 18 }}>
            Ajustes del documento
          </div>
          <div className={styles.btnStack}>
            <Link to={`/comprobantes/nota-credito?origen=${id}`} className={styles.btnNc}>
              <FileText size={15} /> Nota de crédito
            </Link>
            <Link to={`/comprobantes/nota-debito?origen=${id}`} className={styles.btnNd}>
              <FileText size={15} /> Nota de débito
            </Link>
            <button
              type="button"
              className={styles.btnDanger}
              onClick={handleAnular}
              disabled={esAutorizado || esAnulado || accion === 'anular'}
              title={esAutorizado ? 'Un comprobante Autorizado no se anula: emite una Nota de Crédito.' : undefined}
            >
              {accion === 'anular' ? <Loader2 size={15} className={styles.girando} /> : <AlertTriangle size={15} />}
              Anular
            </button>
          </div>

          <div className={styles.metaBox}>
            <div>
              <span>Clave acceso</span>
              <code>{claveAcceso ?? '— (borrador)'}</code>
            </div>
            <div>
              <span>Núm. autorización</span>
              <code>{crudo?.numero_autorizacion ?? '—'}</code>
            </div>
          </div>
        </div>
      </div>

      {/* Trazabilidad interna */}
      <div className={styles.trazabilidadHead}>
        <div style={{ flex: 1 }}>
          <div className={styles.trazabilidadEyebrow}>Trazabilidad interna</div>
          <div className={styles.trazabilidadTitle}>Movimientos relacionados</div>
          <div className={styles.trazabilidadSub}>Consulta los pagos y las notas aplicadas a este comprobante.</div>
        </div>
        <span style={{ color: 'var(--accent-primary)', display: 'flex', marginTop: 4 }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 8h13l-3-3M20 16H7l3 3" />
          </svg>
        </span>
      </div>

      {/* Acordeones */}
      <Acordeon
        titulo="Pagos aplicados"
        icon={<Check size={18} style={{ color: 'var(--success)' }} />}
        abierto={pagosOpen}
        onToggle={() => setPagosOpen((v) => !v)}
        columnas={['NÚMERO', 'FECHA', 'ABONO', 'SALDO ANTERIOR', 'ACCIONES']}
      />
      <Acordeon
        titulo="Notas de crédito"
        icon={<FileText size={18} style={{ color: 'var(--accent-primary)' }} />}
        abierto={ncOpen}
        onToggle={() => setNcOpen((v) => !v)}
        columnas={['NÚMERO', 'FECHA', 'REFERENCIA', 'MOTIVO', 'SALDO ANTERIOR', 'MONTO', 'ACTUAL', 'ACCIONES']}
      />
      <Acordeon
        titulo="Notas de débito"
        icon={<FileText size={18} style={{ color: 'var(--accent-primary)' }} />}
        abierto={ndOpen}
        onToggle={() => setNdOpen((v) => !v)}
        columnas={['NÚMERO', 'FECHA', 'REFERENCIA', 'MOTIVO', 'SALDO ANTERIOR', 'MONTO', 'ACTUAL', 'ACCIONES']}
      />
    </div>
  );
}

function Acordeon({ titulo, icon, abierto, onToggle, columnas }) {
  return (
    <div className={styles.acordeon}>
      <button type="button" className={styles.acordeonHead} onClick={onToggle} aria-expanded={abierto}>
        {icon}
        <span style={{ flex: 1, fontSize: 15, fontWeight: 800, color: 'var(--text-primary)', textAlign: 'left' }}>{titulo}</span>
        <ChevronDown size={18} style={{ color: 'var(--text-muted)', transform: abierto ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
      </button>
      {abierto && (
        <div className={styles.acordeonBody}>
          <div className={styles.acordeonSearchLabel}>Buscar por número</div>
          <div className={styles.acordeonSearchWrap}>
            <span className={styles.acordeonSearchIcon}>
              <Search size={15} />
            </span>
            <input placeholder="" className={styles.acordeonSearchInput} aria-label="Buscar por número" />
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className={styles.acordeonTabla}>
              <thead>
                <tr>
                  {columnas.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td colSpan={columnas.length} className={styles.acordeonVacio}>
                    Este comprobante no tiene detalles para mostrar.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className={styles.acordeonFoot}>
            <span>Viendo 0 a 0 de 0 entradas</span>
            <span style={{ display: 'flex', gap: 6 }}>
              <button type="button" className={styles.pagBtn} disabled>
                « Atrás
              </button>
              <button type="button" className={styles.pagBtnActivo}>
                1
              </button>
              <button type="button" className={styles.pagBtn} disabled>
                Siguiente »
              </button>
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
