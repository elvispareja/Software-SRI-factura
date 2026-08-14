import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Eye, FileText } from 'lucide-react';
import { COMPROBANTES } from '../../data/comprobantes';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { comprobanteDesdeApi } from '../../api/adaptadores';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import TablaCWO from '../../components/ui/TablaCWO';
import estilos from './ComprobantesList.module.css';

const TAMANO_CONSULTA = { tamano: 200 };

function iniciales(nombre) {
  return String(nombre).trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('').slice(0, 2) || 'CL';
}

/**
 * El estado del comprobante decide el tono del chip, no un color: la clase
 * resuelve el verde/ámbar/rojo con los tokens de estado, que existen en los dos
 * temas. Así el significado se conserva sin congelar la paleta clara.
 */
function claseEstado(estado) {
  if (estado === 'Autorizado') return estilos.chipExito;
  if (estado === 'Pendiente' || estado === 'Borrador') return estilos.chipAviso;
  if (estado === 'Rechazado' || estado === 'Devuelto') return estilos.chipError;
  return estilos.chipNeutro;
}

function chipTributacion(estado) {
  if (estado === 'Autorizado') return { clase: estilos.chipExito, label: 'Aceptado' };
  if (estado === 'Rechazado' || estado === 'Devuelto') return { clase: estilos.chipError, label: 'Rechazada' };
  return { clase: estilos.chipAviso, label: 'No Entregado' };
}

export default function ComprobantesList() {
  const navigate = useNavigate();
  const [termino, setTermino] = useState('');
  const [fMetodo, setFMetodo] = useState(VALOR_TODOS);
  const [fEstado, setFEstado] = useState(VALOR_TODOS);
  const [fTrib, setFTrib] = useState(VALOR_TODOS);
  const [archivado, setArchivado] = useState(false);

  const recurso = useRecurso('/comprobantes', { parametros: TAMANO_CONSULTA, datosDemo: COMPROBANTES });
  const registros = useMemo(() => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(comprobanteDesdeApi)), [recurso.datos, recurso.usandoDemo]);

  // Mapea filtros trib/estado a estado_sri
  const filtradosPorSelect = useMemo(() => {
    return registros.filter((r) => {
      const est = r.estadoSRI ?? r.estado ?? '';
      if (fEstado !== VALOR_TODOS && est !== fEstado) return false;
      if (fTrib !== VALOR_TODOS) {
        const trib = chipTributacion(est).label;
        if (trib !== fTrib) return false;
      }
      if (fMetodo !== VALOR_TODOS && r.metodo !== fMetodo) return false;
      if (archivado && est !== 'Anulado') return false;
      return true;
    });
  }, [registros, fEstado, fTrib, fMetodo, archivado]);

  const tabla = useTablaFiltrada({
    datos: filtradosPorSelect,
    termino,
    camposBusqueda: ['numero', 'cliente'],
    filtros: {},
  });

  const filtrosTop = [
    { key: 'fMetodo', label: 'Seleccionar método', value: fMetodo, onChange: setFMetodo, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar método' }, { value: 'Contado', label: 'Contado' }, { value: 'Crédito', label: 'Crédito' }] },
    { key: 'fEstado', label: 'Seleccionar Estado', value: fEstado, onChange: setFEstado, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Estado' }, { value: 'Autorizado', label: 'Autorizado' }, { value: 'Pendiente', label: 'Pendiente' }, { value: 'Rechazado', label: 'Rechazado' }, { value: 'Anulado', label: 'Anulado' }] },
    { key: 'fTrib', label: 'Seleccionar Tributación', value: fTrib, onChange: setFTrib, opciones: [{ value: VALOR_TODOS, label: 'Seleccionar Tributación' }, { value: 'No Entregado', label: 'No Entregado' }, { value: 'Aceptado', label: 'Aceptadas' }, { value: 'Rechazada', label: 'Rechazadas' }, { value: 'Desconocido', label: 'Desconocido' }] },
  ];

  const columnas = [
    { key: 'numero', titulo: 'NÚMERO', render: (r) => <span className={`cifra ${estilos.numero}`}>{r.numero}</span>, cifra: true },
    { key: 'fecha', titulo: 'FECHA', cifra: true, render: (r) => <span className={`cifra ${estilos.celdaSuave}`}>{r.fecha}</span> },
    {
      key: 'receptor',
      titulo: 'RECEPTOR',
      render: (r) => (
        <div className={estilos.receptor}>
          <span className={estilos.avatar}>{iniciales(r.cliente)}</span>
          <div className={estilos.receptorDatos}>
            <div className={estilos.receptorNombre}>{r.cliente}</div>
            <div className={estilos.receptorIdentificacion}>{r.identificacion ?? ''}</div>
          </div>
        </div>
      ),
    },
    { key: 'metodo', titulo: 'MÉTODO', render: (r) => <span className={`${estilos.chip} ${estilos.chipNeutro}`}>{r.metodo ?? 'Contado'}</span> },
    { key: 'total', titulo: 'TOTAL', align: 'right', cifra: true, render: (r) => <span className={estilos.total}>{formatearMoneda(r.total)}</span> },
    { key: 'saldo', titulo: 'SALDO', align: 'right', cifra: true, render: () => <span className={`cifra ${estilos.celdaSuave}`}>0.00</span> },
    { key: 'ncnd', titulo: 'NC|ND', align: 'center', cifra: true, render: () => <span className={estilos.celdaSuave}>0 | 0</span> },
    {
      key: 'estado',
      titulo: 'ESTADO',
      align: 'center',
      render: (r) => {
        const estado = r.estadoSRI ?? r.estado;
        return <span className={`${estilos.chip} ${claseEstado(estado)}`}>{estado}</span>;
      },
    },
    {
      key: 'tributacion',
      titulo: 'TRIBUTACIÓN',
      align: 'center',
      render: (r) => {
        const c = chipTributacion(r.estadoSRI ?? r.estado);
        return <span className={`${estilos.chip} ${c.clase}`}>{c.label}</span>;
      },
    },
    {
      key: 'correo',
      titulo: 'CORREO',
      align: 'center',
      render: () => <span className={`${estilos.chip} ${estilos.chipExito}`}>enviado</span>,
    },
    {
      key: 'acciones',
      titulo: 'ACCIONES',
      align: 'center',
      render: (r) => (
        <span className={estilos.acciones}>
          <button onClick={() => navigate(`/comprobantes/${r.id}`)} className={estilos.btnVer} title="Ver"><Eye size={16} /></button>
        </span>
      ),
    },
  ];

  return (
    <TablaCWO
      titulo="Comprobantes Electrónicos"
      subtitulo="Listado de facturas, notas de crédito y retenciones."
      accionNuevo={<><Link to="/comprobantes/nota-credito" className={estilos.btnAlterno}><FileText size={16} /> Nota de Crédito</Link><Link to="/comprobantes/nuevo" className={estilos.btnNuevo}><Plus size={17} /> Nueva Factura</Link></>}
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
      minWidth={1080}
      paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
    />
  );
}
