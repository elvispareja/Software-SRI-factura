/**
 * Cuentas por cobrar: cuotas y recibos.
 *
 * Como en egresos, la **cuota** (lo que se debe) y el **recibo** (lo que se
 * cobró) son cosas distintas: un cliente puede abonar de a poco, y cada abono
 * es un movimiento de caja que hay que poder explicar por separado.
 */

import { api } from './cliente';

const numero = (valor) => Number(valor ?? 0);

export const FORMAS_COBRO = [
  'Efectivo',
  'Transferencia',
  'Cheque',
  'Tarjeta de crédito',
  'Tarjeta de débito',
  'Depósito',
];

export const cuotaDesdeApi = (registro) => ({
  id: registro.id,
  comprobanteId: registro.comprobante_id,
  numeroComprobante: registro.numero_comprobante,
  receptor: registro.receptor,
  numero: registro.numero,
  vence: registro.vence,
  monto: numero(registro.monto),
  cobrado: numero(registro.cobrado),
  saldo: numero(registro.saldo),
  estado: registro.estado,
  // Positivo son días de mora; negativo, días que faltan para vencer.
  diasMora: registro.dias_mora ?? 0,
});

export const reciboDesdeApi = (registro) => ({
  id: registro.id,
  numero: registro.numero,
  fecha: registro.fecha,
  cuotaId: registro.cuota_id,
  comprobanteId: registro.comprobante_id,
  receptor: registro.receptor_razon_social,
  monto: numero(registro.monto),
  formaPago: registro.forma_pago,
  referencia: registro.referencia ?? '',
  estado: registro.estado,
  observacion: registro.observacion ?? '',
});

export const resumenCobrosDesdeApi = (registro) => ({
  pendiente: numero(registro.pendiente),
  vencido: numero(registro.vencido),
  porVencer30: numero(registro.por_vencer_30),
  cuotasVencidas: registro.cuotas_vencidas ?? 0,
  cobradoMes: numero(registro.cobrado_mes),
});

export const cargarCuotas = (parametros, opciones) =>
  api.obtener('/cuentas/cuotas', parametros, opciones);

export const cargarRecibos = (parametros, opciones) =>
  api.obtener('/cuentas/recibos', parametros, opciones);

export const cargarResumenCobros = (opciones) =>
  api.obtener('/cuentas/resumen', undefined, opciones);

/**
 * Reparte el importe de un comprobante en cuotas.
 *
 * El resto se acumula en la última: dividir 100 en 3 da 33,33 tres veces, que
 * suma 99,99, y la cuota que falta un centavo es un cobro que nunca cuadra.
 */
export const generarCuotas = (comprobanteId, { cuotas, diasEntreCuotas, primeraFecha }) =>
  api.crear(`/cuentas/comprobantes/${comprobanteId}/cuotas`, {
    cuotas: Number(cuotas),
    dias_entre_cuotas: Number(diasEntreCuotas ?? 30),
    primera_fecha: primeraFecha || null,
  });

export const registrarRecibo = (recibo) =>
  api.crear('/cuentas/recibos', {
    fecha: recibo.fecha || null,
    cuota_id: recibo.cuotaId ? Number(recibo.cuotaId) : null,
    comprobante_id: recibo.comprobanteId ? Number(recibo.comprobanteId) : null,
    monto: String(recibo.monto ?? '0'),
    forma_pago: recibo.formaPago ?? 'Efectivo',
    cuenta_id: recibo.cuentaId ? Number(recibo.cuentaId) : null,
    referencia: recibo.referencia || null,
    observacion: recibo.observacion || null,
  });

export const anularRecibo = (id) => api.crear(`/cuentas/recibos/${id}/anular`);


// --------------------------------------------------------------------------
// Reportes de cuentas pendientes
//
// Los cinco de la pestaña «Reportes», más el modo que decide qué se lee.
//
// `modo` no es un rótulo: en `cobrar` la deuda son los comprobantes de venta y
// el abono es el recibo; en `pagar` son los gastos saldados con egresos más las
// liquidaciones de compra. Por eso viaja en TODAS las consultas de la pantalla
// y no solo en las tarjetas: enseñar cobros bajo la palabra «Proveedor» es un
// dato falso, no un rótulo mal puesto.
// --------------------------------------------------------------------------

