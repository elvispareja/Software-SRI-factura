import { useMemo, useState } from 'react';
import { Plus, Search, Trash2, X } from 'lucide-react';
import { PERIODICIDADES, actualizarPlantilla, crearPlantilla } from '../../api/egresos';
import { useCatalogos } from '../../hooks/useCatalogos';
import { TARIFAS_IVA } from '../../lib/sri/impuestos';
import { calcularComprobante, formatearMoneda } from '../../lib/sri/calculoComprobante';
import styles from '../Egresos/Egresos.module.css';

/**
 * Alta y edición de una plantilla recurrente.
 *
 * El total se calcula con el **mismo motor** que las facturas, no con una
 * multiplicación aparte: lo que se enseña aquí es exactamente lo que se
 * facturará cada período, y dos fórmulas distintas acabarían discrepando.
 */

let contador = 0;
const nuevaLinea = () => ({
  id: `linea-${++contador}`,
  codigo: '',
  descripcion: '',
  cantidad: '1',
  precioUnitario: '',
  codigoIva: '4',
});

const hoyISO = () => new Date().toISOString().slice(0, 10);

export default function PlantillaForm({ plantilla, onCerrar, onGuardado }) {
  const catalogos = useCatalogos();
  const editando = Boolean(plantilla);

  const [datos, setDatos] = useState(() => ({
    nombre: plantilla?.nombre ?? '',
    periodicidad: plantilla?.periodicidad ?? 'Mensual',
    proximaEmision: plantilla?.proximaEmision ?? hoyISO(),
    hasta: plantilla?.hasta ?? '',
    activa: plantilla?.activa ?? true,
  }));

  const [receptorId, setReceptorId] = useState('');
  const [busqueda, setBusqueda] = useState(plantilla?.receptor ?? '');
  const [enfocado, setEnfocado] = useState(false);

  const [lineas, setLineas] = useState(() =>
    plantilla?.lineas?.length
      ? plantilla.lineas.map((l, i) => ({
          id: `linea-existente-${i}`,
          codigo: l.codigo,
          descripcion: l.descripcion,
          cantidad: String(l.cantidad),
          precioUnitario: String(l.precioUnitario),
          codigoIva: l.codigoIva,
        }))
      : [nuevaLinea()],
  );

  const [error, setError] = useState(null);
  const [guardando, setGuardando] = useState(false);

  const resultados = useMemo(
    () => catalogos.buscarReceptores(busqueda, 'Cliente'),
    [catalogos, busqueda],
  );

  // El mismo motor que las facturas: lo que se ve aquí es lo que se emitirá.
  const calculo = useMemo(() => calcularComprobante(lineas), [lineas]);

  const errores = useMemo(() => {
    const lista = [];
    if (!datos.nombre.trim()) lista.push('Ponle un nombre a la plantilla.');
    if (!receptorId && !editando) lista.push('Elige el cliente al que se factura.');
    if (!datos.proximaEmision) lista.push('Indica la fecha de la próxima emisión.');
    if (datos.hasta && datos.hasta < datos.proximaEmision) {
      lista.push('La fecha de fin no puede ser anterior a la próxima emisión.');
    }
    if (lineas.length === 0) lista.push('Agrega al menos una línea.');
    if (lineas.some((l) => !l.descripcion.trim())) {
      lista.push('Todas las líneas necesitan descripción.');
    }
    if (calculo.importeTotal <= 0) lista.push('El importe de la plantilla debe ser mayor que cero.');
    return lista;
  }, [datos, receptorId, editando, lineas, calculo]);

  const cambiar = (campo, valor) => setDatos((a) => ({ ...a, [campo]: valor }));

  const cambiarLinea = (id, campo, valor) =>
    setLineas((actuales) =>
      actuales.map((l) => (l.id === id ? { ...l, [campo]: valor } : l)),
    );

  const agregarArticulo = (articulo) => {
    setLineas((actuales) => [
      ...actuales.filter((l) => l.descripcion.trim() !== '' || l.precioUnitario !== ''),
      {
        id: `linea-${++contador}`,
        codigo: articulo.codigo,
        descripcion: articulo.nombre,
        cantidad: '1',
        precioUnitario: String(articulo.precio),
        codigoIva: articulo.codigoIva,
      },
    ]);
  };

  const guardar = async () => {
    setGuardando(true);
    setError(null);
    try {
      const cuerpo = { ...datos, hasta: datos.hasta || null };
      const id = receptorId || plantilla?.receptorId;

      if (editando) {
        await actualizarPlantilla(plantilla.id, cuerpo, Number(id), lineas);
      } else {
        await crearPlantilla(cuerpo, Number(id), lineas);
      }
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
        style={{ maxWidth: 760 }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={editando ? 'Editar plantilla' : 'Nueva plantilla recurrente'}
      >
        <div className={styles.dialogoCabecera}>
          <span className={styles.dialogoTitulo}>
            {editando ? 'Editar plantilla' : 'Nueva plantilla recurrente'}
          </span>
          <button className={styles.btnIcono} onClick={onCerrar} aria-label="Cerrar">
            <X size={16} />
          </button>
        </div>

        <div className={styles.dialogoCuerpo}>
          {error && <div className={styles.errorCaja}>{error}</div>}

          <div className={styles.campoAncho}>
            <label htmlFor="nombre">Nombre de la plantilla *</label>
            <input
              id="nombre"
              className={styles.input}
              value={datos.nombre}
              onChange={(e) => cambiar('nombre', e.target.value)}
              placeholder="Arriendo local comercial, suscripción mensual…"
            />
          </div>

          {/* Cliente */}
          <div className={styles.campoAncho} style={{ position: 'relative' }}>
            <label htmlFor="cliente">Cliente *</label>
            <div className={styles.buscador}>
              <Search size={15} />
              <input
                id="cliente"
                placeholder="Buscar cliente por nombre o identificación…"
                value={busqueda}
                onChange={(e) => {
                  setBusqueda(e.target.value);
                  setReceptorId('');
                }}
                onFocus={() => setEnfocado(true)}
                onBlur={() => setEnfocado(false)}
              />
            </div>
            {enfocado && busqueda.trim() !== '' && !receptorId && (
              <ul
                className={`${styles.panel} glass-panel`}
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  zIndex: 5,
                  listStyle: 'none',
                  maxHeight: 200,
                  overflowY: 'auto',
                }}
              >
                {resultados.length === 0 && (
                  <li style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>
                    Sin clientes que coincidan.
                  </li>
                )}
                {resultados.map((receptor) => (
                  <li key={receptor.id}>
                    <button
                      type="button"
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        width: '100%',
                        padding: '10px 14px',
                        textAlign: 'left',
                      }}
                      onMouseDown={(evento) => {
                        evento.preventDefault();
                        setReceptorId(receptor.id);
                        setBusqueda(receptor.razonSocial);
                      }}
                    >
                      <span>{receptor.razonSocial}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{receptor.identificacion}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className={styles.campo}>
            <label htmlFor="periodicidad">Periodicidad</label>
            <select
              id="periodicidad"
              className={styles.input}
              value={datos.periodicidad}
              onChange={(e) => cambiar('periodicidad', e.target.value)}
            >
              {PERIODICIDADES.map((valor) => (
                <option key={valor}>{valor}</option>
              ))}
            </select>
          </div>

          <div className={styles.campo}>
            <label htmlFor="proxima">Próxima emisión *</label>
            <input
              id="proxima"
              type="date"
              className={styles.input}
              value={datos.proximaEmision}
              onChange={(e) => cambiar('proximaEmision', e.target.value)}
            />
          </div>

          <div className={styles.campo}>
            <label htmlFor="hasta">Emitir hasta</label>
            <input
              id="hasta"
              type="date"
              className={styles.input}
              value={datos.hasta}
              min={datos.proximaEmision || undefined}
              onChange={(e) => cambiar('hasta', e.target.value)}
            />
            <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Sin fecha, la plantilla es indefinida.
            </span>
          </div>

          <div className={styles.campo}>
            <label htmlFor="activa">Estado</label>
            <select
              id="activa"
              className={styles.input}
              value={datos.activa ? 'activa' : 'pausada'}
              onChange={(e) => cambiar('activa', e.target.value === 'activa')}
            >
              <option value="activa">Activa</option>
              <option value="pausada">Pausada</option>
            </select>
          </div>

          {/* Líneas */}
          <div className={styles.campoAncho}>
            <label>Líneas de la factura</label>

            <div className={styles.buscador} style={{ marginBottom: 10 }}>
              <Search size={15} />
              <input
                placeholder="Buscar un artículo para añadirlo…"
                onChange={(e) => {
                  const encontrados = catalogos.buscarArticulos(e.target.value);
                  if (encontrados.length === 1) {
                    agregarArticulo(encontrados[0]);
                    e.target.value = '';
                  }
                }}
              />
            </div>

            <table className={styles.tabla}>
              <thead>
                <tr>
                  <th>Descripción</th>
                  <th style={{ width: 80 }}>Cant.</th>
                  <th style={{ width: 110 }}>P. unit.</th>
                  <th style={{ width: 110 }}>IVA</th>
                  <th className={styles.numero} style={{ width: 110 }}>
                    Total
                  </th>
                  <th style={{ width: 44 }} />
                </tr>
              </thead>
              <tbody>
                {calculo.detalles.map((linea) => (
                  <tr key={linea.id}>
                    <td>
                      <input
                        className={styles.input}
                        value={linea.descripcion}
                        aria-label="Descripción de la línea"
                        onChange={(e) => cambiarLinea(linea.id, 'descripcion', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className={styles.input}
                        value={linea.cantidad}
                        aria-label="Cantidad"
                        onChange={(e) => cambiarLinea(linea.id, 'cantidad', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        className={styles.input}
                        value={linea.precioUnitario}
                        aria-label="Precio unitario"
                        onChange={(e) =>
                          cambiarLinea(linea.id, 'precioUnitario', e.target.value)
                        }
                      />
                    </td>
                    <td>
                      <select
                        className={styles.input}
                        value={linea.codigoIva}
                        aria-label="Tarifa de IVA"
                        onChange={(e) => cambiarLinea(linea.id, 'codigoIva', e.target.value)}
                      >
                        {TARIFAS_IVA.map((tarifa) => (
                          <option key={tarifa.codigo} value={tarifa.codigo}>
                            {tarifa.etiquetaCorta}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className={styles.numero}>{formatearMoneda(linea.total)}</td>
                    <td>
                      <button
                        className={styles.btnIcono}
                        aria-label="Quitar línea"
                        onClick={() =>
                          setLineas((actuales) => actuales.filter((l) => l.id !== linea.id))
                        }
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              className={styles.btnSecundario}
              style={{ marginTop: 10 }}
              onClick={() => setLineas((actuales) => [...actuales, nuevaLinea()])}
            >
              <Plus size={14} /> Añadir línea
            </button>
          </div>

          <div className={styles.total}>
            <span>Importe de cada emisión</span>
            <strong>{formatearMoneda(calculo.importeTotal)}</strong>
          </div>

          {errores.length > 0 && (
            <div className={styles.errorCaja} style={{ background: 'var(--warning-soft)', color: 'var(--warning)' }}>
              {errores[0]}
            </div>
          )}
        </div>

        <div className={styles.dialogoPie}>
          <button className={styles.btnSecundario} onClick={onCerrar}>
            Cancelar
          </button>
          <button
            className={styles.btnPrimary}
            onClick={guardar}
            disabled={errores.length > 0 || guardando || catalogos.usandoDemo}
            title={catalogos.usandoDemo ? 'Sin conexión con el servidor.' : errores[0]}
          >
            {guardando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear plantilla'}
          </button>
        </div>
      </div>
    </div>
  );
}
