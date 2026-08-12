/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Reportes from './Reportes.jsx';

/**
 * Prueba de la pantalla, no de sus piezas: se monta el componente real y se
 * comprueba lo que vería el usuario. El API se sustituye porque lo que se
 * prueba es la pantalla, no el servidor.
 */

vi.mock('../../api/reportes.js', async (importarOriginal) => {
  const original = await importarOriginal();
  return {
    ...original,
    cargarIva: vi.fn(),
    cargarRetenciones: vi.fn(),
    cargarVentasPorTipo: vi.fn(),
    cargarResumenVentas: vi.fn(),
    cargarEstadoSri: vi.fn(),
    cargarNotasVenta: vi.fn(),
  };
});

const api = await import('../../api/reportes.js');

const IVA = {
  periodo_fiscal: '08/2026',
  tarifas: [
    { codigo_iva: '4', porcentaje: '15', base_imponible: '1500.00', valor_iva: '225.00' },
    { codigo_iva: '0', porcentaje: '0', base_imponible: '200.00', valor_iva: '0.00' },
  ],
  base_total: '1700.00',
  iva_total: '225.00',
};

const RETENCIONES = {
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
};

beforeEach(() => {
  vi.clearAllMocks();
  api.cargarIva.mockResolvedValue({ datos: IVA });
  api.cargarRetenciones.mockResolvedValue({ datos: RETENCIONES });
  api.cargarVentasPorTipo.mockResolvedValue({
    datos: [{ tipo: 'Factura', cantidad: 4, total: '2730.00' }],
  });
  api.cargarResumenVentas.mockResolvedValue({
    datos: {
      comprobantes: 4,
      subtotal: '2400.00',
      descuento: '0.00',
      iva: '330.00',
      total: '2730.00',
      ticket_promedio: '682.50',
    },
  });
  // Sin datos el panel de estado no se pinta, que es lo que quiere la mayoría
  // de pruebas: así el único enlace de descarga es el de la tarjeta.
  api.cargarEstadoSri.mockResolvedValue({ datos: null });
  api.cargarNotasVenta.mockResolvedValue({
    datos: {
      receptores: [
        {
          razon_social: 'BETA CIA. LTDA.',
          identificacion: '0992339411001',
          comprobantes: 2,
          total: '120.00',
        },
      ],
      comprobantes: 2,
      total: '120.00',
    },
  });
});

