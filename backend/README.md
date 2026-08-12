# Backend — Motor SRI

Python 3.12 + FastAPI. Por ahora contiene el **Motor SRI**: generación del XML
del comprobante, firma XAdES-BES y comunicación con los WebServices del SRI.

## Puesta en marcha

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/Mac
```

## Estructura

```
app/sri/
  clave_acceso.py   Clave de 49 dígitos y su verificador módulo 11
  modelos.py        Emisor, Comprador, Detalle, Factura (dinero en Decimal)
  xml_factura.py    XML de factura v1.1.0 en el orden que exige el XSD
  firma.py          Firma XAdES-BES + verificación interna
  servicios.py      Recepción y autorización (SOAP)
scripts/
  generar_certificado_pruebas.py   .p12 autofirmado para pruebas locales
  poc_factura.py                   Flujo completo de punta a punta
tests/
  test_motor_sri.py                18 pruebas
```

## Probar

```bash
.venv/Scripts/python -m pytest tests/ -q

# Generar un certificado local y correr el flujo sin tocar la red
.venv/Scripts/python scripts/generar_certificado_pruebas.py certificados/pruebas.p12 pruebas123
.venv/Scripts/python scripts/poc_factura.py --p12 certificados/pruebas.p12 --clave pruebas123

# Enviar de verdad al ambiente de PRUEBAS del SRI (requiere certificado acreditado)
.venv/Scripts/python scripts/poc_factura.py --p12 mi_firma.p12 --clave xxxx --enviar
```

## Notas importantes

**El certificado autofirmado no sirve para el SRI.** Valida que la firma se
construya y verifique bien, pero el SRI solo acepta certificados de entidades
acreditadas (Banco Central del Ecuador, Security Data, ANF, Uanataca). Para la
prueba real hace falta un `.p12` de pruebas emitido por una de ellas.

**Dinero en `Decimal`, nunca en `float`.** El SRI valida que los totales cuadren
al centavo y rechaza el comprobante si no. El redondeo es `ROUND_HALF_UP` en cada
paso, no solo al final.

**El orden de los elementos del XML importa.** El XSD usa `xsd:sequence`: un
campo correcto pero fuera de sitio provoca rechazo por estructura.

**Nunca versionar certificados.** `.gitignore` ya excluye `*.p12`, `*.pfx` y la
carpeta `certificados/`. Las contraseñas van por variable de entorno o gestor de
secretos, jamás en el código.
