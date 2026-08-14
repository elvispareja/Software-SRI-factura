import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Eye, MoreVertical, SlidersHorizontal } from 'lucide-react';
import { CATALOGO_ARTICULOS, TIPOS_ARTICULO, ESTADOS_ARTICULO } from '../../data/catalogoArticulos';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { articuloDesdeApi } from '../../api/adaptadores';
import { api } from '../../api/cliente';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import TablaCWO from '../../components/ui/TablaCWO';
import styles from './Articulos.module.css';

const FILTROS_INICIALES = { tipo: VALOR_TODOS, categoria: VALOR_TODOS, estado: VALOR_TODOS };
const TAMANO_CONSULTA = { tamano: 200 };

// El tinte del avatar no codifica ningún dato del artículo: solo da variedad
// visual estable. Por eso se reparte con un hash del nombre y son clases de
// tema, no colores con significado.
const TINTES_AVATAR = [
  'avatarNeutro',
  'avatarAcento',
  'avatarInfo',
  'avatarExito',
  'avatarAviso',
];

function iniciales(nombre) {
  const parts = String(nombre).trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? '').join('').slice(0, 2) || 'AR';
}

function claseAvatar(nombre) {
  const hash = [...String(nombre)].reduce((a, c) => a + c.charCodeAt(0), 0);
  return styles[TINTES_AVATAR[hash % TINTES_AVATAR.length]];
}

