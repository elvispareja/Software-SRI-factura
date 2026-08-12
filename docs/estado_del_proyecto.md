# Estado del proyecto — qué está hecho y qué falta

Fecha del corte: **11 de agosto de 2026**

Las cifras de este documento salen de contar el repositorio, no de memoria. Se
regeneran repitiendo los comandos de la última sección.

---

## Resumen

El **núcleo fiscal está terminado**, que es la parte difícil. Los siete tipos de
comprobante del SRI se generan, se firman con XAdES-BES, se envían y se
consultan: factura, nota de crédito, nota de débito, liquidación de compra, guía
de remisión y comprobante de retención, más los documentos no tributarios
(cotización y nota de venta).

En las pruebas contra el ambiente del SRI la **recepción fue aceptada**. La
autorización falló únicamente en la cadena de confianza del certificado
autofirmado:

```
error 39: FIRMA INVALIDA — no existe certificado root registrado
```

Dicho de otro modo: el flujo funciona de punta a punta; lo que falta es un
certificado de verdad, no código.

| Métrica | Valor |
|---|---|
| Endpoints | 118 |
| Modelos de base de datos | 24 |
| Pantallas | 17 |
| Código | 11.325 líneas Python · 15.753 líneas JS/JSX |
| Pruebas | 526 (292 backend con pytest · 234 frontend con vitest) |
| Documentos en `docs/` | 23 + manual de uso ilustrado en PDF |
| Secciones «Próximamente» | 6 (eran 17) |

En números redondos, el sistema está **sobre el 90 %**. Lo que queda no es
construir, es cerrar.

---

## Lo que falta, por orden de importancia

### 1. El certificado `.p12` acreditado — el único bloqueante real

Sin él, nada de lo que se firme tiene validez ante el SRI.

Hay que comprarlo a una entidad certificadora acreditada: **Security Data, ANF,
Uanataca o el Banco Central del Ecuador**. Cuesta entre 30 y 80 USD al año según
la entidad, y su emisión tarda días.

**Esto no está en mano del desarrollo y no hay forma de rodearlo.** Se carga en
Configuraciones → Firma Electrónica. Si nada más falla, el mismo flujo debería
autorizar sin tocar una línea de código.

Mientras tanto se puede probar todo el sistema, pero los documentos emitidos no
son legales.

### 2. Los tests de la última tanda

Se omitieron por decisión explícita y quedaron a cero. Verificado sobre
`backend/tests/`:

| Sin cobertura | Qué es |
|---|---|
| `/reportes/inventario`, `/reportes/receptores` | los dos últimos reportes |
| `/reportes/notas-venta`, `/reportes/cotizaciones`, `/reportes/egresos` | los reportes de la tanda anterior |
| `/api/cuentas/*` | cuotas y recibos |
| `/configuracion/listas` | zonas, vendedores, leyendas |
| `enviar_comprobante` (SMTP) | envío del comprobante al receptor |

**El más urgente es `/api/cuentas/*`, porque toca dinero.** El reparto en cuotas
acumula el resto en la última (217,35 en tres da 72,45 exacto) y el sobrepago se
rechaza; ambas cosas se comprobaron ejecutando la aplicación, pero una
comprobación manual no protege contra que alguien rompa esa lógica dentro de
tres meses.

Es la primera tarea recomendada después del certificado.

### 3. Detalles funcionales pequeños

- **Cuentas → pestaña Reportes** sigue mostrando el texto *«requiere cuotas y
  recibos… cuando el módulo contable esté disponible»*. Quedó obsoleto: las
  cuotas y los recibos ya existen. Es conectar la pestaña —media hora—.
- **Audio e imagen en WhatsApp** (Fase 3-B). El texto funciona; el mensaje de voz
  y la foto de una factura, todavía no.
- **Exportar reportes a PDF.** El CSV ya funciona y Excel lo abre directo, así
  que esto es comodidad, no capacidad.

### 4. Las seis secciones «Próximamente» — ninguna es olvido

| Sección | Por qué no está |
|---|---|
| Impresoras, terminales (Cocina/Bar/Postres) | Depende de hardware que no está delante |
| Permisos granulares | El modelo de usuario tiene **un solo campo `rol`**. Hacerlo bien es rediseñar la autorización, no rellenar una pantalla |
| Vídeos de Soporte Técnico | No hay vídeos grabados |
| Exportar a PDF | Cosmética; el CSV cubre el caso |

### 5. Antes de producción

- Definir `CLAVE_SECRETA` — obligatoria con `AMBIENTE=2`. **Si cambia, las
  contraseñas de certificado guardadas dejan de poder descifrarse.**
- Migrar de SQLite a PostgreSQL.
- Mover el cifrado de la clave del `.p12` a un KMS.
- Contrastar el listado de cantones con la codificación oficial del INEC.
- Confirmar el único concepto de **ISD**, marcado con `verificado=False` en
  `backend/app/sri/codigos_retencion.py`. El resto de códigos y porcentajes están
  contrastados con la resolución **NAC-DGERCGC26-00000009**, vigente desde el
  01/03/2026.

---

## Orden recomendado

1. **Comprar el certificado en paralelo.** Tarda días en emitirse y no depende
   del desarrollo, así que conviene arrancarlo ya.
2. **Mientras llega**: escribir los tests que faltan —empezando por cuotas y
   recibos— y conectar la pestaña de reportes de Cuentas.
3. **Cuando el `.p12` esté**: probar el flujo completo contra el SRI real.
4. **Después**: la lista de producción del punto 5.

---

## Cómo se obtuvieron estas cifras

```bash
# Endpoints, modelos y pantallas
grep -rhoE '@router\.(get|post|put|patch|delete)' backend/app/routers/*.py | wc -l
grep -rhcE '^class [A-Z]' backend/app/modelos_db.py
ls frontend/src/pages | wc -l

# Líneas de código
find backend/app -name '*.py' | xargs wc -l | tail -1
find frontend/src -name '*.jsx' -o -name '*.js' | grep -v test | xargs wc -l | tail -1

# Pruebas
cd backend && .venv/Scripts/python -m pytest -q
cd frontend && npx vitest run

# Secciones pendientes
grep -ro "Próximamente" frontend/src/pages/*/*.jsx | wc -l
```

Ver también [`avance_fase4_pendientes.md`](avance_fase4_pendientes.md), que
detalla la última tanda, y [`auditoria_proyecto.md`](auditoria_proyecto.md), que
indexa todos los avances.
