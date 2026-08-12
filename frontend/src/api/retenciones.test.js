import { describe, expect, it } from 'vitest';
import {
  ACCIONES_RETENCION,
  DOCUMENTOS_SUSTENTO,
  IMPUESTOS_RETENCION,
  retencionDesdeApi,
  retencionHaciaApi,
} from './retenciones.js';

describe('retencionHaciaApi', () => {
  const retencion = {
    fechaEmision: '2026-08-09',
    periodoFiscal: '08/2026',
    codDocSustento: '01',
    numDocSustento: '001-001-000000123',
    fechaDocSustento: '2026-08-05',
  };

  const lineas = [
    { codigoImpuesto: '1', codigoRetencion: '312', baseImponible: '1000', porcentaje: '2' },
    { codigoImpuesto: '2', codigoRetencion: '1', baseImponible: '150', porcentaje: '30' },
  ];

  it('arma el cuerpo con la cabecera y las líneas', () => {
    const cuerpo = retencionHaciaApi(retencion, 5, lineas);

    expect(cuerpo.sujeto_id).toBe(5);
    expect(cuerpo.periodo_fiscal).toBe('08/2026');
    expect(cuerpo.num_doc_sustento).toBe('001-001-000000123');
    expect(cuerpo.detalles).toHaveLength(2);
    expect(cuerpo.detalles[0]).toEqual({
      codigo_impuesto: '1',
      codigo_retencion: '312',
      base_imponible: '1000',
      porcentaje_retener: '2',
    });
  });

  it('manda los importes como texto', () => {
    const cuerpo = retencionHaciaApi(retencion, 5, [
      { codigoImpuesto: '1', codigoRetencion: '303', baseImponible: 1000, porcentaje: 10 },
    ]);

    expect(cuerpo.detalles[0].base_imponible).toBe('1000');
    expect(cuerpo.detalles[0].porcentaje_retener).toBe('10');
  });

  it('deja que el backend deduzca el período si no se indicó', () => {
    const cuerpo = retencionHaciaApi({ ...retencion, periodoFiscal: '' }, 5, lineas);
    expect(cuerpo.periodo_fiscal).toBeNull();
  });

  it('aplica "0" a los campos de línea ausentes', () => {
    const cuerpo = retencionHaciaApi(retencion, 5, [
      { codigoImpuesto: '1', codigoRetencion: '343' },
    ]);

    expect(cuerpo.detalles[0].base_imponible).toBe('0');
    expect(cuerpo.detalles[0].porcentaje_retener).toBe('0');
  });
});

describe('retencionDesdeApi', () => {
  it('resume la retención para el listado', () => {
    const resumen = retencionDesdeApi({
      id: 3,
      numero: '001-001-000000003',
      clave_acceso: '7'.repeat(49),
      numero_autorizacion: '5566778899',
      sujeto_razon_social: 'PROVEEDOR DEMO S.A.',
      sujeto_identificacion: '0992339411001',
      fecha_emision: '2026-08-09',
      periodo_fiscal: '08/2026',
      num_doc_sustento: '001-001-000000123',
      total_retenido: '62.500000',
      detalles: [{}, {}],
      estado_sri: 'Autorizado',
    });

    expect(resumen.proveedor).toBe('PROVEEDOR DEMO S.A.');
    expect(resumen.total).toBe(62.5);
    expect(resumen.lineas).toBe(2);
    expect(resumen.claveAcceso).toHaveLength(49);
    expect(resumen.numeroAutorizacion).toBe('5566778899');
  });

  it('cuenta cero líneas si el API no las envió', () => {
    expect(retencionDesdeApi({ detalles: undefined }).lineas).toBe(0);
  });
});

describe('catálogos de la interfaz', () => {
  it('los impuestos son los códigos 1, 2 y 6 de la tabla 20', () => {
    expect(IMPUESTOS_RETENCION.map((i) => i.codigo)).toEqual(['1', '2', '6']);
  });

  it('los documentos sustento llevan el código de dos dígitos del SRI', () => {
    for (const documento of DOCUMENTOS_SUSTENTO) {
      expect(documento.codigo).toMatch(/^\d{2}$/);
    }
    expect(DOCUMENTOS_SUSTENTO.map((d) => d.codigo)).toContain('01');
  });
});

describe('ACCIONES_RETENCION', () => {
  it('apunta a las rutas de retención, no a las de comprobante', () => {
    // Copiar el juego de acciones de otro documento y olvidar cambiar la ruta
    // descargaría el RIDE equivocado sin dar ningún error.
    expect(ACCIONES_RETENCION.urlRide(3)).toContain('/retenciones/3/ride');
    expect(ACCIONES_RETENCION.urlXml(3)).toContain('/retenciones/3/xml');
  });

  it('expone emitir y consultar', () => {
    expect(typeof ACCIONES_RETENCION.emitir).toBe('function');
    expect(typeof ACCIONES_RETENCION.consultar).toBe('function');
  });
});
