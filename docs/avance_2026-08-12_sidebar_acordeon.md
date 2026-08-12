# El sidebar se comporta como acordeón: un desplegable abierto cierra el anterior

Fecha: **12 de agosto de 2026**

Lo señaló el usuario probando la interfaz: al abrir un submenú del menú
lateral (Receptores, Comprobantes, Egresos, Cuentas), el que ya estaba
abierto se quedaba abierto también, en vez de cerrarse. Con dos o tres
submenús abiertos a la vez, el sidebar deja de caber en la pantalla y hay que
hacer scroll para encontrar la opción que se busca.

## La causa

`Layout.jsx` llevaba **cuatro banderas booleanas independientes** —una por
cada submenú—, cada una con su propio `useState` y su propio `onClick` que
solo se togglaba a sí misma:

```js
const [recOpen, setRecOpen] = useState(esReceptores);
const [compOpen, setCompOpen] = useState(esComprobantes);
const [egrOpen, setEgrOpen] = useState(esEgresos);
const [ctasOpen, setCtasOpen] = useState(esCuentas);
```

Ninguna de las cuatro sabía de la existencia de las otras tres, así que no
había forma de que abrir una cerrara las demás: técnicamente no era un fallo,
era que nunca se había escrito la coordinación entre ellas.

## La corrección

Se sustituyeron las cuatro banderas por **un solo estado** que guarda cuál
sección está abierta (`'receptores' | 'comprobantes' | 'egresos' | 'cuentas' | null`).
Las cuatro variables `recOpen`/`compOpen`/`egrOpen`/`ctasOpen` que usa el resto
del componente para pintar cada submenú y su flecha se dejaron como constantes
derivadas, así que no hizo falta tocar el JSX que ya las usaba:

```js
const [seccionAbierta, setSeccionAbierta] = useState(seccionDeRuta);
const alternarSeccion = (seccion) =>
  setSeccionAbierta((actual) => (actual === seccion ? null : seccion));

const recOpen = seccionAbierta === 'receptores';
const compOpen = seccionAbierta === 'comprobantes';
const egrOpen = seccionAbierta === 'egresos';
const ctasOpen = seccionAbierta === 'cuentas';
```

Cada botón ahora llama a `alternarSeccion('...')` en vez de a su propio
`setXOpen`. Un segundo clic sobre la misma sección la cierra —no solo abre una
distinta—, porque `alternarSeccion` compara contra el valor actual.

El `useEffect` que abre automáticamente la sección correspondiente cuando se
navega a una de sus rutas (por ejemplo, entrar directo a `/egresos` desde un
enlace externo) se simplificó igual: antes ponía hasta cuatro banderas en
`true` sin nunca apagar las otras; ahora solo asigna la sección de la ruta
actual, lo que automáticamente cierra cualquier otra que hubiera quedado
abierta.

## Un detalle que no era el bug

Al verificar con Playwright, la primera pasada del script de prueba dio un
falso positivo: "Cotización" parecía seguir visible al cambiar de sección.
No era un fallo del acordeón — **"Cotización" nunca estuvo dentro del
desplegable de Comprobantes**; es un enlace de nivel superior, hermano del
botón "Comprobantes", no un hijo suyo. El desplegable de Comprobantes
contiene "Facturas" y "Liquidación Compra"; eso sí se verificó que se oculta
al abrir otra sección.

## Verificación

Con Playwright contra la app real (usuario `demo@empresa.ec`):

```
Abro Receptores -> Clientes en el sidebar: true
Abro Comprobantes -> Clientes (Receptores) sigue en el sidebar: false
Abro Comprobantes -> "Liquidación Compra" (su propio submenu) visible: true
Abro Egresos -> "Liquidación Compra" (Comprobantes) sigue visible: false
Abro Egresos -> "Gastos" (su propio submenu) visible: true
Clic otra vez sobre Egresos -> se cierra: true
errores de consola: ninguno
```

Lint y build limpios. Las 253 pruebas de frontend siguen en verde —esta
pantalla no tenía pruebas propias que cubrieran el sidebar, así que no había
ninguna que romper ni que actualizar.
