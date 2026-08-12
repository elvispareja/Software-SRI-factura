"""Endpoints de configuración de la empresa emisora."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..base_datos import obtener_sesion
from ..seguridad import administrador_actual
from ..esquemas import (
    ImpuestoCatalogo,
    ListaAuxiliarEntrada,
    ListaAuxiliarSalida,
    UsuarioListado,
    CuentaBancariaEntrada,
    CuentaBancariaSalida,
    EmpresaEntrada,
    EmpresaSalida,
    EstablecimientoEntrada,
    EstablecimientoSalida,
    FirmaSalida,
)
from ..modelos_db import (
    ListaAuxiliar,
    Usuario,
    CuentaBancaria,
    Empresa,
    Establecimiento,
    FirmaElectronica,
    PuntoEmision,
)
from ..servicios.cifrado import cifrar
from ..sri.firma import ErrorFirma, cargar_p12

router = APIRouter(prefix="/configuracion", tags=["configuración"])
registro = logging.getLogger(__name__)

# 5 MB: un .p12 legítimo pesa unos pocos KB. El límite evita que una subida
# accidental de otro archivo llene la base de datos.
TAMANO_MAXIMO_P12 = 5 * 1024 * 1024


def _empresa(sesion: Session) -> Empresa:
    empresa = sesion.scalars(
        select(Empresa).options(selectinload(Empresa.establecimientos)).limit(1)
    ).first()
    if empresa is None:
        raise HTTPException(404, "No hay empresa configurada.")
    return empresa


@router.get("/empresa", response_model=EmpresaSalida)
def obtener_empresa(sesion: Session = Depends(obtener_sesion)):
    return _empresa(sesion)


@router.put("/empresa", response_model=EmpresaSalida)
def guardar_empresa(
    datos: EmpresaEntrada,
    sesion: Session = Depends(obtener_sesion),
    _admin: Usuario = Depends(administrador_actual),
):
    """Crea la empresa si no existe; el sistema es de un solo emisor por ahora."""
    empresa = sesion.scalars(select(Empresa).limit(1)).first()

    if empresa is None:
        empresa = Empresa(**datos.model_dump())
        sesion.add(empresa)
    else:
        for campo, valor in datos.model_dump().items():
            setattr(empresa, campo, valor)

    sesion.commit()
    sesion.refresh(empresa)
    return empresa


@router.get("/establecimientos", response_model=list[EstablecimientoSalida])
def listar_establecimientos(sesion: Session = Depends(obtener_sesion)):
    empresa = _empresa(sesion)
    return sesion.scalars(
        select(Establecimiento)
        .options(selectinload(Establecimiento.puntos_emision))
        .where(Establecimiento.empresa_id == empresa.id)
        .order_by(Establecimiento.codigo)
    ).all()


@router.post("/establecimientos", response_model=EstablecimientoSalida, status_code=201)
def crear_establecimiento(
    datos: EstablecimientoEntrada, sesion: Session = Depends(obtener_sesion)
):
    empresa = _empresa(sesion)

    duplicado = sesion.scalar(
        select(Establecimiento).where(
            Establecimiento.empresa_id == empresa.id, Establecimiento.codigo == datos.codigo
        )
    )
    if duplicado:
        raise HTTPException(409, f"Ya existe el establecimiento {datos.codigo}.")

    establecimiento = Establecimiento(
        empresa_id=empresa.id,
        codigo=datos.codigo,
        nombre=datos.nombre,
        direccion=datos.direccion,
    )
    for punto in datos.puntos_emision:
        establecimiento.puntos_emision.append(PuntoEmision(**punto.model_dump()))

    sesion.add(establecimiento)
    sesion.commit()
    sesion.refresh(establecimiento)
    return establecimiento


@router.put("/establecimientos/{establecimiento_id}", response_model=EstablecimientoSalida)
def actualizar_establecimiento(
    establecimiento_id: int,
    datos: EstablecimientoEntrada,
    sesion: Session = Depends(obtener_sesion),
):
    """
    Actualiza el establecimiento y sus puntos de emisión.

    Los puntos se emparejan por su código, no por posición: así renombrar o
    reordenar en pantalla no reasigna secuenciales entre cajas distintas, que
    sería la forma más silenciosa de romper la numeración.
    """
    establecimiento = sesion.get(Establecimiento, establecimiento_id)
    if establecimiento is None:
        raise HTTPException(404, "Establecimiento no encontrado.")

    establecimiento.codigo = datos.codigo
    establecimiento.nombre = datos.nombre
    establecimiento.direccion = datos.direccion

    existentes = {punto.codigo: punto for punto in establecimiento.puntos_emision}
    recibidos = {punto.codigo for punto in datos.puntos_emision}

    for entrada in datos.puntos_emision:
        punto = existentes.get(entrada.codigo)
        if punto is None:
            establecimiento.puntos_emision.append(PuntoEmision(**entrada.model_dump()))
            continue

        punto.nombre = entrada.nombre
        # El secuencial solo se puede adelantar: retrocederlo produciría números
        # repetidos y el SRI rechazaría los comprobantes.
        if entrada.secuencial_factura < punto.secuencial_factura:
            raise HTTPException(
                422,
                f"El secuencial del punto {entrada.codigo} no puede retroceder de "
                f"{punto.secuencial_factura} a {entrada.secuencial_factura}: "
                "produciría números repetidos.",
            )
        punto.secuencial_factura = entrada.secuencial_factura

    for codigo, punto in existentes.items():
        if codigo not in recibidos:
            establecimiento.puntos_emision.remove(punto)

    sesion.commit()
    sesion.refresh(establecimiento)
    return establecimiento


@router.delete("/establecimientos/{establecimiento_id}", status_code=204)
def eliminar_establecimiento(
    establecimiento_id: int, sesion: Session = Depends(obtener_sesion)
):
    establecimiento = sesion.get(Establecimiento, establecimiento_id)
    if establecimiento is None:
        raise HTTPException(404, "Establecimiento no encontrado.")

    sesion.delete(establecimiento)
    sesion.commit()


# --------------------------------------------------------------------------
# Cuentas bancarias
# --------------------------------------------------------------------------


@router.get("/cuentas", response_model=list[CuentaBancariaSalida])
def listar_cuentas(sesion: Session = Depends(obtener_sesion)):
    empresa = _empresa(sesion)
    return sesion.scalars(
        select(CuentaBancaria)
        .where(CuentaBancaria.empresa_id == empresa.id, CuentaBancaria.activa.is_(True))
        .order_by(CuentaBancaria.banco)
    ).all()


@router.post("/cuentas", response_model=CuentaBancariaSalida, status_code=201)
def crear_cuenta(datos: CuentaBancariaEntrada, sesion: Session = Depends(obtener_sesion)):
    empresa = _empresa(sesion)

    duplicada = sesion.scalar(
        select(CuentaBancaria).where(
            CuentaBancaria.empresa_id == empresa.id,
            CuentaBancaria.numero == datos.numero,
            CuentaBancaria.activa.is_(True),
        )
    )
    if duplicada:
        raise HTTPException(409, f"Ya existe una cuenta activa con el número {datos.numero}.")

    cuenta = CuentaBancaria(empresa_id=empresa.id, **datos.model_dump())
    sesion.add(cuenta)
    sesion.commit()
    sesion.refresh(cuenta)
    return cuenta


@router.delete("/cuentas/{cuenta_id}", status_code=204)
def desactivar_cuenta(cuenta_id: int, sesion: Session = Depends(obtener_sesion)):
    """No se borra: los RIDE ya emitidos la mencionan."""
    cuenta = sesion.get(CuentaBancaria, cuenta_id)
    if cuenta is None:
        raise HTTPException(404, "Cuenta no encontrada.")
    cuenta.activa = False
    sesion.commit()


# --------------------------------------------------------------------------
# Firma electrónica
# --------------------------------------------------------------------------


@router.get("/firma", response_model=FirmaSalida | None)
def obtener_firma(sesion: Session = Depends(obtener_sesion)):
    """Metadatos del certificado activo. Nunca devuelve el archivo ni la clave."""
    empresa = _empresa(sesion)
    return sesion.scalar(
        select(FirmaElectronica).where(
            FirmaElectronica.empresa_id == empresa.id, FirmaElectronica.activa.is_(True)
        )
    )


@router.post("/firma", response_model=FirmaSalida, status_code=201)
async def subir_firma(
    archivo: UploadFile = File(...),
    contrasena: str = Form(...),
    sesion: Session = Depends(obtener_sesion),
    _admin: Usuario = Depends(administrador_actual),
):
    """
    Sube el certificado .p12/.pfx.

    Se abre con la contraseña recibida **antes de guardar nada**: si no abre, la
    contraseña es incorrecta o el archivo no es un PKCS#12, y es mucho mejor
    descubrirlo aquí que al intentar firmar el primer comprobante.

    Los metadatos se extraen del propio certificado; el usuario no los teclea.
    """
    empresa = _empresa(sesion)

    if not archivo.filename or not archivo.filename.lower().endswith((".p12", ".pfx")):
        raise HTTPException(422, "El certificado debe ser un archivo .p12 o .pfx.")

    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO_P12:
        raise HTTPException(413, "El archivo supera el tamaño máximo permitido (5 MB).")
    if not contenido:
        raise HTTPException(422, "El archivo está vacío.")

    # cargar_p12 lee de disco, así que se escribe a un temporal que se borra
    # enseguida: el certificado no debe quedar en el sistema de archivos.
    import os
    import tempfile

    ruta_temporal = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as temporal:
            temporal.write(contenido)
            ruta_temporal = temporal.name

        firmante = cargar_p12(ruta_temporal, contrasena)
    except ErrorFirma as error:
        # No se registra la contraseña ni el motivo exacto del fallo criptográfico.
        registro.warning("Certificado rechazado para la empresa %s", empresa.id)
        raise HTTPException(422, str(error)) from error
    finally:
        if ruta_temporal:
            os.unlink(ruta_temporal)

    certificado = firmante.certificado

    # Solo un certificado activo a la vez: el que se usa para firmar.
    for anterior in sesion.scalars(
        select(FirmaElectronica).where(
            FirmaElectronica.empresa_id == empresa.id, FirmaElectronica.activa.is_(True)
        )
    ).all():
        anterior.activa = False

    firma = FirmaElectronica(
        empresa_id=empresa.id,
        nombre_archivo=archivo.filename,
        contenido=contenido,
        contrasena_cifrada=cifrar(contrasena),
        propietario=certificado.subject.rfc4514_string(),
        emisor=firmante.emisor,
        numero_serie=str(firmante.numero_serie),
        valida_desde=certificado.not_valid_before_utc.date(),
        valida_hasta=certificado.not_valid_after_utc.date(),
    )
    sesion.add(firma)
    sesion.commit()
    sesion.refresh(firma)
    return firma


@router.delete("/firma", status_code=204)
def quitar_firma(
    sesion: Session = Depends(obtener_sesion),
    _admin: Usuario = Depends(administrador_actual),
):
    empresa = _empresa(sesion)
    firma = sesion.scalar(
        select(FirmaElectronica).where(
            FirmaElectronica.empresa_id == empresa.id, FirmaElectronica.activa.is_(True)
        )
    )
    if firma is None:
        raise HTTPException(404, "No hay certificado configurado.")

    firma.activa = False
    sesion.commit()


# --------------------------------------------------------------------------
# Listas auxiliares: zonas, vendedores y leyendas
#
# Las define el negocio a su gusto. Los catálogos del SRI (tarifas de IVA,
# tipos de identificación, códigos de retención) NO están aquí: los fija la
# ficha técnica y el usuario no puede inventárselos.
# --------------------------------------------------------------------------

TIPOS_LISTA = ("zona", "vendedor", "leyenda")


def _validar_tipo(tipo: str) -> str:
    if tipo not in TIPOS_LISTA:
        raise HTTPException(
            404,
            f"No existe la lista «{tipo}». Las disponibles son: "
            f"{', '.join(TIPOS_LISTA)}.",
        )
    return tipo


@router.get("/listas/{tipo}", response_model=list[ListaAuxiliarSalida])
def listar_lista(
    tipo: str,
    sesion: Session = Depends(obtener_sesion),
    incluir_inactivos: bool = False,
):
    _validar_tipo(tipo)

    consulta = select(ListaAuxiliar).where(ListaAuxiliar.tipo == tipo)
    if not incluir_inactivos:
        consulta = consulta.where(ListaAuxiliar.estado == "Activo")

    return sesion.scalars(consulta.order_by(ListaAuxiliar.nombre)).all()


@router.post("/listas/{tipo}", response_model=ListaAuxiliarSalida, status_code=201)
def crear_en_lista(
    tipo: str,
    datos: ListaAuxiliarEntrada,
    sesion: Session = Depends(obtener_sesion),
):
    _validar_tipo(tipo)

    repetido = sesion.scalar(
        select(ListaAuxiliar).where(
            ListaAuxiliar.tipo == tipo, ListaAuxiliar.nombre == datos.nombre
        )
    )
    if repetido:
        raise HTTPException(409, f"Ya existe «{datos.nombre}» en esta lista.")

    entrada = ListaAuxiliar(tipo=tipo, **datos.model_dump())
    sesion.add(entrada)
    sesion.commit()
    sesion.refresh(entrada)
    return entrada


@router.put("/listas/{tipo}/{entrada_id}", response_model=ListaAuxiliarSalida)
def actualizar_en_lista(
    tipo: str,
    entrada_id: int,
    datos: ListaAuxiliarEntrada,
    sesion: Session = Depends(obtener_sesion),
):
    _validar_tipo(tipo)

    entrada = sesion.get(ListaAuxiliar, entrada_id)
    if entrada is None or entrada.tipo != tipo:
        raise HTTPException(404, "Entrada no encontrada.")

    repetido = sesion.scalar(
        select(ListaAuxiliar).where(
            ListaAuxiliar.tipo == tipo,
            ListaAuxiliar.nombre == datos.nombre,
            ListaAuxiliar.id != entrada_id,
        )
    )
    if repetido:
        raise HTTPException(409, f"Ya existe «{datos.nombre}» en esta lista.")

    for campo, valor in datos.model_dump().items():
        setattr(entrada, campo, valor)

    sesion.commit()
    sesion.refresh(entrada)
    return entrada


@router.delete("/listas/{tipo}/{entrada_id}", status_code=204)
def desactivar_en_lista(tipo: str, entrada_id: int, sesion: Session = Depends(obtener_sesion)):
    """
    Se desactiva, no se borra.

    Los receptores guardan la zona y el vendedor como texto: borrar la entrada
    dejaría registros apuntando a algo que ya no está en la lista.
    """
    _validar_tipo(tipo)

    entrada = sesion.get(ListaAuxiliar, entrada_id)
    if entrada is None or entrada.tipo != tipo:
        raise HTTPException(404, "Entrada no encontrada.")

    entrada.estado = "Inactivo"
    sesion.commit()


# --------------------------------------------------------------------------
# Usuarios e impuestos: solo lectura
# --------------------------------------------------------------------------


@router.get("/usuarios", response_model=list[UsuarioListado])
def listar_usuarios(sesion: Session = Depends(obtener_sesion)):
    """
    Usuarios del sistema.

    Solo lectura: el alta pasa por el registro, que es donde se aplica el
    hash de la contraseña. Un endpoint de creación aquí duplicaría esa lógica.
    """
    return sesion.scalars(select(Usuario).order_by(Usuario.nombre)).all()


@router.get("/impuestos", response_model=list[ImpuestoCatalogo])
def listar_impuestos():
    """
    Tarifas de IVA de la tabla 17 de la ficha técnica.

    No se editan: los códigos viajan literalmente en el XML y cambiarlos hace
    que el SRI rechace el comprobante. Se exponen para que la interfaz pueda
    enseñarlas sin duplicar la tabla.
    """
    from ..sri.modelos import PORCENTAJES_IVA

    nombres = {
        "0": "IVA 0%",
        "2": "IVA 12%",
        "3": "IVA 14%",
        "4": "IVA 15%",
        "5": "IVA 5%",
        "6": "No objeto de impuesto",
        "7": "Exento de IVA",
    }

    return [
        ImpuestoCatalogo(
            codigo=codigo,
            nombre=nombres.get(codigo, f"Código {codigo}"),
            porcentaje=porcentaje,
        )
        for codigo, porcentaje in sorted(PORCENTAJES_IVA.items())
    ]
