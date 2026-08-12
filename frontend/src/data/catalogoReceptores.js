/**
 * Receptores de demostración (clientes, proveedores y transportistas).
 * Se reemplaza por el API sin tocar los componentes.
 */

export const TIPOS_IDENTIFICACION = [
  'RUC',
  'Cédula',
  'Pasaporte',
  'Consumidor Final',
  'Identificación del Exterior',
];

export const TIPOS_PERSONA = ['Jurídica', 'Natural'];
export const ESTADOS_RECEPTOR = ['Activo', 'Inactivo'];
export const ROLES_RECEPTOR = ['Cliente', 'Proveedor', 'Transportista'];

export const CATALOGO_RECEPTORES = [
  { id: 1, tipoIdentificacion: 'RUC', identificacion: '1790016919001', razonSocial: 'CORPORACIÓN FAVORITA C.A.', nombreComercial: 'SUPERMAXI', tipoPersona: 'Jurídica', rol: 'Cliente', correo: 'facturacion@favorita.com', estado: 'Activo' },
  { id: 2, tipoIdentificacion: 'Cédula', identificacion: '0912345675', razonSocial: 'JUAN PÉREZ', nombreComercial: 'TIENDA JUANITO', tipoPersona: 'Natural', rol: 'Cliente', correo: 'juan.perez@correo.com', estado: 'Activo' },
  { id: 3, tipoIdentificacion: 'Consumidor Final', identificacion: '9999999999999', razonSocial: 'CONSUMIDOR FINAL', nombreComercial: '', tipoPersona: 'Natural', rol: 'Cliente', correo: '', estado: 'Activo' },
  { id: 4, tipoIdentificacion: 'RUC', identificacion: '0992339411001', razonSocial: 'PLÁSTICOS DEL LITORAL PLASTLIT S.A.', nombreComercial: 'PLASTLIT', tipoPersona: 'Jurídica', rol: 'Proveedor', correo: 'compras@plastlit.com', estado: 'Activo' },
  { id: 5, tipoIdentificacion: 'RUC', identificacion: '1791287541001', razonSocial: 'TRANSPORTES ANDINOS CÍA. LTDA.', nombreComercial: 'TRANSANDINOS', tipoPersona: 'Jurídica', rol: 'Transportista', correo: 'logistica@transandinos.ec', estado: 'Activo' },
  { id: 6, tipoIdentificacion: 'Cédula', identificacion: '1712345675', razonSocial: 'MARÍA ANDRADE', nombreComercial: '', tipoPersona: 'Natural', rol: 'Cliente', correo: 'maria.andrade@correo.com', estado: 'Activo' },
  { id: 7, tipoIdentificacion: 'RUC', identificacion: '0190001946001', razonSocial: 'IMPORTADORA AUSTRAL S.A.', nombreComercial: 'AUSTRAL', tipoPersona: 'Jurídica', rol: 'Proveedor', correo: 'ventas@austral.com.ec', estado: 'Activo' },
  { id: 8, tipoIdentificacion: 'Pasaporte', identificacion: 'AB1234567', razonSocial: 'JOHN SMITH', nombreComercial: '', tipoPersona: 'Natural', rol: 'Cliente', correo: 'john.smith@mail.com', estado: 'Activo' },
  { id: 9, tipoIdentificacion: 'RUC', identificacion: '1792060346001', razonSocial: 'DISTRIBUIDORA ANDINA S.A.', nombreComercial: 'DISANDINA', tipoPersona: 'Jurídica', rol: 'Cliente', correo: 'cobranzas@disandina.ec', estado: 'Inactivo' },
  { id: 10, tipoIdentificacion: 'Cédula', identificacion: '0604567891', razonSocial: 'CARLOS VILLACÍS', nombreComercial: 'FERRETERÍA EL TORNILLO', tipoPersona: 'Natural', rol: 'Cliente', correo: 'cvillacis@correo.com', estado: 'Activo' },
  { id: 11, tipoIdentificacion: 'RUC', identificacion: '1890123453001', razonSocial: 'IMPRENTA GRÁFICA CENTRAL', nombreComercial: 'GRAFICENTRO', tipoPersona: 'Jurídica', rol: 'Proveedor', correo: 'pedidos@graficentro.ec', estado: 'Activo' },
  { id: 12, tipoIdentificacion: 'Identificación del Exterior', identificacion: 'EXT-889201', razonSocial: 'GLOBAL SUPPLIES LLC', nombreComercial: '', tipoPersona: 'Jurídica', rol: 'Proveedor', correo: 'ap@globalsupplies.com', estado: 'Activo' },
  { id: 13, tipoIdentificacion: 'Cédula', identificacion: '0201456787', razonSocial: 'LUIS MOROCHO', nombreComercial: '', tipoPersona: 'Natural', rol: 'Transportista', correo: 'lmorocho@correo.com', estado: 'Inactivo' },
  { id: 14, tipoIdentificacion: 'RUC', identificacion: '1791251458001', razonSocial: 'ASEGURADORA MITAD DEL MUNDO S.A.', nombreComercial: 'AMM SEGUROS', tipoPersona: 'Jurídica', rol: 'Cliente', correo: 'facturas@ammseguros.ec', estado: 'Activo' },
];
