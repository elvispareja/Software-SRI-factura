/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import Cuentas from './Cuentas.jsx';

/**
 * Prueba de la pantalla, no de sus piezas: se monta el componente real y se
 * comprueba lo que vería el usuario. El API se sustituye porque lo que se
 * prueba es la pantalla; el cálculo tiene sus propias pruebas en el backend.
 *
 * Lo que de verdad se vigila aquí son dos mentiras ya corregidas: la pestaña
 * Reportes prometía «Próximamente» sobre datos que existen, y el interruptor
 * Cobrar/Pagar cambiaba los rótulos sin cambiar la consulta.
 */

vi.mock('../../api/cuentas.js', async (importarOriginal) => {
  const original = await importarOriginal();
  return {
    ...original,
    cargarSaldosPendientes: vi.fn(),
    cargarAgendaCuotas: vi.fn(),
    cargarRecibosGenerados: vi.fn(),
    cargarRotacionCuentas: vi.fn(),
    cargarHistorialContactos: vi.fn(),
    registrarRecibo: vi.fn(),
    anularRecibo: vi.fn(),
  };
});

const api = await import('../../api/cuentas.js');

const SALDOS = {
  modo: 'cobrar',
  etiqueta_contacto: 'Cliente',
  moneda: 'USD',
  hoy: '2026-08-11',
  documentos: [
    {
      origen: 'Comprobante',
      documento_id: 1,
      tipo: 'Factura',
      numero: '001-001-000000007',
      fecha: '2026-07-01',
      contacto: 'ACME S.A.',
      identificacion: '1790012345001',
      moneda: 'USD',
      vence: '2026-08-01',
      dias_mora: 10,
      total: '1000.00',
      abonado: '400.00',
      saldo: '600.00',
      estado: 'Parcial',
    },
  ],
  total_documentos: 1,
  total_original: '1000.00',
  abonado: '400.00',
  saldo: '600.00',
};

const AGENDA = {
  modo: 'cobrar',
  etiqueta_contacto: 'Cliente',
  desde: null,
  hasta: null,
  hoy: '2026-08-11',
  cuotas: [
    {
      origen: 'Comprobante',
      documento_id: 1,
      documento: '001-001-000000007',
      tipo: 'Factura',
      contacto: 'ACME S.A.',
      identificacion: '1790012345001',
      correo: 'pagos@acme.ec',
      telefono: '0999999999',
      cuota_id: 5,
      numero: 2,
      vence: '2026-08-01',
      dias_mora: 10,
      monto: '500.00',
      abonado: '0.00',
      saldo: '500.00',
      estado: 'Pendiente',
    },
  ],
  total_cuotas: 1,
  monto: '500.00',
  abonado: '0.00',
  saldo: '500.00',
  vencidas: 1,
  saldo_vencido: '500.00',
};

const RECIBOS = {
  modo: 'cobrar',
  etiqueta_contacto: 'Cliente',
  desde: null,
  hasta: null,
  recibos: [
    {
      origen: 'Recibo',
      recibo_id: 3,
      numero: 'REC-000003',
      fecha: '2026-08-05',
      contacto: 'ACME S.A.',
      documento: '001-001-000000007',
      cuota_id: 4,
      monto: '400.00',
      forma_pago: 'Transferencia',
      estado: 'Registrado',
      referencia: 'TR-88',
    },
  ],
  total_recibos: 1,
  aplicado: '400.00',
  anulados: 0,
  monto_anulado: '0.00',
};

const ROTACION = {
  modo: 'cobrar',
  etiqueta_contacto: 'Cliente',
  desde: '2026-01-01',
  hasta: '2026-12-31',
  dias_periodo: 365,
  por_tipo: [
    {
      grupo: 'Factura',
      documentos: 1,
      total: '1000.00',
      cobrado: '400.00',
      pendiente: '600.00',
      promedio: '1000.00',
      dias_recuperacion: '35.0',
    },
  ],
  por_contacto: [
    {
      grupo: 'ACME S.A.',
      documentos: 1,
      total: '1000.00',
      cobrado: '400.00',
      pendiente: '600.00',
      promedio: '1000.00',
      dias_recuperacion: '35.0',
    },
  ],
  totales: {
    grupo: 'TOTAL',
    documentos: 1,
    total: '1000.00',
    cobrado: '400.00',
    pendiente: '600.00',
    promedio: '1000.00',
    dias_recuperacion: '35.0',
  },
};

