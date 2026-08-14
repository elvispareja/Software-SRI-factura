"""
Cuentas por cobrar: cuotas, vencimientos y recibos.

El SRI no sabe nada de esto —una factura a crédito está igual de autorizada que
una al contado— pero el negocio necesita saber cuándo vence cada parte y quién
ya pagó.

Como en egresos, la **cuota** (lo que se debe) y el **recibo** (lo que se
cobró) son cosas distintas: un cliente puede abonar de a poco, y cada abono es
un movimiento de caja que hay que poder explicar por separado.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..esquemas import (
    CuotaSalida,
    GenerarCuotas,
    ReciboEntrada,
    ReciboSalida,
    ReporteAgendaCuotas,
    ReporteHistorialContactos,
    ReporteRecibosGenerados,
    ReporteRotacionCuentas,
    ReporteSaldosPendientes,
    ResumenCobros,
    SaldoInicialEntrada,
    SaldoInicialSalida,
)
from ..modelos_db import Comprobante, Cuota, Receptor, Recibo, SaldoInicial
from ..servicios import reportes_cuentas as servicio_reportes
from ..sri.modelos import redondear

# Importar no es tocar: el armador de CSV vive en el router de reportes y se
# reutiliza tal cual para que estos cinco salgan con el mismo `;` y el mismo BOM
# que el resto. No hay ciclo: aquel módulo no sabe nada de este.
from .reportes import _csv

router = APIRouter(prefix="/cuentas", tags=["cuentas por cobrar"])


def _recalcular_comprobante(sesion: Session, comprobante: Comprobante) -> None:
    """
    El estado de pago del comprobante sale de lo que se le haya cobrado.

    Se recalcula sobre la suma y no se toca a mano en cada recibo: dos caminos
    que escriben el mismo campo acaban discrepando.

    Hay **dos** fuentes de cobro, y contar solo la primera fue un fallo real:

    1. Lo imputado a sus cuotas (`Cuota.cobrado`), para las ventas a crédito.
    2. Los recibos emitidos contra el comprobante **sin cuota de por medio**,
       que es como se cobra una factura al contado. `crear_recibo` admite ese
       camino a propósito, pero esos recibos no incrementan ninguna cuota, así
       que mientras solo se sumaba (1) una factura cobrada al 100 % seguía
       marcada «Por Cobrar» para siempre, y aparecía como deuda pendiente en la
       pantalla de Cuentas y en los reportes de saldo.

    Los recibos anulados no cuentan: anular es la forma de deshacer un cobro.
    """
    cobrado_en_cuotas = sesion.scalar(
        select(func.coalesce(func.sum(Cuota.cobrado), 0)).where(
            Cuota.comprobante_id == comprobante.id
        )
    )
    cobrado_directo = sesion.scalar(
        select(func.coalesce(func.sum(Recibo.monto), 0)).where(
            Recibo.comprobante_id == comprobante.id,
            Recibo.cuota_id.is_(None),
            Recibo.estado != "Anulado",
        )
    )
    cobrado = redondear((cobrado_en_cuotas or 0) + (cobrado_directo or 0))

    if cobrado <= 0:
        comprobante.estado_pago = "Por Cobrar"
    elif cobrado >= comprobante.importe_total:
        comprobante.estado_pago = "Pagado"
    else:
        comprobante.estado_pago = "Parcial"


# --------------------------------------------------------------------------
# Cuotas
# --------------------------------------------------------------------------


@router.get("/cuotas", response_model=list[CuotaSalida])
def listar_cuotas(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    comprobante_id: int | None = None,
    vence_desde: date | None = None,
    vence_hasta: date | None = None,
    solo_pendientes: bool = False,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(50, ge=1, le=200),
):
    consulta = select(Cuota).options(selectinload(Cuota.comprobante))

    if comprobante_id:
        consulta = consulta.where(Cuota.comprobante_id == comprobante_id)
    if vence_desde:
        consulta = consulta.where(Cuota.vence >= vence_desde)
    if vence_hasta:
        consulta = consulta.where(Cuota.vence <= vence_hasta)
    if solo_pendientes:
        consulta = consulta.where(Cuota.cobrado < Cuota.monto)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = consulta.order_by(Cuota.vence).offset((pagina - 1) * tamano).limit(tamano)

    hoy = date.today()
    return [
        CuotaSalida(
            id=cuota.id,
            comprobante_id=cuota.comprobante_id,
            numero_comprobante=cuota.comprobante.numero if cuota.comprobante else "",
            receptor=cuota.comprobante.receptor_razon_social if cuota.comprobante else "",
            numero=cuota.numero,
            vence=cuota.vence,
            monto=cuota.monto,
            cobrado=cuota.cobrado,
            saldo=cuota.saldo,
            estado=cuota.estado,
            # Negativo si aún no vence; positivo son días de mora.
            dias_mora=(hoy - cuota.vence).days if cuota.saldo > 0 else 0,
        )
        for cuota in sesion.scalars(consulta).all()
    ]


@router.post("/comprobantes/{comprobante_id}/cuotas", response_model=list[CuotaSalida])
def generar_cuotas(
    comprobante_id: int,
    datos: GenerarCuotas,
    sesion: Session = Depends(obtener_sesion),
):
    """
    Reparte el importe del comprobante en cuotas.

    El reparto se hace en partes iguales y **el resto se acumula en la última**:
    dividir 100 en 3 da 33,33 tres veces, que suma 99,99. La cuota que falta un
    centavo es un cobro que nunca cuadra.
    """
    comprobante = sesion.get(Comprobante, comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "Comprobante no encontrado.")

    ya_cobrado = sesion.scalar(
        select(func.coalesce(func.sum(Cuota.cobrado), 0)).where(
            Cuota.comprobante_id == comprobante_id
        )
    )
    if redondear(ya_cobrado or 0) > 0:
        raise HTTPException(
            409,
            "Este comprobante ya tiene cobros registrados. Anula los recibos "
            "antes de rehacer el plan de cuotas.",
        )

    # Se borran las anteriores: regenerar es reemplazar, no acumular.
    for antigua in sesion.scalars(
        select(Cuota).where(Cuota.comprobante_id == comprobante_id)
    ).all():
        sesion.delete(antigua)
    sesion.flush()

    total = comprobante.importe_total
    cuota_base = redondear(total / datos.cuotas)
    primera = datos.primera_fecha or comprobante.fecha_emision

    creadas: list[Cuota] = []
    acumulado = Decimal("0")

    for indice in range(datos.cuotas):
        es_ultima = indice == datos.cuotas - 1
        monto = redondear(total - acumulado) if es_ultima else cuota_base
        acumulado += monto

        cuota = Cuota(
            comprobante_id=comprobante_id,
            numero=indice + 1,
            vence=primera + timedelta(days=datos.dias_entre_cuotas * indice),
            monto=monto,
        )
        sesion.add(cuota)
        creadas.append(cuota)

    # Con cuotas, el comprobante pasa a ser a crédito.
    comprobante.metodo = "Crédito"
    _recalcular_comprobante(sesion, comprobante)

    sesion.commit()
    for cuota in creadas:
        sesion.refresh(cuota)

    hoy = date.today()
    return [
        CuotaSalida(
            id=cuota.id,
            comprobante_id=cuota.comprobante_id,
            numero_comprobante=comprobante.numero,
            receptor=comprobante.receptor_razon_social,
            numero=cuota.numero,
            vence=cuota.vence,
            monto=cuota.monto,
            cobrado=cuota.cobrado,
            saldo=cuota.saldo,
            estado=cuota.estado,
            dias_mora=(hoy - cuota.vence).days if cuota.saldo > 0 else 0,
        )
        for cuota in creadas
    ]


# --------------------------------------------------------------------------
# Recibos
# --------------------------------------------------------------------------


def _siguiente_numero(sesion: Session) -> str:
    """
    Numeración propia de los recibos.

    No pasa por `reservar_secuencial` porque un recibo **no es un comprobante
    electrónico**: no viaja al SRI y no comparte serie con las facturas.
    """
    ultimo = sesion.scalar(select(func.count(Recibo.id))) or 0
    return f"REC-{ultimo + 1:06d}"


@router.get("/recibos", response_model=list[ReciboSalida])
def listar_recibos(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    buscar: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    pagina: int = Query(1, ge=1),
    tamano: int = Query(50, ge=1, le=200),
):
    consulta = select(Recibo)

    if buscar:
        patron = f"%{buscar.lower()}%"
        consulta = consulta.where(
            or_(
                func.lower(Recibo.numero).like(patron),
                func.lower(Recibo.receptor_razon_social).like(patron),
                func.lower(func.coalesce(Recibo.referencia, "")).like(patron),
            )
        )
    if estado:
        consulta = consulta.where(Recibo.estado == estado)
    if desde:
        consulta = consulta.where(Recibo.fecha >= desde)
    if hasta:
        consulta = consulta.where(Recibo.fecha <= hasta)

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = (
        consulta.order_by(Recibo.fecha.desc(), Recibo.id.desc())
        .offset((pagina - 1) * tamano)
        .limit(tamano)
    )
    return sesion.scalars(consulta).all()


def _nuevo_recibo(sesion: Session, numero: str, datos: ReciboEntrada, comprobante, cuota, monto: Decimal) -> Recibo:
    recibo = Recibo(
        numero=numero,
        fecha=datos.fecha or date.today(),
        cuota_id=cuota.id if cuota else None,
        comprobante_id=comprobante.id if comprobante else None,
        receptor_razon_social=comprobante.receptor_razon_social if comprobante else "",
        monto=monto,
        forma_pago=datos.forma_pago,
        cuenta_id=datos.cuenta_id,
        referencia=datos.referencia,
        observacion=datos.observacion,
    )
    sesion.add(recibo)
    if cuota is not None:
        cuota.cobrado = redondear(cuota.cobrado + monto)
    return recibo


@router.post("/recibos", response_model=ReciboSalida, status_code=201)
def crear_recibo(datos: ReciboEntrada, sesion: Session = Depends(obtener_sesion)):
    """
    Registra un cobro e imputa lo cobrado a su cuota.

    Un abono contra un `comprobante_id` directo, sin `cuota_id`, es como se
    cobra una venta al contado. Pero si ese comprobante además tiene un plan de
    cuotas, el abono suelto no bajaba ninguna, y la agenda —que suma cuotas—
    seguía mostrando pendiente lo que en caja ya se había cobrado.

    Se asume el criterio más común de cobranza, **FIFO**: el abono se reparte
    primero contra la cuota más próxima a vencer, y así sucesivamente. Es una
    decisión contable que no estaba tomada; queda documentada en
    `docs/avance_2026-08-11_fifo_y_correcciones.md`.
    """
    if datos.cuota_id is not None:
        cuota = sesion.get(Cuota, datos.cuota_id)
        if cuota is None:
            raise HTTPException(404, "La cuota indicada no existe.")

        if datos.monto > cuota.saldo:
            raise HTTPException(
                422,
                f"La cuota debe ${cuota.saldo:.2f} y se intentó cobrar "
                f"${datos.monto:.2f}. Registra el exceso como otro recibo.",
            )
        comprobante = sesion.get(Comprobante, cuota.comprobante_id)
        recibo = _nuevo_recibo(sesion, _siguiente_numero(sesion), datos, comprobante, cuota, datos.monto)
        sesion.flush()
        _recalcular_comprobante(sesion, comprobante)
        sesion.commit()
        sesion.refresh(recibo)
        return recibo

    if datos.comprobante_id is None:
        recibo = _nuevo_recibo(sesion, _siguiente_numero(sesion), datos, None, None, datos.monto)
        sesion.commit()
        sesion.refresh(recibo)
        return recibo

    comprobante = sesion.get(Comprobante, datos.comprobante_id)
    if comprobante is None:
        raise HTTPException(404, "El comprobante indicado no existe.")

    cuotas_pendientes = sesion.scalars(
        select(Cuota)
        .where(Cuota.comprobante_id == comprobante.id, Cuota.cobrado < Cuota.monto)
        .order_by(Cuota.vence, Cuota.numero)
    ).all()

    restante = datos.monto
    ultimo_numero = sesion.scalar(select(func.count(Recibo.id))) or 0
    ultimo_recibo = None

    for cuota in cuotas_pendientes:
        if restante <= 0:
            break
        aplicado = min(restante, cuota.saldo)
        ultimo_numero += 1
        ultimo_recibo = _nuevo_recibo(
            sesion, f"REC-{ultimo_numero:06d}", datos, comprobante, cuota, redondear(aplicado)
        )
        restante = redondear(restante - aplicado)

    # Lo que sobra tras cubrir todas las cuotas —o si no había ninguna— queda
    # como recibo suelto contra el comprobante, igual que antes de repartir.
    if restante > 0 or ultimo_recibo is None:
        ultimo_numero += 1
        ultimo_recibo = _nuevo_recibo(
            sesion, f"REC-{ultimo_numero:06d}", datos, comprobante, None, redondear(max(restante, Decimal("0")))
        )

    sesion.flush()
    _recalcular_comprobante(sesion, comprobante)
    sesion.commit()
    sesion.refresh(ultimo_recibo)
    return ultimo_recibo


@router.post("/recibos/{recibo_id}/anular", response_model=ReciboSalida)
def anular_recibo(recibo_id: int, sesion: Session = Depends(obtener_sesion)):
    """Se anula, no se borra: la caja debe poder explicar cada movimiento."""
    recibo = sesion.get(Recibo, recibo_id)
    if recibo is None:
        raise HTTPException(404, "Recibo no encontrado.")
    if recibo.estado == "Anulado":
        raise HTTPException(409, "Este recibo ya está anulado.")

    recibo.estado = "Anulado"

    if recibo.cuota_id:
        cuota = sesion.get(Cuota, recibo.cuota_id)
        if cuota is not None:
            cuota.cobrado = redondear(max(Decimal("0"), cuota.cobrado - recibo.monto))

    if recibo.comprobante_id:
        comprobante = sesion.get(Comprobante, recibo.comprobante_id)
        if comprobante is not None:
            sesion.flush()
            _recalcular_comprobante(sesion, comprobante)

    sesion.commit()
    sesion.refresh(recibo)
    return recibo


# --------------------------------------------------------------------------
# Resumen
# --------------------------------------------------------------------------


@router.get("/resumen", response_model=ResumenCobros)
def resumen(sesion: Session = Depends(obtener_sesion)):
    """
    Cuánto se debe y cuánto está vencido.

    No se acota por período: una cuota de hace tres meses sigue debiéndose hoy,
    y filtrarla escondería justo la deuda más vieja.
    """
    hoy = date.today()

    pendiente = sesion.scalar(
        select(func.coalesce(func.sum(Cuota.monto - Cuota.cobrado), 0)).where(
            Cuota.cobrado < Cuota.monto
        )
    )
    vencido = sesion.scalar(
        select(func.coalesce(func.sum(Cuota.monto - Cuota.cobrado), 0)).where(
            Cuota.cobrado < Cuota.monto, Cuota.vence < hoy
        )
    )
    por_vencer = sesion.scalar(
        select(func.coalesce(func.sum(Cuota.monto - Cuota.cobrado), 0)).where(
            Cuota.cobrado < Cuota.monto,
            Cuota.vence >= hoy,
            Cuota.vence <= hoy + timedelta(days=30),
        )
    )
    cuotas_vencidas = sesion.scalar(
        select(func.count(Cuota.id)).where(Cuota.cobrado < Cuota.monto, Cuota.vence < hoy)
    )
    cobrado_mes = sesion.scalar(
        select(func.coalesce(func.sum(Recibo.monto), 0)).where(
            Recibo.estado != "Anulado", Recibo.fecha >= hoy.replace(day=1)
        )
    )

    return ResumenCobros(
        pendiente=redondear(pendiente or 0),
        vencido=redondear(vencido or 0),
        por_vencer_30=redondear(por_vencer or 0),
        cuotas_vencidas=cuotas_vencidas or 0,
        cobrado_mes=redondear(cobrado_mes or 0),
    )


# --------------------------------------------------------------------------
# Reportes de cuentas pendientes
#
# Los cinco de la pestaña «Reportes», cada uno con su JSON y su CSV.
#
# Todos aceptan `modo=cobrar|pagar` y devuelven **datos distintos**, no los
# mismos con otro rótulo: en `cobrar` la deuda son los comprobantes de venta y
# el abono es el recibo; en `pagar` son los gastos saldados con egresos, más
# las liquidaciones de compra. El porqué de ese reparto está documentado en
# `servicios/reportes_cuentas.py`, que es donde se decide.
# --------------------------------------------------------------------------


def _modo(modo: str) -> str:
    try:
        return servicio_reportes.validar_modo(modo)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def _periodo(anio: int | None, mes: int | None) -> servicio_reportes.Periodo:
    try:
        return servicio_reportes.resolver_periodo(anio, mes)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


def _dinero(valor) -> str:
    """
    Dinero para el CSV: siempre dos decimales.

    Los importes van a Excel, y `0E-8` o `12.5` en una columna de dólares se
    leen como un error de la aplicación aunque el número esté bien.
    """
    return f"{redondear(valor):.2f}"


@router.get("/reportes/saldos", response_model=ReporteSaldosPendientes)
def reporte_saldos(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    incluir_saldados: bool = False,
    receptor_id: int | None = None,
):
    """Saldo pendiente por documento: total original y lo que falta."""
    return servicio_reportes.saldos_por_documento(
        sesion, _modo(modo), incluir_saldados, receptor_id
    )


@router.get("/reportes/saldos/csv")
def reporte_saldos_csv(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    incluir_saldados: bool = False,
    receptor_id: int | None = None,
):
    reporte = servicio_reportes.saldos_por_documento(
        sesion, _modo(modo), incluir_saldados, receptor_id
    )

    filas = [
        [
            documento["numero"],
            documento["tipo"],
            documento["fecha"],
            documento["contacto"],
            documento["identificacion"],
            documento["moneda"],
            documento["vence"],
            documento["dias_mora"],
            _dinero(documento["total"]),
            _dinero(documento["abonado"]),
            _dinero(documento["saldo"]),
            documento["estado"],
        ]
        for documento in reporte["documentos"]
    ]
    filas.append(
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            _dinero(reporte["total_original"]),
            _dinero(reporte["abonado"]),
            _dinero(reporte["saldo"]),
            "",
        ]
    )

    return _csv(
        f"saldos-por-{modo}",
        [
            "Documento",
            "Tipo",
            "Fecha",
            reporte["etiqueta_contacto"],
            "Identificación",
            "Moneda",
            "Vence",
            "Días de mora",
            "Total original",
            "Abonado",
            "Saldo",
            "Estado",
        ],
        filas,
    )


@router.get("/reportes/agenda", response_model=ReporteAgendaCuotas)
def reporte_agenda(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    desde: date | None = None,
    hasta: date | None = None,
    solo_vencidas: bool = False,
    solo_pendientes: bool = True,
):
    """Agenda de cuotas: por fecha, o todas las vencidas hasta hoy."""
    return servicio_reportes.agenda_de_cuotas(
        sesion, _modo(modo), desde, hasta, solo_vencidas, solo_pendientes
    )


@router.get("/reportes/agenda/csv")
def reporte_agenda_csv(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    desde: date | None = None,
    hasta: date | None = None,
    solo_vencidas: bool = False,
    solo_pendientes: bool = True,
):
    reporte = servicio_reportes.agenda_de_cuotas(
        sesion, _modo(modo), desde, hasta, solo_vencidas, solo_pendientes
    )

    filas = [
        [
            cuota["vence"],
            cuota["dias_mora"],
            cuota["documento"],
            cuota["tipo"],
            cuota["numero"],
            cuota["contacto"],
            cuota["identificacion"],
            cuota["telefono"],
            cuota["correo"],
            _dinero(cuota["monto"]),
            _dinero(cuota["abonado"]),
            _dinero(cuota["saldo"]),
            cuota["estado"],
        ]
        for cuota in reporte["cuotas"]
    ]
    filas.append(
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            _dinero(reporte["monto"]),
            _dinero(reporte["abonado"]),
            _dinero(reporte["saldo"]),
            "",
        ]
    )

    return _csv(
        f"agenda-de-cuotas-{modo}",
        [
            "Vence",
            "Días de mora",
            "Documento",
            "Tipo",
            "Cuota",
            reporte["etiqueta_contacto"],
            "Identificación",
            "Teléfono",
            "Correo",
            "Monto",
            "Abonado",
            "Saldo",
            "Estado",
        ],
        filas,
    )


@router.get("/reportes/recibos", response_model=ReporteRecibosGenerados)
def reporte_recibos(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
):
    """Recibos generados: pagos aplicados, estado, método y trazabilidad."""
    return servicio_reportes.recibos_generados(sesion, _modo(modo), desde, hasta, estado)


@router.get("/reportes/recibos/csv")
def reporte_recibos_csv(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    desde: date | None = None,
    hasta: date | None = None,
    estado: str | None = None,
):
    reporte = servicio_reportes.recibos_generados(
        sesion, _modo(modo), desde, hasta, estado
    )

    filas = [
        [
            recibo["numero"],
            recibo["fecha"],
            recibo["contacto"],
            recibo["documento"],
            recibo["cuota_id"] or "",
            recibo["forma_pago"],
            recibo["referencia"],
            _dinero(recibo["monto"]),
            recibo["estado"],
        ]
        for recibo in reporte["recibos"]
    ]
    filas.append(["TOTAL APLICADO", "", "", "", "", "", "", _dinero(reporte["aplicado"]), ""])

    return _csv(
        f"recibos-{modo}",
        [
            "Número",
            "Fecha",
            reporte["etiqueta_contacto"],
            "Documento",
            "Cuota",
            "Forma de pago",
            "Referencia",
            "Monto",
            "Estado",
        ],
        filas,
    )


@router.get("/reportes/rotacion", response_model=ReporteRotacionCuentas)
def reporte_rotacion(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    """Rotación: volumen pendiente por tipo y por receptor, con recuperación."""
    return servicio_reportes.rotacion_de_cuentas(
        sesion, _modo(modo), _periodo(anio, mes)
    )


@router.get("/reportes/rotacion/csv")
def reporte_rotacion_csv(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    periodo = _periodo(anio, mes)
    reporte = servicio_reportes.rotacion_de_cuentas(sesion, _modo(modo), periodo)

    def _fila(agrupacion: str, fila: dict) -> list:
        return [
            agrupacion,
            fila["grupo"],
            fila["documentos"],
            _dinero(fila["total"]),
            _dinero(fila["cobrado"]),
            _dinero(fila["pendiente"]),
            _dinero(fila["promedio"]),
            # Sin dinero movido no hay días que enseñar: un guion, no un cero.
            "—" if fila["dias_recuperacion"] is None else fila["dias_recuperacion"],
        ]

    filas = [_fila("Tipo de documento", fila) for fila in reporte["por_tipo"]]
    filas += [
        _fila(reporte["etiqueta_contacto"], fila) for fila in reporte["por_contacto"]
    ]
    filas.append(_fila("TOTAL", reporte["totales"]))

    return _csv(
        f"rotacion-{modo}-{periodo.etiqueta()}",
        [
            "Agrupación",
            "Grupo",
            "Documentos",
            "Total emitido",
            "Aplicado en el período",
            "Pendiente al corte",
            "Promedio por documento",
            "Días de recuperación",
        ],
        filas,
    )


@router.get("/reportes/historial", response_model=ReporteHistorialContactos)
def reporte_historial(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    solo_con_saldo: bool = False,
):
    """Historial por cliente o proveedor: saldo, abonos, cuotas y próximo pago."""
    return servicio_reportes.historial_por_contacto(sesion, _modo(modo), solo_con_saldo)


@router.get("/reportes/historial/csv")
def reporte_historial_csv(
    sesion: Session = Depends(obtener_sesion),
    modo: str = Query("cobrar"),
    solo_con_saldo: bool = False,
):
    reporte = servicio_reportes.historial_por_contacto(
        sesion, _modo(modo), solo_con_saldo
    )

    filas = [
        [
            ficha["contacto"],
            ficha["identificacion"],
            ficha["telefono"],
            ficha["correo"],
            ficha["documentos"],
            _dinero(ficha["total"]),
            _dinero(ficha["abonado"]),
            _dinero(ficha["saldo"]),
            ficha["cuotas_pendientes"],
            ficha["cuotas_vencidas"],
            _dinero(ficha["saldo_vencido"]),
            ficha["proxima_fecha"] or "—",
            ficha["ultimo_movimiento"] or "—",
        ]
        for ficha in reporte["contactos"]
    ]
    filas.append(
        [
            "TOTAL",
            "",
            "",
            "",
            "",
            _dinero(reporte["total"]),
            _dinero(reporte["abonado"]),
            _dinero(reporte["saldo"]),
            "",
            "",
            "",
            "",
            "",
        ]
    )

    return _csv(
        f"historial-{modo}",
        [
            reporte["etiqueta_contacto"],
            "Identificación",
            "Teléfono",
            "Correo",
            "Documentos",
            "Total",
            "Abonado",
            "Saldo actual",
            "Cuotas pendientes",
            "Cuotas vencidas",
            "Saldo vencido",
            "Próxima fecha de pago",
            "Último movimiento",
        ],
        filas,
    )


# --------------------------------------------------------------------------
# Saldos iniciales (arrastre)
#
# Deuda anterior a Factoa que el usuario carga a mano. Vive aparte del cálculo
# de saldos vivos para no arriesgar un doble conteo: la pantalla suma el saldo
# anterior y el saldo vivo solo en el frontend.
# --------------------------------------------------------------------------


@router.get("/saldos-iniciales", response_model=list[SaldoInicialSalida])
def listar_saldos_iniciales(
    respuesta: Response,
    sesion: Session = Depends(obtener_sesion),
    tipo: str | None = None,
):
    consulta = select(SaldoInicial)
    if tipo is not None:
        consulta = consulta.where(SaldoInicial.tipo == _modo(tipo))

    total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    respuesta.headers["X-Total-Registros"] = str(total)

    consulta = consulta.order_by(SaldoInicial.fecha.desc(), SaldoInicial.id.desc())
    return sesion.scalars(consulta).all()


@router.post("/saldos-iniciales", response_model=SaldoInicialSalida, status_code=201)
def crear_saldo_inicial(
    datos: SaldoInicialEntrada, sesion: Session = Depends(obtener_sesion)
):
    razon_social = datos.receptor_razon_social
    identificacion = ""
    receptor_id = None

    # Si apunta a un receptor del catálogo, sus datos mandan sobre el texto libre.
    if datos.receptor_id is not None:
        receptor = sesion.get(Receptor, datos.receptor_id)
        if receptor is None:
            raise HTTPException(404, "El receptor indicado no existe.")
        receptor_id = receptor.id
        razon_social = receptor.razon_social
        identificacion = receptor.identificacion

    saldo = SaldoInicial(
        receptor_id=receptor_id,
        receptor_razon_social=razon_social,
        identificacion=identificacion,
        tipo=_modo(datos.tipo),
        monto=redondear(datos.monto),
        fecha=datos.fecha or date.today(),
        detalle=datos.detalle,
        documento=datos.documento,
    )
    sesion.add(saldo)
    sesion.commit()
    sesion.refresh(saldo)
    return saldo


@router.delete("/saldos-iniciales/{saldo_id}", status_code=204)
def eliminar_saldo_inicial(saldo_id: int, sesion: Session = Depends(obtener_sesion)):
    saldo = sesion.get(SaldoInicial, saldo_id)
    if saldo is None:
        raise HTTPException(404, "Saldo inicial no encontrado.")
    sesion.delete(saldo)
    sesion.commit()