export default function ArticulosList() {
  const [termino, setTermino] = useState('');
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [colsVisibles, setColsVisibles] = useState({
    codigo: true,
    tipo: true,
    gravamen: true,
    estado: true,
    caja: true,
    unidad: true,
    precioCompra: true,
    precio1: true,
    costoTotal: true,
  });
  const [colsOpen, setColsOpen] = useState(false);
  const [menuOpenId, setMenuOpenId] = useState(null);

  const recurso = useRecurso('/articulos', { parametros: TAMANO_CONSULTA, datosDemo: CATALOGO_ARTICULOS });
  const navigate = useNavigate();
  const registros = useMemo(() => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(articuloDesdeApi)), [recurso.datos, recurso.usandoDemo]);

  const categorias = useMemo(() => [...new Set(registros.map((r) => r.categoria).filter(Boolean))].sort(), [registros]);

  const tabla = useTablaFiltrada({ datos: registros, termino, camposBusqueda: ['codigo', 'nombre', 'categoria'], filtros });

  const cambiarFiltro = (campo, valor) => setFiltros((a) => ({ ...a, [campo]: valor }));

  const desactivar = async (id) => {
    if (recurso.usandoDemo) return;
    try {
      await api.eliminar(`/articulos/${id}`);
      setMenuOpenId(null);
      recurso.recargar();
    } catch {
      // error visible vía recurso.error
    }
  };

  const COL_OPTS = [
    { key: 'codigo', label: 'CÓDIGO' },
    { key: 'tipo', label: 'TIPO' },
    { key: 'gravamen', label: 'GRAVAMEN' },
    { key: 'estado', label: 'ESTADO' },
    { key: 'caja', label: 'CAJA CHICA' },
    { key: 'unidad', label: 'UNIDAD' },
    { key: 'precioCompra', label: 'PRECIO DE COMPRA' },
    { key: 'precio1', label: 'PRECIO 1 SIN IMPUESTO' },
    { key: 'costoTotal', label: 'COSTO TOTAL' },
  ];

  const columnas = [
    {
      key: 'nombre',
      titulo: 'NOMBRE',
      render: (r) => (
        <div className={styles.celdaNombre}>
          <div className={`${styles.avatar} ${claseAvatar(r.nombre)}`}>{iniciales(r.nombre)}</div>
          <span className={styles.nombreArticulo}>{r.nombre}</span>
        </div>
      ),
    },
    { key: 'codigo', titulo: 'CÓDIGO', cifra: true, hidden: !colsVisibles.codigo, render: (r) => <span className={styles.codigoCelda}>{r.codigo}</span> },
    {
      key: 'tipo',
      titulo: 'TIPO',
      hidden: !colsVisibles.tipo,
      render: (r) => (
        <span className={`${styles.chip} ${r.tipo === 'Producto' ? styles.chipNeutro : styles.chipAcento}`}>{r.tipo}</span>
      ),
    },
    {
      key: 'gravamen',
      titulo: 'GRAVAMEN',
      hidden: !colsVisibles.gravamen,
      render: (r) => {
        const grav = r.codigoIva === '0' || r.codigoIva === '6' ? 'Exento' : 'Gravado';
        return <span className={`${styles.chip} ${styles.chipAcento} ${styles.chipGravamen}`}>{grav}</span>;
      },
    },
    {
      key: 'estado',
      titulo: 'ESTADO',
      hidden: !colsVisibles.estado,
      render: (r) => (
        <span className={`${styles.pildora} ${r.estado === 'Activo' ? styles.pildoraExito : styles.pildoraError}`}>{r.estado}</span>
      ),
    },
    { key: 'caja', titulo: 'CAJA CHICA', hidden: !colsVisibles.caja, render: () => <span className={`${styles.chip} ${styles.chipNeutro}`}>-</span> },
    { key: 'unidad', titulo: 'UNIDAD', hidden: !colsVisibles.unidad, render: (r) => r.unidad },
    { key: 'precioCompra', titulo: 'PRECIO DE COMPRA', cifra: true, hidden: !colsVisibles.precioCompra, render: (r) => formatearMoneda(r.costo) },
    { key: 'precio1', titulo: 'PRECIO 1 SIN IMPUESTO', cifra: true, hidden: !colsVisibles.precio1, render: (r) => formatearMoneda(r.precio) },
    { key: 'costoTotal', titulo: 'COSTO TOTAL', cifra: true, hidden: !colsVisibles.costoTotal, render: (r) => formatearMoneda(r.costo) },
    {
      key: 'acciones',
      titulo: 'ACCIONES',
      align: 'right',
      render: (r) => (
        <span className={styles.celdaAcciones}>
          <button type="button" onClick={() => navigate(`/articulos/${r.id}/editar`)} className={styles.btnIconoTabla} aria-label={`Ver ${r.nombre}`}><Eye size={16} /></button>
          <span className={styles.envoltorioMenu}>
            <button
              type="button"
              onClick={() => setMenuOpenId((v) => (v === r.id ? null : r.id))}
              className={styles.btnIconoTabla}
              aria-label="Más"
              aria-expanded={menuOpenId === r.id}
            >
              <MoreVertical size={16} />
            </button>
            {menuOpenId === r.id && (
              <>
                <span onClick={() => setMenuOpenId(null)} className={styles.capaCierre} aria-hidden="true" />
                <span className={styles.menuAcciones}>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpenId(null);
                      navigate(`/articulos/${r.id}/editar`);
                    }}
                    className={styles.menuOpcion}
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    onClick={() => desactivar(r.id)}
                    className={`${styles.menuOpcion} ${styles.menuOpcionPeligro}`}
                    disabled={Boolean(recurso.usandoDemo)}
                    title={recurso.usandoDemo ? 'No disponible en modo demo' : 'Desactivar (soft delete)'}
                  >
                    Desactivar
                  </button>
                </span>
              </>
            )}
          </span>
        </span>
      ),
    },
  ];

  const filtrosTop = [
    { key: 'tipo', label: 'Tipo', value: filtros.tipo, onChange: (v) => cambiarFiltro('tipo', v), opciones: [{ value: VALOR_TODOS, label: 'Producto y servicio' }, ...TIPOS_ARTICULO.map((t) => ({ value: t, label: t }))] },
    { key: 'categoria', label: 'Categoría', value: filtros.categoria, onChange: (v) => cambiarFiltro('categoria', v), opciones: [{ value: VALOR_TODOS, label: 'Toda categoría' }, ...categorias.map((c) => ({ value: c, label: c }))] },
    { key: 'estado', label: 'Estado', value: filtros.estado, onChange: (v) => cambiarFiltro('estado', v), opciones: [{ value: VALOR_TODOS, label: 'Todo estado' }, ...ESTADOS_ARTICULO.map((e) => ({ value: e, label: e }))] },
  ];

  const montoTotal = useMemo(() => tabla.filtrados.reduce((s, r) => s + (Number(r.costo) || 0), 0), [tabla.filtrados]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ position: 'relative' }}>
        <TablaCWO
          titulo="Artículos y Servicios"
          subtitulo="Busca y administra tu catálogo de venta."
          icono={null}
          accionNuevo={<Link to="/articulos/nuevo" className={styles.btnNuevo}><Plus size={17} /> Nuevo Artículo</Link>}
          accionSecundaria={<button type="button" onClick={() => setColsOpen((v) => !v)} className={styles.btnColumnas} title="Filtrar columnas"><SlidersHorizontal size={16} /></button>}
          filtrosTop={filtrosTop}
          busqueda={termino}
          onBusqueda={setTermino}
          placeholder="Buscar por nombre o código"
          pageSize={tabla.tamanoPagina}
          onPageSize={tabla.setTamanoPagina}
          cargando={recurso.cargando}
          error={recurso.error}
          usandoDemo={recurso.usandoDemo}
          onReintentar={recurso.recargar}
          columnas={columnas}
          filas={tabla.visibles.map((r) => ({ ...r, key: r.id }))}
          minWidth={1080}
          pie={<span>Monto total inventario (costo): <strong className={`cifra ${styles.totalPie}`}>{formatearMoneda(montoTotal)}</strong></span>}
          paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
        />

        {colsOpen && (
          <>
            <div onClick={() => setColsOpen(false)} className={styles.capaCierrePanel} />
            <div className={styles.panelColumnas}>
              <div className={styles.panelColumnasCabecera}><div className={styles.panelColumnasTitulo}>Columnas visibles</div><button type="button" onClick={() => setColsOpen(false)} className={styles.btnCerrarPanel}>×</button></div>
              <div className={styles.panelColumnasNota}>Nombre y Acciones son fijas.</div>
              <div className={styles.listaColumnas}>
                {COL_OPTS.map((co) => {
                  const activo = colsVisibles[co.key];
                  return (
                    <div key={co.key} onClick={() => setColsVisibles((v) => ({ ...v, [co.key]: !v[co.key] }))} className={styles.filaColumna}>
                      <span>{co.label}</span>
                      <span className={`${styles.interruptor} ${activo ? styles.interruptorActivo : ''}`}>
                        <span className={styles.interruptorBolita} />
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>

      <style>{`.cifra{font-variant-numeric:tabular-nums}`}</style>
    </div>
  );
}
