/**
 * Validación de identificaciones ecuatorianas (cédula y RUC).
 *
 * Los algoritmos son los del Registro Civil / SRI:
 *   - Cédula: módulo 10 con coeficientes 2,1,2,1,2,1,2,1,2
 *   - RUC jurídico (3er dígito 9):  módulo 11, coeficientes 4,3,2,7,6,5,4,3,2
 *   - RUC público  (3er dígito 6):  módulo 11, coeficientes 3,2,7,6,5,4,3,2
 *   - RUC natural  (3er dígito 0-5): los 10 primeros dígitos son una cédula
 *
 * Validar en el cliente evita mandar al SRI un comprobante que va a rebotar por
 * un dígito mal tecleado, que es de los rechazos más comunes.
 */

export const TIPOS_IDENTIFICACION_SRI = [
  { codigo: '04', nombre: 'RUC', longitud: 13 },
  { codigo: '05', nombre: 'Cédula', longitud: 10 },
  { codigo: '06', nombre: 'Pasaporte', longitud: null },
  { codigo: '07', nombre: 'Consumidor Final', longitud: 13 },
  { codigo: '08', nombre: 'Identificación del Exterior', longitud: null },
];

export const CONSUMIDOR_FINAL = '9999999999999';

const PROVINCIAS_VALIDAS = { min: 1, max: 24, exterior: 30 };

const soloDigitos = (valor) => /^\d+$/.test(valor);
const aDigitos = (valor) => [...valor].map(Number);

/** Suma ponderada; en módulo 10 los productos de dos cifras se reducen restando 9. */
function sumaPonderada(digitos, coeficientes, reducirDosCifras) {
  return digitos.reduce((total, digito, indice) => {
    const producto = digito * coeficientes[indice];
    return total + (reducirDosCifras && producto >= 10 ? producto - 9 : producto);
  }, 0);
}

function provinciaValida(valor) {
  const provincia = Number(valor.slice(0, 2));
  return (
    (provincia >= PROVINCIAS_VALIDAS.min && provincia <= PROVINCIAS_VALIDAS.max) ||
    provincia === PROVINCIAS_VALIDAS.exterior
  );
}

/** Cédula de ciudadanía: 10 dígitos, módulo 10. */
export function validarCedula(valor) {
  const cedula = String(valor ?? '').trim();

  if (cedula.length !== 10) return { esValida: false, error: 'La cédula debe tener 10 dígitos.' };
  if (!soloDigitos(cedula)) return { esValida: false, error: 'La cédula solo admite dígitos.' };
  if (!provinciaValida(cedula)) {
    return { esValida: false, error: 'Los dos primeros dígitos no corresponden a una provincia.' };
  }

  const digitos = aDigitos(cedula);
  // El tercer dígito indica persona natural: 6 y 9 están reservados para RUC.
  if (digitos[2] > 5) return { esValida: false, error: 'El tercer dígito no es válido para una cédula.' };

  const suma = sumaPonderada(digitos.slice(0, 9), [2, 1, 2, 1, 2, 1, 2, 1, 2], true);
  const verificador = (10 - (suma % 10)) % 10;

  return verificador === digitos[9]
    ? { esValida: true }
    : { esValida: false, error: 'El dígito verificador no coincide. Revisa la cédula.' };
}

/** Verificador módulo 11 usado por los RUC jurídicos y públicos. */
function verificadorModulo11(digitos, coeficientes) {
  const residuo = sumaPonderada(digitos, coeficientes, false) % 11;
  return residuo === 0 ? 0 : 11 - residuo;
}

/** RUC: 13 dígitos. El tercero define el tipo de contribuyente. */
export function validarRuc(valor) {
  const ruc = String(valor ?? '').trim();

  if (ruc === CONSUMIDOR_FINAL) return { esValida: true, tipo: 'consumidor final' };
  if (ruc.length !== 13) return { esValida: false, error: 'El RUC debe tener 13 dígitos.' };
  if (!soloDigitos(ruc)) return { esValida: false, error: 'El RUC solo admite dígitos.' };
  if (!provinciaValida(ruc)) {
    return { esValida: false, error: 'Los dos primeros dígitos no corresponden a una provincia.' };
  }

  const digitos = aDigitos(ruc);
  const tercerDigito = digitos[2];

  // Los tres últimos dígitos son el establecimiento y nunca son 000.
  if (ruc.slice(10) === '000') {
    return { esValida: false, error: 'El código de establecimiento no puede ser 000.' };
  }

  if (tercerDigito <= 5) {
    const cedula = validarCedula(ruc.slice(0, 10));
    return cedula.esValida
      ? { esValida: true, tipo: 'persona natural' }
      : { esValida: false, error: 'El RUC de persona natural no contiene una cédula válida.' };
  }

  if (tercerDigito === 6) {
    const verificador = verificadorModulo11(digitos.slice(0, 8), [3, 2, 7, 6, 5, 4, 3, 2]);
    return verificador === digitos[8]
      ? { esValida: true, tipo: 'sector público' }
      : { esValida: false, error: 'El dígito verificador del RUC público no coincide.' };
  }

  if (tercerDigito === 9) {
    const verificador = verificadorModulo11(digitos.slice(0, 9), [4, 3, 2, 7, 6, 5, 4, 3, 2]);
    return verificador === digitos[9]
      ? { esValida: true, tipo: 'sociedad privada' }
      : { esValida: false, error: 'El dígito verificador del RUC no coincide.' };
  }

  return { esValida: false, error: 'El tercer dígito no corresponde a ningún tipo de contribuyente.' };
}

/**
 * Valida según el tipo elegido en el formulario.
 * Pasaporte e identificación del exterior no tienen algoritmo: solo se exige
 * que no vengan vacíos.
 */
export function validarIdentificacion(tipo, valor) {
  const identificacion = String(valor ?? '').trim();

  switch (tipo) {
    case 'Cédula':
      return validarCedula(identificacion);
    case 'RUC':
      return validarRuc(identificacion);
    case 'Consumidor Final':
      return identificacion === CONSUMIDOR_FINAL
        ? { esValida: true }
        : { esValida: false, error: `Consumidor final debe ser ${CONSUMIDOR_FINAL}.` };
    case 'Pasaporte':
    case 'Identificación del Exterior':
      return identificacion.length >= 3
        ? { esValida: true }
        : { esValida: false, error: 'Ingresa al menos 3 caracteres.' };
    default:
      return { esValida: false, error: 'Selecciona un tipo de identificación.' };
  }
}
