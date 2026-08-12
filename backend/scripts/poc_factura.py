"""
Prueba de concepto del Motor SRI, de punta a punta y sin interfaz.

    XML -> firma XAdES-BES -> recepción SRI -> autorización SRI

Uso:
    # Solo generar y firmar (no toca la red). Con certificado de pruebas propio:
    python scripts/poc_factura.py --p12 certificados/pruebas.p12 --clave pruebas123

    # Además enviar al ambiente de PRUEBAS del SRI:
    python scripts/poc_factura.py --p12 mi_firma.p12 --clave xxxx --enviar

El envío solo funciona con un certificado emitido por una entidad acreditada
(Banco Central, Security Data, ANF…). Un autofirmado sirve para validar la
mecánica local, pero el SRI lo devolverá con "FIRMA INVALIDA".
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.sri.clave_acceso import validar_clave_acceso  # noqa: E402
from app.sri.firma import cargar_p12, firmar_xml, verificar_firma  # noqa: E402
from app.sri.modelos import Comprador, Detalle, Emisor, Factura, Pago  # noqa: E402
from app.sri.xml_factura import generar_xml_factura  # noqa: E402


def factura_de_ejemplo() -> Factura:
    emisor = Emisor(
        ruc="1790016919001",
        razon_social="MI EMPRESA DEMO S.A.",
        nombre_comercial="DEMO",
        direccion_matriz="Av. Amazonas N21-147 y Roca",
        direccion_establecimiento="Av. Amazonas N21-147 y Roca",
        establecimiento="001",
        punto_emision="002",
        obligado_contabilidad=True,
    )
    comprador = Comprador(
        tipo_identificacion="04",
        identificacion="0992339411001",
        razon_social="PLASTICOS DEL LITORAL PLASTLIT S.A.",
        direccion="Km 14.5 via Daule, Guayaquil",
        correo="compras@plastlit.com",
    )
    detalles = [
        Detalle("PROD-001", "Laptop Dell XPS 13", Decimal("1"), Decimal("1200.00"), "4"),
        Detalle("PROD-003", "Pan comun - funda 500g", Decimal("10"), Decimal("1.85"), "0"),
        Detalle("SERV-001", "Mantenimiento preventivo", Decimal("2"), Decimal("45.00"), "4",
                Decimal("10")),
    ]

    factura = Factura(
        emisor=emisor,
        comprador=comprador,
        fecha_emision=date.today(),
        secuencial=135,
        detalles=detalles,
        ambiente="1",
        info_adicional={"Vendedor": "Ana Salazar", "Observacion": "Prueba de concepto"},
    )
    factura.pagos = [Pago(forma_pago="01", total=factura.importe_total)]
    return factura


def separador(titulo: str) -> None:
    print(f"\n{'=' * 62}\n{titulo}\n{'=' * 62}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PoC del Motor SRI")
    parser.add_argument("--p12", required=True, help="Ruta del certificado .p12/.pfx")
    parser.add_argument("--clave", required=True, help="Contraseña del certificado")
    parser.add_argument("--codigo-numerico", default="12345678", help="8 dígitos")
    parser.add_argument("--enviar", action="store_true", help="Enviar al SRI (ambiente pruebas)")
    parser.add_argument("--salida", default="salida", help="Carpeta donde dejar los XML")
    argumentos = parser.parse_args()

    salida = Path(argumentos.salida)
    salida.mkdir(parents=True, exist_ok=True)

    factura = factura_de_ejemplo()

    separador("1. Totales calculados")
    print(f"  Total sin impuestos : {factura.total_sin_impuestos}")
    print(f"  Total descuento     : {factura.total_descuento}")
    for grupo in factura.impuestos_agrupados():
        print(
            f"  IVA {grupo['tarifa']:>5}%        : base {grupo['base_imponible']:>10}"
            f"  valor {grupo['valor']}"
        )
    print(f"  IMPORTE TOTAL       : {factura.importe_total}")

    separador("2. Generación del XML")
    xml, clave_acceso = generar_xml_factura(factura, argumentos.codigo_numerico)
    ruta_xml = salida / f"{clave_acceso}.xml"
    ruta_xml.write_bytes(xml)
    print(f"  Clave de acceso : {clave_acceso}")
    print(f"  Válida          : {validar_clave_acceso(clave_acceso)}")
    print(f"  Archivo         : {ruta_xml}")

    separador("3. Firma XAdES-BES")
    firmante = cargar_p12(argumentos.p12, argumentos.clave)
    print(f"  Certificado de  : {firmante.certificado.subject.rfc4514_string()}")
    print(f"  Emitido por     : {firmante.emisor}")
    print(f"  Válido hasta    : {firmante.certificado.not_valid_after_utc:%Y-%m-%d}")

    xml_firmado = firmar_xml(xml, firmante)
    ruta_firmado = salida / f"{clave_acceso}_firmado.xml"
    ruta_firmado.write_bytes(xml_firmado)
    print(f"  Archivo firmado : {ruta_firmado}")

    separador("4. Verificación interna de la firma")
    resultado = verificar_firma(xml_firmado)
    for comprobacion, valor in resultado.items():
        print(f"  {'OK  ' if valor else 'FALLA'} {comprobacion}")

    if not all(resultado.values()):
        print("\n  La firma no es consistente. No tiene sentido enviarla al SRI.")
        return 1

    if not argumentos.enviar:
        separador("Listo")
        print("  XML generado y firmado correctamente.")
        print("  Añade --enviar para transmitirlo al ambiente de PRUEBAS del SRI.")
        return 0

    separador("5. Envío al SRI (ambiente de pruebas)")
    from app.sri.servicios import emitir  # import diferido: solo se usa al enviar

    recepcion, autorizacion = emitir(xml_firmado, clave_acceso, factura.ambiente)
    print(f"  Recepción : {recepcion.estado}")
    for mensaje in recepcion.mensajes:
        print(f"    [{mensaje['identificador']}] {mensaje['mensaje']} — {mensaje['informacion_adicional']}")

    if autorizacion is None:
        print("\n  El comprobante fue devuelto en la recepción. Revisa los mensajes.")
        return 1

    print(f"  Autorización : {autorizacion.estado}")
    for mensaje in autorizacion.mensajes:
        print(f"    [{mensaje['identificador']}] {mensaje['mensaje']} — {mensaje['informacion_adicional']}")

    if autorizacion.autorizada:
        print(f"\n  AUTORIZADO. Número: {autorizacion.numero_autorizacion}")
        print(f"  Fecha: {autorizacion.fecha_autorizacion}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
