/**
 * Texto de bienvenida del panel.
 *
 * Vive fuera del componente porque exportar funciones junto a componentes
 * rompe el Fast Refresh de React, y porque así se puede probar sin montar
 * nada.
 */

/** Buenos días / tardes / noches según la hora local. */
export function saludoSegunHora(hora = new Date().getHours()) {
  if (hora < 12) return 'Buenos días';
  if (hora < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

/**
 * Primer nombre de la persona: "Ana Salazar Vera" → "Ana".
 *
 * Saludar con el nombre completo suena a carta del banco. Se parte por
 * cualquier espacio en blanco para tolerar nombres con espacios de más.
 */
export function primerNombre(nombre) {
  return String(nombre ?? '').trim().split(/\s+/)[0] || '';
}

/** Saludo completo; sin nombre conocido, solo la hora. */
export function saludoCompleto(nombre, hora) {
  const primero = primerNombre(nombre);
  const saludo = saludoSegunHora(hora);
  return primero ? `${saludo}, ${primero}` : saludo;
}
