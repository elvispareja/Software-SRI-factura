"""
Validación de identificaciones ecuatorianas.

Réplica en el servidor de lo que valida el frontend: el cliente valida para dar
feedback inmediato, pero el API no puede confiar en él.

    - Cédula: módulo 10, coeficientes 2,1,2,1,2,1,2,1,2
    - RUC jurídico (3.er dígito 9): módulo 11, coeficientes 4,3,2,7,6,5,4,3,2
    - RUC público  (3.er dígito 6): módulo 11, coeficientes 3,2,7,6,5,4,3,2
    - RUC natural  (3.er dígito 0-5): los 10 primeros son una cédula
"""

from __future__ import annotations

from dataclasses import dataclass

CONSUMIDOR_FINAL = "9999999999999"

PROVINCIA_MIN = 1
PROVINCIA_MAX = 24
PROVINCIA_EXTERIOR = 30

# Código del SRI (tabla 6) por nombre usado en la interfaz.
CODIGOS_TIPO_IDENTIFICACION = {
    "RUC": "04",
    "Cédula": "05",
    "Pasaporte": "06",
    "Consumidor Final": "07",
    "Identificación del Exterior": "08",
}


@dataclass(frozen=True)
class ResultadoValidacion:
    es_valida: bool
    tipo: str | None = None
    error: str | None = None


def _provincia_valida(valor: str) -> bool:
    provincia = int(valor[:2])
    return PROVINCIA_MIN <= provincia <= PROVINCIA_MAX or provincia == PROVINCIA_EXTERIOR


def _suma_ponderada(digitos: list[int], coeficientes: list[int], reducir: bool) -> int:
    total = 0
    for digito, coeficiente in zip(digitos, coeficientes, strict=True):
        producto = digito * coeficiente
        total += producto - 9 if reducir and producto >= 10 else producto
    return total


def _verificador_modulo11(digitos: list[int], coeficientes: list[int]) -> int:
    residuo = _suma_ponderada(digitos, coeficientes, reducir=False) % 11
    return 0 if residuo == 0 else 11 - residuo


def validar_cedula(valor: str) -> ResultadoValidacion:
    cedula = (valor or "").strip()

    if len(cedula) != 10:
        return ResultadoValidacion(False, error="La cédula debe tener 10 dígitos.")
    if not cedula.isdigit():
        return ResultadoValidacion(False, error="La cédula solo admite dígitos.")
    if not _provincia_valida(cedula):
        return ResultadoValidacion(
            False, error="Los dos primeros dígitos no corresponden a una provincia."
        )

    digitos = [int(caracter) for caracter in cedula]
    # 6 y 9 en la tercera posición están reservados para RUC.
    if digitos[2] > 5:
        return ResultadoValidacion(False, error="El tercer dígito no es válido para una cédula.")

    suma = _suma_ponderada(digitos[:9], [2, 1, 2, 1, 2, 1, 2, 1, 2], reducir=True)
    verificador = (10 - (suma % 10)) % 10

    if verificador != digitos[9]:
        return ResultadoValidacion(False, error="El dígito verificador no coincide.")
    return ResultadoValidacion(True, tipo="persona natural")


def validar_ruc(valor: str) -> ResultadoValidacion:
    ruc = (valor or "").strip()

    if ruc == CONSUMIDOR_FINAL:
        return ResultadoValidacion(True, tipo="consumidor final")
    if len(ruc) != 13:
        return ResultadoValidacion(False, error="El RUC debe tener 13 dígitos.")
    if not ruc.isdigit():
        return ResultadoValidacion(False, error="El RUC solo admite dígitos.")
    if not _provincia_valida(ruc):
        return ResultadoValidacion(
            False, error="Los dos primeros dígitos no corresponden a una provincia."
        )
    if ruc[10:] == "000":
        return ResultadoValidacion(False, error="El código de establecimiento no puede ser 000.")

    digitos = [int(caracter) for caracter in ruc]
    tercer_digito = digitos[2]

    if tercer_digito <= 5:
        if validar_cedula(ruc[:10]).es_valida:
            return ResultadoValidacion(True, tipo="persona natural")
        return ResultadoValidacion(
            False, error="El RUC de persona natural no contiene una cédula válida."
        )

    if tercer_digito == 6:
        verificador = _verificador_modulo11(digitos[:8], [3, 2, 7, 6, 5, 4, 3, 2])
        if verificador == digitos[8]:
            return ResultadoValidacion(True, tipo="sector público")
        return ResultadoValidacion(False, error="El dígito verificador del RUC público no coincide.")

    if tercer_digito == 9:
        verificador = _verificador_modulo11(digitos[:9], [4, 3, 2, 7, 6, 5, 4, 3, 2])
        if verificador == digitos[9]:
            return ResultadoValidacion(True, tipo="sociedad privada")
        return ResultadoValidacion(False, error="El dígito verificador del RUC no coincide.")

    return ResultadoValidacion(
        False, error="El tercer dígito no corresponde a ningún tipo de contribuyente."
    )


def validar_identificacion(tipo: str, valor: str) -> ResultadoValidacion:
    identificacion = (valor or "").strip()

    if tipo == "Cédula":
        return validar_cedula(identificacion)
    if tipo == "RUC":
        return validar_ruc(identificacion)
    if tipo == "Consumidor Final":
        if identificacion == CONSUMIDOR_FINAL:
            return ResultadoValidacion(True, tipo="consumidor final")
        return ResultadoValidacion(False, error=f"Consumidor final debe ser {CONSUMIDOR_FINAL}.")
    if tipo in ("Pasaporte", "Identificación del Exterior"):
        if len(identificacion) >= 3:
            return ResultadoValidacion(True, tipo=tipo.lower())
        return ResultadoValidacion(False, error="Ingresa al menos 3 caracteres.")

    return ResultadoValidacion(False, error=f"Tipo de identificación desconocido: {tipo}")


def codigo_sri(tipo: str) -> str:
    """Código de la tabla 6 del SRI que va en `tipoIdentificacionComprador`."""
    return CODIGOS_TIPO_IDENTIFICACION.get(tipo, "07")
