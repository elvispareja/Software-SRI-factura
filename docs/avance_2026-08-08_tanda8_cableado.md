# Avance — Tanda 8: Formularios que guardan, firma persistida y sesión endurecida

> **Fecha:** 8 de agosto de 2026
> **Estado:** completado y verificado — 126 tests de backend, 24 verificaciones del contrato contra el servidor real

Cierra la última brecha funcional: los formularios ya no calculan en el aire,
el certificado `.p12` se guarda de verdad, y el token deja de estar al alcance
de un XSS.

---

## 1. Los formularios guardan

Antes los listados leían del API pero los formularios de creación calculaban en
memoria y el botón de guardar no hacía nada. Ahora los seis envían:

| Formulario | Tipo que crea |
|---|---|
| FacturaForm | Factura |
| CotizacionForm | Cotización (+ validez) |
| NotaVentaForm | Nota de Venta |
| LiquidacionForm | Liquidación de Compra |
| NotaCreditoForm | Nota de Crédito / Débito (+ referencia) |
| GuiaRemisionForm | Guía de Remisión |

### Catálogos reales

Nuevo hook `useCatalogos`: receptores y artículos vienen del API, con los
buscadores ya filtrados y el filtro por rol que necesitan la liquidación
(Proveedor) y la guía (Transportista).

**Si los catálogos caen a datos de demostración, el botón de guardar se
deshabilita** con el motivo en el tooltip. Es la decisión importante de esta
parte: los `id` del catálogo demo no existen en el backend, así que guardar
fallaría con un error confuso — mejor impedirlo y decir por qué.

### Reglas por tipo, en el formulario y en el servidor

`DocumentoVentaForm` acepta `erroresExtra` y `datosExtra`, así cada pantalla
añade lo suyo sin duplicar el formulario:

- **Cotización** — la validez debe ser al menos 1 día.
- **Nota de crédito/débito** — el número del documento original debe cumplir el formato `001-001-000000135`, y hacen falta fecha y motivo. El banner pasa de aviso a informativo solo cuando la referencia está completa.

Las mismas reglas viven en el backend (Tanda 7): el formulario evita el viaje
inútil, el servidor es quien decide.

### Estado del guardado

Botón con spinner mientras envía, mensaje de éxito con el número asignado y el
importe, vuelta automática al listado, y el error del servidor mostrado tal cual
en vez de un genérico.

---

## 2. Cuentas bancarias y firma electrónica

### Cuentas

Tabla `CuentaBancaria` con endpoints de alta, listado y baja. **La baja
desactiva, no borra:** los RIDE ya emitidos mencionan la cuenta. Rechaza
duplicados por número.

### Firma electrónica

Aquí estaba la parte sensible. `FirmaElectronica` guarda los bytes del `.p12` y
la contraseña **cifrada**, y el endpoint hace tres cosas que importan:

1. **Abre el certificado con la contraseña antes de guardar nada.** Si no abre, o la clave es incorrecta o el archivo no es un PKCS#12 — mucho mejor descubrirlo al subir que al firmar el primer comprobante.
2. **Extrae los metadatos del propio certificado** (propietario, emisor, número de serie, vigencia). El usuario no los teclea, así que no pueden mentir.
3. **Solo un certificado activo a la vez.** Subir otro desactiva el anterior.

El esquema de salida **no incluye `contenido` ni `contrasena_cifrada`**: el
archivo y la clave no salen del servidor por ningún endpoint. El archivo se
escribe a un temporal para poder abrirlo y se borra en el `finally`, y el log de
un certificado rechazado no registra ni la contraseña ni el motivo criptográfico.

**Cifrado en reposo** (`app/servicios/cifrado.py`): Fernet con clave derivada de
`CLAVE_SECRETA` por PBKDF2, reutilizando `cryptography`, que ya era dependencia
del motor de firma. Sin un segundo secreto que gestionar.

