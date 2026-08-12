import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { useSesion } from './useSesion';
import styles from './RutaProtegida.module.css';

/**
 * Bloquea las rutas internas hasta que haya sesión.
 *
 * Guarda la ruta a la que se intentaba entrar para volver a ella después del
 * login, en vez de dejar siempre al usuario en el inicio.
 */
export default function RutaProtegida() {
  const { autenticado, comprobando } = useSesion();
  const ubicacion = useLocation();

  if (comprobando) {
    return (
      <div className={styles.cargando}>
        <Loader2 size={28} className={styles.girando} />
        <span>Comprobando sesión…</span>
      </div>
    );
  }

  if (!autenticado) {
    return <Navigate to="/login" state={{ desde: ubicacion.pathname }} replace />;
  }

  return <Outlet />;
}
