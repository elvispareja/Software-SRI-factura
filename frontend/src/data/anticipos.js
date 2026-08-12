/**
 * Formas de pago que ofrece el formulario de anticipos.
 *
 * Este archivo contenía además `ANTICIPOS_MOCK`, `ESTADOS_ANTICIPO` y
 * `TIPOS_ANTICIPO`. Los tres desaparecieron al conectar la pantalla al API:
 * los estados y los tipos ahora los define el backend (`api/egresos.js`) y los
 * anticipos vienen de `/anticipos`. Solo queda esta lista, que es una elección
 * de la interfaz y no un dato del servidor.
 */

export const PAY_OPTS = [
  'Efectivo',
  'Transferencia bancaria',
  'Cheque',
  'Tarjeta de crédito',
  'Tarjeta de débito',
  'Depósito',
  'Otro',
];
