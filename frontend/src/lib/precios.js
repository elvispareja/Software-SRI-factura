/**
 * Cálculo de precios de venta a partir del costo.
 *
 * Distingue dos cosas que suelen confundirse y descuadran los precios:
 *
 *   - MARKUP (utilidad sobre el costo):  precio = costo × (1 + p/100)
 *     Costo 10 con 50% → precio 15. Es lo que la gente suele llamar "utilidad".
 *
 *   - MARGEN (utilidad sobre la venta):  precio = costo ÷ (1 − p/100)
 *     Costo 10 con 50% → precio 20. Es el margen contable.
 *
 * Un 50% significa precios muy distintos según la base, por eso el formulario
 * obliga a elegir cuál se está usando en vez de asumirlo.
 */

import { redondear, aNumero } from './sri/calculoComprobante.js';

export const BASES_UTILIDAD = [
  { id: 'costo', etiqueta: '% sobre el costo', descripcion: 'Markup. Costo 10 + 50% = 15.00' },
  { id: 'venta', etiqueta: '% sobre la venta', descripcion: 'Margen. Costo 10 con 50% = 20.00' },
];

/** Precio sin impuesto a partir del costo y el porcentaje de utilidad. */
export function precioDesdeUtilidad(costo, porcentaje, base = 'costo') {
  const costoNumerico = Math.max(aNumero(costo), 0);
  const utilidad = aNumero(porcentaje);

  if (base === 'venta') {
    // Un 100% de margen sobre la venta es imposible: el precio tendería a infinito.
    if (utilidad >= 100) return 0;
    return redondear(costoNumerico / (1 - utilidad / 100));
  }

  return redondear(costoNumerico * (1 + utilidad / 100));
}

/** Porcentaje de utilidad implícito en un precio dado. */
export function utilidadDesdePrecio(costo, precio, base = 'costo') {
  const costoNumerico = Math.max(aNumero(costo), 0);
  const precioNumerico = Math.max(aNumero(precio), 0);

  if (base === 'venta') {
    if (precioNumerico === 0) return 0;
    return redondear(((precioNumerico - costoNumerico) / precioNumerico) * 100);
  }

  if (costoNumerico === 0) return 0;
  return redondear(((precioNumerico - costoNumerico) / costoNumerico) * 100);
}

/** Precio final que ve el cliente, con el IVA aplicado. */
export function precioConImpuesto(precioSinImpuesto, tarifa) {
  return redondear(aNumero(precioSinImpuesto) * (1 + aNumero(tarifa) / 100));
}

/** Ganancia absoluta por unidad. */
export function utilidadUnitaria(costo, precioSinImpuesto) {
  return redondear(aNumero(precioSinImpuesto) - aNumero(costo));
}

/**
 * Semáforo de inventario a partir de los umbrales configurados.
 * Devuelve null cuando el artículo no maneja stock (servicios).
 */
export function estadoStock({ stock, stockMinimo, puntoReorden }) {
  if (stock === null || stock === undefined || stock === '') return null;

  const actual = aNumero(stock);
  const minimo = aNumero(stockMinimo);
  const reorden = aNumero(puntoReorden);

  if (actual <= 0) return { nivel: 'agotado', mensaje: 'Sin existencias' };
  if (actual <= minimo) return { nivel: 'critico', mensaje: 'Bajo el stock mínimo' };
  if (reorden > 0 && actual <= reorden) return { nivel: 'reorden', mensaje: 'Toca reponer' };
  return { nivel: 'ok', mensaje: 'Existencias suficientes' };
}
