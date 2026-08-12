import { describe, expect, it } from 'vitest';
import {
  estadoStock,
  precioConImpuesto,
  precioDesdeUtilidad,
  utilidadDesdePrecio,
  utilidadUnitaria,
} from './precios.js';

/**
 * Markup y margen son la confusión que más descuadra precios: un 50% sobre un
 * costo de 10 da 15 o 20 según la base. Estas pruebas fijan ambas fórmulas y
 * la relación de ida y vuelta entre ellas.
 */

describe('precioDesdeUtilidad', () => {
  it('markup: costo 10 + 50% da 15', () => {
    expect(precioDesdeUtilidad(10, 50, 'costo')).toBe(15);
  });

  it('margen: costo 10 con 50% da 20', () => {
    expect(precioDesdeUtilidad(10, 50, 'venta')).toBe(20);
  });

  it('usa markup por defecto', () => {
    expect(precioDesdeUtilidad(10, 50)).toBe(precioDesdeUtilidad(10, 50, 'costo'));
  });

  it('un margen del 100% o más es imposible y devuelve 0', () => {
    // El precio tendería a infinito; devolver 0 evita mostrar "Infinity".
    expect(precioDesdeUtilidad(10, 100, 'venta')).toBe(0);
    expect(precioDesdeUtilidad(10, 150, 'venta')).toBe(0);
  });

  it('con utilidad 0 el precio es el costo', () => {
    expect(precioDesdeUtilidad(37.5, 0, 'costo')).toBe(37.5);
    expect(precioDesdeUtilidad(37.5, 0, 'venta')).toBe(37.5);
  });

  it('no admite costos negativos', () => {
    expect(precioDesdeUtilidad(-10, 50)).toBe(0);
  });

  it('acepta valores de texto con coma decimal', () => {
    expect(precioDesdeUtilidad('10,50', '20')).toBe(12.6);
  });
});

describe('utilidadDesdePrecio', () => {
  it('es la inversa del markup', () => {
    expect(utilidadDesdePrecio(10, 15, 'costo')).toBe(50);
  });

  it('es la inversa del margen', () => {
    expect(utilidadDesdePrecio(10, 20, 'venta')).toBe(50);
  });

  it('ida y vuelta conserva el porcentaje', () => {
    for (const base of ['costo', 'venta']) {
      const precio = precioDesdeUtilidad(80, 25, base);
      expect(utilidadDesdePrecio(80, precio, base)).toBe(25);
    }
  });

  it('devuelve 0 en vez de dividir por cero', () => {
    expect(utilidadDesdePrecio(0, 50, 'costo')).toBe(0);
    expect(utilidadDesdePrecio(10, 0, 'venta')).toBe(0);
  });

  it('reporta utilidad negativa cuando se vende bajo el costo', () => {
    expect(utilidadDesdePrecio(100, 80, 'costo')).toBe(-20);
  });
});

describe('precioConImpuesto', () => {
  it('aplica la tarifa al precio sin impuesto', () => {
    expect(precioConImpuesto(100, 15)).toBe(115);
    expect(precioConImpuesto(10, 0)).toBe(10);
  });

  it('redondea a dos decimales', () => {
    expect(precioConImpuesto(0.99, 15)).toBe(1.14);
  });
});

describe('utilidadUnitaria', () => {
  it('es la diferencia entre precio y costo', () => {
    expect(utilidadUnitaria(10, 15)).toBe(5);
    expect(utilidadUnitaria(15, 10)).toBe(-5);
  });
});

describe('estadoStock', () => {
  it('devuelve null si el artículo no maneja stock', () => {
    // Los servicios no tienen existencias: no deben pintar semáforo.
    expect(estadoStock({ stock: null })).toBeNull();
    expect(estadoStock({ stock: undefined })).toBeNull();
    expect(estadoStock({ stock: '' })).toBeNull();
  });

  it('marca agotado en cero o menos', () => {
    expect(estadoStock({ stock: 0, stockMinimo: 5 }).nivel).toBe('agotado');
    expect(estadoStock({ stock: -3, stockMinimo: 5 }).nivel).toBe('agotado');
  });

  it('marca crítico al tocar el mínimo', () => {
    expect(estadoStock({ stock: 5, stockMinimo: 5 }).nivel).toBe('critico');
    expect(estadoStock({ stock: 3, stockMinimo: 5 }).nivel).toBe('critico');
  });

  it('marca reorden entre el mínimo y el punto de reposición', () => {
    expect(estadoStock({ stock: 8, stockMinimo: 5, puntoReorden: 10 }).nivel).toBe('reorden');
  });

  it('marca ok por encima de todos los umbrales', () => {
    expect(estadoStock({ stock: 40, stockMinimo: 5, puntoReorden: 10 }).nivel).toBe('ok');
  });

  it('sin punto de reorden configurado no inventa el nivel intermedio', () => {
    expect(estadoStock({ stock: 8, stockMinimo: 5, puntoReorden: 0 }).nivel).toBe('ok');
  });

  it('el mínimo manda sobre el reorden cuando ambos aplican', () => {
    expect(estadoStock({ stock: 4, stockMinimo: 5, puntoReorden: 10 }).nivel).toBe('critico');
  });
});
