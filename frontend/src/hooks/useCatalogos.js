import { useCallback, useMemo } from 'react';
import { useRecurso } from './useRecurso';
import { articuloDesdeApi, receptorDesdeApi } from '../api/adaptadores';
import { CATALOGO_RECEPTORES } from '../data/catalogoReceptores';
import { CATALOGO_ARTICULOS } from '../data/catalogoArticulos';
import { contieneTexto } from '../lib/texto';

/**
 * Catálogos que necesitan los formularios de documentos: receptores y
 * artículos, con buscadores ya filtrados.
 *
 * Se traen enteros y se filtran en el cliente porque el buscador responde a
 * cada tecla; con miles de registros habrá que mover la búsqueda al API, que
 * ya la soporta.
 */

const CONSULTA = { tamano: 200 };
const LIMITE_RESULTADOS = 6;

export function useCatalogos() {
  const receptores = useRecurso('/receptores', {
    parametros: CONSULTA,
    datosDemo: CATALOGO_RECEPTORES,
  });
  const articulos = useRecurso('/articulos', {
    parametros: CONSULTA,
    datosDemo: CATALOGO_ARTICULOS,
  });

  const listaReceptores = useMemo(
    () => (receptores.usandoDemo ? receptores.datos : receptores.datos.map(receptorDesdeApi)),
    [receptores.datos, receptores.usandoDemo],
  );

  const listaArticulos = useMemo(
    () => (articulos.usandoDemo ? articulos.datos : articulos.datos.map(articuloDesdeApi)),
    [articulos.datos, articulos.usandoDemo],
  );

  /** Busca receptores activos, opcionalmente acotando por rol. */
  const buscarReceptores = useCallback(
    (termino, rol = null) => {
      if (termino.trim() === '') return [];

      return listaReceptores
        .filter(
          (receptor) =>
            receptor.estado === 'Activo' &&
            (rol === null || receptor.rol === rol) &&
            (contieneTexto(receptor.razonSocial, termino) ||
              contieneTexto(receptor.identificacion, termino) ||
              contieneTexto(receptor.nombreComercial, termino)),
        )
        .slice(0, LIMITE_RESULTADOS);
    },
    [listaReceptores],
  );

  const buscarArticulos = useCallback(
    (termino) => {
      if (termino.trim() === '') return [];

      return listaArticulos
        .filter(
          (articulo) =>
            articulo.estado === 'Activo' &&
            (contieneTexto(articulo.codigo, termino) || contieneTexto(articulo.nombre, termino)),
        )
        .slice(0, LIMITE_RESULTADOS);
    },
    [listaArticulos],
  );

  return {
    receptores: listaReceptores,
    articulos: listaArticulos,
    buscarReceptores,
    buscarArticulos,
    cargando: receptores.cargando || articulos.cargando,
    // Si cualquiera de los dos cae a demo, el documento no se puede guardar
    // de verdad: los ids que se enviarían no existen en el backend.
    usandoDemo: receptores.usandoDemo || articulos.usandoDemo,
  };
}
