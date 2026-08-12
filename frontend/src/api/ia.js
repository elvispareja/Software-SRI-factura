import { api } from './cliente';

export const ia = {
  /**
   * Envía un mensaje al simulador local del orquestador IA.
   * 
   * @param {string} telefono - Un identificador cualquiera para mantener la sesión.
   * @param {string} texto - El texto del mensaje que el usuario "envió".
   * @returns {Promise<string>} La respuesta del asistente.
   */
  simularMensaje: async (telefono, texto) => {
    const respuesta = await api.crear('/whatsapp/simulador', { telefono, texto });
    return respuesta.datos.respuesta;
  },
};
