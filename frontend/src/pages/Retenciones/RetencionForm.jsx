import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Send,
  Search,
  Plus,
  Trash2,
  Building2,
  AlertTriangle,
  ReceiptText,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { useCatalogos } from '../../hooks/useCatalogos';
import {
  DOCUMENTOS_SUSTENTO,
  IMPUESTOS_RETENCION,
  cargarCodigosRetencion,
  crearRetencion,
  emitirRetencionAlSri,
} from '../../api/retenciones';
import { formatearMoneda, redondear } from '../../lib/sri/calculoComprobante';
import { AvisoDemo } from '../../components/ui/EstadoCarga';
import styles from './Retenciones.module.css';

/**
 * Comprobante de Retención.
 *
 * Estructura distinta a la de una venta: no hay artículos ni IVA que cobrar,
 * sino porcentajes que se retienen al proveedor sobre el documento que
 * sustenta el pago. Por eso no reutiliza `DocumentoVentaForm`.
 */

let contador = 0;
const nuevoId = () => `linea-${++contador}`;

const lineaVacia = () => ({
  id: nuevoId(),
  codigoImpuesto: '1',
  // `concepto` es el id del catálogo, no el código del SRI: muchos conceptos
  // de la resolución no tienen código verificado y el desplegable necesita
  // igual una clave estable.
  concepto: '',
  codigoRetencion: '',
  baseImponible: '',
  porcentaje: '',
});

/** MM/AAAA de hoy: es el período fiscal por defecto. */
const periodoDeHoy = () => {
  const hoy = new Date();
  return `${String(hoy.getMonth() + 1).padStart(2, '0')}/${hoy.getFullYear()}`;
};

const hoyISO = () => new Date().toISOString().slice(0, 10);

