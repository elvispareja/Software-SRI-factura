import { useLocation, useNavigate } from 'react-router-dom';
import { resolverEstacion } from './estaciones';
import styles from './EstacionComprobante.module.css';

export default function EstacionComprobante({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const ws = resolverEstacion(location.pathname);

  if (!ws) return children ?? null;

  const tabs = ws.tabs.map((tab) => {
    const activo =
      tab.label === 'Crear'
        ? location.pathname === tab.to || location.pathname.startsWith(`${tab.to}/`)
        : location.pathname === tab.to;
    return { ...tab, activo };
  });

  return (
    <div className={styles.wrapper}>
      <div className={styles.estacion} role="region" aria-label={ws.titulo}>
        <span className={styles.rail} style={{ background: ws.rail }} aria-hidden="true" />
        <div className={styles.fila}>
          <div className={styles.identidad}>
            <span className={styles.iconBox} style={{ color: ws.rail }}>
              <ws.Icon size={23} strokeWidth={1.7} />
            </span>
            <div className={styles.titulos}>
              <div className={styles.tituloFila}>
                <span className={styles.titulo}>{ws.titulo}</span>
                <span className={styles.familia} style={{ color: ws.rail }}>
                  {ws.familia}
                </span>
              </div>
              <div className={`${styles.meta} cifra`}>{ws.meta}</div>
            </div>
          </div>

          <div className={styles.tabs} role="tablist" aria-label="Secciones">
            {tabs.map((tab) => (
              <button
                key={tab.to}
                type="button"
                role="tab"
                aria-selected={tab.activo}
                className={`${styles.tab} ${tab.activo ? styles.tabActivo : ''}`}
                onClick={() => navigate(tab.to)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className={styles.stats} aria-hidden="true">
            <div className={styles.stat}>
              <span className={styles.statLabel}>Total</span>
              <span className={`${styles.statValue} cifra`}>—</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Pendiente</span>
              <span className={`${styles.statValue} cifra`}>—</span>
            </div>
          </div>
        </div>
      </div>
      {children}
    </div>
  );
}
