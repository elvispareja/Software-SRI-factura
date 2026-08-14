"""
Modelos de base de datos.

El dinero se guarda en `Numeric(14, 6)`, no en `Float`: los comprobantes del SRI
se validan al centavo y un float acumula error en cuanto se suman líneas.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base_datos import Base

DINERO = Numeric(14, 6)


def ahora() -> datetime:
    return datetime.now(timezone.utc)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    correo: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    # Nunca la contraseña en claro: aquí va el hash con sal (ver seguridad.py).
    contrasena_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(30), default="administrador")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class TokenRevocado(Base):
    """
    Lista de revocación de tokens JWT (para que el logout tenga efecto inmediato).

    El JWT es autocontenido: una vez emitido vale hasta expirar (~12 h) y borrar
    la cookie no lo invalida. Al cerrar sesión se apunta aquí el `jti` (id único)
    del token; `usuario_actual` rechaza con 401 cualquier token cuyo `jti` figure
    en esta tabla. La crea `Base.metadata.create_all()`; el backend no usa
    migraciones.

    En producción conviene purgar periódicamente las filas cuyo token ya expiró:
    una vez vencido el token, su entrada aquí ya no aporta nada.
    """

    __tablename__ = "tokens_revocados"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    revocado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Empresa(Base):
    __tablename__ = "empresas"

    id: Mapped[int] = mapped_column(primary_key=True)
    ruc: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    nombre_comercial: Mapped[str | None] = mapped_column(String(300), default=None)
    direccion_matriz: Mapped[str] = mapped_column(String(300))
    provincia: Mapped[str | None] = mapped_column(String(100), default=None)
    canton: Mapped[str | None] = mapped_column(String(100), default=None)
    telefono: Mapped[str | None] = mapped_column(String(50), default=None)
    correo: Mapped[str | None] = mapped_column(String(200), default=None)
    regimen: Mapped[str] = mapped_column(String(100), default="Régimen General")
    obligado_contabilidad: Mapped[bool] = mapped_column(Boolean, default=True)
    contribuyente_especial: Mapped[str | None] = mapped_column(String(20), default=None)
    agente_retencion: Mapped[str | None] = mapped_column(String(20), default=None)
    contribuyente_rimpe: Mapped[str | None] = mapped_column(String(100), default=None)
    ambiente: Mapped[str] = mapped_column(String(1), default="1")

    establecimientos: Mapped[list[Establecimiento]] = relationship(
        back_populates="empresa", cascade="all, delete-orphan"
    )


class Establecimiento(Base):
    __tablename__ = "establecimientos"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_establecimiento_codigo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(3))
    nombre: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300))

    empresa: Mapped[Empresa] = relationship(back_populates="establecimientos")
    puntos_emision: Mapped[list[PuntoEmision]] = relationship(
        back_populates="establecimiento", cascade="all, delete-orphan"
    )


class PuntoEmision(Base):
    __tablename__ = "puntos_emision"
    __table_args__ = (
        UniqueConstraint("establecimiento_id", "codigo", name="uq_punto_codigo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    establecimiento_id: Mapped[int] = mapped_column(
        ForeignKey("establecimientos.id", ondelete="CASCADE")
    )
    codigo: Mapped[str] = mapped_column(String(3))
    nombre: Mapped[str] = mapped_column(String(200))
    # Secuencial del PRÓXIMO comprobante. Se incrementa al emitir, nunca se reusa.
    secuencial_factura: Mapped[int] = mapped_column(Integer, default=1)

    establecimiento: Mapped[Establecimiento] = relationship(back_populates="puntos_emision")


class CuentaBancaria(Base):
    """Cuentas que se imprimen en el RIDE para que el cliente sepa dónde pagar."""

    __tablename__ = "cuentas_bancarias"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"))
    banco: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(20), default="Corriente")
    numero: Mapped[str] = mapped_column(String(50))
    titular: Mapped[str] = mapped_column(String(200))
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class FirmaElectronica(Base):
    """
    Certificado .p12 del emisor.

    Los bytes del certificado y la contraseña **cifrada** viven aquí. La
    contraseña nunca se devuelve por el API ni se registra en logs: solo el
    proceso de firma la descifra, en memoria, en el momento de firmar.

    Los metadatos (emisor, propietario, vigencia) se extraen del propio
    certificado al subirlo, no se piden al usuario: así no pueden mentir.
    """

    __tablename__ = "firmas_electronicas"

    id: Mapped[int] = mapped_column(primary_key=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresas.id", ondelete="CASCADE"))
    nombre_archivo: Mapped[str] = mapped_column(String(200))
    contenido: Mapped[bytes] = mapped_column(LargeBinary)
    contrasena_cifrada: Mapped[str] = mapped_column(Text)

    propietario: Mapped[str] = mapped_column(String(300))
    emisor: Mapped[str] = mapped_column(String(300))
    numero_serie: Mapped[str] = mapped_column(String(80))
    valida_desde: Mapped[date] = mapped_column(Date)
    valida_hasta: Mapped[date] = mapped_column(Date)

    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    subida_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class SecuencialDocumento(Base):
    """
    Numeración por punto de emisión **y tipo de documento**.

    El SRI exige secuencias independientes: la factura 000000135 y la nota de
    crédito 000000135 coexisten sin conflicto. Una tabla en vez de una columna
    por tipo evita migrar el esquema cada vez que se soporta un comprobante más.

    `secuencial_factura` en PuntoEmision sigue existiendo como valor inicial de
    la serie de facturas (es lo que edita el usuario en Configuraciones); a
    partir de la primera emisión, el contador vivo es esta tabla.
    """

    __tablename__ = "secuenciales_documento"
    __table_args__ = (
        UniqueConstraint("punto_emision_id", "tipo", name="uq_secuencial_punto_tipo"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    punto_emision_id: Mapped[int] = mapped_column(
        ForeignKey("puntos_emision.id", ondelete="CASCADE")
    )
    tipo: Mapped[str] = mapped_column(String(30))
    siguiente: Mapped[int] = mapped_column(Integer, default=1)


class Receptor(Base):
    __tablename__ = "receptores"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo_identificacion: Mapped[str] = mapped_column(String(50))
    identificacion: Mapped[str] = mapped_column(String(20), index=True)
    razon_social: Mapped[str] = mapped_column(String(300))
    nombre_comercial: Mapped[str | None] = mapped_column(String(300), default=None)
    tipo_persona: Mapped[str] = mapped_column(String(20), default="Natural")
    rol: Mapped[str] = mapped_column(String(20), default="Cliente")
    correo: Mapped[str | None] = mapped_column(String(200), default=None)
    correo2: Mapped[str | None] = mapped_column(String(200), default=None)
    telefono1: Mapped[str | None] = mapped_column(String(50), default=None)
    telefono2: Mapped[str | None] = mapped_column(String(50), default=None)
    direccion: Mapped[str] = mapped_column(String(300), default="")
    provincia: Mapped[str | None] = mapped_column(String(100), default=None)
    canton: Mapped[str | None] = mapped_column(String(100), default=None)
    metodo_cancelacion: Mapped[str] = mapped_column(String(20), default="Contado")
    vendedor: Mapped[str | None] = mapped_column(String(120), default=None)
    lista_precio: Mapped[str] = mapped_column(String(20), default="PVP 1")
    zona: Mapped[str | None] = mapped_column(String(120), default=None)
    descuento: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    credito_maximo: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(20), default="Activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Articulo(Base):
    __tablename__ = "articulos"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    codigo_auxiliar: Mapped[str | None] = mapped_column(String(50), default=None)
    nombre: Mapped[str] = mapped_column(String(300))
    detalle: Mapped[str | None] = mapped_column(Text, default=None)
    tipo: Mapped[str] = mapped_column(String(20), default="Producto")
    categoria: Mapped[str | None] = mapped_column(String(120), default=None)
    marca: Mapped[str | None] = mapped_column(String(120), default=None)
    unidad: Mapped[str] = mapped_column(String(50), default="Unidad")
    bodega: Mapped[str | None] = mapped_column(String(120), default=None)
    ubicacion: Mapped[str | None] = mapped_column(String(120), default=None)
    codigo_iva: Mapped[str] = mapped_column(String(2), default="4")
    codigo_ice: Mapped[str | None] = mapped_column(String(10), default=None)
    costo: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    precio: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    stock: Mapped[Decimal | None] = mapped_column(DINERO, default=None)
    stock_minimo: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    punto_reorden: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    stock_maximo: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    estado: Mapped[str] = mapped_column(String(20), default="Activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)


class Comprobante(Base):
    """
    Documento de venta o compra.

    Una sola tabla para factura, cotización, nota de venta, liquidación de
    compra y nota de crédito/débito: todos comparten cabecera, receptor,
    detalle y totales. Los campos propios de cada tipo van como columnas
    opcionales, documentadas abajo — separar en cinco tablas casi idénticas
    obligaría a duplicar el listado, el cálculo y la emisión.

    La guía de remisión sí tiene tabla propia: no lleva importes.
    """

    __tablename__ = "comprobantes"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), default="Factura")
    # La clave de acceso es única en todo el SRI: es la mejor llave natural.
    clave_acceso: Mapped[str | None] = mapped_column(String(49), unique=True, index=True)
    numero: Mapped[str] = mapped_column(String(20), index=True)
    establecimiento: Mapped[str] = mapped_column(String(3))
    punto_emision: Mapped[str] = mapped_column(String(3))
    secuencial: Mapped[int] = mapped_column(Integer)
    fecha_emision: Mapped[date] = mapped_column(Date)

    receptor_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")
    receptor_identificacion: Mapped[str] = mapped_column(String(20), default="")

    total_sin_impuestos: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    total_descuento: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    total_iva: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    importe_total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    metodo: Mapped[str] = mapped_column(String(20), default="Contado")
    forma_pago: Mapped[str] = mapped_column(String(2), default="01")
    estado_sri: Mapped[str] = mapped_column(String(30), default="Borrador")
    estado_pago: Mapped[str] = mapped_column(String(30), default="Por Cobrar")
    numero_autorizacion: Mapped[str | None] = mapped_column(String(100), default=None)
    fecha_autorizacion: Mapped[str | None] = mapped_column(String(50), default=None)
    mensajes_sri: Mapped[str | None] = mapped_column(Text, default=None)
    xml_firmado: Mapped[str | None] = mapped_column(Text, default=None)

    # --- Solo cotizaciones ---
    validez_dias: Mapped[int | None] = mapped_column(Integer, default=None)

    # --- Solo notas de crédito y débito ---
    # El SRI rechaza la nota si falta cualquiera de estos tres.
    cod_doc_modificado: Mapped[str | None] = mapped_column(String(2), default=None)
    num_doc_modificado: Mapped[str | None] = mapped_column(String(20), default=None)
    fecha_doc_modificado: Mapped[date | None] = mapped_column(Date, default=None)
    motivo: Mapped[str | None] = mapped_column(String(300), default=None)

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    detalles: Mapped[list[DetalleComprobante]] = relationship(
        back_populates="comprobante", cascade="all, delete-orphan"
    )
    receptor: Mapped[Receptor | None] = relationship()


class DetalleComprobante(Base):
    __tablename__ = "detalles_comprobante"

    id: Mapped[int] = mapped_column(primary_key=True)
    comprobante_id: Mapped[int] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE")
    )
    codigo_principal: Mapped[str] = mapped_column(String(50))
    codigo_auxiliar: Mapped[str | None] = mapped_column(String(50), default=None)
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("1"))
    precio_unitario: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    descuento: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    codigo_iva: Mapped[str] = mapped_column(String(2), default="4")
    base_imponible: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    valor_iva: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    comprobante: Mapped[Comprobante] = relationship(back_populates="detalles")


class GuiaRemision(Base):
    """
    Guía de remisión: sustenta el traslado físico de mercadería.

    Tabla propia porque no lleva importes ni impuestos — solo qué se mueve,
    de dónde a dónde y quién lo transporta.
    """

    __tablename__ = "guias_remision"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave_acceso: Mapped[str | None] = mapped_column(String(49), unique=True, index=True)
    numero: Mapped[str] = mapped_column(String(20), index=True)
    establecimiento: Mapped[str] = mapped_column(String(3))
    punto_emision: Mapped[str] = mapped_column(String(3))
    secuencial: Mapped[int] = mapped_column(Integer)

    fecha_inicio: Mapped[date] = mapped_column(Date)
    fecha_fin: Mapped[date | None] = mapped_column(Date, default=None)
    motivo_traslado: Mapped[str] = mapped_column(String(300))
    ruta: Mapped[str | None] = mapped_column(String(300), default=None)
    tipo_transporte: Mapped[str] = mapped_column(String(20), default="Privado")
    documento_aduanero: Mapped[str | None] = mapped_column(String(50), default=None)

    transportista_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    transportista_razon_social: Mapped[str] = mapped_column(String(300), default="")
    transportista_identificacion: Mapped[str] = mapped_column(String(20), default="")
    placa: Mapped[str] = mapped_column(String(20), default="")

    provincia_partida: Mapped[str | None] = mapped_column(String(100), default=None)
    canton_partida: Mapped[str | None] = mapped_column(String(100), default=None)
    direccion_partida: Mapped[str] = mapped_column(String(300), default="")
    provincia_llegada: Mapped[str | None] = mapped_column(String(100), default=None)
    canton_llegada: Mapped[str | None] = mapped_column(String(100), default=None)
    direccion_llegada: Mapped[str] = mapped_column(String(300), default="")

    estado_sri: Mapped[str] = mapped_column(String(30), default="Borrador")
    numero_autorizacion: Mapped[str | None] = mapped_column(String(100), default=None)
    fecha_autorizacion: Mapped[str | None] = mapped_column(String(50), default=None)
    # Se guarda el XML firmado antes de transmitir: si la red falla, el
    # reintento no vuelve a firmar. Los mensajes son lo único que explica
    # un rechazo.
    xml_firmado: Mapped[str | None] = mapped_column(Text, default=None)
    mensajes_sri: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    items: Mapped[list[ItemGuiaRemision]] = relationship(
        back_populates="guia", cascade="all, delete-orphan"
    )
    transportista: Mapped[Receptor | None] = relationship()


class ItemGuiaRemision(Base):
    __tablename__ = "items_guia_remision"

    id: Mapped[int] = mapped_column(primary_key=True)
    guia_id: Mapped[int] = mapped_column(ForeignKey("guias_remision.id", ondelete="CASCADE"))
    codigo: Mapped[str] = mapped_column(String(50), default="")
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("1"))

    guia: Mapped[GuiaRemision] = relationship(back_populates="items")


class Retencion(Base):
    """
    Comprobante de retención.

    Tabla propia, y no un `Comprobante` más, porque su estructura no se parece:
    no hay líneas de producto ni IVA que cobrar, sino porcentajes retenidos al
    proveedor sobre el documento que sustenta el pago. Meterlo en la tabla de
    comprobantes obligaría a dejar en blanco casi todas sus columnas.
    """

    __tablename__ = "retenciones"

    id: Mapped[int] = mapped_column(primary_key=True)
    clave_acceso: Mapped[str | None] = mapped_column(String(49), unique=True, index=True)
    numero: Mapped[str] = mapped_column(String(20), index=True)
    establecimiento: Mapped[str] = mapped_column(String(3))
    punto_emision: Mapped[str] = mapped_column(String(3))
    secuencial: Mapped[int] = mapped_column(Integer)

    fecha_emision: Mapped[date] = mapped_column(Date)
    # Formato MM/AAAA: el SRI lo exige así, no como fecha.
    periodo_fiscal: Mapped[str] = mapped_column(String(7))

    # Sujeto retenido: normalmente el proveedor a quien se le paga.
    sujeto_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    sujeto_razon_social: Mapped[str] = mapped_column(String(300), default="")
    sujeto_identificacion: Mapped[str] = mapped_column(String(20), default="")
    sujeto_tipo_identificacion: Mapped[str] = mapped_column(String(30), default="RUC")

    # Documento sustento, común a todas las líneas en la versión 1.0.0 del XML.
    cod_doc_sustento: Mapped[str] = mapped_column(String(2), default="01")
    num_doc_sustento: Mapped[str] = mapped_column(String(20), default="")
    fecha_doc_sustento: Mapped[date | None] = mapped_column(Date, default=None)

    total_retenido: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    estado_sri: Mapped[str] = mapped_column(String(30), default="Borrador")
    numero_autorizacion: Mapped[str | None] = mapped_column(String(100), default=None)
    fecha_autorizacion: Mapped[str | None] = mapped_column(String(50), default=None)
    xml_firmado: Mapped[str | None] = mapped_column(Text, default=None)
    mensajes_sri: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    detalles: Mapped[list[DetalleRetencion]] = relationship(
        back_populates="retencion", cascade="all, delete-orphan"
    )
    sujeto: Mapped[Receptor | None] = relationship()


class DetalleRetencion(Base):
    """Una línea: impuesto, concepto, base y porcentaje."""

    __tablename__ = "detalles_retencion"

    id: Mapped[int] = mapped_column(primary_key=True)
    retencion_id: Mapped[int] = mapped_column(ForeignKey("retenciones.id", ondelete="CASCADE"))
    codigo_impuesto: Mapped[str] = mapped_column(String(2))
    codigo_retencion: Mapped[str] = mapped_column(String(10))
    base_imponible: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    porcentaje_retener: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    valor_retenido: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    retencion: Mapped[Retencion] = relationship(back_populates="detalles")


# --------------------------------------------------------------------------
# Egresos: gastos y pagos
#
# El SRI no pide estos documentos —no son comprobantes electrónicos— pero sin
# ellos no se sabe cuánto se gastó, y el formulario 104 declara también las
# compras. Por eso viven aquí y no en una hoja de cálculo aparte.
# --------------------------------------------------------------------------


class TipoGasto(Base):
    """
    Categoría de gasto: arriendo, servicios básicos, sueldos, suministros…

    Es una tabla y no una lista fija porque cada negocio agrupa sus gastos a su
    manera, y el reporte solo sirve si las categorías son las suyas.
    """

    __tablename__ = "tipos_gasto"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    descripcion: Mapped[str | None] = mapped_column(String(300), default=None)
    # Deducible del impuesto a la renta. Lo decide el contador, no el sistema.
    deducible: Mapped[bool] = mapped_column(Boolean, default=True)
    estado: Mapped[str] = mapped_column(String(20), default="Activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    gastos: Mapped[list["Gasto"]] = relationship(back_populates="tipo")


class Gasto(Base):
    """
    Un gasto registrado, con el documento que lo sustenta.

    El `documento` es la factura que dio el proveedor: sin él el gasto no se
    puede deducir, así que se pide aunque el formulario lo deje pasar vacío.
    """

    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    concepto: Mapped[str] = mapped_column(String(300))

    tipo_id: Mapped[int | None] = mapped_column(
        ForeignKey("tipos_gasto.id", ondelete="SET NULL"), default=None
    )
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    proveedor_razon_social: Mapped[str] = mapped_column(String(300), default="")
    proveedor_identificacion: Mapped[str] = mapped_column(String(20), default="")

    # Documento sustento emitido por el proveedor.
    documento: Mapped[str] = mapped_column(String(30), default="")
    fecha_documento: Mapped[date | None] = mapped_column(Date, default=None)
    # Clave de acceso del comprobante del proveedor, autorizada por el SRI a
    # su nombre. Es dato del ATS y del formulario 104: sin ella el gasto no se
    # puede sustentar como crédito tributario ante el SRI.
    autorizacion_proveedor: Mapped[str | None] = mapped_column(String(60), default=None)

    subtotal: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    iva: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    # Código de tarifa (tabla 17 del SRI): 4=15%, 5=5%, 0=0%, 6=No objeto,
    # 7=Exento. Sin esto el `iva` es un monto sin tarifa, y el formulario 104
    # separa el crédito tributario por tarifa, no en un solo total.
    codigo_iva: Mapped[str] = mapped_column(String(2), default="4")

    estado_pago: Mapped[str] = mapped_column(String(20), default="Por Pagar")
    observacion: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    tipo: Mapped["TipoGasto | None"] = relationship(back_populates="gastos")
    proveedor: Mapped["Receptor | None"] = relationship()


class Egreso(Base):
    """
    Salida de dinero: el pago en sí, no el gasto que lo motivó.

    Se separa del gasto porque no coinciden: un gasto puede pagarse en varios
    egresos, y un egreso puede saldar varios gastos. Mezclarlos haría imposible
    cuadrar la caja.
    """

    __tablename__ = "egresos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    concepto: Mapped[str] = mapped_column(String(300))
    beneficiario: Mapped[str] = mapped_column(String(300), default="")

    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    forma_pago: Mapped[str] = mapped_column(String(30), default="Efectivo")
    cuenta_id: Mapped[int | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id", ondelete="SET NULL"), default=None
    )
    referencia: Mapped[str | None] = mapped_column(String(60), default=None)

    gasto_id: Mapped[int | None] = mapped_column(
        ForeignKey("gastos.id", ondelete="SET NULL"), default=None
    )

    estado: Mapped[str] = mapped_column(String(20), default="Registrado")
    observacion: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    cuenta: Mapped["CuentaBancaria | None"] = relationship()
    gasto: Mapped["Gasto | None"] = relationship()


class Anticipo(Base):
    """
    Dinero movido antes de que exista la factura.

    `saldo` no se guarda: se calcula como `monto - facturado`. Guardarlo sería
    un tercer número que puede dejar de cuadrar con los otros dos.
    """

    __tablename__ = "anticipos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)
    # ARD: anticipo recibido de un cliente. APP: anticipo pagado a un proveedor.
    tipo: Mapped[str] = mapped_column(String(3), default="ARD")

    receptor_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")

    detalle: Mapped[str] = mapped_column(String(300), default="")
    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    facturado: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))

    forma_pago: Mapped[str] = mapped_column(String(30), default="Transferencia")
    estado: Mapped[str] = mapped_column(String(20), default="Pendiente")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    receptor: Mapped["Receptor | None"] = relationship()

    @property
    def saldo(self) -> Decimal:
        return self.monto - self.facturado


class DevolucionAnticipo(Base):
    """
    Devolución del saldo sobrante de un anticipo.

    Cuando un anticipo se devuelve, el saldo (`monto - facturado`) sale de caja.
    Se guarda como registro propio —y no como un ajuste del anticipo— para que
    el movimiento de dinero quede explicado por separado, igual que un egreso se
    separa del gasto. El servidor calcula el monto; no se genera asiento
    contable porque este sistema no lleva libro.
    """

    __tablename__ = "devoluciones_anticipo"

    id: Mapped[int] = mapped_column(primary_key=True)
    anticipo_id: Mapped[int] = mapped_column(
        ForeignKey("anticipos.id", ondelete="CASCADE"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date, index=True)
    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    forma_pago: Mapped[str] = mapped_column(String(30), default="Transferencia")
    observacion: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    anticipo: Mapped["Anticipo"] = relationship()


class PlantillaRecurrente(Base):
    """
    Factura que se repite: arriendos, suscripciones, iguala mensual.

    Guarda la plantilla, no las facturas. Cada emisión crea un `Comprobante`
    normal, porque una factura recurrente autorizada es una factura como
    cualquier otra ante el SRI: mismo XML, misma numeración, misma firma.
    """

    __tablename__ = "plantillas_recurrentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(200))

    receptor_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")

    # Mensual, Quincenal, Semanal o Anual.
    periodicidad: Mapped[str] = mapped_column(String(20), default="Mensual")
    proxima_emision: Mapped[date] = mapped_column(Date, index=True)
    ultima_emision: Mapped[date | None] = mapped_column(Date, default=None)
    # Sin fecha de fin la plantilla es indefinida.
    hasta: Mapped[date | None] = mapped_column(Date, default=None)

    establecimiento: Mapped[str] = mapped_column(String(3), default="001")
    punto_emision: Mapped[str] = mapped_column(String(3), default="001")
    forma_pago: Mapped[str] = mapped_column(String(2), default="01")

    total: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    emitidas: Mapped[int] = mapped_column(Integer, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    receptor: Mapped["Receptor | None"] = relationship()
    lineas: Mapped[list["LineaRecurrente"]] = relationship(
        back_populates="plantilla", cascade="all, delete-orphan"
    )


class LineaRecurrente(Base):
    """Una línea de la plantilla; se copia tal cual al emitir."""

    __tablename__ = "lineas_recurrentes"

    id: Mapped[int] = mapped_column(primary_key=True)
    plantilla_id: Mapped[int] = mapped_column(
        ForeignKey("plantillas_recurrentes.id", ondelete="CASCADE")
    )
    codigo_principal: Mapped[str] = mapped_column(String(50), default="SIN-COD")
    descripcion: Mapped[str] = mapped_column(String(300))
    cantidad: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("1"))
    precio_unitario: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    descuento_porcentaje: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    codigo_iva: Mapped[str] = mapped_column(String(2), default="4")

    plantilla: Mapped["PlantillaRecurrente"] = relationship(back_populates="lineas")


# --------------------------------------------------------------------------
# Cuentas pendientes: cuotas y recibos
#
# El SRI no sabe nada de esto —una factura a crédito está igual de autorizada
# que una al contado— pero el negocio necesita saber cuándo vence cada parte y
# quién ya pagó.
# --------------------------------------------------------------------------


class Cuota(Base):
    """
    Una parte de un comprobante, con su fecha de vencimiento.

    Un comprobante al contado no tiene cuotas; uno a crédito tiene una por
    cada vencimiento pactado. La suma de las cuotas debe cuadrar con el
    importe del comprobante, y el router lo comprueba al generarlas.
    """

    __tablename__ = "cuotas"

    id: Mapped[int] = mapped_column(primary_key=True)
    comprobante_id: Mapped[int] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="CASCADE"), index=True
    )
    numero: Mapped[int] = mapped_column(Integer, default=1)
    vence: Mapped[date] = mapped_column(Date, index=True)
    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    # Lo cobrado hasta ahora. El saldo se calcula, no se guarda.
    cobrado: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    comprobante: Mapped["Comprobante"] = relationship()
    recibos: Mapped[list["Recibo"]] = relationship(back_populates="cuota")

    @property
    def saldo(self) -> Decimal:
        return self.monto - self.cobrado

    @property
    def estado(self) -> str:
        if self.cobrado >= self.monto:
            return "Cobrada"
        if self.cobrado > 0:
            return "Parcial"
        return "Pendiente"


class Recibo(Base):
    """
    Un cobro recibido.

    Se separa de la cuota por lo mismo que el egreso se separa del gasto: un
    cliente puede abonar de a poco, y cada abono es un movimiento de caja que
    hay que poder explicar por separado.
    """

    __tablename__ = "recibos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), index=True)
    fecha: Mapped[date] = mapped_column(Date, index=True)

    cuota_id: Mapped[int | None] = mapped_column(
        ForeignKey("cuotas.id", ondelete="SET NULL"), default=None
    )
    comprobante_id: Mapped[int | None] = mapped_column(
        ForeignKey("comprobantes.id", ondelete="SET NULL"), default=None
    )
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")

    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    forma_pago: Mapped[str] = mapped_column(String(30), default="Efectivo")
    cuenta_id: Mapped[int | None] = mapped_column(
        ForeignKey("cuentas_bancarias.id", ondelete="SET NULL"), default=None
    )
    referencia: Mapped[str | None] = mapped_column(String(60), default=None)

    estado: Mapped[str] = mapped_column(String(20), default="Registrado")
    observacion: Mapped[str | None] = mapped_column(Text, default=None)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    cuota: Mapped["Cuota | None"] = relationship(back_populates="recibos")
    comprobante: Mapped["Comprobante | None"] = relationship()
    cuenta: Mapped["CuentaBancaria | None"] = relationship()


class SaldoInicial(Base):
    """
    Saldo anterior cargado a mano: deuda que ya existía antes de usar Factoa.

    No sale de ningún comprobante ni cuota del sistema; es un arrastre que el
    usuario registra para que las cuentas por cobrar/pagar reflejen también lo
    que se debía de antes. Por eso vive en su propia tabla y **no** entra en el
    cálculo de saldos vivos (`servicios/reportes_cuentas.py`): sumarlos allí
    arriesgaría un doble conteo. La pantalla los combina solo en el frontend.
    """

    __tablename__ = "saldos_iniciales"

    id: Mapped[int] = mapped_column(primary_key=True)
    receptor_id: Mapped[int | None] = mapped_column(
        ForeignKey("receptores.id", ondelete="SET NULL"), default=None
    )
    # Se copia el nombre y la identificación: si el receptor se desactiva o el
    # saldo se cargó a nombre libre, el histórico sigue diciendo de quién era.
    receptor_razon_social: Mapped[str] = mapped_column(String(300), default="")
    identificacion: Mapped[str] = mapped_column(String(20), default="")
    # cobrar: nos lo deben. pagar: lo debemos.
    tipo: Mapped[str] = mapped_column(String(10), default="cobrar")
    monto: Mapped[Decimal] = mapped_column(DINERO, default=Decimal("0"))
    fecha: Mapped[date] = mapped_column(Date, index=True)
    detalle: Mapped[str] = mapped_column(String(300), default="")
    documento: Mapped[str] = mapped_column(String(50), default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)

    receptor: Mapped["Receptor | None"] = relationship()


class ListaAuxiliar(Base):
    """
    Listas que el negocio define a su gusto: zonas, vendedores, leyendas.

    Una sola tabla con un campo `tipo` en vez de tres tablas casi idénticas:
    las tres son lo mismo —un nombre, a veces un detalle y un estado— y
    separarlas obligaría a triplicar el CRUD para no ganar nada.

    No son catálogos del SRI. Los del SRI (tarifas de IVA, tipos de
    identificación, códigos de retención) viven en `app/sri/` porque los fija
    la ficha técnica y el usuario no puede inventárselos.
    """

    __tablename__ = "listas_auxiliares"
    __table_args__ = (UniqueConstraint("tipo", "nombre", name="uq_lista_tipo_nombre"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # zona · vendedor · leyenda
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    nombre: Mapped[str] = mapped_column(String(200))
    detalle: Mapped[str | None] = mapped_column(String(300), default=None)
    estado: Mapped[str] = mapped_column(String(20), default="Activo")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=ahora)
