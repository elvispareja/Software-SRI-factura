"""
Firma XAdES-BES sobre el XML del comprobante, en el formato que exige el SRI.

Es la pieza más frágil del sistema: el SRI valida la estructura de la firma con
mucho detalle y no da mensajes útiles cuando algo no cuadra. Se construye a mano
en vez de usar una librería genérica porque el perfil del SRI tiene
particularidades (tres referencias, `Id` propios, digest SHA1) que las librerías
XAdES de propósito general no reproducen tal cual.

Estructura generada:

    ds:Signature
      ds:SignedInfo
        Reference -> #...SignedProperties   (Type = etsi SignedProperties)
        Reference -> #Certificate...        (el KeyInfo)
        Reference -> #comprobante           (transform: enveloped-signature)
      ds:SignatureValue
      ds:KeyInfo        (X509Certificate + RSAKeyValue)
      ds:Object
        etsi:QualifyingProperties
          etsi:SignedProperties
            SigningTime, SigningCertificate (CertDigest + IssuerSerial)
            DataObjectFormat
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate
from lxml import etree

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ETSI = "http://uri.etsi.org/01903/v1.3.2#"
NSMAP = {"ds": NS_DS, "etsi": NS_ETSI}

ALGORITMO_C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
ALGORITMO_FIRMA = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
ALGORITMO_DIGEST = "http://www.w3.org/2000/09/xmldsig#sha1"
ALGORITMO_ENVELOPED = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
TIPO_SIGNED_PROPERTIES = "http://uri.etsi.org/01903#SignedProperties"


class ErrorFirma(Exception):
    """Fallo al cargar el certificado o al firmar."""


@dataclass
class CertificadoFirmante:
    clave_privada: rsa.RSAPrivateKey
    certificado: Certificate

    @property
    def certificado_base64(self) -> str:
        der = self.certificado.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(der).decode()

    @property
    def digest_certificado(self) -> str:
        der = self.certificado.public_bytes(serialization.Encoding.DER)
        return base64.b64encode(hashlib.sha1(der).digest()).decode()

    @property
    def emisor(self) -> str:
        return self.certificado.issuer.rfc4514_string()

    @property
    def numero_serie(self) -> int:
        return self.certificado.serial_number


def cargar_p12(ruta: str, contrasena: str) -> CertificadoFirmante:
    """Abre un .p12/.pfx y extrae la clave privada y el certificado."""
    try:
        with open(ruta, "rb") as archivo:
            datos = archivo.read()
        clave, certificado, _ = pkcs12.load_key_and_certificates(
            datos, contrasena.encode() if contrasena else None
        )
    except Exception as error:  # noqa: BLE001 - se reempaqueta con contexto útil
        raise ErrorFirma(f"No se pudo abrir el certificado: {error}") from error

    if clave is None or certificado is None:
        raise ErrorFirma("El archivo no contiene clave privada y certificado.")
    if not isinstance(clave, rsa.RSAPrivateKey):
        raise ErrorFirma("El SRI requiere un certificado con clave RSA.")

    return CertificadoFirmante(clave_privada=clave, certificado=certificado)


def _c14n(elemento: etree._Element) -> bytes:
    """Canonicalización C14N inclusiva sin comentarios, la que exige el SRI."""
    return etree.tostring(elemento, method="c14n", exclusive=False, with_comments=False)


def _digest_b64(datos: bytes) -> str:
    return base64.b64encode(hashlib.sha1(datos).digest()).decode()


def _entero_a_b64(valor: int) -> str:
    longitud = (valor.bit_length() + 7) // 8
    return base64.b64encode(valor.to_bytes(longitud, "big")).decode()


def _sub(padre: etree._Element, etiqueta: str, texto: str | None = None, **atributos):
    elemento = etree.SubElement(padre, etiqueta, **atributos)
    if texto is not None:
        elemento.text = texto
    return elemento


def firmar_xml(
    xml: bytes,
    firmante: CertificadoFirmante,
    identificador: int = 1,
    momento: datetime | None = None,
) -> bytes:
    """
    Devuelve el XML con la firma XAdES-BES incrustada.

    `identificador` solo genera los sufijos de los atributos `Id`; puede ser
    cualquier número estable dentro del documento.
    """
    parser = etree.XMLParser(remove_blank_text=False)
    raiz = etree.fromstring(xml, parser=parser)

    if raiz.get("id") is None:
        raise ErrorFirma("El comprobante debe tener el atributo id='comprobante'.")
    referencia_documento = raiz.get("id")

    # El digest del documento se calcula ANTES de añadir la firma: es
    # exactamente lo que produce la transformada enveloped-signature.
    digest_documento = _digest_b64(_c14n(raiz))

    sufijo = identificador
    id_firma = f"Signature{sufijo}"
    id_signed_info = f"Signature-SignedInfo{sufijo}"
    id_signed_properties = f"{id_firma}-SignedProperties{sufijo}"
    id_certificado = f"Certificate{sufijo}"
    id_referencia_doc = f"Reference-ID-{sufijo}"
    id_objeto = f"{id_firma}-Object{sufijo}"
    id_valor_firma = f"SignatureValue{sufijo}"

    firma = etree.SubElement(raiz, f"{{{NS_DS}}}Signature", nsmap=NSMAP, Id=id_firma)

    # --- SignedInfo (se rellenan los digests más abajo) ---
    signed_info = _sub(firma, f"{{{NS_DS}}}SignedInfo", Id=id_signed_info)
    _sub(signed_info, f"{{{NS_DS}}}CanonicalizationMethod", Algorithm=ALGORITMO_C14N)
    _sub(signed_info, f"{{{NS_DS}}}SignatureMethod", Algorithm=ALGORITMO_FIRMA)

    ref_propiedades = _sub(
        signed_info,
        f"{{{NS_DS}}}Reference",
        Id=f"SignedPropertiesID{sufijo}",
        Type=TIPO_SIGNED_PROPERTIES,
        URI=f"#{id_signed_properties}",
    )
    _sub(ref_propiedades, f"{{{NS_DS}}}DigestMethod", Algorithm=ALGORITMO_DIGEST)
    digest_propiedades = _sub(ref_propiedades, f"{{{NS_DS}}}DigestValue")

    ref_certificado = _sub(signed_info, f"{{{NS_DS}}}Reference", URI=f"#{id_certificado}")
    _sub(ref_certificado, f"{{{NS_DS}}}DigestMethod", Algorithm=ALGORITMO_DIGEST)
    digest_key_info = _sub(ref_certificado, f"{{{NS_DS}}}DigestValue")

    ref_documento = _sub(
        signed_info,
        f"{{{NS_DS}}}Reference",
        Id=id_referencia_doc,
        URI=f"#{referencia_documento}",
    )
    transformadas = _sub(ref_documento, f"{{{NS_DS}}}Transforms")
    _sub(transformadas, f"{{{NS_DS}}}Transform", Algorithm=ALGORITMO_ENVELOPED)
    _sub(ref_documento, f"{{{NS_DS}}}DigestMethod", Algorithm=ALGORITMO_DIGEST)
    _sub(ref_documento, f"{{{NS_DS}}}DigestValue", digest_documento)

    valor_firma = _sub(firma, f"{{{NS_DS}}}SignatureValue", Id=id_valor_firma)

    # --- KeyInfo ---
    key_info = _sub(firma, f"{{{NS_DS}}}KeyInfo", Id=id_certificado)
    x509_data = _sub(key_info, f"{{{NS_DS}}}X509Data")
    _sub(x509_data, f"{{{NS_DS}}}X509Certificate", firmante.certificado_base64)

    numeros = firmante.clave_privada.public_key().public_numbers()
    key_value = _sub(key_info, f"{{{NS_DS}}}KeyValue")
    rsa_key = _sub(key_value, f"{{{NS_DS}}}RSAKeyValue")
    _sub(rsa_key, f"{{{NS_DS}}}Modulus", _entero_a_b64(numeros.n))
    _sub(rsa_key, f"{{{NS_DS}}}Exponent", _entero_a_b64(numeros.e))

    # --- Object / QualifyingProperties / SignedProperties ---
    objeto = _sub(firma, f"{{{NS_DS}}}Object", Id=id_objeto)
    calificadas = _sub(
        objeto, f"{{{NS_ETSI}}}QualifyingProperties", Target=f"#{id_firma}"
    )
    propiedades = _sub(
        calificadas, f"{{{NS_ETSI}}}SignedProperties", Id=id_signed_properties
    )

    props_firma = _sub(propiedades, f"{{{NS_ETSI}}}SignedSignatureProperties")
    instante = (momento or datetime.now(timezone.utc).astimezone()).replace(microsecond=0)
    _sub(props_firma, f"{{{NS_ETSI}}}SigningTime", instante.isoformat())

    certificado_firmante = _sub(props_firma, f"{{{NS_ETSI}}}SigningCertificate")
    cert = _sub(certificado_firmante, f"{{{NS_ETSI}}}Cert")
    cert_digest = _sub(cert, f"{{{NS_ETSI}}}CertDigest")
    _sub(cert_digest, f"{{{NS_DS}}}DigestMethod", Algorithm=ALGORITMO_DIGEST)
    _sub(cert_digest, f"{{{NS_DS}}}DigestValue", firmante.digest_certificado)

    emisor_serie = _sub(cert, f"{{{NS_ETSI}}}IssuerSerial")
    _sub(emisor_serie, f"{{{NS_DS}}}X509IssuerName", firmante.emisor)
    _sub(emisor_serie, f"{{{NS_DS}}}X509SerialNumber", str(firmante.numero_serie))

    props_datos = _sub(propiedades, f"{{{NS_ETSI}}}SignedDataObjectProperties")
    formato = _sub(
        props_datos,
        f"{{{NS_ETSI}}}DataObjectFormat",
        ObjectReference=f"#{id_referencia_doc}",
    )
    _sub(formato, f"{{{NS_ETSI}}}Description", "contenido comprobante")
    _sub(formato, f"{{{NS_ETSI}}}MimeType", "text/xml")

    # --- Digests que dependen del árbol ya construido ---
    digest_propiedades.text = _digest_b64(_c14n(propiedades))
    digest_key_info.text = _digest_b64(_c14n(key_info))

    # --- Firma RSA sobre el SignedInfo canonicalizado ---
    firma_binaria = firmante.clave_privada.sign(
        _c14n(signed_info), padding.PKCS1v15(), hashes.SHA1()
    )
    valor_firma.text = base64.b64encode(firma_binaria).decode()

    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def verificar_firma(xml_firmado: bytes) -> dict[str, bool]:
    """
    Verificación interna: recalcula los tres digests y comprueba la firma RSA
    contra la clave pública del certificado incrustado.

    Confirma que lo generado es criptográficamente consistente. No sustituye la
    validación del SRI, que además comprueba que la entidad certificadora esté
    acreditada.
    """
    raiz = etree.fromstring(xml_firmado)
    firma = raiz.find(f"{{{NS_DS}}}Signature")
    if firma is None:
        raise ErrorFirma("El XML no contiene una firma.")

    signed_info = firma.find(f"{{{NS_DS}}}SignedInfo")
    key_info = firma.find(f"{{{NS_DS}}}KeyInfo")
    propiedades = firma.find(
        f"{{{NS_DS}}}Object/{{{NS_ETSI}}}QualifyingProperties/{{{NS_ETSI}}}SignedProperties"
    )

    referencias = signed_info.findall(f"{{{NS_DS}}}Reference")
    digest_por_uri = {
        ref.get("URI"): ref.find(f"{{{NS_DS}}}DigestValue").text for ref in referencias
    }

    id_propiedades = propiedades.get("Id")
    id_certificado = key_info.get("Id")
    id_documento = raiz.get("id")

    # El documento sin firma: se replica la transformada enveloped-signature.
    copia = etree.fromstring(xml_firmado)
    copia.remove(copia.find(f"{{{NS_DS}}}Signature"))

    resultados = {
        "digest_signed_properties": digest_por_uri.get(f"#{id_propiedades}")
        == _digest_b64(_c14n(propiedades)),
        "digest_key_info": digest_por_uri.get(f"#{id_certificado}")
        == _digest_b64(_c14n(key_info)),
        "digest_documento": digest_por_uri.get(f"#{id_documento}") == _digest_b64(_c14n(copia)),
    }

    certificado_b64 = raiz.find(
        f"{{{NS_DS}}}Signature/{{{NS_DS}}}KeyInfo/{{{NS_DS}}}X509Data/{{{NS_DS}}}X509Certificate"
    ).text
    from cryptography.x509 import load_der_x509_certificate

    certificado = load_der_x509_certificate(base64.b64decode(certificado_b64))
    valor = base64.b64decode(firma.find(f"{{{NS_DS}}}SignatureValue").text)

    try:
        certificado.public_key().verify(
            valor, _c14n(signed_info), padding.PKCS1v15(), hashes.SHA1()
        )
        resultados["firma_rsa"] = True
    except Exception:  # noqa: BLE001 - la verificación fallida no es excepcional aquí
        resultados["firma_rsa"] = False

    return resultados