export const COBRAR = 'cobrar';
export const PAGAR = 'pagar';

/** Cualquier otra cosa es `cobrar`: el modo lo trae la URL y puede venir sucio. */
export const modoValido = (modo) => (modo === PAGAR ? PAGAR : COBRAR);

const cabeceraReporte = (reporte) => ({
  modo: reporte.modo,
  // El backend manda cómo se llama la otra parte en este modo (Cliente o
  // Proveedor): así el CSV suelto se entiende sin ver la pantalla, y la
  // pantalla no tiene que deducir dos veces lo mismo.
  etiquetaContacto: reporte.etiqueta_contacto,
});

export const documentoPendienteDesdeApi = (fila) => ({
  origen: fila.origen,
  documentoId: fila.documento_id,
  tipo: fila.tipo,
  numero: fila.numero,
  fecha: fila.fecha,
  contacto: fila.contacto,
  identificacion: fila.identificacion,
  moneda: fila.moneda,
  vence: fila.vence,
  diasMora: fila.dias_mora ?? 0,
  total: numero(fila.total),
  abonado: numero(fila.abonado),
  saldo: numero(fila.saldo),
  estado: fila.estado,
});

export const saldosPendientesDesdeApi = (reporte) => ({
  ...cabeceraReporte(reporte),
  moneda: reporte.moneda,
  hoy: reporte.hoy,
  documentos: (reporte.documentos ?? []).map(documentoPendienteDesdeApi),
  totalDocumentos: reporte.total_documentos ?? 0,
  totalOriginal: numero(reporte.total_original),
  abonado: numero(reporte.abonado),
  saldo: numero(reporte.saldo),
});

export const cuotaAgendadaDesdeApi = (fila) => ({
  origen: fila.origen,
  documentoId: fila.documento_id,
  documento: fila.documento,
  tipo: fila.tipo,
  contacto: fila.contacto,
  identificacion: fila.identificacion,
  correo: fila.correo ?? '',
  telefono: fila.telefono ?? '',
  // Nulo cuando el documento no tiene plan de cuotas y entra como cuota única.
  cuotaId: fila.cuota_id ?? null,
  numero: fila.numero,
  vence: fila.vence,
  diasMora: fila.dias_mora ?? 0,
  monto: numero(fila.monto),
  abonado: numero(fila.abonado),
  saldo: numero(fila.saldo),
  estado: fila.estado,
});

export const agendaCuotasDesdeApi = (reporte) => ({
  ...cabeceraReporte(reporte),
  desde: reporte.desde,
  hasta: reporte.hasta,
  hoy: reporte.hoy,
  cuotas: (reporte.cuotas ?? []).map(cuotaAgendadaDesdeApi),
  totalCuotas: reporte.total_cuotas ?? 0,
  monto: numero(reporte.monto),
  abonado: numero(reporte.abonado),
  saldo: numero(reporte.saldo),
  vencidas: reporte.vencidas ?? 0,
  saldoVencido: numero(reporte.saldo_vencido),
});

export const reciboAplicadoDesdeApi = (fila) => ({
  origen: fila.origen,
  reciboId: fila.recibo_id,
  numero: fila.numero,
  fecha: fila.fecha,
  contacto: fila.contacto,
  documento: fila.documento ?? '',
  cuotaId: fila.cuota_id ?? null,
  monto: numero(fila.monto),
  formaPago: fila.forma_pago,
  estado: fila.estado,
  referencia: fila.referencia ?? '',
});

export const recibosGeneradosDesdeApi = (reporte) => ({
  ...cabeceraReporte(reporte),
  desde: reporte.desde,
  hasta: reporte.hasta,
  recibos: (reporte.recibos ?? []).map(reciboAplicadoDesdeApi),
  totalRecibos: reporte.total_recibos ?? 0,
  aplicado: numero(reporte.aplicado),
  anulados: reporte.anulados ?? 0,
  montoAnulado: numero(reporte.monto_anulado),
});

