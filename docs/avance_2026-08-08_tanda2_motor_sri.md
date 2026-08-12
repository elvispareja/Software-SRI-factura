# Avance — Tanda 2: Configuraciones, Receptores y Motor SRI

> **Fecha:** 8 de agosto de 2026
> **Resuelve:** §3.4 (Dirección obligatoria, Configuración Comercial), §5 (Configuraciones, Motor SRI)
> **Estado:** completado y verificado

---

## 1. Validación de identificaciones ecuatorianas

Pieza transversal que necesitaban tanto Configuraciones como Receptores:
`frontend/src/lib/sri/identificacion.js`.

Implementa los algoritmos reales del Registro Civil / SRI:

| Tipo | Algoritmo |
|---|---|
| Cédula | Módulo 10, coeficientes `2,1,2,1,2,1,2,1,2` |
| RUC jurídico (3.er dígito `9`) | Módulo 11, coeficientes `4,3,2,7,6,5,4,3,2` |
| RUC público (3.er dígito `6`) | Módulo 11, coeficientes `3,2,7,6,5,4,3,2` |
| RUC natural (3.er dígito `0-5`) | Los 10 primeros dígitos son una cédula |

Valida además el código de provincia (01–24, más 30 para el exterior) y que el
código de establecimiento no sea `000`.

Validar en el cliente evita mandar al SRI un comprobante que va a rebotar por un
dígito mal tecleado, que es de los rechazos más comunes.

> **Hallazgo:** al pasar los datos de demostración por el validador, **6 de 14
> identificaciones tenían dígito verificador inválido** — las había inventado en
> tandas anteriores. Se corrigieron calculando el verificador correcto. Además se
> reemplazaron dos nombres de empresas reales cuyos RUC no se podían verificar,
> por nombres ficticios.

---

## 2. Pantalla de Configuraciones

`frontend/src/pages/Configuraciones/` — cuatro pestañas:

**Empresa.** RUC con validación en vivo y tipo de contribuyente detectado, razón
social, nombre comercial, dirección matriz, provincia/cantón encadenados,
régimen tributario, y el selector de **ambiente SRI**. Elegir "Pruebas" muestra
un banner permanente advirtiendo que los comprobantes no tienen validez
tributaria — es el error de configuración más caro de descubrir tarde.

**Establecimientos y puntos de emisión.** Alta y baja de establecimientos, cada
uno con sus puntos de emisión y su secuencial propio. Muestra en vivo el próximo
número que se emitiría (`001-002-000000135`). Avisa cuando un establecimiento no
tiene puntos de emisión, porque en ese estado no puede facturar.

**Firma electrónica.** Zona de carga del `.p12`/`.pfx` y tarjeta de estado del
certificado con semáforo: vigente, por caducar (menos de 60 días) o expirado,
con los días exactos. La contraseña se marca explícitamente como cifrada y que
nunca viaja en el XML.

**Cuentas bancarias.** Se aclara en la propia pantalla que se imprimen en el
RIDE pero no forman parte del XML.

También se añadieron los datos geográficos: `frontend/src/data/geografiaEcuador.js`
con las 24 provincias y sus cantones, encadenados en los desplegables.

---

## 3. Formulario de Receptores completo

Reescrito según el plan. Lo que cambió:

- **La Dirección pasó a Datos Principales y es obligatoria.** Estaba en "Datos
  Adicionales" cuando el XML del SRI la exige como `direccionComprador`. La
  ayuda del campo lo dice explícitamente.
- **Validación de identificación en vivo**, con mensaje de error concreto o
  confirmación del tipo de contribuyente detectado.
- **"Corregir identidad" ahora funciona de verdad**: la identificación arranca
  bloqueada y el interruptor la desbloquea. Se explica por qué existe el
  bloqueo — cambiarla dejaría comprobantes ya autorizados apuntando a otra
  persona.
- **Configuración Comercial completa**: los 7 campos del plan (método de
  cancelación, vendedor, lista de precios, zona, % descuento, código interno,
  crédito máximo). Antes había 3.
- **Datos Adicionales completos**: nombre comercial, teléfono 2, correos 2 y 3.
- Provincia y cantón encadenados, rol y tipo de persona, y el botón Guardar
  deshabilitado hasta que estén los campos obligatorios.

---

## 4. Motor SRI (backend Python)

