/** Utilidades de texto para búsqueda y comparación. */

/**
 * Pasa a minúsculas y quita tildes descomponiendo en NFD y borrando el rango
 * de diacríticos combinantes (U+0300–U+036F). Así "Peréz" encuentra "perez".
 */
export function normalizarTexto(valor) {
  return String(valor ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .trim();
}

/** ¿El texto contiene el término, ignorando tildes y mayúsculas? */
export function contieneTexto(texto, termino) {
  return normalizarTexto(texto).includes(normalizarTexto(termino));
}
