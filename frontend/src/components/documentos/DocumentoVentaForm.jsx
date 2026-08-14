import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Search,
  Plus,
  Trash2,
  AlertTriangle,
  PackageOpen,
  UserRound,
  Loader2,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useCatalogos } from '../../hooks/useCatalogos';
import { crearDocumento, emitirAlSri, TIPOS } from '../../api/documentos';
import {
  calcularComprobante,
  validarComprobante,
  formatearMoneda,
} from '../../lib/sri/calculoComprobante';
import { TARIFAS_IVA, TARIFA_IVA_POR_DEFECTO } from '../../lib/sri/impuestos';
import { AvisoDemo } from '../ui/EstadoCarga';
import styles from './DocumentoVentaForm.module.css';

/**
 * Formulario de documento de venta, compartido por Factura, Cotización, Nota
 * de Venta, Liquidación de Compra y Notas de Crédito/Débito. Todos tienen la
 * misma estructura —receptor, grilla de ítems y totales— y cambian la
 * cabecera, el botón principal, si desglosan IVA y las reglas de su tipo.
 *
 * Nota de Venta (RIMPE Negocio Popular) no desglosa IVA: se fuerza tarifa 0%
 * y se oculta la columna, en vez de dejar al usuario elegir una tarifa que el
 * régimen no admite.
 */

const FORMAS_PAGO = [
  { codigo: '01', nombre: '01 - Sin utilización del sistema financiero' },
  { codigo: '16', nombre: '16 - Tarjeta de débito' },
  { codigo: '19', nombre: '19 - Tarjeta de crédito' },
  { codigo: '20', nombre: '20 - Otros con utilización del sistema financiero' },
];

let contadorLineas = 0;
const nuevoIdLinea = () => `linea-${++contadorLineas}`;

const lineaDesdeArticulo = (articulo, tarifaForzada) => ({
  id: nuevoIdLinea(),
  articuloId: articulo.id,
  codigo: articulo.codigo,
  descripcion: articulo.nombre,
  cantidad: '1',
  precioUnitario: String(articulo.precio),
  descuentoPorcentaje: '0',
  codigoIva: tarifaForzada ?? articulo.codigoIva ?? TARIFA_IVA_POR_DEFECTO,
});

const lineaLibre = (tarifaForzada) => ({
  id: nuevoIdLinea(),
  articuloId: null,
  codigo: '',
  descripcion: '',
  cantidad: '1',
  precioUnitario: '0',
  descuentoPorcentaje: '0',
  codigoIva: tarifaForzada ?? TARIFA_IVA_POR_DEFECTO,
});

