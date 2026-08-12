import { useCallback, useEffect, useMemo, useState } from 'react';
import { CLAVE_ALMACENAMIENTO, PREFERENCIAS_VALIDAS, TemaContext } from './contexto';

/**
 * Gestión del tema claro/oscuro.
 *
 * La preferencia tiene tres valores: 'sistema' (sigue al SO), 'claro' y
 * 'oscuro'. Solo las dos últimas escriben `data-tema` en <html>; 'sistema'
 * quita el atributo para que mande el `prefers-color-scheme` de index.css.
 */

const leerPreferenciaGuardada = () => {
  try {
    const guardada = localStorage.getItem(CLAVE_ALMACENAMIENTO);
    return PREFERENCIAS_VALIDAS.includes(guardada) ? guardada : 'sistema';
  } catch {
    // Modo privado o storage bloqueado: se sigue al sistema.
    return 'sistema';
  }
};

export function TemaProvider({ children }) {
  const [preferencia, setPreferencia] = useState(leerPreferenciaGuardada);
  const [prefiereOscuroElSistema, setPrefiereOscuroElSistema] = useState(
    () => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
  );

  useEffect(() => {
    const consulta = window.matchMedia?.('(prefers-color-scheme: dark)');
    if (!consulta) return undefined;

    const alCambiar = (evento) => setPrefiereOscuroElSistema(evento.matches);
    consulta.addEventListener('change', alCambiar);
    return () => consulta.removeEventListener('change', alCambiar);
  }, []);

  useEffect(() => {
    const raiz = document.documentElement;
    if (preferencia === 'sistema') {
      raiz.removeAttribute('data-tema');
    } else {
      raiz.setAttribute('data-tema', preferencia);
    }

    try {
      localStorage.setItem(CLAVE_ALMACENAMIENTO, preferencia);
    } catch {
      // Sin persistencia: el tema igual aplica durante la sesión.
    }
  }, [preferencia]);

  const temaEfectivo = useMemo(() => {
    if (preferencia !== 'sistema') return preferencia;
    return prefiereOscuroElSistema ? 'oscuro' : 'claro';
  }, [preferencia, prefiereOscuroElSistema]);

  /** Cicla sistema -> claro -> oscuro -> sistema. */
  const alternarTema = useCallback(() => {
    setPreferencia((actual) => {
      const indice = PREFERENCIAS_VALIDAS.indexOf(actual);
      return PREFERENCIAS_VALIDAS[(indice + 1) % PREFERENCIAS_VALIDAS.length];
    });
  }, []);

  const valor = useMemo(
    () => ({ preferencia, temaEfectivo, setPreferencia, alternarTema }),
    [preferencia, temaEfectivo, alternarTema],
  );

  return <TemaContext.Provider value={valor}>{children}</TemaContext.Provider>;
}
