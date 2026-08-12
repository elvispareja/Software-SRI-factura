"""
Reportes de cuentas pendientes: los cinco que promete la pestaña «Reportes».

QUÉ ALIMENTA CADA MODO (la decisión de fondo de este módulo)
------------------------------------------------------------
La pantalla tiene un interruptor Cobrar/Pagar que hasta ahora solo cambiaba
rótulos: en modo Pagar seguía enseñando las cuotas y los recibos de las ventas
bajo la etiqueta «Proveedor». Eso no es un detalle cosmético, es un dato falso.
Aquí cada modo lee tablas distintas:

**Cobrar** — dinero que ENTRA. La deuda es el `Comprobante` de venta
(`Factura`, `Nota de Venta`, `Nota de Débito`) y el abono es el `Recibo`, que el
propio modelo define como «un cobro recibido».

**Pagar** — dinero que SALE. Tiene dos orígenes, y hacen falta los dos:

1. `Gasto` (la factura que dio el proveedor) saldado con `Egreso` (el pago).
   Es la vía normal de una compra: el SRI no recibe estos documentos, así que
   no tienen `estado_sri` y cuentan todos.
2. `Comprobante` de tipo `Liquidación de Compra`. Es un comprobante
   electrónico, pero de COMPRA: lo emite el comprador por el proveedor que no
   puede facturar, y deja una deuda con ese proveedor. Sus abonos van por
   `Cuota`/`Recibo` porque es lo único que el módulo de cuentas sabe crear
   contra un comprobante; ignorarlos dejaría la liquidación pendiente para
   siempre.

Por eso `Nota de Crédito` no aparece en ninguno de los dos: no es una deuda,
es la anulación de otra. Y la `Cotización` tampoco: no obliga a nadie.

REGLAS QUE GOBIERNAN TODO EL MÓDULO
-----------------------------------
* **Solo comprobantes `Autorizado`.** Un borrador no es una venta y un rechazado
  no llegó a serlo. Los gastos no pasan por el SRI y no tienen este filtro.
* **El saldo no se guarda: se calcula.** `total - abonado`, siempre.
* **La doble fuente del abono.** `crear_recibo` rellena `Recibo.comprobante_id`
  también cuando hay cuota, así que sumar `Cuota.cobrado` MÁS todos los recibos
  del comprobante cuenta el mismo dinero dos veces. Lo cobrado de un comprobante
  es `Cuota.cobrado` + los recibos **sin cuota** y no anulados (la misma regla
  que aplica `_recalcular_comprobante`).
* **Los saldos históricos no salen de `Cuota.cobrado`.** Ese campo es un
  acumulado a hoy y no sabe cuándo entró el dinero. Para la rotación, el saldo a
  una fecha se reconstruye con la fecha de los `Recibo`/`Egreso`, que sí la
  tienen. Ahí no hace falta descartar nada: se suman los recibos del
  comprobante, con cuota o sin ella, y cada uno cuenta una sola vez.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..modelos_db import Comprobante, Cuota, Egreso, Gasto, Recibo, Receptor
from ..sri.modelos import redondear

COBRAR = "cobrar"
PAGAR = "pagar"
MODOS = (COBRAR, PAGAR)

# Documentos de venta: generan derecho de cobro.
TIPOS_POR_COBRAR = ("Factura", "Nota de Venta", "Nota de Débito")
# Documento de compra que sí es comprobante electrónico.
TIPO_POR_PAGAR = "Liquidación de Compra"

ESTADO_DECLARABLE = "Autorizado"
ANULADO = "Anulado"

# El SRI factura en dólares y el sistema no maneja otra divisa. La columna
# existe porque el reporte la promete y porque el día que haya otra moneda el
# hueco ya está abierto; hoy es constante a propósito.
MONEDA = "USD"

CERO = Decimal("0")

# El SRI guarda comprobantes electrónicos desde 2012; antes no hay nada que ver.
ANIO_MINIMO = 2012


# --------------------------------------------------------------------------
# Período
#
# Ayudante propio y privado: `servicios/reportes.py` tiene el suyo, pero este
# módulo no debe quedar atado a los cambios de aquel — sus períodos son
# tributarios (mes o año fiscal) y los de aquí son de gestión de cobranza.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Periodo:
    """Rango de fechas cerrado por ambos extremos."""

    desde: date
    hasta: date

    @classmethod
    def del_mes(cls, anio: int, mes: int) -> Periodo:
        return cls(desde=date(anio, mes, 1), hasta=date(anio, mes, monthrange(anio, mes)[1]))

    @classmethod
    def del_anio(cls, anio: int) -> Periodo:
        return cls(desde=date(anio, 1, 1), hasta=date(anio, 12, 31))

    @property
    def dias(self) -> int:
        """Ambos extremos incluidos: enero tiene 31 días, no 30."""
        return (self.hasta - self.desde).days + 1

    def etiqueta(self) -> str:
        return f"{self.desde:%Y-%m-%d}-a-{self.hasta:%Y-%m-%d}"


def resolver_periodo(anio: int | None, mes: int | None, hoy: date | None = None) -> Periodo:
    """
    Resuelve el período pedido; sin argumentos, el año en curso.

    Devuelve `ValueError` en vez de `HTTPException` para no atar el servicio a
    FastAPI: quien llame decide qué código HTTP merece un año imposible.
    """
    hoy = hoy or date.today()
    anio = anio or hoy.year
    if anio < ANIO_MINIMO or anio > hoy.year + 1:
        raise ValueError(f"El año {anio} está fuera de rango.")
    if mes is None:
        return Periodo.del_anio(anio)
    if not 1 <= mes <= 12:
        raise ValueError(f"El mes {mes} no existe.")
    return Periodo.del_mes(anio, mes)


def validar_modo(modo: str) -> str:
    if modo not in MODOS:
        raise ValueError("El modo debe ser 'cobrar' o 'pagar'.")
    return modo


def etiqueta_contacto(modo: str) -> str:
    """Cómo se llama la otra parte en cada modo. La interfaz ya rotula así."""
    return "Cliente" if modo == COBRAR else "Proveedor"


def _decimal(valor) -> Decimal:
    """
    Normaliza lo que devuelve SQL.

    SQLite suma en float aunque la columna sea `Numeric`, así que el resultado
    llega como `float` —o como `None` si no hubo filas— y hay que devolverlo a
    `Decimal` antes de que contamine ninguna otra suma.
    """
    if valor is None:
        return CERO
    return redondear(Decimal(str(valor)))


def _estado_saldo(total: Decimal, abonado: Decimal) -> str:
    """Nombre neutro: sirve para lo que se cobra y para lo que se paga."""
    if abonado <= 0:
        return "Pendiente"
    if abonado >= total:
        return "Saldado"
    return "Parcial"


# --------------------------------------------------------------------------
# El documento pendiente, común a los dos modos
# --------------------------------------------------------------------------


@dataclass
class _Documento:
    """
    Una deuda, venga de donde venga.

    Los cinco reportes hablan de «documento» sin distinguir si detrás hay un
    comprobante electrónico o un gasto de caja; esta forma común es lo que
    permite que el modo Pagar lea otras tablas sin duplicar los cinco cálculos.
    """

    origen: str  # "Comprobante" o "Gasto"
    id: int
    tipo: str
    numero: str
    fecha: date
    receptor_id: int | None
    contacto: str
    identificacion: str
    correo: str
    telefono: str
    total: Decimal

    @property
    def clave(self) -> tuple[str, int]:
        return (self.origen, self.id)

    @property
    def clave_contacto(self) -> tuple[str, str]:
        """
        Agrupa por receptor.

        Por `receptor_id` cuando lo hay; si el documento se emitió con el
        nombre escrito a mano, por ese nombre. Mezclar ambos en una sola clave
        partiría en dos al mismo cliente.
        """
        if self.receptor_id is not None:
            return ("id", str(self.receptor_id))
        return ("nombre", self.contacto.strip().upper())


def _texto(valor: str | None) -> str:
    return valor or ""


def _documentos(sesion: Session, modo: str, periodo: Periodo | None = None) -> list[_Documento]:
    """Los documentos que deben dinero (o lo debieron) en el modo pedido."""
    documentos: list[_Documento] = []

    tipos = TIPOS_POR_COBRAR if modo == COBRAR else (TIPO_POR_PAGAR,)
    consulta = (
        select(Comprobante, Receptor)
        .join(Receptor, Comprobante.receptor_id == Receptor.id, isouter=True)
        .where(
            Comprobante.tipo.in_(tipos),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
        )
    )
    if periodo is not None:
        consulta = consulta.where(
            Comprobante.fecha_emision.between(periodo.desde, periodo.hasta)
        )

    for comprobante, receptor in sesion.execute(consulta):
        documentos.append(
            _Documento(
                origen="Comprobante",
                id=comprobante.id,
                tipo=comprobante.tipo,
                numero=comprobante.numero,
                fecha=comprobante.fecha_emision,
                receptor_id=comprobante.receptor_id,
                contacto=comprobante.receptor_razon_social,
                identificacion=comprobante.receptor_identificacion,
                correo=_texto(receptor.correo if receptor else None),
                telefono=_texto(receptor.telefono1 if receptor else None),
                total=redondear(comprobante.importe_total),
            )
        )

    if modo == PAGAR:
        consulta_gastos = select(Gasto, Receptor).join(
            Receptor, Gasto.proveedor_id == Receptor.id, isouter=True
        )
        if periodo is not None:
            consulta_gastos = consulta_gastos.where(
                Gasto.fecha.between(periodo.desde, periodo.hasta)
            )

        for gasto, proveedor in sesion.execute(consulta_gastos):
            documentos.append(
                _Documento(
                    origen="Gasto",
                    id=gasto.id,
                    tipo="Gasto",
                    # El número es el del documento que dio el proveedor. Si no
                    # se registró, se etiqueta con el id para que la fila siga
                    # siendo identificable en el CSV.
                    numero=gasto.documento or f"GASTO-{gasto.id:06d}",
                    fecha=gasto.fecha,
                    receptor_id=gasto.proveedor_id,
                    contacto=gasto.proveedor_razon_social,
                    identificacion=gasto.proveedor_identificacion,
                    correo=_texto(proveedor.correo if proveedor else None),
                    telefono=_texto(proveedor.telefono1 if proveedor else None),
                    total=redondear(gasto.total),
                )
            )

    documentos.sort(key=lambda documento: (documento.fecha, documento.numero))
    return documentos


def _abonado_actual(sesion: Session, modo: str) -> dict[tuple[str, int], Decimal]:
    """
    Lo abonado a cada documento **a día de hoy**.

    Aquí vive la trampa del doble conteo. `crear_recibo` rellena siempre
    `Recibo.comprobante_id`, también cuando el recibo va contra una cuota; si se
    sumara `Cuota.cobrado` y además todos los recibos del comprobante, cada
    abono con cuota contaría dos veces. La suma correcta es
    `Cuota.cobrado` + los recibos **sin cuota** y no anulados.
    """
    abonos: dict[tuple[str, int], Decimal] = {}

    for comprobante_id, suma in sesion.execute(
        select(Cuota.comprobante_id, func.sum(Cuota.cobrado)).group_by(Cuota.comprobante_id)
    ):
        abonos[("Comprobante", comprobante_id)] = _decimal(suma)

    for comprobante_id, suma in sesion.execute(
        select(Recibo.comprobante_id, func.sum(Recibo.monto))
        .where(
            Recibo.comprobante_id.is_not(None),
            Recibo.cuota_id.is_(None),
            Recibo.estado != ANULADO,
        )
        .group_by(Recibo.comprobante_id)
    ):
        clave = ("Comprobante", comprobante_id)
        abonos[clave] = redondear(abonos.get(clave, CERO) + _decimal(suma))

    if modo == PAGAR:
        for gasto_id, suma in sesion.execute(
            select(Egreso.gasto_id, func.sum(Egreso.monto))
            .where(Egreso.gasto_id.is_not(None), Egreso.estado != ANULADO)
            .group_by(Egreso.gasto_id)
        ):
            abonos[("Gasto", gasto_id)] = _decimal(suma)

    return abonos


# --------------------------------------------------------------------------
# Los pagos, comunes a los dos modos
# --------------------------------------------------------------------------


@dataclass
class _Pago:
    """Un movimiento de caja aplicado a un documento: recibo o egreso."""

    origen: str  # "Recibo" o "Egreso"
    id: int
    numero: str
    fecha: date
    contacto: str
    documento_clave: tuple[str, int] | None
    documento: str
    cuota_id: int | None
    monto: Decimal
    forma_pago: str
    estado: str
    referencia: str


def _pagos(
    sesion: Session,
    modo: str,
    desde: date | None = None,
    hasta: date | None = None,
    incluir_anulados: bool = True,
) -> list[_Pago]:
    """
    Los cobros (modo cobrar) o los pagos (modo pagar) del rango pedido.

    Los anulados se devuelven por defecto porque el reporte de recibos promete
    «estado del recibo»: esconderlos sería tapar justo el movimiento que hay que
    explicar. Quien suma dinero los descarta él mismo.
    """
    pagos: list[_Pago] = []

    if modo == COBRAR:
        consulta = (
            select(Recibo, Comprobante)
            .join(Comprobante, Recibo.comprobante_id == Comprobante.id, isouter=True)
            # Un recibo suelto (sin comprobante) sigue siendo dinero que entró;
            # el que va contra una Liquidación de Compra no, que ese es un pago.
            .where(
                (Comprobante.id.is_(None)) | (Comprobante.tipo.in_(TIPOS_POR_COBRAR))
            )
        )
        if desde:
            consulta = consulta.where(Recibo.fecha >= desde)
        if hasta:
            consulta = consulta.where(Recibo.fecha <= hasta)
        if not incluir_anulados:
            consulta = consulta.where(Recibo.estado != ANULADO)

        for recibo, comprobante in sesion.execute(consulta):
            pagos.append(
                _Pago(
                    origen="Recibo",
                    id=recibo.id,
                    numero=recibo.numero,
                    fecha=recibo.fecha,
                    contacto=recibo.receptor_razon_social,
                    documento_clave=(
                        ("Comprobante", comprobante.id) if comprobante else None
                    ),
                    documento=comprobante.numero if comprobante else "",
                    cuota_id=recibo.cuota_id,
                    monto=redondear(recibo.monto),
                    forma_pago=recibo.forma_pago,
                    estado=recibo.estado,
                    referencia=_texto(recibo.referencia),
                )
            )
        pagos.sort(key=lambda pago: (pago.fecha, pago.id))
        return pagos

    # Modo pagar: el egreso es el pago propiamente dicho…
    consulta_egresos = select(Egreso, Gasto).join(
        Gasto, Egreso.gasto_id == Gasto.id, isouter=True
    )
    if desde:
        consulta_egresos = consulta_egresos.where(Egreso.fecha >= desde)
    if hasta:
        consulta_egresos = consulta_egresos.where(Egreso.fecha <= hasta)
    if not incluir_anulados:
        consulta_egresos = consulta_egresos.where(Egreso.estado != ANULADO)

    for egreso, gasto in sesion.execute(consulta_egresos):
        pagos.append(
            _Pago(
                origen="Egreso",
                id=egreso.id,
                # Los egresos no llevan numeración propia —no son comprobantes
                # electrónicos— así que se etiquetan con su id, que es estable.
                numero=f"EGR-{egreso.id:06d}",
                fecha=egreso.fecha,
                contacto=egreso.beneficiario or (gasto.proveedor_razon_social if gasto else ""),
                documento_clave=("Gasto", gasto.id) if gasto else None,
                documento=(gasto.documento or f"GASTO-{gasto.id:06d}") if gasto else "",
                cuota_id=None,
                monto=redondear(egreso.monto),
                forma_pago=egreso.forma_pago,
                estado=egreso.estado,
                referencia=_texto(egreso.referencia),
            )
        )

    # …y el recibo contra una Liquidación de Compra también saca dinero: es el
    # único modo que tiene el módulo de cuentas de abonar un comprobante.
    consulta_recibos = select(Recibo, Comprobante).join(
        Comprobante, Recibo.comprobante_id == Comprobante.id
    ).where(Comprobante.tipo == TIPO_POR_PAGAR)
    if desde:
        consulta_recibos = consulta_recibos.where(Recibo.fecha >= desde)
    if hasta:
        consulta_recibos = consulta_recibos.where(Recibo.fecha <= hasta)
    if not incluir_anulados:
        consulta_recibos = consulta_recibos.where(Recibo.estado != ANULADO)

    for recibo, comprobante in sesion.execute(consulta_recibos):
        pagos.append(
            _Pago(
                origen="Recibo",
                id=recibo.id,
                numero=recibo.numero,
                fecha=recibo.fecha,
                contacto=recibo.receptor_razon_social,
                documento_clave=("Comprobante", comprobante.id),
                documento=comprobante.numero,
                cuota_id=recibo.cuota_id,
                monto=redondear(recibo.monto),
                forma_pago=recibo.forma_pago,
                estado=recibo.estado,
                referencia=_texto(recibo.referencia),
            )
        )

    pagos.sort(key=lambda pago: (pago.fecha, pago.origen, pago.id))
    return pagos


# --------------------------------------------------------------------------
# Las cuotas, comunes a los dos modos
# --------------------------------------------------------------------------


@dataclass
class _CuotaFila:
    """
    Una cuota de la agenda.

    Un documento sin plan de cuotas entra igual, como cuota única que vence el
    día de su emisión: se debe entero desde el primer día. Si se dejara fuera,
    la agenda del modo Pagar saldría siempre vacía —un gasto nunca tiene
    cuotas— y la pantalla seguiría mintiendo, que es justo lo que se corrige.
    """

    documento: _Documento
    cuota_id: int | None
    numero: int
    vence: date
    monto: Decimal
    abonado: Decimal

    @property
    def saldo(self) -> Decimal:
        return redondear(self.monto - self.abonado)

    @property
    def estado(self) -> str:
        return _estado_saldo(self.monto, self.abonado)

    def dias_mora(self, hoy: date) -> int:
        """Negativo si aún no vence; positivo son días de mora."""
        return (hoy - self.vence).days


def _cuotas(
    sesion: Session,
    documentos: list[_Documento],
    abonos: dict[tuple[str, int], Decimal],
) -> list[_CuotaFila]:
    identificadores = [d.id for d in documentos if d.origen == "Comprobante"]
    por_comprobante: dict[int, list[Cuota]] = {}
    if identificadores:
        for cuota in sesion.scalars(
            select(Cuota).where(Cuota.comprobante_id.in_(identificadores))
        ):
            por_comprobante.setdefault(cuota.comprobante_id, []).append(cuota)

    filas: list[_CuotaFila] = []
    for documento in documentos:
        plan = por_comprobante.get(documento.id, []) if documento.origen == "Comprobante" else []
        if plan:
            for cuota in sorted(plan, key=lambda c: (c.vence, c.numero)):
                filas.append(
                    _CuotaFila(
                        documento=documento,
                        cuota_id=cuota.id,
                        numero=cuota.numero,
                        vence=cuota.vence,
                        monto=redondear(cuota.monto),
                        # `Cuota.cobrado` y nada más: los recibos sueltos del
                        # comprobante no se imputan a ninguna cuota, y sumarlos
                        # aquí sería el doble conteo.
                        abonado=redondear(cuota.cobrado),
                    )
                )
        else:
            filas.append(
                _CuotaFila(
                    documento=documento,
                    cuota_id=None,
                    numero=1,
                    vence=documento.fecha,
                    monto=documento.total,
                    abonado=abonos.get(documento.clave, CERO),
                )
            )

    filas.sort(key=lambda fila: (fila.vence, fila.documento.numero, fila.numero))
    return filas


# --------------------------------------------------------------------------
# 1. Saldo pendiente por documento
# --------------------------------------------------------------------------


def saldos_por_documento(
    sesion: Session,
    modo: str,
    incluir_saldados: bool = False,
    receptor_id: int | None = None,
    hoy: date | None = None,
) -> dict:
    """
    Cada documento con su total original y lo que queda por saldar.

    No se acota por período: una factura de hace tres meses sigue debiéndose
    hoy, y filtrarla escondería justo la deuda más vieja.
    """
    validar_modo(modo)
    hoy = hoy or date.today()

    documentos = _documentos(sesion, modo)
    abonos = _abonado_actual(sesion, modo)
    vencimientos = _proximo_vencimiento(sesion, documentos)

    filas: list[dict] = []
    for documento in documentos:
        if receptor_id is not None and documento.receptor_id != receptor_id:
            continue

        abonado = abonos.get(documento.clave, CERO)
        saldo = redondear(documento.total - abonado)
        if not incluir_saldados and saldo <= 0:
            continue

        vence = vencimientos.get(documento.clave, documento.fecha)
        filas.append(
            {
                "origen": documento.origen,
                "documento_id": documento.id,
                "tipo": documento.tipo,
                "numero": documento.numero,
                "fecha": documento.fecha,
                "contacto": documento.contacto,
                "identificacion": documento.identificacion,
                "moneda": MONEDA,
                "vence": vence,
                "dias_mora": (hoy - vence).days if saldo > 0 else 0,
                "total": documento.total,
                "abonado": abonado,
                "saldo": saldo,
                "estado": _estado_saldo(documento.total, abonado),
            }
        )

    return {
        "modo": modo,
        "etiqueta_contacto": etiqueta_contacto(modo),
        "moneda": MONEDA,
        "hoy": hoy,
        "documentos": filas,
        "total_documentos": len(filas),
        "total_original": redondear(sum((f["total"] for f in filas), CERO)),
        "abonado": redondear(sum((f["abonado"] for f in filas), CERO)),
        "saldo": redondear(sum((f["saldo"] for f in filas), CERO)),
    }


def _proximo_vencimiento(
    sesion: Session, documentos: list[_Documento]
) -> dict[tuple[str, int], date]:
    """
    La fecha en que vence lo que aún se debe de cada documento.

    Es la cuota pendiente más próxima. Sin plan de cuotas no hay más
    vencimiento que la fecha de emisión: el documento se debe entero desde el
    primer día.
    """
    identificadores = [d.id for d in documentos if d.origen == "Comprobante"]
    if not identificadores:
        return {}

    filas = sesion.execute(
        select(Cuota.comprobante_id, func.min(Cuota.vence))
        .where(Cuota.comprobante_id.in_(identificadores), Cuota.cobrado < Cuota.monto)
        .group_by(Cuota.comprobante_id)
    )
    return {("Comprobante", comprobante_id): vence for comprobante_id, vence in filas}


# --------------------------------------------------------------------------
# 2. Agenda de cuotas
# --------------------------------------------------------------------------


def agenda_de_cuotas(
    sesion: Session,
    modo: str,
    desde: date | None = None,
    hasta: date | None = None,
    solo_vencidas: bool = False,
    solo_pendientes: bool = True,
    hoy: date | None = None,
) -> dict:
    """
    Las cuotas por fecha, o todas las vencidas hasta hoy.

    `solo_vencidas` manda sobre el rango: pedir «lo vencido» y a la vez una
    ventana de fechas dejaría fuera la mora vieja, que es lo único que interesa
    de ese listado.
    """
    validar_modo(modo)
    hoy = hoy or date.today()

    documentos = _documentos(sesion, modo)
    abonos = _abonado_actual(sesion, modo)
    filas = _cuotas(sesion, documentos, abonos)

    if solo_vencidas:
        # Vencida es la que ya pasó su día y sigue debiendo. La que vence hoy
        # todavía está en plazo.
        filas = [fila for fila in filas if fila.vence < hoy and fila.saldo > 0]
        desde, hasta = None, None
    else:
        if desde:
            filas = [fila for fila in filas if fila.vence >= desde]
        if hasta:
            filas = [fila for fila in filas if fila.vence <= hasta]
        if solo_pendientes:
            filas = [fila for fila in filas if fila.saldo > 0]

    cuotas = [
        {
            "origen": fila.documento.origen,
            "documento_id": fila.documento.id,
            "documento": fila.documento.numero,
            "tipo": fila.documento.tipo,
            "contacto": fila.documento.contacto,
            "identificacion": fila.documento.identificacion,
            "correo": fila.documento.correo,
            "telefono": fila.documento.telefono,
            "cuota_id": fila.cuota_id,
            "numero": fila.numero,
            "vence": fila.vence,
            "dias_mora": fila.dias_mora(hoy) if fila.saldo > 0 else 0,
            "monto": fila.monto,
            "abonado": fila.abonado,
            "saldo": fila.saldo,
            "estado": fila.estado,
        }
        for fila in filas
    ]
    vencidas = [c for c in cuotas if c["saldo"] > 0 and c["vence"] < hoy]

    return {
        "modo": modo,
        "etiqueta_contacto": etiqueta_contacto(modo),
        "desde": desde,
        "hasta": hasta,
        "hoy": hoy,
        "cuotas": cuotas,
        "total_cuotas": len(cuotas),
        "monto": redondear(sum((c["monto"] for c in cuotas), CERO)),
        "abonado": redondear(sum((c["abonado"] for c in cuotas), CERO)),
        "saldo": redondear(sum((c["saldo"] for c in cuotas), CERO)),
        "vencidas": len(vencidas),
        "saldo_vencido": redondear(sum((c["saldo"] for c in vencidas), CERO)),
    }


# --------------------------------------------------------------------------
# 3. Recibos generados
# --------------------------------------------------------------------------


def recibos_generados(
    sesion: Session,
    modo: str,
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
) -> dict:
    """Los pagos aplicados, con su estado, su forma de pago y su documento."""
    validar_modo(modo)

    pagos = _pagos(sesion, modo, desde, hasta)
    if estado:
        pagos = [pago for pago in pagos if pago.estado == estado]

    filas = [
        {
            "origen": pago.origen,
            "recibo_id": pago.id,
            "numero": pago.numero,
            "fecha": pago.fecha,
            "contacto": pago.contacto,
            "documento": pago.documento,
            "cuota_id": pago.cuota_id,
            "monto": pago.monto,
            "forma_pago": pago.forma_pago,
            "estado": pago.estado,
            "referencia": pago.referencia,
        }
        for pago in pagos
    ]
    anulados = [fila for fila in filas if fila["estado"] == ANULADO]

    return {
        "modo": modo,
        "etiqueta_contacto": etiqueta_contacto(modo),
        "desde": desde,
        "hasta": hasta,
        "recibos": filas,
        "total_recibos": len(filas),
        # Lo aplicado descarta los anulados: anular es la forma de deshacer un
        # movimiento, no puede seguir sumando.
        "aplicado": redondear(
            sum((f["monto"] for f in filas if f["estado"] != ANULADO), CERO)
        ),
        "anulados": len(anulados),
        "monto_anulado": redondear(sum((f["monto"] for f in anulados), CERO)),
    }


# --------------------------------------------------------------------------
# 4. Rotación de cuentas
# --------------------------------------------------------------------------


@dataclass
class _Acumulado:
    """Lo que se va sumando de un grupo (un tipo de documento, un receptor)."""

    documentos: int = 0
    total: Decimal = field(default_factory=lambda: CERO)
    cobrado: Decimal = field(default_factory=lambda: CERO)
    pendiente: Decimal = field(default_factory=lambda: CERO)
    # Numerador y denominador del promedio ponderado de días.
    dias_por_dinero: Decimal = field(default_factory=lambda: CERO)
    dinero: Decimal = field(default_factory=lambda: CERO)

    def fila(self, grupo: str) -> dict:
        return {
            "grupo": grupo,
            "documentos": self.documentos,
            "total": redondear(self.total),
            "cobrado": redondear(self.cobrado),
            "pendiente": redondear(self.pendiente),
            "promedio": redondear(self.total / self.documentos) if self.documentos else CERO,
            # Días de recuperación: cuánto tarda de media en entrar (o salir)
            # cada dólar, ponderado por el importe de cada movimiento.
            #
            # Sin dinero movido en el período NO es cero: cero diría «se cobra
            # al contado», que es exactamente lo contrario de la verdad. Se
            # devuelve nulo y la interfaz pinta un guion.
            "dias_recuperacion": (
                redondear(self.dias_por_dinero / self.dinero, 1) if self.dinero > 0 else None
            ),
        }


def rotacion_de_cuentas(sesion: Session, modo: str, periodo: Periodo) -> dict:
    """
    Volumen pendiente por tipo de documento y por receptor, con días de
    recuperación.

    El saldo al corte NO sale de `Cuota.cobrado`: ese campo es un acumulado a
    hoy y no sabe cuándo entró el dinero, así que usarlo daría el saldo de hoy
    disfrazado de saldo de entonces. Se reconstruye con la fecha de los recibos
    y egresos, que sí la tienen — y ahí cada movimiento cuenta una sola vez,
    tenga cuota o no.
    """
    validar_modo(modo)

    documentos = _documentos(sesion, modo, periodo)
    por_clave = {documento.clave: documento for documento in documentos}

    # Todo lo aplicado a esos documentos hasta el corte del período. Sin fecha
    # inicial: un abono anterior al período también rebaja el saldo al corte.
    pagos = [
        pago
        for pago in _pagos(sesion, modo, None, periodo.hasta, incluir_anulados=False)
        if pago.documento_clave in por_clave
    ]

    cobrado_hasta_corte: dict[tuple[str, int], Decimal] = {}
    for pago in pagos:
        clave = pago.documento_clave
        cobrado_hasta_corte[clave] = cobrado_hasta_corte.get(clave, CERO) + pago.monto

    por_tipo: dict[str, _Acumulado] = {}
    por_contacto: dict[tuple[str, str], _Acumulado] = {}
    nombres: dict[tuple[str, str], str] = {}
    totales = _Acumulado()

    for documento in documentos:
        pendiente = redondear(
            documento.total - cobrado_hasta_corte.get(documento.clave, CERO)
        )
        for acumulado in (
            por_tipo.setdefault(documento.tipo, _Acumulado()),
            por_contacto.setdefault(documento.clave_contacto, _Acumulado()),
            totales,
        ):
            acumulado.documentos += 1
            acumulado.total += documento.total
            acumulado.pendiente += pendiente
        nombres[documento.clave_contacto] = documento.contacto

    for pago in pagos:
        if not (periodo.desde <= pago.fecha <= periodo.hasta):
            continue
        documento = por_clave[pago.documento_clave]
        # Un abono fechado antes que su documento (un anticipo mal registrado)
        # daría días negativos y rebajaría el promedio de todo el grupo; cuenta
        # como cero días, que es lo más cerca de la verdad que se puede afirmar.
        dias = Decimal(max(0, (pago.fecha - documento.fecha).days))
        for acumulado in (
            por_tipo.setdefault(documento.tipo, _Acumulado()),
            por_contacto.setdefault(documento.clave_contacto, _Acumulado()),
            totales,
        ):
            acumulado.cobrado += pago.monto
            acumulado.dias_por_dinero += dias * pago.monto
            acumulado.dinero += pago.monto

    filas_tipo = sorted(
        (acumulado.fila(tipo) for tipo, acumulado in por_tipo.items()),
        key=lambda fila: fila["pendiente"],
        reverse=True,
    )
    filas_contacto = sorted(
        (acumulado.fila(nombres[clave]) for clave, acumulado in por_contacto.items()),
        key=lambda fila: fila["pendiente"],
        reverse=True,
    )

    return {
        "modo": modo,
        "etiqueta_contacto": etiqueta_contacto(modo),
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "dias_periodo": periodo.dias,
        "por_tipo": filas_tipo,
        "por_contacto": filas_contacto,
        "totales": totales.fila("TOTAL"),
    }


# --------------------------------------------------------------------------
# 5. Historial por cliente/proveedor
# --------------------------------------------------------------------------


def historial_por_contacto(
    sesion: Session,
    modo: str,
    solo_con_saldo: bool = False,
    hoy: date | None = None,
) -> dict:
    """
    Un renglón por cliente (o proveedor): saldo, abonado, cuotas y próximo pago.

    La próxima fecha de pago es la cuota pendiente más antigua, esté vencida o
    no: si hay mora, lo próximo que toca pagar es justamente lo que ya venció.
    """
    validar_modo(modo)
    hoy = hoy or date.today()

    documentos = _documentos(sesion, modo)
    abonos = _abonado_actual(sesion, modo)
    filas_cuota = _cuotas(sesion, documentos, abonos)

    agrupado: dict[tuple[str, str], dict] = {}

    for documento in documentos:
        clave = documento.clave_contacto
        ficha = agrupado.setdefault(
            clave,
            {
                "receptor_id": documento.receptor_id,
                "contacto": documento.contacto,
                "identificacion": documento.identificacion,
                "correo": documento.correo,
                "telefono": documento.telefono,
                "documentos": 0,
                "total": CERO,
                "abonado": CERO,
                "saldo": CERO,
                "cuotas_pendientes": 0,
                "cuotas_vencidas": 0,
                "saldo_vencido": CERO,
                "proxima_fecha": None,
                "ultimo_movimiento": None,
            },
        )
        abonado = abonos.get(documento.clave, CERO)
        ficha["documentos"] += 1
        ficha["total"] += documento.total
        ficha["abonado"] += abonado
        ficha["saldo"] += documento.total - abonado

    for fila in filas_cuota:
        if fila.saldo <= 0:
            continue
        ficha = agrupado[fila.documento.clave_contacto]
        ficha["cuotas_pendientes"] += 1
        if fila.vence < hoy:
            ficha["cuotas_vencidas"] += 1
            ficha["saldo_vencido"] += fila.saldo
        if ficha["proxima_fecha"] is None or fila.vence < ficha["proxima_fecha"]:
            ficha["proxima_fecha"] = fila.vence

    por_documento = {documento.clave: documento for documento in documentos}
    for pago in _pagos(sesion, modo, incluir_anulados=False):
        documento = por_documento.get(pago.documento_clave)
        if documento is None:
            continue
        ficha = agrupado[documento.clave_contacto]
        if ficha["ultimo_movimiento"] is None or pago.fecha > ficha["ultimo_movimiento"]:
            ficha["ultimo_movimiento"] = pago.fecha

    contactos = []
    for ficha in agrupado.values():
        ficha["total"] = redondear(ficha["total"])
        ficha["abonado"] = redondear(ficha["abonado"])
        ficha["saldo"] = redondear(ficha["saldo"])
        ficha["saldo_vencido"] = redondear(ficha["saldo_vencido"])
        if solo_con_saldo and ficha["saldo"] <= 0:
            continue
        contactos.append(ficha)

    contactos.sort(key=lambda ficha: (-ficha["saldo"], ficha["contacto"]))

    return {
        "modo": modo,
        "etiqueta_contacto": etiqueta_contacto(modo),
        "hoy": hoy,
        "contactos": contactos,
        "total_contactos": len(contactos),
        "total": redondear(sum((c["total"] for c in contactos), CERO)),
        "abonado": redondear(sum((c["abonado"] for c in contactos), CERO)),
        "saldo": redondear(sum((c["saldo"] for c in contactos), CERO)),
    }
