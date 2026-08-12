/**
 * Cotizaciones y notas de venta de demostración.
 *
 * Ninguno de los dos es un comprobante electrónico con el mismo ciclo que la
 * factura: la cotización no va al SRI, y la nota de venta pertenece al régimen
 * RIMPE Negocio Popular. Por eso llevan estados propios y no `estadoSRI`.
 */

export const ESTADOS_COTIZACION = ['Pendiente', 'Aceptada', 'Rechazada', 'Vencida', 'Facturada'];
export const ESTADOS_NOTA_VENTA = ['Emitida', 'Anulada'];
export const METODOS_PAGO = ['Contado', 'Crédito'];

export const COTIZACIONES = [
  { id: 1, numero: 'COT-000000045', cliente: 'CORPORACIÓN FAVORITA C.A.', fecha: '2026-08-06', validez: 15, total: 3480.5, metodo: 'Crédito', estado: 'Pendiente' },
  { id: 2, numero: 'COT-000000044', cliente: 'MARÍA ANDRADE', fecha: '2026-08-05', validez: 8, total: 189.0, metodo: 'Contado', estado: 'Aceptada' },
  { id: 3, numero: 'COT-000000043', cliente: 'ASEGURADORA MITAD DEL MUNDO S.A.', fecha: '2026-08-03', validez: 30, total: 2100.0, metodo: 'Crédito', estado: 'Facturada' },
  { id: 4, numero: 'COT-000000042', cliente: 'CARLOS VILLACÍS', fecha: '2026-07-30', validez: 7, total: 76.4, metodo: 'Contado', estado: 'Vencida' },
  { id: 5, numero: 'COT-000000041', cliente: 'DISTRIBUIDORA ANDINA S.A.', fecha: '2026-07-28', validez: 15, total: 5240.0, metodo: 'Crédito', estado: 'Rechazada' },
  { id: 6, numero: 'COT-000000040', cliente: 'JUAN PÉREZ', fecha: '2026-07-26', validez: 10, total: 320.75, metodo: 'Contado', estado: 'Aceptada' },
  { id: 7, numero: 'COT-000000039', cliente: 'IMPORTADORA AUSTRAL S.A.', fecha: '2026-07-24', validez: 20, total: 1875.3, metodo: 'Crédito', estado: 'Pendiente' },
  { id: 8, numero: 'COT-000000038', cliente: 'JOHN SMITH', fecha: '2026-07-22', validez: 15, total: 640.0, metodo: 'Contado', estado: 'Facturada' },
  { id: 9, numero: 'COT-000000037', cliente: 'CORPORACIÓN FAVORITA C.A.', fecha: '2026-07-20', validez: 30, total: 9120.0, metodo: 'Crédito', estado: 'Pendiente' },
  { id: 10, numero: 'COT-000000036', cliente: 'MARÍA ANDRADE', fecha: '2026-07-18', validez: 7, total: 55.0, metodo: 'Contado', estado: 'Vencida' },
  { id: 11, numero: 'COT-000000035', cliente: 'CARLOS VILLACÍS', fecha: '2026-07-15', validez: 15, total: 1180.6, metodo: 'Crédito', estado: 'Aceptada' },
  { id: 12, numero: 'COT-000000034', cliente: 'DISTRIBUIDORA ANDINA S.A.', fecha: '2026-07-12', validez: 15, total: 430.9, metodo: 'Contado', estado: 'Facturada' },
];

export const NOTAS_VENTA = [
  { id: 1, numero: '001-001-000000078', cliente: 'CONSUMIDOR FINAL', fecha: '2026-08-07', total: 24.5, metodo: 'Contado', estado: 'Emitida' },
  { id: 2, numero: '001-001-000000077', cliente: 'JUAN PÉREZ', fecha: '2026-08-06', total: 18.0, metodo: 'Contado', estado: 'Emitida' },
  { id: 3, numero: '001-001-000000076', cliente: 'CONSUMIDOR FINAL', fecha: '2026-08-05', total: 7.4, metodo: 'Contado', estado: 'Emitida' },
  { id: 4, numero: '001-001-000000075', cliente: 'MARÍA ANDRADE', fecha: '2026-08-04', total: 45.0, metodo: 'Contado', estado: 'Anulada' },
  { id: 5, numero: '001-001-000000074', cliente: 'CONSUMIDOR FINAL', fecha: '2026-08-03', total: 12.85, metodo: 'Contado', estado: 'Emitida' },
  { id: 6, numero: '001-001-000000073', cliente: 'CARLOS VILLACÍS', fecha: '2026-08-01', total: 63.2, metodo: 'Crédito', estado: 'Emitida' },
  { id: 7, numero: '001-001-000000072', cliente: 'CONSUMIDOR FINAL', fecha: '2026-07-31', total: 9.9, metodo: 'Contado', estado: 'Emitida' },
  { id: 8, numero: '001-001-000000071', cliente: 'JUAN PÉREZ', fecha: '2026-07-29', total: 31.75, metodo: 'Contado', estado: 'Emitida' },
  { id: 9, numero: '001-001-000000070', cliente: 'CONSUMIDOR FINAL', fecha: '2026-07-27', total: 5.5, metodo: 'Contado', estado: 'Anulada' },
  { id: 10, numero: '001-001-000000069', cliente: 'MARÍA ANDRADE', fecha: '2026-07-25', total: 88.0, metodo: 'Contado', estado: 'Emitida' },
  { id: 11, numero: '001-001-000000068', cliente: 'CONSUMIDOR FINAL', fecha: '2026-07-23', total: 16.3, metodo: 'Contado', estado: 'Emitida' },
];

/** Tono del badge según el estado; se usa en los dos listados. */
export const TONO_ESTADO = {
  // Estados del ciclo SRI, que llegan del API
  Autorizado: 'success',
  Borrador: 'neutral',
  Rechazado: 'error',
  // Estados propios de cotizaciones y notas de venta
  Pendiente: 'warning',
  Aceptada: 'success',
  Facturada: 'success',
  Rechazada: 'error',
  Vencida: 'neutral',
  Emitida: 'success',
  Anulada: 'neutral',
};
