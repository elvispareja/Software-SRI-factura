/**
 * Egresos, anticipos y facturación recurrente contra el API.
 *
 * La distinción entre **gasto** y **egreso** es la del backend y conviene
 * repetirla aquí: el gasto es la obligación (llegó la factura del arriendo) y
 * el egreso es la salida de dinero (se pagó). No coinciden ni en fecha ni en
 * importe, por eso son dos listados distintos.
 */

import { api } from './cliente';

const numero = (valor) => Number(valor ?? 0);

export const FORMAS_PAGO_EGRESO = [
  'Efectivo',
  'Transferencia',
  'Cheque',
  'Tarjeta de crédito',
  'Tarjeta de débito',
];

export const ESTADOS_PAGO_GASTO = ['Por Pagar', 'Parcial', 'Pagado'];

export const PERIODICIDADES = [
  'Semanal',
  'Quincenal',
  'Mensual',
  'Bimestral',
  'Trimestral',
  'Anual',
];

/** ARD: recibido de un cliente. APP: pagado a un proveedor. */
export const TIPOS_ANTICIPO = [
  { codigo: 'ARD', nombre: 'Recibido de cliente' },
  { codigo: 'APP', nombre: 'Pagado a proveedor' },
];

export const ESTADOS_ANTICIPO = ['Pendiente', 'Parcial', 'Aplicado', 'Anulado'];

// --------------------------------------------------------------------------
// Tipos de gasto
// --------------------------------------------------------------------------

export const tipoGastoDesdeApi = (registro) => ({
  id: registro.id,
  nombre: registro.nombre,
  descripcion: registro.descripcion ?? '',
  deducible: registro.deducible,
  estado: registro.estado,
});

export const tipoGastoHaciaApi = (tipo) => ({
  nombre: tipo.nombre,
  descripcion: tipo.descripcion || null,
  // `?? true` y no `Boolean(...)`: con `Boolean` un campo sin tocar viajaría
  // como false e invertiría el valor por defecto del backend, marcando el
  // gasto como no deducible sin que nadie lo pidiera.
  deducible: tipo.deducible ?? true,
  estado: tipo.estado ?? 'Activo',
});

export const cargarTiposGasto = (opciones) =>
  api.obtener('/egresos/tipos', undefined, opciones);
export const crearTipoGasto = (tipo) => api.crear('/egresos/tipos', tipoGastoHaciaApi(tipo));
export const actualizarTipoGasto = (id, tipo) =>
  api.actualizar(`/egresos/tipos/${id}`, tipoGastoHaciaApi(tipo));
export const desactivarTipoGasto = (id) => api.eliminar(`/egresos/tipos/${id}`);

// --------------------------------------------------------------------------
// Gastos
// --------------------------------------------------------------------------

export const gastoDesdeApi = (registro) => ({
  id: registro.id,
  fecha: registro.fecha,
  concepto: registro.concepto,
  tipoId: registro.tipo_id,
  proveedor: registro.proveedor_razon_social,
  identificacion: registro.proveedor_identificacion,
  documento: registro.documento,
  fechaDocumento: registro.fecha_documento,
  autorizacionProveedor: registro.autorizacion_proveedor ?? '',
  subtotal: numero(registro.subtotal),
  iva: numero(registro.iva),
  codigoIva: registro.codigo_iva ?? '4',
  total: numero(registro.total),
  estadoPago: registro.estado_pago,
  observacion: registro.observacion ?? '',
});

export const gastoHaciaApi = (gasto) => ({
  fecha: gasto.fecha || null,
  concepto: gasto.concepto,
  tipo_id: gasto.tipoId ? Number(gasto.tipoId) : null,
  proveedor_id: gasto.proveedorId ? Number(gasto.proveedorId) : null,
  documento: gasto.documento || '',
  fecha_documento: gasto.fechaDocumento || null,
  autorizacion_proveedor: gasto.autorizacionProveedor || null,
  subtotal: String(gasto.subtotal ?? '0'),
  iva: String(gasto.iva ?? '0'),
  codigo_iva: gasto.codigoIva || '4',
  estado_pago: gasto.estadoPago ?? 'Por Pagar',
  observacion: gasto.observacion || null,
});

export const crearGasto = (gasto) => api.crear('/egresos/gastos', gastoHaciaApi(gasto));
export const actualizarGasto = (id, gasto) =>
  api.actualizar(`/egresos/gastos/${id}`, gastoHaciaApi(gasto));
export const eliminarGasto = (id) => api.eliminar(`/egresos/gastos/${id}`);

// --------------------------------------------------------------------------
// Egresos (pagos)
// --------------------------------------------------------------------------

export const egresoDesdeApi = (registro) => ({
  id: registro.id,
  fecha: registro.fecha,
  concepto: registro.concepto,
  beneficiario: registro.beneficiario,
  monto: numero(registro.monto),
  formaPago: registro.forma_pago,
  referencia: registro.referencia ?? '',
  gastoId: registro.gasto_id,
  estado: registro.estado,
  observacion: registro.observacion ?? '',
});

