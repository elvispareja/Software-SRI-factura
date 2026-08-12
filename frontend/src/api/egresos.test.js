import { describe, expect, it } from 'vitest';
import {
  ESTADOS_ANTICIPO,
  PERIODICIDADES,
  TIPOS_ANTICIPO,
  anticipoDesdeApi,
  anticipoHaciaApi,
  egresoDesdeApi,
  egresoHaciaApi,
  gastoDesdeApi,
  gastoHaciaApi,
  plantillaDesdeApi,
  plantillaHaciaApi,
  tipoGastoHaciaApi,
} from './egresos.js';

/**
 * Los importes llegan del backend como texto (`Decimal` serializado) y deben
 * salir como número, o cualquier suma en la interfaz concatenaría cadenas.
 */

describe('gastoDesdeApi', () => {
  it('convierte los importes a número', () => {
    const gasto = gastoDesdeApi({
      id: 1,
      fecha: '2026-08-05',
      concepto: 'Planilla de luz',
      tipo_id: 2,
      proveedor_razon_social: 'EMPRESA ELÉCTRICA',
      proveedor_identificacion: '1790016919001',
      documento: '001-001-000000777',
      subtotal: '100.000000',
      iva: '15.000000',
      total: '115.000000',
      estado_pago: 'Por Pagar',
    });

    expect(gasto.subtotal).toBe(100);
    expect(gasto.iva).toBe(15);
    expect(gasto.total).toBe(115);
    expect(gasto.proveedor).toBe('EMPRESA ELÉCTRICA');
  });

  it('trata la observación ausente como cadena vacía', () => {
    expect(gastoDesdeApi({ observacion: null }).observacion).toBe('');
  });
});

describe('gastoHaciaApi', () => {
  it('manda los importes como texto para no perder precisión', () => {
    const cuerpo = gastoHaciaApi({ concepto: 'X', subtotal: 100, iva: 15 });

    expect(typeof cuerpo.subtotal).toBe('string');
    expect(cuerpo.subtotal).toBe('100');
  });

  it('convierte a null los identificadores vacíos', () => {
    // Un "" en un campo de id haría que Pydantic rechace el cuerpo entero.
    const cuerpo = gastoHaciaApi({ concepto: 'X', tipoId: '', proveedorId: '' });

    expect(cuerpo.tipo_id).toBeNull();
    expect(cuerpo.proveedor_id).toBeNull();
  });

  it('convierte los identificadores de texto a número', () => {
    const cuerpo = gastoHaciaApi({ concepto: 'X', tipoId: '3', proveedorId: '7' });

    expect(cuerpo.tipo_id).toBe(3);
    expect(cuerpo.proveedor_id).toBe(7);
  });
});

describe('tipoGastoHaciaApi', () => {
  it('manda null en la descripción vacía y Activo por defecto', () => {
    const cuerpo = tipoGastoHaciaApi({ nombre: 'Arriendo', descripcion: '' });

    expect(cuerpo.descripcion).toBeNull();
    expect(cuerpo.estado).toBe('Activo');
  });

  it('un tipo sin tocar el campo es deducible, como en el backend', () => {
    // Con `Boolean(undefined)` viajaría false y marcaría el gasto como no
    // deducible sin que nadie lo pidiera.
    expect(tipoGastoHaciaApi({ nombre: 'Arriendo' }).deducible).toBe(true);
    expect(tipoGastoHaciaApi({ nombre: 'Multa', deducible: false }).deducible).toBe(false);
  });
});

describe('egresoDesdeApi', () => {
  it('traduce el pago', () => {
    const egreso = egresoDesdeApi({
      id: 4,
      fecha: '2026-08-10',
      concepto: 'Pago planilla',
      beneficiario: 'EMPRESA ELÉCTRICA',
      monto: '115.000000',
      forma_pago: 'Transferencia',
      gasto_id: 1,
      estado: 'Registrado',
    });

    expect(egreso.monto).toBe(115);
    expect(egreso.formaPago).toBe('Transferencia');
    expect(egreso.gastoId).toBe(1);
  });
});

