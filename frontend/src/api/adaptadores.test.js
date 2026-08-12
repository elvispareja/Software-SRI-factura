import { describe, expect, it } from 'vitest';
import {
  articuloDesdeApi,
  articuloHaciaApi,
  comprobanteDesdeApi,
  receptorDesdeApi,
  receptorHaciaApi,
} from './adaptadores.js';

/**
 * Los adaptadores traducen entre el snake_case del API y el camelCase de la
 * interfaz. Un campo mal mapeado no rompe nada visiblemente: guarda un null
 * donde debía ir un dato, y se descubre cuando el SRI rechaza el comprobante.
 */

describe('receptorDesdeApi', () => {
  it('traduce los campos del API', () => {
    const receptor = receptorDesdeApi({
      id: 7,
      tipo_identificacion: 'RUC',
      identificacion: '1790016919001',
      razon_social: 'EMPRESA DEMO S.A.',
      nombre_comercial: 'DEMO',
      tipo_persona: 'Jurídica',
      rol: 'Cliente',
      correo: 'demo@empresa.ec',
      direccion: 'Av. Amazonas',
      estado: 'Activo',
    });

    // `toMatchObject` y no `toEqual`: el adaptador crece cuando una pantalla
    // necesita un campo más, y una igualdad exacta convertiría cada ampliación
    // legítima en un fallo.
    expect(receptor).toMatchObject({
      id: 7,
      tipoIdentificacion: 'RUC',
      identificacion: '1790016919001',
      razonSocial: 'EMPRESA DEMO S.A.',
      nombreComercial: 'DEMO',
      tipoPersona: 'Jurídica',
      rol: 'Cliente',
      correo: 'demo@empresa.ec',
      direccion: 'Av. Amazonas',
      estado: 'Activo',
    });
  });

  it('rellena la configuración comercial con sus valores por defecto', () => {
    // La pantalla de clientes los pinta como texto; un `undefined` ahí saldría
    // como celda en blanco sin explicar que es el valor por defecto.
    const receptor = receptorDesdeApi({ id: 1, direccion: 'Quito' });

    expect(receptor.metodoCancelacion).toBe('Contado');
    expect(receptor.listaPrecio).toBe('PVP 1');
    expect(receptor.vendedor).toBe('Sin asignar');
    expect(receptor.zona).toBe('Sin zona');
    expect(receptor.descuento).toBe('0');
    expect(receptor.creditoMaximo).toBe('0');
  });

  it('convierte los nulos opcionales en cadena vacía', () => {
    // Un null llegaría a un <input value={null}> y React avisaría en consola.
    const receptor = receptorDesdeApi({ nombre_comercial: null, correo: null });

    expect(receptor.nombreComercial).toBe('');
    expect(receptor.correo).toBe('');
  });
});

describe('receptorHaciaApi', () => {
  it('manda null en los opcionales vacíos, no cadena vacía', () => {
    // Pydantic acepta null en un `str | None`; "" pasaría la validación y
    // guardaría un correo vacío como si fuera un dato.
    const cuerpo = receptorHaciaApi({
      tipoIdentificacion: 'Cédula',
      identificacion: '1710034065',
      razonSocial: 'JUAN PEREZ',
      direccion: 'Quito',
      nombreComercial: '',
      correo: '',
      provincia: '',
    });

    expect(cuerpo.nombre_comercial).toBeNull();
    expect(cuerpo.correo).toBeNull();
    expect(cuerpo.provincia).toBeNull();
  });

  it('los importes vacíos viajan como "0", no como null', () => {
    const cuerpo = receptorHaciaApi({ descuento: '', creditoMaximo: undefined });

    expect(cuerpo.descuento).toBe('0');
    expect(cuerpo.credito_maximo).toBe('0');
  });

  it('da Activo por defecto si no se indicó estado', () => {
    expect(receptorHaciaApi({}).estado).toBe('Activo');
    expect(receptorHaciaApi({ estado: 'Inactivo' }).estado).toBe('Inactivo');
  });
});

describe('receptorDesdeApi + receptorHaciaApi (ida y vuelta)', () => {
  it('no pierde campos al editar un receptor sin tocar nada', () => {
    // Antes, receptorDesdeApi solo devolvía 9 de 20 campos: guardar sin
    // tocar nada borraba vendedor, zona y crédito máximo porque el formulario
    // nunca los recibió. Este registro trae los 20 campos que da el API.
    const registroCompleto = {
      id: 42,
      tipo_identificacion: 'RUC',
      identificacion: '1790016919001',
      razon_social: 'EMPRESA DEMO S.A.',
      nombre_comercial: 'DEMO',
      tipo_persona: 'Jurídica',
      rol: 'Proveedor',
      correo: 'demo@empresa.ec',
      correo2: 'copia@empresa.ec',
      telefono1: '0999999999',
      telefono2: '022222222',
      direccion: 'Av. Amazonas N21-147',
      provincia: 'Pichincha',
      canton: 'Quito',
      metodo_cancelacion: 'Crédito',
      vendedor: 'Diego Ruiz',
      lista_precio: 'PVP 3',
      zona: 'Norte',
      descuento: '5',
      credito_maximo: '1500',
      estado: 'Activo',
    };

    const cuerpo = receptorHaciaApi(receptorDesdeApi(registroCompleto));

    // `id` no viaja de vuelta a propósito: lo pone la URL, no el cuerpo.
    const { id: _id, ...esperado } = registroCompleto;
    expect(cuerpo).toEqual(esperado);
  });
});

