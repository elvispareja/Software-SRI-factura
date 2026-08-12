/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import RetencionForm from './RetencionForm.jsx';

/**
 * El formulario de retención es el que más aritmética tiene en pantalla y el
 * que más reglas del SRI impone. Se monta entero y se comprueba lo que ve el
 * usuario: qué se le impide hacer, y qué números le salen.
 */

vi.mock('../../hooks/useCatalogos.js', () => ({
  useCatalogos: vi.fn(),
}));

vi.mock('../../api/retenciones.js', async (importarOriginal) => {
  const original = await importarOriginal();
  return {
    ...original,
    cargarCodigosRetencion: vi.fn(),
    crearRetencion: vi.fn(),
    emitirRetencionAlSri: vi.fn(),
  };
});

const { useCatalogos } = await import('../../hooks/useCatalogos.js');
const api = await import('../../api/retenciones.js');

const PROVEEDOR = {
  id: 7,
  razonSocial: 'PROVEEDOR DEMO S.A.',
  identificacion: '0992339411001',
  rol: 'Proveedor',
  estado: 'Activo',
};

// Misma forma que devuelve `GET /retenciones/codigos`: el `id` existe porque
// muchos conceptos de la resolución no tienen código en la ficha técnica, así
// que el código no sirve como clave del desplegable.
const CODIGOS = [
  {
    id: '1-0',
    codigo_impuesto: '1',
    codigo_retencion: '312',
    descripcion: 'Transferencia de bienes muebles',
    porcentaje: '2',
    verificado: true,
  },
  {
    id: '1-1',
    codigo_impuesto: '1',
    codigo_retencion: '303',
    descripcion: 'Honorarios profesionales',
    porcentaje: '10',
    verificado: true,
  },
  {
    id: '1-2',
    codigo_impuesto: '1',
    codigo_retencion: '',
    descripcion: 'Pagos sin porcentaje específico',
    porcentaje: '3',
    verificado: true,
  },
  {
    id: '2-0',
    codigo_impuesto: '2',
    codigo_retencion: '1',
    descripcion: 'Retención 30% de IVA',
    porcentaje: '30',
    verificado: true,
  },
];

function montar() {
  return render(
    <MemoryRouter>
      <RetencionForm />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();

  useCatalogos.mockReturnValue({
    receptores: [PROVEEDOR],
    articulos: [],
    buscarReceptores: (termino, rol) =>
      termino && rol === 'Proveedor' ? [PROVEEDOR] : [],
    buscarArticulos: () => [],
    cargando: false,
    usandoDemo: false,
  });

  api.cargarCodigosRetencion.mockResolvedValue({ datos: CODIGOS });
  api.crearRetencion.mockResolvedValue({
    datos: { id: 1, numero: '001-001-000000001' },
  });
  api.emitirRetencionAlSri.mockResolvedValue({
    datos: { retencion: { id: 1, numero: '001-001-000000001', estado_sri: 'Autorizado' } },
  });
});

