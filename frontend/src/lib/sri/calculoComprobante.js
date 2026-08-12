/**
 * Motor de cálculo de comprobantes electrónicos (SRI Ecuador).
 *
 * Funciones puras, sin React: las reutilizan Factura, Cotización, Nota de Venta
 * y Liquidación de Compra, y son la misma fuente de verdad que usará el backend
 * para armar el XML. Si un número aquí no cuadra con el XML, el SRI rechaza el
 * comprobante — por eso el redondeo se hace en cada paso y no solo al final.
 */

import { obtenerTarifaIva, ordenTarifa, CODIGO_IMPUESTO_IVA } from './impuestos.js';

export const DECIMALES_MONEDA = 2;
export const DECIMALES_CANTIDAD = 6;

/**
 * Redondeo "half away from zero" a N decimales, el que espera el SRI.
 *
 * Usa notación exponencial en vez de multiplicar por 10^n porque el escalado
 * binario falla en casos de frontera: `Math.round(1.005 * 100)` da 100 (→ 1.00)
 * cuando el resultado correcto es 1.01.
 */
export function redondear(valor, decimales = DECIMALES_MONEDA) {
  if (!Number.isFinite(valor)) return 0;
  if (valor === 0) return 0;

  const signo = valor < 0 ? -1 : 1;
  const absoluto = Math.abs(valor);

  const [mantisa, exponente = '0'] = absoluto.toExponential().split('e');
  const desplazado = Math.round(Number(`${mantisa}e${Number(exponente) + decimales}`));

  const [mantisaFinal, exponenteFinal = '0'] = desplazado.toExponential().split('e');
  return signo * Number(`${mantisaFinal}e${Number(exponenteFinal) - decimales}`);
}

/** Convierte a número tolerando strings de inputs, comas decimales y vacíos. */
export function aNumero(valor) {
  if (typeof valor === 'number') return Number.isFinite(valor) ? valor : 0;
  if (typeof valor !== 'string') return 0;

  const limpio = valor.trim().replace(',', '.');
  if (limpio === '') return 0;

  const numero = Number(limpio);
  return Number.isFinite(numero) ? numero : 0;
}

const acotar = (valor, minimo, maximo) => Math.min(Math.max(valor, minimo), maximo);

/**
 * Calcula una línea de detalle.
 *
 * `baseImponible` es el `precioTotalSinImpuesto` del XML: cantidad × precio
 * unitario menos el descuento, ya redondeado. El IVA se calcula sobre esa base,
 * nunca sobre el bruto.
 */
export function calcularLinea(linea) {
  const cantidad = redondear(Math.max(aNumero(linea.cantidad), 0), DECIMALES_CANTIDAD);
  const precioUnitario = redondear(Math.max(aNumero(linea.precioUnitario), 0), DECIMALES_CANTIDAD);
  const descuentoPorcentaje = acotar(aNumero(linea.descuentoPorcentaje), 0, 100);
  const tarifa = obtenerTarifaIva(linea.codigoIva);

  const bruto = redondear(cantidad * precioUnitario);
  const descuento = redondear((bruto * descuentoPorcentaje) / 100);
  const baseImponible = redondear(bruto - descuento);
  const valorIva = redondear((baseImponible * tarifa.porcentaje) / 100);

  return {
    ...linea,
    cantidad,
    precioUnitario,
    descuentoPorcentaje,
    tarifa,
    bruto,
    descuento,
    baseImponible,
    valorIva,
    total: redondear(baseImponible + valorIva),
  };
}

/**
 * Calcula el comprobante completo a partir de sus líneas.
 *
 * Devuelve el desglose por tarifa (lo que va en `totalConImpuestos`) además de
 * los totales, para que el resumen muestre solo las tarifas realmente usadas en
 * vez de un "Subtotal 15% / Subtotal 0%" fijo.
 */
export function calcularComprobante(lineas = []) {
  const detalles = lineas.map(calcularLinea);

  const grupos = new Map();
  for (const detalle of detalles) {
    const { codigo } = detalle.tarifa;
    const grupo = grupos.get(codigo) ?? {
      codigoImpuesto: CODIGO_IMPUESTO_IVA,
      codigoPorcentaje: codigo,
      tarifa: detalle.tarifa,
      baseImponible: 0,
      valor: 0,
    };

    grupo.baseImponible = redondear(grupo.baseImponible + detalle.baseImponible);
    grupo.valor = redondear(grupo.valor + detalle.valorIva);
    grupos.set(codigo, grupo);
  }

  const impuestos = [...grupos.values()].sort(
    (a, b) => ordenTarifa(a.codigoPorcentaje) - ordenTarifa(b.codigoPorcentaje),
  );

  const totalSinImpuestos = detalles.reduce(
    (acumulado, detalle) => redondear(acumulado + detalle.baseImponible),
    0,
  );
  const totalDescuento = detalles.reduce(
    (acumulado, detalle) => redondear(acumulado + detalle.descuento),
    0,
  );
  const totalIva = impuestos.reduce((acumulado, grupo) => redondear(acumulado + grupo.valor), 0);

  return {
    detalles,
    impuestos,
    totalSinImpuestos,
    totalDescuento,
    totalIva,
    importeTotal: redondear(totalSinImpuestos + totalIva),
  };
}

/**
 * Reglas mínimas que debe cumplir el comprobante antes de intentar emitirlo.
 * No reemplaza la validación del backend; evita viajes inútiles al SRI.
 */
export function validarComprobante(resultado) {
  const errores = [];

  if (resultado.detalles.length === 0) {
    errores.push('Agrega al menos un artículo o servicio al detalle.');
  }
  if (resultado.detalles.some((detalle) => detalle.cantidad <= 0)) {
    errores.push('Hay líneas con cantidad en cero. Corrígelas o elimínalas.');
  }
  if (resultado.detalles.some((detalle) => detalle.baseImponible <= 0 && detalle.cantidad > 0)) {
    errores.push('Hay líneas cuyo total es cero. Revisa el precio unitario o el descuento.');
  }

  return { esValido: errores.length === 0, errores };
}

const formateadorMoneda = new Intl.NumberFormat('es-EC', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: DECIMALES_MONEDA,
  maximumFractionDigits: DECIMALES_MONEDA,
});

export const formatearMoneda = (valor) => formateadorMoneda.format(aNumero(valor));
