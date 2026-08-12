import { describe, expect, it } from 'vitest';
import {
  CATALOGO_RECEPTORES,
  ESTADOS_RECEPTOR,
  ROLES_RECEPTOR,
  TIPOS_IDENTIFICACION,
} from './catalogoReceptores.js';
import { CATALOGO_ARTICULOS } from './catalogoArticulos.js';
import { TARIFAS_IVA } from '../lib/sri/impuestos.js';
import { validarIdentificacion } from '../lib/sri/identificacion.js';

/**
 * Los datos de demostración se ven cuando el backend no responde, así que
 * pasan por delante del usuario. Una identificación con dígito verificador
 * inválido ahí enseña a desconfiar del validador, que es lo contrario de lo
 * que hace falta. Esta prueba impide que se cuele una al añadir un registro.
 */

describe('catálogo de receptores', () => {
  it('todas las identificaciones son válidas según el algoritmo del SRI', () => {
    const invalidos = CATALOGO_RECEPTORES.filter(
      (receptor) =>
        !validarIdentificacion(receptor.tipoIdentificacion, receptor.identificacion).esValida,
    ).map((receptor) => `${receptor.razonSocial} (${receptor.identificacion})`);

    expect(invalidos).toEqual([]);
  });

  it('no hay identificaciones repetidas', () => {
    const identificaciones = CATALOGO_RECEPTORES.map((r) => r.identificacion);
    const repetidas = identificaciones.filter(
      (valor, indice) => identificaciones.indexOf(valor) !== indice,
    );

    // El consumidor final es el único que puede repetirse legítimamente.
    expect(repetidas.filter((valor) => valor !== '9999999999999')).toEqual([]);
  });

  it('los identificadores son únicos', () => {
    const ids = CATALOGO_RECEPTORES.map((r) => r.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('usa solo los tipos, roles y estados del catálogo', () => {
    for (const receptor of CATALOGO_RECEPTORES) {
      expect(TIPOS_IDENTIFICACION).toContain(receptor.tipoIdentificacion);
      expect(ROLES_RECEPTOR).toContain(receptor.rol);
      expect(ESTADOS_RECEPTOR).toContain(receptor.estado);
    }
  });

  it('incluye al menos un transportista y un proveedor activos', () => {
    // Las guías y las retenciones no se pueden demostrar sin ellos.
    const activos = CATALOGO_RECEPTORES.filter((r) => r.estado === 'Activo');

    expect(activos.some((r) => r.rol === 'Transportista')).toBe(true);
    expect(activos.some((r) => r.rol === 'Proveedor')).toBe(true);
  });
});

describe('catálogo de artículos', () => {
  it('los códigos de IVA existen en la tabla 17', () => {
    const codigosValidos = TARIFAS_IVA.map((t) => t.codigo);

    for (const articulo of CATALOGO_ARTICULOS) {
      expect(codigosValidos).toContain(String(articulo.codigoIva));
    }
  });

  it('no hay códigos de artículo repetidos', () => {
    const codigos = CATALOGO_ARTICULOS.map((a) => a.codigo);
    expect(new Set(codigos).size).toBe(codigos.length);
  });

  it('ningún precio es negativo', () => {
    for (const articulo of CATALOGO_ARTICULOS) {
      expect(Number(articulo.precio)).toBeGreaterThanOrEqual(0);
    }
  });

  it('el costo, cuando está, es un número válido', () => {
    // El catálogo de demostración no lleva costo: el listado no lo muestra y
    // el formulario arranca vacío. Se comprueba solo si algún registro lo trae,
    // para que añadirlo mal no pase inadvertido.
    for (const articulo of CATALOGO_ARTICULOS) {
      if (articulo.costo === undefined) continue;
      expect(Number(articulo.costo)).toBeGreaterThanOrEqual(0);
    }
  });

  it('solo los servicios tienen stock nulo', () => {
    for (const articulo of CATALOGO_ARTICULOS) {
      if (articulo.tipo === 'Servicio') expect(articulo.stock).toBeNull();
      else expect(articulo.stock).not.toBeNull();
    }
  });
});
