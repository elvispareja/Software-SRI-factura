import { createContext } from 'react';

/** Clave de localStorage. Debe coincidir con el script inline de index.html. */
export const CLAVE_ALMACENAMIENTO = 'factoa-tema';

export const PREFERENCIAS_VALIDAS = ['sistema', 'claro', 'oscuro'];

export const TemaContext = createContext(null);
