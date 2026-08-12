/**
 * @vitest-environment happy-dom
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { ErrorApi } from '../api/cliente.js';
import { useReporte } from './useReporte.js';

/**
 * La diferencia con `useRecurso` es deliberada: un listado puede caer a datos
 * de demostración, pero un reporte de ventas no. Enseñar cifras inventadas es
 * peor que no enseñar ninguna, porque nadie distingue un total falso de uno
 * real de un vistazo.
 */

const PANEL = { mes: { total: '2385.00' } };

describe('useReporte', () => {
  beforeEach(() => vi.clearAllMocks());

  it('carga el reporte', async () => {
    const cargar = vi.fn().mockResolvedValue({ datos: PANEL });

    const { result } = renderHook(() => useReporte(cargar));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.datos).toEqual(PANEL);
    expect(result.current.error).toBeNull();
    expect(result.current.sinConexion).toBe(false);
  });

  it('sin backend, marca sinConexion y NO inventa datos', async () => {
    const cargar = vi.fn().mockRejectedValue(new ErrorApi('Sin conexión', { estado: 0 }));

    const { result } = renderHook(() => useReporte(cargar));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.sinConexion).toBe(true);
    expect(result.current.datos).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('un error del servidor se muestra y no se confunde con falta de conexión', async () => {
    const cargar = vi.fn().mockRejectedValue(new ErrorApi('Error interno', { estado: 500 }));

    const { result } = renderHook(() => useReporte(cargar));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(result.current.error).toBe('Error interno');
    expect(result.current.sinConexion).toBe(false);
  });

  it('vuelve a consultar cuando cambia el período', async () => {
    const cargar = vi.fn().mockResolvedValue({ datos: PANEL });

    const { rerender } = renderHook(({ fn }) => useReporte(fn), {
      initialProps: { fn: cargar },
    });
    await waitFor(() => expect(cargar).toHaveBeenCalledTimes(1));

    // Cambiar de mes produce una función distinta (useCallback con deps).
    const otro = vi.fn().mockResolvedValue({ datos: PANEL });
    rerender({ fn: otro });

    await waitFor(() => expect(otro).toHaveBeenCalledTimes(1));
  });

  it('no consulta si está inactivo', async () => {
    const cargar = vi.fn();

    const { result } = renderHook(() => useReporte(cargar, { activo: false }));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    expect(cargar).not.toHaveBeenCalled();
  });

  it('ignora un AbortError: es una carga cancelada, no un fallo', async () => {
    const abortado = new Error('cancelado');
    abortado.name = 'AbortError';
    const cargar = vi.fn().mockRejectedValue(abortado);

    const { result } = renderHook(() => useReporte(cargar));
    await waitFor(() => expect(cargar).toHaveBeenCalled());

    expect(result.current.error).toBeNull();
    expect(result.current.sinConexion).toBe(false);
  });

  it('recargar vuelve a pedir', async () => {
    const cargar = vi.fn().mockResolvedValue({ datos: PANEL });

    const { result } = renderHook(() => useReporte(cargar));
    await waitFor(() => expect(result.current.cargando).toBe(false));

    result.current.recargar();
    await waitFor(() => expect(cargar).toHaveBeenCalledTimes(2));
  });
});
