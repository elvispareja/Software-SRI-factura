import { describe, expect, it } from 'vitest';
import { primerNombre, saludoCompleto, saludoSegunHora } from './saludo.js';

describe('saludoSegunHora', () => {
  it('elige el saludo según la franja del día', () => {
    expect(saludoSegunHora(0)).toBe('Buenos días');
    expect(saludoSegunHora(11)).toBe('Buenos días');
    expect(saludoSegunHora(12)).toBe('Buenas tardes');
    expect(saludoSegunHora(18)).toBe('Buenas tardes');
    expect(saludoSegunHora(19)).toBe('Buenas noches');
    expect(saludoSegunHora(23)).toBe('Buenas noches');
  });
});

describe('primerNombre', () => {
  it('toma solo el primer nombre', () => {
    // Saludar con el nombre completo suena a carta del banco.
    expect(primerNombre('Ana Salazar Vera')).toBe('Ana');
    expect(primerNombre('Juan')).toBe('Juan');
  });

  it('tolera espacios de más y valores ausentes', () => {
    expect(primerNombre('   Ana   Salazar  ')).toBe('Ana');
    expect(primerNombre('')).toBe('');
    expect(primerNombre(null)).toBe('');
    expect(primerNombre(undefined)).toBe('');
  });
});

describe('saludoCompleto', () => {
  it('incluye el nombre cuando se conoce', () => {
    expect(saludoCompleto('Ana Salazar', 10)).toBe('Buenos días, Ana');
  });

  it('sin nombre, saluda igual pero sin coma colgando', () => {
    expect(saludoCompleto(null, 10)).toBe('Buenos días');
    expect(saludoCompleto('', 20)).toBe('Buenas noches');
  });
});