describe('articuloDesdeApi', () => {
  it('convierte a número los importes que el API manda como texto', () => {
    // El backend serializa Decimal como string; sin esto, "12.50" + 1 sería
    // "12.501" en cualquier suma de la interfaz.
    const articulo = articuloDesdeApi({
      id: 1,
      codigo: 'P-001',
      nombre: 'Laptop',
      precio: '1200.000000',
      costo: '900.000000',
      stock: '5.000000',
      codigo_iva: '4',
    });

    expect(articulo.precio).toBe(1200);
    expect(articulo.costo).toBe(900);
    expect(articulo.stock).toBe(5);
    expect(articulo.codigoIva).toBe('4');
  });

  it('distingue stock null (servicio) de stock cero (agotado)', () => {
    expect(articuloDesdeApi({ stock: null }).stock).toBeNull();
    expect(articuloDesdeApi({ stock: '0' }).stock).toBe(0);
  });

  it('rellena la categoría ausente', () => {
    expect(articuloDesdeApi({ categoria: null }).categoria).toBe('Sin categoría');
  });
});

describe('articuloHaciaApi', () => {
  it('manda null en los opcionales vacíos y "0" en los importes', () => {
    const cuerpo = articuloHaciaApi({
      codigo: 'P-001',
      nombre: 'Laptop',
      codigoAuxiliar: '',
      marca: '',
      costo: '',
      precio: '',
      stockMinimo: '',
    });

    expect(cuerpo.codigo_auxiliar).toBeNull();
    expect(cuerpo.marca).toBeNull();
    expect(cuerpo.costo).toBe('0');
    expect(cuerpo.precio).toBe('0');
    expect(cuerpo.stock_minimo).toBe('0');
  });

  it('conserva el stock nulo de los servicios', () => {
    expect(articuloHaciaApi({ stock: undefined }).stock).toBeNull();
    expect(articuloHaciaApi({ stock: '0' }).stock).toBe('0');
  });
});

describe('articuloDesdeApi + articuloHaciaApi (ida y vuelta)', () => {
  it('no pierde campos al editar un artículo sin tocar nada', () => {
    // Los 18 campos que da el API. La ida y vuelta debe conservarlos todos:
    // un campo que se agregue a uno de los dos adaptadores y se olvide en el
    // otro se borraría en silencio al guardar sin tocar nada.
    const registroCompleto = {
      id: 9,
      codigo: 'P-001',
      codigo_auxiliar: 'AUX-1',
      nombre: 'Laptop 14"',
      detalle: 'Core i5, 16GB RAM',
      tipo: 'Producto',
      categoria: 'Cómputo',
      marca: 'Genérica',
      unidad: 'Unidad',
      bodega: 'Bodega Principal',
      ubicacion: 'Pasillo 3',
      // El backend serializa Decimal como texto con seis decimales.
      precio: '1200.000000',
      costo: '900.000000',
      stock: '5.000000',
      stock_minimo: '2.000000',
      punto_reorden: '3.000000',
      stock_maximo: '20.000000',
      codigo_iva: '4',
      codigo_ice: null,
      estado: 'Activo',
    };

    const cuerpo = articuloHaciaApi(articuloDesdeApi(registroCompleto));

    // `id` no viaja de vuelta a propósito: lo pone la URL, no el cuerpo.
    // `precio`, `costo` y `stock` sí cambian de forma en el camino —de texto a
    // número, porque así los usa la interfaz para calcular—, y eso es
    // conocido y deliberado, no una pérdida de dato: el valor numérico es el
    // mismo. `stock_minimo`, `punto_reorden` y `stock_maximo` viajan como
    // texto sin parsear en los dos sentidos, así que sí se comparan tal cual.
    const { id: _id, ...esperado } = registroCompleto;
    expect(cuerpo).toEqual({
      ...esperado,
      precio: 1200,
      costo: 900,
      stock: 5,
    });
  });
});

describe('comprobanteDesdeApi', () => {
  it('expone la clave de acceso y la autorización que usan las acciones', () => {
    const comprobante = comprobanteDesdeApi({
      id: 3,
      numero: '001-001-000000003',
      tipo: 'Factura',
      receptor_razon_social: 'CLIENTE DEMO',
      receptor_identificacion: '1790016919001',
      fecha_emision: '2026-08-09',
      importe_total: '1150.000000',
      metodo: 'Contado',
      estado_sri: 'Autorizado',
      estado_pago: 'Pagado',
      clave_acceso: '0'.repeat(49),
      numero_autorizacion: '1122334455',
    });

    expect(comprobante.total).toBe(1150);
    expect(comprobante.estadoSRI).toBe('Autorizado');
    expect(comprobante.claveAcceso).toHaveLength(49);
    expect(comprobante.numeroAutorizacion).toBe('1122334455');
  });
});