const filaRotacionDesdeApi = (fila) => ({
  grupo: fila.grupo,
  documentos: fila.documentos ?? 0,
  total: numero(fila.total),
  cobrado: numero(fila.cobrado),
  pendiente: numero(fila.pendiente),
  promedio: numero(fila.promedio),
  // Nulo, y no cero, cuando en el período no se movió dinero: cero diría que se
  // cobra al contado. Se conserva el nulo para que la tabla pinte un guion.
  diasRecuperacion:
    fila.dias_recuperacion === null || fila.dias_recuperacion === undefined
      ? null
      : Number(fila.dias_recuperacion),
});

export const rotacionCuentasDesdeApi = (reporte) => ({
  ...cabeceraReporte(reporte),
  desde: reporte.desde,
  hasta: reporte.hasta,
  diasPeriodo: reporte.dias_periodo ?? 0,
  porTipo: (reporte.por_tipo ?? []).map(filaRotacionDesdeApi),
  porContacto: (reporte.por_contacto ?? []).map(filaRotacionDesdeApi),
  totales: reporte.totales ? filaRotacionDesdeApi(reporte.totales) : null,
});

export const historialContactoDesdeApi = (fila) => ({
  receptorId: fila.receptor_id ?? null,
  contacto: fila.contacto,
  identificacion: fila.identificacion ?? '',
  correo: fila.correo ?? '',
  telefono: fila.telefono ?? '',
  documentos: fila.documentos ?? 0,
  total: numero(fila.total),
  abonado: numero(fila.abonado),
  saldo: numero(fila.saldo),
  cuotasPendientes: fila.cuotas_pendientes ?? 0,
  cuotasVencidas: fila.cuotas_vencidas ?? 0,
  saldoVencido: numero(fila.saldo_vencido),
  proximaFecha: fila.proxima_fecha ?? null,
  ultimoMovimiento: fila.ultimo_movimiento ?? null,
});

export const historialContactosDesdeApi = (reporte) => ({
  ...cabeceraReporte(reporte),
  hoy: reporte.hoy,
  contactos: (reporte.contactos ?? []).map(historialContactoDesdeApi),
  totalContactos: reporte.total_contactos ?? 0,
  total: numero(reporte.total),
  abonado: numero(reporte.abonado),
  saldo: numero(reporte.saldo),
});

export const cargarSaldosPendientes = (modo, parametros, opciones) =>
  api.obtener('/cuentas/reportes/saldos', { modo: modoValido(modo), ...parametros }, opciones);

export const cargarAgendaCuotas = (modo, parametros, opciones) =>
  api.obtener('/cuentas/reportes/agenda', { modo: modoValido(modo), ...parametros }, opciones);

export const cargarRecibosGenerados = (modo, parametros, opciones) =>
  api.obtener('/cuentas/reportes/recibos', { modo: modoValido(modo), ...parametros }, opciones);

export const cargarRotacionCuentas = (modo, parametros, opciones) =>
  api.obtener('/cuentas/reportes/rotacion', { modo: modoValido(modo), ...parametros }, opciones);

export const cargarHistorialContactos = (modo, parametros, opciones) =>
  api.obtener('/cuentas/reportes/historial', { modo: modoValido(modo), ...parametros }, opciones);

/**
 * URL de descarga del CSV de un reporte de cuentas.
 *
 * Se devuelve la URL y no un Blob: así la descarga la gestiona el navegador con
 * su propio diálogo, igual que en la pantalla de Reportes.
 */
export const urlCsvCuentas = (reporte, parametros = {}) => {
  const limpios = Object.entries({ ...parametros })
    .filter(([, valor]) => valor !== undefined && valor !== null && valor !== '')
    .map(([clave, valor]) => [clave, String(valor)]);
  return api.urlDescarga(`/cuentas/reportes/${reporte}/csv?${new URLSearchParams(limpios)}`);
};
