import { describe, expect, it } from 'vitest';
import { contieneTexto, normalizarTexto } from './texto.js';

/**
 * Sin esto, buscar "perez" no encuentra "PÉREZ" y el usuario concluye que el
 * cliente no está registrado. Es la clase de fallo que nadie reporta como bug.
 */

describe('normalizarTexto', () => {
  it('quita tildes y pasa a minúsculas', () => {
    expect(normalizarTexto('PÉREZ')).toBe('perez');
    expect(normalizarTexto('Andrés Muñoz')).toBe('andres munoz');
  });

  it('cubre las cinco vocales acentuadas y la diéresis', () => {
    expect(normalizarTexto('áéíóúü')).toBe('aeiouu');
  });

  it('recorta espacios de los extremos', () => {
    expect(normalizarTexto('  Quito  ')).toBe('quito');
  });

  it('devuelve cadena vacía ante nulos, no "null"', () => {
    expect(normalizarTexto(null)).toBe('');
    expect(normalizarTexto(undefined)).toBe('');
  });

  it('convierte números a texto', () => {
    expect(normalizarTexto(1234)).toBe('1234');
  });

  it('reduce la ñ a n, y eso es lo que se busca', () => {
    // NFD descompone la ñ en "n" + tilde combinante (U+0303), que cae dentro
    // del rango que se borra. No es un descuido: quien escribe "munoz" en el
    // buscador espera encontrar a MUÑOZ.
    expect(normalizarTexto('ÑANDÚ')).toBe('nandu');
    expect(contieneTexto('MUÑOZ', 'munoz')).toBe(true);
  });
});

describe('contieneTexto', () => {
  it('encuentra ignorando tildes y mayúsculas', () => {
    expect(contieneTexto('PLÁSTICOS DEL LITORAL', 'plasticos')).toBe(true);
    expect(contieneTexto('José Andrés', 'andres')).toBe(true);
  });

  it('busca también en medio de la cadena', () => {
    expect(contieneTexto('001-001-000000123', '000123')).toBe(true);
  });

  it('un término vacío coincide con todo', () => {
    // Así el buscador muestra la lista completa mientras no se escribe nada.
    expect(contieneTexto('cualquier cosa', '')).toBe(true);
  });

  it('devuelve false cuando no hay coincidencia', () => {
    expect(contieneTexto('Guayaquil', 'quito')).toBe(false);
  });

  it('no explota con nulos en ninguno de los dos lados', () => {
    expect(contieneTexto(null, 'algo')).toBe(false);
    expect(contieneTexto('algo', null)).toBe(true);
  });
});
