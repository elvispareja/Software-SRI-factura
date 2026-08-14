import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye } from 'lucide-react';
import { RETENCIONES, ESTADOS_SRI } from '../../data/documentosCompra';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { retencionDesdeApi } from '../../api/retenciones';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import TablaCWO from '../../components/ui/TablaCWO';
// Es la misma tabla que la de comprobantes con otras columnas: se reutilizan
// sus celdas en vez de duplicar las clases y arriesgar que se separen.
import estilos from '../Comprobantes/ComprobantesList.module.css';

const CONSULTA = { tamano: 200 };

function iniciales(n) { return String(n).trim().split(/\s+/).slice(0,2).map((p)=>p[0]?.toUpperCase()??'').join('').slice(0,2)||'RE'; }

// El tono del chip lo fija el estado, y cada tono es un token con el mismo
// significado en claro y en oscuro.
function claseEstado(estado) {
  if (estado === 'Autorizado') return estilos.chipExito;
  if (estado === 'Rechazado') return estilos.chipError;
  return estilos.chipAviso;
}

export default function RetencionesList() {
  const [termino, setTermino] = useState('');
  const [fEstado, setFEstado] = useState(VALOR_TODOS);
  const [fTrib, setFTrib] = useState(VALOR_TODOS);
  const [archivado, setArchivado] = useState(false);

  const recurso = useRecurso('/retenciones', { parametros: CONSULTA, datosDemo: RETENCIONES });
  const registros = useMemo(() => (recurso.usandoDemo ? recurso.datos.map((r)=>({ ...r, estado: r.estado, total: r.total, numero: r.numero, fecha: r.fecha, proveedor: r.proveedor, ivaRet: r.total })) : recurso.datos.map(retencionDesdeApi).map((r)=>({ ...r, estado: r.estado, total: r.total, numero: r.numero, fecha: r.fecha, proveedor: r.proveedor, ivaRet: r.total }))), [recurso.datos, recurso.usandoDemo]);

  const filtrados = useMemo(() => registros.filter((r)=>{
    if (fEstado !== VALOR_TODOS && r.estado !== fEstado) return false;
    if (fTrib !== VALOR_TODOS) {
      const trib = r.estado === 'Autorizado' ? 'Aceptado' : r.estado === 'Rechazado' ? 'Rechazada' : 'No Entregado';
      if (trib !== fTrib) return false;
    }
    if (archivado && r.estado !== 'Anulado') return false;
    return true;
  }), [registros, fEstado, fTrib, archivado]);

  const tabla = useTablaFiltrada({ datos: filtrados, termino, camposBusqueda: ['numero', 'proveedor', 'identificacion', 'sustento'], filtros: {} });

  const totalRetenido = useMemo(() => tabla.filtrados.reduce((s, r) => s + (Number(r.total) || 0), 0), [tabla.filtrados]);

  const filtrosTop = [
    { key: 'fEstado', label: 'Seleccionar Estado', value: fEstado, onChange: setFEstado, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Estado' }, ...ESTADOS_SRI.map((e)=>({ value: e, label: e }))] },
    { key: 'fTrib', label: 'Seleccionar Tributación', value: fTrib, onChange: setFTrib, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Tributación' }, { value: 'No Entregado', label: 'No Entregado' }, { value: 'Aceptado', label: 'Aceptadas' }, { value: 'Rechazada', label: 'Rechazadas' }] },
  ];

  const columnas = [
    { key: 'numero', titulo: 'NÚMERO', cifra: true, render: (r) => <span className={estilos.numero}>{r.numero}</span> },
    { key: 'fecha', titulo: 'FECHA', cifra: true, render: (r) => <span className={`cifra ${estilos.celdaSuave}`}>{r.fecha}</span> },
    { key: 'receptor', titulo: 'RECEPTOR', render: (r) => <div className={estilos.receptor}><span className={estilos.avatar}>{iniciales(r.proveedor)}</span><span className={estilos.receptorNombre}>{r.proveedor}</span></div> },
    { key: 'total', titulo: 'TOTAL', align: 'right', cifra: true, render: (r) => <span className={estilos.total}>{formatearMoneda(r.total)}</span> },
    { key: 'ivaRet', titulo: 'TOTAL IVA RETENIDO', align: 'right', cifra: true, render: (r) => <span className={`cifra ${estilos.celdaSuave}`}>{formatearMoneda(r.ivaRet ?? r.total)}</span> },
    { key: 'ncnd', titulo: 'NC|ND', align: 'center', render: () => <span className={estilos.celdaSuave}>0 | 0</span> },
    { key: 'estado', titulo: 'ESTADO', align: 'center', render: (r) => <span className={`${estilos.chip} ${claseEstado(r.estado)}`}>{r.estado}</span> },
    { key: 'trib', titulo: 'TRIBUTACIÓN', align: 'center', render: (_r) => <span className={`${estilos.chip} ${estilos.chipExito}`}>Aceptado</span> },
    { key: 'correo', titulo: 'CORREO', align: 'center', render: () => <span className={`${estilos.chip} ${estilos.chipExito}`}>enviado</span> },
    { key: 'acciones', titulo: 'ACCIONES', align: 'center', render: () => <span className={estilos.acciones}><button type="button" className={estilos.btnVer} disabled title="Detalle de retención no disponible"><Eye size={16} /></button></span> },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <TablaCWO
        titulo="Retenciones"
        subtitulo="Comprobantes de retención emitidos a los proveedores."
        accionNuevo={<Link to="/retenciones/nueva" className={estilos.btnNuevo}>Nueva Retención</Link>}
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
        minWidth={1000}
        paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
      />
      <div className={estilos.pieTotal}>Total retenido ({tabla.total} comprobantes): <strong className="cifra">{formatearMoneda(totalRetenido)}</strong></div>
    </div>
  );
}
