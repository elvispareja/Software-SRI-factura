import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, FileMinus2, FilePlus2 } from 'lucide-react';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { documentoDesdeApi, TIPOS } from '../../api/documentos';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import TablaCWO from '../../components/ui/TablaCWO';
// Misma tabla y estilos que la lista de comprobantes: se reutilizan para no
// duplicar clases y arriesgar que se separen visualmente.
import estilos from './ComprobantesList.module.css';

// El endpoint no filtra por varios tipos a la vez, así que se traen todos los
// comprobantes y se filtran en cliente a las dos clases de nota.
const TIPOS_NOTA = [TIPOS.NOTA_CREDITO, TIPOS.NOTA_DEBITO];
const CONSULTA = { tamano: 200 };

function iniciales(n) {
  return String(n).trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('').slice(0, 2) || 'NT';
}

// El tono del chip lo fija el estado; cada tono es un token con el mismo
// significado en claro y en oscuro.
function claseEstado(estado) {
  if (estado === 'Autorizado') return estilos.chipExito;
  if (estado === 'Rechazado' || estado === 'Devuelto') return estilos.chipError;
  if (estado === 'Anulado') return estilos.chipNeutro;
  return estilos.chipAviso;
}

export default function NotasList() {
  const [termino, setTermino] = useState('');
  const [fTipo, setFTipo] = useState(VALOR_TODOS);
  const [fEstado, setFEstado] = useState(VALOR_TODOS);
  const [archivado, setArchivado] = useState(false);
  const navigate = useNavigate();

  const recurso = useRecurso('/comprobantes', { parametros: CONSULTA, datosDemo: [] });

  const registros = useMemo(() => {
    const base = recurso.usandoDemo ? recurso.datos : recurso.datos.map(documentoDesdeApi);
    return base.filter((r) => TIPOS_NOTA.includes(r.tipo));
  }, [recurso.datos, recurso.usandoDemo]);

  const filtrados = useMemo(() => registros.filter((r) => {
    const est = r.estadoSRI ?? r.estado ?? '';
    if (fTipo !== VALOR_TODOS && r.tipo !== fTipo) return false;
    if (fEstado !== VALOR_TODOS && est !== fEstado) return false;
    if (archivado && est !== 'Anulado') return false;
    return true;
  }), [registros, fTipo, fEstado, archivado]);

  const tabla = useTablaFiltrada({ datos: filtrados, termino, camposBusqueda: ['numero', 'cliente'], filtros: {} });

  const filtrosTop = [
    { key: 'fTipo', label: 'Tipo', value: fTipo, onChange: setFTipo, opciones: [
      { value: VALOR_TODOS, label: 'Todos los tipos' },
      { value: TIPOS.NOTA_CREDITO, label: 'Nota de Crédito' },
      { value: TIPOS.NOTA_DEBITO, label: 'Nota de Débito' },
    ] },
    { key: 'fEstado', label: 'Seleccionar Estado', value: fEstado, onChange: setFEstado, opciones: [
      { value: VALOR_TODOS, label: 'Seleccionar Estado' },
      { value: 'Autorizado', label: 'Autorizado' },
      { value: 'Pendiente', label: 'Pendiente' },
      { value: 'Rechazado', label: 'Rechazado' },
      { value: 'Anulado', label: 'Anulado' },
    ] },
  ];

  const columnas = [
    { key: 'numero', titulo: 'NÚMERO', cifra: true, render: (r) => <span className={`cifra ${estilos.numero}`}>{r.numero}</span> },
    { key: 'tipo', titulo: 'TIPO', render: (r) => <span className={`${estilos.chip} ${estilos.chipNeutro}`}>{r.tipo === TIPOS.NOTA_CREDITO ? 'Crédito' : 'Débito'}</span> },
    { key: 'modificado', titulo: 'DOC. MODIFICADO', render: (r) => <span className={estilos.celdaTenue}>{r.documentoModificado || '—'}</span> },
    { key: 'fecha', titulo: 'FECHA', cifra: true, render: (r) => <span className={`cifra ${estilos.celdaSuave}`}>{r.fecha}</span> },
    { key: 'receptor', titulo: 'RECEPTOR', render: (r) => <div className={estilos.receptor}><span className={estilos.avatar}>{iniciales(r.cliente)}</span><span className={estilos.receptorNombre}>{r.cliente}</span></div> },
    { key: 'total', titulo: 'TOTAL', align: 'right', cifra: true, render: (r) => <span className={estilos.total}>{formatearMoneda(r.total)}</span> },
    { key: 'estado', titulo: 'ESTADO', align: 'center', render: (r) => { const est = r.estadoSRI ?? r.estado; return <span className={`${estilos.chip} ${claseEstado(est)}`}>{est}</span>; } },
    { key: 'acciones', titulo: 'ACCIONES', align: 'center', render: (r) => <span className={estilos.acciones}><button onClick={() => navigate(`/comprobantes/${r.id}`)} className={estilos.btnVer} title="Ver"><Eye size={16} /></button></span> },
  ];

  return (
    <TablaCWO
      titulo="Notas de Crédito y Débito"
      subtitulo="Comprobantes que modifican una factura ya emitida (devoluciones, descuentos, recargos)."
      accionNuevo={(
        <>
          <Link to="/comprobantes/nota-credito" className={estilos.btnAlterno}><FileMinus2 size={16} /> Nota de Crédito</Link>
          <Link to="/comprobantes/nota-debito" className={estilos.btnNuevo}><FilePlus2 size={17} /> Nota de Débito</Link>
        </>
      )}
      filtrosTop={filtrosTop}
      busqueda={termino}
      onBusqueda={setTermino}
      placeholder="Buscar por Número o receptor"
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
      minWidth={980}
      paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
    />
  );
}
