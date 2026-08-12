import { useCallback, useEffect, useState } from 'react';
import { ErrorApi } from '../api/cliente';

/**
 * Carga un reporte: un único objeto, no una colección.
 *
 * `useRecurso` no sirve aquí porque asume una lista (cae a `[]` y calcula el
 * total por `length`). Un reporte tampoco tiene datos de demostración: enseñar
 * cifras inventadas de ventas es peor que no enseñar ninguna, porque nadie
 * distingue un total falso de uno real de un vistazo.
 */
export function useReporte(cargar, { activo = true } = {}) {
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(activo);
  const [error, setError] = useState(null);
  const [sinConexion, setSinConexion] = useState(false);

  const ejecutar = useCallback(
    async (senal) => {
      setCargando(true);
      setError(null);

      try {
        const respuesta = await cargar({ senal });
        if (senal?.aborted) return;

        setDatos(respuesta.datos ?? null);
        setSinConexion(false);
      } catch (fallo) {
        if (fallo.name === 'AbortError') return;

        // Se distingue el backend caído del error del servidor: el primero se
        // resuelve levantándolo, el segundo hay que mirarlo.
        if (fallo instanceof ErrorApi && fallo.esFalloDeRed) {
          setSinConexion(true);
          setDatos(null);
          setError(null);
        } else {
          setError(fallo.message);
        }
      } finally {
        if (!senal?.aborted) setCargando(false);
      }
    },
    [cargar],
  );

  useEffect(() => {
    if (!activo) {
      setCargando(false);
      return undefined;
    }

    const controlador = new AbortController();
    ejecutar(controlador.signal);
    return () => controlador.abort();
  }, [ejecutar, activo]);

  return { datos, cargando, error, sinConexion, recargar: () => ejecutar() };
}