Nuevo directorio `backend/`. **Es la parte que decide si el proyecto es viable**,
y ya funciona de punta a punta salvo el envío real.

### Módulos

| Archivo | Rol |
|---|---|
| `app/sri/clave_acceso.py` | Clave de 49 dígitos y verificador módulo 11 |
| `app/sri/modelos.py` | Emisor, Comprador, Detalle, Factura — dinero en `Decimal` |
| `app/sri/xml_factura.py` | XML de factura v1.1.0 en el orden que exige el XSD |
| `app/sri/firma.py` | Firma XAdES-BES + verificación interna |
| `app/sri/servicios.py` | Recepción y autorización vía SOAP |
| `scripts/generar_certificado_pruebas.py` | `.p12` autofirmado para pruebas locales |
| `scripts/poc_factura.py` | Flujo completo de punta a punta |

### Clave de acceso

Los 49 dígitos con su estructura documentada campo por campo, el verificador
módulo 11 (con los casos especiales: verificador 11 → 0, verificador 10 → 1), y
una función que **descompone** una clave en sus campos, útil para depurar
rechazos del SRI.

### Firma XAdES-BES

Se construye a mano en lugar de usar una librería XAdES genérica, porque el
perfil del SRI tiene particularidades (tres referencias con `Id` concretos,
digests SHA1, `DataObjectFormat` apuntando a la referencia del documento) que las
librerías de propósito general no reproducen tal cual.

Genera las tres referencias del `SignedInfo`:

1. → `#…SignedProperties` (tipo ETSI)
2. → `#Certificate…` (el `KeyInfo`)
3. → `#comprobante` con transformada `enveloped-signature`

El digest del documento se calcula **antes** de insertar la firma, que es
exactamente lo que produce la transformada enveloped.

### Servicios SOAP

Endpoints de pruebas (`celcer.sri.gob.ec`) y producción (`cel.sri.gob.ec`). El
flujo `emitir()` hace recepción y luego reconsulta la autorización con espera,
porque **el SRI no autoriza de forma síncrona**: responde `RECIBIDA` y la
autorización llega después.

---

## 5. Verificación

| Chequeo | Resultado |
|---|---|
| `pytest` backend | **18/18 pasando** |
| `oxlint` frontend | Limpio |
| `npm run build` | OK |
| Identificaciones de los datos de demostración | 14/14 válidas |
| Clave de acceso: 49 dígitos, autoconsistente, campos en orden | OK |
| Alterar un dígito de la clave la invalida | OK |
| XML: agrupación por tarifa, totales cuadrados, orden del esquema | OK |
| Firma: 3 referencias, transformada enveloped, certificado incrustado | OK |
| **Los 3 digests y la firma RSA verifican** | OK |
| **Alterar el `importeTotal` rompe la verificación** | OK |

Salida real del PoC de punta a punta:

```
1. Totales:  sin impuestos 1299.50 · descuento 9.00
             IVA 0%  base   18.50  valor   0.00
             IVA 15% base 1281.00  valor 192.15
             IMPORTE TOTAL 1491.65
2. XML:      clave 0808202601179001691900110010020000001351234567817 (válida)
3. Firma:    XAdES-BES generada
4. Verificación: digest_signed_properties OK · digest_key_info OK
                 digest_documento OK · firma_rsa OK
```

---

## 6. Lo que falta para cerrar el Motor SRI

**Se necesita un certificado `.p12` de pruebas emitido por una entidad
acreditada** (Banco Central del Ecuador, Security Data, ANF, Uanataca). El
autofirmado que genera el proyecto valida toda la mecánica local — y demuestra
que la firma es criptográficamente correcta — pero el SRI lo devolverá con
"FIRMA INVALIDA" porque solo acepta certificados de entidades acreditadas.

Con ese certificado, el envío real es un solo comando:

```bash
python scripts/poc_factura.py --p12 mi_firma.p12 --clave xxxx --enviar
```

Otros pendientes del motor: generador del RIDE (PDF) y los demás tipos de
comprobante (nota de crédito, retención, guía de remisión), que reutilizan la
misma clave de acceso y el mismo firmador.

---

## 7. Nota de seguridad

`backend/.gitignore` excluye `*.p12`, `*.pfx`, `certificados/` y `salida/`. Los
certificados y sus contraseñas **nunca** deben versionarse; las contraseñas van
por variable de entorno o gestor de secretos.
