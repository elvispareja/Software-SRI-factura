/**
 * Comprobantes emitidos de demostración.
 *
 * `estadoSRI` refleja el ciclo real del comprobante electrónico; `estadoPago`
 * es el estado interno del negocio y son independientes entre sí: una factura
 * autorizada por el SRI puede seguir pendiente de cobro.
 */

export const ESTADOS_SRI = ['Autorizado', 'Pendiente', 'Rechazado', 'Anulado'];
export const ESTADOS_PAGO = ['Cobrado', 'Por Cobrar', 'Anulado'];
export const METODOS_PAGO = ['Contado', 'Crédito'];
export const TIPOS_COMPROBANTE = ['Factura', 'Nota de Crédito', 'Nota de Débito', 'Retención'];

export const COMPROBANTES = [
  { id: 1, numero: '001-002-000000123', tipo: 'Factura', cliente: 'CORPORACIÓN FAVORITA C.A.', fecha: '2026-08-04', total: 1250.5, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 2, numero: '001-002-000000124', tipo: 'Factura', cliente: 'JUAN PÉREZ', fecha: '2026-08-04', total: 45.0, metodo: 'Contado', estadoSRI: 'Pendiente', estadoPago: 'Por Cobrar' },
  { id: 3, numero: '001-002-000000125', tipo: 'Factura', cliente: 'CONSUMIDOR FINAL', fecha: '2026-08-03', total: 12.0, metodo: 'Contado', estadoSRI: 'Rechazado', estadoPago: 'Por Cobrar' },
  { id: 4, numero: '001-002-000000126', tipo: 'Factura', cliente: 'DISTRIBUIDORA ANDINA S.A.', fecha: '2026-08-03', total: 3420.75, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Por Cobrar' },
  { id: 5, numero: '001-002-000000127', tipo: 'Factura', cliente: 'MARÍA ANDRADE', fecha: '2026-08-02', total: 189.0, metodo: 'Contado', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 6, numero: '001-001-000000045', tipo: 'Nota de Crédito', cliente: 'CORPORACIÓN FAVORITA C.A.', fecha: '2026-08-02', total: 125.05, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Anulado' },
  { id: 7, numero: '001-002-000000128', tipo: 'Factura', cliente: 'CARLOS VILLACÍS', fecha: '2026-08-01', total: 76.4, metodo: 'Contado', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 8, numero: '001-002-000000129', tipo: 'Factura', cliente: 'ASEGURADORA MITAD DEL MUNDO S.A.', fecha: '2026-08-01', total: 2100.0, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Por Cobrar' },
  { id: 9, numero: '001-002-000000130', tipo: 'Factura', cliente: 'JOHN SMITH', fecha: '2026-07-31', total: 320.0, metodo: 'Contado', estadoSRI: 'Anulado', estadoPago: 'Anulado' },
  { id: 10, numero: '001-003-000000012', tipo: 'Retención', cliente: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', fecha: '2026-07-31', total: 84.3, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 11, numero: '001-002-000000131', tipo: 'Factura', cliente: 'CONSUMIDOR FINAL', fecha: '2026-07-30', total: 8.5, metodo: 'Contado', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 12, numero: '001-002-000000132', tipo: 'Factura', cliente: 'CORPORACIÓN FAVORITA C.A.', fecha: '2026-07-30', total: 940.2, metodo: 'Crédito', estadoSRI: 'Pendiente', estadoPago: 'Por Cobrar' },
  { id: 13, numero: '001-001-000000046', tipo: 'Nota de Débito', cliente: 'DISTRIBUIDORA ANDINA S.A.', fecha: '2026-07-29', total: 45.9, metodo: 'Crédito', estadoSRI: 'Autorizado', estadoPago: 'Por Cobrar' },
  { id: 14, numero: '001-002-000000133', tipo: 'Factura', cliente: 'MARÍA ANDRADE', fecha: '2026-07-29', total: 55.0, metodo: 'Contado', estadoSRI: 'Autorizado', estadoPago: 'Cobrado' },
  { id: 15, numero: '001-002-000000134', tipo: 'Factura', cliente: 'CARLOS VILLACÍS', fecha: '2026-07-28', total: 1180.6, metodo: 'Crédito', estadoSRI: 'Rechazado', estadoPago: 'Por Cobrar' },
];

/** Contadores del encabezado del listado, derivados de los datos. */
export function resumirComprobantes(comprobantes) {
  const contar = (estado) => comprobantes.filter((c) => c.estadoSRI === estado).length;
  return {
    autorizados: contar('Autorizado'),
    pendientes: contar('Pendiente'),
    rechazados: contar('Rechazado'),
  };
}
