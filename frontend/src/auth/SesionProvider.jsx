import { useCallback, useEffect, useMemo, useState } from 'react';
import { ErrorApi, URL_API } from '../api/cliente';
import { CLAVE_SESION, SesionContext } from './contexto';

/**
 * Sesión del usuario.
 *
 * El token vive en una cookie HttpOnly que emite el backend: el JavaScript de
 * la página no puede leerlo, así que un XSS no se lleva la sesión. Aquí solo
 * se guardan los datos visibles del usuario (nombre, correo, rol) para pintar
 * la cabecera sin pedirlos en cada carga.
 *
 * Si el API no responde se ofrece un "modo demostración" para poder recorrer
 * la interfaz sin backend. Ese modo se marca en la sesión y la cabecera lo
 * indica, para que nunca se confunda con datos reales.
 */

const leerSesionGuardada = () => {
  try {
    const guardada = localStorage.getItem(CLAVE_SESION);
    return guardada ? JSON.parse(guardada) : null;
  } catch {
    return null;
  }
};

export function SesionProvider({ children }) {
  const [usuario, setUsuario] = useState(leerSesionGuardada);
  const [comprobando, setComprobando] = useState(Boolean(leerSesionGuardada()));

  const persistir = useCallback((datos) => {
    setUsuario(datos);
    try {
      if (datos) localStorage.setItem(CLAVE_SESION, JSON.stringify(datos));
      else localStorage.removeItem(CLAVE_SESION);
    } catch {
      // Sin persistencia la sesión dura lo que la pestaña.
    }
  }, []);

  // Al arrancar se revalida contra el servidor: la cookie pudo expirar
  // mientras la pestaña estaba cerrada, y aquí no hay forma de inspeccionarla.
  useEffect(() => {
    if (!usuario || usuario.modoDemo) {
      setComprobando(false);
      return undefined;
    }

    const controlador = new AbortController();

    fetch(`${URL_API}/auth/yo`, {
      credentials: 'include',
      signal: controlador.signal,
    })
      .then((respuesta) => {
        if (respuesta.status === 401) persistir(null);
      })
      .catch(() => {
        // Sin red no se cierra la sesión: puede ser un corte momentáneo.
      })
      .finally(() => setComprobando(false));

    return () => controlador.abort();
    // Solo debe correr al montar.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const iniciarSesion = useCallback(
    async (correo, contrasena) => {
      // El endpoint de token usa formulario, no JSON: es el estándar de OAuth2.
      const cuerpo = new URLSearchParams({ username: correo, password: contrasena });

      let respuesta;
      try {
        respuesta = await fetch(`${URL_API}/auth/token`, {
          method: 'POST',
          // Necesario para que el navegador acepte la cookie de sesión.
          credentials: 'include',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: cuerpo,
        });
      } catch {
        throw new ErrorApi('No se pudo conectar con el servidor.', { estado: 0 });
      }

      const datos = await respuesta.json().catch(() => null);

      if (!respuesta.ok) {
        throw new ErrorApi(datos?.detail ?? 'No se pudo iniciar sesión.', {
          estado: respuesta.status,
        });
      }

      // El token ya viaja en la cookie HttpOnly; aquí solo se guarda lo visible.
      persistir({
        nombre: datos.nombre,
        correo: datos.correo,
        rol: datos.rol,
        modoDemo: false,
      });
    },
    [persistir],
  );

  const registrar = useCallback(async (correo, nombre, contrasena) => {
    let respuesta;
    try {
      respuesta = await fetch(`${URL_API}/auth/registro`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ correo, nombre, contrasena }),
      });
    } catch {
      throw new ErrorApi('No se pudo conectar con el servidor.', { estado: 0 });
    }

    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
      const detalle = Array.isArray(datos?.detail)
        ? datos.detail.map((item) => item.msg).join(' · ')
        : datos?.detail;
      throw new ErrorApi(detalle ?? 'No se pudo crear la cuenta.', { estado: respuesta.status });
    }
    return datos;
  }, []);

  const entrarEnModoDemo = useCallback(() => {
    persistir({ nombre: 'Usuario demo', correo: 'demo@local', rol: 'demo', modoDemo: true });
  }, [persistir]);

  const cerrarSesion = useCallback(async () => {
    // Solo el servidor puede borrar una cookie HttpOnly.
    try {
      await fetch(`${URL_API}/auth/salir`, { method: 'POST', credentials: 'include' });
    } catch {
      // Sin red igual se limpia el estado local.
    }
    persistir(null);
  }, [persistir]);

  const valor = useMemo(
    () => ({
      usuario,
      comprobando,
      autenticado: Boolean(usuario),
      iniciarSesion,
      registrar,
      entrarEnModoDemo,
      cerrarSesion,
    }),
    [usuario, comprobando, iniciarSesion, registrar, entrarEnModoDemo, cerrarSesion],
  );

  return <SesionContext.Provider value={valor}>{children}</SesionContext.Provider>;
}