describe('pantalla de Reportes', () => {
  it('abre en el reporte de IVA y pinta sus tarifas', async () => {
    render(<Reportes />);

    await waitFor(() => expect(screen.getByText(/IVA en ventas —/)).toBeTruthy());

    expect(screen.getByText('15%')).toBeTruthy();
    expect(screen.getByText('0%')).toBeTruthy();
    // Base total y suma de IVA.
    expect(screen.getByText(/1[.,]700[.,]00/)).toBeTruthy();
  });

  it('explica de dónde salen las cifras', async () => {
    render(<Reportes />);

    await waitFor(() => expect(screen.getByText(/formulario 104/)).toBeTruthy());
    expect(screen.getByText(/comprobantes autorizados/i)).toBeTruthy();
  });

  it('cambia a retenciones al pulsar su pestaña', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await waitFor(() => expect(api.cargarIva).toHaveBeenCalled());

    await usuario.click(screen.getByRole('button', { name: /Retenciones/ }));

    await waitFor(() => expect(api.cargarRetenciones).toHaveBeenCalled());
    expect(await screen.findByText(/formulario 103/)).toBeTruthy();
    expect(screen.getByText('312')).toBeTruthy();
  });

  it('el reporte de retenciones separa renta de IVA', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await usuario.click(screen.getByRole('button', { name: /Retenciones/ }));

    expect(await screen.findByText('Retenido de renta')).toBeTruthy();
    expect(screen.getByText('Retenido de IVA')).toBeTruthy();
  });

  it('la pestaña de ventas muestra el resumen y el desglose por tipo', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await usuario.click(screen.getByRole('button', { name: /Ventas/ }));

    expect(await screen.findByText('Ticket promedio')).toBeTruthy();
    expect(screen.getByText('Factura')).toBeTruthy();
  });

  it('cambiar de mes vuelve a consultar el API', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await waitFor(() => expect(api.cargarIva).toHaveBeenCalledTimes(1));

    await usuario.selectOptions(screen.getByLabelText('Mes'), '3');

    await waitFor(() => expect(api.cargarIva).toHaveBeenCalledTimes(2));
    expect(api.cargarIva).toHaveBeenLastCalledWith(expect.any(Number), 3, expect.anything());
  });

  it('sin ventas, lo dice en vez de enseñar una tabla vacía', async () => {
    api.cargarIva.mockResolvedValue({
      datos: { periodo_fiscal: '01/2026', tarifas: [], base_total: '0', iva_total: '0' },
    });

    render(<Reportes />);

    expect(
      await screen.findByText(/No hay ventas autorizadas en este período/),
    ).toBeTruthy();
  });

  it('ofrece exportar a CSV con el período seleccionado', async () => {
    render(<Reportes />);

    const enlace = await screen.findByRole('link', { name: /Exportar CSV/ });

    expect(enlace.getAttribute('href')).toContain('/reportes/iva/csv');
    expect(enlace.getAttribute('href')).toContain('anio=');
    expect(enlace.hasAttribute('download')).toBe(true);
  });

  it('elegir PDF cambia la descarga de la tarjeta', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await screen.findByRole('link', { name: /Exportar CSV/ });

    await usuario.click(screen.getByRole('radio', { name: 'PDF' }));

    const enlace = await screen.findByRole('link', { name: /Exportar PDF/ });
    expect(enlace.getAttribute('href')).toContain('/reportes/iva/pdf');
    expect(enlace.getAttribute('href')).toContain('mes=');
    // El formato es uno u otro: no pueden quedar los dos botones a la vez.
    expect(screen.queryByRole('link', { name: /Exportar CSV/ })).toBeNull();
  });

  it('el pie describe el formato elegido y ya no promete el PDF para más adelante', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    expect(await screen.findByText(/Excel\/CSV/)).toBeTruthy();
    expect(screen.queryByText(/próximamente/)).toBeNull();

    await usuario.click(screen.getByRole('radio', { name: 'PDF' }));

    expect(await screen.findByText(/Descarga en PDF/)).toBeTruthy();
    expect(screen.queryByText(/próximamente/)).toBeNull();
  });

  it('el reporte que solo existe en PDF deshabilita Excel', async () => {
    const usuario = userEvent.setup();
    render(<Reportes />);

    await usuario.click(screen.getByRole('button', { name: /Notas de Venta/ }));

    // Notas de venta no tiene endpoint /csv: ofrecer Excel sería un enlace roto.
    expect(screen.getByRole('radio', { name: 'Excel' }).disabled).toBe(true);
    expect(screen.getByRole('radio', { name: 'PDF' }).getAttribute('aria-checked')).toBe('true');

    const enlace = await screen.findByRole('link', { name: /Exportar PDF/ });
    expect(enlace.getAttribute('href')).toContain('/reportes/notas-venta/pdf');
  });

  it('el panel de estado ante el SRI se exporta en PDF, su único formato', async () => {
    const usuario = userEvent.setup();
    api.cargarEstadoSri.mockResolvedValue({
      datos: { por_estado: [{ estado: 'Autorizado', cantidad: 3 }], total: 3, requieren_atencion: 0 },
    });
    render(<Reportes />);

    await usuario.click(screen.getByRole('radio', { name: 'PDF' }));

    const enlaces = await screen.findAllByRole('link', { name: /Exportar PDF/ });
    const destinos = enlaces.map((e) => e.getAttribute('href'));
    expect(destinos.some((url) => url.includes('/reportes/estado-sri/pdf'))).toBe(true);
  });

  it('sin conexión avisa y no inventa cifras', async () => {
    const { ErrorApi } = await import('../../api/cliente.js');
    api.cargarIva.mockRejectedValue(new ErrorApi('Sin conexión', { estado: 0 }));

    render(<Reportes />);

    expect(await screen.findByText(/Sin conexión con el servidor/)).toBeTruthy();
    // Ninguna cifra de ejemplo debe colarse.
    expect(screen.queryByText('15%')).toBeNull();
  });

  it('un error del servidor se muestra tal cual', async () => {
    const { ErrorApi } = await import('../../api/cliente.js');
    api.cargarIva.mockRejectedValue(new ErrorApi('Error 500 al consultar', { estado: 500 }));

    render(<Reportes />);

    expect(await screen.findByText(/Error 500 al consultar/)).toBeTruthy();
  });
});
