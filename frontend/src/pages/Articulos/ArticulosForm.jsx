import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Box, PenTool, Percent, Info, AlertTriangle, AlertCircle } from 'lucide-react';
import {
  precioDesdeUtilidad,
  utilidadDesdePrecio,
  precioConImpuesto,
  utilidadUnitaria,
  estadoStock,
  BASES_UTILIDAD,
} from '../../lib/precios';
import { formatearMoneda, aNumero } from '../../lib/sri/calculoComprobante';
import { TARIFAS_IVA, obtenerTarifaIva, TARIFA_IVA_POR_DEFECTO } from '../../lib/sri/impuestos';
import { api, ErrorApi } from '../../api/cliente';
import { articuloDesdeApi, articuloHaciaApi } from '../../api/adaptadores';
import styles from './Articulos.module.css';

const UNIDADES_MEDIDA = [
  'Unidad', 'Caja', 'Paquete', 'Docena', 'Kilogramo', 'Libra', 'Gramo',
  'Litro', 'Galón', 'Metro', 'Metro cuadrado', 'Saco', 'Quintal',
  'Hora', 'Día', 'Servicio',
];

const TIPOS_CODIFICACION = [
  'Código interno',
  'Código de barras (EAN)',
  'Operadora de transporte',
  'Sin codificación',
];

const OPCIONES_ICE = [
  { codigo: '', nombre: 'No aplica ICE' },
  { codigo: '3011', nombre: 'Cigarrillos rubios' },
  { codigo: '3023', nombre: 'Bebidas alcohólicas' },
  { codigo: '3610', nombre: 'Bebidas gaseosas con azúcar' },
  { codigo: '3620', nombre: 'Bebidas energizantes' },
];

const NIVELES_PRECIO = ['PVP 1', 'PVP 2', 'PVP 3', 'PVP 4', 'PVP 5', 'PVP 6'];
const UTILIDADES_SUGERIDAS = [50, 40, 30, 20, 15, 10];

const PESTANAS = [
  { id: 'basica', etiqueta: 'Información Básica' },
  { id: 'impuestos', etiqueta: 'Impuestos' },
  { id: 'precios', etiqueta: 'Costos y Precios' },
];

const CLASE_STOCK = {
  agotado: styles.stockAgotado,
  critico: styles.stockCritico,
  reorden: styles.stockReorden,
  ok: styles.stockOk,
};

const ARTICULO_INICIAL = {
  codigo: '',
  codigoAuxiliar: '',
  tipoCodificacion: 'Código interno',
  nombre: '',
  unidad: 'Unidad',
  detalle: '',
  categoria: 'Sin categoría',
  marca: '',
  bodega: 'Bodega Principal',
  ubicacion: '',
  codigoIva: TARIFA_IVA_POR_DEFECTO,
  codigoIce: '',
  costo: '10.00',
  stockActual: '0',
  stockMinimo: '5',
  puntoReorden: '10',
  stockMaximo: '100',
};

