/**
 * Cliente HTTP del API.
 *
 * Centraliza URL base, cabeceras, token y traducción de errores, para que los
 * componentes no repitan `fetch` ni interpreten códigos HTTP a mano.
 */

export const URL_API = import.meta.env.VITE_URL_API ?? 'http://localhost:8000/api';

export class ErrorApi extends Error {
  constructor(mensaje, { estado = 0, detalles = null } = {}) {
    super(mensaje);
    this.name = 'ErrorApi';
    this.estado = estado;
    this.detalles = detalles;
  }

  /** El API no respondió: probablemente el backend no está levantado. */
  get esFalloDeRed() {
    return this.estado === 0;
  }
}

/**
 * FastAPI devuelve los errores de validación en `detail` como lista de objetos.
 * Se aplana a un texto legible en vez de mostrar el JSON crudo.
 */
function describirError(cuerpo, estado) {
  const detalle = cuerpo?.detail;

  if (typeof detalle === 'string') return detalle;
  if (Array.isArray(detalle)) {
    return detalle
      .map((item) => {
        const campo = Array.isArray(item.loc) ? item.loc.at(-1) : null;
        return campo ? `${campo}: ${item.msg}` : item.msg;
      })
      .join(' · ');
  }

  return `Error ${estado} al comunicarse con el servidor.`;
}

export async function peticion(ruta, { metodo = 'GET', cuerpo, senal, ...resto } = {}) {
  let respuesta;
  try {
    respuesta = await fetch(`${URL_API}${ruta}`, {
      method: metodo,
      signal: senal,
      // La sesión viaja en una cookie HttpOnly que el JavaScript no puede
      // leer; el navegador la adjunta sola si se piden las credenciales.
      credentials: 'include',
      headers: cuerpo ? { 'Content-Type': 'application/json' } : {},
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      ...resto,
    });
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new ErrorApi('No se pudo conectar con el servidor.', { estado: 0 });
  }

  if (respuesta.status === 204) {
    return { datos: null, total: 0 };
  }

  const tipo = respuesta.headers.get('content-type') ?? '';
  const cuerpoRespuesta = tipo.includes('application/json') ? await respuesta.json() : null;

  if (!respuesta.ok) {
    throw new ErrorApi(describirError(cuerpoRespuesta, respuesta.status), {
      estado: respuesta.status,
      detalles: cuerpoRespuesta,
    });
  }

  // El backend expone el total de registros en cabecera para paginar sin
  // una segunda petición de conteo.
  const total = Number(respuesta.headers.get('X-Total-Registros') ?? 0);
  return { datos: cuerpoRespuesta, total };
}

const construirRuta = (ruta, parametros) => {
  if (!parametros) return ruta;
  const limpios = Object.entries(parametros).filter(
    ([, valor]) => valor !== undefined && valor !== null && valor !== '',
  );
  if (limpios.length === 0) return ruta;
  return `${ruta}?${new URLSearchParams(limpios)}`;
};

export const api = {
  obtener: (ruta, parametros, opciones) =>
    peticion(construirRuta(ruta, parametros), opciones),
  crear: (ruta, cuerpo, opciones) => peticion(ruta, { metodo: 'POST', cuerpo, ...opciones }),
  actualizar: (ruta, cuerpo, opciones) => peticion(ruta, { metodo: 'PUT', cuerpo, ...opciones }),
  eliminar: (ruta, opciones) => peticion(ruta, { metodo: 'DELETE', ...opciones }),
  urlDescarga: (ruta) => `${URL_API}${ruta}`,
};
