"""
Endpoints de reportes.

El período se pide como año y mes sueltos en vez de dos fechas: los reportes
tributarios son siempre mensuales o anuales, y aceptar rangos arbitrarios
invitaría a declarar un período que el SRI no reconoce.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import NamedTuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..base_datos import obtener_sesion
from ..modelos_db import Empresa
from ..esquemas import (
    ArticuloDestacado,
    ClienteDestacado,
    Panel,
    ReporteCotizaciones,
    ReporteEgresos,
    ReporteNotas,
    ReporteNotasVenta,
    ReporteInventario,
    ReporteReceptores,
    ReporteEstadoSri,
    ReporteIva,
    ReporteRetenciones,
    ResumenVentas,
    VentasPorMes,
    VentasPorTipo,
)
from ..servicios import reportes as servicio
from ..servicios.reportes_pdf import generar_pdf_reporte

router = APIRouter(prefix="/reportes", tags=["reportes"])

# El SRI guarda comprobantes electrónicos desde 2012; antes no hay nada que ver.
ANIO_MINIMO = 2012


def _periodo(anio: int | None, mes: int | None) -> servicio.Periodo:
    """Resuelve el período pedido; sin argumentos, el mes en curso."""
    hoy = date.today()
    anio = anio or hoy.year
    if anio < ANIO_MINIMO or anio > hoy.year + 1:
        raise HTTPException(422, f"El año {anio} está fuera de rango.")

    if mes is None:
        return servicio.Periodo.del_anio(anio)
    return servicio.Periodo.del_mes(anio, mes)


@router.get("/panel", response_model=Panel)
def panel(sesion: Session = Depends(obtener_sesion)):
    """Todo lo que necesita el Dashboard, en una sola petición."""
    return servicio.panel(sesion, date.today())


@router.get("/ventas", response_model=ResumenVentas)
def ventas(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return servicio.resumen_ventas(sesion, _periodo(anio, mes))


@router.get("/ventas/por-tipo", response_model=list[VentasPorTipo])
def ventas_por_tipo(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return servicio.ventas_por_tipo(sesion, _periodo(anio, mes))


@router.get("/ventas/por-mes", response_model=list[VentasPorMes])
def ventas_por_mes(sesion: Session = Depends(obtener_sesion), anio: int | None = None):
    return servicio.ventas_por_mes(sesion, anio or date.today().year)


@router.get("/clientes", response_model=list[ClienteDestacado])
def clientes(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    limite: int = Query(10, ge=1, le=100),
):
    return servicio.top_clientes(sesion, _periodo(anio, mes), limite)


@router.get("/articulos", response_model=list[ArticuloDestacado])
def articulos(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
    limite: int = Query(10, ge=1, le=100),
):
    return servicio.top_articulos(sesion, _periodo(anio, mes), limite)


@router.get("/iva", response_model=ReporteIva)
def iva(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    """
    IVA en ventas del mes, agrupado por tarifa.

    El mes es obligatorio: el 104 se declara mensualmente y un acumulado anual
    no se puede trasladar a ningún casillero.
    """
    return servicio.iva_en_ventas(sesion, _periodo(anio, mes))


@router.get("/retenciones", response_model=ReporteRetenciones)
def retenciones(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    """Retenciones emitidas del período fiscal, para el 103."""
    return servicio.retenciones_emitidas(sesion, _periodo(anio, mes))


@router.get("/estado-sri", response_model=ReporteEstadoSri)
def estado_sri(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return servicio.estado_sri(sesion, _periodo(anio, mes))


# --------------------------------------------------------------------------
# Reportes por familia de documento
# --------------------------------------------------------------------------


@router.get("/notas-venta", response_model=ReporteNotasVenta)
def notas_venta(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    """Notas de venta autorizadas del período, desglosadas por receptor."""
    return servicio.notas_de_venta(sesion, _periodo(anio, mes))


@router.get("/cotizaciones", response_model=ReporteCotizaciones)
def cotizaciones(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    """
    Cotizaciones del período.

    No filtra por autorizadas: una cotización nunca se transmite al SRI, así
    que exigirlo daría siempre cero.
    """
    return servicio.cotizaciones(sesion, _periodo(anio, mes))


@router.get("/notas", response_model=ReporteNotas)
def notas(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    """Notas de crédito y débito, separadas: una resta y la otra suma."""
    return servicio.notas_credito_debito(sesion, _periodo(anio, mes))


@router.get("/egresos", response_model=ReporteEgresos)
def egresos(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    """Gastos del período por categoría, separando lo deducible."""
    return servicio.egresos_por_tipo(sesion, _periodo(anio, mes))


@router.get("/inventario", response_model=ReporteInventario)
def inventario(
    sesion: Session = Depends(obtener_sesion),
    solo_con_stock: bool = False,
):
    """Existencias y su valor al costo, no al precio de venta."""
    return servicio.inventario(sesion, solo_con_stock)


@router.get("/receptores", response_model=ReporteReceptores)
def receptores(sesion: Session = Depends(obtener_sesion), rol: str | None = None):
    """Clientes, proveedores y transportistas con lo que han facturado."""
    return servicio.receptores(sesion, rol)


# --------------------------------------------------------------------------
# Exportación
#
# Cada reporte se describe una sola vez, en un `Tabla`, y de ahí salen tanto el
# CSV como el PDF. Escribir las filas dos veces —una por formato— haría que el
# día que alguien añada una columna al CSV el PDF quede desactualizado y nadie
# se entere hasta que un cliente lo imprima.
# --------------------------------------------------------------------------


class Tabla(NamedTuple):
    """Un reporte listo para volcar a cualquier formato tabular."""

    nombre: str  # nombre del archivo, sin extensión
    titulo: str
    subtitulo: str
    cabeceras: list[str]
    filas: list[list]
    # Fila de cierre. Va aparte de `filas` porque el PDF la destaca y el CSV la
    # escribe como una fila más.
    totales: list | None = None
    nota: str | None = None


def _rotulo(periodo: servicio.Periodo) -> str:
    return f"Del {periodo.desde:%d/%m/%Y} al {periodo.hasta:%d/%m/%Y}"


def _csv(nombre: str, cabeceras: list[str], filas: list[list]) -> StreamingResponse:
    """
    Arma un CSV descargable.

    Se escribe con `;` y BOM porque el destino real de estos archivos es Excel
    en español: con `,` mete todo en una columna, y sin BOM rompe las tildes.
    """
    memoria = io.StringIO()
    escritor = csv.writer(memoria, delimiter=";")
    escritor.writerow(cabeceras)
    escritor.writerows(filas)

    contenido = "﻿" + memoria.getvalue()

    return StreamingResponse(
        io.BytesIO(contenido.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.csv"'},
    )


def _descargar_csv(tabla: Tabla) -> StreamingResponse:
    filas = list(tabla.filas)
    if tabla.totales:
        filas.append(list(tabla.totales))
    return _csv(tabla.nombre, tabla.cabeceras, filas)


def _descargar_pdf(sesion: Session, tabla: Tabla) -> StreamingResponse:
    """
    Genera el PDF del reporte.

    Si la empresa no está configurada el PDF sale igual, sin cabecera de
    emisor: a diferencia de un comprobante electrónico, un reporte de gestión
    no se transmite al SRI, así que bloquear la descarga con un 409 sería
    estorbar a quien solo quiere ver sus números.
    """
    empresa = sesion.scalars(select(Empresa).limit(1)).first()

    contenido = generar_pdf_reporte(
        empresa=empresa,
        titulo=tabla.titulo,
        subtitulo=tabla.subtitulo,
        cabeceras=tabla.cabeceras,
        filas=tabla.filas,
        totales=tabla.totales,
        nota=tabla.nota,
    )

    return StreamingResponse(
        io.BytesIO(contenido),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{tabla.nombre}.pdf"'},
    )


# --- Armado de cada reporte ------------------------------------------------


def _tabla_iva(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.iva_en_ventas(sesion, periodo)
    etiqueta = reporte["periodo_fiscal"]

    return Tabla(
        nombre=f"iva-ventas-{etiqueta.replace('/', '-')}",
        titulo="IVA en ventas",
        subtitulo=f"Período fiscal {etiqueta} — {_rotulo(periodo)}",
        cabeceras=["Código IVA", "Tarifa", "Base imponible", "IVA"],
        filas=[
            [
                tarifa["codigo_iva"],
                f"{tarifa['porcentaje']}%",
                tarifa["base_imponible"],
                tarifa["valor_iva"],
            ]
            for tarifa in reporte["tarifas"]
        ],
        totales=["", "TOTAL", reporte["base_total"], reporte["iva_total"]],
        nota="Solo comprobantes autorizados por el SRI.",
    )


def _tabla_retenciones(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.retenciones_emitidas(sesion, periodo)
    etiqueta = reporte["periodo_fiscal"]

    return Tabla(
        nombre=f"retenciones-{etiqueta.replace('/', '-')}",
        titulo="Retenciones emitidas",
        subtitulo=f"Período fiscal {etiqueta}",
        cabeceras=["Impuesto", "Concepto", "Líneas", "Base imponible", "Retenido"],
        filas=[
            [
                concepto["codigo_impuesto"],
                concepto["codigo_retencion"],
                concepto["lineas"],
                concepto["base_imponible"],
                concepto["valor_retenido"],
            ]
            for concepto in reporte["conceptos"]
        ],
        totales=["", "TOTAL", "", "", reporte["total_retenido"]],
        nota=f"{reporte['comprobantes']} comprobantes de retención autorizados.",
    )


def _tabla_ventas(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    resumen = servicio.resumen_ventas(sesion, periodo)

    return Tabla(
        nombre=f"ventas-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Ventas por tipo de comprobante",
        subtitulo=_rotulo(periodo),
        cabeceras=["Tipo de comprobante", "Cantidad", "Total"],
        filas=[
            [fila["tipo"], fila["cantidad"], fila["total"]]
            for fila in servicio.ventas_por_tipo(sesion, periodo)
        ],
        totales=["TOTAL", resumen["comprobantes"], resumen["total"]],
        nota=f"Ticket promedio: {resumen['ticket_promedio']:.2f}",
    )


def _tabla_egresos(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.egresos_por_tipo(sesion, periodo)

    return Tabla(
        nombre=f"egresos-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Egresos por tipo de gasto",
        subtitulo=_rotulo(periodo),
        cabeceras=["Tipo de gasto", "Deducible", "Gastos", "Subtotal", "IVA", "Total"],
        filas=[
            [
                fila["tipo"],
                "Sí" if fila["deducible"] else "No",
                fila["gastos"],
                fila["subtotal"],
                fila["iva"],
                fila["total"],
            ]
            for fila in reporte["tipos"]
        ],
        totales=["TOTAL", "", "", "", reporte["iva_soportado"], reporte["total"]],
        nota=f"Deducible: {reporte['total_deducible']:.2f} — "
             f"Pagado en el período: {reporte['total_pagado']:.2f}",
    )


def _tabla_notas(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.notas_credito_debito(sesion, periodo)

    return Tabla(
        nombre=f"notas-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Notas de crédito y débito",
        subtitulo=_rotulo(periodo),
        cabeceras=[
            "Número", "Tipo", "Fecha", "Receptor", "Documento modificado", "Motivo", "Total",
        ],
        filas=[
            [
                documento["numero"],
                documento["tipo"],
                documento["fecha"],
                documento["receptor"],
                documento["documento_modificado"],
                documento["motivo"],
                documento["total"],
            ]
            for documento in reporte["documentos"]
        ],
        # Sin fila de totales: la nota de crédito resta y la de débito suma, así
        # que una columna "Total" sumada de arriba abajo no significaría nada.
        nota=f"Crédito: {reporte['notas_credito']} por {reporte['total_credito']:.2f} — "
             f"Débito: {reporte['notas_debito']} por {reporte['total_debito']:.2f} — "
             f"Neto: {reporte['neto']:.2f}",
    )


def _tabla_inventario(sesion: Session, solo_con_stock: bool) -> Tabla:
    reporte = servicio.inventario(sesion, solo_con_stock)

    return Tabla(
        nombre="inventario",
        titulo="Inventario",
        subtitulo=(
            "Solo artículos con existencias" if solo_con_stock else "Todos los artículos activos"
        ),
        cabeceras=[
            "Código", "Nombre", "Tipo", "Categoría", "Unidad", "Stock", "Costo",
            "Precio", "Valor al costo", "Bajo mínimo",
        ],
        filas=[
            [
                a["codigo"],
                a["nombre"],
                a["tipo"],
                a["categoria"],
                a["unidad"],
                "" if a["stock"] is None else a["stock"],
                a["costo"],
                a["precio"],
                a["valor"],
                "Sí" if a["bajo_minimo"] else "",
            ]
            for a in reporte["articulos"]
        ],
        totales=["", "TOTAL", "", "", "", "", "", "", reporte["valor_inventario"], ""],
        nota=f"{reporte['productos']} productos y {reporte['servicios']} servicios; "
             f"{reporte['bajo_minimo']} bajo mínimo. El valor es al costo, no al precio de venta.",
    )


def _tabla_receptores(sesion: Session, rol: str | None) -> Tabla:
    reporte = servicio.receptores(sesion, rol)

    return Tabla(
        nombre="receptores",
        titulo="Receptores",
        subtitulo=(f"Rol: {rol}" if rol else "Clientes, proveedores y transportistas"),
        cabeceras=[
            "Razón social", "Tipo", "Identificación", "Rol", "Correo", "Teléfono", "Facturado",
        ],
        filas=[
            [r["razon_social"], r["tipo_identificacion"], r["identificacion"],
             r["rol"], r["correo"], r["telefono"], r["facturado"]]
            for r in reporte["receptores"]
        ],
        nota=f"{reporte['clientes']} clientes, {reporte['proveedores']} proveedores y "
             f"{reporte['transportistas']} transportistas.",
    )


def _tabla_notas_venta(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.notas_de_venta(sesion, periodo)

    return Tabla(
        nombre=f"notas-venta-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Notas de venta",
        subtitulo=_rotulo(periodo),
        cabeceras=["Razón social", "Identificación", "Comprobantes", "Total"],
        filas=[
            [r["razon_social"], r["identificacion"], r["comprobantes"], r["total"]]
            for r in reporte["receptores"]
        ],
        totales=["", "TOTAL", reporte["comprobantes"], reporte["total"]],
    )


def _tabla_cotizaciones(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.cotizaciones(sesion, periodo)

    return Tabla(
        nombre=f"cotizaciones-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Cotizaciones",
        subtitulo=_rotulo(periodo),
        cabeceras=["Razón social", "Identificación", "Cotizaciones", "Total", "¿Facturó?"],
        filas=[
            [
                r["razon_social"],
                r["identificacion"],
                r["comprobantes"],
                r["total"],
                "Sí" if r["con_factura"] else "No",
            ]
            for r in reporte["receptores"]
        ],
        totales=["", "TOTAL", reporte["comprobantes"], reporte["total"], ""],
        nota=f"{reporte['receptores_con_factura']} receptores cotizados tienen además una "
             "factura autorizada en el período. La cotización no se transmite al SRI.",
    )


def _tabla_estado_sri(sesion: Session, periodo: servicio.Periodo) -> Tabla:
    reporte = servicio.estado_sri(sesion, periodo)

    return Tabla(
        nombre=f"estado-sri-{periodo.desde:%Y-%m-%d}-a-{periodo.hasta:%Y-%m-%d}",
        titulo="Estado ante el SRI",
        subtitulo=_rotulo(periodo),
        cabeceras=["Estado", "Comprobantes"],
        filas=[[fila["estado"], fila["cantidad"]] for fila in reporte["por_estado"]],
        totales=["TOTAL", reporte["total"]],
        nota=f"{reporte['requieren_atencion']} comprobantes requieren atención "
             "(borrador, pendiente, devuelto, rechazado o con error).",
    )


# --- CSV -------------------------------------------------------------------


@router.get("/iva/csv")
def iva_csv(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    return _descargar_csv(_tabla_iva(sesion, _periodo(anio, mes)))


@router.get("/retenciones/csv")
def retenciones_csv(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    return _descargar_csv(_tabla_retenciones(sesion, _periodo(anio, mes)))


@router.get("/ventas/csv")
def ventas_csv(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_csv(_tabla_ventas(sesion, _periodo(anio, mes)))


@router.get("/egresos/csv")
def egresos_csv(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_csv(_tabla_egresos(sesion, _periodo(anio, mes)))


@router.get("/notas/csv")
def notas_csv(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_csv(_tabla_notas(sesion, _periodo(anio, mes)))


@router.get("/inventario/csv")
def inventario_csv(sesion: Session = Depends(obtener_sesion), solo_con_stock: bool = False):
    return _descargar_csv(_tabla_inventario(sesion, solo_con_stock))


@router.get("/receptores/csv")
def receptores_csv(sesion: Session = Depends(obtener_sesion), rol: str | None = None):
    return _descargar_csv(_tabla_receptores(sesion, rol))


# --- PDF -------------------------------------------------------------------


@router.get("/iva/pdf")
def iva_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_iva(sesion, _periodo(anio, mes)))


@router.get("/retenciones/pdf")
def retenciones_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int = Query(..., ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_retenciones(sesion, _periodo(anio, mes)))


@router.get("/ventas/pdf")
def ventas_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_ventas(sesion, _periodo(anio, mes)))


@router.get("/egresos/pdf")
def egresos_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_egresos(sesion, _periodo(anio, mes)))


@router.get("/notas/pdf")
def notas_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_notas(sesion, _periodo(anio, mes)))


@router.get("/inventario/pdf")
def inventario_pdf(sesion: Session = Depends(obtener_sesion), solo_con_stock: bool = False):
    return _descargar_pdf(sesion, _tabla_inventario(sesion, solo_con_stock))


@router.get("/receptores/pdf")
def receptores_pdf(sesion: Session = Depends(obtener_sesion), rol: str | None = None):
    return _descargar_pdf(sesion, _tabla_receptores(sesion, rol))


@router.get("/notas-venta/pdf")
def notas_venta_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_notas_venta(sesion, _periodo(anio, mes)))


@router.get("/cotizaciones/pdf")
def cotizaciones_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_cotizaciones(sesion, _periodo(anio, mes)))


@router.get("/estado-sri/pdf")
def estado_sri_pdf(
    sesion: Session = Depends(obtener_sesion),
    anio: int | None = None,
    mes: int | None = Query(None, ge=1, le=12),
):
    return _descargar_pdf(sesion, _tabla_estado_sri(sesion, _periodo(anio, mes)))
