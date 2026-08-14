/** Configuración de la empresa emisora contra el API. */

import { api, URL_API } from './cliente';

export const empresaDesdeApi = (registro) => ({
  ruc: registro.ruc,
  razonSocial: registro.razon_social,
  nombreComercial: registro.nombre_comercial ?? '',
  direccionMatriz: registro.direccion_matriz,
  provincia: registro.provincia ?? '',
  canton: registro.canton ?? '',
  telefono: registro.telefono ?? '',
  correo: registro.correo ?? '',
  regimen: registro.regimen,
  obligadoContabilidad: registro.obligado_contabilidad,
  agenteRetencion: registro.agente_retencion ?? '',
  // Se conserva aunque el formulario no lo edite: si no se reenvía, el backend
  // lo pone en null al guardar la empresa y deja de poder emitir retenciones.
  contribuyenteEspecial: registro.contribuyente_especial ?? '',
  contribuyenteRimpe: Boolean(registro.contribuyente_rimpe),
  ambiente: registro.ambiente,
});

export const empresaHaciaApi = (empresa) => ({
  ruc: empresa.ruc,
  razon_social: empresa.razonSocial,
  nombre_comercial: empresa.nombreComercial || null,
  direccion_matriz: empresa.direccionMatriz,
  provincia: empresa.provincia || null,
  canton: empresa.canton || null,
  telefono: empresa.telefono || null,
  correo: empresa.correo || null,
  regimen: empresa.regimen,
  obligado_contabilidad: empresa.obligadoContabilidad,
  agente_retencion: empresa.agenteRetencion || null,
  // Se reenvía el valor cargado para que guardar la empresa no lo borre.
  contribuyente_especial: empresa.contribuyenteEspecial || null,
  // El backend guarda la leyenda, no un booleano.
  contribuyente_rimpe: empresa.contribuyenteRimpe
    ? 'CONTRIBUYENTE RÉGIMEN RIMPE'
    : null,
  ambiente: empresa.ambiente,
});

export const establecimientoDesdeApi = (registro) => ({
  id: registro.id,
  codigo: registro.codigo,
  nombre: registro.nombre,
  direccion: registro.direccion,
  puntosEmision: (registro.puntos_emision ?? []).map((punto) => ({
    id: punto.id,
    codigo: punto.codigo,
    nombre: punto.nombre,
    secuencialFactura: punto.secuencial_factura,
  })),
});

export const establecimientoHaciaApi = (establecimiento) => ({
  codigo: establecimiento.codigo,
  nombre: establecimiento.nombre,
  direccion: establecimiento.direccion,
  puntos_emision: (establecimiento.puntosEmision ?? []).map((punto) => ({
    codigo: punto.codigo,
    nombre: punto.nombre,
    secuencial_factura: Number(punto.secuencialFactura) || 1,
  })),
});

export const guardarEmpresa = (empresa) =>
  api.actualizar('/configuracion/empresa', empresaHaciaApi(empresa));

export const crearEstablecimiento = (establecimiento) =>
  api.crear('/configuracion/establecimientos', establecimientoHaciaApi(establecimiento));

export const eliminarEstablecimiento = (id) =>
  api.eliminar(`/configuracion/establecimientos/${id}`);


export const cuentaDesdeApi = (registro) => ({
  id: registro.id,
  banco: registro.banco,
  tipo: registro.tipo,
  numero: registro.numero,
  titular: registro.titular,
});

export const crearCuenta = (cuenta) =>
  api.crear('/configuracion/cuentas', {
    banco: cuenta.banco,
    tipo: cuenta.tipo,
    numero: cuenta.numero,
    titular: cuenta.titular,
  });

export const eliminarCuenta = (id) => api.eliminar(`/configuracion/cuentas/${id}`);

export const firmaDesdeApi = (registro) =>
  registro
    ? {
        nombreArchivo: registro.nombre_archivo,
        propietario: registro.propietario,
        emisor: registro.emisor,
        validaDesde: registro.valida_desde,
        validaHasta: registro.valida_hasta,
      }
    : null;

/**
 * Sube el certificado.
 *
 * Va como multipart, no JSON: lleva un archivo binario. No se usa el helper
 * `api.crear` porque ese fija Content-Type a JSON, y aquí el navegador debe
 * poner el boundary del multipart por su cuenta.
 */
export async function subirFirma(archivo, contrasena) {
  const cuerpo = new FormData();
  cuerpo.append('archivo', archivo);
  cuerpo.append('contrasena', contrasena);

  const respuesta = await fetch(`${URL_API}/configuracion/firma`, {
    method: 'POST',
    credentials: 'include',
    body: cuerpo,
  });

  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    const detalle = Array.isArray(datos?.detail)
      ? datos.detail.map((item) => item.msg).join(' · ')
      : datos?.detail;
    throw new Error(detalle ?? 'No se pudo subir el certificado.');
  }
  return firmaDesdeApi(datos);
}

export const quitarFirma = () => api.eliminar('/configuracion/firma');

export const actualizarEstablecimiento = (id, establecimiento) =>
  api.actualizar(
    `/configuracion/establecimientos/${id}`,
    establecimientoHaciaApi(establecimiento),
  );


// --------------------------------------------------------------------------
// Listas auxiliares de configuración
//
// Zonas, vendedores y leyendas las define el negocio. Los catálogos del SRI
// (tarifas de IVA, códigos de retención) no viven aquí: los fija la ficha
// técnica y el usuario no puede inventárselos.
// --------------------------------------------------------------------------

export const listaDesdeApi = (registro) => ({
  id: registro.id,
  tipo: registro.tipo,
  nombre: registro.nombre,
  detalle: registro.detalle ?? '',
  estado: registro.estado,
});

export const usuarioDesdeApi = (registro) => ({
  id: registro.id,
  nombre: registro.nombre,
  correo: registro.correo,
  rol: registro.rol,
  activo: registro.activo,
});

/**
 * Edita el perfil del usuario en sesión.
 *
 * La contraseña actual es obligatoria (la exige el backend); la nueva es
 * opcional y viaja como null si no se cambia.
 */
export const actualizarPerfil = ({ nombre, correo, contrasenaActual, contrasenaNueva }) =>
  api.actualizar('/auth/perfil', {
    nombre,
    correo,
    contrasena_actual: contrasenaActual,
    contrasena_nueva: contrasenaNueva || null,
  });

export const crearEnLista = (tipo, entrada) =>
  api.crear(`/configuracion/listas/${tipo}`, {
    nombre: entrada.nombre,
    detalle: entrada.detalle || null,
    estado: entrada.estado ?? 'Activo',
  });

export const actualizarEnLista = (tipo, id, entrada) =>
  api.actualizar(`/configuracion/listas/${tipo}/${id}`, {
    nombre: entrada.nombre,
    detalle: entrada.detalle || null,
    estado: entrada.estado ?? 'Activo',
  });

/** Se desactiva, no se borra: los receptores guardan la zona como texto. */
export const desactivarEnLista = (tipo, id) =>
  api.eliminar(`/configuracion/listas/${tipo}/${id}`);
