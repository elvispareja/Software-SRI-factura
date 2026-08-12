/**
 * Estaciones de comprobante: qué cabecera corresponde a cada ruta.
 *
 * Vive fuera del componente porque `esRutaComprobante` la usa el Layout para
 * decidir si envuelve el contenido, y exportar funciones junto a componentes
 * rompe el Fast Refresh de React.
 */

import { FileText, Receipt, ScrollText, Truck } from 'lucide-react';

export const MAPA_WS = [
  {
    match: /^\/comprobantes(\/|$)/,
    titulo: 'Facturas',
    familia: 'COMPROBANTES',
    rail: 'var(--ws-rail-facturas)',
    Icon: FileText,
    iconPath: 'M5 3h8l4 4v14H7ZM14.5 3v4H19',
    meta: 'Facturación electrónica · SRI',
    tabs: [
      { label: 'Listado', to: '/comprobantes' },
      { label: 'Crear', to: '/comprobantes/nuevo' },
    ],
  },
  {
    match: /^\/liquidaciones(\/|$)/,
    titulo: 'Liquidación Compra',
    familia: 'LIQUIDACIÓN',
    rail: 'var(--ws-rail-liquidacion)',
    Icon: ScrollText,
    iconPath: 'M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z',
    meta: 'Compra generada · afecta caja/bancos',
    tabs: [
      { label: 'Listado', to: '/liquidaciones' },
      { label: 'Crear', to: '/liquidaciones/nueva' },
    ],
  },
  {
    match: /^\/retenciones(\/|$)/,
    titulo: 'Retenciones',
    familia: 'RETENCIÓN',
    rail: 'var(--ws-rail-retencion)',
    Icon: Receipt,
    iconPath: 'M14 2H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3v3l3-3h3a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2Z',
    meta: 'Comprobantes de retención · SRI',
    tabs: [
      { label: 'Listado', to: '/retenciones' },
      { label: 'Crear', to: '/retenciones/nueva' },
    ],
  },
  {
    match: /^\/guias(\/|$)/,
    titulo: 'Guía de Remisión',
    familia: 'GUÍA',
    rail: 'var(--ws-rail-guia)',
    Icon: Truck,
    iconPath: 'M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h2M12 18h2a2 2 0 0 1 2 2M7 18a2 2 0 0 1 2 2',
    meta: 'Transporte de mercadería · SRI',
    tabs: [
      { label: 'Listado', to: '/guias' },
      { label: 'Crear', to: '/guias/nueva' },
    ],
  },
];


/** Estación que corresponde a la ruta, o null si no es un comprobante. */
export function resolverEstacion(pathname) {
  return MAPA_WS.find((entrada) => entrada.match.test(pathname)) ?? null;
}

/** ¿La ruta pertenece a alguna estación de comprobante? */
export function esRutaComprobante(pathname) {
  return MAPA_WS.some((entrada) => entrada.match.test(pathname));
}
