import { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Search, Plus, FileText, SearchX } from 'lucide-react';
import { useTablaFiltrada, VALOR_TODOS } from '../../hooks/useTablaFiltrada';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { urlRide } from '../../api/documentos';
import { METODOS_PAGO, TONO_ESTADO } from '../../data/documentosVenta';
import Paginacion from '../ui/Paginacion';
import { AvisoDemo, ErrorCarga, TablaCargando } from '../ui/EstadoCarga';
import styles from './ListaDocumentosVenta.module.css';

/**
 * Listado compartido por Cotizaciones y Notas de Venta: misma forma de datos
 * (número, cliente, fecha, total, método, estado) y mismas acciones.
 */
export default function ListaDocumentosVenta({
  titulo,
  subtitulo,
  datos,
  estados,
  rutaNuevo,
  textoNuevo,
  columnaExtra = null,
  // Estado de carga: lo pasa la página que consulta el API.
  cargando = false,
  error = null,
  usandoDemo = false,
  onReintentar = null,
}) {
  const [termino, setTermino] = useState('');
  const [filtros, setFiltros] = useState({ estado: VALOR_TODOS, metodo: VALOR_TODOS });

  const tabla = useTablaFiltrada({
    datos,
    termino,
    camposBusqueda: ['numero', 'cliente'],
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
          <h1 className={styles.title}>{titulo}</h1>
          <p className={styles.subtitle}>{subtitulo}</p>
        </div>
        <div className={styles.headerActions}>
          <Link to={rutaNuevo} className={styles.btnPrimary}>
            <Plus size={18} /> {textoNuevo}
          </Link>
        </div>
      </header>

      {usandoDemo && <AvisoDemo />}

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
              placeholder="Buscar por número o cliente…"
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
              aria-label="Filtrar por estado"
            >
              <option value={VALOR_TODOS}>Todo estado</option>
              {estados.map((estado) => (
                <option key={estado} value={estado}>
                  {estado}
                </option>
              ))}
            </select>

            <select
              className={styles.filtroSelect}
              value={filtros.metodo}
              onChange={(evento) => cambiarFiltro('metodo', evento.target.value)}
              aria-label="Filtrar por método de pago"
            >
              <option value={VALOR_TODOS}>Todo método</option>
              {METODOS_PAGO.map((metodo) => (
                <option key={metodo} value={metodo}>
                  {metodo}
                </option>
              ))}
            </select>

            {hayFiltrosActivos && (
              <button
                className={styles.btnLimpiar}
                onClick={() => {
                  setTermino('');
                  setFiltros({ estado: VALOR_TODOS, metodo: VALOR_TODOS });
                }}
              >
                Limpiar
              </button>
            )}
          </div>
        </div>

        {cargando ? (
          <TablaCargando columnas={columnaExtra ? 8 : 7} />
        ) : error ? (
          <ErrorCarga mensaje={error} onReintentar={onReintentar} />
        ) : tabla.total === 0 ? (
          <div className={styles.sinCoincidencias}>
            <SearchX size={32} />
            <p>Ningún documento coincide con la búsqueda.</p>
            <span>Ajusta el texto o los filtros.</span>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Documento</th>
                  <th>Cliente</th>
                  <th>Fecha</th>
                  {columnaExtra && <th>{columnaExtra.titulo}</th>}
                  <th>Total</th>
                  <th>Método</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {tabla.visibles.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className={styles.docWrapper}>
                        <FileText size={16} className={styles.textMuted} />
                        <span className={styles.docNumber}>{item.numero}</span>
                      </div>
                    </td>
                    <td className={styles.mainText}>{item.cliente}</td>
                    <td className={styles.textMuted}>{item.fecha}</td>
                    {columnaExtra && (
                      <td className={styles.textMuted}>{columnaExtra.valor(item)}</td>
                    )}
                    <td className={styles.price}>{formatearMoneda(item.total)}</td>
                    <td className={styles.textMuted}>{item.metodo}</td>
                    <td>
                      <span
                        className={`${styles.statusBadge} ${
                          styles[`estado${TONO_ESTADO[item.estado] ?? 'neutral'}`]
                        }`}
                      >
                        {item.estado}
                      </span>
                    </td>
                    <td>
                      {usandoDemo ? (
                        <button
                          className={styles.btnActionSmall}
                          disabled
                          title="Sin conexión: el PDF no está disponible en modo demostración."
                        >
                          Ver PDF
                        </button>
                      ) : (
                        <a
                          className={styles.btnActionSmall}
                          href={urlRide(item.id)}
                          target="_blank"
                          rel="noreferrer"
                          title="Abrir el PDF (RIDE) en una pestaña nueva."
                        >
                          Ver PDF
                        </a>
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
