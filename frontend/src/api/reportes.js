/**
 * Reportes contra el API.
 *
 * Los totales se calculan en el servidor y no aquí por dos razones: los
 * importes viven en `Decimal` y traerlos al navegador para sumarlos los
 * degrada a `float`, y un negocio con miles de comprobantes no puede
 * descargarlos todos para pintar una tarjeta con el total del mes.
 */

import { api } from './cliente';

export const MESES = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
];

/** Nombre corto para los ejes de las gráficas. */
export const MESES_CORTOS = MESES.map((mes) => mes.slice(0, 3));

const numero = (valor) => Number(valor ?? 0);

export const resumenDesdeApi = (resumen) => ({
  desde: resumen.desde,
  hasta: resumen.hasta,
  comprobantes: resumen.comprobantes,
  subtotal: numero(resumen.subtotal),
  descuento: numero(resumen.descuento),
  iva: numero(resumen.iva),
  total: numero(resumen.total),
  ticketPromedio: numero(resumen.ticket_promedio),
});

/** Del panel del API a la forma que pinta el Dashboard. */
export const panelDesdeApi = (panel) => ({
  hoy: panel.hoy,
  // '1' es pruebas y '2' producción, según la ficha técnica del SRI.
  ambiente: panel.ambiente ?? '1',
  mes: resumenDesdeApi(panel.mes),
  anio: resumenDesdeApi(panel.anio),
  porTipo: (panel.por_tipo ?? []).map((fila) => ({
    tipo: fila.tipo,
    cantidad: fila.cantidad,
    total: numero(fila.total),
  })),
  serieMensual: (panel.serie_mensual ?? []).map((fila) => ({
    mes: fila.mes,
    etiqueta: MESES_CORTOS[fila.mes - 1] ?? String(fila.mes),
    cantidad: fila.cantidad,
    total: numero(fila.total),
  })),
  topClientes: (panel.top_clientes ?? []).map((fila) => ({
    razonSocial: fila.razon_social,
    identificacion: fila.identificacion,
    comprobantes: fila.comprobantes,
    total: numero(fila.total),
  })),
  topArticulos: (panel.top_articulos ?? []).map((fila) => ({
    codigo: fila.codigo,
    descripcion: fila.descripcion,
    cantidad: numero(fila.cantidad),
    total: numero(fila.total),
  })),
  estadoSri: {
    porEstado: (panel.estado_sri?.por_estado ?? []).map((fila) => ({
      estado: fila.estado,
      cantidad: fila.cantidad,
    })),
    total: panel.estado_sri?.total ?? 0,
    requierenAtencion: panel.estado_sri?.requieren_atencion ?? 0,
  },
  porCobrar: {
    comprobantes: panel.por_cobrar?.comprobantes ?? 0,
    total: numero(panel.por_cobrar?.total),
    aCredito: numero(panel.por_cobrar?.a_credito),
  },
});

export const ivaDesdeApi = (reporte) => ({
  periodoFiscal: reporte.periodo_fiscal,
  tarifas: (reporte.tarifas ?? []).map((fila) => ({
    codigoIva: fila.codigo_iva,
    porcentaje: numero(fila.porcentaje),
    baseImponible: numero(fila.base_imponible),
    valorIva: numero(fila.valor_iva),
  })),
  baseTotal: numero(reporte.base_total),
  ivaTotal: numero(reporte.iva_total),
});

export const retencionesDesdeApi = (reporte) => ({
  periodoFiscal: reporte.periodo_fiscal,
  comprobantes: reporte.comprobantes,
  conceptos: (reporte.conceptos ?? []).map((fila) => ({
    codigoImpuesto: fila.codigo_impuesto,
    codigoRetencion: fila.codigo_retencion,
    lineas: fila.lineas,
    baseImponible: numero(fila.base_imponible),
    valorRetenido: numero(fila.valor_retenido),
  })),
  totalRenta: numero(reporte.total_renta),
  totalIva: numero(reporte.total_iva),
  totalRetenido: numero(reporte.total_retenido),
});

// Todas aceptan `opciones` para poder pasar la señal de cancelación: al
// cambiar de mes mientras carga, la respuesta vieja no debe pisar a la nueva.
export const cargarPanel = (opciones) => api.obtener('/reportes/panel', undefined, opciones);

export const cargarClientes = (anio, mes, opciones) =>
  api.obtener('/reportes/clientes', { anio, mes, limite: 10 }, opciones);

export const cargarArticulos = (anio, mes, opciones) =>
  api.obtener('/reportes/articulos', { anio, mes, limite: 10 }, opciones);

export const cargarVentasPorMes = (anio, opciones) =>
  api.obtener('/reportes/ventas/por-mes', { anio }, opciones);

export const cargarIva = (anio, mes, opciones) =>
  api.obtener('/reportes/iva', { anio, mes }, opciones);

export const cargarRetenciones = (anio, mes, opciones) =>
  api.obtener('/reportes/retenciones', { anio, mes }, opciones);

export const cargarVentasPorTipo = (anio, mes, opciones) =>
  api.obtener('/reportes/ventas/por-tipo', { anio, mes }, opciones);

export const cargarResumenVentas = (anio, mes, opciones) =>
  api.obtener('/reportes/ventas', { anio, mes }, opciones);

export const cargarEstadoSri = (anio, mes, opciones) =>
  api.obtener('/reportes/estado-sri', { anio, mes }, opciones);

export const cargarNotasVenta = (anio, mes, opciones) =>
  api.obtener('/reportes/notas-venta', { anio, mes }, opciones);

