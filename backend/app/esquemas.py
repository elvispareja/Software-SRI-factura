"""Esquemas Pydantic: contrato del API, separado de los modelos de base de datos."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .sri.identificacion import validar_identificacion


class Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------
# Receptores
# --------------------------------------------------------------------------


class ReceptorEntrada(Base):
    tipo_identificacion: str
    identificacion: str
    razon_social: str = Field(min_length=1, max_length=300)
    nombre_comercial: str | None = None
    tipo_persona: str = "Natural"
    rol: str = "Cliente"
    correo: str | None = None
    correo2: str | None = None
    telefono1: str | None = None
    telefono2: str | None = None
    # Obligatoria: el XML del SRI la exige como direccionComprador.
    direccion: str = Field(min_length=1, max_length=300)
    provincia: str | None = None
    canton: str | None = None
    metodo_cancelacion: str = "Contado"
    vendedor: str | None = None
    lista_precio: str = "PVP 1"
    zona: str | None = None
    descuento: Decimal = Decimal("0")
    credito_maximo: Decimal = Decimal("0")
    estado: str = "Activo"

    @field_validator("identificacion")
    @classmethod
    def identificacion_valida(cls, valor: str, info) -> str:
        tipo = info.data.get("tipo_identificacion")
        if tipo is None:
            return valor
        resultado = validar_identificacion(tipo, valor)
        if not resultado.es_valida:
            raise ValueError(resultado.error)
        return valor


class ReceptorSalida(ReceptorEntrada):
    id: int


# --------------------------------------------------------------------------
# Artículos
# --------------------------------------------------------------------------


class ArticuloEntrada(Base):
    codigo: str = Field(min_length=1, max_length=50)
    codigo_auxiliar: str | None = None
    nombre: str = Field(min_length=1, max_length=300)
    detalle: str | None = None
    tipo: str = "Producto"
    categoria: str | None = None
    marca: str | None = None
    unidad: str = "Unidad"
    bodega: str | None = None
    ubicacion: str | None = None
    codigo_iva: str = "4"
    codigo_ice: str | None = None
    costo: Decimal = Decimal("0")
    precio: Decimal = Decimal("0")
    stock: Decimal | None = None
    stock_minimo: Decimal = Decimal("0")
    punto_reorden: Decimal = Decimal("0")
    stock_maximo: Decimal = Decimal("0")
    estado: str = "Activo"

    @field_validator("codigo_iva")
    @classmethod
    def iva_conocido(cls, valor: str) -> str:
        from .sri.modelos import PORCENTAJES_IVA

        if valor not in PORCENTAJES_IVA:
            raise ValueError(f"Código de IVA desconocido: {valor}")
        return valor


class ArticuloSalida(ArticuloEntrada):
    id: int


# --------------------------------------------------------------------------
# Comprobantes
# --------------------------------------------------------------------------


class DetalleEntrada(Base):
    codigo_principal: str
    codigo_auxiliar: str | None = None
    descripcion: str
    # Guardas numéricas en el servidor: hasta ahora solo las validaba el
    # frontend, y un descuento negativo o un IVA desconocido derivaban en un
    # importe negativo o en un 500. Aquí devuelven 422.
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    descuento_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    codigo_iva: str = "4"

    @field_validator("codigo_iva")
    @classmethod
    def iva_conocido(cls, valor: str) -> str:
        from .sri.modelos import PORCENTAJES_IVA

        if valor not in PORCENTAJES_IVA:
            raise ValueError(f"Código de IVA desconocido: {valor}")
        return valor


class DetalleSalida(DetalleEntrada):
    id: int
    descuento: Decimal
    base_imponible: Decimal
    valor_iva: Decimal
    total: Decimal


class ComprobanteEntrada(Base):
    tipo: str = "Factura"
    fecha_emision: date | None = None
    receptor_id: int
    establecimiento: str = "001"
    punto_emision: str = "001"
    metodo: str = "Contado"
    forma_pago: str = "01"
    detalles: list[DetalleEntrada] = Field(min_length=1)

    # Solo cotizaciones
    validez_dias: int | None = None

    # Solo notas de crédito y débito; el router exige los tres juntos.
    cod_doc_modificado: str | None = "01"
    num_doc_modificado: str | None = None
    fecha_doc_modificado: date | None = None
    motivo: str | None = None


class ComprobanteSalida(Base):
    id: int
    tipo: str
    clave_acceso: str | None
    numero: str
    secuencial: int
    fecha_emision: date
    receptor_razon_social: str
    receptor_identificacion: str
    total_sin_impuestos: Decimal
    total_descuento: Decimal
    total_iva: Decimal
    importe_total: Decimal
    metodo: str
    estado_sri: str
    estado_pago: str
    numero_autorizacion: str | None
    validez_dias: int | None = None
    num_doc_modificado: str | None = None
    motivo: str | None = None
    detalles: list[DetalleSalida] = []


# --------------------------------------------------------------------------
# Guías de remisión
# --------------------------------------------------------------------------


class ItemGuiaEntrada(Base):
    codigo: str = ""
    descripcion: str = Field(min_length=1)
    cantidad: Decimal = Decimal("1")


class ItemGuiaSalida(ItemGuiaEntrada):
    id: int


class GuiaEntrada(Base):
    establecimiento: str = "001"
    punto_emision: str = "001"
    fecha_inicio: date
    fecha_fin: date | None = None
    motivo_traslado: str = Field(min_length=1)
    ruta: str | None = None
    tipo_transporte: str = "Privado"
    documento_aduanero: str | None = None
    transportista_id: int
    placa: str = Field(min_length=1, max_length=20)
    provincia_partida: str | None = None
    canton_partida: str | None = None
    direccion_partida: str = Field(min_length=1)
    provincia_llegada: str | None = None
    canton_llegada: str | None = None
    direccion_llegada: str = Field(min_length=1)
    items: list[ItemGuiaEntrada] = Field(min_length=1)

    @field_validator("fecha_fin")
    @classmethod
    def fin_no_anterior_al_inicio(cls, valor: date | None, info) -> date | None:
        inicio = info.data.get("fecha_inicio")
        if valor and inicio and valor < inicio:
            raise ValueError("La fecha fin no puede ser anterior a la fecha de inicio.")
        return valor


class GuiaSalida(Base):
    id: int
    numero: str
    clave_acceso: str | None
    fecha_inicio: date
    fecha_fin: date | None
    motivo_traslado: str
    tipo_transporte: str
    transportista_razon_social: str
    transportista_identificacion: str
    placa: str
    direccion_partida: str
    direccion_llegada: str
    estado_sri: str
    numero_autorizacion: str | None = None
    items: list[ItemGuiaSalida] = []


# --------------------------------------------------------------------------
# Retenciones
# --------------------------------------------------------------------------


class DetalleRetencionEntrada(Base):
    codigo_impuesto: str = "1"
    codigo_retencion: str = Field(min_length=1, max_length=10)
    base_imponible: Decimal = Decimal("0")
    porcentaje_retener: Decimal = Decimal("0")

    @field_validator("codigo_impuesto")
    @classmethod
    def impuesto_conocido(cls, valor: str) -> str:
        from .sri.codigos_retencion import IMPUESTOS

        if valor not in IMPUESTOS:
            raise ValueError(
                f"Impuesto {valor} desconocido. Usa 1 (renta), 2 (IVA) o 6 (ISD)."
            )
        return valor

    @field_validator("porcentaje_retener")
    @classmethod
    def porcentaje_en_rango(cls, valor: Decimal) -> Decimal:
        if valor < 0 or valor > 100:
            raise ValueError("El porcentaje a retener debe estar entre 0 y 100.")
        return valor


class DetalleRetencionSalida(DetalleRetencionEntrada):
    id: int
    valor_retenido: Decimal


class RetencionEntrada(Base):
    establecimiento: str = "001"
    punto_emision: str = "001"
    fecha_emision: date | None = None
    periodo_fiscal: str | None = None
    sujeto_id: int
    cod_doc_sustento: str = "01"
    num_doc_sustento: str = Field(min_length=1, max_length=20)
    fecha_doc_sustento: date | None = None
    detalles: list[DetalleRetencionEntrada] = Field(min_length=1)

    @field_validator("periodo_fiscal")
    @classmethod
    def periodo_con_formato_sri(cls, valor: str | None) -> str | None:
        # El SRI lo quiere como MM/AAAA, no como fecha.
        if valor is None:
            return valor
        partes = valor.split("/")
        if len(partes) != 2 or len(partes[0]) != 2 or len(partes[1]) != 4:
            raise ValueError("El período fiscal debe tener el formato MM/AAAA.")
        if not (1 <= int(partes[0]) <= 12):
            raise ValueError("El mes del período fiscal no es válido.")
        return valor


class RetencionSalida(Base):
    id: int
    numero: str
    clave_acceso: str | None
    fecha_emision: date
    periodo_fiscal: str
    sujeto_razon_social: str
    sujeto_identificacion: str
    cod_doc_sustento: str
    num_doc_sustento: str
    fecha_doc_sustento: date | None
    total_retenido: Decimal
    estado_sri: str
    numero_autorizacion: str | None = None
    detalles: list[DetalleRetencionSalida] = []


# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------


class PuntoEmisionEntrada(Base):
    codigo: str = Field(min_length=1, max_length=3)
    nombre: str
    secuencial_factura: int = 1


class PuntoEmisionSalida(PuntoEmisionEntrada):
    id: int


class EstablecimientoEntrada(Base):
    codigo: str = Field(min_length=1, max_length=3)
    nombre: str
    direccion: str
    puntos_emision: list[PuntoEmisionEntrada] = []


class EstablecimientoSalida(Base):
    id: int
    codigo: str
    nombre: str
    direccion: str
    puntos_emision: list[PuntoEmisionSalida] = []


class EmpresaEntrada(Base):
    ruc: str
    razon_social: str
    nombre_comercial: str | None = None
    direccion_matriz: str
    provincia: str | None = None
    canton: str | None = None
    telefono: str | None = None
    correo: str | None = None
    regimen: str = "Régimen General"
    obligado_contabilidad: bool = True
    contribuyente_especial: str | None = None
    agente_retencion: str | None = None
    contribuyente_rimpe: str | None = None
    ambiente: str = "1"

    @field_validator("ruc")
    @classmethod
    def ruc_valido(cls, valor: str) -> str:
        resultado = validar_identificacion("RUC", valor)
        if not resultado.es_valida:
            raise ValueError(resultado.error)
        return valor


class EmpresaSalida(EmpresaEntrada):
    id: int
    establecimientos: list[EstablecimientoSalida] = []


class CuentaBancariaEntrada(Base):
    banco: str = Field(min_length=1, max_length=120)
    tipo: str = "Corriente"
    numero: str = Field(min_length=1, max_length=50)
    titular: str = Field(min_length=1, max_length=200)


class CuentaBancariaSalida(CuentaBancariaEntrada):
    id: int


class FirmaSalida(Base):
    """
    Metadatos del certificado.

    Deliberadamente **no** expone `contenido` ni `contrasena_cifrada`: el
    archivo y la clave no salen del servidor por ningún endpoint.
    """

    id: int
    nombre_archivo: str
    propietario: str
    emisor: str
    numero_serie: str
    valida_desde: date
    valida_hasta: date


# --------------------------------------------------------------------------
# Respuestas comunes
# --------------------------------------------------------------------------


class Pagina(Base):
    total: int
    pagina: int
    tamano: int


class RespuestaEmision(Base):
    comprobante: ComprobanteSalida
    estado_recepcion: str
    estado_autorizacion: str | None = None
    mensajes: list[dict] = []


class RespuestaEmisionGuia(Base):
    guia: GuiaSalida
    estado_recepcion: str
    estado_autorizacion: str | None = None
    mensajes: list[dict] = []


class RespuestaEmisionRetencion(Base):
    retencion: RetencionSalida
    estado_recepcion: str
    estado_autorizacion: str | None = None
    mensajes: list[dict] = []


# --------------------------------------------------------------------------
# Reportes
# --------------------------------------------------------------------------


class ResumenVentas(Base):
    desde: date
    hasta: date
    comprobantes: int
    subtotal: Decimal
    descuento: Decimal
    iva: Decimal
    total: Decimal
    ticket_promedio: Decimal


class VentasPorTipo(Base):
    tipo: str
    cantidad: int
    total: Decimal


class VentasPorMes(Base):
    mes: int
    cantidad: int
    total: Decimal


class ClienteDestacado(Base):
    razon_social: str
    identificacion: str
    comprobantes: int
    total: Decimal


class ArticuloDestacado(Base):
    codigo: str
    descripcion: str
    cantidad: Decimal
    total: Decimal


class TarifaIvaReporte(Base):
    codigo_iva: str
    porcentaje: Decimal
    base_imponible: Decimal
    valor_iva: Decimal


class ReporteIva(Base):
    """Sustento del formulario 104: ventas agrupadas por tarifa."""

    periodo_fiscal: str
    desde: date
    hasta: date
    tarifas: list[TarifaIvaReporte]
    base_total: Decimal
    iva_total: Decimal


class ConceptoRetenido(Base):
    codigo_impuesto: str
    codigo_retencion: str
    lineas: int
    base_imponible: Decimal
    valor_retenido: Decimal


class ReporteRetenciones(Base):
    """Sustento del formulario 103: retenciones agrupadas por concepto."""

    periodo_fiscal: str
    comprobantes: int
    conceptos: list[ConceptoRetenido]
    total_renta: Decimal
    total_iva: Decimal
    total_retenido: Decimal


class ConteoEstado(Base):
    estado: str
    cantidad: int


class ReporteEstadoSri(Base):
    desde: date
    hasta: date
    por_estado: list[ConteoEstado]
    total: int
    requieren_atencion: int


class PorCobrar(Base):
    comprobantes: int
    total: Decimal
    a_credito: Decimal


class Panel(Base):
    """Todo lo que pinta el Dashboard, en una sola respuesta."""

    hoy: date
    ambiente: str = "1"
    mes: ResumenVentas
    anio: ResumenVentas
    por_tipo: list[VentasPorTipo]
    serie_mensual: list[VentasPorMes]
    top_clientes: list[ClienteDestacado]
    top_articulos: list[ArticuloDestacado]
    estado_sri: ReporteEstadoSri
    por_cobrar: PorCobrar


# --------------------------------------------------------------------------
# Egresos: tipos de gasto, gastos y pagos
# --------------------------------------------------------------------------


class TipoGastoEntrada(Base):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = None
    deducible: bool = True
    estado: str = "Activo"


class TipoGastoSalida(TipoGastoEntrada):
    id: int


class GastoEntrada(Base):
    fecha: date | None = None
    concepto: str = Field(min_length=1, max_length=300)
    tipo_id: int | None = None
    proveedor_id: int | None = None
    documento: str = ""
    fecha_documento: date | None = None
    autorizacion_proveedor: str | None = None
    subtotal: Decimal = Decimal("0")
    iva: Decimal = Decimal("0")
    codigo_iva: str = "4"
    estado_pago: str = "Por Pagar"
    observacion: str | None = None

    @field_validator("subtotal", "iva")
    @classmethod
    def no_negativo(cls, valor: Decimal) -> Decimal:
        if valor < 0:
            raise ValueError("Los importes de un gasto no pueden ser negativos.")
        return valor

    @field_validator("codigo_iva")
    @classmethod
    def iva_conocido(cls, valor: str) -> str:
        from .sri.modelos import PORCENTAJES_IVA

        if valor not in PORCENTAJES_IVA:
            raise ValueError(f"Código de IVA desconocido: {valor}")
        return valor


class GastoSalida(Base):
    id: int
    fecha: date
    concepto: str
    tipo_id: int | None
    proveedor_id: int | None
    proveedor_razon_social: str
    proveedor_identificacion: str
    documento: str
    fecha_documento: date | None
    autorizacion_proveedor: str | None
    subtotal: Decimal
    iva: Decimal
    codigo_iva: str
    total: Decimal
    estado_pago: str
    observacion: str | None


class EgresoEntrada(Base):
    fecha: date | None = None
    concepto: str = Field(min_length=1, max_length=300)
    beneficiario: str = ""
    monto: Decimal = Decimal("0")
    forma_pago: str = "Efectivo"
    cuenta_id: int | None = None
    referencia: str | None = None
    gasto_id: int | None = None
    observacion: str | None = None

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, valor: Decimal) -> Decimal:
        # Un pago de cero no es un pago; y uno negativo es un ingreso, que se
        # registra en otro sitio.
        if valor <= 0:
            raise ValueError("El monto del egreso debe ser mayor que cero.")
        return valor


class EgresoSalida(Base):
    id: int
    fecha: date
    concepto: str
    beneficiario: str
    monto: Decimal
    forma_pago: str
    cuenta_id: int | None
    referencia: str | None
    gasto_id: int | None
    estado: str
    observacion: str | None


class ResumenEgresos(Base):
    gastos: int
    total_gastos: Decimal
    total_pagos: Decimal
    pendiente: Decimal


# --------------------------------------------------------------------------
# Anticipos
# --------------------------------------------------------------------------


class AnticipoEntrada(Base):
    fecha: date | None = None
    # ARD: recibido de un cliente. APP: pagado a un proveedor.
    tipo: str = "ARD"
    receptor_id: int
    detalle: str = ""
    monto: Decimal = Decimal("0")
    forma_pago: str = "Transferencia"

    @field_validator("tipo")
    @classmethod
    def tipo_conocido(cls, valor: str) -> str:
        if valor not in ("ARD", "APP"):
            raise ValueError("El tipo de anticipo debe ser ARD (recibido) o APP (pagado).")
        return valor

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, valor: Decimal) -> Decimal:
        if valor <= 0:
            raise ValueError("El monto del anticipo debe ser mayor que cero.")
        return valor


class AnticipoSalida(Base):
    id: int
    fecha: date
    tipo: str
    receptor_id: int | None
    receptor_razon_social: str
    detalle: str
    monto: Decimal
    facturado: Decimal
    saldo: Decimal
    forma_pago: str
    estado: str


class AplicarAnticipo(Base):
    """Cuánto del anticipo se imputa a una factura."""

    monto: Decimal

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, valor: Decimal) -> Decimal:
        if valor <= 0:
            raise ValueError("El monto a aplicar debe ser mayor que cero.")
        return valor


class DevolverAnticipo(Base):
    """
    Devuelve el saldo sobrante de un anticipo.

    Deliberadamente **sin monto**: el saldo lo calcula el servidor como
    `monto - facturado`, para que la devolución no pueda descuadrar.
    """

    fecha: date | None = None
    forma_pago: str = "Transferencia"
    observacion: str | None = None


class DevolucionAnticipoSalida(Base):
    id: int
    anticipo_id: int
    fecha: date
    monto: Decimal
    forma_pago: str
    observacion: str | None


# --------------------------------------------------------------------------
# Facturación recurrente
# --------------------------------------------------------------------------


class LineaRecurrenteEntrada(Base):
    codigo_principal: str = "SIN-COD"
    descripcion: str = Field(min_length=1, max_length=300)
    # Mismas guardas que en DetalleEntrada: la plantilla recurrente termina
    # generando facturas reales, así que un valor fuera de rango debe frenarse
    # al guardar la plantilla, no al emitir.
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    descuento_porcentaje: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    codigo_iva: str = "4"

    @field_validator("codigo_iva")
    @classmethod
    def iva_conocido(cls, valor: str) -> str:
        from .sri.modelos import PORCENTAJES_IVA

        if valor not in PORCENTAJES_IVA:
            raise ValueError(f"Código de IVA desconocido: {valor}")
        return valor


class LineaRecurrenteSalida(LineaRecurrenteEntrada):
    id: int


class PlantillaRecurrenteEntrada(Base):
    nombre: str = Field(min_length=1, max_length=200)
    receptor_id: int
    periodicidad: str = "Mensual"
    proxima_emision: date
    hasta: date | None = None
    establecimiento: str = "001"
    punto_emision: str = "001"
    forma_pago: str = "01"
    activa: bool = True
    lineas: list[LineaRecurrenteEntrada] = Field(min_length=1)

    @field_validator("periodicidad")
    @classmethod
    def periodicidad_conocida(cls, valor: str) -> str:
        from .servicios.recurrentes import PERIODICIDADES

        if valor not in PERIODICIDADES:
            raise ValueError(
                f"Periodicidad desconocida: {valor}. "
                f"Usa una de {', '.join(PERIODICIDADES)}."
            )
        return valor

    @field_validator("hasta")
    @classmethod
    def hasta_no_anterior(cls, valor: date | None, info) -> date | None:
        proxima = info.data.get("proxima_emision")
        if valor and proxima and valor < proxima:
            raise ValueError("La fecha de fin no puede ser anterior a la próxima emisión.")
        return valor


class PlantillaRecurrenteSalida(Base):
    id: int
    nombre: str
    receptor_id: int | None
    receptor_razon_social: str
    periodicidad: str
    proxima_emision: date
    ultima_emision: date | None
    hasta: date | None
    establecimiento: str
    punto_emision: str
    forma_pago: str
    total: Decimal
    emitidas: int
    activa: bool
    lineas: list[LineaRecurrenteSalida] = []


class RespuestaEmisionRecurrente(Base):
    plantilla: PlantillaRecurrenteSalida
    comprobante: ComprobanteSalida


# --------------------------------------------------------------------------
# Reportes por familia de documento
# --------------------------------------------------------------------------


class ReceptorEnReporte(Base):
    razon_social: str
    identificacion: str
    comprobantes: int
    total: Decimal


class ReceptorCotizado(ReceptorEnReporte):
    """Indica si ese receptor tuvo factura en el mismo período."""

    con_factura: bool = False


class ReporteNotasVenta(Base):
    desde: date
    hasta: date
    receptores: list[ReceptorEnReporte]
    comprobantes: int
    total: Decimal


class ReporteCotizaciones(Base):
    desde: date
    hasta: date
    receptores: list[ReceptorCotizado]
    comprobantes: int
    total: Decimal
    receptores_con_factura: int


class DocumentoNota(Base):
    numero: str
    tipo: str
    fecha: date
    receptor: str
    documento_modificado: str
    motivo: str
    total: Decimal


class ReporteNotas(Base):
    """Notas de crédito y débito del período, nunca sumadas entre sí."""

    desde: date
    hasta: date
    notas_credito: int
    total_credito: Decimal
    notas_debito: int
    total_debito: Decimal
    neto: Decimal
    documentos: list[DocumentoNota]


class TipoEnReporteEgresos(Base):
    tipo: str
    deducible: bool
    gastos: int
    subtotal: Decimal
    iva: Decimal
    total: Decimal


class ReporteEgresos(Base):
    desde: date
    hasta: date
    tipos: list[TipoEnReporteEgresos]
    total: Decimal
    total_deducible: Decimal
    iva_soportado: Decimal
    total_pagado: Decimal


# --------------------------------------------------------------------------
# Envío por correo
# --------------------------------------------------------------------------


class EnvioCorreo(Base):
    """
    Destinatario alternativo.

    Por defecto se usa el correo del receptor; este campo existe para cuando
    el cliente pide que se mande a contabilidad y no a quien compró.
    """

    destinatario: str | None = None
    copia: str | None = None


class RespuestaEnvio(Base):
    enviado: bool
    destinatario: str
    mensaje: str


# --------------------------------------------------------------------------
# Cuentas por cobrar: cuotas y recibos
# --------------------------------------------------------------------------


class GenerarCuotas(Base):
    cuotas: int = Field(ge=1, le=60)
    dias_entre_cuotas: int = Field(default=30, ge=1, le=365)
    primera_fecha: date | None = None


class CuotaSalida(Base):
    id: int
    comprobante_id: int
    numero_comprobante: str
    receptor: str
    numero: int
    vence: date
    monto: Decimal
    cobrado: Decimal
    saldo: Decimal
    estado: str
    # Positivo son días de mora; cero si no vence o ya se cobró.
    dias_mora: int


class ReciboEntrada(Base):
    fecha: date | None = None
    cuota_id: int | None = None
    comprobante_id: int | None = None
    monto: Decimal = Decimal("0")
    forma_pago: str = "Efectivo"
    cuenta_id: int | None = None
    referencia: str | None = None
    observacion: str | None = None

    @field_validator("monto")
    @classmethod
    def monto_positivo(cls, valor: Decimal) -> Decimal:
        if valor <= 0:
            raise ValueError("El monto del recibo debe ser mayor que cero.")
        return valor


class ReciboSalida(Base):
    id: int
    numero: str
    fecha: date
    cuota_id: int | None
    comprobante_id: int | None
    receptor_razon_social: str
    monto: Decimal
    forma_pago: str
    referencia: str | None
    estado: str
    observacion: str | None


class ResumenCobros(Base):
    pendiente: Decimal
    vencido: Decimal
    por_vencer_30: Decimal
    cuotas_vencidas: int
    cobrado_mes: Decimal


# --------------------------------------------------------------------------
# Saldos iniciales (arrastre)
# --------------------------------------------------------------------------


class SaldoInicialEntrada(Base):
    # Opcional: el saldo puede cargarse a nombre de un receptor del catálogo o
    # a nombre libre, escribiendo la razón social a mano.
    receptor_id: int | None = None
    receptor_razon_social: str = ""
    tipo: str = "cobrar"
    monto: Decimal = Field(default=Decimal("0"), ge=0)
    fecha: date | None = None
    detalle: str = ""
    documento: str = ""

    @field_validator("tipo")
    @classmethod
    def tipo_conocido(cls, valor: str) -> str:
        if valor not in ("cobrar", "pagar"):
            raise ValueError("El tipo de saldo debe ser 'cobrar' o 'pagar'.")
        return valor


class SaldoInicialSalida(Base):
    id: int
    receptor_id: int | None
    receptor_razon_social: str
    identificacion: str
    tipo: str
    monto: Decimal
    fecha: date
    detalle: str
    documento: str


# --------------------------------------------------------------------------
# Reportes de cuentas pendientes
#
# Los cinco comparten dos campos de cabecera: `modo` (cobrar o pagar) y
# `etiqueta_contacto` (Cliente o Proveedor). Van en la respuesta y no los
# deduce la interfaz porque el modo decide qué tablas se leyeron, y quien lee
# el CSV suelto tiene que poder saberlo sin ver la pantalla.
# --------------------------------------------------------------------------


class DocumentoPendiente(Base):
    """Un documento con deuda viva. `origen` dice de qué tabla salió."""

    origen: str
    documento_id: int
    tipo: str
    numero: str
    fecha: date
    contacto: str
    identificacion: str
    moneda: str
    vence: date
    # Positivo son días de mora; cero si ya no debe nada.
    dias_mora: int
    total: Decimal
    abonado: Decimal
    saldo: Decimal
    estado: str


class ReporteSaldosPendientes(Base):
    modo: str
    etiqueta_contacto: str
    moneda: str
    hoy: date
    documentos: list[DocumentoPendiente]
    total_documentos: int
    total_original: Decimal
    abonado: Decimal
    saldo: Decimal


class CuotaAgendada(Base):
    origen: str
    documento_id: int
    documento: str
    tipo: str
    contacto: str
    identificacion: str
    correo: str
    telefono: str
    # Nulo cuando el documento no tiene plan de cuotas y entra como cuota única.
    cuota_id: int | None
    numero: int
    vence: date
    dias_mora: int
    monto: Decimal
    abonado: Decimal
    saldo: Decimal
    estado: str


class ReporteAgendaCuotas(Base):
    modo: str
    etiqueta_contacto: str
    desde: date | None
    hasta: date | None
    hoy: date
    cuotas: list[CuotaAgendada]
    total_cuotas: int
    monto: Decimal
    abonado: Decimal
    saldo: Decimal
    vencidas: int
    saldo_vencido: Decimal


class ReciboAplicado(Base):
    origen: str
    recibo_id: int
    numero: str
    fecha: date
    contacto: str
    documento: str
    cuota_id: int | None
    monto: Decimal
    forma_pago: str
    estado: str
    referencia: str


class ReporteRecibosGenerados(Base):
    modo: str
    etiqueta_contacto: str
    desde: date | None
    hasta: date | None
    recibos: list[ReciboAplicado]
    total_recibos: int
    aplicado: Decimal
    anulados: int
    monto_anulado: Decimal


class RotacionFila(Base):
    grupo: str
    documentos: int
    total: Decimal
    cobrado: Decimal
    pendiente: Decimal
    promedio: Decimal
    # Nulo, y no cero, cuando en el período no se movió dinero: cero diría que
    # se cobra al contado, que es lo contrario de la verdad.
    dias_recuperacion: Decimal | None


class ReporteRotacionCuentas(Base):
    modo: str
    etiqueta_contacto: str
    desde: date
    hasta: date
    dias_periodo: int
    por_tipo: list[RotacionFila]
    por_contacto: list[RotacionFila]
    totales: RotacionFila


class HistorialContacto(Base):
    receptor_id: int | None
    contacto: str
    identificacion: str
    correo: str
    telefono: str
    documentos: int
    total: Decimal
    abonado: Decimal
    saldo: Decimal
    cuotas_pendientes: int
    cuotas_vencidas: int
    saldo_vencido: Decimal
    proxima_fecha: date | None
    ultimo_movimiento: date | None


class ReporteHistorialContactos(Base):
    modo: str
    etiqueta_contacto: str
    hoy: date
    contactos: list[HistorialContacto]
    total_contactos: int
    total: Decimal
    abonado: Decimal
    saldo: Decimal


# --------------------------------------------------------------------------
# Listas auxiliares de configuración
# --------------------------------------------------------------------------


class ListaAuxiliarEntrada(Base):
    nombre: str = Field(min_length=1, max_length=200)
    detalle: str | None = None
    estado: str = "Activo"


class ListaAuxiliarSalida(ListaAuxiliarEntrada):
    id: int
    tipo: str


class UsuarioListado(Base):
    """
    Usuario del sistema, sin nada sensible.

    Deliberadamente no expone `contrasena_hash`: aunque sea un hash, no hay
    razón para que salga por el API.
    """

    id: int
    nombre: str
    correo: str
    rol: str
    activo: bool


class ImpuestoCatalogo(Base):
    """Tarifa de IVA de la tabla 17. Es de solo lectura: la fija el SRI."""

    codigo: str
    nombre: str
    porcentaje: Decimal


class ArticuloInventario(Base):
    codigo: str
    nombre: str
    tipo: str
    categoria: str
    unidad: str
    stock: Decimal | None
    stock_minimo: Decimal
    costo: Decimal
    precio: Decimal
    valor: Decimal
    bajo_minimo: bool


class ReporteInventario(Base):
    articulos: list[ArticuloInventario]
    total_articulos: int
    productos: int
    servicios: int
    valor_inventario: Decimal
    bajo_minimo: int


class ReceptorEnListado(Base):
    razon_social: str
    identificacion: str
    tipo_identificacion: str
    rol: str
    correo: str
    telefono: str
    facturado: Decimal


class ReporteReceptores(Base):
    receptores: list[ReceptorEnListado]
    total: int
    clientes: int
    proveedores: int
    transportistas: int
