import { describe, expect, it } from 'vitest';
import {
  ESTADOS_CONSULTABLES,
  ESTADOS_EMITIBLES,
  TIPOS,
  documentoDesdeApi,
  documentoHaciaApi,
  guiaDesdeApi,
  guiaHaciaApi,
} from './documentos.js';

/**
 * Lo que arman estas funciones es literalmente el cuerpo que termina en el XML
 * del SRI. Un campo omitido aquí es un rechazo en recepción.
 */

describe('documentoHaciaApi', () => {
  const base = {
    tipo: TIPOS.FACTURA,
    receptorId: 4,
    lineas: [
      {
        codigo: 'P-001',
        descripcion: 'Laptop',
        cantidad: 2,
        precioUnitario: 1200,
        descuentoPorcentaje: 10,
        codigoIva: '4',
      },
    ],
  };

  it('traduce cabecera y detalles al contrato del API', () => {
    const cuerpo = documentoHaciaApi(base);

    expect(cuerpo.tipo).toBe('Factura');
    expect(cuerpo.receptor_id).toBe(4);
    expect(cuerpo.establecimiento).toBe('001');
    expect(cuerpo.punto_emision).toBe('001');
    expect(cuerpo.detalles[0]).toEqual({
      codigo_principal: 'P-001',
      descripcion: 'Laptop',
      cantidad: '2',
      precio_unitario: '1200',
      descuento_porcentaje: '10',
      codigo_iva: '4',
    });
  });

  it('manda los importes como texto para no perder precisión', () => {
    // El backend los recibe en Decimal; un float de JS ya vendría redondeado
    // en binario y podría descuadrar el total del XML.
    const cuerpo = documentoHaciaApi(base);

    expect(typeof cuerpo.detalles[0].cantidad).toBe('string');
    expect(typeof cuerpo.detalles[0].precio_unitario).toBe('string');
  });

  it('pone un código de relleno cuando la línea es libre', () => {
    // El SRI exige `codigoPrincipal`; una línea escrita a mano no lo tiene.
    const cuerpo = documentoHaciaApi({
      ...base,
      lineas: [{ descripcion: 'Servicio puntual', cantidad: 1, precioUnitario: 50 }],
    });

    expect(cuerpo.detalles[0].codigo_principal).toBe('SIN-COD');
  });

  it('aplica los valores por defecto de una línea incompleta', () => {
    const cuerpo = documentoHaciaApi({
      ...base,
      lineas: [{ codigo: 'X', descripcion: 'Algo' }],
    });

    expect(cuerpo.detalles[0].cantidad).toBe('1');
    expect(cuerpo.detalles[0].precio_unitario).toBe('0');
    expect(cuerpo.detalles[0].descuento_porcentaje).toBe('0');
    expect(cuerpo.detalles[0].codigo_iva).toBe('4');
  });

  it('solo incluye validez_dias en las cotizaciones', () => {
    expect(documentoHaciaApi(base)).not.toHaveProperty('validez_dias');
    expect(documentoHaciaApi({ ...base, validezDias: '15' }).validez_dias).toBe(15);
  });

  it('solo incluye el documento modificado en notas de crédito y débito', () => {
    expect(documentoHaciaApi(base)).not.toHaveProperty('num_doc_modificado');

    const cuerpo = documentoHaciaApi({
      ...base,
      tipo: TIPOS.NOTA_CREDITO,
      documentoModificado: {
        numero: '001-001-000000123',
        fecha: '2026-08-01',
        motivo: 'Devolución',
      },
    });

    expect(cuerpo.cod_doc_modificado).toBe('01');
    expect(cuerpo.num_doc_modificado).toBe('001-001-000000123');
    expect(cuerpo.fecha_doc_modificado).toBe('2026-08-01');
    expect(cuerpo.motivo).toBe('Devolución');
  });
});

