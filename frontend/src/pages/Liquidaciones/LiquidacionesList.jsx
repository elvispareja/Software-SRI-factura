import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye } from 'lucide-react';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { documentoDesdeApi, TIPOS } from '../../api/documentos';
import { LIQUIDACIONES } from '../../data/documentosCompra';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import TablaCWO from '../../components/ui/TablaCWO';
// Es la misma tabla que la de comprobantes con otras columnas: se reutilizan
// sus celdas en vez de duplicar las clases y arriesgar que se separen.
import estilos from '../Comprobantes/ComprobantesList.module.css';

const CONSULTA = { tipo: TIPOS.LIQUIDACION, tamano: 200 };

function iniciales(n) { return String(n).trim().split(/\s+/).slice(0,2).map((p)=>p[0]?.toUpperCase()??'').join('').slice(0,2)||'LI'; }

// El tono del chip lo fija el estado, y cada tono es un token con el mismo
// significado en claro y en oscuro.
function claseEstado(estado) {
  if (estado === 'Autorizado') return estilos.chipExito;
  if (estado === 'Rechazado' || estado === 'Devuelto') return estilos.chipError;
  if (estado === 'Anulado') return estilos.chipNeutro;
  return estilos.chipAviso;
}

// Tributación real según el estado del SRI (antes era un valor fijo "Aceptado"):
// solo un comprobante autorizado está aceptado; uno rechazado o devuelto,
// "Rechazada"; mientras no se transmite al SRI, "No Entregado".
function tributacion(estado) {
  if (estado === 'Autorizado') return 'Aceptado';
  if (estado === 'Rechazado' || estado === 'Devuelto') return 'Rechazada';
  return 'No Entregado';
}

