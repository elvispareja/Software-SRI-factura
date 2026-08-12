/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { ErrorApi } from '../api/cliente.js';
import { useRecurso } from './useRecurso.js';

// Se sustituye solo `api.obtener`; `ErrorApi` sigue siendo el real para que la
// distinción entre fallo de red y error del servidor se pruebe de verdad.
vi.mock('../api/cliente.js', async (importarOriginal) => {
  const original = await importarOriginal();
  return { ...original, api: { obtener: vi.fn() } };
});

const { api } = await import('../api/cliente.js');

const DEMO = [{ id: 'demo-1', nombre: 'Registro de muestra' }];
const DEL_SERVIDOR = [{ id: 1, nombre: 'Registro real' }];

describe('useRecurso', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('carga los datos del servidor', async () => {
    api.obtener.mockResolvedValue({ datos: DEL_SERVIDOR, total: 1 });

    const { result } = renderHook(() => useRecurso('/receptores', { datosDemo: DEMO }));

    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.datos).toEqual(DEL_SERVIDOR);
    expect(result.current.total).toBe(1);
    expect(result.current.usandoDemo).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('cae a los datos de demostración si el backend no responde', async () => {
    // Sin esto la interfaz queda en blanco y parece rota cuando en realidad
    // solo falta levantar el backend.
    api.obtener.mockRejectedValue(new ErrorApi('Sin conexión', { estado: 0 }));

    const { result } = renderHook(() => useRecurso('/receptores', { datosDemo: DEMO }));

    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.usandoDemo).toBe(true);
    expect(result.current.datos).toEqual(DEMO);
    // No es un error que haya que mostrar: es un modo degradado con aviso.
    expect(result.current.error).toBeNull();
  });

  it('un error del servidor sí se muestra y no cae a demo', async () => {
    // Un 500 significa que el backend está, pero algo falló: ocultarlo tras
    // datos de muestra escondería el problema.
    api.obtener.mockRejectedValue(new ErrorApi('Error interno', { estado: 500 }));

    const { result } = renderHook(() => useRecurso('/receptores', { datosDemo: DEMO }));

    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.error).toBe('Error interno');
    expect(result.current.usandoDemo).toBe(false);
  });

  it('deduce el total cuando el servidor no manda la cabecera', async () => {
    api.obtener.mockResolvedValue({ datos: DEL_SERVIDOR, total: 0 });

    const { result } = renderHook(() => useRecurso('/receptores'));

    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.total).toBe(1);
  });

  it('no consulta nada cuando está inactivo', async () => {
    const { result } = renderHook(() =>
      useRecurso('/receptores', { datosDemo: DEMO, activo: false }),
    );

    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(api.obtener).not.toHaveBeenCalled();
    expect(result.current.datos).toEqual(DEMO);
  });

  it('recargar vuelve a consultar', async () => {
    api.obtener.mockResolvedValue({ datos: DEL_SERVIDOR, total: 1 });

    const { result } = renderHook(() => useRecurso('/receptores'));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(api.obtener).toHaveBeenCalledTimes(1);

    result.current.recargar();
    await waitFor(() => expect(api.obtener).toHaveBeenCalledTimes(2));
  });

  it('pasa los parámetros de consulta al API', async () => {
    api.obtener.mockResolvedValue({ datos: [], total: 0 });

    renderHook(() => useRecurso('/comprobantes', { parametros: { tamano: 200 } }));

    await waitFor(() => expect(api.obtener).toHaveBeenCalled());

    const [ruta, parametros] = api.obtener.mock.calls[0];
    expect(ruta).toBe('/comprobantes');
    expect(parametros).toEqual({ tamano: 200 });
  });

  it('ignora un AbortError: no es un fallo que mostrar', async () => {
    // Ocurre al cambiar de filtro mientras carga; pintar el error confundiría.
    const abortado = new Error('cancelado');
    abortado.name = 'AbortError';
    api.obtener.mockRejectedValue(abortado);

    const { result } = renderHook(() => useRecurso('/receptores', { datosDemo: DEMO }));

    await waitFor(() => expect(api.obtener).toHaveBeenCalled());

    expect(result.current.error).toBeNull();
    expect(result.current.usandoDemo).toBe(false);
  });
});
