/**
 * Comprobantes de retención contra el API.
 *
 * Endpoint propio y no `/comprobantes` porque la retención no tiene líneas de
 * producto: declara porcentajes retenidos sobre el documento que sustenta el
 * pago al proveedor.
 */

import { api } from './cliente';

/** Tabla 20 del SRI. */
export const IMPUESTOS_RETENCION = [
  { codigo: '1', nombre: 'Impuesto a la renta' },
  { codigo: '2', nombre: 'IVA' },
  { codigo: '6', nombre: 'ISD' },
];

/** Tabla 4 del SRI: documento sobre el que se retiene. */
export const DOCUMENTOS_SUSTENTO = [
  { codigo: '01', nombre: 'Factura' },
  { codigo: '03', nombre: 'Liquidación de compra' },
  { codigo: '04', nombre: 'Nota de crédito' },
  { codigo: '05', nombre: 'Nota de débito' },
];

export const retencionDesdeApi = (registro) => ({
  id: registro.id,
  numero: registro.numero,
  claveAcceso: registro.clave_acceso,
  numeroAutorizacion: registro.numero_autorizacion,
  proveedor: registro.sujeto_razon_social,
  identificacion: registro.sujeto_identificacion,
  fecha: registro.fecha_emision,
  periodo: registro.periodo_fiscal,
  sustento: registro.num_doc_sustento,
  total: Number(registro.total_retenido),
  lineas: registro.detalles?.length ?? 0,
  estado: registro.estado_sri,
});

export const retencionHaciaApi = (retencion, sujetoId, lineas) => ({
  establecimiento: '001',
  punto_emision: '001',
  fecha_emision: retencion.fechaEmision || null,
  periodo_fiscal: retencion.periodoFiscal || null,
  sujeto_id: sujetoId,
  cod_doc_sustento: retencion.codDocSustento,
  num_doc_sustento: retencion.numDocSustento,
  fecha_doc_sustento: retencion.fechaDocSustento || null,
  detalles: lineas.map((linea) => ({
    codigo_impuesto: linea.codigoImpuesto,
    codigo_retencion: linea.codigoRetencion,
    base_imponible: String(linea.baseImponible ?? '0'),
    porcentaje_retener: String(linea.porcentaje ?? '0'),
  })),
});

/** Catálogo de conceptos con su porcentaje habitual (ayuda de la interfaz). */
export const cargarCodigosRetencion = () => api.obtener('/retenciones/codigos');

export const crearRetencion = (retencion, sujetoId, lineas) =>
  api.crear('/retenciones', retencionHaciaApi(retencion, sujetoId, lineas));

export const anularRetencion = (id) => api.crear(`/retenciones/${id}/anular`);

export const emitirRetencionAlSri = (id) => api.crear(`/retenciones/${id}/emitir`);

/** Juego de rutas que consume `AccionesDocumento`. */
export const ACCIONES_RETENCION = {
  urlRide: (id) => api.urlDescarga(`/retenciones/${id}/ride`),
  urlXml: (id) => api.urlDescarga(`/retenciones/${id}/xml`),
  emitir: emitirRetencionAlSri,
  consultar: (id) => api.crear(`/retenciones/${id}/consultar`),
};
