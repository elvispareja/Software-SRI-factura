import { describe, expect, it } from 'vitest';
import {
  MESES,
  MESES_CORTOS,
  ivaDesdeApi,
  panelDesdeApi,
  resumenDesdeApi,
  retencionesDesdeApi,
  urlCsv,
  urlPdf,
} from './reportes.js';

/**
 * Los adaptadores de reportes convierten importes que el API manda como texto
 * (`Decimal` serializado). Sin la conversión, `"1150.00" + 0` sería
 * `"1150.000"` en cualquier suma de la interfaz.
 */

describe('resumenDesdeApi', () => {
  it('convierte los importes a número', () => {
    const resumen = resumenDesdeApi({
      desde: '2026-08-01',
      hasta: '2026-08-31',
      comprobantes: 3,
      subtotal: '2100.000000',
      descuento: '0.000000',
      iva: '285.000000',
      total: '2385.000000',
      ticket_promedio: '795.000000',
    });

    expect(resumen.total).toBe(2385);
    expect(resumen.iva).toBe(285);
    expect(resumen.ticketPromedio).toBe(795);
    expect(typeof resumen.total).toBe('number');
  });

  it('trata los ausentes como cero, no como NaN', () => {
    const resumen = resumenDesdeApi({ comprobantes: 0 });

    expect(resumen.total).toBe(0);
    expect(resumen.ticketPromedio).toBe(0);
    expect(Number.isNaN(resumen.total)).toBe(false);
  });
});

describe('panelDesdeApi', () => {
  const PANEL = {
    hoy: '2026-08-09',
    mes: { comprobantes: 3, total: '2385.00', iva: '285.00', ticket_promedio: '795.00' },
    anio: { comprobantes: 4, total: '2730.00', iva: '330.00', ticket_promedio: '682.50' },
    por_tipo: [{ tipo: 'Factura', cantidad: 4, total: '2730.00' }],
    serie_mensual: [
      { mes: 1, cantidad: 0, total: '0.00' },
      { mes: 8, cantidad: 3, total: '2385.00' },
    ],
    top_clientes: [
      {
        razon_social: 'BETA CIA. LTDA.',
        identificacion: '0992339411001',
        comprobantes: 2,
        total: '1235.00',
      },
    ],
    top_articulos: [
      { codigo: 'PROD-001', descripcion: 'Laptop', cantidad: '2.000000', total: '1500.00' },
    ],
    estado_sri: {
      por_estado: [{ estado: 'Autorizado', cantidad: 3 }],
      total: 6,
      requieren_atencion: 2,
    },
    por_cobrar: { comprobantes: 1, total: '460.00', a_credito: '460.00' },
  };

  it('traduce el panel completo a camelCase', () => {
    const panel = panelDesdeApi(PANEL);

    expect(panel.mes.total).toBe(2385);
    expect(panel.anio.comprobantes).toBe(4);
    expect(panel.topClientes[0].razonSocial).toBe('BETA CIA. LTDA.');
    expect(panel.topArticulos[0].cantidad).toBe(2);
    expect(panel.estadoSri.requierenAtencion).toBe(2);
    expect(panel.porCobrar.aCredito).toBe(460);
  });

  it('etiqueta cada mes de la serie para el eje de la gráfica', () => {
    const panel = panelDesdeApi(PANEL);

    expect(panel.serieMensual[0].etiqueta).toBe('Ene');
    expect(panel.serieMensual[1].etiqueta).toBe('Ago');
  });

  it('no explota si el API omite secciones', () => {
    // Un panel a medias no debe tumbar la pantalla de inicio.
    const panel = panelDesdeApi({ mes: {}, anio: {} });

    expect(panel.porTipo).toEqual([]);
    expect(panel.topClientes).toEqual([]);
    expect(panel.estadoSri.requierenAtencion).toBe(0);
    expect(panel.porCobrar.total).toBe(0);
  });
});