describe('egresoHaciaApi', () => {
  it('manda el monto como texto y los ids vacíos como null', () => {
    const cuerpo = egresoHaciaApi({ concepto: 'Pago', monto: 50, cuentaId: '', gastoId: '' });

    expect(cuerpo.monto).toBe('50');
    expect(cuerpo.cuenta_id).toBeNull();
    expect(cuerpo.gasto_id).toBeNull();
  });
});

describe('anticipoDesdeApi', () => {
  it('expone el saldo que calcula el servidor', () => {
    // El saldo no se recalcula aquí a propósito: un tercer número puede dejar
    // de cuadrar con los otros dos.
    const anticipo = anticipoDesdeApi({
      id: 1,
      fecha: '2026-08-01',
      tipo: 'ARD',
      receptor_razon_social: 'CONSTRUCTORA ANDINA S.A.',
      detalle: 'Anticipo fase 2',
      monto: '2500.000000',
      facturado: '1200.000000',
      saldo: '1300.000000',
      forma_pago: 'Transferencia',
      estado: 'Parcial',
    });

    expect(anticipo.monto).toBe(2500);
    expect(anticipo.facturado).toBe(1200);
    expect(anticipo.saldo).toBe(1300);
    expect(anticipo.estado).toBe('Parcial');
  });
});

describe('anticipoHaciaApi', () => {
  it('usa ARD y transferencia por defecto', () => {
    const cuerpo = anticipoHaciaApi({ monto: 500 }, 9);

    expect(cuerpo.tipo).toBe('ARD');
    expect(cuerpo.forma_pago).toBe('Transferencia');
    expect(cuerpo.receptor_id).toBe(9);
    expect(cuerpo.monto).toBe('500');
  });
});

describe('plantillaDesdeApi', () => {
  it('traduce la plantilla y sus líneas', () => {
    const plantilla = plantillaDesdeApi({
      id: 1,
      nombre: 'Arriendo local',
      receptor_razon_social: 'ARRENDATARIO S.A.',
      periodicidad: 'Mensual',
      proxima_emision: '2026-09-01',
      ultima_emision: '2026-08-01',
      total: '920.000000',
      emitidas: 3,
      activa: true,
      lineas: [
        {
          id: 1,
          codigo_principal: 'ARR-001',
          descripcion: 'Arriendo mensual',
          cantidad: '1.000000',
          precio_unitario: '800.000000',
          codigo_iva: '4',
        },
      ],
    });

    expect(plantilla.total).toBe(920);
    expect(plantilla.emitidas).toBe(3);
    expect(plantilla.lineas[0].precioUnitario).toBe(800);
    expect(plantilla.lineas[0].codigo).toBe('ARR-001');
  });

  it('sin líneas devuelve una lista vacía', () => {
    expect(plantillaDesdeApi({ lineas: undefined }).lineas).toEqual([]);
  });
});

describe('plantillaHaciaApi', () => {
  it('rellena el código de las líneas libres', () => {
    const cuerpo = plantillaHaciaApi(
      { nombre: 'X', proximaEmision: '2026-09-01' },
      5,
      [{ descripcion: 'Servicio', cantidad: 1, precioUnitario: 100 }],
    );

    expect(cuerpo.lineas[0].codigo_principal).toBe('SIN-COD');
    expect(cuerpo.lineas[0].codigo_iva).toBe('4');
    expect(cuerpo.receptor_id).toBe(5);
  });

  it('manda null en la fecha de fin vacía: la plantilla es indefinida', () => {
    const cuerpo = plantillaHaciaApi({ nombre: 'X', hasta: '' }, 1, []);
    expect(cuerpo.hasta).toBeNull();
  });
});

describe('catálogos', () => {
  it('las periodicidades son las que acepta el backend', () => {
    expect(PERIODICIDADES).toEqual([
      'Semanal',
      'Quincenal',
      'Mensual',
      'Bimestral',
      'Trimestral',
      'Anual',
    ]);
  });

  it('los tipos de anticipo distinguen recibido de pagado', () => {
    expect(TIPOS_ANTICIPO.map((t) => t.codigo)).toEqual(['ARD', 'APP']);
  });

  it('los estados de anticipo incluyen el saldo parcial', () => {
    expect(ESTADOS_ANTICIPO).toContain('Parcial');
    expect(ESTADOS_ANTICIPO).toContain('Aplicado');
  });
});
