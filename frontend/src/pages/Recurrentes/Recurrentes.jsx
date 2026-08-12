import { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import {
  CalendarClock,
  Pause,
  Pencil,
  Play,
  Plus,
  Repeat,
  Search,
  SearchX,
  Send,
  Trash2,
} from 'lucide-react';
import {
  eliminarPlantilla,
  emitirPlantilla,
  pausarPlantilla,
  plantillaDesdeApi,
} from '../../api/egresos';
import { useRecurso } from '../../hooks/useRecurso';
import { formatearMoneda } from '../../lib/sri/calculoComprobante';
import { contieneTexto } from '../../lib/texto';
import { ErrorCarga, TablaCargando } from '../../components/ui/EstadoCarga';
import PlantillaForm from './PlantillaForm';
import styles from '../Egresos/Egresos.module.css';

/**
 * Facturación recurrente.
 *
 * La emisión **no es automática**: la pantalla marca qué plantillas vencieron
 * y la persona confirma. Una factura emitida sola contra un cliente que ya
 * canceló el servicio hay que anularla con nota de crédito, y eso cuesta más
 * que pulsar un botón al mes.
 */

const hoyISO = () => new Date().toISOString().slice(0, 10);

export default function Recurrentes() {
  const recurso = useRecurso('/recurrentes', { parametros: { tamano: 200 }, datosDemo: [] });
  const [termino, setTermino] = useState('');
  const [error, setError] = useState(null);
  const [aviso, setAviso] = useState(null);
  // null = cerrado · 'nueva' = alta · objeto = edición de esa plantilla
  const [formulario, setFormulario] = useState(null);

  const plantillas = useMemo(
    () => recurso.datos.map(plantillaDesdeApi),
    [recurso.datos],
  );

  const hoy = hoyISO();
  const vencidas = plantillas.filter((p) => p.activa && p.proximaEmision <= hoy);

  const visibles = plantillas.filter(
    (p) => !termino || contieneTexto(p.nombre, termino) || contieneTexto(p.receptor, termino),
  );

  const accion = async (ejecutar, mensajeExito) => {
    setError(null);
    setAviso(null);
    try {
      const resultado = await ejecutar();
      if (mensajeExito) setAviso(mensajeExito(resultado));
      recurso.recargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Facturación recurrente</h1>
          <p className={styles.subtitle}>
            Arriendos, suscripciones e igualas. La factura se genera cuando tú lo confirmas,
            no sola: la emitida por error hay que anularla con nota de crédito.
          </p>
        </div>
        <button className={styles.btnPrimary} onClick={() => setFormulario('nueva')}>
          <Plus size={16} /> Nueva plantilla
        </button>
      </header>

      <div className={styles.resumen}>
        <Tarjeta etiqueta="Plantillas activas" valor={String(plantillas.filter((p) => p.activa).length)} />
        <Tarjeta etiqueta="Vencidas por emitir" valor={String(vencidas.length)} aviso={vencidas.length > 0} />
        <Tarjeta
          etiqueta="Importe mensual comprometido"
          valor={formatearMoneda(
            plantillas.filter((p) => p.activa).reduce((suma, p) => suma + p.total, 0),
          )}
          acento
        />
      </div>

      {error && <ErrorCarga mensaje={error} onReintentar={() => setError(null)} />}

      {aviso && (
        <div className={`${styles.panel} glass-panel`} style={{ padding: '14px 18px' }}>
          {aviso}{' '}
          <Link to="/comprobantes" style={{ color: 'var(--accent-primary)', fontWeight: 700 }}>
            Ver comprobantes
          </Link>
        </div>
      )}

      <motion.section
        className={`${styles.panel} glass-panel`}
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className={styles.toolbar}>
          <div className={styles.buscador}>
            <Search size={16} />
            <input
              placeholder="Buscar por nombre o cliente…"
              value={termino}
              onChange={(e) => setTermino(e.target.value)}
            />
          </div>
        </div>

        {recurso.cargando ? (
          <TablaCargando columnas={6} filas={4} />
        ) : recurso.error ? (
          <ErrorCarga mensaje={recurso.error} onReintentar={recurso.recargar} />
        ) : visibles.length === 0 ? (
          <div className={styles.vacio}>
            <SearchX size={30} />
            <p>Aún no hay plantillas recurrentes.</p>
            <button className={styles.btnPrimary} onClick={() => setFormulario('nueva')}>
              <Plus size={16} /> Crear la primera
            </button>
          </div>
        ) : (
          <div className={styles.tablaWrapper}>
            <table className={styles.tabla}>
              <thead>
                <tr>
                  <th>Plantilla</th>
                  <th>Periodicidad</th>
                  <th>Próxima emisión</th>
                  <th className={styles.numero}>Importe</th>
                  <th className={styles.numero}>Emitidas</th>
                  <th>Estado</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {visibles.map((plantilla) => {
                  const vencida = plantilla.activa && plantilla.proximaEmision <= hoy;
                  return (
                    <tr key={plantilla.id}>
                      <td>
                        <div className={styles.principal}>{plantilla.nombre}</div>
                        <div className={styles.secundario}>{plantilla.receptor}</div>
                      </td>
                      <td className={styles.secundario}>
                        <Repeat size={13} /> {plantilla.periodicidad}
                      </td>
                      <td>
                        <span
                          className={`${styles.insignia} ${
                            vencida ? styles.insigniaAviso : styles.insigniaNeutro
                          }`}
                        >
                          <CalendarClock size={12} /> {plantilla.proximaEmision}
                        </span>
                      </td>
                      <td className={`${styles.numero} ${styles.principal}`}>
                        {formatearMoneda(plantilla.total)}
                      </td>
                      <td className={styles.numero}>{plantilla.emitidas}</td>
                      <td>
                        <span
                          className={`${styles.insignia} ${
                            plantilla.activa ? styles.insigniaOk : styles.insigniaNeutro
                          }`}
                        >
                          {plantilla.activa ? 'Activa' : 'Pausada'}
                        </span>
                      </td>
                      <td>
                        <div className={styles.acciones}>
                          <button
                            className={styles.btnIcono}
                            disabled={!plantilla.activa}
                            title="Emitir la factura de este período"
                            aria-label={`Emitir ${plantilla.nombre}`}
                            onClick={() =>
                              accion(
                                () => emitirPlantilla(plantilla.id),
                                (r) =>
                                  `Factura ${r.datos.comprobante.numero} creada en borrador.`,
                              )
                            }
                          >
                            <Send size={15} />
                          </button>
                          <button
                            className={styles.btnIcono}
                            title="Editar"
                            aria-label={`Editar ${plantilla.nombre}`}
                            onClick={() => setFormulario(plantilla)}
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            className={styles.btnIcono}
                            title={plantilla.activa ? 'Pausar' : 'Reanudar'}
                            aria-label={`${plantilla.activa ? 'Pausar' : 'Reanudar'} ${plantilla.nombre}`}
                            onClick={() => accion(() => pausarPlantilla(plantilla.id))}
                          >
                            {plantilla.activa ? <Pause size={15} /> : <Play size={15} />}
                          </button>
                          <button
                            className={styles.btnIcono}
                            title="Eliminar la plantilla"
                            aria-label={`Eliminar ${plantilla.nombre}`}
                            onClick={() => accion(() => eliminarPlantilla(plantilla.id))}
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </motion.section>

      {formulario && (
        <PlantillaForm
          plantilla={formulario === 'nueva' ? null : formulario}
          onCerrar={() => setFormulario(null)}
          onGuardado={() => {
            setFormulario(null);
            recurso.recargar();
          }}
        />
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
