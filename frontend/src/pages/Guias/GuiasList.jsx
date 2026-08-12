import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Search, Plus, Truck, SearchX } from 'lucide-react';
import {
  GUIAS_REMISION,
  ESTADOS_SRI,
  MOTIVOS_TRASLADO,
  TONO_ESTADO_SRI,
} from '../../data/documentosCompra';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { useRecurso } from '../../hooks/useRecurso';
import { ACCIONES_GUIA, guiaDesdeApi } from '../../api/documentos';
import AccionesDocumento from '../../components/documentos/AccionesDocumento';
import Paginacion from '../../components/ui/Paginacion';
import { AvisoDemo, ErrorCarga, TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './GuiasList.module.css';

const FILTROS_INICIALES = { estado: VALOR_TODOS, motivo: VALOR_TODOS };
const CONSULTA = { tamano: 200 };

export default function GuiasList() {
  const [termino, setTermino] = useState('');
  const [filtros, setFiltros] = useState(FILTROS_INICIALES);

  const recurso = useRecurso('/guias', { parametros: CONSULTA, datosDemo: GUIAS_REMISION });

  const registros = useMemo(
    () => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(guiaDesdeApi)),
    [recurso.datos, recurso.usandoDemo],
  );

  const tabla = useTablaFiltrada({
    datos: registros,
    termino,
    camposBusqueda: ['numero', 'transportista', 'placa', 'destino'],
    filtros,
  });

  const cambiarFiltro = (campo, valor) =>
    setFiltros((actuales) => ({ ...actuales, [campo]: valor }));

  const hayFiltrosActivos =
    termino !== '' || Object.values(filtros).some((valor) => valor !== VALOR_TODOS);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Guías de Remisión</h1>
          <p className={styles.subtitle}>Sustento del traslado físico de mercadería.</p>
        </div>
        <Link to="/guias/nueva" className={styles.btnPrimary}>
          <Plus size={18} /> Nueva Guía
        </Link>
      </header>

      {recurso.usandoDemo && <AvisoDemo />}

      <motion.div
        className={`${styles.tableContainer} glass-panel`}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className={styles.toolbar}>
          <div className={styles.searchWrapper}>
            <Search size={18} className={styles.searchIcon} />
            <input
              type="text"
              placeholder="Buscar por número, transportista, placa o destino…"
              className={styles.searchInput}
              value={termino}
              onChange={(evento) => setTermino(evento.target.value)}
            />
          </div>

          <div className={styles.filtros}>
            <select
              className={styles.filtroSelect}
              value={filtros.estado}
              onChange={(evento) => cambiarFiltro('estado', evento.target.value)}
              aria-label="Filtrar por estado SRI"
            >
              <option value={VALOR_TODOS}>Todo estado</option>
              {ESTADOS_SRI.map((estado) => (
                <option key={estado} value={estado}>
                  {estado}
                </option>
              ))}
            </select>

            <select
              className={styles.filtroSelect}
              value={filtros.motivo}
              onChange={(evento) => cambiarFiltro('motivo', evento.target.value)}
              aria-label="Filtrar por motivo"
            >
              <option value={VALOR_TODOS}>Todo motivo</option>
              {MOTIVOS_TRASLADO.map((motivo) => (
                <option key={motivo} value={motivo}>
                  {motivo}
                </option>
              ))}
            </select>

            {hayFiltrosActivos && (
              <button
                className={styles.btnLimpiar}
                onClick={() => {
                  setTermino('');
                  setFiltros(FILTROS_INICIALES);
                }}
              >
                Limpiar
              </button>
            )}
          </div>
        </div>

        {recurso.cargando ? (
          <TablaCargando columnas={9} />
        ) : recurso.error ? (
          <ErrorCarga mensaje={recurso.error} onReintentar={recurso.recargar} />
        ) : tabla.total === 0 ? (
          <div className={styles.sinCoincidencias}>
            <SearchX size={32} />
            <p>Ninguna guía coincide con la búsqueda.</p>
            <span>Ajusta el texto o los filtros.</span>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Transportista</th>
                  <th>Placa</th>
                  <th>Traslado</th>
                  <th>Destino</th>
                  <th>Motivo</th>
                  <th>Ítems</th>
                  <th>Estado SRI</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {tabla.visibles.map((guia) => (
                  <tr key={guia.id}>
                    <td>
                      <div className={styles.docWrapper}>
                        <Truck size={16} className={styles.textMuted} />
                        <span className={styles.docNumber}>{guia.numero}</span>
                      </div>
                    </td>
                    <td className={styles.mainText}>{guia.transportista}</td>
                    <td>
                      <span className={styles.placa}>{guia.placa}</span>
                    </td>
                    <td className={styles.textMuted}>
                      {guia.fechaInicio} → {guia.fechaFin}
                    </td>
                    <td className={styles.mainText}>{guia.destino}</td>
                    <td className={styles.textMuted}>{guia.motivo}</td>
                    <td className={styles.textMuted}>{guia.items}</td>
                    <td>
                      <span
                        className={`${styles.statusBadge} ${
                          styles[`estado${TONO_ESTADO_SRI[guia.estado] ?? 'neutral'}`]
                        }`}
                      >
                        {guia.estado}
                      </span>
                    </td>
                    <td>
                      {/* En modo demo los ids no existen en el servidor. */}
                      {!recurso.usandoDemo && (
                        <AccionesDocumento
                          comprobante={guia}
                          acciones={ACCIONES_GUIA}
                          onActualizar={recurso.recargar}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <Paginacion
          desde={tabla.desde}
          hasta={tabla.hasta}
          total={tabla.total}
          pagina={tabla.pagina}
          totalPaginas={tabla.totalPaginas}
          tamanoPagina={tabla.tamanoPagina}
          onCambiarPagina={tabla.setPagina}
          onCambiarTamano={tabla.setTamanoPagina}
        />
      </motion.div>
    </div>
  );
}
