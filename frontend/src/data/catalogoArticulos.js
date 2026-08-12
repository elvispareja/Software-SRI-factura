/**
 * Catálogo de artículos de demostración.
 *
 * Fuente única mientras no exista el backend: lo consumen tanto el listado de
 * Artículos como el buscador de la factura, para que no se desincronicen.
 * Se reemplaza por una llamada al API sin tocar los componentes.
 */

import { TARIFA_IVA_POR_DEFECTO } from '../lib/sri/impuestos.js';
import { normalizarTexto } from '../lib/texto.js';

const IVA = TARIFA_IVA_POR_DEFECTO;

export const CATALOGO_ARTICULOS = [
  { id: 1, codigo: 'PROD-001', nombre: 'Laptop Dell XPS 13', tipo: 'Producto', categoria: 'Tecnología', unidad: 'Unidad', precio: 1200.0, stock: 15, estado: 'Activo', codigoIva: IVA },
  { id: 2, codigo: 'SERV-001', nombre: 'Mantenimiento Preventivo', tipo: 'Servicio', categoria: 'Soporte', unidad: 'Servicio', precio: 45.0, stock: null, estado: 'Activo', codigoIva: IVA },
  { id: 3, codigo: 'PROD-002', nombre: 'Mouse Inalámbrico Logitech', tipo: 'Producto', categoria: 'Tecnología', unidad: 'Unidad', precio: 25.5, stock: 40, estado: 'Activo', codigoIva: IVA },
  { id: 4, codigo: 'PROD-003', nombre: 'Pan común - funda 500g', tipo: 'Producto', categoria: 'Alimentos', unidad: 'Unidad', precio: 1.85, stock: 120, estado: 'Activo', codigoIva: '0' },
  { id: 5, codigo: 'SERV-002', nombre: 'Consultoría contable mensual', tipo: 'Servicio', categoria: 'Profesional', unidad: 'Servicio', precio: 180.0, stock: null, estado: 'Activo', codigoIva: IVA },
  { id: 6, codigo: 'PROD-004', nombre: 'Teclado mecánico retroiluminado', tipo: 'Producto', categoria: 'Tecnología', unidad: 'Unidad', precio: 62.9, stock: 18, estado: 'Activo', codigoIva: IVA },
  { id: 7, codigo: 'PROD-005', nombre: 'Monitor LED 24"', tipo: 'Producto', categoria: 'Tecnología', unidad: 'Unidad', precio: 189.0, stock: 7, estado: 'Activo', codigoIva: IVA },
  { id: 8, codigo: 'PROD-006', nombre: 'Resma de papel bond A4', tipo: 'Producto', categoria: 'Oficina', unidad: 'Unidad', precio: 4.75, stock: 240, estado: 'Activo', codigoIva: IVA },
  { id: 9, codigo: 'PROD-007', nombre: 'Arroz flor - saco 25kg', tipo: 'Producto', categoria: 'Alimentos', unidad: 'Saco', precio: 32.5, stock: 60, estado: 'Activo', codigoIva: '0' },
  { id: 10, codigo: 'SERV-003', nombre: 'Instalación de red LAN', tipo: 'Servicio', categoria: 'Soporte', unidad: 'Servicio', precio: 320.0, stock: null, estado: 'Activo', codigoIva: IVA },
  { id: 11, codigo: 'SERV-004', nombre: 'Capacitación de personal (hora)', tipo: 'Servicio', categoria: 'Profesional', unidad: 'Hora', precio: 55.0, stock: null, estado: 'Activo', codigoIva: IVA },
  { id: 12, codigo: 'PROD-008', nombre: 'Disco SSD 1TB NVMe', tipo: 'Producto', categoria: 'Tecnología', unidad: 'Unidad', precio: 98.0, stock: 3, estado: 'Activo', codigoIva: IVA },
  { id: 13, codigo: 'PROD-009', nombre: 'Silla ergonómica de oficina', tipo: 'Producto', categoria: 'Oficina', unidad: 'Unidad', precio: 245.0, stock: 0, estado: 'Inactivo', codigoIva: IVA },
  { id: 14, codigo: 'SERV-005', nombre: 'Diseño de identidad de marca', tipo: 'Servicio', categoria: 'Profesional', unidad: 'Servicio', precio: 850.0, stock: null, estado: 'Inactivo', codigoIva: IVA },
];

export const TIPOS_ARTICULO = ['Producto', 'Servicio'];
export const ESTADOS_ARTICULO = ['Activo', 'Inactivo'];
export const CATEGORIAS_ARTICULO = [...new Set(CATALOGO_ARTICULOS.map((a) => a.categoria))].sort();

/** Búsqueda por código o nombre, sin distinguir mayúsculas ni tildes. */
export function buscarArticulos(termino, limite = 6) {
  const consulta = normalizarTexto(termino);
  if (consulta === '') return [];

  return CATALOGO_ARTICULOS.filter(
    (articulo) =>
      articulo.estado === 'Activo' &&
      (normalizarTexto(articulo.codigo).includes(consulta) ||
        normalizarTexto(articulo.nombre).includes(consulta)),
  ).slice(0, limite);
}
