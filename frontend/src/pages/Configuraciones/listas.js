/**
 * Qué enseña cada listado de configuración y de dónde salen sus datos.
 *
 * Vive fuera del componente porque `Configuraciones` lo consulta para decidir
 * qué secciones ya tienen datos, y exportar constantes junto a componentes
 * rompe el Fast Refresh de React.
 */

import { usuarioDesdeApi } from '../../api/configuracion';

/** Configuración por sección: de dónde salen los datos y si se editan. */
export const LISTAS = {
  zonas: {
    tipo: 'zona',
    titulo: 'Zonas',
    subtitulo: 'Agrupaciones geográficas o comerciales para tus receptores.',
    ruta: '/configuracion/listas/zona',
    columnas: ['NOMBRE', 'DETALLE', 'ESTADO', 'ACCIONES'],
    vacio: 'No hay zonas configuradas. Crea la primera cuando necesites agrupar tus operaciones.',
    etiquetaAlta: 'Zona',
    editable: true,
  },
  vendedores: {
    tipo: 'vendedor',
    titulo: 'Vendedores',
    subtitulo: 'Quién atiende a cada cliente. Se puede asignar en Receptores.',
    ruta: '/configuracion/listas/vendedor',
    columnas: ['NOMBRE', 'PUESTO', 'ESTADO', 'ACCIONES'],
    vacio: 'No hay vendedores registrados.',
    etiquetaAlta: 'Vendedor',
    editable: true,
  },
  leyendas: {
    tipo: 'leyenda',
    titulo: 'Leyendas',
    subtitulo: 'Textos que se añaden al comprobante como información adicional.',
    ruta: '/configuracion/listas/leyenda',
    columnas: ['DESCRIPCIÓN', 'DETALLE', 'ESTADO', 'ACCIONES'],
    vacio: 'No hay leyendas configuradas.',
    etiquetaAlta: 'Leyenda',
    editable: true,
  },
  usuarios: {
    titulo: 'Usuarios',
    subtitulo: 'Cuentas con acceso al sistema. Se crean desde el registro.',
    ruta: '/configuracion/usuarios',
    columnas: ['USUARIO', 'CORREO', 'ROL', 'ESTADO'],
    vacio: 'No hay usuarios registrados.',
    editable: false,
    adaptador: usuarioDesdeApi,
  },
  impuestos: {
    titulo: 'Impuestos',
    subtitulo:
      'Tarifas de IVA de la tabla 17 del SRI. No se editan: sus códigos viajan en el XML.',
    ruta: '/configuracion/impuestos',
    columnas: ['NOMBRE', 'CÓDIGO', 'PORCENTAJE'],
    vacio: 'Sin tarifas.',
    editable: false,
    soloLectura: true,
  },
};

