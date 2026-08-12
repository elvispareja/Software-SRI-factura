import { describe, expect, it } from 'vitest';
import {
  aNumero,
  calcularComprobante,
  calcularLinea,
  formatearMoneda,
  redondear,
  validarComprobante,
} from './calculoComprobante.js';

/**
 * El motor de cálculo es la pieza donde un error no se ve: produce un número
 * que no cuadra con el XML y el SRI rechaza el comprobante sin decir por qué.
 * De ahí que estas pruebas insistan tanto en los casos de frontera del redondeo.
 */

describe('redondear', () => {
  it('redondea "half away from zero", como espera el SRI', () => {
    expect(redondear(1.005)).toBe(1.01);
    expect(redondear(2.675)).toBe(2.68);
    expect(redondear(0.125)).toBe(0.13);
  });

  it('no cae en el error del escalado binario', () => {
    // `Math.round(1.005 * 100)` da 100 (→ 1.00), que es incorrecto.
    // Esta es la razón de que `redondear` use notación exponencial.
    expect(Math.round(1.005 * 100) / 100).toBe(1);
    expect(redondear(1.005)).toBe(1.01);
  });

  it('conserva el signo al redondear negativos', () => {
    expect(redondear(-1.005)).toBe(-1.01);
    expect(redondear(-2.344)).toBe(-2.34);
  });

  it('acepta otra cantidad de decimales', () => {
    expect(redondear(1.23456789, 6)).toBe(1.234568);
    expect(redondear(10.5, 0)).toBe(11);
  });

  it('devuelve 0 ante valores no finitos', () => {
    expect(redondear(NaN)).toBe(0);
    expect(redondear(Infinity)).toBe(0);
    expect(redondear(0)).toBe(0);
  });
});

describe('aNumero', () => {
  it('acepta la coma decimal que se teclea en Ecuador', () => {
    expect(aNumero('12,50')).toBe(12.5);
  });

  it('tolera espacios y cadenas vacías', () => {
    expect(aNumero('  8.25  ')).toBe(8.25);
    expect(aNumero('')).toBe(0);
    expect(aNumero('   ')).toBe(0);
  });

  it('devuelve 0 ante basura, en vez de NaN', () => {
    // Un NaN se propagaría por todo el cálculo y saldría en el XML.
    expect(aNumero('abc')).toBe(0);
    expect(aNumero(null)).toBe(0);
    expect(aNumero(undefined)).toBe(0);
    expect(aNumero({})).toBe(0);
    expect(aNumero(NaN)).toBe(0);
  });
});

describe('calcularLinea', () => {
  it('calcula base e IVA de una línea simple al 15%', () => {
    const linea = calcularLinea({
      cantidad: '2',
      precioUnitario: '100',
      codigoIva: '4',
    });

    expect(linea.bruto).toBe(200);
    expect(linea.descuento).toBe(0);
    expect(linea.baseImponible).toBe(200);
    expect(linea.valorIva).toBe(30);
    expect(linea.total).toBe(230);
  });

  it('aplica el IVA sobre la base ya descontada, no sobre el bruto', () => {
    const linea = calcularLinea({
      cantidad: '1',
      precioUnitario: '100',
      descuentoPorcentaje: '10',
      codigoIva: '4',
    });

    expect(linea.descuento).toBe(10);
    expect(linea.baseImponible).toBe(90);
    // 15% de 90, no de 100.
    expect(linea.valorIva).toBe(13.5);
    expect(linea.total).toBe(103.5);
  });

  it('no cobra IVA con tarifa 0%, exento o no objeto', () => {
    for (const codigo of ['0', '6', '7']) {
      const linea = calcularLinea({ cantidad: '1', precioUnitario: '50', codigoIva: codigo });
      expect(linea.valorIva).toBe(0);
      expect(linea.total).toBe(50);
    }
  });

  it('acota el descuento al rango 0–100', () => {
    const excesivo = calcularLinea({
      cantidad: '1',
      precioUnitario: '100',
      descuentoPorcentaje: '150',
    });
    expect(excesivo.descuentoPorcentaje).toBe(100);
    expect(excesivo.baseImponible).toBe(0);

    const negativo = calcularLinea({
      cantidad: '1',
      precioUnitario: '100',
      descuentoPorcentaje: '-20',
    });
    expect(negativo.descuentoPorcentaje).toBe(0);
    expect(negativo.baseImponible).toBe(100);
  });

  it('no admite cantidades ni precios negativos', () => {
    const linea = calcularLinea({ cantidad: '-5', precioUnitario: '-10' });
    expect(linea.cantidad).toBe(0);
    expect(linea.precioUnitario).toBe(0);
    expect(linea.total).toBe(0);
  });

  it('usa la tarifa por defecto cuando el código no existe', () => {
    const linea = calcularLinea({ cantidad: '1', precioUnitario: '100', codigoIva: 'zzz' });
    expect(linea.tarifa.codigo).toBe('4');
    expect(linea.valorIva).toBe(15);
  });

  it('admite hasta 6 decimales en la cantidad, como el XML', () => {
    const linea = calcularLinea({ cantidad: '1.2345678', precioUnitario: '10', codigoIva: '0' });
    expect(linea.cantidad).toBe(1.234568);
  });
});