export const cargarCotizaciones = (anio, mes, opciones) =>
  api.obtener('/reportes/cotizaciones', { anio, mes }, opciones);

export const cargarNotas = (anio, mes, opciones) =>
  api.obtener('/reportes/notas', { anio, mes }, opciones);

export const cargarEgresos = (anio, mes, opciones) =>
  api.obtener('/reportes/egresos', { anio, mes }, opciones);

// Estos dos no llevan período: el inventario y el padrón de receptores
// son fotos del estado actual, no de un mes.
export const cargarInventario = (opciones) =>
  api.obtener('/reportes/inventario', undefined, opciones);

export const cargarReceptores = (rol, opciones) =>
  api.obtener('/reportes/receptores', rol ? { rol } : undefined, opciones);

/**
 * Se devuelve la URL en vez de hacer `fetch`: así el navegador gestiona la
 * descarga con su propio diálogo, sin tener que construir un Blob a mano.
 *
 * El año y el mes se omiten si no vienen porque el inventario y el padrón de
 * receptores no llevan período: mandarles `anio=undefined` daría un 422.
 */
const urlReporte = (reporte, extension, anio, mes) => {
  const parametros = new URLSearchParams();
  if (anio) parametros.set('anio', String(anio));
  if (mes) parametros.set('mes', String(mes));
  const consulta = parametros.toString();
  return api.urlDescarga(`/reportes/${reporte}/${extension}${consulta ? `?${consulta}` : ''}`);
};

/** URL de descarga del CSV. */
export const urlCsv = (reporte, anio, mes) => urlReporte(reporte, 'csv', anio, mes);

/**
 * URL de descarga del PDF.
 *
 * No todos los reportes tienen las dos caras: notas de venta, cotizaciones y
 * estado ante el SRI solo se sirven en PDF, así que la pantalla debe
 * deshabilitar Excel en esos casos en vez de ofrecer una descarga que falla.
 */
export const urlPdf = (reporte, anio, mes) => urlReporte(reporte, 'pdf', anio, mes);


// --------------------------------------------------------------------------
// Reportes por familia de documento
// --------------------------------------------------------------------------

const receptorDesdeApi = (fila) => ({
  razonSocial: fila.razon_social,
  identificacion: fila.identificacion,
  comprobantes: fila.comprobantes,
  total: numero(fila.total),
  conFactura: fila.con_factura ?? false,
});

export const porReceptorDesdeApi = (reporte) => ({
  receptores: (reporte.receptores ?? []).map(receptorDesdeApi),
  comprobantes: reporte.comprobantes ?? 0,
  total: numero(reporte.total),
  // Solo lo trae el reporte de cotizaciones.
  receptoresConFactura: reporte.receptores_con_factura ?? 0,
});

export const notasDesdeApi = (reporte) => ({
  notasCredito: reporte.notas_credito ?? 0,
  totalCredito: numero(reporte.total_credito),
  notasDebito: reporte.notas_debito ?? 0,
  totalDebito: numero(reporte.total_debito),
  // El servidor lo da calculado para que nadie lo sume al revés: una nota de
  // crédito resta y una de débito suma.
  neto: numero(reporte.neto),
  documentos: (reporte.documentos ?? []).map((d) => ({
    numero: d.numero,
    tipo: d.tipo,
    fecha: d.fecha,
    receptor: d.receptor,
    documentoModificado: d.documento_modificado,
    motivo: d.motivo,
    total: numero(d.total),
  })),
});

export const egresosDesdeApi = (reporte) => ({
  tipos: (reporte.tipos ?? []).map((t) => ({
    tipo: t.tipo,
    deducible: t.deducible,
    gastos: t.gastos,
    subtotal: numero(t.subtotal),
    iva: numero(t.iva),
    total: numero(t.total),
  })),
  total: numero(reporte.total),
  totalDeducible: numero(reporte.total_deducible),
  ivaSoportado: numero(reporte.iva_soportado),
  totalPagado: numero(reporte.total_pagado),
});


export const inventarioDesdeApi = (reporte) => ({
  articulos: (reporte.articulos ?? []).map((a) => ({
    codigo: a.codigo,
    nombre: a.nombre,
    tipo: a.tipo,
    categoria: a.categoria,
    unidad: a.unidad,
    // null en los servicios: no manejan existencias.
    stock: a.stock === null || a.stock === undefined ? null : numero(a.stock),
    stockMinimo: numero(a.stock_minimo),
    costo: numero(a.costo),
    precio: numero(a.precio),
    valor: numero(a.valor),
    bajoMinimo: a.bajo_minimo,
  })),
  totalArticulos: reporte.total_articulos ?? 0,
  productos: reporte.productos ?? 0,
  servicios: reporte.servicios ?? 0,
  valorInventario: numero(reporte.valor_inventario),
  bajoMinimo: reporte.bajo_minimo ?? 0,
});

export const receptoresDesdeApi = (reporte) => ({
  receptores: (reporte.receptores ?? []).map((r) => ({
    razonSocial: r.razon_social,
    identificacion: r.identificacion,
    tipoIdentificacion: r.tipo_identificacion,
    rol: r.rol,
    correo: r.correo,
    telefono: r.telefono,
    facturado: numero(r.facturado),
  })),
  total: reporte.total ?? 0,
  clientes: reporte.clientes ?? 0,
  proveedores: reporte.proveedores ?? 0,
  transportistas: reporte.transportistas ?? 0,
});
