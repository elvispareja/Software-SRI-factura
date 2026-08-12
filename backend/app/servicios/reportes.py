"""
Reportes de gestión y de sustento tributario.

Se calculan en SQL y no en la interfaz por dos razones: los importes viven en
`Decimal` y traerlos al navegador para sumarlos allí los degrada a `float`, y
un negocio con miles de comprobantes no puede descargarlos todos para pintar
una tarjeta con el total del mes.

REGLA QUE GOBIERNA TODOS LOS REPORTES
-------------------------------------
**Solo cuentan los comprobantes autorizados por el SRI.** Un borrador no es una
venta y un anulado dejó de serlo. Mezclarlos daría cifras que no cuadran con lo
que el SRI tiene registrado, que es justo con lo que hay que declarar.

La única excepción es `estado_sri`, cuyo propósito es precisamente enseñar
cuántos comprobantes están en cada estado, incluidos los que fallaron.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from ..modelos_db import (
    Comprobante,
    DetalleComprobante,
    DetalleRetencion,
    Egreso,
    Empresa,
    Gasto,
    Retencion,
    TipoGasto,
)
from ..sri.modelos import PORCENTAJES_IVA, redondear

# Comprobantes que representan una venta declarable.
TIPOS_VENTA = ("Factura", "Nota de Venta", "Liquidación de Compra")

# Estado que un comprobante debe tener para contar en un reporte tributario.
ESTADO_DECLARABLE = "Autorizado"


@dataclass
class Periodo:
    """Rango de fechas cerrado por ambos extremos."""

    desde: date
    hasta: date

    @classmethod
    def del_mes(cls, anio: int, mes: int) -> Periodo:
        ultimo = monthrange(anio, mes)[1]
        return cls(desde=date(anio, mes, 1), hasta=date(anio, mes, ultimo))

    @classmethod
    def del_anio(cls, anio: int) -> Periodo:
        return cls(desde=date(anio, 1, 1), hasta=date(anio, 12, 31))

    def etiqueta_sri(self) -> str:
        """Período fiscal en el formato MM/AAAA que usa el SRI."""
        return f"{self.desde:%m/%Y}"


def _entre(columna, periodo: Periodo):
    return columna.between(periodo.desde, periodo.hasta)


def _decimal(valor) -> Decimal:
    """
    Normaliza lo que devuelve SQL.

    SQLite suma en float aunque la columna sea Numeric, así que el resultado
    puede llegar como `float` o como `None` si no hubo filas.
    """
    if valor is None:
        return Decimal("0")
    return redondear(Decimal(str(valor)))


# --------------------------------------------------------------------------
# Ventas
# --------------------------------------------------------------------------


def resumen_ventas(sesion: Session, periodo: Periodo) -> dict:
    """Totales del período: cuántos comprobantes y por cuánto."""
    fila = sesion.execute(
        select(
            func.count(Comprobante.id),
            func.sum(Comprobante.total_sin_impuestos),
            func.sum(Comprobante.total_descuento),
            func.sum(Comprobante.total_iva),
            func.sum(Comprobante.importe_total),
        ).where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
    ).one()

    cantidad = fila[0] or 0
    total = _decimal(fila[4])

    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "comprobantes": cantidad,
        "subtotal": _decimal(fila[1]),
        "descuento": _decimal(fila[2]),
        "iva": _decimal(fila[3]),
        "total": total,
        # Un promedio sobre cero comprobantes no es cero: no existe. Pero
        # devolver null obligaría a la interfaz a distinguirlo, y para una
        # tarjeta de resumen cero es una lectura honesta de "no hubo ventas".
        "ticket_promedio": redondear(total / cantidad) if cantidad else Decimal("0"),
    }


def ventas_por_tipo(sesion: Session, periodo: Periodo) -> list[dict]:
    filas = sesion.execute(
        select(
            Comprobante.tipo,
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
        )
        .where(
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(Comprobante.tipo)
        .order_by(func.sum(Comprobante.importe_total).desc())
    ).all()

    return [
        {"tipo": tipo, "cantidad": cantidad or 0, "total": _decimal(total)}
        for tipo, cantidad, total in filas
    ]


def ventas_por_mes(sesion: Session, anio: int) -> list[dict]:
    """
    Serie mensual del año, con los doce meses siempre presentes.

    Los meses sin ventas van en cero y no ausentes: una gráfica a la que le
    faltan meses sugiere que no hay datos, no que no hubo ventas.
    """
    # `extract` en vez de `strftime`: SQLAlchemy lo traduce al dialecto de
    # turno, así que esto sigue funcionando al migrar a PostgreSQL.
    numero_mes = extract("month", Comprobante.fecha_emision)

    filas = sesion.execute(
        select(
            numero_mes,
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
        )
        .where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, Periodo.del_anio(anio)),
        )
        .group_by(numero_mes)
    ).all()

    por_mes = {int(mes): (cantidad or 0, _decimal(total)) for mes, cantidad, total in filas}

    return [
        {
            "mes": mes,
            "cantidad": por_mes.get(mes, (0, Decimal("0")))[0],
            "total": por_mes.get(mes, (0, Decimal("0")))[1],
        }
        for mes in range(1, 13)
    ]


def top_clientes(sesion: Session, periodo: Periodo, limite: int = 10) -> list[dict]:
    filas = sesion.execute(
        select(
            Comprobante.receptor_razon_social,
            Comprobante.receptor_identificacion,
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
        )
        .where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(Comprobante.receptor_identificacion, Comprobante.receptor_razon_social)
        .order_by(func.sum(Comprobante.importe_total).desc())
        .limit(limite)
    ).all()

    return [
        {
            "razon_social": razon_social,
            "identificacion": identificacion,
            "comprobantes": cantidad or 0,
            "total": _decimal(total),
        }
        for razon_social, identificacion, cantidad, total in filas
    ]


def top_articulos(sesion: Session, periodo: Periodo, limite: int = 10) -> list[dict]:
    """Lo más vendido, por importe facturado y no por número de líneas."""
    filas = sesion.execute(
        select(
            DetalleComprobante.codigo_principal,
            func.max(DetalleComprobante.descripcion),
            func.sum(DetalleComprobante.cantidad),
            func.sum(DetalleComprobante.base_imponible),
        )
        .join(Comprobante, DetalleComprobante.comprobante_id == Comprobante.id)
        .where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(DetalleComprobante.codigo_principal)
        .order_by(func.sum(DetalleComprobante.base_imponible).desc())
        .limit(limite)
    ).all()

    return [
        {
            "codigo": codigo,
            "descripcion": descripcion,
            "cantidad": _decimal(cantidad),
            "total": _decimal(total),
        }
        for codigo, descripcion, cantidad, total in filas
    ]


# --------------------------------------------------------------------------
# IVA en ventas — sustento del formulario 104
# --------------------------------------------------------------------------


def iva_en_ventas(sesion: Session, periodo: Periodo) -> dict:
    """
    Base imponible e IVA agrupados por tarifa.

    Es lo que se traslada al formulario 104: las ventas con tarifa distinta de
    cero van en casilleros distintos de las de tarifa cero, así que sumarlas
    todas juntas no sirve para declarar.
    """
    filas = sesion.execute(
        select(
            DetalleComprobante.codigo_iva,
            func.sum(DetalleComprobante.base_imponible),
            func.sum(DetalleComprobante.valor_iva),
        )
        .join(Comprobante, DetalleComprobante.comprobante_id == Comprobante.id)
        .where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(DetalleComprobante.codigo_iva)
    ).all()

    tarifas = [
        {
            "codigo_iva": codigo,
            "porcentaje": PORCENTAJES_IVA.get(codigo, Decimal("0")),
            "base_imponible": _decimal(base),
            "valor_iva": _decimal(iva),
        }
        for codigo, base, iva in filas
    ]
    tarifas.sort(key=lambda fila: fila["porcentaje"], reverse=True)

    return {
        "periodo_fiscal": periodo.etiqueta_sri(),
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "tarifas": tarifas,
        "base_total": redondear(sum((t["base_imponible"] for t in tarifas), Decimal("0"))),
        "iva_total": redondear(sum((t["valor_iva"] for t in tarifas), Decimal("0"))),
    }


# --------------------------------------------------------------------------
# Retenciones emitidas — sustento del formulario 103
# --------------------------------------------------------------------------


def retenciones_emitidas(sesion: Session, periodo: Periodo) -> dict:
    """
    Retenciones autorizadas del período, agrupadas por concepto.

    Se filtra por `periodo_fiscal` y no por fecha de emisión: el SRI declara
    por el período al que corresponde la retención, que puede no coincidir con
    el día en que se emitió el comprobante.
    """
    etiqueta = periodo.etiqueta_sri()

    filas = sesion.execute(
        select(
            DetalleRetencion.codigo_impuesto,
            DetalleRetencion.codigo_retencion,
            func.count(DetalleRetencion.id),
            func.sum(DetalleRetencion.base_imponible),
            func.sum(DetalleRetencion.valor_retenido),
        )
        .join(Retencion, DetalleRetencion.retencion_id == Retencion.id)
        .where(
            Retencion.estado_sri == ESTADO_DECLARABLE,
            Retencion.periodo_fiscal == etiqueta,
        )
        .group_by(DetalleRetencion.codigo_impuesto, DetalleRetencion.codigo_retencion)
        .order_by(func.sum(DetalleRetencion.valor_retenido).desc())
    ).all()

    conceptos = [
        {
            "codigo_impuesto": codigo_impuesto,
            "codigo_retencion": codigo_retencion,
            "lineas": cantidad or 0,
            "base_imponible": _decimal(base),
            "valor_retenido": _decimal(retenido),
        }
        for codigo_impuesto, codigo_retencion, cantidad, base, retenido in filas
    ]

    total_comprobantes = sesion.scalar(
        select(func.count(Retencion.id)).where(
            Retencion.estado_sri == ESTADO_DECLARABLE,
            Retencion.periodo_fiscal == etiqueta,
        )
    )

    def _suma(impuesto: str) -> Decimal:
        return redondear(
            sum(
                (c["valor_retenido"] for c in conceptos if c["codigo_impuesto"] == impuesto),
                Decimal("0"),
            )
        )

    return {
        "periodo_fiscal": etiqueta,
        "comprobantes": total_comprobantes or 0,
        "conceptos": conceptos,
        "total_renta": _suma("1"),
        "total_iva": _suma("2"),
        "total_retenido": redondear(
            sum((c["valor_retenido"] for c in conceptos), Decimal("0"))
        ),
    }


# --------------------------------------------------------------------------
# Estado ante el SRI
# --------------------------------------------------------------------------


def estado_sri(sesion: Session, periodo: Periodo) -> dict:
    """
    Cuántos comprobantes hay en cada estado.

    A diferencia del resto, aquí **sí** entran los no autorizados: el objetivo
    es justamente sacar a la luz los que quedaron a medias, que de otro modo
    pasan inadvertidos hasta que el SRI los reclama.
    """
    filas = sesion.execute(
        select(Comprobante.estado_sri, func.count(Comprobante.id))
        .where(_entre(Comprobante.fecha_emision, periodo))
        .group_by(Comprobante.estado_sri)
        .order_by(func.count(Comprobante.id).desc())
    ).all()

    por_estado = [{"estado": estado, "cantidad": cantidad or 0} for estado, cantidad in filas]
    total = sum(fila["cantidad"] for fila in por_estado)

    pendientes = sum(
        fila["cantidad"]
        for fila in por_estado
        if fila["estado"] in ("Borrador", "Pendiente", "Devuelto", "Rechazado", "Error")
    )

    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "por_estado": por_estado,
        "total": total,
        # Lo que el usuario tiene que resolver: emitidos a medias o rechazados.
        "requieren_atencion": pendientes,
    }


def cuentas_por_cobrar(sesion: Session) -> dict:
    """
    Saldo pendiente de cobro, sin acotar por período.

    Una factura de hace tres meses sigue debiéndose hoy; filtrarla por fecha
    escondería justo la deuda más vieja.
    """
    fila = sesion.execute(
        select(
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
            func.sum(
                case((Comprobante.metodo == "Crédito", Comprobante.importe_total), else_=0)
            ),
        ).where(
            Comprobante.tipo.in_(TIPOS_VENTA),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            Comprobante.estado_pago != "Pagado",
        )
    ).one()

    return {
        "comprobantes": fila[0] or 0,
        "total": _decimal(fila[1]),
        "a_credito": _decimal(fila[2]),
    }


# --------------------------------------------------------------------------
# Panel de inicio
# --------------------------------------------------------------------------


def panel(sesion: Session, hoy: date) -> dict:
    """Todo lo que pinta el Dashboard, en una sola consulta al API."""
    mes = Periodo.del_mes(hoy.year, hoy.month)
    anio = Periodo.del_anio(hoy.year)

    empresa = sesion.scalars(select(Empresa).limit(1)).first()

    return {
        "hoy": hoy,
        # El ambiente se enseña en el panel porque emitir en pruebas creyendo
        # que es producción no se nota hasta que hay que declarar.
        "ambiente": (empresa.ambiente if empresa else "1"),
        "mes": resumen_ventas(sesion, mes),
        "anio": resumen_ventas(sesion, anio),
        "por_tipo": ventas_por_tipo(sesion, anio),
        "serie_mensual": ventas_por_mes(sesion, hoy.year),
        "top_clientes": top_clientes(sesion, anio, limite=5),
        "top_articulos": top_articulos(sesion, anio, limite=5),
        "estado_sri": estado_sri(sesion, anio),
        "por_cobrar": cuentas_por_cobrar(sesion),
    }


# --------------------------------------------------------------------------
# Reportes por familia de documento
#
# Los cuatro comparten forma —cuántos, por cuánto, y quién— pero difieren en
# qué tipo de comprobante miran y en si cuentan como venta. Se escriben por
# separado en vez de con un parámetro genérico porque cada uno tiene reglas
# propias: la cotización nunca se autoriza, y la nota de crédito resta.
# --------------------------------------------------------------------------


def _por_receptor(sesion: Session, tipos: tuple[str, ...], periodo: Periodo,
                  estados: tuple[str, ...] | None = None) -> list[dict]:
    """Desglose por receptor de los tipos indicados."""
    consulta = (
        select(
            Comprobante.receptor_razon_social,
            Comprobante.receptor_identificacion,
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
        )
        .where(
            Comprobante.tipo.in_(tipos),
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(Comprobante.receptor_identificacion, Comprobante.receptor_razon_social)
        .order_by(func.sum(Comprobante.importe_total).desc())
    )
    if estados is not None:
        consulta = consulta.where(Comprobante.estado_sri.in_(estados))

    return [
        {
            "razon_social": razon_social,
            "identificacion": identificacion,
            "comprobantes": cantidad or 0,
            "total": _decimal(total),
        }
        for razon_social, identificacion, cantidad, total in sesion.execute(consulta).all()
    ]


def notas_de_venta(sesion: Session, periodo: Periodo) -> dict:
    """Notas de venta autorizadas del período, por receptor."""
    filas = _por_receptor(sesion, ("Nota de Venta",), periodo, (ESTADO_DECLARABLE,))
    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "receptores": filas,
        "comprobantes": sum(f["comprobantes"] for f in filas),
        "total": redondear(sum((f["total"] for f in filas), Decimal("0"))),
    }


def cotizaciones(sesion: Session, periodo: Periodo) -> dict:
    """
    Cotizaciones del período y cuántas acabaron en factura.

    No se filtra por estado autorizado: una cotización **nunca** se transmite
    al SRI, así que exigirlo daría siempre cero. La conversión se estima
    comparando contra las facturas del mismo receptor en el período, que es lo
    máximo que se puede afirmar sin un vínculo explícito entre ambos
    documentos.
    """
    filas = _por_receptor(sesion, ("Cotización",), periodo)

    facturados = {
        identificacion
        for (identificacion,) in sesion.execute(
            select(Comprobante.receptor_identificacion).where(
                Comprobante.tipo == "Factura",
                Comprobante.estado_sri == ESTADO_DECLARABLE,
                _entre(Comprobante.fecha_emision, periodo),
            )
        ).all()
    }

    for fila in filas:
        fila["con_factura"] = fila["identificacion"] in facturados

    convertidas = sum(1 for f in filas if f["con_factura"])

    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "receptores": filas,
        "comprobantes": sum(f["comprobantes"] for f in filas),
        "total": redondear(sum((f["total"] for f in filas), Decimal("0"))),
        "receptores_con_factura": convertidas,
    }


def notas_credito_debito(sesion: Session, periodo: Periodo) -> dict:
    """
    Notas de crédito y débito, separadas.

    Van juntas en un reporte porque se revisan juntas —son las correcciones
    del período— pero nunca se suman: una resta valor y la otra lo aumenta.
    """
    filas = sesion.execute(
        select(
            Comprobante.tipo,
            func.count(Comprobante.id),
            func.sum(Comprobante.importe_total),
        )
        .where(
            Comprobante.tipo.in_(("Nota de Crédito", "Nota de Débito")),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .group_by(Comprobante.tipo)
    ).all()

    por_tipo = {tipo: (cantidad or 0, _decimal(total)) for tipo, cantidad, total in filas}
    credito = por_tipo.get("Nota de Crédito", (0, Decimal("0")))
    debito = por_tipo.get("Nota de Débito", (0, Decimal("0")))

    documentos = sesion.execute(
        select(
            Comprobante.numero,
            Comprobante.tipo,
            Comprobante.fecha_emision,
            Comprobante.receptor_razon_social,
            Comprobante.num_doc_modificado,
            Comprobante.motivo,
            Comprobante.importe_total,
        )
        .where(
            Comprobante.tipo.in_(("Nota de Crédito", "Nota de Débito")),
            Comprobante.estado_sri == ESTADO_DECLARABLE,
            _entre(Comprobante.fecha_emision, periodo),
        )
        .order_by(Comprobante.fecha_emision.desc())
    ).all()

    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "notas_credito": credito[0],
        "total_credito": credito[1],
        "notas_debito": debito[0],
        "total_debito": debito[1],
        # El neto se ofrece calculado para que nadie lo sume al revés.
        "neto": redondear(debito[1] - credito[1]),
        "documentos": [
            {
                "numero": numero,
                "tipo": tipo,
                "fecha": fecha,
                "receptor": receptor,
                "documento_modificado": modificado or "",
                "motivo": motivo or "",
                "total": _decimal(total),
            }
            for numero, tipo, fecha, receptor, modificado, motivo, total in documentos
        ],
    }


def egresos_por_tipo(sesion: Session, periodo: Periodo) -> dict:
    """
    Gastos del período agrupados por su categoría.

    Los gastos no son comprobantes electrónicos, así que aquí no aplica el
    filtro de "autorizado": lo que se registró, se gastó.
    """
    filas = sesion.execute(
        select(
            func.coalesce(TipoGasto.nombre, "Sin clasificar"),
            func.coalesce(TipoGasto.deducible, True),
            func.count(Gasto.id),
            func.sum(Gasto.subtotal),
            func.sum(Gasto.iva),
            func.sum(Gasto.total),
        )
        .select_from(Gasto)
        .join(TipoGasto, Gasto.tipo_id == TipoGasto.id, isouter=True)
        .where(_entre(Gasto.fecha, periodo))
        .group_by(TipoGasto.nombre, TipoGasto.deducible)
        .order_by(func.sum(Gasto.total).desc())
    ).all()

    tipos = [
        {
            "tipo": nombre,
            "deducible": bool(deducible),
            "gastos": cantidad or 0,
            "subtotal": _decimal(subtotal),
            "iva": _decimal(iva),
            "total": _decimal(total),
        }
        for nombre, deducible, cantidad, subtotal, iva, total in filas
    ]

    pagado = sesion.scalar(
        select(func.coalesce(func.sum(Egreso.monto), 0)).where(
            Egreso.estado != "Anulado", _entre(Egreso.fecha, periodo)
        )
    )

    return {
        "desde": periodo.desde,
        "hasta": periodo.hasta,
        "tipos": tipos,
        "total": redondear(sum((t["total"] for t in tipos), Decimal("0"))),
        # Deducible y no deducible por separado: solo el primero baja la renta.
        "total_deducible": redondear(
            sum((t["total"] for t in tipos if t["deducible"]), Decimal("0"))
        ),
        "iva_soportado": redondear(sum((t["iva"] for t in tipos), Decimal("0"))),
        "total_pagado": redondear(pagado or 0),
    }


def inventario(sesion: Session, solo_con_stock: bool = False) -> dict:
    """
    Existencias y su valor.

    El valor se calcula al **costo**, no al precio de venta: el inventario es
    lo que costó reponerlo, no lo que se espera cobrar por él.
    """
    from ..modelos_db import Articulo

    consulta = select(Articulo).where(Articulo.estado == "Activo")
    if solo_con_stock:
        consulta = consulta.where(Articulo.stock.isnot(None), Articulo.stock > 0)

    articulos = sesion.scalars(consulta.order_by(Articulo.nombre)).all()

    filas = []
    for articulo in articulos:
        # Los servicios no manejan stock; se listan aparte de los productos.
        stock = _decimal(articulo.stock) if articulo.stock is not None else None
        filas.append(
            {
                "codigo": articulo.codigo,
                "nombre": articulo.nombre,
                "tipo": articulo.tipo,
                "categoria": articulo.categoria or "Sin categoría",
                "unidad": articulo.unidad,
                "stock": stock,
                "stock_minimo": _decimal(articulo.stock_minimo),
                "costo": _decimal(articulo.costo),
                "precio": _decimal(articulo.precio),
                "valor": redondear((stock or Decimal("0")) * _decimal(articulo.costo)),
                "bajo_minimo": stock is not None and stock <= _decimal(articulo.stock_minimo),
            }
        )

    con_stock = [f for f in filas if f["stock"] is not None]

    return {
        "articulos": filas,
        "total_articulos": len(filas),
        "productos": len(con_stock),
        "servicios": len(filas) - len(con_stock),
        "valor_inventario": redondear(sum((f["valor"] for f in filas), Decimal("0"))),
        "bajo_minimo": sum(1 for f in filas if f["bajo_minimo"]),
    }


def receptores(sesion: Session, rol: str | None = None) -> dict:
    """
    Clientes, proveedores y transportistas con lo que han facturado.

    Se cuentan solo comprobantes autorizados, como en el resto de reportes.
    """
    from ..modelos_db import Receptor

    consulta = select(Receptor).where(Receptor.estado == "Activo")
    if rol:
        consulta = consulta.where(Receptor.rol == rol)

    lista = sesion.scalars(consulta.order_by(Receptor.razon_social)).all()

    facturado = dict(
        sesion.execute(
            select(
                Comprobante.receptor_identificacion,
                func.coalesce(func.sum(Comprobante.importe_total), 0),
            )
            .where(Comprobante.estado_sri == ESTADO_DECLARABLE)
            .group_by(Comprobante.receptor_identificacion)
        ).all()
    )

    filas = [
        {
            "razon_social": receptor.razon_social,
            "identificacion": receptor.identificacion,
            "tipo_identificacion": receptor.tipo_identificacion,
            "rol": receptor.rol,
            "correo": receptor.correo or "",
            "telefono": receptor.telefono1 or "",
            "facturado": _decimal(facturado.get(receptor.identificacion, 0)),
        }
        for receptor in lista
    ]

    return {
        "receptores": filas,
        "total": len(filas),
        "clientes": sum(1 for f in filas if f["rol"] == "Cliente"),
        "proveedores": sum(1 for f in filas if f["rol"] == "Proveedor"),
        "transportistas": sum(1 for f in filas if f["rol"] == "Transportista"),
    }
