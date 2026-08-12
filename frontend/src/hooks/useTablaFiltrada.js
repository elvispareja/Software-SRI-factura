import { useEffect, useMemo, useState } from 'react';
import { normalizarTexto } from '../lib/texto';

export const VALOR_TODOS = 'todos';
export const TAMANOS_PAGINA = [10, 20, 30, 40, 50];

/**
 * Búsqueda, filtrado y paginación para los listados.
 *
 * @param datos          Colección completa.
 * @param termino        Texto libre del buscador.
 * @param camposBusqueda Campos (o funciones) contra los que se busca el término.
 * @param filtros        Mapa `{ campo: valor }`; el valor `'todos'` no filtra.
 *                       El campo puede ser una función `(registro) => valor`.
 *
 * La paginación vive aquí porque siempre debe volver a la página 1 cuando
 * cambian los filtros: si no, se ve una tabla vacía y parece que no hay datos.
 */
export function useTablaFiltrada({ datos = [], termino = '', camposBusqueda = [], filtros = {} }) {
  const [pagina, setPagina] = useState(1);
  const [tamanoPagina, setTamanoPagina] = useState(TAMANOS_PAGINA[0]);

  // Se serializa para poder compararlo por valor en las dependencias.
  const filtrosSerializados = JSON.stringify(filtros);

  const filtrados = useMemo(() => {
    const filtrosActivos = Object.entries(JSON.parse(filtrosSerializados)).filter(
      ([, valor]) => valor !== VALOR_TODOS && valor !== '' && valor != null,
    );
    const terminoNormalizado = normalizarTexto(termino);

    return datos.filter((registro) => {
      const pasaFiltros = filtrosActivos.every(
        ([campo, valor]) => String(registro[campo] ?? '') === String(valor),
      );
      if (!pasaFiltros) return false;
      if (terminoNormalizado === '') return true;

      return camposBusqueda.some((campo) => {
        const valor = typeof campo === 'function' ? campo(registro) : registro[campo];
        return normalizarTexto(valor).includes(terminoNormalizado);
      });
    });
    // camposBusqueda se declara inline en los componentes; se omite a propósito
    // para no recalcular en cada render por identidad de array.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datos, termino, filtrosSerializados]);

  const totalPaginas = Math.max(1, Math.ceil(filtrados.length / tamanoPagina));

  useEffect(() => {
    setPagina(1);
  }, [termino, filtrosSerializados, tamanoPagina]);

  // Si al filtrar la página actual queda fuera de rango, se ajusta.
  const paginaSegura = Math.min(pagina, totalPaginas);
  const inicio = (paginaSegura - 1) * tamanoPagina;
  const visibles = filtrados.slice(inicio, inicio + tamanoPagina);

  return {
    filtrados,
    visibles,
    pagina: paginaSegura,
    setPagina,
    tamanoPagina,
    setTamanoPagina,
    totalPaginas,
    total: filtrados.length,
    totalSinFiltrar: datos.length,
    desde: filtrados.length === 0 ? 0 : inicio + 1,
    hasta: inicio + visibles.length,
  };
}
