import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Save,
  Send,
  Search,
  Plus,
  Trash2,
  Truck,
  AlertTriangle,
  PackageOpen,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { NOMBRES_PROVINCIAS, cantonesDe } from '../../data/geografiaEcuador';
import { useCatalogos } from '../../hooks/useCatalogos';
import { crearGuia, emitirGuiaAlSri } from '../../api/documentos';
import { AvisoDemo } from '../../components/ui/EstadoCarga';
import styles from './Guias.module.css';

/**
 * Guía de Remisión: sustenta el traslado físico de mercadería.
 *
 * A diferencia de la factura no lleva precios ni impuestos —solo qué se mueve,
 * de dónde a dónde y quién lo transporta—, así que no reutiliza el formulario
 * de venta.
 */

const MOTIVOS_TRASLADO = [
  'Venta',
  'Compra',
  'Traslado entre bodegas',
  'Devolución',
  'Consignación',
  'Reparación / mantenimiento',
  'Exportación',
];

const TIPOS_TRANSPORTE = ['Público', 'Privado'];

let contador = 0;
const nuevoId = () => `item-${++contador}`;

export default function GuiaRemisionForm() {
  const navegar = useNavigate();
  const catalogos = useCatalogos();

  const [guardando, setGuardando] = useState(false);
  const [errorGuardado, setErrorGuardado] = useState(null);
  const [guardada, setGuardada] = useState(null);

  const [guia, setGuia] = useState({
    fechaInicio: '',
    fechaFin: '',
    motivo: 'Venta',
    ruta: '',
    tipoTransporte: 'Privado',
    documentoAduanero: '',
    placa: '',
    provinciaPartida: '',
    cantonPartida: '',
    direccionPartida: '',
    provinciaLlegada: '',
    cantonLlegada: '',
    direccionLlegada: '',
  });

  const [transportista, setTransportista] = useState(null);
  const [busquedaTransportista, setBusquedaTransportista] = useState('');
  const [transportistaEnfocado, setTransportistaEnfocado] = useState(false);

  const [items, setItems] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [buscadorEnfocado, setBuscadorEnfocado] = useState(false);

  const resultadosTransportistas = useMemo(
    () => catalogos.buscarReceptores(busquedaTransportista, 'Transportista'),
    [catalogos, busquedaTransportista],
  );

  const resultadosArticulos = useMemo(
    () => catalogos.buscarArticulos(busqueda),
    [catalogos, busqueda],
  );

  const cantonesPartida = useMemo(
    () => cantonesDe(guia.provinciaPartida),
    [guia.provinciaPartida],
  );
  const cantonesLlegada = useMemo(
    () => cantonesDe(guia.provinciaLlegada),
    [guia.provinciaLlegada],
  );

  const errores = useMemo(() => {
    const lista = [];
    if (!transportista) lista.push('Selecciona el transportista.');
    if (!guia.placa.trim()) lista.push('Ingresa la placa del vehículo.');
    if (!guia.fechaInicio) lista.push('Falta la fecha de inicio del traslado.');
    if (!guia.direccionPartida.trim()) lista.push('Falta la dirección de partida.');
    if (!guia.direccionLlegada.trim()) lista.push('Falta la dirección de llegada.');
    if (items.length === 0) lista.push('Agrega al menos un ítem a transportar.');
    // El SRI valida que el traslado no termine antes de empezar.
    if (guia.fechaInicio && guia.fechaFin && guia.fechaFin < guia.fechaInicio) {
      lista.push('La fecha fin no puede ser anterior a la fecha de inicio.');
    }
    return lista;
  }, [transportista, guia, items]);

  const guardar = async () => {
    setGuardando(true);
    setErrorGuardado(null);

    try {
      const { datos } = await crearGuia(guia, transportista.id, items);
      setGuardada(datos);

      // La guía ya existe; si la transmisión falla se avisa pero no se pierde,
      // y desde el listado se puede reintentar.
      try {
        const emision = await emitirGuiaAlSri(datos.id);
        setGuardada(emision.datos.guia);
      } catch (falloEmision) {
        setErrorGuardado(
          `La guía ${datos.numero} se guardó, pero no se pudo emitir: ${falloEmision.message}`,
        );
      }

      setTimeout(() => navegar('/guias'), 1800);
    } catch (fallo) {
      setErrorGuardado(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  // Guarda la guía como borrador, sin transmitirla al SRI.
  const guardarBorrador = async () => {
    setGuardando(true);
    setErrorGuardado(null);

    try {
      const { datos } = await crearGuia(guia, transportista.id, items);
      setGuardada(datos);
      setTimeout(() => navegar('/guias'), 1800);
    } catch (fallo) {
      setErrorGuardado(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  const actualizar = (campo, valor) =>
    setGuia((actual) => {
      if (campo === 'provinciaPartida') return { ...actual, provinciaPartida: valor, cantonPartida: '' };
      if (campo === 'provinciaLlegada') return { ...actual, provinciaLlegada: valor, cantonLlegada: '' };
      return { ...actual, [campo]: valor };
    });

  const agregarItem = (articulo) => {
    setItems((actuales) => {
      const existente = actuales.find((item) => item.articuloId === articulo.id);
      if (!existente) {
        return [
          ...actuales,
          {
            id: nuevoId(),
            articuloId: articulo.id,
            codigo: articulo.codigo,
            descripcion: articulo.nombre,
            cantidad: '1',
          },
        ];
      }
      return actuales.map((item) =>
        item.id === existente.id
          ? { ...item, cantidad: String((Number(item.cantidad) || 0) + 1) }
          : item,
      );
    });
    setBusqueda('');
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerTitleGroup}>
          <Link to="/guias" className={styles.btnIcon} aria-label="Volver">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className={styles.title}>Nueva Guía de Remisión</h1>
            <p className={styles.subtitle}>Sustenta el traslado físico de la mercadería.</p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnSecondary}
            onClick={guardarBorrador}
            disabled={errores.length > 0 || catalogos.usandoDemo || guardando || Boolean(guardada)}
            title={
              catalogos.usandoDemo
                ? 'Sin conexión con el servidor: no se puede guardar.'
                : 'Guarda la guía como borrador, sin enviarla al SRI.'
            }
          >
            <Save size={18} /> Guardar borrador
          </button>
          <button
            className={styles.btnPrimary}
            onClick={guardar}
            disabled={errores.length > 0 || catalogos.usandoDemo || guardando || Boolean(guardada)}
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
            Guía <strong>{guardada.numero}</strong> creada. Volviendo al listado…
          </span>
        </div>
      ) : (
        <div className={styles.banner}>
          Este comprobante electrónico se entregará a los servidores del SRI.
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
          {/* Datos del traslado */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <h3 className={styles.panelTitulo}>1. Datos del traslado</h3>
            <div className={styles.grid}>
              <div className={styles.grupo}>
                <label htmlFor="fechaInicio">Fecha de inicio *</label>
                <input
                  id="fechaInicio"
                  type="date"
                  className={styles.input}
                  value={guia.fechaInicio}
                  onChange={(e) => actualizar('fechaInicio', e.target.value)}
                />
              </div>
              <div className={styles.grupo}>
                <label htmlFor="fechaFin">Fecha de fin</label>
                <input
                  id="fechaFin"
                  type="date"
                  className={styles.input}
                  value={guia.fechaFin}
                  min={guia.fechaInicio || undefined}
                  onChange={(e) => actualizar('fechaFin', e.target.value)}
                />
              </div>
              <div className={styles.grupo}>
                <label htmlFor="motivo">Motivo del traslado *</label>
                <select
                  id="motivo"
                  className={styles.input}
                  value={guia.motivo}
                  onChange={(e) => actualizar('motivo', e.target.value)}
                >
                  {MOTIVOS_TRASLADO.map((motivo) => (
                    <option key={motivo}>{motivo}</option>
                  ))}
                </select>
              </div>
              <div className={styles.grupo}>
                <label htmlFor="tipoTransporte">Tipo de transporte</label>
                <select
                  id="tipoTransporte"
                  className={styles.input}
                  value={guia.tipoTransporte}
                  onChange={(e) => actualizar('tipoTransporte', e.target.value)}
                >
                  {TIPOS_TRANSPORTE.map((tipo) => (
                    <option key={tipo}>{tipo}</option>
                  ))}
                </select>
              </div>
              <div className={styles.grupoAncho}>
                <label htmlFor="ruta">Ruta del traslado</label>
                <input
                  id="ruta"
                  className={styles.input}
                  placeholder="Ej: Quito - Ambato - Guayaquil"
                  value={guia.ruta}
                  onChange={(e) => actualizar('ruta', e.target.value)}
                />
              </div>
              <div className={styles.grupoAncho}>
                <label htmlFor="documentoAduanero">Documento aduanero</label>
                <input
                  id="documentoAduanero"
                  className={styles.input}
                  placeholder="Solo si el traslado es de importación o exportación"
                  value={guia.documentoAduanero}
                  onChange={(e) => actualizar('documentoAduanero', e.target.value)}
                />
              </div>
            </div>
          </motion.section>

          {/* Transportista */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
          >
            <h3 className={styles.panelTitulo}>2. Transportista</h3>

            <div className={styles.buscadorWrapper}>
              <div className={styles.buscadorCampo}>
                <Search size={18} className={styles.buscadorIcono} />
                <input
                  className={styles.input}
                  placeholder="Buscar transportista por nombre o identificación…"
                  value={busquedaTransportista}
                  onChange={(e) => setBusquedaTransportista(e.target.value)}
                  onFocus={() => setTransportistaEnfocado(true)}
                  onBlur={() => setTransportistaEnfocado(false)}
                />
              </div>

              {transportistaEnfocado && busquedaTransportista.trim() !== '' && (
                <ul className={`${styles.resultados} glass-panel`}>
                  {resultadosTransportistas.length === 0 && (
                    <li className={styles.sinResultados}>
                      Sin transportistas que coincidan. Regístralo en Receptores.
                    </li>
                  )}
                  {resultadosTransportistas.map((item) => (
                    <li key={item.id}>
                      <button
                        type="button"
                        className={styles.resultado}
                        onMouseDown={(evento) => {
                          evento.preventDefault();
                          setTransportista(item);
                          setBusquedaTransportista('');
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

            {transportista ? (
              <div className={styles.tarjetaTransportista}>
                <Truck size={20} />
                <div>
                  <strong>{transportista.razonSocial}</strong>
                  <span>{transportista.identificacion}</span>
                </div>
                <button className={styles.btnQuitar} onClick={() => setTransportista(null)}>
                  Cambiar
                </button>
              </div>
            ) : (
              <p className={styles.aviso}>Ningún transportista seleccionado.</p>
            )}

            <div className={styles.grupo} style={{ marginTop: 16 }}>
              <label htmlFor="placa">Placa del vehículo *</label>
              <input
                id="placa"
                className={styles.input}
                placeholder="Ej: PBA-1234"
                value={guia.placa}
                onChange={(e) => actualizar('placa', e.target.value.toUpperCase())}
              />
            </div>
          </motion.section>

          {/* Origen y destino */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h3 className={styles.panelTitulo}>3. Punto de partida y llegada</h3>

            <div className={styles.dosColumnas}>
              <div>
                <h4 className={styles.subtituloBloque}>Partida</h4>
                <div className={styles.grupo}>
                  <label htmlFor="provinciaPartida">Provincia</label>
                  <select
                    id="provinciaPartida"
                    className={styles.input}
                    value={guia.provinciaPartida}
                    onChange={(e) => actualizar('provinciaPartida', e.target.value)}
                  >
                    <option value="">Seleccionar…</option>
                    {NOMBRES_PROVINCIAS.map((provincia) => (
                      <option key={provincia}>{provincia}</option>
                    ))}
                  </select>
                </div>
                <div className={styles.grupo}>
                  <label htmlFor="cantonPartida">Cantón</label>
                  <select
                    id="cantonPartida"
                    className={styles.input}
                    value={guia.cantonPartida}
                    disabled={cantonesPartida.length === 0}
                    onChange={(e) => actualizar('cantonPartida', e.target.value)}
                  >
                    <option value="">
                      {cantonesPartida.length === 0 ? 'Elige una provincia' : 'Seleccionar…'}
                    </option>
                    {cantonesPartida.map((canton) => (
                      <option key={canton}>{canton}</option>
                    ))}
                  </select>
                </div>
                <div className={styles.grupo}>
                  <label htmlFor="direccionPartida">Dirección exacta *</label>
                  <textarea
                    id="direccionPartida"
                    rows="2"
                    className={styles.input}
                    value={guia.direccionPartida}
                    onChange={(e) => actualizar('direccionPartida', e.target.value)}
                  ></textarea>
                </div>
              </div>

              <div>
                <h4 className={styles.subtituloBloque}>Llegada</h4>
                <div className={styles.grupo}>
                  <label htmlFor="provinciaLlegada">Provincia</label>
                  <select
                    id="provinciaLlegada"
                    className={styles.input}
                    value={guia.provinciaLlegada}
                    onChange={(e) => actualizar('provinciaLlegada', e.target.value)}
                  >
                    <option value="">Seleccionar…</option>
                    {NOMBRES_PROVINCIAS.map((provincia) => (
                      <option key={provincia}>{provincia}</option>
                    ))}
                  </select>
                </div>
                <div className={styles.grupo}>
                  <label htmlFor="cantonLlegada">Cantón</label>
                  <select
                    id="cantonLlegada"
                    className={styles.input}
                    value={guia.cantonLlegada}
                    disabled={cantonesLlegada.length === 0}
                    onChange={(e) => actualizar('cantonLlegada', e.target.value)}
                  >
                    <option value="">
                      {cantonesLlegada.length === 0 ? 'Elige una provincia' : 'Seleccionar…'}
                    </option>
                    {cantonesLlegada.map((canton) => (
                      <option key={canton}>{canton}</option>
                    ))}
                  </select>
                </div>
                <div className={styles.grupo}>
                  <label htmlFor="direccionLlegada">Dirección exacta *</label>
                  <textarea
                    id="direccionLlegada"
                    rows="2"
                    className={styles.input}
                    value={guia.direccionLlegada}
                    onChange={(e) => actualizar('direccionLlegada', e.target.value)}
                  ></textarea>
                </div>
              </div>
            </div>
          </motion.section>

          {/* Ítems */}
          <motion.section
            className={`${styles.panel} glass-panel`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
          >
            <h3 className={styles.panelTitulo}>4. Mercadería transportada</h3>

            <div className={styles.buscadorWrapper}>
              <div className={styles.buscadorCampo}>
                <Search size={18} className={styles.buscadorIcono} />
                <input
                  className={styles.input}
                  placeholder="Buscar artículo…"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  onFocus={() => setBuscadorEnfocado(true)}
                  onBlur={() => setBuscadorEnfocado(false)}
                  onKeyDown={(evento) => {
                    if (evento.key === 'Escape') setBusqueda('');
                    if (evento.key === 'Enter' && resultadosArticulos.length > 0) {
                      evento.preventDefault();
                      agregarItem(resultadosArticulos[0]);
                    }
                  }}
                />
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
                        className={styles.resultado}
                        onMouseDown={(evento) => {
                          evento.preventDefault();
                          agregarItem(articulo);
                        }}
                      >
                        <span>{articulo.nombre}</span>
                        <span className={styles.resultadoId}>{articulo.codigo}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {items.length === 0 ? (
              <div className={styles.vacio}>
                <PackageOpen size={30} />
                <p>Sin mercadería agregada.</p>
              </div>
            ) : (
              <table className={styles.tabla}>
                <thead>
                  <tr>
                    <th>Código</th>
                    <th>Descripción</th>
                    <th width="110">Cantidad</th>
                    <th width="48"></th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td className={styles.codigo}>{item.codigo}</td>
                      <td>{item.descripcion}</td>
                      <td>
                        <input
                          type="number"
                          min="0"
                          className={styles.inputMini}
                          value={item.cantidad}
                          onChange={(e) =>
                            setItems((actuales) =>
                              actuales.map((i) =>
                                i.id === item.id ? { ...i, cantidad: e.target.value } : i,
                              ),
                            )
                          }
                        />
                      </td>
                      <td>
                        <button
                          className={styles.btnEliminar}
                          onClick={() =>
                            setItems((actuales) => actuales.filter((i) => i.id !== item.id))
                          }
                          aria-label={`Eliminar ${item.descripcion}`}
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
              onClick={() =>
                setItems((actuales) => [
                  ...actuales,
                  { id: nuevoId(), articuloId: null, codigo: '', descripcion: '', cantidad: '1' },
                ])
              }
            >
              <Plus size={16} /> Línea libre
            </button>
          </motion.section>
        </div>

        {/* Validación */}
        <aside className={styles.columnaLateral}>
          <motion.div
            className={`${styles.panel} glass-panel ${styles.panelResumen}`}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <h3 className={styles.panelTitulo}>Resumen</h3>
            <p className={styles.resumenLinea}>
              <span>Ítems a transportar</span>
              <strong>{items.length}</strong>
            </p>
            <p className={styles.resumenLinea}>
              <span>Motivo</span>
              <strong>{guia.motivo}</strong>
            </p>
            <p className={styles.resumenLinea}>
              <span>Transporte</span>
              <strong>{guia.tipoTransporte}</strong>
            </p>

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
              <p className={styles.listo}>La guía está lista para emitirse.</p>
            )}
          </motion.div>
        </aside>
      </div>
    </div>
  );
}
