import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Eye, MoreVertical } from 'lucide-react';
import { CATALOGO_RECEPTORES } from '../../data/catalogoReceptores';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { receptorDesdeApi } from '../../api/adaptadores';
import { api } from '../../api/cliente';
import TablaCWO from '../../components/ui/TablaCWO';
import styles from './Receptores.module.css';

const FILTROS_INICIALES = { rol: VALOR_TODOS };
const TAMANO_CONSULTA = { tamano: 200 };

// El tinte del avatar no codifica ningún dato del receptor: solo da variedad
// visual estable, por eso se reparte con un hash del nombre. Son clases de
// tema, no colores con significado.
const TINTES_AVATAR = [
  'avatarNeutro',
  'avatarAcento',
  'avatarInfo',
  'avatarExito',
  'avatarAviso',
];

function iniciales(nombre) {
  return String(nombre).trim().split(/\s+/).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? '').join('').slice(0, 2) || 'RE';
}

function claseAvatar(nombre) {
  const hash = [...String(nombre)].reduce((a, c) => a + c.charCodeAt(0), 0);
  return styles[TINTES_AVATAR[hash % TINTES_AVATAR.length]];
}

export default function ReceptoresList() {
  const [termino, setTermino] = useState('');
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);
  const [menuOpenId, setMenuOpenId] = useState(null);

  const recurso = useRecurso('/receptores', { parametros: TAMANO_CONSULTA, datosDemo: CATALOGO_RECEPTORES });
  const navigate = useNavigate();
  const registros = useMemo(() => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(receptorDesdeApi)), [recurso.datos, recurso.usandoDemo]);

  const tabla = useTablaFiltrada({
    datos: registros,
    termino,
    camposBusqueda: ['identificacion', 'razonSocial', 'nombreComercial', 'correo'],
    filtros,
  });

  const segmento = filtros.rol === VALOR_TODOS ? 'Todos' : filtros.rol;

  const desactivar = async (id) => {
    if (recurso.usandoDemo) return;
    try {
      await api.eliminar(`/receptores/${id}`);
      setMenuOpenId(null);
      recurso.recargar();
    } catch {
      // El error ya se muestra vía recurso.error en el próximo ciclo
    }
  };

  const columnas = [
    {
      key: 'nombre',
      titulo: 'NOMBRE',
      render: (r) => (
        <div className={styles.celdaNombre}>
          <div className={`${styles.avatar} ${claseAvatar(r.razonSocial)}`}>{iniciales(r.razonSocial)}</div>
          <div className={styles.datosNombre}>
            <div className={styles.razonSocial}>{r.razonSocial}</div>
            <div className={styles.correoCelda}>{r.correo || '-'}</div>
          </div>
        </div>
      ),
    },
    { key: 'tipo', titulo: 'TIPO', render: (r) => <span className={`${styles.chip} ${styles.chipNeutro}`}>{r.rol}</span> },
    { key: 'identificacion', titulo: '# IDENTIFICACIÓN', cifra: true, render: (r) => <span className={styles.identificacionCelda}>{r.identificacion}</span> },
    { key: 'telefonos', titulo: 'TELÉFONOS', render: () => <span className={`${styles.chip} ${styles.chipAcento}`}>-</span> },
    { key: 'facturaCon', titulo: 'FACTURA CON', render: (r) => <span className={`${styles.chip} ${styles.chipAcento}`}>{r.tipoIdentificacion}</span> },
    { key: 'codigo', titulo: 'CÓDIGO', render: (r) => <span className={styles.codigoCelda}>{r.id}</span> },
    {
      key: 'estado',
      titulo: 'ESTADO',
      render: (r) => (
        <span className={`${styles.pildora} ${r.estado === 'Activo' ? styles.pildoraExito : styles.pildoraError}`}>{r.estado}</span>
      ),
    },
    {
      key: 'acciones',
      titulo: 'ACCIONES',
      align: 'right',
      render: (r) => (
        <span className={styles.celdaAcciones}>
          <button type="button" className={styles.btnIconoTabla} aria-label={`Ver ${r.razonSocial}`}><Eye size={16} /></button>
          <span className={styles.envoltorioMenu}>
            <button
              type="button"
              onClick={() => setMenuOpenId((v) => (v === r.id ? null : r.id))}
              className={styles.btnIconoTabla}
              aria-label="Más acciones"
              aria-expanded={menuOpenId === r.id}
            >
              <MoreVertical size={16} />
            </button>
            {menuOpenId === r.id && (
              <>
                <span
                  onClick={() => setMenuOpenId(null)}
                  className={styles.capaCierre}
                  aria-hidden="true"
                />
                <span className={styles.menuAcciones}>
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpenId(null);
                      navigate(`/receptores/${r.id}/editar`);
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

  const filtrosExtra = (
    <div className={styles.chipsSegmento}>
      {[
        { value: VALOR_TODOS, label: 'Todos' },
        { value: 'Cliente', label: 'Clientes' },
        { value: 'Proveedor', label: 'Proveedores' },
        { value: 'Transportista', label: 'Transportista' },
      ].map((op) => (
        <button
          key={op.value}
          onClick={() => setFiltros({ rol: op.value })}
          className={`${styles.chipSegmento} ${filtros.rol === op.value ? styles.chipSegmentoActivo : ''}`}
        >
          {op.label}
        </button>
      ))}
    </div>
  );

  return (
    <TablaCWO
      titulo={segmento === 'Todos' ? 'Receptores' : segmento}
      subtitulo={segmento === 'Todos' ? 'Gestiona tus clientes, proveedores y transportistas.' : `Listado de ${segmento.toLowerCase()}s.`}
      accionNuevo={<Link to="/receptores/nuevo" className={styles.btnNuevo}><Plus size={17} /> Nuevo Receptor</Link>}
      busqueda={termino}
      onBusqueda={setTermino}
      placeholder="Buscar por RUC, nombre o correo"
      pageSize={tabla.tamanoPagina}
      onPageSize={tabla.setTamanoPagina}
      filtrosExtra={filtrosExtra}
      cargando={recurso.cargando}
      error={recurso.error}
      usandoDemo={recurso.usandoDemo}
      onReintentar={recurso.recargar}
      columnas={columnas}
      filas={tabla.visibles.map((r) => ({ ...r, key: r.id }))}
      minWidth={940}
      paginacion={{ desde: tabla.desde, hasta: tabla.hasta, total: tabla.total, pagina: tabla.pagina, totalPaginas: tabla.totalPaginas, onCambiarPagina: tabla.setPagina }}
    />
  );
}
