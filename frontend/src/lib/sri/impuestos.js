/**
 * Catálogo de tarifas de IVA del SRI.
 *
 * Los códigos corresponden a la tabla 17 de la Ficha Técnica de Comprobantes
 * Electrónicos (campo `codigoPorcentaje`, para el impuesto código 2 = IVA).
 * El `codigo` es el valor que viaja en el XML: no lo cambies sin revisar la ficha.
 */

export const CODIGO_IMPUESTO_IVA = '2';

export const TARIFAS_IVA = [
  { codigo: '4', nombre: 'IVA 15%', etiquetaCorta: '15%', porcentaje: 15 },
  { codigo: '5', nombre: 'IVA 5%', etiquetaCorta: '5%', porcentaje: 5 },
  { codigo: '0', nombre: 'IVA 0%', etiquetaCorta: '0%', porcentaje: 0 },
  { codigo: '6', nombre: 'No objeto de impuesto', etiquetaCorta: 'No objeto', porcentaje: 0 },
  { codigo: '7', nombre: 'Exento de IVA', etiquetaCorta: 'Exento', porcentaje: 0 },
];

export const TARIFA_IVA_POR_DEFECTO = '4';

const TARIFAS_POR_CODIGO = new Map(TARIFAS_IVA.map((tarifa) => [tarifa.codigo, tarifa]));

/** Devuelve la tarifa correspondiente al código, o la tarifa por defecto si no existe. */
export function obtenerTarifaIva(codigo) {
  return TARIFAS_POR_CODIGO.get(String(codigo)) ?? TARIFAS_POR_CODIGO.get(TARIFA_IVA_POR_DEFECTO);
}

/** Orden de presentación en el resumen de totales (mismo orden que TARIFAS_IVA). */
export function ordenTarifa(codigo) {
  const indice = TARIFAS_IVA.findIndex((tarifa) => tarifa.codigo === String(codigo));
  return indice === -1 ? TARIFAS_IVA.length : indice;
}
