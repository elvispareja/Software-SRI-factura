/**
 * Documentos de venta y compra contra el API.
 *
 * Un solo endpoint sirve factura, cotización, nota de venta, liquidación y
 * notas de crédito/débito: cambian por el campo `tipo`. Las guías de remisión
 * tienen endpoint propio porque no llevan importes.
 */

import { api } from './cliente';

export const TIPOS = {
  FACTURA: 'Factura',
  COTIZACION: 'Cotización',
  NOTA_VENTA: 'Nota de Venta',
  LIQUIDACION: 'Liquidación de Compra',
  NOTA_CREDITO: 'Nota de Crédito',
  NOTA_DEBITO: 'Nota de Débito',
};

/** Del API a la forma que usan los listados. */
export const documentoDesdeApi = (registro) => ({
  id: registro.id,
  numero: registro.numero,
  tipo: registro.tipo,
  cliente: registro.receptor_razon_social,
  identificacion: registro.receptor_identificacion,
  fecha: registro.fecha_emision,
  total: Number(registro.importe_total),
  metodo: registro.metodo,
  estado: registro.estado_sri,
  estadoSRI: registro.estado_sri,
  estadoPago: registro.estado_pago,
  validez: registro.validez_dias,
  documentoModificado: registro.num_doc_modificado,
  motivo: registro.motivo,
});

export const guiaDesdeApi = (registro) => ({
  id: registro.id,
  numero: registro.numero,
  claveAcceso: registro.clave_acceso,
  numeroAutorizacion: registro.numero_autorizacion,
  transportista: registro.transportista_razon_social,
  identificacion: registro.transportista_identificacion,
  placa: registro.placa,
  fechaInicio: registro.fecha_inicio,
  fechaFin: registro.fecha_fin,
  motivo: registro.motivo_traslado,
  destino: registro.direccion_llegada,
  items: registro.items?.length ?? 0,
  estado: registro.estado_sri,
});

/** De la interfaz al cuerpo que espera el API. */
export const documentoHaciaApi = ({
  tipo,
  receptorId,
  establecimiento = '001',
  puntoEmision = '001',
  metodo = 'Contado',
  formaPago = '01',
  lineas,
  validezDias,
  documentoModificado,
}) => ({
  tipo,
  receptor_id: receptorId,
  establecimiento,
  punto_emision: puntoEmision,
  metodo,
  forma_pago: formaPago,
  detalles: lineas.map((linea) => ({
    codigo_principal: linea.codigo || 'SIN-COD',
    descripcion: linea.descripcion,
    cantidad: String(linea.cantidad ?? '1'),
    precio_unitario: String(linea.precioUnitario ?? '0'),
    descuento_porcentaje: String(linea.descuentoPorcentaje ?? '0'),
    codigo_iva: linea.codigoIva ?? '4',
  })),
  ...(validezDias ? { validez_dias: Number(validezDias) } : {}),
  ...(documentoModificado
    ? {
        cod_doc_modificado: documentoModificado.codigo ?? '01',
        num_doc_modificado: documentoModificado.numero,
        fecha_doc_modificado: documentoModificado.fecha,
        motivo: documentoModificado.motivo,
      }
    : {}),
});

export const guiaHaciaApi = (guia, transportistaId, items) => ({
  establecimiento: '001',
  punto_emision: '001',
  fecha_inicio: guia.fechaInicio,
  fecha_fin: guia.fechaFin || null,
  motivo_traslado: guia.motivo,
  ruta: guia.ruta || null,
  tipo_transporte: guia.tipoTransporte,
  documento_aduanero: guia.documentoAduanero || null,
  transportista_id: transportistaId,
  placa: guia.placa,
  provincia_partida: guia.provinciaPartida || null,
  canton_partida: guia.cantonPartida || null,
  direccion_partida: guia.direccionPartida,
  provincia_llegada: guia.provinciaLlegada || null,
  canton_llegada: guia.cantonLlegada || null,
  direccion_llegada: guia.direccionLlegada,
  items: items.map((item) => ({
    codigo: item.codigo || '',
    descripcion: item.descripcion,
    cantidad: String(item.cantidad ?? '1'),
  })),
});

export const crearDocumento = (documento) =>
  api.crear('/comprobantes', documentoHaciaApi(documento));

export const anularDocumento = (id) => api.crear(`/comprobantes/${id}/anular`);

export const crearGuia = (guia, transportistaId, items) =>
  api.crear('/guias', guiaHaciaApi(guia, transportistaId, items));

export const anularGuia = (id) => api.crear(`/guias/${id}/anular`);

/** Firma la guía y la transmite. Mismo certificado que los comprobantes. */
export const emitirGuiaAlSri = (id) => api.crear(`/guias/${id}/emitir`);

export const urlRide = (id) => api.urlDescarga(`/comprobantes/${id}/ride`);
export const urlXml = (id) => api.urlDescarga(`/comprobantes/${id}/xml`);

/** Firma el comprobante con el certificado configurado y lo envía al SRI. */
export const emitirAlSri = (id) => api.crear(`/comprobantes/${id}/emitir`);

/**
 * Reconsulta la autorización.
 *
 * El SRI no autoriza de forma síncrona: un comprobante puede quedar pendiente
 * y autorizarse minutos después.
 */
export const consultarEstadoSri = (id) => api.crear(`/comprobantes/${id}/consultar`);

/**
 * Manda el comprobante al receptor con el XML y el RIDE adjuntos.
 *
 * Solo funciona sobre autorizados: mandar un borrador le entrega al cliente un
 * documento que el SRI no reconoce, y el backend lo rechaza por eso.
 */
export const enviarPorCorreo = (id, destinatario) =>
  api.crear(`/comprobantes/${id}/enviar`, destinatario ? { destinatario } : {});

/** ¿Hay servidor SMTP configurado? La interfaz lo pregunta antes de ofrecerlo. */
export const estadoCorreo = (opciones) =>
  api.obtener('/comprobantes/correo/estado', undefined, opciones);

/** Estados desde los que tiene sentido (re)intentar la emisión. */
export const ESTADOS_EMITIBLES = new Set(['Borrador', 'Rechazado', 'Devuelto', 'Error']);

/** Estados en los que el SRI ya recibió el comprobante y se puede reconsultar. */
export const ESTADOS_CONSULTABLES = new Set(['Pendiente', 'Devuelto', 'Rechazado']);

/**
 * Rutas que necesita `AccionesDocumento` para operar sobre un comprobante.
 *
 * Los tres documentos electrónicos exponen el mismo juego de endpoints, así
 * que el componente de acciones es uno solo y cambia este objeto.
 */
export const ACCIONES_COMPROBANTE = {
  enviar: enviarPorCorreo,
  urlRide,
  urlXml,
  emitir: emitirAlSri,
  consultar: consultarEstadoSri,
};

export const ACCIONES_GUIA = {
  urlRide: (id) => api.urlDescarga(`/guias/${id}/ride`),
  urlXml: (id) => api.urlDescarga(`/guias/${id}/xml`),
  emitir: emitirGuiaAlSri,
  consultar: (id) => api.crear(`/guias/${id}/consultar`),
};