export const egresoHaciaApi = (egreso) => ({
  fecha: egreso.fecha || null,
  concepto: egreso.concepto,
  beneficiario: egreso.beneficiario || '',
  monto: String(egreso.monto ?? '0'),
  forma_pago: egreso.formaPago ?? 'Efectivo',
  cuenta_id: egreso.cuentaId ? Number(egreso.cuentaId) : null,
  referencia: egreso.referencia || null,
  gasto_id: egreso.gastoId ? Number(egreso.gastoId) : null,
  observacion: egreso.observacion || null,
});

export const crearEgreso = (egreso) => api.crear('/egresos', egresoHaciaApi(egreso));
export const anularEgreso = (id) => api.crear(`/egresos/${id}/anular`);

export const cargarResumenEgresos = (desde, hasta, opciones) =>
  api.obtener('/egresos/resumen/periodo', { desde, hasta }, opciones);

// --------------------------------------------------------------------------
// Anticipos
// --------------------------------------------------------------------------

export const anticipoDesdeApi = (registro) => ({
  id: registro.id,
  fecha: registro.fecha,
  tipo: registro.tipo,
  receptor: registro.receptor_razon_social,
  detalle: registro.detalle,
  monto: numero(registro.monto),
  facturado: numero(registro.facturado),
  saldo: numero(registro.saldo),
  formaPago: registro.forma_pago,
  estado: registro.estado,
});

export const anticipoHaciaApi = (anticipo, receptorId) => ({
  fecha: anticipo.fecha || null,
  tipo: anticipo.tipo ?? 'ARD',
  receptor_id: receptorId,
  detalle: anticipo.detalle || '',
  monto: String(anticipo.monto ?? '0'),
  forma_pago: anticipo.formaPago ?? 'Transferencia',
});

export const crearAnticipo = (anticipo, receptorId) =>
  api.crear('/anticipos', anticipoHaciaApi(anticipo, receptorId));
export const aplicarAnticipo = (id, monto) =>
  api.crear(`/anticipos/${id}/aplicar`, { monto: String(monto) });
export const anularAnticipo = (id) => api.crear(`/anticipos/${id}/anular`);
export const eliminarAnticipo = (id) => api.eliminar(`/anticipos/${id}`);

// --------------------------------------------------------------------------
// Facturación recurrente
// --------------------------------------------------------------------------

export const plantillaDesdeApi = (registro) => ({
  id: registro.id,
  nombre: registro.nombre,
  receptor: registro.receptor_razon_social,
  periodicidad: registro.periodicidad,
  proximaEmision: registro.proxima_emision,
  ultimaEmision: registro.ultima_emision,
  hasta: registro.hasta,
  total: numero(registro.total),
  emitidas: registro.emitidas,
  activa: registro.activa,
  lineas: (registro.lineas ?? []).map((linea) => ({
    id: linea.id,
    codigo: linea.codigo_principal,
    descripcion: linea.descripcion,
    cantidad: numero(linea.cantidad),
    precioUnitario: numero(linea.precio_unitario),
    codigoIva: linea.codigo_iva,
  })),
});

export const plantillaHaciaApi = (plantilla, receptorId, lineas) => ({
  nombre: plantilla.nombre,
  receptor_id: receptorId,
  periodicidad: plantilla.periodicidad ?? 'Mensual',
  proxima_emision: plantilla.proximaEmision,
  hasta: plantilla.hasta || null,
  establecimiento: '001',
  punto_emision: '001',
  forma_pago: plantilla.formaPago ?? '01',
  activa: plantilla.activa ?? true,
  lineas: lineas.map((linea) => ({
    codigo_principal: linea.codigo || 'SIN-COD',
    descripcion: linea.descripcion,
    cantidad: String(linea.cantidad ?? '1'),
    precio_unitario: String(linea.precioUnitario ?? '0'),
    descuento_porcentaje: String(linea.descuentoPorcentaje ?? '0'),
    codigo_iva: linea.codigoIva ?? '4',
  })),
});

export const crearPlantilla = (plantilla, receptorId, lineas) =>
  api.crear('/recurrentes', plantillaHaciaApi(plantilla, receptorId, lineas));
export const actualizarPlantilla = (id, plantilla, receptorId, lineas) =>
  api.actualizar(`/recurrentes/${id}`, plantillaHaciaApi(plantilla, receptorId, lineas));
export const pausarPlantilla = (id) => api.crear(`/recurrentes/${id}/pausar`);
export const emitirPlantilla = (id) => api.crear(`/recurrentes/${id}/emitir`);
export const eliminarPlantilla = (id) => api.eliminar(`/recurrentes/${id}`);
export const cargarVencidas = (opciones) =>
  api.obtener('/recurrentes/vencidas', undefined, opciones);
