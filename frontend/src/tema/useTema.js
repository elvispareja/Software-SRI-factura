import { useContext } from 'react';
import { TemaContext } from './contexto';

export function useTema() {
  const contexto = useContext(TemaContext);
  if (!contexto) throw new Error('useTema debe usarse dentro de <TemaProvider>');
  return contexto;
}