describe('formulario de retención', () => {
  it('arranca con el período fiscal del mes en curso, en formato MM/AAAA', async () => {
    montar();

    const periodo = screen.getByLabelText(/Período fiscal/);
    expect(periodo.value).toMatch(/^\d{2}\/\d{4}$/);
  });

  it('no deja emitir hasta que estén los datos obligatorios', async () => {
    montar();

    const emitir = screen.getByRole('button', { name: /Emitir al SRI/ });
    expect(emitir.disabled).toBe(true);

    expect(screen.getByText(/Selecciona el proveedor/)).toBeTruthy();
    expect(screen.getByText(/número del documento sustento/)).toBeTruthy();
  });

  it('avisa si el período fiscal no tiene el formato del SRI', async () => {
    const usuario = userEvent.setup();
    montar();

    const periodo = screen.getByLabelText(/Período fiscal/);
    await usuario.clear(periodo);
    await usuario.type(periodo, '2026-08');

    expect(await screen.findByText(/formato MM\/AAAA/)).toBeTruthy();
  });

  it('busca solo proveedores y lo selecciona', async () => {
    const usuario = userEvent.setup();
    montar();

    const buscador = screen.getByPlaceholderText(/Buscar proveedor/);
    await usuario.type(buscador, 'prov');

    const opcion = await screen.findByRole('button', { name: /PROVEEDOR DEMO S.A./ });
    await usuario.click(opcion);

    expect(await screen.findByText('PROVEEDOR DEMO S.A.')).toBeTruthy();
    expect(screen.queryByText(/Ningún proveedor seleccionado/)).toBeNull();
  });

  it('calcula el valor retenido de la línea y el total', async () => {
    const usuario = userEvent.setup();
    montar();

    await usuario.type(screen.getByLabelText('Base imponible'), '1000');
    await usuario.type(screen.getByLabelText('Porcentaje a retener'), '2');

    // 2% de 1000 = 20.
    await waitFor(() => expect(screen.getAllByText(/20[.,]00/).length).toBeGreaterThan(0));
  });

  it('precarga el porcentaje al elegir el concepto', async () => {
    const usuario = userEvent.setup();
    montar();

    await waitFor(() => expect(api.cargarCodigosRetencion).toHaveBeenCalled());

    await usuario.selectOptions(screen.getByLabelText('Concepto de retención'), '1-1');

    await waitFor(() =>
      expect(screen.getByLabelText('Porcentaje a retener').value).toBe('10'),
    );
  });

  it('cambiar de impuesto limpia el concepto y ofrece los del nuevo', async () => {
    const usuario = userEvent.setup();
    montar();

    await waitFor(() => expect(api.cargarCodigosRetencion).toHaveBeenCalled());

    await usuario.selectOptions(screen.getByLabelText('Concepto de retención'), '1-1');
    await usuario.selectOptions(screen.getByLabelText('Impuesto'), '2');

    // El concepto de renta ya no aplica; el select vuelve a vacío.
    await waitFor(() => expect(screen.getByLabelText('Concepto de retención').value).toBe(''));

    const conceptos = within(screen.getByLabelText('Concepto de retención'));
    expect(conceptos.getByText(/Retención 30% de IVA/)).toBeTruthy();
  });

  it('permite agregar y quitar líneas', async () => {
    const usuario = userEvent.setup();
    montar();

    expect(screen.getAllByLabelText('Base imponible')).toHaveLength(1);

    await usuario.click(screen.getByRole('button', { name: /Agregar línea/ }));
    expect(screen.getAllByLabelText('Base imponible')).toHaveLength(2);

    await usuario.click(screen.getAllByRole('button', { name: /Eliminar línea/ })[0]);
    expect(screen.getAllByLabelText('Base imponible')).toHaveLength(1);
  });

  it('cita la resolución vigente y avisa de que los campos son editables', () => {
    montar();

    // Quien fija los porcentajes es el SRI por resolución, no esta tabla; el
    // usuario tiene que poder corregirlos sin esperar a que se actualice.
    expect(screen.getByText('NAC-DGERCGC26-00000009')).toBeTruthy();
    expect(screen.getByText(/El código y el porcentaje son editables/)).toBeTruthy();
  });

  it('con todo completo, emite y avisa del número', async () => {
    const usuario = userEvent.setup();
    montar();

    await waitFor(() => expect(api.cargarCodigosRetencion).toHaveBeenCalled());

    await usuario.type(screen.getByPlaceholderText(/Buscar proveedor/), 'prov');
    await usuario.click(await screen.findByRole('button', { name: /PROVEEDOR DEMO S.A./ }));

    await usuario.type(
      screen.getByPlaceholderText('001-001-000000123'),
      '001-001-000000123',
    );
    await usuario.selectOptions(screen.getByLabelText('Concepto de retención'), '1-0');
    await usuario.type(screen.getByLabelText('Base imponible'), '1000');

    const emitir = screen.getByRole('button', { name: /Emitir al SRI/ });
    await waitFor(() => expect(emitir.disabled).toBe(false));

    await usuario.click(emitir);

    await waitFor(() => expect(api.crearRetencion).toHaveBeenCalled());
    expect(await screen.findByText(/001-001-000000001/)).toBeTruthy();
  });

  it('si el SRI rechaza, lo dice sin perder la retención', async () => {
    const usuario = userEvent.setup();
    api.emitirRetencionAlSri.mockRejectedValue(new Error('FIRMA INVALIDA'));

    montar();
    await waitFor(() => expect(api.cargarCodigosRetencion).toHaveBeenCalled());

    await usuario.type(screen.getByPlaceholderText(/Buscar proveedor/), 'prov');
    await usuario.click(await screen.findByRole('button', { name: /PROVEEDOR DEMO S.A./ }));
    await usuario.type(
      screen.getByPlaceholderText('001-001-000000123'),
      '001-001-000000123',
    );
    await usuario.selectOptions(screen.getByLabelText('Concepto de retención'), '1-0');
    await usuario.type(screen.getByLabelText('Base imponible'), '1000');

    await usuario.click(screen.getByRole('button', { name: /Emitir al SRI/ }));

    expect(await screen.findByText(/se guardó, pero no se pudo emitir/)).toBeTruthy();
    expect(screen.getByText(/FIRMA INVALIDA/)).toBeTruthy();
  });

  it('sin conexión con el servidor no deja guardar', async () => {
    useCatalogos.mockReturnValue({
      receptores: [PROVEEDOR],
      articulos: [],
      buscarReceptores: () => [PROVEEDOR],
      buscarArticulos: () => [],
      cargando: false,
      usandoDemo: true,
    });

    montar();

    // Los identificadores del modo demo no existen en el servidor.
    expect(screen.getByRole('button', { name: /Emitir al SRI/ }).disabled).toBe(true);
    expect(screen.getByText(/datos de demostración/)).toBeTruthy();
  });
});
