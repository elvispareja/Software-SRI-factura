import { AlertTriangle, Loader2, WifiOff } from 'lucide-react';
import styles from './EstadoCarga.module.css';

/** Fila de esqueleto mientras llegan los datos. */
export function TablaCargando({ filas = 5, columnas = 6 }) {
  return (
    <div className={styles.esqueleto}>
      {Array.from({ length: filas }, (_, fila) => (
        <div className={styles.esqueletoFila} key={fila}>
          {Array.from({ length: columnas }, (_, columna) => (
            <span className={styles.esqueletoCelda} key={columna} />
          ))}
        </div>
      ))}
      <span className={styles.esqueletoAviso}>
        <Loader2 size={16} className={styles.girando} /> Cargando…
      </span>
    </div>
  );
}

/** Error real del API: algo respondió, pero mal. */
export function ErrorCarga({ mensaje, onReintentar }) {
  return (
    <div className={styles.error}>
      <AlertTriangle size={32} />
      <p>No se pudieron cargar los datos.</p>
      <span>{mensaje}</span>
      {onReintentar && (
        <button className={styles.btnReintentar} onClick={onReintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}

/**
 * El backend no responde y **no** hay datos de ejemplo que enseñar.
 *
 * Distinto de `AvisoDemo`: en los listados se puede caer a datos de muestra
 * para que la interfaz siga siendo navegable, pero en un reporte de ventas
 * enseñar cifras inventadas es peor que no enseñar ninguna — nadie distingue
 * un total falso de uno real de un vistazo.
 */
export function SinConexion({ onReintentar }) {
  return (
    <div className={styles.error}>
      <WifiOff size={32} />
      <p>Sin conexión con el servidor.</p>
      <span>Los reportes se calculan en el servidor; no hay cifras que mostrar sin él.</span>
      {onReintentar && (
        <button className={styles.btnReintentar} onClick={onReintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}

/**
 * Aviso de que el backend no responde y se están mostrando datos de ejemplo.
 * Es importante que se vea: si no, el usuario cree que está viendo su negocio.
 */
export function AvisoDemo() {
  return (
    <div className={styles.avisoDemo}>
      <WifiOff size={16} />
      <span>
        Sin conexión con el servidor. Estás viendo <strong>datos de demostración</strong>.
      </span>
    </div>
  );
}
