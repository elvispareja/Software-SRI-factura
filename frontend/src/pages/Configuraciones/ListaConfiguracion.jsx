import { useMemo, useState } from 'react';
import { Plus, RefreshCw, Search, Trash2 } from 'lucide-react';
import { crearEnLista, desactivarEnLista, listaDesdeApi } from '../../api/configuracion';
import { LISTAS } from './listas';
import { useRecurso } from '../../hooks/useRecurso';
import { contieneTexto } from '../../lib/texto';
import { TablaCargando } from '../../components/ui/EstadoCarga';
import styles from './Configuraciones.module.css';

/**
 * Listados de configuración: zonas, vendedores, leyendas, usuarios e impuestos.
 *
 * Los tres primeros los define el negocio y se editan aquí. Los usuarios son
 * de solo lectura —el alta pasa por el registro, que es donde se aplica el
 * hash de la contraseña— y los impuestos también, porque sus códigos viajan
 * literalmente en el XML y cambiarlos hace que el SRI rechace el comprobante.
 */

export default function ListaConfiguracion({ seccion }) {
  const config = LISTAS[seccion];
  const recurso = useRecurso(config.ruta, { datosDemo: [] });

  const [termino, setTermino] = useState('');
  const [nombre, setNombre] = useState('');
  const [detalle, setDetalle] = useState('');
  const [error, setError] = useState(null);

  const filas = useMemo(() => {
    const datos = recurso.datos ?? [];
    if (config.soloLectura) return datos;
    if (config.adaptador) return datos.map(config.adaptador);
    return datos.map(listaDesdeApi);
  }, [recurso.datos, config]);

  const visibles = filas.filter(
    (fila) =>
      !termino ||
      contieneTexto(fila.nombre ?? fila.descripcion ?? '', termino) ||
      contieneTexto(fila.correo ?? fila.detalle ?? '', termino),
  );

  const agregar = async () => {
    if (!nombre.trim()) return;
    setError(null);
    try {
      await crearEnLista(config.tipo, { nombre: nombre.trim(), detalle });
      setNombre('');
      setDetalle('');
      recurso.recargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  };

  const quitar = async (id) => {
    setError(null);
    try {
      await desactivarEnLista(config.tipo, id);
      recurso.recargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  };

  return (
    <div className={styles.cwoCard}>
      <div className={styles.cwoListHead}>
        <div style={{ flex: 1 }}>
          <div className={styles.cwoListTitle}>{config.titulo}</div>
          <div className={styles.cwoListSub}>{config.subtitulo}</div>
        </div>
      </div>

      {error && <div className={styles.cwoEmpty} style={{ color: 'var(--error)' }}>{error}</div>}

      <div className={styles.cwoToolbar}>
        <span className={styles.cwoSearch}>
          <Search size={15} />
          <input
            value={termino}
            onChange={(e) => setTermino(e.target.value)}
            placeholder="Buscar"
          />
        </span>
        <button className={styles.cwoIconBtn} onClick={recurso.recargar} title="Actualizar">
          <RefreshCw size={16} />
        </button>
        <span className={styles.cwoCount}>{visibles.length}</span>
      </div>

      {config.editable && (
        <div className={styles.cwoToolbar}>
          <span className={styles.cwoSearch} style={{ flex: '1 1 200px' }}>
            <input
              value={nombre}
              onChange={(e) => setNombre(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && agregar()}
              placeholder={`Nombre de la ${config.etiquetaAlta.toLowerCase()}`}
              aria-label={`Nombre de la ${config.etiquetaAlta.toLowerCase()}`}
            />
          </span>
          <span className={styles.cwoSearch} style={{ flex: '1 1 200px' }}>
            <input
              value={detalle}
              onChange={(e) => setDetalle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && agregar()}
              placeholder="Detalle (opcional)"
              aria-label="Detalle"
            />
          </span>
          <button className={styles.btnPrimary} onClick={agregar} disabled={!nombre.trim()}>
            <Plus size={15} /> {config.etiquetaAlta}
          </button>
        </div>
      )}

      {recurso.cargando ? (
        <TablaCargando columnas={config.columnas.length} filas={3} />
      ) : (
        <div className={styles.cwoTableWrap}>
          <table className={styles.cwoTable}>
            <thead>
              <tr>
                {config.columnas.map((columna) => (
                  <th key={columna}>{columna}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visibles.length === 0 ? (
                <tr>
                  <td colSpan={config.columnas.length} className={styles.cwoEmpty}>
                    {config.vacio}
                  </td>
                </tr>
              ) : (
                visibles.map((fila) => (
                  <Fila
                    key={fila.id ?? fila.codigo}
                    fila={fila}
                    config={config}
                    onQuitar={quitar}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className={styles.cwoFoot}>
        <span>
          Viendo {visibles.length === 0 ? 0 : 1} a {visibles.length} de {filas.length} entradas
        </span>
      </div>
    </div>
  );
}

function Fila({ fila, config, onQuitar }) {
  if (config.soloLectura) {
    return (
      <tr>
        <td>{fila.nombre}</td>
        <td className="cifra">{fila.codigo}</td>
        <td className="cifra">{fila.porcentaje}%</td>
      </tr>
    );
  }

  if (config.adaptador) {
    return (
      <tr>
        <td>{fila.nombre}</td>
        <td>{fila.correo}</td>
        <td>{fila.rol}</td>
        <td>{fila.activo ? 'Activo' : 'Inactivo'}</td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{fila.nombre}</td>
      <td>{fila.detalle || '—'}</td>
      <td>{fila.estado}</td>
      <td>
        <button
          className={styles.cwoIconBtn}
          onClick={() => onQuitar(fila.id)}
          title="Desactivar"
          aria-label={`Desactivar ${fila.nombre}`}
        >
          <Trash2 size={15} />
        </button>
      </td>
    </tr>
  );
}