describe('calcularComprobante', () => {
  it('agrupa las líneas por tarifa para el bloque totalConImpuestos', () => {
    const resultado = calcularComprobante([
      { cantidad: '1', precioUnitario: '100', codigoIva: '4' },
      { cantidad: '1', precioUnitario: '50', codigoIva: '4' },
      { cantidad: '1', precioUnitario: '20', codigoIva: '0' },
    ]);

    expect(resultado.impuestos).toHaveLength(2);

    const quince = resultado.impuestos.find((i) => i.codigoPorcentaje === '4');
    expect(quince.baseImponible).toBe(150);
    expect(quince.valor).toBe(22.5);

    const cero = resultado.impuestos.find((i) => i.codigoPorcentaje === '0');
    expect(cero.baseImponible).toBe(20);
    expect(cero.valor).toBe(0);
  });

  it('suma los totales del comprobante', () => {
    const resultado = calcularComprobante([
      { cantidad: '2', precioUnitario: '100', codigoIva: '4' },
      { cantidad: '1', precioUnitario: '30', codigoIva: '0' },
    ]);

    expect(resultado.totalSinImpuestos).toBe(230);
    expect(resultado.totalIva).toBe(30);
    expect(resultado.importeTotal).toBe(260);
  });

  it('acumula los descuentos de todas las líneas', () => {
    const resultado = calcularComprobante([
      { cantidad: '1', precioUnitario: '100', descuentoPorcentaje: '10', codigoIva: '0' },
      { cantidad: '1', precioUnitario: '200', descuentoPorcentaje: '25', codigoIva: '0' },
    ]);

    expect(resultado.totalDescuento).toBe(60);
    expect(resultado.totalSinImpuestos).toBe(240);
  });

  it('ordena las tarifas igual que el catálogo (15%, 5%, 0%)', () => {
    const resultado = calcularComprobante([
      { cantidad: '1', precioUnitario: '10', codigoIva: '0' },
      { cantidad: '1', precioUnitario: '10', codigoIva: '5' },
      { cantidad: '1', precioUnitario: '10', codigoIva: '4' },
    ]);

    expect(resultado.impuestos.map((i) => i.codigoPorcentaje)).toEqual(['4', '5', '0']);
  });

  it('devuelve un comprobante vacío coherente sin líneas', () => {
    const resultado = calcularComprobante([]);

    expect(resultado.detalles).toEqual([]);
    expect(resultado.impuestos).toEqual([]);
    expect(resultado.totalSinImpuestos).toBe(0);
    expect(resultado.importeTotal).toBe(0);
  });

  it('la suma de las líneas cuadra con el total, sin arrastre de redondeo', () => {
    // Tres céntimos que se redondean por separado: si el motor sumara en
    // bruto y redondeara solo al final, el XML no cuadraría.
    const lineas = Array.from({ length: 3 }, () => ({
      cantidad: '1',
      precioUnitario: '0.335',
      codigoIva: '4',
    }));
    const resultado = calcularComprobante(lineas);

    const sumaBases = resultado.detalles.reduce((t, d) => t + d.baseImponible, 0);
    expect(redondear(sumaBases)).toBe(resultado.totalSinImpuestos);
    expect(redondear(resultado.totalSinImpuestos + resultado.totalIva)).toBe(
      resultado.importeTotal,
    );
  });
});

describe('validarComprobante', () => {
  it('rechaza un comprobante sin líneas', () => {
    const resultado = validarComprobante(calcularComprobante([]));

    expect(resultado.esValido).toBe(false);
    expect(resultado.errores[0]).toMatch(/al menos un artículo/i);
  });

  it('avisa de líneas con cantidad en cero', () => {
    const resultado = validarComprobante(
      calcularComprobante([{ cantidad: '0', precioUnitario: '10' }]),
    );

    expect(resultado.esValido).toBe(false);
    expect(resultado.errores.some((e) => /cantidad en cero/i.test(e))).toBe(true);
  });

  it('avisa de líneas cuyo total quedó en cero por el descuento', () => {
    const resultado = validarComprobante(
      calcularComprobante([
        { cantidad: '1', precioUnitario: '100', descuentoPorcentaje: '100' },
      ]),
    );

    expect(resultado.esValido).toBe(false);
    expect(resultado.errores.some((e) => /total es cero/i.test(e))).toBe(true);
  });

  it('acepta un comprobante correcto', () => {
    const resultado = validarComprobante(
      calcularComprobante([{ cantidad: '1', precioUnitario: '100', codigoIva: '4' }]),
    );

    expect(resultado.esValido).toBe(true);
    expect(resultado.errores).toEqual([]);
  });
});

describe('formatearMoneda', () => {
  it('siempre muestra dos decimales', () => {
    // Se comprueban los dígitos y no el símbolo: el separador de miles y la
    // posición del "$" dependen de la implementación de Intl del entorno.
    expect(formatearMoneda(1234.5)).toMatch(/1.234[.,]50/);
    expect(formatearMoneda(0)).toMatch(/0[.,]00/);
  });

  it('no explota con entradas inválidas', () => {
    expect(formatearMoneda(null)).toMatch(/0[.,]00/);
    expect(formatearMoneda('abc')).toMatch(/0[.,]00/);
  });
});
