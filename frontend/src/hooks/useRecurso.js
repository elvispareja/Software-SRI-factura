import { useCallback, useEffect, useRef, useState } from 'react';
import { ErrorApi, api } from '../api/cliente';

/**
 * Carga una colección del API con estados de carga y error.
 *
 * Si el backend no responde, se cae a los datos de demostración y se avisa con
 * `usandoDemo`. Así la interfaz sigue siendo navegable sin backend levantado,
 * pero sin fingir que los datos son reales: la pantalla muestra el aviso.
 */
// Hay recursos que no son listas: /configuracion/empresa y /configuracion/firma
// devuelven un objeto, o null cuando aún no se han configurado. En esos casos
// «cuántos hay» no es `.length` —que reventaría— sino uno o ninguno.
const cuantos = (datos) => (Array.isArray(datos) ? datos.length : datos ? 1 : 0);

export function useRecurso(ruta, { parametros, datosDemo = [], activo = true } = {}) {
  const [datos, setDatos] = useState(datosDemo);
  const [total, setTotal] = useState(() => cuantos(datosDemo));
  const [cargando, setCargando] = useState(activo);
  const [error, setError] = useState(null);
  const [usandoDemo, setUsandoDemo] = useState(false);

  // Se serializa para poder compararlo por valor en las dependencias.
  const parametrosSerializados = JSON.stringify(parametros ?? {});
  const datosDemoRef = useRef(datosDemo);
  datosDemoRef.current = datosDemo;

  const cargar = useCallback(
    async (senal) => {
      setCargando(true);
      setError(null);

      try {
        const respuesta = await api.obtener(ruta, JSON.parse(parametrosSerializados), { senal });
        if (senal?.aborted) return;

        setDatos(respuesta.datos ?? []);
        setTotal(respuesta.total || cuantos(respuesta.datos));
        setUsandoDemo(false);
      } catch (fallo) {
        if (fallo.name === 'AbortError') return;

        if (fallo instanceof ErrorApi && fallo.esFalloDeRed) {
          setDatos(datosDemoRef.current);
          setTotal(cuantos(datosDemoRef.current));
          setUsandoDemo(true);
          setError(null);
        } else {
          setError(fallo.message);
        }
      } finally {
        if (!senal?.aborted) setCargando(false);
      }
    },
    [ruta, parametrosSerializados],
  );

  useEffect(() => {
    if (!activo) {
      setCargando(false);
      return undefined;
    }

    // Se cancela la petición anterior si cambian los filtros mientras carga:
    // sin esto, una respuesta lenta puede pisar a otra más reciente.
    const controlador = new AbortController();
    cargar(controlador.signal);
    return () => controlador.abort();
  }, [cargar, activo]);

  return { datos, total, cargando, error, usandoDemo, recargar: () => cargar() };
}
