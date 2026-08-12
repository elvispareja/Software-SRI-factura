# Avance — Tanda 1: Cimientos del frontend

> **Fecha:** 8 de agosto de 2026
> **Resuelve:** puntos 3.1, 3.4 (responsive) y 3.5 de la [Auditoría del Proyecto](./auditoria_proyecto.md)
> **Estado:** completado y verificado

Se atacaron primero los cimientos porque hacerlos ahora cuesta una fracción de lo que costaría después de crear los 8 módulos que faltan: cada pantalla nueva heredará el tema dual, el responsive y el patrón de listado sin trabajo extra.

---

## 1. Sistema de tema dual (claro / oscuro)

### Tokenización

Ningún componente define ya colores literales. Los ~50 valores hardcodeados que había repartidos en los CSS de página se reemplazaron por variables:

| Antes | Token |
|---|---|
| `rgba(255,255,255,0.05)` | `--surface-1` |
| `rgba(255,255,255,0.1)` | `--surface-2` |
| `rgba(255,255,255,0.02)` | `--surface-0` |
| `rgba(0,0,0,0.2)` / `0.3` | `--field-bg` / `--field-bg-strong` |
| `rgba(16,185,129,0.1)` y familia | `--success-soft`, `--error-soft`, `--warning-soft`, `--info-soft` |

Verificación: `grep` de colores literales en `src/pages/**/*.module.css` devuelve **cero** coincidencias.

### Resolución del tema en tres estados

`src/index.css` define la paleta clara en `:root` y solo **redefine los tokens** (nunca las reglas) para el oscuro:

1. `:root` → tema claro, valor por defecto
2. `@media (prefers-color-scheme: dark)` sobre `:root:not([data-tema="claro"])` → sigue al sistema
3. `:root[data-tema="oscuro"]` → elección explícita del usuario, gana siempre

En el tema claro el naranja de marca se oscurece a `#d95f00` y los colores de estado se intensifican, porque los valores del dark no alcanzan contraste legible sobre fondo blanco.

### Componentes

| Archivo | Rol |
|---|---|
| `src/tema/contexto.js` | Contexto, clave de `localStorage` y preferencias válidas |
| `src/tema/TemaProvider.jsx` | Aplica `data-tema`, persiste y escucha cambios del SO en vivo |
| `src/tema/useTema.js` | Hook de consumo (separado del provider para no romper Fast Refresh) |
| `src/tema/SelectorTema.jsx` | Botón del header que cicla sistema → claro → oscuro |

**Anti-parpadeo:** un script inline en `index.html` aplica el tema guardado antes del primer pintado. Sin él se ve un flash blanco al recargar en modo oscuro.

---

## 2. Layout responsive (mobile-first)

El layout no tenía **una sola media query**, pese a ser requisito explícito del plan.

- **Sidebar como drawer en móvil:** bajo 1024px sale del flujo, se desliza sobre el contenido con overlay, se cierra al navegar, al tocar fuera o con `Escape`. En escritorio mantiene el colapso a iconos.
- `100dvh` además de `100vh`, para que la barra de URL del navegador móvil no recorte el layout.
- `min-width: 0` en el contenedor principal: sin eso las tablas anchas desbordan la página en vez de hacer scroll propio.
- Cabeceras de página que se apilan, barras de herramientas que envuelven, buscador a ancho completo y grillas de formulario a una columna bajo 900px.
- El nombre de usuario se oculta bajo 1024px para dejar sitio al avatar y al selector de tema.
- Se respeta `prefers-reduced-motion`.

---

## 3. Listados funcionales

Antes los buscadores guardaban el texto pero **nunca filtraban**, y la paginación era decorativa ("Mostrando 1 a 3 de 3" fijo en el HTML).

### Lógica compartida

| Archivo | Rol |
|---|---|
| `src/hooks/useTablaFiltrada.js` | Búsqueda por texto, filtros por campo y paginación |
| `src/components/ui/Paginacion.jsx` | Controles de paginación reutilizables |
| `src/styles/tabla.module.css` | Filtros, estado vacío y badges, enlazados con `composes` |
| `src/lib/texto.js` | `normalizarTexto` y `contieneTexto` (ignoran tildes y mayúsculas) |

La paginación vive dentro del hook a propósito: **siempre debe volver a la página 1 cuando cambian los filtros**. Si no, el usuario filtra estando en la página 3 y ve una tabla vacía, como si no hubiera datos.

Los estilos compartidos se enlazan con `composes` de CSS Modules en vez de copiarse: el JSX sigue usando `styles.filtros` y la definición vive en un solo archivo.

### Por módulo

| Listado | Búsqueda por | Filtros |
|---|---|---|
| Receptores | identificación, razón social, nombre comercial, correo | rol, tipo de persona, tipo de identificación, estado |
| Artículos | código, nombre, categoría | tipo, categoría, estado |
| Comprobantes | número, cliente | tipo, estado SRI, estado de pago, método |

Además: botón "Limpiar" que aparece solo si hay algo que limpiar, estado vacío explícito cuando nada coincide, y en Comprobantes los contadores del encabezado ahora se **derivan de lo filtrado** en vez de ser números inventados en el HTML.

### Datos de demostración

Los mocks se movieron a `src/data/` como fuente única (`catalogoArticulos`, `catalogoReceptores`, `comprobantes`) y se ampliaron a 14–15 registros para que la paginación y los filtros sean realmente ejercitables. `ArticulosList` y el buscador de la factura leen del mismo catálogo, así no se desincronizan.

---

## 4. Limpieza incluida

- `src/App.css` eliminado: era plantilla de Vite (`.counter`, `.hero`) y ni siquiera se importaba.
- `index.html`: título real, `lang="es"`, meta descripción, y **la fuente Inter ahora sí se carga** (estaba declarada en CSS pero nunca enlazada, así que se veía con la fuente del sistema).
- El botón de Configuraciones del sidebar ya navega en vez de no hacer nada (la pantalla se construye en la Tanda 2).
- Estilos de foco visibles y consistentes en todo lo interactivo.

---

## 5. Verificación

| Chequeo | Resultado |
|---|---|
| `oxlint` | Limpio, sin hallazgos |
| `npm run build` | OK |
| Colores literales en CSS de páginas | 0 coincidencias |
| Integridad de datos (ids únicos, categorías derivadas, estados cubiertos por los filtros) | OK |
| Normalización de tildes en búsqueda | OK (`PERÉZ` → `perez`) |
| Buscador de factura excluye artículos inactivos | OK |

---

## 6. Siguiente tanda propuesta

1. **Pantalla de Configuraciones** — empresa, establecimientos y puntos de emisión, y carga de la firma `.p12`. Es prerrequisito de todo el Motor SRI.
2. **Completar el formulario de Receptores** — mover Dirección a datos obligatorios (el SRI la exige en el XML) y agregar los campos comerciales que faltan.
3. **PoC del Motor SRI en Python** — armar, firmar y enviar a PRUEBAS.

> **Nota:** el paso 3 necesita un certificado `.p12` de pruebas. Sin él se puede construir y validar toda la generación de XML y la firma con un certificado autofirmado, pero no la autorización real del SRI.