describe('documentoDesdeApi', () => {
  it('convierte el importe a número y expone el estado SRI dos veces', () => {
    // `estado` lo usa el filtro genérico de los listados y `estadoSRI` las
    // acciones; se mantienen ambos a propósito.
    const documento = documentoDesdeApi({
      id: 1,
      numero: '001-001-000000001',
      tipo: 'Factura',
      receptor_razon_social: 'CLIENTE',
      receptor_identificacion: '1710034065',
      fecha_emision: '2026-08-09',
      importe_total: '230.000000',
      metodo: 'Contado',
      estado_sri: 'Autorizado',
      estado_pago: 'Pagado',
    });

    expect(documento.total).toBe(230);
    expect(documento.estado).toBe('Autorizado');
    expect(documento.estadoSRI).toBe('Autorizado');
  });
});

describe('guiaHaciaApi', () => {
  const guia = {
    fechaInicio: '2026-08-09',
    fechaFin: '',
    motivo: 'Venta',
    ruta: '',
    tipoTransporte: 'Privado',
    documentoAduanero: '',
    placa: 'PBA1234',
    provinciaPartida: 'Pichincha',
    cantonPartida: 'Quito',
    direccionPartida: 'Bodega Norte',
    provinciaLlegada: '',
    cantonLlegada: '',
    direccionLlegada: 'Km 14.5 vía Daule',
  };

  it('manda null en los opcionales vacíos', () => {
    const cuerpo = guiaHaciaApi(guia, 9, [{ codigo: 'P-001', descripcion: 'Laptop', cantidad: 2 }]);

    expect(cuerpo.fecha_fin).toBeNull();
    expect(cuerpo.ruta).toBeNull();
    expect(cuerpo.documento_aduanero).toBeNull();
    expect(cuerpo.provincia_llegada).toBeNull();
  });

  it('conserva los datos obligatorios del traslado', () => {
    const cuerpo = guiaHaciaApi(guia, 9, [{ codigo: 'P-001', descripcion: 'Laptop', cantidad: 2 }]);

    expect(cuerpo.transportista_id).toBe(9);
    expect(cuerpo.placa).toBe('PBA1234');
    expect(cuerpo.fecha_inicio).toBe('2026-08-09');
    expect(cuerpo.direccion_partida).toBe('Bodega Norte');
    expect(cuerpo.direccion_llegada).toBe('Km 14.5 vía Daule');
    expect(cuerpo.items).toEqual([
      { codigo: 'P-001', descripcion: 'Laptop', cantidad: '2' },
    ]);
  });

  it('acepta ítems sin código', () => {
    const cuerpo = guiaHaciaApi(guia, 9, [{ descripcion: 'Bulto suelto' }]);

    expect(cuerpo.items[0].codigo).toBe('');
    expect(cuerpo.items[0].cantidad).toBe('1');
  });
});

describe('guiaDesdeApi', () => {
  it('resume la guía para el listado', () => {
    const resumen = guiaDesdeApi({
      id: 2,
      numero: '001-001-000000002',
      transportista_razon_social: 'TRANSPORTES DEL SUR',
      transportista_identificacion: '0992339411001',
      placa: 'PBA1234',
      fecha_inicio: '2026-08-09',
      fecha_fin: '2026-08-10',
      motivo_traslado: 'Venta',
      direccion_llegada: 'Guayaquil',
      items: [{}, {}, {}],
      estado_sri: 'Autorizado',
    });

    expect(resumen.transportista).toBe('TRANSPORTES DEL SUR');
    expect(resumen.items).toBe(3);
    expect(resumen.destino).toBe('Guayaquil');
  });

  it('cuenta cero ítems si el API no los envió', () => {
    expect(guiaDesdeApi({ items: undefined }).items).toBe(0);
  });
});

describe('estados del ciclo SRI', () => {
  it('solo se (re)emite desde estados no autorizados', () => {
    expect([...ESTADOS_EMITIBLES].sort()).toEqual(
      ['Borrador', 'Devuelto', 'Error', 'Rechazado'].sort(),
    );
    // Reenviar un autorizado da "CLAVE ACCESO REGISTRADA" y perdería el número.
    expect(ESTADOS_EMITIBLES.has('Autorizado')).toBe(false);
  });

  it('solo se reconsulta lo que el SRI ya recibió', () => {
    expect(ESTADOS_CONSULTABLES.has('Pendiente')).toBe(true);
    expect(ESTADOS_CONSULTABLES.has('Borrador')).toBe(false);
    expect(ESTADOS_CONSULTABLES.has('Autorizado')).toBe(false);
  });
});