export default function LiquidacionesList() {
  const [termino, setTermino] = useState('');
  const [fMetodo, setFMetodo] = useState(VALOR_TODOS);
  const [fEstado, setFEstado] = useState(VALOR_TODOS);
  const [fTrib, setFTrib] = useState(VALOR_TODOS);
  const [archivado, setArchivado] = useState(false);
  const navigate = useNavigate();

  const recurso = useRecurso('/comprobantes', { parametros: CONSULTA, datosDemo: LIQUIDACIONES });
  const registros = useMemo(() => (recurso.usandoDemo ? recurso.datos.map((r)=>({ ...r, cliente: r.cliente ?? r.proveedor, estadoSRI: r.estado, total: r.total, numero: r.numero, fecha: r.fecha, metodo: r.metodo })) : recurso.datos.map(documentoDesdeApi).map((r)=>({ ...r, cliente: r.cliente, estadoSRI: r.estadoSRI, total: r.total, numero: r.numero, fecha: r.fecha, metodo: r.metodo }))), [recurso.datos, recurso.usandoDemo]);

  const filtrados = useMemo(() => registros.filter((r)=>{
    const est = r.estadoSRI ?? r.estado ?? '';
    if (fEstado !== VALOR_TODOS && est !== fEstado) return false;
    if (fMetodo !== VALOR_TODOS && r.metodo !== fMetodo) return false;
    if (fTrib !== VALOR_TODOS && tributacion(est) !== fTrib) return false;
    if (archivado && est !== 'Anulado') return false;
    return true;
  }), [registros, fEstado, fMetodo, fTrib, archivado]);

  const tabla = useTablaFiltrada({ datos: filtrados, termino, camposBusqueda: ['numero', 'cliente'], filtros: {} });

  const filtrosTop = [
    { key: 'fMetodo', label: 'Seleccionar método', value: fMetodo, onChange: setFMetodo, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar método' }, { value: 'Contado', label: 'Contado' }, { value: 'Crédito', label: 'Crédito' }] },
    { key: 'fEstado', label: 'Seleccionar Estado', value: fEstado, onChange: setFEstado, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Estado' }, { value: 'Autorizado', label: 'Autorizado' }, { value: 'Pendiente', label: 'Pendiente' }, { value: 'Rechazado', label: 'Rechazado' }, { value: 'Anulado', label: 'Anulado' }] },
    { key: 'fTrib', label: 'Seleccionar Tributación', value: fTrib, onChange: setFTrib, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Tributación' }, { value: 'No Entregado', label: 'No Entregado' }, { value: 'Aceptado', label: 'Aceptadas' }, { value: 'Rechazada', label: 'Rechazadas' }] },
  ];

  const columnas = [
    { key: 'numero', titulo: 'NÚMERO', cifra: true, render: (r) => <span className={`cifra ${estilos.numero}`}>{r.numero}</span> },
    { key: 'afectado', titulo: 'COMPROBANTE AFECTADO', render: () => <span className={estilos.celdaTenue}>-</span> },
    { key: 'fecha', titulo: 'FECHA', cifra: true, render: (r) => <span className={`cifra ${estilos.celdaSuave}`}>{r.fecha}</span> },
    { key: 'receptor', titulo: 'RECEPTOR', render: (r) => <div className={estilos.receptor}><span className={estilos.avatar}>{iniciales(r.cliente)}</span><span className={estilos.receptorNombre}>{r.cliente}</span></div> },
    { key: 'metodo', titulo: 'MÉTODO', render: (r) => <span className={`${estilos.chip} ${estilos.chipNeutro}`}>{r.metodo}</span> },
    { key: 'total', titulo: 'TOTAL', align: 'right', cifra: true, render: (r) => <span className={estilos.total}>{formatearMoneda(r.total)}</span> },
    { key: 'saldo', titulo: 'SALDO', align: 'right', cifra: true, render: () => <span className={`cifra ${estilos.celdaSuave}`}>0.00</span> },
    { key: 'ncnd', titulo: 'NC|ND', align: 'center', render: () => <span className={estilos.celdaSuave}>0 | 0</span> },
    { key: 'estado', titulo: 'ESTADO', align: 'center', render: (r) => { const est = r.estadoSRI ?? r.estado; return <span className={`${estilos.chip} ${claseEstado(est)}`}>{est}</span>; } },
    { key: 'trib', titulo: 'TRIBUTACIÓN', align: 'center', render: (r) => { const t = tributacion(r.estadoSRI ?? r.estado); const cls = t === 'Aceptado' ? estilos.chipExito : t === 'Rechazada' ? estilos.chipError : estilos.chipNeutro; return <span className={`${estilos.chip} ${cls}`}>{t}</span>; } },
    { key: 'correo', titulo: 'CORREO', align: 'center', render: (r) => { const enviado = (r.estadoSRI ?? r.estado) === 'Autorizado'; return <span className={`${estilos.chip} ${enviado ? estilos.chipExito : estilos.chipNeutro}`}>{enviado ? 'enviado' : '—'}</span>; } },
    { key: 'acciones', titulo: 'ACCIONES', align: 'center', render: (r) => <span className={estilos.acciones}><button onClick={() => navigate(`/comprobantes/${r.id}`)} className={estilos.btnVer}><Eye size={16} /></button></span> },
  ];

  return (
    <TablaCWO
      titulo="Liquidaciones de Compra"
      subtitulo="Comprobantes que emites por cuenta de proveedores que no pueden facturar."
      accionNuevo={<Link to="/liquidaciones/nueva" className={estilos.btnNuevo}>Nueva Liquidación</Link>}
      filtrosTop={filtrosTop}
      busqueda={termino}
      onBusqueda={setTermino}
      placeholder="Buscar por Número"
      pageSize={tabla.tamanoPagina}
      onPageSize={tabla.setTamanoPagina}
      archivado={archivado}
      onToggleArchivado={() => setArchivado((v) => !v)}
      cargando={recurso.cargando}
      error={recurso.error}
      usandoDemo={recurso.usandoDemo}
      onReintentar={recurso.recargar}
      columnas={columnas}
      filas={tabla.visibles.map((r) => ({ ...r, key: r.id }))}
      minWidth={1040}
      paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
    />
  );
}