export default function ArticulosForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const esEdicion = Boolean(id);

  const [pestana, setPestana] = useState('basica');
  const [esServicio, setEsServicio] = useState(false);

  const [articulo, setArticulo] = useState(ARTICULO_INICIAL);

  const [baseUtilidad, setBaseUtilidad] = useState('costo');

  // Cada nivel guarda su % de utilidad; el precio se deriva salvo que el
  // usuario lo escriba, en cuyo caso se recalcula el % (edición bidireccional).
  const [niveles, setNiveles] = useState(() =>
    NIVELES_PRECIO.map((nombre, indice) => ({
      nombre,
      utilidad: String(UTILIDADES_SUGERIDAS[indice]),
      precio: '',
    })),
  );

  const [cargando, setCargando] = useState(Boolean(esEdicion));
  const [errorCarga, setErrorCarga] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [ayudaError, setAyudaError] = useState(null);

  // Precarga en edición: GET /articulos/:id
  useEffect(() => {
    if (!esEdicion) return undefined;
    const controlador = new AbortController();
    setCargando(true);
    setErrorCarga(null);
    api
      .obtener(`/articulos/${id}`, undefined, { senal: controlador.signal })
      .then(({ datos }) => {
        if (controlador.signal.aborted) return;
        const m = articuloDesdeApi(datos);
        setArticulo({
          codigo: m.codigo ?? '',
          codigoAuxiliar: m.codigoAuxiliar ?? '',
          tipoCodificacion: 'Código interno',
          nombre: m.nombre ?? '',
          unidad: m.unidad ?? 'Unidad',
          detalle: m.detalle ?? '',
          categoria: m.categoria ?? 'Sin categoría',
          marca: m.marca ?? '',
          bodega: m.bodega ?? 'Bodega Principal',
          ubicacion: m.ubicacion ?? '',
          codigoIva: m.codigoIva ?? TARIFA_IVA_POR_DEFECTO,
          codigoIce: m.codigoIce ?? '',
          costo: m.costo != null ? String(m.costo) : '0',
          stockActual: m.stock != null ? String(m.stock) : '0',
          stockMinimo: m.stockMinimo ?? '0',
          puntoReorden: m.puntoReorden ?? '0',
          stockMaximo: m.stockMaximo ?? '0',
        });
        // Tipo derivado: si el artículo guardado es servicio
        if (m.tipo === 'Servicio') setEsServicio(true);
        // Precio principal → nivel PVP 1
        if (m.precio != null) {
          setNiveles((prev) => prev.map((n, i) => (i === 0 ? { ...n, precio: String(m.precio) } : n)));
        }
      })
      .catch((fallo) => {
        if (fallo.name === 'AbortError') return;
        setErrorCarga(fallo instanceof ErrorApi ? fallo.message : 'No se pudo cargar el artículo.');
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false);
      });
    return () => controlador.abort();
  }, [esEdicion, id]);

  const tarifa = useMemo(() => obtenerTarifaIva(articulo.codigoIva), [articulo.codigoIva]);

  const filas = useMemo(
    () =>
      niveles.map((nivel) => {
        // Si hay precio escrito manda ese; si no, se calcula desde la utilidad.
        const precioSinImpuesto =
          nivel.precio !== ''
            ? aNumero(nivel.precio)
            : precioDesdeUtilidad(articulo.costo, nivel.utilidad, baseUtilidad);

        return {
          ...nivel,
          precioSinImpuesto,
          utilidadEfectiva:
            nivel.precio !== ''
              ? utilidadDesdePrecio(articulo.costo, precioSinImpuesto, baseUtilidad)
              : aNumero(nivel.utilidad),
          precioConIva: precioConImpuesto(precioSinImpuesto, tarifa.porcentaje),
          ganancia: utilidadUnitaria(articulo.costo, precioSinImpuesto),
        };
      }),
    [niveles, articulo.costo, baseUtilidad, tarifa.porcentaje],
  );

  const semaforo = esServicio
    ? null
    : estadoStock({
        stock: articulo.stockActual,
        stockMinimo: articulo.stockMinimo,
        puntoReorden: articulo.puntoReorden,
      });

  const stockValido =
    Number(articulo.stockActual) >= 0 &&
    Number(articulo.puntoReorden) >= 0 &&
    Number(articulo.stockMinimo) >= 0 &&
    Number(articulo.stockMaximo) >= 0;

  const hayPrecioBajoCosto = filas.some((fila) => fila.ganancia < 0);
  const puedeGuardar = articulo.codigo.trim() !== '' && articulo.nombre.trim() !== '' && stockValido;

  const actualizar = (campo, valor) => setArticulo((actual) => ({ ...actual, [campo]: valor }));

  const actualizarNivel = (indice, campo, valor) =>
    setNiveles((actuales) =>
      actuales.map((nivel, i) => {
        if (i !== indice) return nivel;
        // Escribir un % descarta el precio manual y viceversa.
        if (campo === 'utilidad') return { ...nivel, utilidad: valor, precio: '' };
        return { ...nivel, precio: valor };
      }),
    );

  const guardar = async () => {
    if (!puedeGuardar || guardando) return;
    setAyudaError(null);
    setGuardando(true);
    // Mapear el estado local al payload del API: precio principal = PVP 1
    const precioPrincipal = filas[0]?.precioSinImpuesto ?? 0;
    const payloadBase = {
      codigo: articulo.codigo,
      codigoAuxiliar: articulo.codigoAuxiliar,
      nombre: articulo.nombre,
      detalle: articulo.detalle,
      tipo: esServicio ? 'Servicio' : 'Producto',
      categoria: articulo.categoria,
      marca: articulo.marca,
      unidad: articulo.unidad,
      bodega: articulo.bodega,
      ubicacion: articulo.ubicacion,
      codigoIva: articulo.codigoIva,
      codigoIce: articulo.codigoIce,
      costo: articulo.costo,
      precio: String(precioPrincipal),
      stock: esServicio ? null : articulo.stockActual,
      stockMinimo: articulo.stockMinimo,
      puntoReorden: articulo.puntoReorden,
      stockMaximo: articulo.stockMaximo,
    };
    try {
      const cuerpo = articuloHaciaApi({
        codigo: payloadBase.codigo,
        codigoAuxiliar: payloadBase.codigoAuxiliar,
        nombre: payloadBase.nombre,
        detalle: payloadBase.detalle,
        tipo: payloadBase.tipo,
        categoria: payloadBase.categoria,
        marca: payloadBase.marca,
        unidad: payloadBase.unidad,
        bodega: payloadBase.bodega,
        ubicacion: payloadBase.ubicacion,
        codigoIva: payloadBase.codigoIva,
        codigoIce: payloadBase.codigoIce,
        costo: payloadBase.costo,
        precio: payloadBase.precio,
        stock: payloadBase.stock,
        stockMinimo: payloadBase.stockMinimo,
        puntoReorden: payloadBase.puntoReorden,
        stockMaximo: payloadBase.stockMaximo,
        estado: 'Activo',
      });
      if (esEdicion) {
        await api.actualizar(`/articulos/${id}`, cuerpo);
      } else {
        await api.crear('/articulos', cuerpo);
      }
      navigate('/articulos');
    } catch (fallo) {
      if (fallo instanceof ErrorApi) {
        if (fallo.estado === 409 || fallo.estado === 422) {
          setAyudaError(fallo.message);
        } else {
          setAyudaError(fallo.message || 'No se pudo guardar el artículo.');
        }
      } else {
        setAyudaError('No se pudo guardar el artículo.');
      }
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) {
    return (
      <div className={styles.container}>
        <p style={{ color: 'var(--text-secondary)', padding: 24 }}>Cargando artículo…</p>
      </div>
    );
  }

  if (errorCarga) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.headerTitleGroup}>
            <Link to="/articulos" className={styles.btnIcon} aria-label="Volver a artículos">
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className={styles.title}>{esEdicion ? 'Editar Artículo' : 'Nuevo Artículo'}</h1>
              <p className={styles.subtitle} style={{ color: 'var(--error)' }}>{errorCarga}</p>
            </div>
          </div>
        </header>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <Link to="/articulos" className={styles.btnIcon} aria-label="Volver a artículos">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className={styles.title}>{esEdicion ? 'Editar' : 'Nuevo'} {esServicio ? 'Servicio' : 'Artículo'}</h1>
            <p className={styles.subtitle}>{esEdicion ? 'Actualiza la información, precios e impuestos.' : 'Configura la información, precios e impuestos.'}</p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnPrimary}
            disabled={!puedeGuardar || guardando}
            onClick={guardar}
            title={puedeGuardar ? undefined : 'Completa el código y el nombre. Stock y punto de reorden deben ser ≥ 0.'}
          >
            <Save size={18} /> {guardando ? 'Guardando…' : esEdicion ? 'Actualizar' : 'Guardar'}
          </button>
        </div>
      </header>

      {ayudaError && (
        <div className={styles.avisoError}>
          <AlertCircle size={18} /> <span>{ayudaError}</span>
        </div>
      )}

      <div className={`${styles.formContainer} glass-panel`}>
        <div className={styles.tabsContainer}>
          {PESTANAS.map((item) => (
            <button
              key={item.id}
              className={`${styles.tab} ${pestana === item.id ? styles.tabActive : ''}`}
              onClick={() => setPestana(item.id)}
            >
              {item.etiqueta}
            </button>
          ))}
        </div>

        <div className={styles.tabContent}>
          <AnimatePresence mode="wait">
            {pestana === 'basica' && (
              <motion.div
                key="basica"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.formGrid}
              >
                <div className={styles.formGroupFull}>
                  <div className={styles.typeSelectorWrapper}>
                    <button
                      className={`${styles.typeBtn} ${!esServicio ? styles.typeBtnActive : ''}`}
                      onClick={() => setEsServicio(false)}
                      type="button"
                    >
                      <Box size={20} /> Es un Producto
                    </button>
                    <button
                      className={`${styles.typeBtn} ${esServicio ? styles.typeBtnActive : ''}`}
                      onClick={() => setEsServicio(true)}
                      type="button"
                    >
                      <PenTool size={20} /> Es un Servicio
                    </button>
                  </div>
                  <span className={styles.ayuda}>
                    Los servicios no manejan inventario: se ocultan los campos de stock.
                  </span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="codigo">Código Principal *</label>
                  <input
                    id="codigo"
                    className={styles.input}
                    placeholder="Ej: PROD-001"
                    value={articulo.codigo}
                    disabled={esEdicion}
                    title={esEdicion ? 'El código no se cambia tras crear' : undefined}
                    onChange={(e) => actualizar('codigo', e.target.value)}
                  />
                  <span className={styles.ayuda}>{esEdicion ? 'El código no se cambia tras crear.' : 'Viaja en el XML como codigoPrincipal.'}</span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="codigoAuxiliar">Código Auxiliar</label>
                  <input
                    id="codigoAuxiliar"
                    className={styles.input}
                    placeholder="Opcional"
                    value={articulo.codigoAuxiliar}
                    onChange={(e) => actualizar('codigoAuxiliar', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="tipoCodificacion">Tipo de Codificación</label>
                  <select
                    id="tipoCodificacion"
                    className={styles.input}
                    value={articulo.tipoCodificacion}
                    onChange={(e) => actualizar('tipoCodificacion', e.target.value)}
                  >
                    {TIPOS_CODIFICACION.map((tipo) => (
                      <option key={tipo}>{tipo}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="unidad">Unidad de Medida *</label>
                  <select
                    id="unidad"
                    className={styles.input}
                    value={articulo.unidad}
                    onChange={(e) => actualizar('unidad', e.target.value)}
                  >
                    {UNIDADES_MEDIDA.map((unidad) => (
                      <option key={unidad}>{unidad}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroupFull}>
                  <label htmlFor="nombre">Nombre *</label>
                  <input
                    id="nombre"
                    className={styles.input}
                    placeholder="Nombre completo del ítem"
                    value={articulo.nombre}
                    onChange={(e) => actualizar('nombre', e.target.value)}
                  />
                </div>

                <div className={styles.formGroupFull}>
                  <label htmlFor="detalle">Detalle</label>
                  <textarea
                    id="detalle"
                    className={styles.input}
                    rows="2"
                    placeholder="Descripción ampliada que aparece en la factura"
                    value={articulo.detalle}
                    onChange={(e) => actualizar('detalle', e.target.value)}
                  ></textarea>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="categoria">Categoría</label>
                  <select
                    id="categoria"
                    className={styles.input}
                    value={articulo.categoria}
                    onChange={(e) => actualizar('categoria', e.target.value)}
                  >
                    {['Sin categoría', 'Tecnología', 'Oficina', 'Alimentos', 'Soporte', 'Profesional'].map(
                      (categoria) => (
                        <option key={categoria}>{categoria}</option>
                      ),
                    )}
                  </select>
                </div>

                {!esServicio && (
                  <>
                    <div className={styles.formGroup}>
                      <label htmlFor="marca">Marca</label>
                      <input
                        id="marca"
                        className={styles.input}
                        placeholder="Ej: Samsung, HP…"
                        value={articulo.marca}
                        onChange={(e) => actualizar('marca', e.target.value)}
                      />
                    </div>

                    <div className={styles.formGroup}>
                      <label htmlFor="bodega">Bodega</label>
                      <select
                        id="bodega"
                        className={styles.input}
                        value={articulo.bodega}
                        onChange={(e) => actualizar('bodega', e.target.value)}
                      >
                        {['Bodega Principal', 'Bodega Norte', 'Showroom'].map((bodega) => (
                          <option key={bodega}>{bodega}</option>
                        ))}
                      </select>
                    </div>

                    <div className={styles.formGroup}>
                      <label htmlFor="ubicacion">Ubicación física</label>
                      <input
                        id="ubicacion"
                        className={styles.input}
                        placeholder="Ej: Estante B, nivel 2"
                        value={articulo.ubicacion}
                        onChange={(e) => actualizar('ubicacion', e.target.value)}
                      />
                    </div>
                  </>
                )}
              </motion.div>
            )}

            {pestana === 'impuestos' && (
              <motion.div
                key="impuestos"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.formGrid}
              >
                <div className={styles.formGroup}>
                  <label htmlFor="iva">Impuesto al Valor Agregado (IVA) *</label>
                  <select
                    id="iva"
                    className={styles.input}
                    value={articulo.codigoIva}
                    onChange={(e) => actualizar('codigoIva', e.target.value)}
                  >
                    {TARIFAS_IVA.map((item) => (
                      <option key={item.codigo} value={item.codigo}>
                        {item.nombre}
                      </option>
                    ))}
                  </select>
                  <span className={styles.ayuda}>
                    Se propone al facturar y determina el grupo de <code>totalConImpuestos</code>{' '}
                    del XML.
                  </span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="ice">Impuesto a Consumos Especiales (ICE)</label>
                  <select
                    id="ice"
                    className={styles.input}
                    value={articulo.codigoIce}
                    onChange={(e) => actualizar('codigoIce', e.target.value)}
                  >
                    {OPCIONES_ICE.map((item) => (
                      <option key={item.codigo || 'ninguno'} value={item.codigo}>
                        {item.nombre}
                      </option>
                    ))}
                  </select>
                  <span className={styles.ayuda}>
                    Solo para bienes gravados con ICE. Las tarifas las publica el SRI y cambian
                    cada año.
                  </span>
                </div>

                <div className={styles.formGroupFull}>
                  <div className={styles.avisoInfo}>
                    <Info size={18} />
                    <span>
                      Con <strong>{tarifa.nombre}</strong>, un precio de {formatearMoneda(100)} sin
                      impuesto se factura al cliente en{' '}
                      <strong>{formatearMoneda(precioConImpuesto(100, tarifa.porcentaje))}</strong>.
                    </span>
                  </div>
                </div>
              </motion.div>
            )}

            {pestana === 'precios' && (
              <motion.div
                key="precios"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <div className={styles.bloqueCostos}>
                  <div className={styles.formGroup}>
                    <label htmlFor="costo">Costo de Compra ($)</label>
                    <input
                      id="costo"
                      type="number"
                      min="0"
                      step="0.01"
                      className={styles.inputLarge}
                      value={articulo.costo}
                      onChange={(e) => actualizar('costo', e.target.value)}
                    />
                  </div>

                  <div className={styles.formGroup}>
                    <label>Base del porcentaje de utilidad</label>
                    <div className={styles.selectorBase}>
                      {BASES_UTILIDAD.map((base) => (
                        <button
                          key={base.id}
                          className={`${styles.opcionBase} ${
                            baseUtilidad === base.id ? styles.opcionBaseActiva : ''
                          }`}
                          onClick={() => setBaseUtilidad(base.id)}
                          title={base.descripcion}
                          type="button"
                        >
                          {base.etiqueta}
                        </button>
                      ))}
                    </div>
                    <span className={styles.ayuda}>
                      {BASES_UTILIDAD.find((b) => b.id === baseUtilidad).descripcion}
                    </span>
                  </div>
                </div>

                {hayPrecioBajoCosto && (
                  <div className={styles.avisoAlerta}>
                    <AlertTriangle size={18} />
                    <span>Hay niveles cuyo precio queda por debajo del costo.</span>
                  </div>
                )}

                <div className={styles.tablaWrapper}>
                  <table className={styles.pricesTable}>
                    <thead>
                      <tr>
                        <th>Nivel</th>
                        <th width="120">% Utilidad</th>
                        <th width="140">Precio sin IVA</th>
                        <th width="130">Precio con IVA</th>
                        <th width="120">Ganancia</th>
                        <th width="110">Origen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filas.map((fila, indice) => (
                        <tr key={fila.nombre}>
                          <td className={styles.levelName}>
                            {fila.nombre}
                            {indice === 0 && (
                              <span className={styles.badgePrimary}>Principal</span>
                            )}
                          </td>
                          <td>
                            <div className={styles.inputWithIcon}>
                              <input
                                type="number"
                                step="0.01"
                                className={styles.inputSmall}
                                value={
                                  niveles[indice].precio !== ''
                                    ? fila.utilidadEfectiva
                                    : niveles[indice].utilidad
                                }
                                onChange={(e) =>
                                  actualizarNivel(indice, 'utilidad', e.target.value)
                                }
                              />
                              <Percent size={14} />
                            </div>
                          </td>
                          <td>
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              className={styles.inputMedium}
                              value={
                                niveles[indice].precio !== ''
                                  ? niveles[indice].precio
                                  : fila.precioSinImpuesto
                              }
                              onChange={(e) => actualizarNivel(indice, 'precio', e.target.value)}
                            />
                          </td>
                          <td className={styles.precioFinal}>
                            {formatearMoneda(fila.precioConIva)}
                          </td>
                          <td
                            className={fila.ganancia < 0 ? styles.gananciaMala : styles.gananciaBuena}
                          >
                            {formatearMoneda(fila.ganancia)}
                          </td>
                          <td className={styles.origen}>
                            {niveles[indice].precio !== '' ? 'Manual' : 'Calculado'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {!esServicio && (
                  <div className={styles.bloqueInventario}>
                    <h4>Control de inventario</h4>

                    <div className={styles.gridInventario}>
                      <div className={styles.formGroup}>
                        <label htmlFor="stockActual">Stock actual</label>
                        <input
                          id="stockActual"
                          type="number"
                          min="0"
                          className={styles.input}
                          value={articulo.stockActual}
                          onChange={(e) => actualizar('stockActual', e.target.value)}
                        />
                        {!stockValido && Number(articulo.stockActual) < 0 && (
                          <span style={{ color: 'var(--error)', fontSize: 12 }}>Debe ser ≥ 0</span>
                        )}
                      </div>
                      <div className={styles.formGroup}>
                        <label htmlFor="stockMinimo">Stock mínimo</label>
                        <input
                          id="stockMinimo"
                          type="number"
                          min="0"
                          className={styles.input}
                          value={articulo.stockMinimo}
                          onChange={(e) => actualizar('stockMinimo', e.target.value)}
                        />
                      </div>
                      <div className={styles.formGroup}>
                        <label htmlFor="puntoReorden">Punto de reorden</label>
                        <input
                          id="puntoReorden"
                          type="number"
                          min="0"
                          className={styles.input}
                          value={articulo.puntoReorden}
                          onChange={(e) => actualizar('puntoReorden', e.target.value)}
                        />
                        {!stockValido && Number(articulo.puntoReorden) < 0 && (
                          <span style={{ color: 'var(--error)', fontSize: 12 }}>Debe ser ≥ 0</span>
                        )}
                      </div>
                      <div className={styles.formGroup}>
                        <label htmlFor="stockMaximo">Stock máximo</label>
                        <input
                          id="stockMaximo"
                          type="number"
                          min="0"
                          className={styles.input}
                          value={articulo.stockMaximo}
                          onChange={(e) => actualizar('stockMaximo', e.target.value)}
                        />
                      </div>
                    </div>

                    {semaforo && (
                      <p className={`${styles.semaforo} ${CLASE_STOCK[semaforo.nivel]}`}>
                        {semaforo.mensaje}
                      </p>
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