const HISTORIAL = {
  modo: 'cobrar',
  etiqueta_contacto: 'Cliente',
  hoy: '2026-08-11',
  contactos: [
    {
      receptor_id: 9,
      contacto: 'ACME S.A.',
      identificacion: '1790012345001',
      correo: 'pagos@acme.ec',
      telefono: '0999999999',
      documentos: 1,
      total: '1000.00',
      abonado: '400.00',
      saldo: '600.00',
      cuotas_pendientes: 1,
      cuotas_vencidas: 1,
      saldo_vencido: '500.00',
      proxima_fecha: '2026-08-01',
      ultimo_movimiento: '2026-08-05',
    },
  ],
  total_contactos: 1,
  total: '1000.00',
  abonado: '400.00',
  saldo: '600.00',
};

const pintar = () =>
  render(
    <MemoryRouter initialEntries={['/cuentas']}>
      <Cuentas />
    </MemoryRouter>,
  );

const abrirReportes = async (usuario) => {
  await usuario.click(screen.getByRole('button', { name: /Reportes/ }));
  await waitFor(() => expect(api.cargarRotacionCuentas).toHaveBeenCalled());
};

beforeEach(() => {
  vi.clearAllMocks();
  api.cargarSaldosPendientes.mockResolvedValue({ datos: SALDOS });
  api.cargarAgendaCuotas.mockResolvedValue({ datos: AGENDA });
  api.cargarRecibosGenerados.mockResolvedValue({ datos: RECIBOS });
  api.cargarRotacionCuentas.mockResolvedValue({ datos: ROTACION });
  api.cargarHistorialContactos.mockResolvedValue({ datos: HISTORIAL });
});

describe('pestaña Reportes de Cuentas', () => {
  it('pinta las cinco tarjetas con datos del servidor', async () => {
    const usuario = userEvent.setup();
    pintar();
    await abrirReportes(usuario);

    await waitFor(() =>
      expect(screen.getByText('Saldo pendiente por documento')).toBeTruthy(),
    );
    expect(screen.getByText('Agenda de cuotas')).toBeTruthy();
    expect(screen.getByText('Recibos generados')).toBeTruthy();
    expect(screen.getByText('Rotación de cuentas')).toBeTruthy();
    expect(screen.getByText('Historial por cliente')).toBeTruthy();

    // Datos reales, no marcadores de posición.
    expect(screen.getAllByText('001-001-000000007').length).toBeGreaterThan(0);
    expect(screen.getByText('REC-000003')).toBeTruthy();
    expect(screen.getAllByText('ACME S.A.').length).toBeGreaterThan(0);
  });

  it('ya no promete un módulo contable que no existe', async () => {
    const usuario = userEvent.setup();
    pintar();
    await abrirReportes(usuario);

    await waitFor(() => expect(screen.getByText('Agenda de cuotas')).toBeTruthy());
    expect(screen.queryByText(/Próximamente/)).toBeNull();
    expect(screen.queryByText(/módulo contable/)).toBeNull();
    // Se genera CSV, no Excel: prometer Excel y dar CSV es otra mentira.
    expect(screen.getAllByText('Cuentas por cobrar · CSV')).toHaveLength(5);
    expect(screen.queryByText(/· Excel/)).toBeNull();
  });

  it('descarga cada CSV con un enlace, dejándoselo al navegador', async () => {
    const usuario = userEvent.setup();
    const { container } = pintar();
    await abrirReportes(usuario);

    await waitFor(() => expect(screen.getByText('Agenda de cuotas')).toBeTruthy());
    const enlaces = container.querySelectorAll('a[download]');
    expect(enlaces).toHaveLength(5);
    expect(enlaces[0].getAttribute('href')).toContain('/cuentas/reportes/saldos/csv?modo=cobrar');
    expect(enlaces[1].getAttribute('href')).toContain('/cuentas/reportes/agenda/csv?modo=cobrar');
  });

  it('cada tarjeta avisa cuando el reporte viene vacío', async () => {
    api.cargarRotacionCuentas.mockResolvedValue({
      datos: { ...ROTACION, por_tipo: [], por_contacto: [], totales: null },
    });
    const usuario = userEvent.setup();
    pintar();
    await abrirReportes(usuario);

    await waitFor(() =>
      expect(screen.getByText('No hay documentos emitidos en el período para cobrar.')).toBeTruthy(),
    );
  });

  it('cada tarjeta enseña el error del servidor sin tumbar las demás', async () => {
    api.cargarRecibosGenerados.mockRejectedValue(new Error('Fallo al calcular recibos.'));
    const usuario = userEvent.setup();
    pintar();
    await abrirReportes(usuario);

    await waitFor(() => expect(screen.getByText('Fallo al calcular recibos.')).toBeTruthy());
    // La tarjeta de al lado sigue con sus datos.
    expect(screen.getByText('Rotación de cuentas')).toBeTruthy();
  });
});

