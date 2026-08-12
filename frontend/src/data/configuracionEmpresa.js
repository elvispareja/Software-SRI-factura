/**
 * Configuración de la empresa emisora.
 *
 * Todo lo que hay aquí alimenta directamente la cabecera del XML del SRI:
 * el RUC, la razón social, la dirección matriz y el par establecimiento/punto
 * de emisión con el que se arma la clave de acceso y el secuencial.
 */

export const REGIMENES = [
  'Régimen General',
  'RIMPE - Emprendedor',
  'RIMPE - Negocio Popular',
  'Contribuyente Especial',
];

export const AMBIENTES_SRI = [
  { codigo: '1', nombre: 'Pruebas' },
  { codigo: '2', nombre: 'Producción' },
];

export const TIPOS_EMISION = [{ codigo: '1', nombre: 'Emisión Normal' }];

export const EMPRESA_INICIAL = {
  ruc: '1790016919001',
  razonSocial: 'MI EMPRESA DEMO S.A.',
  nombreComercial: 'DEMO',
  direccionMatriz: 'Av. Amazonas N21-147 y Roca',
  provincia: 'Pichincha',
  canton: 'Quito',
  telefono: '022345678',
  correo: 'facturacion@miempresa.ec',
  regimen: 'Régimen General',
  obligadoContabilidad: true,
  agenteRetencion: '',
  contribuyenteRimpe: false,
  ambiente: '1',
  tipoEmision: '1',
};

export const ESTABLECIMIENTOS_INICIALES = [
  {
    id: 1,
    codigo: '001',
    nombre: 'Matriz',
    direccion: 'Av. Amazonas N21-147 y Roca',
    puntosEmision: [
      { id: 1, codigo: '001', nombre: 'Caja principal', secuencialFactura: 135 },
      { id: 2, codigo: '002', nombre: 'Ventas en línea', secuencialFactura: 42 },
    ],
  },
  {
    id: 2,
    codigo: '002',
    nombre: 'Sucursal Norte',
    direccion: 'Av. Eloy Alfaro N45-120',
    puntosEmision: [{ id: 3, codigo: '001', nombre: 'Caja sucursal', secuencialFactura: 8 }],
  },
];

export const CUENTAS_BANCARIAS_INICIALES = [
  { id: 1, banco: 'Banco Pichincha', tipo: 'Corriente', numero: '2100123456', titular: 'MI EMPRESA DEMO S.A.' },
  { id: 2, banco: 'Banco del Pacífico', tipo: 'Ahorros', numero: '1045887711', titular: 'MI EMPRESA DEMO S.A.' },
];

/** Estado de la firma electrónica cargada. `null` = no hay firma configurada. */
export const FIRMA_INICIAL = {
  nombreArchivo: 'firma_electronica.p12',
  emisor: 'AC BANCO CENTRAL DEL ECUADOR',
  propietario: 'MI EMPRESA DEMO S.A.',
  validaDesde: '2026-01-15',
  validaHasta: '2028-01-15',
};

/** Días que faltan para que expire la firma; negativo si ya expiró. */
export function diasParaExpirar(validaHasta, hoy = new Date()) {
  const expiracion = new Date(`${validaHasta}T00:00:00`);
  const milisegundosPorDia = 24 * 60 * 60 * 1000;
  return Math.ceil((expiracion - hoy) / milisegundosPorDia);
}
