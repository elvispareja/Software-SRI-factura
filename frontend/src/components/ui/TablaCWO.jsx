import { Search, RefreshCw } from 'lucide-react';
import { TAMANOS_PAGINA } from '../../hooks/useTablaFiltrada';
import { AvisoDemo, ErrorCarga, TablaCargando } from './EstadoCarga';
import styles from './TablaCWO.module.css';

export default function TablaCWO({
  titulo,
  subtitulo,
  icono,
  accionNuevo,
  accionSecundaria,
  // Toolbar superior: filtros en selects
  filtrosTop,
  // Toolbar búsqueda + pageSize + archivado
  busqueda,
  onBusqueda,
  placeholder = 'Buscar...',
  pageSize,
  onPageSize,
  archivado,
  onToggleArchivado,
  // Filtros extra (chips)
  filtrosExtra,
  // Datos
  cargando,
  error,
  usandoDemo,
  onReintentar,
  sinCoincidencias,
  columnas,
  filas,
  // Paginación
  paginacion,
  // Pie adicional
  pie,
  minWidth = 640,
}) {
  const Icono = icono;

  return (
    <div className={styles.container}>
      {(titulo || accionNuevo) && (
        <header className={styles.header}>
          <div className={styles.headerTitle}>
            {Icono && (
              <span className={styles.headerIcon}><Icono size={22} /></span>
            )}
            <div>
              {titulo && <h1 className={styles.title}>{titulo}</h1>}
              {subtitulo && <p className={styles.subtitle}>{subtitulo}</p>}
            </div>
          </div>
          <div className={styles.headerActions}>
            {accionSecundaria}
            {accionNuevo}
          </div>
        </header>
      )}

      {usandoDemo && <AvisoDemo />}

      <div className={styles.panel}>
        {filtrosTop && (
          <div className={styles.filtrosTop}>
            {filtrosTop.map((f) => (
              <label key={f.key} className={styles.filtroLabel}>
                <span>{f.label}</span>
                <select value={f.value} onChange={(e) => f.onChange(e.target.value)} className={styles.select}>
                  {f.opciones.map((op) => (
                    <option key={String(op.value ?? op)} value={op.value ?? op}>{op.label ?? op}</option>
                  ))}
                </select>
              </label>
            ))}
          </div>
        )}

        <div className={styles.toolbar}>
          <div className={styles.searchWrap}>
            <Search size={17} className={styles.searchIcon} />
            <input
              type="text"
              className={styles.searchInput}
              placeholder={placeholder}
              value={busqueda ?? ''}
              onChange={(e) => onBusqueda?.(e.target.value)}
            />
          </div>
          <button className={styles.btnRefresh} onClick={onReintentar} title="Actualizar" aria-label="Actualizar">
            <RefreshCw size={16} />
          </button>
          {onPageSize && (
            <select className={styles.select} value={pageSize} onChange={(e) => onPageSize(Number(e.target.value))} aria-label="Registros por página">
              {TAMANOS_PAGINA.map((t) => <option key={t} value={t}>{t}</option>)}
              {[25, 50, 100].filter((n) => !TAMANOS_PAGINA.includes(n)).map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          )}
          {onToggleArchivado && (
            <label className={styles.toggleWrap}>
              <span className={styles.toggleTrack} data-activo={archivado ? 'true' : 'false'} onClick={onToggleArchivado} role="switch" aria-checked={archivado} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onToggleArchivado()}>
                <span className={styles.toggleKnob} style={{ left: archivado ? '21px' : '3px' }} />
              </span>
              <span className={styles.toggleLabel}>Archivado</span>
            </label>
          )}
          {filtrosExtra}
        </div>

        {cargando ? (
          <TablaCargando columnas={columnas?.length ?? 6} />
        ) : error ? (
          <ErrorCarga mensaje={error} onReintentar={onReintentar} />
        ) : filas?.length === 0 ? (
          sinCoincidencias ?? (
            <div className={styles.sinCoincidencias}><p>Sin resultados. Ajusta los filtros.</p></div>
          )
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table} style={{ minWidth }}>
              <thead>
                <tr>
                  {columnas.map((c) => (
                    <th key={c.key} style={{ textAlign: c.align ?? 'left', display: c.hidden ? 'none' : undefined }}>{c.titulo}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filas.map((fila, idx) => (
                  <tr key={fila.key ?? idx}>
                    {columnas.map((c) => (
                      <td key={c.key} style={{ textAlign: c.align ?? 'left', display: c.hidden ? 'none' : undefined }} className={c.cifra ? 'cifra' : undefined}>
                        {c.render ? c.render(fila, idx) : fila[c.key]}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {pie && <div className={styles.pie}>{pie}</div>}

        {paginacion && (
          <div className={styles.paginacion}>
            <span className={styles.pagInfo}>
              {paginacion.total === 0 ? 'Sin registros' : `Mostrando ${paginacion.desde} a ${paginacion.hasta} de ${paginacion.total} registros`}
            </span>
            <div className={styles.pagBtns}>
              <button className={styles.pagBtn} disabled={paginacion.pagina <= 1} onClick={() => paginacion.onCambiarPagina(paginacion.pagina - 1)}>Atrás</button>
              <span className={styles.pagNum}>{paginacion.pagina}</span>
              <button className={styles.pagBtn} disabled={paginacion.pagina >= paginacion.totalPaginas} onClick={() => paginacion.onCambiarPagina(paginacion.pagina + 1)}>Siguiente</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