> **Consecuencia que conviene tener presente:** si `CLAVE_SECRETA` cambia, las
> contraseñas guardadas dejan de poder descifrarse y hay que volver a subir el
> certificado. Es el precio de no introducir todavía un gestor de claves; en
> producción esto debe moverse a un KMS o a Vault. El error lo dice
> explícitamente en vez de fallar de forma opaca.

---

## 3. Sesión endurecida: cookie HttpOnly

Era la deuda de seguridad que venía arrastrándose desde la Tanda 5. El token
estaba en `localStorage`, donde cualquier XSS podía leerlo.

Ahora el backend emite una **cookie `HttpOnly`**: el JavaScript de la página no
puede acceder a ella, así que un XSS ya no se lleva la sesión.

| Aspecto | Decisión |
|---|---|
| `HttpOnly` | Siempre |
| `Secure` | Activado salvo que `COOKIE_SEGURA=false` (desarrollo sobre `http://localhost`) |
| `SameSite` | `lax` por defecto. Si frontend y API se despliegan en dominios distintos hay que pasar a `none`, que exige `Secure` |
| Cabecera `Authorization` | **Sigue funcionando.** Scripts, curl y Swagger no manejan cookies |
| Cierre de sesión | Endpoint `POST /auth/salir`: solo el servidor puede borrar una cookie `HttpOnly` |

En el frontend, `credentials: 'include'` en todas las peticiones y **cero
referencias al token en `localStorage`** (verificado con grep). Lo único que
queda ahí son los datos visibles del usuario —nombre, correo, rol— para pintar
la cabecera sin pedirlos en cada carga.

Al arrancar, la app revalida contra `/auth/yo`: la cookie pudo expirar mientras
la pestaña estaba cerrada, y desde JavaScript no hay forma de inspeccionarla.

---

## 4. Verificación

| Chequeo | Resultado |
|---|---|
| **Tests del backend** | **126/126** (108 previos + 18 nuevos) |
| **Contrato frontend ↔ backend contra el servidor real** | **24/24** |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |
| Referencias al token en `localStorage` | 0 |

Lo más arriesgado de esta tanda era que el cuerpo construido por el frontend no
coincidiera con lo que acepta el backend, así que la verificación **reproduce a
mano lo que hacen `documentoHaciaApi` y `guiaHaciaApi`** y lo envía al servidor
real. Los seis formularios responden 201.

Un cálculo comprobado de punta a punta: 2 unidades × $1200 con 10% de descuento
→ descuento $240, base $2160, IVA 15% $324, **total $2484.00**.

Los 18 tests nuevos cubren el cifrado en reposo (ida y vuelta, dos cifrados del
mismo texto difieren, texto manipulado no descifra), cuentas bancarias
(duplicados, baja lógica), firma (metadatos extraídos, contraseña incorrecta
rechazada al subir, archivo que no es `.p12`, contraseña cifrada en la base, una
sola firma activa) y la sesión por cookie (`HttpOnly` presente, autentica sin
cabecera, salir la borra, la cabecera sigue funcionando).

---

## 5. Qué queda

1. **El certificado `.p12` de entidad acreditada** — el único bloqueante para emitir de verdad. Ahora ya hay dónde cargarlo: Configuraciones → Firma Electrónica.
2. **Conectar la emisión al SRI.** El motor está probado y el certificado ya se persiste; falta el paso que toma el comprobante en Borrador, lo firma con el `.p12` guardado y lo envía. Es la Tanda 9 natural.
3. **Establecimientos y puntos de emisión** siguen editándose en memoria: se leen del API pero el guardado aún no persiste (la empresa sí).
4. **Antes de producción:**
   - Definir `CLAVE_SECRETA` (el servidor avisa al arrancar si falta).
   - Si frontend y API van a dominios distintos, `COOKIE_SAMESITE=none` y revisar CORS.
   - Migrar de SQLite a PostgreSQL (solo cambia `URL_BASE_DATOS`).
   - Mover el cifrado de la contraseña del `.p12` a un KMS.
   - Contrastar los cantones con la codificación oficial del INEC.
