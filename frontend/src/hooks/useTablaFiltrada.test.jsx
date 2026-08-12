/**
 * @vitest-environment happy-dom
 */
import { describe, expect, it } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useTablaFiltrada, VALOR_TODOS } from './useTablaFiltrada.js';

/**
 * Este hook gobierna los seis listados. El caso que más importa es el de
 * volver a la página 1 al filtrar: sin eso se ve una tabla vacía y parece que
 * no hay datos.
 */

const DATOS = [
  { id: 1, numero: '001-000001', cliente: 'PLÁSTICOS DEL LITORAL', estado: 'Autorizado' },
  { id: 2, numero: '001-000002', cliente: 'IMPORTADORA AUSTRAL', estado: 'Pendiente' },
  { id: 3, numero: '001-000003', cliente: 'IMPRENTA CENTRAL', estado: 'Autorizado' },
  { id: 4, numero: '001-000004', cliente: 'GLOBAL SUPPLIES', estado: 'Rechazado' },
];

const montar = (props) =>
  renderHook((argumentos) => useTablaFiltrada(argumentos), {
    initialProps: { datos: DATOS, camposBusqueda: ['numero', 'cliente'], ...props },
  });

describe('sin filtros', () => {
  it('devuelve todos los registros', () => {
    const { result } = montar();

    expect(result.current.total).toBe(4);
    expect(result.current.totalSinFiltrar).toBe(4);
    expect(result.current.visibles).toHaveLength(4);
  });

  it('no explota sin argumentos', () => {
    const { result } = renderHook(() => useTablaFiltrada({}));

    expect(result.current.total).toBe(0);
    expect(result.current.visibles).toEqual([]);
    expect(result.current.desde).toBe(0);
  });
});

describe('búsqueda', () => {
  it('ignora tildes y mayúsculas', () => {
    const { result } = montar({ termino: 'plasticos' });

    expect(result.current.total).toBe(1);
    expect(result.current.visibles[0].id).toBe(1);
  });

  it('busca en todos los campos indicados', () => {
    const { result } = montar({ termino: '000003' });

    expect(result.current.total).toBe(1);
    expect(result.current.visibles[0].id).toBe(3);
  });

  it('un término sin coincidencias deja la tabla vacía', () => {
    const { result } = montar({ termino: 'zzzz' });

    expect(result.current.total).toBe(0);
    expect(result.current.desde).toBe(0);
    expect(result.current.hasta).toBe(0);
  });

  it('admite un campo calculado como función', () => {
    const { result } = montar({
      camposBusqueda: [(registro) => `${registro.cliente} ${registro.estado}`],
      termino: 'rechazado',
    });

    expect(result.current.total).toBe(1);
    expect(result.current.visibles[0].id).toBe(4);
  });
});

describe('filtros', () => {
  it('filtra por valor exacto', () => {
    const { result } = montar({ filtros: { estado: 'Autorizado' } });

    expect(result.current.total).toBe(2);
  });

  it('el valor "todos" no filtra', () => {
    const { result } = montar({ filtros: { estado: VALOR_TODOS } });

    expect(result.current.total).toBe(4);
  });

  it('combina filtro y búsqueda', () => {
    const { result } = montar({ filtros: { estado: 'Autorizado' }, termino: 'imprenta' });

    expect(result.current.total).toBe(1);
    expect(result.current.visibles[0].id).toBe(3);
  });

  it('varios filtros se aplican en conjunto', () => {
    const { result } = montar({ filtros: { estado: 'Autorizado', id: 1 } });

    expect(result.current.total).toBe(1);
  });
});

describe('paginación', () => {
  it('corta por el tamaño de página', () => {
    const { result } = montar();

    act(() => result.current.setTamanoPagina(2));

    expect(result.current.visibles).toHaveLength(2);
    expect(result.current.totalPaginas).toBe(2);
    expect(result.current.desde).toBe(1);
    expect(result.current.hasta).toBe(2);
  });

  it('avanza de página', () => {
    const { result } = montar();

    act(() => result.current.setTamanoPagina(2));
    act(() => result.current.setPagina(2));

    expect(result.current.visibles.map((r) => r.id)).toEqual([3, 4]);
    expect(result.current.desde).toBe(3);
    expect(result.current.hasta).toBe(4);
  });

  it('vuelve a la página 1 al buscar', () => {
    // Sin esto, filtrar desde la página 2 muestra una tabla vacía y el usuario
    // concluye que no hay resultados.
    const { result, rerender } = montar();

    act(() => result.current.setTamanoPagina(2));
    act(() => result.current.setPagina(2));
    expect(result.current.pagina).toBe(2);

    rerender({ datos: DATOS, camposBusqueda: ['numero', 'cliente'], termino: 'a' });

    expect(result.current.pagina).toBe(1);
  });

  it('vuelve a la página 1 al cambiar un filtro', () => {
    const { result, rerender } = montar();

    act(() => result.current.setTamanoPagina(2));
    act(() => result.current.setPagina(2));

    rerender({
      datos: DATOS,
      camposBusqueda: ['numero', 'cliente'],
      filtros: { estado: 'Autorizado' },
    });

    expect(result.current.pagina).toBe(1);
  });

  it('ajusta la página si queda fuera de rango al filtrar', () => {
    const { result, rerender } = montar();

    act(() => result.current.setTamanoPagina(1));
    act(() => result.current.setPagina(4));

    rerender({
      datos: DATOS,
      camposBusqueda: ['numero', 'cliente'],
      filtros: { estado: 'Rechazado' },
    });

    expect(result.current.pagina).toBeLessThanOrEqual(result.current.totalPaginas);
    expect(result.current.visibles).toHaveLength(1);
  });

  it('siempre hay al menos una página, aunque no haya datos', () => {
    const { result } = renderHook(() => useTablaFiltrada({ datos: [] }));

    expect(result.current.totalPaginas).toBe(1);
  });
});