describe('interruptor Cobrar/Pagar', () => {
  it('pide otros datos al pasar a Pagar, no solo otro rótulo', async () => {
    const usuario = userEvent.setup();
    pintar();

    await waitFor(() => expect(api.cargarSaldosPendientes).toHaveBeenCalled());
    expect(api.cargarSaldosPendientes.mock.calls[0][0]).toBe('cobrar');
    expect(api.cargarAgendaCuotas.mock.calls[0][0]).toBe('cobrar');

    await usuario.click(screen.getByRole('button', { name: 'Pagar' }));

    await waitFor(() =>
      expect(
        api.cargarSaldosPendientes.mock.calls.some(([modo]) => modo === 'pagar'),
      ).toBe(true),
    );
    expect(api.cargarAgendaCuotas.mock.calls.some(([modo]) => modo === 'pagar')).toBe(true);
    expect(screen.getByText('Cuentas por Pagar')).toBeTruthy();
  });

  it('arrastra el modo hasta las tarjetas de reportes y sus CSV', async () => {
    const usuario = userEvent.setup();
    const { container } = pintar();

    await usuario.click(screen.getByRole('button', { name: 'Pagar' }));
    await abrirReportes(usuario);

    await waitFor(() =>
      expect(api.cargarRotacionCuentas.mock.calls.some(([modo]) => modo === 'pagar')).toBe(true),
    );
    expect(api.cargarHistorialContactos.mock.calls.some(([modo]) => modo === 'pagar')).toBe(true);
    expect(screen.getAllByText('Cuentas por pagar · CSV')).toHaveLength(5);
    expect(screen.getByText('Historial por proveedor')).toBeTruthy();

    const enlaces = container.querySelectorAll('a[download]');
    expect(enlaces[0].getAttribute('href')).toContain('modo=pagar');
  });

  it('en modo Pagar no ofrece cobrar: ese dinero sale, no entra', async () => {
    const usuario = userEvent.setup();
    pintar();

    await usuario.click(screen.getByRole('button', { name: 'Pagar' }));
    await usuario.click(screen.getByRole('button', { name: /Vencidos/ }));

    await waitFor(() => expect(screen.getByText('001-001-000000007')).toBeTruthy());
    // El botón «Cobrar» del interruptor sigue ahí; el de la fila, no.
    const fila = screen.getByText('001-001-000000007').closest('tr');
    expect(within(fila).getByText('Se paga desde Gastos')).toBeTruthy();
    expect(within(fila).queryByRole('button', { name: 'Cobrar' })).toBeNull();
  });
});

describe('gestión de cuotas', () => {
  it('cobra una cuota vencida y vuelve a pedir la agenda', async () => {
    api.registrarRecibo.mockResolvedValue({ datos: { id: 10 } });
    const usuario = userEvent.setup();
    pintar();

    await usuario.click(screen.getByRole('button', { name: /Vencidos/ }));
    await waitFor(() => expect(screen.getByText('001-001-000000007')).toBeTruthy());

    const fila = screen.getByText('001-001-000000007').closest('tr');
    await usuario.click(within(fila).getByRole('button', { name: 'Cobrar' }));

    await waitFor(() => expect(api.registrarRecibo).toHaveBeenCalled());
    expect(api.registrarRecibo.mock.calls[0][0]).toMatchObject({ cuotaId: 5, monto: 500 });
    // La agenda se vuelve a pedir: el saldo que se acaba de mover ya no vale.
    await waitFor(() => expect(api.cargarAgendaCuotas.mock.calls.length).toBeGreaterThan(1));
  });
});
