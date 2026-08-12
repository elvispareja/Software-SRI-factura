import { describe, expect, it } from 'vitest';
import {
  CONSUMIDOR_FINAL,
  validarCedula,
  validarIdentificacion,
  validarRuc,
} from './identificacion.js';

/**
 * Las identificaciones mal tecleadas son de los rechazos más frecuentes del
 * SRI. Los dígitos verificadores de abajo están calculados con el algoritmo
 * oficial, no copiados de documentos reales: son válidos aritméticamente sin
 * pertenecer a ninguna persona ni empresa.
 */

// 1710034065 → suma ponderada 2,1,2,1,2,1,2,1,2 sobre los 9 primeros dígitos.
const CEDULA_VALIDA = '1710034065';
const RUC_NATURAL_VALIDO = '1710034065001';
const RUC_SOCIEDAD_VALIDO = '1790016919001';
const RUC_PUBLICO_VALIDO = '1760001550001';

describe('validarCedula', () => {
  it('acepta una cédula con dígito verificador correcto', () => {
    expect(validarCedula(CEDULA_VALIDA).esValida).toBe(true);
  });

  it('rechaza si el verificador no coincide', () => {
    const resultado = validarCedula('1710034066');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/verificador/i);
  });

  it('exige exactamente 10 dígitos', () => {
    expect(validarCedula('171003406').error).toMatch(/10 dígitos/);
    expect(validarCedula('17100340655').error).toMatch(/10 dígitos/);
  });

  it('rechaza caracteres que no sean dígitos', () => {
    expect(validarCedula('17100340a5').error).toMatch(/solo admite dígitos/i);
  });

  it('valida el código de provincia', () => {
    // 00 y 25 no existen; 30 sí, es el de residentes en el exterior.
    expect(validarCedula('0010034065').error).toMatch(/provincia/i);
    expect(validarCedula('2510034065').error).toMatch(/provincia/i);
  });

  it('rechaza un tercer dígito mayor que 5: está reservado para RUC', () => {
    const resultado = validarCedula('1760034065');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/tercer dígito/i);
  });

  it('tolera espacios alrededor y entradas nulas', () => {
    expect(validarCedula(`  ${CEDULA_VALIDA}  `).esValida).toBe(true);
    expect(validarCedula(null).esValida).toBe(false);
    expect(validarCedula(undefined).esValida).toBe(false);
  });
});

describe('validarRuc', () => {
  it('acepta el RUC de consumidor final', () => {
    const resultado = validarRuc(CONSUMIDOR_FINAL);
    expect(resultado.esValida).toBe(true);
    expect(resultado.tipo).toBe('consumidor final');
  });

  it('acepta un RUC de persona natural (cédula + 001)', () => {
    const resultado = validarRuc(RUC_NATURAL_VALIDO);
    expect(resultado.esValida).toBe(true);
    expect(resultado.tipo).toBe('persona natural');
  });

  it('rechaza un RUC natural cuya cédula no es válida', () => {
    const resultado = validarRuc('1710034066001');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/persona natural/i);
  });

  it('acepta un RUC de sociedad privada (tercer dígito 9, módulo 11)', () => {
    const resultado = validarRuc(RUC_SOCIEDAD_VALIDO);
    expect(resultado.esValida).toBe(true);
    expect(resultado.tipo).toBe('sociedad privada');
  });

  it('rechaza una sociedad con verificador equivocado', () => {
    const resultado = validarRuc('1790016918001');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/verificador/i);
  });

  it('acepta un RUC del sector público (tercer dígito 6)', () => {
    const resultado = validarRuc(RUC_PUBLICO_VALIDO);
    expect(resultado.esValida).toBe(true);
    expect(resultado.tipo).toBe('sector público');
  });

  it('exige 13 dígitos', () => {
    expect(validarRuc('179001691900').error).toMatch(/13 dígitos/);
  });

  it('rechaza el establecimiento 000', () => {
    const resultado = validarRuc('1790016919000');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/establecimiento/i);
  });

  it('rechaza un tercer dígito que no corresponde a ningún contribuyente', () => {
    // 7 y 8 no están asignados a ningún tipo.
    const resultado = validarRuc('1770016919001');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/tercer dígito/i);
  });

  it('valida el código de provincia', () => {
    expect(validarRuc('9990016919001').error).toMatch(/provincia/i);
  });
});

describe('validarIdentificacion', () => {
  it('enruta según el tipo elegido en el formulario', () => {
    expect(validarIdentificacion('Cédula', CEDULA_VALIDA).esValida).toBe(true);
    expect(validarIdentificacion('RUC', RUC_SOCIEDAD_VALIDO).esValida).toBe(true);
  });

  it('exige el RUC genérico para consumidor final', () => {
    expect(validarIdentificacion('Consumidor Final', CONSUMIDOR_FINAL).esValida).toBe(true);

    const resultado = validarIdentificacion('Consumidor Final', '1234567890123');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toContain(CONSUMIDOR_FINAL);
  });

  it('solo exige longitud mínima en pasaporte e identificación del exterior', () => {
    // No tienen algoritmo de verificación: inventar uno rechazaría documentos
    // legítimos de otros países.
    expect(validarIdentificacion('Pasaporte', 'AB1234567').esValida).toBe(true);
    expect(validarIdentificacion('Pasaporte', 'AB').esValida).toBe(false);
    expect(validarIdentificacion('Identificación del Exterior', 'X-99').esValida).toBe(true);
  });

  it('avisa cuando no se eligió tipo', () => {
    const resultado = validarIdentificacion(undefined, '1710034065');
    expect(resultado.esValida).toBe(false);
    expect(resultado.error).toMatch(/selecciona un tipo/i);
  });
});
