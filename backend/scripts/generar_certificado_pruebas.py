"""
Genera un .p12 autofirmado para probar el pipeline de firma sin depender de un
certificado real del Banco Central / Security Data.

IMPORTANTE: sirve para verificar que la firma se construye y valida bien, pero
el SRI lo rechazará: solo acepta certificados de entidades acreditadas. Para la
prueba real hace falta un .p12 de pruebas emitido por una de ellas.

Uso:
    python scripts/generar_certificado_pruebas.py [ruta_salida] [contrasena]
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID


def generar(ruta_salida: Path, contrasena: str) -> None:
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    sujeto = emisor = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "EC"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Pichincha"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Quito"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CERTIFICADO DE PRUEBAS - NO VALIDO"),
            x509.NameAttribute(NameOID.COMMON_NAME, "MI EMPRESA DEMO S.A."),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, "1790016919001"),
        ]
    )

    ahora = datetime.now(timezone.utc)
    certificado = (
        x509.CertificateBuilder()
        .subject_name(sujeto)
        .issuer_name(emisor)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(days=1))
        .not_valid_after(ahora + timedelta(days=730))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(clave, hashes.SHA256())
    )

    p12 = pkcs12.serialize_key_and_certificates(
        name=b"pruebas",
        key=clave,
        cert=certificado,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(contrasena.encode()),
    )

    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    ruta_salida.write_bytes(p12)
    print(f"Certificado de pruebas generado en: {ruta_salida}")
    print(f"Contraseña: {contrasena}")
    print("Recuerda: el SRI NO acepta este certificado. Es solo para pruebas locales.")


if __name__ == "__main__":
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("certificados/pruebas.p12")
    clave_acceso = sys.argv[2] if len(sys.argv) > 2 else "pruebas123"
    generar(salida, clave_acceso)