describe('ivaDesdeApi', () => {
  it('convierte tarifas e importes', () => {
    const reporte = ivaDesdeApi({
      periodo_fiscal: '08/2026',
      tarifas: [
        { codigo_iva: '4', porcentaje: '15', base_imponible: '1500.00', valor_iva: '225.00' },
        { codigo_iva: '0', porcentaje: '0', base_imponible: '200.00', valor_iva: '0.00' },
      ],
      base_total: '1700.00',
      iva_total: '225.00',
    });

    expect(reporte.periodoFiscal).toBe('08/2026');
    expect(reporte.tarifas[0].porcentaje).toBe(15);
    expect(reporte.tarifas[0].valorIva).toBe(225);
    expect(reporte.baseTotal).toBe(1700);
  });

  it('devuelve lista vacía si no hubo ventas', () => {
    const reporte = ivaDesdeApi({ periodo_fiscal: '01/2026', tarifas: [] });

    expect(reporte.tarifas).toEqual([]);
    expect(reporte.ivaTotal).toBe(0);
  });
});

describe('retencionesDesdeApi', () => {
  it('separa lo retenido de renta y de IVA', () => {
    const reporte = retencionesDesdeApi({
      periodo_fiscal: '08/2026',
      comprobantes: 1,
      conceptos: [
        {
          codigo_impuesto: '1',
          codigo_retencion: '312',
          lineas: 1,
          base_imponible: '1000.00',
          valor_retenido: '20.00',
        },
      ],
      total_renta: '20.00',
      total_iva: '45.00',
      total_retenido: '65.00',
    });

    expect(reporte.totalRenta).toBe(20);
    expect(reporte.totalIva).toBe(45);
    expect(reporte.totalRetenido).toBe(65);
    expect(reporte.conceptos[0].codigoRetencion).toBe('312');
  });
});

describe('catálogo de meses', () => {
  it('tiene los doce en orden', () => {
    expect(MESES).toHaveLength(12);
    expect(MESES[0]).toBe('Enero');
    expect(MESES[11]).toBe('Diciembre');
  });

  it('las etiquetas cortas son de tres letras', () => {
    expect(MESES_CORTOS).toHaveLength(12);
    expect(MESES_CORTOS.every((mes) => mes.length === 3)).toBe(true);
  });
});

describe('urlCsv', () => {
  it('arma la URL del reporte con su período', () => {
    const url = urlCsv('iva', 2026, 8);

    expect(url).toContain('/reportes/iva/csv');
    expect(url).toContain('anio=2026');
    expect(url).toContain('mes=8');
  });

  it('omite el mes cuando el reporte es anual', () => {
    const url = urlCsv('ventas', 2026);

    expect(url).toContain('anio=2026');
    expect(url).not.toContain('mes=');
  });

  it('no manda período en los reportes que no lo tienen', () => {
    // El inventario es una foto del estado actual: `anio=undefined` sería un 422.
    const url = urlCsv('inventario');

    expect(url).toContain('/reportes/inventario/csv');
    expect(url).not.toContain('?');
  });
});

describe('urlPdf', () => {
  it('apunta al mismo reporte pero en PDF', () => {
    const url = urlPdf('iva', 2026, 8);

    expect(url).toContain('/reportes/iva/pdf');
    expect(url).toContain('anio=2026');
    expect(url).toContain('mes=8');
  });

  it('sirve reportes que no tienen CSV', () => {
    // Notas de venta y cotizaciones solo existen en PDF en el backend.
    expect(urlPdf('notas-venta', 2026, 8)).toContain('/reportes/notas-venta/pdf');
    expect(urlPdf('cotizaciones', 2026, 8)).toContain('/reportes/cotizaciones/pdf');
    expect(urlPdf('estado-sri', 2026, 8)).toContain('/reportes/estado-sri/pdf');
  });

  it('comparte el armado de parámetros con urlCsv', () => {
    expect(urlPdf('ventas', 2026)).toBe(urlCsv('ventas', 2026).replace('/csv', '/pdf'));
    expect(urlPdf('receptores')).not.toContain('?');
  });
});
