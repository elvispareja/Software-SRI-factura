"""
Clave de acceso de 49 dígitos de los comprobantes electrónicos del SRI.

Estructura (Ficha Técnica de Comprobantes Electrónicos):

    | Campo                | Long |
    |----------------------|------|
    | Fecha de emisión     |   8  |  ddmmaaaa
    | Tipo de comprobante  |   2  |  01 = factura
    | RUC del emisor       |  13  |
    | Ambiente             |   1  |  1 = pruebas, 2 = producción
    | Serie                |   6  |  establecimiento (3) + punto de emisión (3)
    | Secuencial           |   9  |
    | Código numérico      |   8  |  lo define el emisor
    | Tipo de emisión      |   1  |  1 = normal
    | Dígito verificador   |   1  |  módulo 11
                             ----
                              49

La clave es además el identificador con el que se consulta la autorización, así
que un error aquí no se detecta hasta que el SRI devuelve "CLAVE ACCESO
REGISTRADA" o rechaza el comprobante.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

TIPO_COMPROBANTE = {
    "factura": "01",
    "liquidacion_compra": "03",
    "nota_credito": "04",
    "nota_debito": "05",
    "guia_remision": "06",
    "retencion": "07",
}

AMBIENTE_PRUEBAS = "1"
AMBIENTE_PRODUCCION = "2"
EMISION_NORMAL = "1"

# Los pesos del módulo 11 se aplican de derecha a izquierda y se reciclan.
PESOS_MODULO_11 = (2, 3, 4, 5, 6, 7)


def digito_verificador_modulo11(cadena: str) -> int:
    """Dígito verificador módulo 11 de los primeros 48 dígitos de la clave."""
    if not cadena.isdigit():
        raise ValueError("La clave de acceso solo admite dígitos.")

    total = 0
    for posicion, caracter in enumerate(reversed(cadena)):
        peso = PESOS_MODULO_11[posicion % len(PESOS_MODULO_11)]
        total += int(caracter) * peso

    residuo = total % 11
    verificador = 11 - residuo

    # Casos especiales definidos por el SRI.
    if verificador == 11:
        return 0
    if verificador == 10:
        return 1
    return verificador


@dataclass(frozen=True)
class DatosClaveAcceso:
    fecha_emision: date
    tipo_comprobante: str
    ruc: str
    ambiente: str
    establecimiento: str
    punto_emision: str
    secuencial: int
    codigo_numerico: str
    tipo_emision: str = EMISION_NORMAL

    def __post_init__(self) -> None:
        if len(self.ruc) != 13 or not self.ruc.isdigit():
            raise ValueError("El RUC debe tener 13 dígitos.")
        if self.tipo_comprobante not in TIPO_COMPROBANTE.values():
            raise ValueError(f"Tipo de comprobante desconocido: {self.tipo_comprobante}")
        if self.ambiente not in (AMBIENTE_PRUEBAS, AMBIENTE_PRODUCCION):
            raise ValueError("El ambiente debe ser '1' (pruebas) o '2' (producción).")
        if len(self.establecimiento) != 3 or len(self.punto_emision) != 3:
            raise ValueError("Establecimiento y punto de emisión deben tener 3 dígitos.")
        if not 1 <= self.secuencial <= 999_999_999:
            raise ValueError("El secuencial debe estar entre 1 y 999999999.")
        if len(self.codigo_numerico) != 8 or not self.codigo_numerico.isdigit():
            raise ValueError("El código numérico debe tener 8 dígitos.")

    @property
    def serie(self) -> str:
        return f"{self.establecimiento}{self.punto_emision}"

    @property
    def secuencial_formateado(self) -> str:
        return str(self.secuencial).zfill(9)

    @property
    def numero_comprobante(self) -> str:
        """Número legible que se imprime en el RIDE, p. ej. 001-002-000000135."""
        return f"{self.establecimiento}-{self.punto_emision}-{self.secuencial_formateado}"


def generar_clave_acceso(datos: DatosClaveAcceso) -> str:
    """Arma los 48 dígitos y les añade el verificador."""
    base = (
        datos.fecha_emision.strftime("%d%m%Y")
        + datos.tipo_comprobante
        + datos.ruc
        + datos.ambiente
        + datos.serie
        + datos.secuencial_formateado
        + datos.codigo_numerico
        + datos.tipo_emision
    )

    if len(base) != 48:
        raise ValueError(f"La base de la clave debe tener 48 dígitos, tiene {len(base)}.")

    return base + str(digito_verificador_modulo11(base))


def validar_clave_acceso(clave: str) -> bool:
    """Comprueba longitud y dígito verificador de una clave ya generada."""
    if len(clave) != 49 or not clave.isdigit():
        return False
    return digito_verificador_modulo11(clave[:48]) == int(clave[48])


def descomponer_clave_acceso(clave: str) -> dict[str, str]:
    """Separa la clave en sus campos. Útil para depurar rechazos del SRI."""
    if not validar_clave_acceso(clave):
        raise ValueError("Clave de acceso inválida.")

    return {
        "fecha_emision": clave[0:8],
        "tipo_comprobante": clave[8:10],
        "ruc": clave[10:23],
        "ambiente": clave[23:24],
        "serie": clave[24:30],
        "secuencial": clave[30:39],
        "codigo_numerico": clave[39:47],
        "tipo_emision": clave[47:48],
        "digito_verificador": clave[48:49],
    }
