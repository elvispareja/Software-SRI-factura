/**
 * Liquidaciones de compra y guías de remisión de demostración.
 *
 * Ambas son comprobantes electrónicos con ciclo SRI, por eso llevan `estadoSRI`
 * igual que las facturas. La guía no tiene importe: no documenta una venta,
 * sino un traslado.
 */

export const ESTADOS_SRI = ['Autorizado', 'Pendiente', 'Rechazado', 'Anulado'];
export const MOTIVOS_TRASLADO = ['Venta', 'Compra', 'Traslado entre bodegas', 'Devolución'];

export const LIQUIDACIONES = [
  { id: 1, numero: '001-001-000000021', cliente: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', fecha: '2026-08-06', total: 1840.0, metodo: 'Crédito', estado: 'Autorizado' },
  { id: 2, numero: '001-001-000000020', cliente: 'IMPORTADORA AUSTRAL S.A.', fecha: '2026-08-04', total: 620.5, metodo: 'Contado', estado: 'Autorizado' },
  { id: 3, numero: '001-001-000000019', cliente: 'IMPRENTA GRÁFICA CENTRAL', fecha: '2026-08-01', total: 310.0, metodo: 'Contado', estado: 'Pendiente' },
  { id: 4, numero: '001-001-000000018', cliente: 'GLOBAL SUPPLIES LLC', fecha: '2026-07-29', total: 4250.75, metodo: 'Crédito', estado: 'Autorizado' },
  { id: 5, numero: '001-001-000000017', cliente: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', fecha: '2026-07-25', total: 980.0, metodo: 'Crédito', estado: 'Rechazado' },
  { id: 6, numero: '001-001-000000016', cliente: 'IMPORTADORA AUSTRAL S.A.', fecha: '2026-07-22', total: 155.4, metodo: 'Contado', estado: 'Autorizado' },
  { id: 7, numero: '001-001-000000015', cliente: 'IMPRENTA GRÁFICA CENTRAL', fecha: '2026-07-18', total: 725.0, metodo: 'Crédito', estado: 'Anulado' },
];

export const GUIAS_REMISION = [
  { id: 1, numero: '001-001-000000034', transportista: 'TRANSPORTES ANDINOS CÍA. LTDA.', placa: 'PBA-1234', fechaInicio: '2026-08-07', fechaFin: '2026-08-08', motivo: 'Venta', destino: 'Guayaquil', items: 12, estado: 'Autorizado' },
  { id: 2, numero: '001-001-000000033', transportista: 'LUIS MOROCHO', placa: 'TBC-5678', fechaInicio: '2026-08-05', fechaFin: '2026-08-05', motivo: 'Traslado entre bodegas', destino: 'Quito', items: 40, estado: 'Autorizado' },
  { id: 3, numero: '001-001-000000032', transportista: 'TRANSPORTES ANDINOS CÍA. LTDA.', placa: 'PBA-1234', fechaInicio: '2026-08-02', fechaFin: '2026-08-03', motivo: 'Venta', destino: 'Cuenca', items: 8, estado: 'Pendiente' },
  { id: 4, numero: '001-001-000000031', transportista: 'TRANSPORTES ANDINOS CÍA. LTDA.', placa: 'GSA-9012', fechaInicio: '2026-07-30', fechaFin: '2026-07-31', motivo: 'Devolución', destino: 'Ambato', items: 3, estado: 'Autorizado' },
  { id: 5, numero: '001-001-000000030', transportista: 'LUIS MOROCHO', placa: 'TBC-5678', fechaInicio: '2026-07-27', fechaFin: '2026-07-28', motivo: 'Compra', destino: 'Riobamba', items: 25, estado: 'Rechazado' },
  { id: 6, numero: '001-001-000000029', transportista: 'TRANSPORTES ANDINOS CÍA. LTDA.', placa: 'PBA-1234', fechaInicio: '2026-07-24', fechaFin: '2026-07-25', motivo: 'Venta', destino: 'Manta', items: 17, estado: 'Autorizado' },
];

export const RETENCIONES = [
  { id: 1, numero: '001-001-000000012', proveedor: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', identificacion: '0992339411001', fecha: '2026-08-06', periodo: '08/2026', sustento: '001-001-000000821', total: 62.5, lineas: 2, estado: 'Autorizado' },
  { id: 2, numero: '001-001-000000011', proveedor: 'IMPORTADORA AUSTRAL S.A.', identificacion: '0990304053001', fecha: '2026-08-04', periodo: '08/2026', sustento: '002-001-000004410', total: 18.9, lineas: 1, estado: 'Autorizado' },
  { id: 3, numero: '001-001-000000010', proveedor: 'IMPRENTA GRÁFICA CENTRAL', identificacion: '1791287541001', fecha: '2026-08-01', periodo: '08/2026', sustento: '001-002-000000155', total: 34.75, lineas: 2, estado: 'Pendiente' },
  { id: 4, numero: '001-001-000000009', proveedor: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', identificacion: '0992339411001', fecha: '2026-07-28', periodo: '07/2026', sustento: '001-001-000000790', total: 121.0, lineas: 3, estado: 'Autorizado' },
  { id: 5, numero: '001-001-000000008', proveedor: 'IMPORTADORA AUSTRAL S.A.', identificacion: '0990304053001', fecha: '2026-07-22', periodo: '07/2026', sustento: '002-001-000004302', total: 7.35, lineas: 1, estado: 'Rechazado' },
];

export const TONO_ESTADO_SRI = {
  Autorizado: 'success',
  Borrador: 'neutral',
  Pendiente: 'warning',
  Rechazado: 'error',
  // El SRI devuelve en recepción; es un rechazo temprano, no un estado final.
  Devuelto: 'error',
  Error: 'error',
  Anulado: 'neutral',
};
