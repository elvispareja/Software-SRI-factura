import { useCallback, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Ban,
  Plus,
  Receipt,
  Search,
  SearchX,
  Tags,
  Trash2,
  TrendingDown,
  Wallet,
  X,
} from 'lucide-react';
import {
  ESTADOS_PAGO_GASTO,
  FORMAS_PAGO_EGRESO,
  anularEgreso,
  cargarResumenEgresos,
  crearEgreso,
  crearGasto,
  crearTipoGasto,
  desactivarTipoGasto,
  egresoDesdeApi,
  eliminarGasto,
  gastoDesdeApi,
  tipoGastoDesdeApi,
} from '../../api/egresos';
import { useRecurso } from '../../hooks/useRecurso';
import { useReporte } from '../../hooks/useReporte';
import { useCatalogos } from '../../hooks/useCatalogos';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { TARIFAS_IVA, TARIFA_IVA_POR_DEFECTO } from '../../lib/sri/impuestos';
import { contieneTexto } from '../../lib/texto';
import { ErrorCarga, TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './Egresos.module.css';

/**
 * Egresos: tipos de gasto, gastos y pagos.
 *
 * La distinción entre **gasto** y **egreso** gobierna la pantalla: el gasto es
 * la obligación (llegó la factura del arriendo) y el egreso es la salida de
 * dinero (se pagó). No coinciden ni en fecha ni en importe, por eso son dos
 * pestañas y no una.
 */

const PESTANAS = [
  { id: 'gastos', etiqueta: 'Gastos', Icon: Receipt },
  { id: 'pagos', etiqueta: 'Pagos', Icon: Wallet },
  { id: 'tipos', etiqueta: 'Tipos de gasto', Icon: Tags },
];

const hoyISO = () => new Date().toISOString().slice(0, 10);

export default function Egresos() {
  const [pestana, setPestana] = useState('gastos');
  const [error, setError] = useState(null);

  const gastos = useRecurso('/egresos/gastos', { parametros: { tamano: 200 }, datosDemo: [] });
  const pagos = useRecurso('/egresos', { parametros: { tamano: 200 }, datosDemo: [] });
  const tipos = useRecurso('/egresos/tipos', { datosDemo: [] });

  const cargarResumen = useCallback(({ senal }) => cargarResumenEgresos(undefined, undefined, { senal }), []);
  const resumen = useReporte(cargarResumen);

  const recargarTodo = () => {
    gastos.recargar();
    pagos.recargar();
    tipos.recargar();
    resumen.recargar();
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Egresos</h1>
          <p className={styles.subtitle}>
            El <strong>gasto</strong> es la obligación; el <strong>pago</strong> es la salida
            de dinero. No coinciden ni en fecha ni en importe, por eso se registran aparte.
          </p>
        </div>
      </header>

      {resumen.datos && (
        <div className={styles.resumen}>
          <Tarjeta etiqueta="Gastos registrados" valor={String(resumen.datos.gastos)} />
          <Tarjeta
            etiqueta="Total gastado"
            valor={formatearMoneda(resumen.datos.total_gastos)}
            acento
          />
          <Tarjeta etiqueta="Total pagado" valor={formatearMoneda(resumen.datos.total_pagos)} />
          <Tarjeta
            etiqueta="Pendiente de pago"
            valor={formatearMoneda(resumen.datos.pendiente)}
            aviso
          />
        </div>
      )}

      {error && <ErrorCarga mensaje={error} onReintentar={() => setError(null)} />}

      <nav className={styles.tabs} aria-label="Secciones de egresos">
        {PESTANAS.map((entrada) => (
          <button
            key={entrada.id}
            className={`${styles.tab} ${pestana === entrada.id ? styles.tabActivo : ''}`}
            onClick={() => setPestana(entrada.id)}
            aria-current={pestana === entrada.id ? 'page' : undefined}
          >
            <entrada.Icon size={16} /> {entrada.etiqueta}
          </button>
        ))}
      </nav>

      {pestana === 'gastos' && (
        <PanelGastos
          recurso={gastos}
          tipos={tipos}
          onCambio={recargarTodo}
          onError={setError}
        />
      )}
      {pestana === 'pagos' && (
        <PanelPagos recurso={pagos} gastos={gastos} onCambio={recargarTodo} onError={setError} />
      )}
      {pestana === 'tipos' && (
        <PanelTipos recurso={tipos} onCambio={recargarTodo} onError={setError} />
      )}
    </div>
  );
}

function Tarjeta({ etiqueta, valor, acento, aviso }) {
  return (
    <div
      className={`${styles.tarjeta} glass-panel ${acento ? styles.tarjetaAcento : ''} ${
        aviso ? styles.tarjetaAviso : ''
      }`}
    >
      <span className={styles.tarjetaEtiqueta}>{etiqueta}</span>
      <span className={styles.tarjetaValor}>{valor}</span>
    </div>
  );
}

function Vacio({ mensaje }) {
  return (
    <div className={styles.vacio}>
      <SearchX size={30} />
      <p>{mensaje}</p>
    </div>
  );
}

const TONO_ESTADO = {
  Pagado: styles.insigniaOk,
  Parcial: styles.insigniaAviso,
  'Por Pagar': styles.insigniaNeutro,
  Registrado: styles.insigniaOk,
  Anulado: styles.insigniaError,
};

// --------------------------------------------------------------------------
// Gastos
// --------------------------------------------------------------------------

function PanelGastos({ recurso, tipos, onCambio, onError }) {
  const catalogos = useCatalogos();
  const [termino, setTermino] = useState('');
  const [estado, setEstado] = useState('');
  const [abierto, setAbierto] = useState(false);

  const filas = useMemo(() => recurso.datos.map(gastoDesdeApi), [recurso.datos]);
  const listaTipos = useMemo(() => tipos.datos.map(tipoGastoDesdeApi), [tipos.datos]);

  const visibles = filas.filter(
    (g) =>
      (!estado || g.estadoPago === estado) &&
      (!termino ||
        contieneTexto(g.concepto, termino) ||
        contieneTexto(g.proveedor, termino) ||
        contieneTexto(g.documento, termino)),
  );

  const borrar = async (id) => {
    try {
      await eliminarGasto(id);
      onCambio();
    } catch (fallo) {
      onError(fallo.message);
    }
  };

  return (
    <>
      <motion.section
        className={`${styles.panel} glass-panel`}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className={styles.toolbar}>
          <div className={styles.buscador}>
            <Search size={16} />
            <input
              placeholder="Buscar por concepto, proveedor o documento…"
              value={termino}
              onChange={(e) => setTermino(e.target.value)}
            />
          </div>
          <select
            className={styles.select}
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            aria-label="Filtrar por estado de pago"
          >
            <option value="">Todo estado</option>
            {ESTADOS_PAGO_GASTO.map((valor) => (
              <option key={valor}>{valor}</option>
            ))}
          </select>
          <button
            className={styles.btnPrimary}
            onClick={() => setAbierto(true)}
            disabled={catalogos.usandoDemo}
            title={catalogos.usandoDemo ? 'Sin conexión con el servidor.' : undefined}
          >
            <Plus size={16} /> Nuevo gasto
          </button>
        </div>

        {recurso.cargando ? (
          <TablaCargando columnas={6} filas={4} />
        ) : recurso.error ? (
          <ErrorCarga mensaje={recurso.error} onReintentar={recurso.recargar} />
        ) : visibles.length === 0 ? (
          <Vacio mensaje="No hay gastos registrados con estos filtros." />
        ) : (
          <div className={styles.tablaWrapper}>
            <table className={styles.tabla}>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Concepto</th>
                  <th>Documento</th>
                  <th className={styles.numero}>Subtotal</th>
                  <th className={styles.numero}>Total</th>
                  <th>Estado</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visibles.map((gasto) => (
                  <tr key={gasto.id}>
                    <td className={styles.secundario}>{gasto.fecha}</td>
                    <td>
                      <div className={styles.principal}>{gasto.concepto}</div>
                      <div className={styles.secundario}>{gasto.proveedor || '—'}</div>
                    </td>
                    <td className={styles.secundario}>{gasto.documento || '—'}</td>
                    <td className={styles.numero}>{formatearMoneda(gasto.subtotal)}</td>
                    <td className={`${styles.numero} ${styles.principal}`}>
                      {formatearMoneda(gasto.total)}
                    </td>
                    <td>
                      <span
                        className={`${styles.insignia} ${
                          TONO_ESTADO[gasto.estadoPago] ?? styles.insigniaNeutro
                        }`}
                      >
                        {gasto.estadoPago}
                      </span>
                    </td>
                    <td>
                      <div className={styles.acciones}>
                        <button
                          className={styles.btnIcono}
                          onClick={() => borrar(gasto.id)}
                          title="Eliminar"
                          aria-label={`Eliminar ${gasto.concepto}`}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.section>

      {abierto && (
        <DialogoGasto
          tipos={listaTipos}
          proveedores={catalogos.receptores.filter((r) => r.rol === 'Proveedor')}
          onCerrar={() => setAbierto(false)}
          onGuardado={() => {
            setAbierto(false);
            onCambio();
          }}
        />
      )}
    </>
  );
}

function DialogoGasto({ tipos, proveedores, onCerrar, onGuardado }) {
  const [datos, setDatos] = useState({
    fecha: hoyISO(),
    concepto: '',
    tipoId: '',
    proveedorId: '',
    documento: '',
    fechaDocumento: hoyISO(),
    autorizacionProveedor: '',
    subtotal: '',
    iva: '',
    codigoIva: TARIFA_IVA_POR_DEFECTO,
  });
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const total = (Number(datos.subtotal) || 0) + (Number(datos.iva) || 0);
  const puedeGuardar = datos.concepto.trim() !== '' && Number(datos.subtotal) >= 0;

  const cambiar = (campo, valor) => setDatos((a) => ({ ...a, [campo]: valor }));

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      await crearGasto(datos);
      onGuardado();
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className={styles.fondo} onClick={onCerrar}>
      <div
        className={styles.dialogo}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Nuevo gasto"
      >
        <div className={styles.dialogoCabecera}>
          <span className={styles.dialogoTitulo}>Nuevo gasto</span>
          <button className={styles.btnIcono} onClick={onCerrar} aria-label="Cerrar">
            <X size={16} />
          </button>
        </div>

        <div className={styles.dialogoCuerpo}>
          {error && <div className={styles.errorCaja}>{error}</div>}

          <div className={styles.campoAncho}>
            <label htmlFor="concepto">Concepto *</label>
            <input
              id="concepto"
              className={styles.input}
              value={datos.concepto}
              onChange={(e) => cambiar('concepto', e.target.value)}
              placeholder="Planilla de luz, arriendo, suministros…"
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="fecha">Fecha</label>
            <input
              id="fecha"
              type="date"
              className={styles.input}
              value={datos.fecha}
              onChange={(e) => cambiar('fecha', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="tipo">Tipo de gasto</label>
            <select
              id="tipo"
              className={styles.input}
              value={datos.tipoId}
              onChange={(e) => cambiar('tipoId', e.target.value)}
            >
              <option value="">Sin clasificar</option>
              {tipos.map((tipo) => (
                <option key={tipo.id} value={tipo.id}>
                  {tipo.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.campo}>
            <label htmlFor="proveedor">Proveedor</label>
            <select
              id="proveedor"
              className={styles.input}
              value={datos.proveedorId}
              onChange={(e) => cambiar('proveedorId', e.target.value)}
            >
              <option value="">Sin proveedor</option>
              {proveedores.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.razonSocial}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.campo}>
            <label htmlFor="documento">Documento sustento</label>
            <input
              id="documento"
              className={styles.input}
              value={datos.documento}
              onChange={(e) => cambiar('documento', e.target.value)}
              placeholder="001-001-000000123"
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="autorizacionProveedor">Autorización del proveedor</label>
            <input
              id="autorizacionProveedor"
              className={styles.input}
              value={datos.autorizacionProveedor}
              onChange={(e) => cambiar('autorizacionProveedor', e.target.value)}
              placeholder="Clave de acceso de 49 dígitos"
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="subtotal">Subtotal</label>
            <input
              id="subtotal"
              type="number"
              min="0"
              step="0.01"
              className={styles.input}
              value={datos.subtotal}
              onChange={(e) => cambiar('subtotal', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="codigoIva">Tarifa de IVA</label>
            <select
              id="codigoIva"
              className={styles.input}
              value={datos.codigoIva}
              onChange={(e) => cambiar('codigoIva', e.target.value)}
            >
              {TARIFAS_IVA.map((tarifa) => (
                <option key={tarifa.codigo} value={tarifa.codigo}>
                  {tarifa.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.campo}>
            <label htmlFor="iva">IVA</label>
            <input
              id="iva"
              type="number"
              min="0"
              step="0.01"
              className={styles.input}
              value={datos.iva}
              onChange={(e) => cambiar('iva', e.target.value)}
            />
          </div>

          <div className={styles.total}>
            <span>Total del gasto</span>
            <strong>{formatearMoneda(total)}</strong>
          </div>
        </div>

        <div className={styles.dialogoPie}>
          <button className={styles.btnSecundario} onClick={onCerrar}>
            Cancelar
          </button>
          <button
            className={styles.btnPrimary}
            onClick={guardar}
            disabled={!puedeGuardar || guardando}
          >
            {guardando ? 'Guardando…' : 'Guardar gasto'}
          </button>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Pagos
// --------------------------------------------------------------------------

function PanelPagos({ recurso, gastos, onCambio, onError }) {
  const [termino, setTermino] = useState('');
  const [abierto, setAbierto] = useState(false);

  const filas = useMemo(() => recurso.datos.map(egresoDesdeApi), [recurso.datos]);
  const pendientes = useMemo(
    () => gastos.datos.map(gastoDesdeApi).filter((g) => g.estadoPago !== 'Pagado'),
    [gastos.datos],
  );

  const visibles = filas.filter(
    (e) =>
      !termino || contieneTexto(e.concepto, termino) || contieneTexto(e.beneficiario, termino),
  );

  const anular = async (id) => {
    try {
      await anularEgreso(id);
      onCambio();
    } catch (fallo) {
      onError(fallo.message);
    }
  };

  return (
    <>
      <motion.section
        className={`${styles.panel} glass-panel`}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className={styles.toolbar}>
          <div className={styles.buscador}>
            <Search size={16} />
            <input
              placeholder="Buscar por concepto o beneficiario…"
              value={termino}
              onChange={(e) => setTermino(e.target.value)}
            />
          </div>
          <button className={styles.btnPrimary} onClick={() => setAbierto(true)}>
            <Plus size={16} /> Registrar pago
          </button>
        </div>

        {recurso.cargando ? (
          <TablaCargando columnas={6} filas={4} />
        ) : visibles.length === 0 ? (
          <Vacio mensaje="No hay pagos registrados." />
        ) : (
          <div className={styles.tablaWrapper}>
            <table className={styles.tabla}>
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Concepto</th>
                  <th>Forma de pago</th>
                  <th>Referencia</th>
                  <th className={styles.numero}>Monto</th>
                  <th>Estado</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visibles.map((pago) => (
                  <tr key={pago.id}>
                    <td className={styles.secundario}>{pago.fecha}</td>
                    <td>
                      <div className={styles.principal}>{pago.concepto}</div>
                      <div className={styles.secundario}>{pago.beneficiario || '—'}</div>
                    </td>
                    <td className={styles.secundario}>{pago.formaPago}</td>
                    <td className={styles.secundario}>{pago.referencia || '—'}</td>
                    <td className={`${styles.numero} ${styles.principal}`}>
                      {formatearMoneda(pago.monto)}
                    </td>
                    <td>
                      <span
                        className={`${styles.insignia} ${
                          TONO_ESTADO[pago.estado] ?? styles.insigniaNeutro
                        }`}
                      >
                        {pago.estado}
                      </span>
                    </td>
                    <td>
                      <div className={styles.acciones}>
                        <button
                          className={styles.btnIcono}
                          onClick={() => anular(pago.id)}
                          disabled={pago.estado === 'Anulado'}
                          title="Anular"
                          aria-label={`Anular ${pago.concepto}`}
                        >
                          <Ban size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.section>

      {abierto && (
        <DialogoPago
          pendientes={pendientes}
          onCerrar={() => setAbierto(false)}
          onGuardado={() => {
            setAbierto(false);
            onCambio();
          }}
        />
      )}
    </>
  );
}

function DialogoPago({ pendientes, onCerrar, onGuardado }) {
  const [datos, setDatos] = useState({
    fecha: hoyISO(),
    concepto: '',
    beneficiario: '',
    monto: '',
    formaPago: 'Transferencia',
    referencia: '',
    gastoId: '',
  });
  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const cambiar = (campo, valor) =>
    setDatos((actual) => {
      const siguiente = { ...actual, [campo]: valor };
      // Al elegir el gasto se precargan concepto, beneficiario y saldo: es lo
      // que se va a pagar, y volver a teclearlo invita a equivocarse.
      if (campo === 'gastoId' && valor) {
        const gasto = pendientes.find((g) => String(g.id) === String(valor));
        if (gasto) {
          siguiente.concepto = siguiente.concepto || `Pago ${gasto.concepto}`;
          siguiente.beneficiario = siguiente.beneficiario || gasto.proveedor;
          siguiente.monto = siguiente.monto || String(gasto.total);
        }
      }
      return siguiente;
    });

  const puedeGuardar = datos.concepto.trim() !== '' && Number(datos.monto) > 0;

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      await crearEgreso(datos);
      onGuardado();
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <div className={styles.fondo} onClick={onCerrar}>
      <div
        className={styles.dialogo}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Registrar pago"
      >
        <div className={styles.dialogoCabecera}>
          <span className={styles.dialogoTitulo}>Registrar pago</span>
          <button className={styles.btnIcono} onClick={onCerrar} aria-label="Cerrar">
            <X size={16} />
          </button>
        </div>

        <div className={styles.dialogoCuerpo}>
          {error && <div className={styles.errorCaja}>{error}</div>}

          <div className={styles.campoAncho}>
            <label htmlFor="gasto">Gasto que salda</label>
            <select
              id="gasto"
              className={styles.input}
              value={datos.gastoId}
              onChange={(e) => cambiar('gastoId', e.target.value)}
            >
              <option value="">Pago suelto, sin gasto asociado</option>
              {pendientes.map((gasto) => (
                <option key={gasto.id} value={gasto.id}>
                  {gasto.concepto} — {formatearMoneda(gasto.total)} ({gasto.estadoPago})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.campoAncho}>
            <label htmlFor="conceptoPago">Concepto *</label>
            <input
              id="conceptoPago"
              className={styles.input}
              value={datos.concepto}
              onChange={(e) => cambiar('concepto', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="fechaPago">Fecha</label>
            <input
              id="fechaPago"
              type="date"
              className={styles.input}
              value={datos.fecha}
              onChange={(e) => cambiar('fecha', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="monto">Monto *</label>
            <input
              id="monto"
              type="number"
              min="0"
              step="0.01"
              className={styles.input}
              value={datos.monto}
              onChange={(e) => cambiar('monto', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="beneficiario">Beneficiario</label>
            <input
              id="beneficiario"
              className={styles.input}
              value={datos.beneficiario}
              onChange={(e) => cambiar('beneficiario', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="formaPago">Forma de pago</label>
            <select
              id="formaPago"
              className={styles.input}
              value={datos.formaPago}
              onChange={(e) => cambiar('formaPago', e.target.value)}
            >
              {FORMAS_PAGO_EGRESO.map((forma) => (
                <option key={forma}>{forma}</option>
              ))}
            </select>
          </div>

          <div className={styles.campoAncho}>
            <label htmlFor="referencia">Referencia</label>
            <input
              id="referencia"
              className={styles.input}
              value={datos.referencia}
              onChange={(e) => cambiar('referencia', e.target.value)}
              placeholder="Número de transferencia o cheque"
            />
          </div>
        </div>

        <div className={styles.dialogoPie}>
          <button className={styles.btnSecundario} onClick={onCerrar}>
            Cancelar
          </button>
          <button
            className={styles.btnPrimary}
            onClick={guardar}
            disabled={!puedeGuardar || guardando}
          >
            {guardando ? 'Guardando…' : 'Registrar pago'}
          </button>
        </div>
      </div>
    </div>
  );
}

// --------------------------------------------------------------------------
// Tipos de gasto
// --------------------------------------------------------------------------

function PanelTipos({ recurso, onCambio, onError }) {
  const [nombre, setNombre] = useState('');
  const [deducible, setDeducible] = useState(true);

  const filas = useMemo(() => recurso.datos.map(tipoGastoDesdeApi), [recurso.datos]);

  const crear = async () => {
    if (!nombre.trim()) return;
    try {
      await crearTipoGasto({ nombre: nombre.trim(), deducible });
      setNombre('');
      setDeducible(true);
      onCambio();
    } catch (fallo) {
      onError(fallo.message);
    }
  };

  const desactivar = async (id) => {
    try {
      await desactivarTipoGasto(id);
      onCambio();
    } catch (fallo) {
      onError(fallo.message);
    }
  };

  return (
    <motion.section
      className={`${styles.panel} glass-panel`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className={styles.toolbar}>
        <div className={styles.buscador}>
          <Tags size={16} />
          <input
            placeholder="Nombre del nuevo tipo de gasto…"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && crear()}
          />
        </div>
        <label className={styles.select} style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={deducible}
            onChange={(e) => setDeducible(e.target.checked)}
          />
          Deducible
        </label>
        <button className={styles.btnPrimary} onClick={crear} disabled={!nombre.trim()}>
          <Plus size={16} /> Añadir
        </button>
      </div>

      {recurso.cargando ? (
        <TablaCargando columnas={3} filas={3} />
      ) : filas.length === 0 ? (
        <Vacio mensaje="Aún no hay tipos de gasto. Crea el primero arriba." />
      ) : (
        <div className={styles.tablaWrapper}>
          <table className={styles.tabla}>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Deducible</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filas.map((tipo) => (
                <tr key={tipo.id}>
                  <td className={styles.principal}>{tipo.nombre}</td>
                  <td>
                    <span
                      className={`${styles.insignia} ${
                        tipo.deducible ? styles.insigniaOk : styles.insigniaNeutro
                      }`}
                    >
                      {tipo.deducible ? 'Sí' : 'No'}
                    </span>
                  </td>
                  <td>
                    <div className={styles.acciones}>
                      <button
                        className={styles.btnIcono}
                        onClick={() => desactivar(tipo.id)}
                        title="Desactivar"
                        aria-label={`Desactivar ${tipo.nombre}`}
                      >
                        <TrendingDown size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.section>
  );
}
