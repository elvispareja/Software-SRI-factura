/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Dashboard from './Dashboard.jsx';

/**
 * El panel de inicio enseñaba las mismas ventas a todo el mundo: derivaba sus
 * cifras de los datos de demostración. Ahora vienen de `/reportes/panel`, y lo
 * que estas pruebas vigilan es que sin servidor **no invente ninguna**.
 */

vi.mock('../../api/reportes.js', async (importarOriginal) => {
  const original = await importarOriginal();
  return { ...original, cargarPanel: vi.fn() };
});

vi.mock('../../auth/useSesion.js', () => ({ useSesion: vi.fn() }));

// Recharts mide el contenedor, y en un DOM sin layout eso da cero: se
// sustituye por un div con tamaño para que las gráficas se puedan montar.
vi.mock('recharts', async (importarOriginal) => {
  const original = await importarOriginal();
  return {
    ...original,
    ResponsiveContainer: ({ children }) => (
      <div style={{ width: 800, height: 400 }}>{children}</div>
    ),
  };
});

const api = await import('../../api/reportes.js');
const { useSesion } = await import('../../auth/useSesion.js');

const PANEL = {
  hoy: '2026-08-09',
  mes: {
    desde: '2026-08-01',
    hasta: '2026-08-31',
    comprobantes: 3,
    subtotal: '2100.00',
    descuento: '0.00',
    iva: '285.00',
    total: '2385.00',
    ticket_promedio: '795.00',
  },
  anio: {
    desde: '2026-01-01',
    hasta: '2026-12-31',
    comprobantes: 4,
    subtotal: '2400.00',
    descuento: '0.00',
    iva: '330.00',
    total: '2730.00',
    ticket_promedio: '682.50',
  },
  por_tipo: [{ tipo: 'Factura', cantidad: 4, total: '2730.00' }],
  serie_mensual: Array.from({ length: 12 }, (_, indice) => ({
    mes: indice + 1,
    cantidad: indice === 7 ? 3 : 0,
    total: indice === 7 ? '2385.00' : '0.00',
  })),
  top_clientes: [
    {
      razon_social: 'BETA CIA. LTDA.',
      identificacion: '0992339411001',
      comprobantes: 2,
      total: '1235.00',
    },
  ],
  top_articulos: [
    { codigo: 'PROD-001', descripcion: 'Laptop Dell', cantidad: '2.00', total: '1500.00' },
  ],
  estado_sri: {
    desde: '2026-01-01',
    hasta: '2026-12-31',
    por_estado: [{ estado: 'Autorizado', cantidad: 4 }],
    total: 6,
    requieren_atencion: 2,
  },
  por_cobrar: { comprobantes: 1, total: '460.00', a_credito: '460.00' },
};

const montar = () =>
  render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  useSesion.mockReturnValue({ usuario: { nombre: 'Ana Salazar' } });
  api.cargarPanel.mockResolvedValue({ datos: PANEL });
});

describe('Dashboard', () => {
  it('saluda por el primer nombre de quien inició sesión', async () => {
    montar();

    expect(await screen.findByText(/, Ana$/)).toBeTruthy();
  });

  it('saluda sin nombre si la sesión no lo trae', async () => {
    useSesion.mockReturnValue({ usuario: null });
    montar();

    const titulo = await screen.findByRole('heading', { level: 1 });
    expect(titulo.textContent).toMatch(/^Buen[oa]s/);
    expect(titulo.textContent).not.toContain(',');
  });

  it('pinta los indicadores con las cifras del servidor', async () => {
    montar();

    await waitFor(() => expect(screen.getByText('Facturado este mes')).toBeTruthy());

    expect(screen.getByText(/2[.,]385[.,]00/)).toBeTruthy();
    expect(screen.getByText('Ticket promedio')).toBeTruthy();
    expect(screen.getByText(/795[.,]00/)).toBeTruthy();
  });

  it('destaca los comprobantes que requieren atención', async () => {
    montar();

    expect(await screen.findByText(/2 comprobantes requieren atención/)).toBeTruthy();
    expect(screen.getByText(/rechazados por el SRI/)).toBeTruthy();
  });

  it('concuerda el singular cuando solo hay uno', async () => {
    api.cargarPanel.mockResolvedValue({
      datos: { ...PANEL, estado_sri: { ...PANEL.estado_sri, requieren_atencion: 1 } },
    });
    montar();

    expect(await screen.findByText(/1 comprobante requiere atención/)).toBeTruthy();
  });

  it('oculta el aviso cuando no hay nada pendiente', async () => {
    api.cargarPanel.mockResolvedValue({
      datos: { ...PANEL, estado_sri: { ...PANEL.estado_sri, requieren_atencion: 0 } },
    });
    montar();

    await waitFor(() => expect(screen.getByText('Facturado este mes')).toBeTruthy());
    expect(screen.queryByText(/requieren atención/)).toBeNull();
  });

  it('lista los clientes y artículos que más facturan', async () => {
    montar();

    expect(await screen.findByText('BETA CIA. LTDA.')).toBeTruthy();
    expect(screen.getByText('2 documentos')).toBeTruthy();
    expect(screen.getByText('Laptop Dell')).toBeTruthy();
  });

  it('sin ventas en el año, lo dice en vez de dibujar una gráfica vacía', async () => {
    api.cargarPanel.mockResolvedValue({
      datos: {
        ...PANEL,
        anio: { ...PANEL.anio, comprobantes: 0, total: '0.00' },
        por_tipo: [],
        top_clientes: [],
        top_articulos: [],
      },
    });
    montar();

    expect(
      await screen.findByText(/Aún no hay comprobantes autorizados este año/),
    ).toBeTruthy();
    expect(screen.getByText(/Sin documentos autorizados todavía/)).toBeTruthy();
  });

  it('sin servidor avisa y no enseña ninguna cifra inventada', async () => {
    const { ErrorApi } = await import('../../api/cliente.js');
    api.cargarPanel.mockRejectedValue(new ErrorApi('Sin conexión', { estado: 0 }));

    montar();

    expect(await screen.findByText(/Sin conexión con el servidor/)).toBeTruthy();
    expect(screen.queryByText('Facturado este mes')).toBeNull();
  });

  it('un error del servidor se muestra tal cual', async () => {
    const { ErrorApi } = await import('../../api/cliente.js');
    api.cargarPanel.mockRejectedValue(new ErrorApi('Error interno', { estado: 500 }));

    montar();

    expect(await screen.findByText(/Error interno/)).toBeTruthy();
  });

  it('mantiene las acciones rápidas siempre disponibles', async () => {
    montar();

    // Se ven aunque el panel falle: son navegación, no dependen de los datos.
    expect(screen.getByRole('link', { name: /Crear Factura/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /Crear Receptor/ })).toBeTruthy();
    expect(screen.getByRole('link', { name: /Conexión Tributaria/ })).toBeTruthy();
  });
});