export default function DocumentoVentaForm({
  tipo,
  titulo,
  subtitulo,
  rutaVolver,
  banner,
  accionPrincipal,
  desglosaIva = true,
  tarifaForzada = null,
  camposExtra = null,
  muestraFormaPago = true,
  // La liquidación de compra se emite contra un proveedor, no un cliente.
  rolReceptor = null,
  etiquetaReceptor = 'Receptor',
  accionesSecundarias = null,
  // Datos propios del tipo que se envían al guardar (validez, referencia…).
  datosExtra = {},
  // Reglas del tipo que deben cumplirse antes de poder guardar.
  erroresExtra = [],
}) {
  const navegar = useNavigate();
  const catalogos = useCatalogos();

  const [lineas, setLineas] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [buscadorEnfocado, setBuscadorEnfocado] = useState(false);

  const [busquedaCliente, setBusquedaCliente] = useState('');
  const [clienteEnfocado, setClienteEnfocado] = useState(false);
  const [cliente, setCliente] = useState(null);
  const [correoEnvio, setCorreoEnvio] = useState('');
  const [formaPago, setFormaPago] = useState(FORMAS_PAGO[0].codigo);

  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState(null);
  const [guardado, setGuardado] = useState(null);

  const resultadosArticulos = useMemo(
    () => catalogos.buscarArticulos(busqueda),
    [catalogos, busqueda],
  );

  const resultadosClientes = useMemo(
    () => catalogos.buscarReceptores(busquedaCliente, rolReceptor),
    [catalogos, busquedaCliente, rolReceptor],
  );

  const documento = useMemo(() => calcularComprobante(lineas), [lineas]);
  const validacionBase = useMemo(() => validarComprobante(documento), [documento]);

  const validacion = useMemo(() => {
    const errores = [...validacionBase.errores, ...erroresExtra];
    if (!cliente) errores.push(`Selecciona el ${etiquetaReceptor.toLowerCase()} del documento.`);
    return { esValido: errores.length === 0, errores };
  }, [validacionBase, cliente, etiquetaReceptor, erroresExtra]);

  const seleccionarCliente = (receptor) => {
    setCliente(receptor);
    setCorreoEnvio(receptor.correo ?? '');
    setBusquedaCliente('');
  };

  const agregarArticulo = (articulo) => {
    setLineas((actuales) => {
      const existente = actuales.find((linea) => linea.articuloId === articulo.id);
      if (!existente) return [...actuales, lineaDesdeArticulo(articulo, tarifaForzada)];

      return actuales.map((linea) =>
        linea.id === existente.id
          ? { ...linea, cantidad: String((Number(linea.cantidad) || 0) + 1) }
          : linea,
      );
    });
    setBusqueda('');
  };

  const actualizarLinea = (id, campo, valor) =>
    setLineas((actuales) =>
      actuales.map((linea) => (linea.id === id ? { ...linea, [campo]: valor } : linea)),
    );

  const eliminarLinea = (id) =>
    setLineas((actuales) => actuales.filter((linea) => linea.id !== id));

  // La cotización es el único tipo que no viaja al SRI; el resto sí se emite.
  const emiteAlSri = tipo !== TIPOS.COTIZACION;

  // Guarda el documento como borrador, sin transmitirlo al SRI.
  const guardarBorrador = async () => {
    setGuardando(true);
    setErrorGuardado(null);

    try {
      const { datos } = await crearDocumento({
        tipo,
        receptorId: cliente.id,
        formaPago,
        lineas,
        ...datosExtra,
      });
      setGuardado(datos);
      // Se deja un momento el mensaje de éxito antes de volver al listado.
      setTimeout(() => navegar(rutaVolver), 1400);
    } catch (fallo) {
      setErrorGuardado(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  // Acción principal: crea el documento y, si es un comprobante electrónico,
  // lo transmite al SRI en el mismo paso (el botón dice "Emitir al SRI").
  const guardar = async () => {
    setGuardando(true);
    setErrorGuardado(null);

    try {
      const { datos } = await crearDocumento({
        tipo,
        receptorId: cliente.id,
        formaPago,
        lineas,
        ...datosExtra,
      });

      if (!emiteAlSri) {
        setGuardado(datos);
        setTimeout(() => navegar(rutaVolver), 1400);
        return;
      }

      // El borrador ya quedó creado; si la transmisión falla, la traza del
      // documento permite ver el motivo y reintentar sin perder el trabajo.
      try {
        await emitirAlSri(datos.id);
      } catch {
        /* el estado real (Devuelto/Error/Pendiente) se muestra en la traza */
      }
      navegar(`/comprobantes/${datos.id}`);
    } catch (fallo) {
      setErrorGuardado(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  const IconoAccion = accionPrincipal.icono;
  // Sin backend los ids del catálogo no existen allí: guardar fallaría.
  const puedeGuardar = validacion.esValido && !catalogos.usandoDemo && !guardando && !guardado;

  const [tabIdx, setTabIdx] = useState(0);
  const hoy = new Date().toISOString().slice(0, 10);
  const tabDefs = [
    { n: 1, label: 'Documento', short: 'Documento' },
    { n: 2, label: 'Receptor', short: 'Receptor' },
    { n: 3, label: 'Productos', short: 'Productos' },
    { n: 4, label: 'Pago', short: 'Pago' },
    { n: 5, label: 'Notas', short: 'Notas' },
  ];

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <Link to={rutaVolver} className={styles.btnIcon} aria-label="Volver">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className={styles.title}>{titulo}</h1>
            <p className={styles.subtitle}>{subtitulo}</p>
          </div>
        </div>
        <div className={styles.headerActions}>
          {accionesSecundarias}
          {/* Asistente por pasos: se avanza con Siguiente y solo en el último
              paso aparecen Guardar borrador / Emitir, como en el diseño. */}
          {tabIdx > 0 && !guardado && (
            <button
              className={styles.btnSecondary}
              onClick={() => setTabIdx((i) => Math.max(0, i - 1))}
              disabled={guardando}
            >
              <ChevronLeft size={18} /> Anterior
            </button>
          )}
          {tabIdx < tabDefs.length - 1 ? (
            <button
              className={styles.btnPrimary}
              onClick={() => setTabIdx((i) => Math.min(tabDefs.length - 1, i + 1))}
              disabled={guardando || Boolean(guardado)}
            >
              Siguiente <ChevronRight size={18} />
            </button>
          ) : (
            <>
              <button
                className={styles.btnSecondary}
                onClick={guardarBorrador}
                disabled={!puedeGuardar}
                title={
                  catalogos.usandoDemo
                    ? 'Sin conexión con el servidor: no se puede guardar.'
                    : validacion.esValido
                      ? 'Guarda el documento como borrador, sin enviarlo al SRI.'
                      : validacion.errores[0]
                }
              >
                <Save size={18} /> Guardar borrador
              </button>
              <button
                className={styles.btnPrimary}
                onClick={guardar}
                disabled={!puedeGuardar}
                title={
                  catalogos.usandoDemo
                    ? 'Sin conexión con el servidor: no se puede guardar.'
                    : validacion.esValido
                      ? undefined
                      : validacion.errores[0]
                }
              >
                {guardando ? (
                  <>
                    <Loader2 size={18} className={styles.girando} /> Guardando…
                  </>
                ) : (
                  <>
                    <IconoAccion size={18} /> {accionPrincipal.texto}
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Banner SRI */}
      <div className={styles.badgeEntrega}>
        <span className={styles.badgeIcon}><CheckCircle2 size={18} /></span>
        <span>Este Comprobante Electrónico <strong>Se Entregará</strong> a los servidores de SRI.</span>
      </div>

      {/* Tabs mockup */}
      <div className={styles.tabsBar}>
        {tabDefs.map((t, idx) => {
          const activo = idx === tabIdx;
          return (
            <button key={t.label} onClick={() => setTabIdx(idx)} className={styles.tab} data-activo={activo ? 'true' : 'false'}>
              <span className={styles.tabNum} data-activo={activo ? 'true' : 'false'}>{t.n}</span>
              {t.label}
            </button>
          );
        })}
      </div>

      {catalogos.usandoDemo && <AvisoDemo />}

      {guardado ? (
        <div className={styles.exito}>
          <CheckCircle2 size={20} />
          <span>
            {guardado.tipo} <strong>{guardado.numero}</strong> creada por{' '}
            <strong>{formatearMoneda(guardado.importe_total)}</strong>. Volviendo al listado…
          </span>
        </div>
      ) : (
        <div className={`${styles.banner} ${styles[`banner${banner.tono}`]}`}>{banner.texto}</div>
      )}

      {errorGuardado && (
        <div className={styles.errorGuardado}>
          <AlertTriangle size={18} />
          <span>{errorGuardado}</span>
        </div>
      )}

      {/* Contenido por tab */}
      <div className={styles.tabPanels}>
        {tabIdx === 0 && (
          <div className={`${styles.sectionPanel} glass-panel`}>
            <div className={styles.docHeader}>
              <div>
                <label className={styles.grupo}><span>Empresa Sucursal</span><select className={styles.input}><option>Matriz</option></select></label>
                <div style={{ marginTop: 16, lineHeight: 1.65 }}><div style={{ fontSize: 17, fontWeight: 800 }}>Empresa</div><div className={`cifra ${styles.rucEmpresa}`}>RUC —</div></div>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 12, minWidth: 210 }}>
                <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: '-0.5px' }}>{titulo}</div>
                <div className={styles.fedPill}><span>FED</span><span className={`cifra ${styles.fedVal}`}>{hoy}</span></div>
                <label className={styles.grupo} style={{ width: 200 }}><span>Fecha Emisión</span><input className={styles.input} value={hoy} readOnly style={{ textAlign: 'right' }} /></label>
              </div>
            </div>
          </div>
        )}
        {tabIdx !== 1 && tabIdx !== 2 && tabIdx !== 3 && tabIdx >= 4 ? null : null}
      </div>

      {/* Solo visible según tab: 0=Documento ya arriba, 1=Receptor, 2=Productos, 3=Pago, 4=Notas */}
      <div className={styles.mainLayout} style={{ display: tabIdx === 1 || tabIdx === 2 || tabIdx === 3 ? 'grid' : 'none' }}>
        <div
          className={styles.leftCol}
          style={{ display: tabIdx === 1 || tabIdx === 2 || tabIdx === 3 ? 'flex' : 'none' }}
        >
          {/* 1. Receptor */}
          <motion.div
            className={`${styles.sectionPanel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{ display: tabIdx === 1 ? 'block' : 'none' }}
          >
            <h3 className={styles.sectionTitle}>1. {etiquetaReceptor}</h3>

            <div className={styles.buscadorWrapper}>
              <div className={styles.buscadorCampo}>
                <Search size={18} className={styles.buscadorIcono} />
                <input
                  className={styles.input}
                  placeholder="Buscar por identificación o razón social…"
                  value={busquedaCliente}
                  onChange={(evento) => setBusquedaCliente(evento.target.value)}
                  onFocus={() => setClienteEnfocado(true)}
                  onBlur={() => setClienteEnfocado(false)}
                  onKeyDown={(evento) => {
                    if (evento.key === 'Escape') setBusquedaCliente('');
                    if (evento.key === 'Enter' && resultadosClientes.length > 0) {
                      evento.preventDefault();
                      seleccionarCliente(resultadosClientes[0]);
                    }
                  }}
                />
              </div>

              {clienteEnfocado && busquedaCliente.trim() !== '' && (
                <ul className={`${styles.resultados} glass-panel`}>
                  {resultadosClientes.length === 0 && (
                    <li className={styles.sinResultados}>Sin coincidencias</li>
                  )}
                  {resultadosClientes.map((receptor) => (
                    <li key={receptor.id}>
                      {/* onMouseDown, no onClick: se dispara antes del blur del input */}
                      <button
                        type="button"
                        className={styles.resultadoCliente}
                        onMouseDown={(evento) => {
                          evento.preventDefault();
                          seleccionarCliente(receptor);
                        }}
                      >
                        <span className={styles.resultadoNombre}>{receptor.razonSocial}</span>
                        <span className={styles.resultadoCodigo}>{receptor.identificacion}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {cliente ? (
              <div className={styles.clientePreview}>
                <div className={styles.clienteFila}>
                  <span className={styles.etiqueta}>{etiquetaReceptor}</span>
                  <span className={styles.valor}>{cliente.razonSocial}</span>
                </div>
                <div className={styles.clienteFila}>
                  <span className={styles.etiqueta}>{cliente.tipoIdentificacion}</span>
                  <span className={styles.valor}>{cliente.identificacion}</span>
                </div>
                <div className={styles.grupo} style={{ marginTop: 12 }}>
                  <label htmlFor="correoEnvio">Correo para envío</label>
                  <input
                    id="correoEnvio"
                    type="email"
                    className={styles.input}
                    value={correoEnvio}
                    onChange={(evento) => setCorreoEnvio(evento.target.value)}
                  />
                </div>
                <button className={styles.btnQuitar} onClick={() => setCliente(null)}>
                  Cambiar {etiquetaReceptor.toLowerCase()}
                </button>
              </div>
            ) : (
              <div className={styles.vacioCompacto}>
                <UserRound size={24} />
                <p>Ningún {etiquetaReceptor.toLowerCase()} seleccionado.</p>
              </div>
            )}

            {camposExtra}
          </motion.div>

          {/* 2. Detalle */}
          <motion.div
            className={`${styles.sectionPanel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            style={{ display: tabIdx === 2 ? 'block' : 'none' }}
          >
            <h3 className={styles.sectionTitle}>2. Productos y servicios</h3>

            <div className={styles.buscadorWrapper}>
              <div className={styles.filaBuscador}>
                <div className={styles.buscadorCampo}>
                  <Search size={18} className={styles.buscadorIcono} />
                  <input
                    className={styles.input}
                    placeholder="Buscar código o nombre de artículo…"
                    value={busqueda}
                    onChange={(evento) => setBusqueda(evento.target.value)}
                    onFocus={() => setBuscadorEnfocado(true)}
                    onBlur={() => setBuscadorEnfocado(false)}
                    onKeyDown={(evento) => {
                      if (evento.key === 'Escape') setBusqueda('');
                      if (evento.key === 'Enter' && resultadosArticulos.length > 0) {
                        evento.preventDefault();
                        agregarArticulo(resultadosArticulos[0]);
                      }
                    }}
                  />
                </div>
                <button
                  className={styles.btnSecundarioCompacto}
                  onClick={() => setLineas((actuales) => [...actuales, lineaLibre(tarifaForzada)])}
                >
                  <Plus size={18} /> Línea libre
                </button>
              </div>

              {buscadorEnfocado && busqueda.trim() !== '' && (
                <ul className={`${styles.resultados} glass-panel`}>
                  {resultadosArticulos.length === 0 && (
                    <li className={styles.sinResultados}>Sin coincidencias</li>
                  )}
                  {resultadosArticulos.map((articulo) => (
                    <li key={articulo.id}>
                      <button
                        type="button"
                        className={styles.resultadoItem}
                        onMouseDown={(evento) => {
                          evento.preventDefault();
                          agregarArticulo(articulo);
                        }}
                      >
                        <span className={styles.resultadoCodigo}>{articulo.codigo}</span>
                        <span className={styles.resultadoNombre}>{articulo.nombre}</span>
                        <span className={styles.resultadoPrecio}>
                          {formatearMoneda(articulo.precio)}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {lineas.length === 0 ? (
              <div className={styles.vacio}>
                <PackageOpen size={32} />
                <p>Aún no hay ítems en este documento.</p>
                <span>Búscalos arriba o agrega una línea libre.</span>
              </div>
            ) : (
              <div className={styles.gridWrapper}>
                <table className={styles.itemsTable}>
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Descripción</th>
                      <th width="90">Cant.</th>
                      <th width="110">P. Unitario</th>
                      <th width="90">% Desc</th>
                      {desglosaIva && <th width="130">IVA</th>}
                      <th width="110">Total</th>
                      <th width="48" aria-label="Acciones"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {/* Se itera sobre `lineas` (texto crudo del input) y se toma el
                        cálculo por índice: calcularComprobante conserva el orden 1:1. */}
                    {lineas.map((linea, indice) => {
                      const detalle = documento.detalles[indice];
                      return (
                        <tr key={linea.id}>
                          <td>
                            <input
                              className={styles.gridInput}
                              value={linea.codigo}
                              placeholder="Código"
                              onChange={(e) => actualizarLinea(linea.id, 'codigo', e.target.value)}
                            />
                          </td>
                          <td>
                            <input
                              className={styles.gridInput}
                              value={linea.descripcion}
                              placeholder="Descripción del ítem"
                              onChange={(e) =>
                                actualizarLinea(linea.id, 'descripcion', e.target.value)
                              }
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              className={`${styles.gridInput} ${styles.gridInputNumero}`}
                              value={linea.cantidad}
                              onChange={(e) =>
                                actualizarLinea(linea.id, 'cantidad', e.target.value)
                              }
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              className={`${styles.gridInput} ${styles.gridInputNumero}`}
                              value={linea.precioUnitario}
                              onChange={(e) =>
                                actualizarLinea(linea.id, 'precioUnitario', e.target.value)
                              }
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              className={`${styles.gridInput} ${styles.gridInputNumero}`}
                              value={linea.descuentoPorcentaje}
                              onChange={(e) =>
                                actualizarLinea(linea.id, 'descuentoPorcentaje', e.target.value)
                              }
                            />
                          </td>
                          {desglosaIva && (
                            <td>
                              <select
                                className={styles.gridSelect}
                                value={detalle.tarifa.codigo}
                                onChange={(e) =>
                                  actualizarLinea(linea.id, 'codigoIva', e.target.value)
                                }
                              >
                                {TARIFAS_IVA.map((tarifa) => (
                                  <option key={tarifa.codigo} value={tarifa.codigo}>
                                    {tarifa.nombre}
                                  </option>
                                ))}
                              </select>
                            </td>
                          )}
                          <td className={styles.itemTotal}>
                            {formatearMoneda(detalle.total)}
                            {detalle.descuento > 0 && (
                              <span className={styles.itemDescuento}>
                                -{formatearMoneda(detalle.descuento)}
                              </span>
                            )}
                          </td>
                          <td>
                            <button
                              className={styles.btnDelete}
                              onClick={() => eliminarLinea(linea.id)}
                              aria-label={`Eliminar ${linea.descripcion || 'línea'}`}
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </motion.div>

          {muestraFormaPago && tabIdx === 3 && (
            <motion.div
              className={`${styles.sectionPanel} glass-panel`}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <h3 className={styles.sectionTitle}>3. Forma de pago</h3>
              <div className={styles.grupo}>
                <label htmlFor="formaPago">Medio de pago</label>
                <select
                  id="formaPago"
                  className={styles.input}
                  value={formaPago}
                  onChange={(evento) => setFormaPago(evento.target.value)}
                >
                  {FORMAS_PAGO.map((forma) => (
                    <option key={forma.codigo} value={forma.codigo}>
                      {forma.nombre}
                    </option>
                  ))}
                </select>
              </div>
            </motion.div>
          )}
        </div>

        {/* Totales - visible en todos los tabs */}
        <div className={styles.rightCol} style={{ display: tabIdx === 4 ? 'none' : 'block' }}>
          <motion.div
            className={`${styles.totalsPanel} glass-panel`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className={styles.sectionTitle}>Resumen</h3>

            <div className={styles.totalsGroup}>
              {documento.impuestos.length === 0 ? (
                <div className={styles.totalRow}>
                  <span>Subtotal</span>
                  <span>{formatearMoneda(0)}</span>
                </div>
              ) : (
                documento.impuestos.map((grupo) => (
                  <div className={styles.totalRow} key={`base-${grupo.codigoPorcentaje}`}>
                    <span>Subtotal {desglosaIva ? grupo.tarifa.etiquetaCorta : ''}</span>
                    <span>{formatearMoneda(grupo.baseImponible)}</span>
                  </div>
                ))
              )}

              <div className={styles.totalRow}>
                <span>Descuento</span>
                <span>
                  {documento.totalDescuento > 0 ? '-' : ''}
                  {formatearMoneda(documento.totalDescuento)}
                </span>
              </div>

              <div className={styles.divider}></div>

              <div className={styles.totalRow}>
                <span>Subtotal sin impuestos</span>
                <span>{formatearMoneda(documento.totalSinImpuestos)}</span>
              </div>

              {desglosaIva &&
                documento.impuestos
                  .filter((grupo) => grupo.tarifa.porcentaje > 0)
                  .map((grupo) => (
                    <div className={styles.totalRow} key={`iva-${grupo.codigoPorcentaje}`}>
                      <span>IVA {grupo.tarifa.etiquetaCorta}</span>
                      <span>{formatearMoneda(grupo.valor)}</span>
                    </div>
                  ))}

              <div className={styles.divider}></div>

              <div className={styles.totalRowGrand}>
                <span>Total</span>
                <span className={styles.grandTotal}>
                  {formatearMoneda(documento.importeTotal)}
                </span>
              </div>
            </div>

            {!validacion.esValido && (
              <div className={styles.alertas}>
                {validacion.errores.map((error) => (
                  <p className={styles.alerta} key={error}>
                    <AlertTriangle size={16} />
                    <span>{error}</span>
                  </p>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>

      {tabIdx === 4 && (
        <div className={`${styles.sectionPanel} glass-panel`} style={{ marginTop: 4 }}>
          <h3 className={styles.sectionTitle}>Notas</h3>
          <div className={styles.grupo}><label>Observaciones</label><textarea className={styles.input} rows={4} placeholder="Notas internas o pie del documento" /></div>
        </div>
      )}
    </div>
  );
}
