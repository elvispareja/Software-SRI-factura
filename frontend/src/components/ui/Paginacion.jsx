import { ChevronLeft, ChevronRight } from 'lucide-react';
import { TAMANOS_PAGINA } from '../../hooks/useTablaFiltrada';
import styles from './Paginacion.module.css';

/** Controles de paginación compartidos por todos los listados. */
export default function Paginacion({
  desde,
  hasta,
  total,
  pagina,
  totalPaginas,
  tamanoPagina,
  onCambiarPagina,
  onCambiarTamano,
}) {
  return (
    <div className={styles.contenedor}>
      <span className={styles.info}>
        {total === 0 ? 'Sin registros' : `Mostrando ${desde} a ${hasta} de ${total} registros`}
      </span>

      <div className={styles.controles}>
        <select
          className={styles.selectTamano}
          value={tamanoPagina}
          onChange={(evento) => onCambiarTamano(Number(evento.target.value))}
          aria-label="Registros por página"
        >
          {TAMANOS_PAGINA.map((tamano) => (
            <option key={tamano} value={tamano}>
              {tamano} por página
            </option>
          ))}
        </select>

        <div className={styles.navegacion}>
          <button
            className={styles.botonPagina}
            onClick={() => onCambiarPagina(pagina - 1)}
            disabled={pagina <= 1}
            aria-label="Página anterior"
          >
            <ChevronLeft size={18} />
          </button>
          <span className={styles.indicador}>
            {pagina} / {totalPaginas}
          </span>
          <button
            className={styles.botonPagina}
            onClick={() => onCambiarPagina(pagina + 1)}
            disabled={pagina >= totalPaginas}
            aria-label="Página siguiente"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
