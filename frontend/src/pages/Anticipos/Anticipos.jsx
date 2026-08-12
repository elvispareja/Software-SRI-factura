import { useMemo, useState } from 'react';
import { Search, Plus, X, CalendarDays, Wallet, Trash2, AlertCircle } from 'lucide-react';
import { PAY_OPTS } from '../../data/anticipos';
import {
  ESTADOS_ANTICIPO,
  anticipoDesdeApi,
  anularAnticipo,
  aplicarAnticipo,
  crearAnticipo,
} from '../../api/egresos';
import { useRecurso } from '../../hooks/useRecurso';
import { useCatalogos } from '../../hooks/useCatalogos';
import { useTablaFiltrada } from '../../hooks/useTablaFiltrada';
import { AvisoDemo, ErrorCarga } from '../../components/ui/EstadoCarga';
import styles from './Anticipos.module.css';

/**
 * Estado del anticipo → clase del chip.
 *
 * El estado se lee por el color, así que el color tiene que significar algo y
 * seguir significándolo en los dos temas. Cada uno se apoya en la pareja
 * fondo/texto que el sistema ya define para ese significado: aviso lo que
 * espera, éxito lo que se consumió, información lo que quedó a medias. El gris
 * de "anulado" es deliberado: un anticipo cancelado no reclama la vista.
 */
const CLASE_ESTADO = {
  Pendiente: 'chipPendiente',
  Aplicado: 'chipAplicado',
  Anulado: 'chipAnulado',
  'Residuo pendiente': 'chipResiduo',
  Devuelto: 'chipDevuelto',
  'Facturado (residuo pendiente)': 'chipResiduo',
  'Facturado (residuo devuelto)': 'chipDevuelto',
  Facturado: 'chipAplicado',
};

// 'Todos' encabeza los desplegables; el resto son los estados del backend.
const OPCIONES_ESTADO = ['Todos', ...ESTADOS_ANTICIPO];
const OPCIONES_TIPO = ['Todos', 'ARD', 'APP'];

