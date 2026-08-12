import { Download } from 'lucide-react';
import { ErrorCarga, SinConexion, TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './Cuentas.module.css';

/**
 * Una tarjeta de la pestaña «Reportes» de Cuentas.
 *
 * Es solo el envoltorio: cabecera, estados y botón de descarga. La tabla de
 * previsualización la pone quien la usa, porque cada reporte tiene sus propias
 * columnas y nada se gana con una tabla genérica que las adivine.
 *
 * La descarga es un `<a href download>` y no un `fetch` con Blob: el CSV lo
 * arma el servidor —con `;` y BOM, que es lo que Excel en español abre bien— y
 * el navegador ya sabe guardar un archivo mejor que nosotros.
 */
export default function TarjetaReporte({
  titulo,
  descripcion,
  badge,
  csv,
  reporte,
  columnas = 5,
  hayDatos,
  vacio,
  children,
}) {
  const cuerpo = () => {
    if (reporte.sinConexion) return <SinConexion onReintentar={reporte.recargar} />;
    if (reporte.error) return <ErrorCarga mensaje={reporte.error} onReintentar={reporte.recargar} />;
    if (reporte.cargando) return <TablaCargando columnas={columnas} filas={3} />;
    if (!hayDatos) return <div className={styles.reporteVacio}>{vacio}</div>;
    return children;
  };

  return (
    <div className={styles.reporteCard}>
      <div className={styles.reporteHead}>
        <div>
          <div className={styles.reporteTitle}>{titulo}</div>
          <div className={styles.reporteDesc}>{descripcion}</div>
        </div>
        <span className={styles.reporteBadge}>{badge}</span>
      </div>
      <div className={styles.reporteBody}>
        {cuerpo()}
        <div className={styles.reporteActions}>
          <a className={styles.btnDescarga} href={csv} download>
            <Download size={15} /> Descargar CSV
          </a>
        </div>
      </div>
    </div>
  );
}
