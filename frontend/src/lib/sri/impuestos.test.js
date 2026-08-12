import { describe, expect, it } from 'vitest';
import {
  CODIGO_IMPUESTO_IVA,
  TARIFAS_IVA,
  TARIFA_IVA_POR_DEFECTO,
  obtenerTarifaIva,
  ordenTarifa,
} from './impuestos.js';

/**
 * Los códigos de este catálogo viajan literalmente en el XML (tabla 17 de la
 * ficha técnica). Cambiarlos sin revisar la ficha hace que el SRI rechace el
 * comprobante, así que las pruebas los fijan explícitamente.
 */

describe('catálogo de tarifas', () => {
  it('el impuesto IVA es el código 2', () => {
    expect(CODIGO_IMPUESTO_IVA).toBe('2');
  });

  it('los códigos y porcentajes son los de la tabla 17', () => {
    const catalogo = Object.fromEntries(TARIFAS_IVA.map((t) => [t.codigo, t.porcentaje]));

    expect(catalogo).toEqual({
      4: 15, // IVA 15%
      5: 5, // IVA 5%
      0: 0, // IVA 0%
      6: 0, // No objeto de impuesto
      7: 0, // Exento
    });
  });

  it('no hay códigos repetidos', () => {
    const codigos = TARIFAS_IVA.map((t) => t.codigo);
    expect(new Set(codigos).size).toBe(codigos.length);
  });
});

describe('obtenerTarifaIva', () => {
  it('devuelve la tarifa pedida', () => {
    expect(obtenerTarifaIva('4').porcentaje).toBe(15);
    expect(obtenerTarifaIva('5').porcentaje).toBe(5);
  });

  it('acepta el código como número', () => {
    expect(obtenerTarifaIva(4).codigo).toBe('4');
  });

  it('cae en la tarifa por defecto ante un código desconocido', () => {
    // Preferible a devolver undefined: el cálculo seguiría con NaN.
    expect(obtenerTarifaIva('99').codigo).toBe(TARIFA_IVA_POR_DEFECTO);
    expect(obtenerTarifaIva(null).codigo).toBe(TARIFA_IVA_POR_DEFECTO);
    expect(obtenerTarifaIva(undefined).codigo).toBe(TARIFA_IVA_POR_DEFECTO);
  });
});

describe('ordenTarifa', () => {
  it('respeta el orden del catálogo', () => {
    expect(ordenTarifa('4')).toBeLessThan(ordenTarifa('5'));
    expect(ordenTarifa('5')).toBeLessThan(ordenTarifa('0'));
  });

  it('manda al final lo desconocido', () => {
    expect(ordenTarifa('zzz')).toBe(TARIFAS_IVA.length);
  });
});