export default function RetencionForm() {
  const navegar = useNavigate();
  const catalogos = useCatalogos();

  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState(null);
  const [guardada, setGuardada] = useState(null);

  const [codigos, setCodigos] = useState([]);

  const [retencion, setRetencion] = useState({
    fechaEmision: hoyISO(),
    periodoFiscal: periodoDeHoy(),
    codDocSustento: '01',
    numDocSustento: '',
    fechaDocSustento: hoyISO(),
  });

  const [proveedor, setProveedor] = useState(null);
  const [busquedaProveedor, setBusquedaProveedor] = useState('');
  const [proveedorEnfocado, setProveedorEnfocado] = useState(false);

  const [lineas, setLineas] = useState([lineaVacia()]);

  // El catálogo solo precarga porcentajes; si no llega, se escriben a mano.
  useEffect(() => {
    let vigente = true;
    cargarCodigosRetencion()
      .then(({ datos }) => {
        if (vigente) setCodigos(datos ?? []);
      })
      .catch(() => {
        if (vigente) setCodigos([]);
      });
    return () => {
      vigente = false;
    };
  }, []);

  const conceptosPorImpuesto = useMemo(() => {
    const mapa = {};
    for (const fila of codigos) {
      (mapa[fila.codigo_impuesto] ??= []).push(fila);
    }
    return mapa;
  }, [codigos]);

  const resultadosProveedores = useMemo(
    () => catalogos.buscarReceptores(busquedaProveedor, 'Proveedor'),
    [catalogos, busquedaProveedor],
  );

  const calculadas = useMemo(
    () =>
      lineas.map((linea) => ({
        ...linea,
        valorRetenido: redondear(
          ((Number(linea.baseImponible) || 0) * (Number(linea.porcentaje) || 0)) / 100,
        ),
      })),
    [lineas],
  );

  const totalRetenido = useMemo(
    () => redondear(calculadas.reduce((suma, linea) => suma + linea.valorRetenido, 0)),
    [calculadas],
  );

  const errores = useMemo(() => {
    const lista = [];
    if (!proveedor) lista.push('Selecciona el proveedor al que se retiene.');
    if (!retencion.numDocSustento.trim())
      lista.push('Ingresa el número del documento sustento.');
    if (!retencion.fechaEmision) lista.push('Falta la fecha de emisión.');
    if (!/^\d{2}\/\d{4}$/.test(retencion.periodoFiscal))
      lista.push('El período fiscal debe tener el formato MM/AAAA.');
    if (lineas.length === 0) lista.push('Agrega al menos una línea de retención.');

    lineas.forEach((linea, indice) => {
      if (!linea.codigoRetencion.trim())
        lista.push(`Línea ${indice + 1}: falta el código de retención.`);
      if (!(Number(linea.baseImponible) > 0))
        lista.push(`Línea ${indice + 1}: la base imponible debe ser mayor que cero.`);
      const porcentaje = Number(linea.porcentaje);
      if (Number.isNaN(porcentaje) || porcentaje < 0 || porcentaje > 100)
        lista.push(`Línea ${indice + 1}: el porcentaje debe estar entre 0 y 100.`);
    });

    return lista;
  }, [proveedor, retencion, lineas]);

  const actualizar = (campo, valor) =>
    setRetencion((actual) => ({ ...actual, [campo]: valor }));

  const actualizarLinea = (id, campo, valor) =>
    setLineas((actuales) =>
      actuales.map((linea) => {
        if (linea.id !== id) return linea;
        const siguiente = { ...linea, [campo]: valor };

        // Cambiar de impuesto invalida el concepto: los de renta no aplican al IVA.
        if (campo === 'codigoImpuesto') {
          siguiente.concepto = '';
          siguiente.codigoRetencion = '';
          siguiente.porcentaje = '';
        }

        // Al elegir concepto se precargan porcentaje y código. Ambos siguen
        // siendo editables: el porcentaje vigente lo fija la resolución del
        // SRI, y hay conceptos cuyo código no está confirmado.
        if (campo === 'concepto') {
          const elegido = codigos.find((fila) => fila.id === valor);
          if (elegido) {
            siguiente.porcentaje = elegido.porcentaje;
            siguiente.codigoRetencion = elegido.codigo_retencion;
          }
        }

        return siguiente;
      }),
    );

  /** Conceptos elegidos cuyo código quedó vacío: hay que escribirlo a mano. */
  const conceptosSinCodigo = useMemo(
    () =>
      lineas.filter((linea) => linea.concepto && !linea.codigoRetencion.trim()).length,
    [lineas],
  );

  const guardar = async () => {
    setGuardando(true);
    setErrorGuardado(null);

    try {
      const { datos } = await crearRetencion(retencion, proveedor.id, lineas);
      setGuardada(datos);

      // La retención ya existe; si la transmisión falla se avisa pero no se
      // pierde, y desde el listado se puede reintentar.
      try {
        const emision = await emitirRetencionAlSri(datos.id);
        setGuardada(emision.datos.retencion);
      } catch (falloEmision) {
        setErrorGuardado(
          `La retención ${datos.numero} se guardó, pero no se pudo emitir: ${falloEmision.message}`,
        );
      }

      setTimeout(() => navegar('/retenciones'), 1800);
    } catch (fallo) {
      setErrorGuardado(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <Link to="/retenciones" className={styles.btnIcon} aria-label="Volver">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className={styles.title}>Nueva Retención</h1>
            <p className={styles.subtitle}>
              Comprobante de retención sobre el pago a un proveedor.
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button className={styles.btnSecondary} disabled={guardando || Boolean(guardada)}>
            <Save size={18} /> Guardar borrador
          </button>
          <button
            className={styles.btnPrimary}
            onClick={guardar}
            disabled={
              errores.length > 0 || catalogos.usandoDemo || guardando || Boolean(guardada)
            }
            title={
              catalogos.usandoDemo
                ? 'Sin conexión con el servidor: no se puede guardar.'
                : errores[0]
            }
          >
            {guardando ? (
              <>
                <Loader2 size={18} className={styles.girando} /> Guardando…
              </>
            ) : (
              <>
                <Send size={18} /> Emitir al SRI
              </>
            )}
          </button>
        </div>
      </header>

      {catalogos.usandoDemo && <AvisoDemo />}

      {guardada ? (
        <div className={styles.exito}>
          <CheckCircle2 size={20} />
          <span>
            Retención <strong>{guardada.numero}</strong> creada. Volviendo al listado…
          </span>
        </div>
      ) : (
        <div className={styles.banner}>
          Solo un agente de retención o un contribuyente especial puede emitir este
          comprobante.
        </div>
      )}

      {errorGuardado && (
        <div className={styles.errorGuardado}>
          <AlertTriangle size={18} />
          <span>{errorGuardado}</span>
        </div>
      )}

      <div className={styles.layout}>
        <div className={styles.columna}>
          {/* Proveedor */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className={styles.panelTitulo}>1. Sujeto retenido</h3>

            <div className={styles.buscadorWrapper}>
              <div className={styles.buscadorCampo}>
                <Search size={18} className={styles.buscadorIcono} />
                <input
                  className={styles.input}
                  placeholder="Buscar proveedor por nombre o identificación…"
                  value={busquedaProveedor}
                  onChange={(e) => setBusquedaProveedor(e.target.value)}
                  onFocus={() => setProveedorEnfocado(true)}
                  onBlur={() => setProveedorEnfocado(false)}
                />
              </div>

              {proveedorEnfocado && busquedaProveedor.trim() !== '' && (
                <ul className={`${styles.resultados} glass-panel`}>
                  {resultadosProveedores.length === 0 && (
                    <li className={styles.sinResultados}>
                      Sin proveedores que coincidan. Regístralo en Receptores con el rol
                      Proveedor.
                    </li>
                  )}
                  {resultadosProveedores.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={styles.resultado}
                        onMouseDown={(evento) => {
                          evento.preventDefault();
                          setProveedor(item);
                          setBusquedaProveedor('');
                        }}
                      >
                        <span>{item.razonSocial}</span>
                        <span className={styles.resultadoId}>{item.identificacion}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {proveedor ? (
              <div className={styles.tarjetaProveedor}>
                <Building2 size={20} />
                <div>
                  <strong>{proveedor.razonSocial}</strong>
                  <span>{proveedor.identificacion}</span>
                </div>
                <button className={styles.btnQuitar} onClick={() => setProveedor(null)}>
                  Cambiar
                </button>
              </div>
            ) : (
              <p className={styles.aviso}>Ningún proveedor seleccionado.</p>
            )}
          </motion.section>

          {/* Documento sustento */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <h3 className={styles.panelTitulo}>2. Documento sustento y período</h3>
            <div className={styles.grid}>
              <div className={styles.grupo}>
                <label htmlFor="codDocSustento">Tipo de documento *</label>
                <select
                  id="codDocSustento"
                  className={styles.input}
                  value={retencion.codDocSustento}
                  onChange={(e) => actualizar('codDocSustento', e.target.value)}
                >
                  {DOCUMENTOS_SUSTENTO.map((documento) => (
                    <option key={documento.codigo} value={documento.codigo}>
                      {documento.nombre}
                    </option>
                  ))}
                </select>
              </div>
              <div className={styles.grupo}>
                <label htmlFor="numDocSustento">Número del documento *</label>
                <input
                  id="numDocSustento"
                  className={styles.input}
                  placeholder="001-001-000000123"
                  value={retencion.numDocSustento}
                  onChange={(e) => actualizar('numDocSustento', e.target.value)}
                />
              </div>
              <div className={styles.grupo}>
                <label htmlFor="fechaDocSustento">Fecha del documento</label>
                <input
                  id="fechaDocSustento"
                  type="date"
                  className={styles.input}
                  value={retencion.fechaDocSustento}
                  onChange={(e) => actualizar('fechaDocSustento', e.target.value)}
                />
              </div>
              <div className={styles.grupo}>
                <label htmlFor="fechaEmision">Fecha de emisión *</label>
                <input
                  id="fechaEmision"
                  type="date"
                  className={styles.input}
                  value={retencion.fechaEmision}
                  onChange={(e) => actualizar('fechaEmision', e.target.value)}
                />
              </div>
              <div className={styles.grupo}>
                <label htmlFor="periodoFiscal">Período fiscal *</label>
                <input
                  id="periodoFiscal"
                  className={styles.input}
                  placeholder="MM/AAAA"
                  value={retencion.periodoFiscal}
                  onChange={(e) => actualizar('periodoFiscal', e.target.value)}
                />
              </div>
            </div>
          </motion.section>

          {/* Líneas de retención */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h3 className={styles.panelTitulo}>3. Impuestos retenidos</h3>

            {lineas.length === 0 ? (
              <div className={styles.vacio}>
                <ReceiptText size={30} />
                <p>Sin líneas de retención.</p>
              </div>
            ) : (
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th width="120">Impuesto</th>
                    <th>Concepto</th>
                    <th width="80">Código</th>
                    <th width="110">Base</th>
                    <th width="80">%</th>
                    <th width="100">Retenido</th>
                    <th width="48"></th>
                  </tr>
                </thead>
                <tbody>
                  {calculadas.map((linea) => (
                    <tr key={linea.id}>
                      <td>
                        <select
                          className={styles.inputMini}
                          value={linea.codigoImpuesto}
                          aria-label="Impuesto"
                          onChange={(e) =>
                            actualizarLinea(linea.id, 'codigoImpuesto', e.target.value)
                          }
                        >
                          {IMPUESTOS_RETENCION.map((impuesto) => (
                            <option key={impuesto.codigo} value={impuesto.codigo}>
                              {impuesto.nombre}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <select
                          className={styles.selectConcepto}
                          value={linea.concepto}
                          aria-label="Concepto de retención"
                          onChange={(e) =>
                            actualizarLinea(linea.id, 'concepto', e.target.value)
                          }
                        >
                          <option value="">Seleccionar…</option>
                          {(conceptosPorImpuesto[linea.codigoImpuesto] ?? []).map((fila) => (
                            <option key={fila.id} value={fila.id}>
                              {fila.codigo_retencion
                                ? `${fila.codigo_retencion} — ${fila.descripcion}`
                                : fila.descripcion}
                              {` (${fila.porcentaje}%)`}
                            </option>
                          ))}
                        </select>
                        {linea.concepto && !linea.codigoRetencion.trim() && (
                          <span className={styles.avisoCodigo}>
                            Escribe el código de la ficha técnica del SRI →
                          </span>
                        )}
                      </td>
                      <td>
                        <input
                          className={styles.inputMini}
                          placeholder="000"
                          value={linea.codigoRetencion}
                          aria-label="Código de retención"
                          onChange={(e) =>
                            actualizarLinea(linea.id, 'codigoRetencion', e.target.value)
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          className={styles.inputMini}
                          value={linea.baseImponible}
                          aria-label="Base imponible"
                          onChange={(e) =>
                            actualizarLinea(linea.id, 'baseImponible', e.target.value)
                          }
                        />
                      </td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          max="100"
                          step="0.01"
                          className={styles.inputMini}
                          value={linea.porcentaje}
                          aria-label="Porcentaje a retener"
                          onChange={(e) =>
                            actualizarLinea(linea.id, 'porcentaje', e.target.value)
                          }
                        />
                      </td>
                      <td className={styles.valorRetenido}>
                        {formatearMoneda(linea.valorRetenido)}
                      </td>
                      <td>
                        <button
                          className={styles.btnEliminar}
                          onClick={() =>
                            setLineas((actuales) => actuales.filter((l) => l.id !== linea.id))
                          }
                          aria-label="Eliminar línea"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}

            <button
              className={styles.btnLinea}
              onClick={() => setLineas((actuales) => [...actuales, lineaVacia()])}
            >
              <Plus size={16} /> Agregar línea
            </button>

            <p className={styles.notaCatalogo}>
              Porcentajes de renta según la resolución{' '}
              <strong>NAC-DGERCGC26-00000009</strong>, vigente desde el 1 de marzo de 2026.
              El código y el porcentaje son editables: el código lo fija la ficha técnica
              del SRI, que se publica aparte de la resolución.
              {conceptosSinCodigo > 0 && (
                <>
                  {' '}
                  <strong>
                    Falta el código en {conceptosSinCodigo}{' '}
                    {conceptosSinCodigo === 1 ? 'línea' : 'líneas'}.
                  </strong>
                </>
              )}
            </p>
          </motion.section>
        </div>

        {/* Resumen */}
        <aside>
          <motion.div
            className={`${styles.panel} glass-panel ${styles.panelResumen}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className={styles.panelTitulo}>Resumen</h3>
            <p className={styles.resumenLinea}>
              <span>Líneas</span>
              <strong>{lineas.length}</strong>
            </p>
            <p className={styles.resumenLinea}>
              <span>Período</span>
              <strong>{retencion.periodoFiscal}</strong>
            </p>
            <p className={styles.resumenLinea}>
              <span>Sustento</span>
              <strong>{retencion.numDocSustento || '—'}</strong>
            </p>

            <div className={styles.totalRetenido}>
              <span>Total retenido</span>
              <strong>{formatearMoneda(totalRetenido)}</strong>
            </div>

            {errores.length > 0 ? (
              <div className={styles.alertas}>
                {errores.map((error) => (
                  <p className={styles.alerta} key={error}>
                    <AlertTriangle size={16} />
                    <span>{error}</span>
                  </p>
                ))}
              </div>
            ) : (
              <p className={styles.listo}>La retención está lista para emitirse.</p>
            )}
          </motion.div>
        </aside>
      </div>
    </div>
  );
}