export default function Anticipos() {
  const recurso = useRecurso('/anticipos', { parametros: { tamano: 200 }, datosDemo: [] });
  const catalogos = useCatalogos();

  const anticipos = useMemo(
    () => recurso.datos.map(anticipoDesdeApi),
    [recurso.datos],
  );

  const [errorAccion, setErrorAccion] = useState(null);
  const [estado, setEstado] = useState('Todos');
  const [tipo, setTipo] = useState('Todos');
  const [desde, setDesde] = useState('');
  const [hasta, setHasta] = useState('');
  const [query, setQuery] = useState('');

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [modalKind, setModalKind] = useState('recibido'); // 'recibido' = ARD, 'pagado' = APP
  const [modalFecha, setModalFecha] = useState(() => new Date().toISOString().slice(0, 10));
  const [modalRecep, setModalRecep] = useState('');
  const [modalObs, setModalObs] = useState('');
  const [modalPagos, setModalPagos] = useState([]);
  const [modalPayOpen, setModalPayOpen] = useState(false);
  const [modalRecepOpen, setModalRecepOpen] = useState(false);

  // Los receptores salen del catálogo real: un anticipo tiene que apuntar a
  // alguien que exista, porque el id viaja al servidor.
  const receptoresDisponibles = useMemo(
    () => catalogos.receptores.filter((r) => r.estado === 'Activo'),
    [catalogos.receptores],
  );

  const filtrados = useMemo(() => {
    let rows = anticipos;
    if (estado !== 'Todos') rows = rows.filter((r) => r.estado === estado);
    if (tipo !== 'Todos') rows = rows.filter((r) => r.tipo === tipo);
    if (desde) rows = rows.filter((r) => r.fecha >= desde);
    if (hasta) rows = rows.filter((r) => r.fecha <= hasta);
    const q = query.trim().toLowerCase();
    if (q) rows = rows.filter((r) => (r.receptor + ' ' + r.detalle).toLowerCase().includes(q));
    return rows;
  }, [anticipos, estado, tipo, desde, hasta, query]);

  const tabla = useTablaFiltrada({ datos: filtrados, termino: '', camposBusqueda: [] });

  const totalMonto = useMemo(() => modalPagos.reduce((a, p) => a + (parseFloat(p.monto) || 0), 0), [modalPagos]);

  const abrirModal = () => {
    setModalKind('recibido');
    setModalFecha(new Date().toISOString().slice(0, 10));
    setModalRecep('');
    setModalObs('');
    setModalPagos([]);
    setModalOpen(true);
  };

  const guardarAnticipo = async () => {
    const receptor = receptoresDisponibles.find((r) => r.razonSocial === modalRecep);
    if (!receptor) {
      setErrorAccion('Selecciona un receptor del catálogo.');
      return;
    }
    if (totalMonto <= 0) {
      setErrorAccion('Agrega al menos una forma de pago con monto.');
      return;
    }

    setErrorAccion(null);
    try {
      await crearAnticipo(
        {
          fecha: modalFecha,
          tipo: modalKind === 'recibido' ? 'ARD' : 'APP',
          detalle: modalObs || '',
          monto: totalMonto,
          formaPago: modalPagos[0]?.tipo ?? 'Transferencia',
        },
        receptor.id,
      );
      setModalOpen(false);
      recurso.recargar();
    } catch (fallo) {
      setErrorAccion(fallo.message);
    }
  };

  const accionAnticipo = async (id, accion) => {
    setErrorAccion(null);
    try {
      if (accion === 'anular') {
        await anularAnticipo(id);
      } else if (accion === 'aplicar') {
        const anticipo = anticipos.find((a) => a.id === id);
        // Se aplica el saldo entero: imputar una parte exige indicar contra qué
        // factura, y eso vive en el formulario de la factura, no aquí.
        await aplicarAnticipo(id, anticipo.saldo);
      }
      recurso.recargar();
    } catch (fallo) {
      setErrorAccion(fallo.message);
    }
  };

  const isRecibido = modalKind === 'recibido';

  return (
    <div className={styles.page}>
      {recurso.usandoDemo && <AvisoDemo />}

      {(errorAccion || recurso.error) && (
        <ErrorCarga
          mensaje={errorAccion || recurso.error}
          onReintentar={() => {
            setErrorAccion(null);
            recurso.recargar();
          }}
        />
      )}

      <div className={styles.bannerDev}>
        <AlertCircle size={18} />
        <div>
          El <strong>saldo</strong> lo calcula el servidor como monto menos
          facturado. Un anticipo ya aplicado no se puede anular: para revertirlo
          se emite una nota de crédito.
        </div>
      </div>

      <div className={styles.card}>
        <div className={styles.filtrosGrid}>
          <label className={styles.fieldSelect}>
            <span className={styles.fieldLabel}>Estado</span>
            <select className={styles.select} value={estado} onChange={(e) => setEstado(e.target.value)}>
              {OPCIONES_ESTADO.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
          <label className={styles.fieldSelect}>
            <span className={styles.fieldLabel}>Tipo</span>
            <select className={styles.select} value={tipo} onChange={(e) => setTipo(e.target.value)}>
              {OPCIONES_TIPO.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
          <label className={styles.fieldDate}>
            <span className={styles.fieldLabel}>Desde</span>
            <input type="date" className={styles.input} value={desde} onChange={(e) => setDesde(e.target.value)} />
          </label>
          <label className={styles.fieldDate}>
            <span className={styles.fieldLabel}>Hasta</span>
            <input type="date" className={styles.input} value={hasta} onChange={(e) => setHasta(e.target.value)} />
          </label>
          <div className={styles.searchWrap}>
            <Search size={15} className={styles.searchIcon} />
            <input className={styles.searchInput} placeholder="Buscar..." value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
        </div>
        <div className={styles.toolbar2}>
          <span className={styles.toolbarLabel}>Mostrar</span>
          <select className={styles.selectSm} value={tabla.tamanoPagina} onChange={(e) => tabla.setTamanoPagina(Number(e.target.value))}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select>
          <span className={styles.toolbarLabel} style={{ flex: 1 }}>registros</span>
          <button className={styles.btnPrimario} onClick={abrirModal}><Plus size={16} /> Crear Anticipo</button>
        </div>
      </div>

      <div className={styles.infoBox}>
        <div className={styles.infoIcon}><AlertCircle size={17} /></div>
        <div className={styles.infoText}>
          <div><strong>ARD</strong> = Anticipo Recibido de Dinero (de cliente) · <strong>APP</strong> = Anticipo Pagado a Proveedor</div>
          <div style={{ fontWeight: 700, marginTop: 2 }}>Acciones disponibles según el estado del anticipo:</div>
          <ul className={styles.infoList}>
            <li><strong>Anular</strong> — cancela un anticipo <em>Pendiente</em> que nunca se aplicó.</li>
            <li><strong>Devolver</strong> — aparece cuando el anticipo fue aplicado <em>parcialmente</em> (estado &ldquo;residuo pendiente&rdquo;). Genera asiento por el saldo sobrante.</li>
            <li><strong>Corregir</strong> — modifica monto o cuentas de un anticipo <em>Pendiente</em> ya contabilizado.</li>
          </ul>
        </div>
      </div>

      <div className={styles.cardTable}>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead><tr><th>#</th><th>FECHA</th><th>TIPO</th><th>RECEPTOR</th><th>DETALLE</th><th style={{ textAlign: 'right' }}>MONTO</th><th style={{ textAlign: 'right' }}>MONTO FACTURADO</th><th style={{ textAlign: 'right' }}>SALDO</th><th>ESTADO</th><th>ASIENTO</th><th style={{ textAlign: 'center' }}>ACCIONES</th></tr></thead>
            <tbody>
              {tabla.visibles.length === 0 ? (
                <tr><td colSpan={11} className={styles.emptyCell}>No hay anticipos con estos filtros.</td></tr>
              ) : tabla.visibles.map((r, i) => {
                const saldo = r.monto - (r.facturado || 0);
                const claseEstado = styles[CLASE_ESTADO[r.estado] ?? CLASE_ESTADO.Pendiente];
                return (
                  <tr key={r.id}>
                    <td className={styles.cellMuted}>{tabla.desde + i}</td>
                    <td className="cifra">{r.fecha}</td>
                    <td><span className={`${styles.chipTipo} ${r.tipo === 'ARD' ? styles.chipARD : styles.chipAPP}`}>{r.tipo}</span></td>
                    <td className={styles.cellStrong}>{r.receptor}</td>
                    <td>{r.detalle}</td>
                    <td className="cifra" style={{ textAlign: 'right', fontWeight: 700 }}>{r.monto.toFixed(2)}</td>
                    <td className="cifra" style={{ textAlign: 'right' }}>{(r.facturado || 0).toFixed(2)}</td>
                    <td className="cifra" style={{ textAlign: 'right', fontWeight: 700 }}>{saldo.toFixed(2)}</td>
                    <td><span className={`${styles.chipEstado} ${claseEstado}`}>{r.estado}</span></td>
                    <td className={styles.cellAsiento}>{r.asiento}</td>
                    <td style={{ textAlign: 'center' }}>
                      <div className={styles.accionesCell}>
                        <button className={styles.btnAccion} title="Anular" onClick={() => accionAnticipo(r.id, 'anular')}>⊘</button>
                        <button className={styles.btnAccion} title="Devolver" onClick={() => accionAnticipo(r.id, 'devolver')}>↩</button>
                        <button className={styles.btnAccion} title="Corregir" onClick={() => accionAnticipo(r.id, 'corregir')}>✎</button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className={styles.paginacion}>
          <span className={styles.pagInfo}>Viendo {tabla.desde} a {tabla.hasta} de {tabla.total} entradas</span>
          <div className={styles.pagBtns}>
            <button className={styles.pagBtn} disabled={tabla.pagina <= 1} onClick={() => tabla.setPagina(tabla.pagina - 1)}>Atrás</button>
            <span className={styles.pagNum}>{tabla.pagina}</span>
            <button className={styles.pagBtn} disabled={tabla.pagina >= tabla.totalPaginas} onClick={() => tabla.setPagina(tabla.pagina + 1)}>Siguiente</button>
          </div>
        </div>
      </div>

      {modalOpen && (
        <div className={styles.overlay} onClick={() => setModalOpen(false)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <button className={styles.modalClose} onClick={() => setModalOpen(false)}><X size={17} /></button>
            <div className={`${styles.modalHead} ${isRecibido ? styles.modalHeadRec : styles.modalHeadPag}`}>
              <span className={`${styles.modalIcon} ${isRecibido ? styles.modalIconRec : styles.modalIconPag}`}><Wallet size={22} /></span>
              <div><div className={styles.modalTitle}>Nuevo Anticipo</div><div className={styles.modalSub}>{isRecibido ? 'Dinero recibido de un cliente antes de emitir la factura' : 'Pago anticipado a un proveedor sin factura emitida'}</div></div>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.kindGrid}>
                <button className={`${styles.kindCard} ${isRecibido ? styles.kindActivoRec : ''}`} onClick={() => setModalKind('recibido')}>
                  <span>↓</span><div><div className={styles.kindLabel}>Recibido de cliente</div><div className={styles.kindSub}>Cuenta Pasivo</div></div>{isRecibido && <span className={styles.kindCheck}>✓</span>}
                </button>
                <button className={`${styles.kindCard} ${!isRecibido ? styles.kindActivoPag : ''}`} onClick={() => setModalKind('pagado')}>
                  <span>↑</span><div><div className={styles.kindLabel}>Pagado a proveedor</div><div className={styles.kindSub}>Cuenta Activo</div></div>{!isRecibido && <span className={styles.kindCheck}>✓</span>}
                </button>
              </div>

              <div className={styles.modalGrid2}>
                <label className={styles.field}><span>Fecha</span><input type="date" className={styles.input} value={modalFecha} onChange={(e) => setModalFecha(e.target.value)} /></label>
                <div className={styles.field}>
                  <span>{isRecibido ? 'Cliente' : 'Proveedor'}</span>
                  <div className={styles.selectBox} onClick={() => setModalRecepOpen((v) => !v)}>
                    <span className={`${styles.selectValue} ${modalRecep ? '' : styles.selectValueVacio}`}>{modalRecep || (isRecibido ? 'Cliente' : 'Proveedor')}</span>
                    <span className={styles.chevron}>▾</span>
                  </div>
                  {modalRecepOpen && (
                    <div className={styles.dropdown}>
                      {receptoresDisponibles.map((r) => r.razonSocial).map((n) => (
                        <button key={n} className={styles.dropdownItem} onClick={() => { setModalRecep(n); setModalRecepOpen(false); }}>{n}</button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <label className={styles.field}><span>Observación</span><textarea className={styles.textarea} rows={2} value={modalObs} onChange={(e) => setModalObs(e.target.value)} /></label>

              <div className={styles.pagosHead}><Wallet size={16} /><span>FORMAS DE PAGO</span></div>
              <div className={styles.payAddBox} onClick={() => setModalPayOpen((v) => !v)}>
                <span>+ Agregar forma de pago</span><span>▾</span>
              </div>
              {modalPayOpen && (
                <div className={styles.dropdown}>
                  {PAY_OPTS.map((o) => (
                    <button key={o} className={styles.dropdownItem} onClick={() => { setModalPagos((prev) => [...prev, { key: Date.now() + Math.random(), label: o, monto: '' }]); setModalPayOpen(false); }}>{o}</button>
                  ))}
                </div>
              )}
              {modalPagos.map((p) => (
                <div key={p.key} className={styles.pagoRow}>
                  <span className={styles.pagoLabel}>{p.label}</span>
                  <input className={styles.inputSm} placeholder="0.00" value={p.monto} onChange={(e) => { const v = e.target.value; setModalPagos((prev) => prev.map((x) => x.key === p.key ? { ...x, monto: v } : x)); }} />
                  <button className={styles.btnTrash} onClick={() => setModalPagos((prev) => prev.filter((x) => x.key !== p.key))}><Trash2 size={15} /></button>
                </div>
              ))}

              <div className={`${styles.montoBox} ${isRecibido ? styles.montoBoxRec : styles.montoBoxPag}`}>
                <div><div className={styles.montoLabel}>MONTO ANTICIPADO</div><div className={`${styles.montoVal} cifra`}>$ {totalMonto.toFixed(2)}</div></div>
                <CalendarDays size={26} />
              </div>

              <div className={styles.modalActions}>
                <button className={styles.btnSecundario} onClick={() => setModalOpen(false)}>Cancelar</button>
                <button className={styles.btnPrimario} onClick={guardarAnticipo}><Wallet size={16} /> Guardar</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
