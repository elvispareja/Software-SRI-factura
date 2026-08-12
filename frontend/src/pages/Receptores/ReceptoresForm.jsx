import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Search, AlertCircle, CheckCircle2, Lock } from 'lucide-react';
import {
  TIPOS_IDENTIFICACION,
  TIPOS_PERSONA,
  ROLES_RECEPTOR,
} from '../../data/catalogoReceptores';
import { NOMBRES_PROVINCIAS, cantonesDe } from '../../data/geografiaEcuador';
import { validarIdentificacion } from '../../lib/sri/identificacion';
import { api, ErrorApi } from '../../api/cliente';
import { receptorDesdeApi, receptorHaciaApi } from '../../api/adaptadores';
import styles from './Receptores.module.css';

const METODOS_CANCELACION = ['Contado', 'Crédito'];
const LISTAS_PRECIO = ['PVP 1', 'PVP 2', 'PVP 3', 'PVP 4', 'PVP 5', 'PVP 6'];
const VENDEDORES = ['Sin asignar', 'Ana Salazar', 'Diego Ruiz', 'Paola Chávez'];
const ZONAS = ['Sin zona', 'Norte', 'Centro', 'Sur', 'Valles'];

const RECEPTOR_INICIAL = {
  tipoIdentificacion: 'RUC',
  identificacion: '',
  razonSocial: '',
  nombreComercial: '',
  rol: 'Cliente',
  tipoPersona: 'Jurídica',
  correo: '',
  telefono1: '',
  direccion: '',
  provincia: '',
  canton: '',
  telefono2: '',
  correo2: '',
  correo3: '',
  metodoCancelacion: 'Contado',
  vendedor: 'Sin asignar',
  listaPrecio: 'PVP 1',
  zona: 'Sin zona',
  descuento: '0',
  codigoInterno: '',
  creditoMaximo: '0',
};

const PESTANAS = [
  { id: 'principales', etiqueta: 'Datos Principales' },
  { id: 'adicionales', etiqueta: 'Datos Adicionales' },
  { id: 'comercial', etiqueta: 'Configuración Comercial' },
];

/**
 * Formulario crear/editar receptor.
 * - Si useParams().id existe → modo edición: precarga GET /receptores/:id con AbortController.
 * - identidadBloqueada inicia bloqueada en crear, desbloqueada en editar (banner "Corregir identidad").
 * - Guardar: PUT /receptores/:id si edita, POST si crea. Maneja 409 y 422 como ayudaError y navega a /receptores.
 */
export default function ReceptoresForm() {
  const { id } = useParams();
  const navigate = useNavigate();
  const esEdicion = Boolean(id);

  const [pestana, setPestana] = useState('principales');
  const [receptor, setReceptor] = useState(RECEPTOR_INICIAL);
  // Al crear, editable de entrada: no hay ninguna identidad previa que
  // proteger. Al editar, bloqueada de entrada: la identificación ata el
  // comprobante autorizado al receptor, y reescribirla sin fricción dejaría
  // esos comprobantes apuntando a otra persona. El toggle de abajo es la
  // única forma de desbloquearla, a propósito.
  const [identidadBloqueada, setIdentidadBloqueada] = useState(esEdicion);
  const [consultandoSri, setConsultandoSri] = useState(false);
  const [cargando, setCargando] = useState(Boolean(esEdicion));
  const [errorCarga, setErrorCarga] = useState(null);
  const [guardando, setGuardando] = useState(false);
  const [ayudaError, setAyudaError] = useState(null);

  // Precarga en modo edición
  useEffect(() => {
    if (!esEdicion) return undefined;
    const controlador = new AbortController();
    setCargando(true);
    setErrorCarga(null);
    api
      .obtener(`/receptores/${id}`, undefined, { senal: controlador.signal })
      .then(({ datos }) => {
        if (controlador.signal.aborted) return;
        const mapeado = receptorDesdeApi(datos);
        setReceptor((prev) => ({
          ...prev,
          tipoIdentificacion: mapeado.tipoIdentificacion ?? prev.tipoIdentificacion,
          identificacion: mapeado.identificacion ?? '',
          razonSocial: mapeado.razonSocial ?? '',
          nombreComercial: mapeado.nombreComercial ?? '',
          rol: mapeado.rol ?? prev.rol,
          tipoPersona: mapeado.tipoPersona ?? prev.tipoPersona,
          correo: mapeado.correo ?? '',
          correo2: mapeado.correo2 ?? '',
          telefono1: mapeado.telefono1 ?? '',
          telefono2: mapeado.telefono2 ?? '',
          direccion: mapeado.direccion ?? '',
          provincia: mapeado.provincia ?? '',
          canton: mapeado.canton ?? '',
          metodoCancelacion: mapeado.metodoCancelacion ?? prev.metodoCancelacion,
          vendedor: mapeado.vendedor ?? prev.vendedor,
          listaPrecio: mapeado.listaPrecio ?? prev.listaPrecio,
          zona: mapeado.zona ?? prev.zona,
          descuento: mapeado.descuento ?? '0',
          creditoMaximo: mapeado.creditoMaximo ?? '0',
        }));
      })
      .catch((fallo) => {
        if (fallo.name === 'AbortError') return;
        setErrorCarga(fallo instanceof ErrorApi ? fallo.message : 'No se pudo cargar el receptor.');
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCargando(false);
      });
    return () => controlador.abort();
  }, [esEdicion, id]);

  // Si cambia el id (navegar de un receptor a otro sin desmontar), re-sincronizar.
  useEffect(() => {
    setIdentidadBloqueada(esEdicion);
  }, [esEdicion]);

  const validacion = useMemo(
    () => validarIdentificacion(receptor.tipoIdentificacion, receptor.identificacion),
    [receptor.tipoIdentificacion, receptor.identificacion],
  );

  const cantones = useMemo(() => cantonesDe(receptor.provincia), [receptor.provincia]);

  const actualizar = (campo, valor) =>
    setReceptor((actual) => {
      if (campo === 'provincia') return { ...actual, provincia: valor, canton: '' };
      return { ...actual, [campo]: valor };
    });

  const camposObligatoriosCompletos =
    validacion.esValida &&
    receptor.razonSocial.trim() !== '' &&
    receptor.direccion.trim() !== '' &&
    receptor.correo.trim() !== '';

  /** Simula la consulta al SRI: el backend hará la llamada real. Propaga 409 si existiera. */
  const consultarSri = () => {
    if (!validacion.esValida) return;
    setConsultandoSri(true);
    setAyudaError(null);
    setTimeout(() => setConsultandoSri(false), 700);
  };

  const guardar = async () => {
    if (!camposObligatoriosCompletos || guardando) return;
    setAyudaError(null);
    setGuardando(true);
    try {
      const payload = receptorHaciaApi(receptor);
      // correo3 no existe en el backend: se ignora
      if (esEdicion) {
        await api.actualizar(`/receptores/${id}`, payload);
      } else {
        await api.crear('/receptores', payload);
      }
      navigate('/receptores');
    } catch (fallo) {
      if (fallo instanceof ErrorApi) {
        if (fallo.estado === 409) {
          setAyudaError(fallo.message);
        } else if (fallo.estado === 422) {
          setAyudaError(fallo.message);
        } else {
          setAyudaError(fallo.message || 'No se pudo guardar el receptor.');
        }
      } else {
        setAyudaError('No se pudo guardar el receptor.');
      }
    } finally {
      setGuardando(false);
    }
  };

  if (cargando) {
    return (
      <div className={styles.container}>
        <p style={{ color: 'var(--text-secondary)', padding: 24 }}>Cargando receptor…</p>
      </div>
    );
  }

  if (errorCarga) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.headerTitleGroup}>
            <Link to="/receptores" className={styles.btnIcon} aria-label="Volver a receptores">
              <ArrowLeft size={20} />
            </Link>
            <div>
              <h1 className={styles.title}>{esEdicion ? 'Editar Receptor' : 'Nuevo Receptor'}</h1>
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
          <Link to="/receptores" className={styles.btnIcon} aria-label="Volver a receptores">
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className={styles.title}>{esEdicion ? 'Editar Receptor' : 'Nuevo Receptor'}</h1>
            <p className={styles.subtitle}>
              {esEdicion
                ? 'Corrige los datos del receptor y guarda los cambios.'
                : 'Ingresa los datos para registrar un cliente, proveedor o transportista.'}
            </p>
          </div>
        </div>
        <div className={styles.headerActions}>
          <button
            className={styles.btnPrimary}
            disabled={!camposObligatoriosCompletos || guardando}
            onClick={guardar}
            title={
              camposObligatoriosCompletos
                ? undefined
                : 'Completa identificación, razón social, correo y dirección.'
            }
          >
            <Save size={18} /> {guardando ? 'Guardando…' : esEdicion ? 'Actualizar' : 'Guardar Receptor'}
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
            {pestana === 'principales' && (
              <motion.div
                key="principales"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.formGrid}
              >
                <div className={styles.formGroup}>
                  <label htmlFor="tipoId">Tipo de Identificación *</label>
                  <select
                    id="tipoId"
                    className={styles.input}
                    value={receptor.tipoIdentificacion}
                    disabled={identidadBloqueada}
                    onChange={(e) => actualizar('tipoIdentificacion', e.target.value)}
                  >
                    {TIPOS_IDENTIFICACION.map((tipo) => (
                      <option key={tipo}>{tipo}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="identificacion">Número de Identificación *</label>
                  <div className={styles.inputWithAction}>
                    <input
                      id="identificacion"
                      className={`${styles.input} ${
                        receptor.identificacion && !validacion.esValida ? styles.inputError : ''
                      }`}
                      placeholder="Ej: 1790016919001"
                      value={receptor.identificacion}
                      disabled={identidadBloqueada}
                      inputMode="numeric"
                      onChange={(e) => actualizar('identificacion', e.target.value)}
                    />
                    <button
                      className={styles.btnAction}
                      title="Buscar en SRI"
                      onClick={consultarSri}
                      disabled={!validacion.esValida || consultandoSri}
                      type="button"
                    >
                      <Search size={18} />
                    </button>
                  </div>
                  {receptor.identificacion !== '' && (
                    <span className={validacion.esValida ? styles.ayudaOk : styles.ayudaError}>
                      {validacion.esValida ? (
                        <>
                          <CheckCircle2 size={14} /> Identificación válida
                          {validacion.tipo ? ` · ${validacion.tipo}` : ''}
                        </>
                      ) : (
                        <>
                          <AlertCircle size={14} /> {validacion.error}
                        </>
                      )}
                    </span>
                  )}
                </div>

                <div className={styles.formGroupFull}>
                  <div className={styles.alertBox}>
                    <Lock size={20} className={styles.alertIcon} />
                    <div className={styles.alertContent}>
                      <h4>{esEdicion && !identidadBloqueada ? 'Corregir identidad' : identidadBloqueada ? 'Identidad bloqueada' : 'Identidad desbloqueada'}</h4>
                      <p>
                        {esEdicion && !identidadBloqueada
                          ? 'La identificación está desbloqueada para corregir un error de digitación. Si cambias el RUC/cédula y ya existe otro receptor con ese número, verás un error 409.'
                          : 'La identificación se bloquea para no dejar comprobantes ya emitidos apuntando a otra persona. Actívalo solo para corregir un error de digitación.'}
                      </p>
                    </div>
                    <label className={styles.toggle} title="Corregir identidad">
                      <input
                        type="checkbox"
                        checked={!identidadBloqueada}
                        onChange={(e) => setIdentidadBloqueada(!e.target.checked)}
                      />
                      <span className={styles.slider}></span>
                    </label>
                  </div>
                </div>

                <div className={styles.formGroupFull}>
                  <label htmlFor="razonSocial">Razón Social / Nombres Completos *</label>
                  <input
                    id="razonSocial"
                    className={styles.input}
                    placeholder="Nombre legal de la empresa o persona"
                    value={receptor.razonSocial}
                    onChange={(e) => actualizar('razonSocial', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="rol">Rol *</label>
                  <select
                    id="rol"
                    className={styles.input}
                    value={receptor.rol}
                    onChange={(e) => actualizar('rol', e.target.value)}
                  >
                    {ROLES_RECEPTOR.map((rol) => (
                      <option key={rol}>{rol}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="tipoPersona">Tipo de Persona *</label>
                  <select
                    id="tipoPersona"
                    className={styles.input}
                    value={receptor.tipoPersona}
                    onChange={(e) => actualizar('tipoPersona', e.target.value)}
                  >
                    {TIPOS_PERSONA.map((tipo) => (
                      <option key={tipo}>{tipo}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="correo">Correo Electrónico *</label>
                  <input
                    id="correo"
                    type="email"
                    className={styles.input}
                    placeholder="correo@empresa.com"
                    value={receptor.correo}
                    onChange={(e) => actualizar('correo', e.target.value)}
                  />
                  <span className={styles.ayuda}>A esta dirección se envía el XML y el PDF.</span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="telefono1">Teléfono #1</label>
                  <input
                    id="telefono1"
                    type="tel"
                    className={styles.input}
                    placeholder="0999999999"
                    value={receptor.telefono1}
                    onChange={(e) => actualizar('telefono1', e.target.value)}
                  />
                </div>

                <div className={styles.formGroupFull}>
                  <label htmlFor="direccion">Dirección *</label>
                  <textarea
                    id="direccion"
                    className={styles.input}
                    rows="2"
                    placeholder="Ej: Av. Amazonas N21-147 y Roca"
                    value={receptor.direccion}
                    onChange={(e) => actualizar('direccion', e.target.value)}
                  ></textarea>
                  <span className={styles.ayuda}>
                    Obligatoria para el comprobante electrónico: viaja en el XML como
                    <code> direccionComprador</code>.
                  </span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="provincia">Provincia</label>
                  <select
                    id="provincia"
                    className={styles.input}
                    value={receptor.provincia}
                    onChange={(e) => actualizar('provincia', e.target.value)}
                  >
                    <option value="">Seleccionar provincia…</option>
                    {NOMBRES_PROVINCIAS.map((provincia) => (
                      <option key={provincia}>{provincia}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="canton">Cantón</label>
                  <select
                    id="canton"
                    className={styles.input}
                    value={receptor.canton}
                    disabled={cantones.length === 0}
                    onChange={(e) => actualizar('canton', e.target.value)}
                  >
                    <option value="">
                      {cantones.length === 0 ? 'Elige una provincia primero' : 'Seleccionar cantón…'}
                    </option>
                    {cantones.map((canton) => (
                      <option key={canton}>{canton}</option>
                    ))}
                  </select>
                </div>
              </motion.div>
            )}

            {pestana === 'adicionales' && (
              <motion.div
                key="adicionales"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.formGrid}
              >
                <div className={styles.formGroupFull}>
                  <label htmlFor="nombreComercial">Nombre Comercial</label>
                  <input
                    id="nombreComercial"
                    className={styles.input}
                    placeholder="Nombre de fantasía (opcional)"
                    value={receptor.nombreComercial}
                    onChange={(e) => actualizar('nombreComercial', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="telefono2">Teléfono #2</label>
                  <input
                    id="telefono2"
                    type="tel"
                    className={styles.input}
                    placeholder="Alternativo"
                    value={receptor.telefono2}
                    onChange={(e) => actualizar('telefono2', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="correo2">Correo #2</label>
                  <input
                    id="correo2"
                    type="email"
                    className={styles.input}
                    placeholder="copia@empresa.com"
                    value={receptor.correo2}
                    onChange={(e) => actualizar('correo2', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="correo3">Correo #3</label>
                  <input
                    id="correo3"
                    type="email"
                    className={styles.input}
                    placeholder="contabilidad@empresa.com"
                    value={receptor.correo3}
                    onChange={(e) => actualizar('correo3', e.target.value)}
                  />
                </div>

                <div className={styles.formGroupFull}>
                  <span className={styles.ayuda}>
                    Los correos adicionales reciben copia del comprobante autorizado.
                  </span>
                </div>
              </motion.div>
            )}

            {pestana === 'comercial' && (
              <motion.div
                key="comercial"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className={styles.formGrid}
              >
                <div className={styles.formGroup}>
                  <label htmlFor="metodoCancelacion">Método de Cancelación</label>
                  <select
                    id="metodoCancelacion"
                    className={styles.input}
                    value={receptor.metodoCancelacion}
                    onChange={(e) => actualizar('metodoCancelacion', e.target.value)}
                  >
                    {METODOS_CANCELACION.map((metodo) => (
                      <option key={metodo}>{metodo}</option>
                    ))}
                  </select>
                  <span className={styles.ayuda}>Se propone por defecto al facturar.</span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="vendedor">Vendedor Asignado</label>
                  <select
                    id="vendedor"
                    className={styles.input}
                    value={receptor.vendedor}
                    onChange={(e) => actualizar('vendedor', e.target.value)}
                  >
                    {VENDEDORES.map((vendedor) => (
                      <option key={vendedor}>{vendedor}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="listaPrecio">Precio a Facturar</label>
                  <select
                    id="listaPrecio"
                    className={styles.input}
                    value={receptor.listaPrecio}
                    onChange={(e) => actualizar('listaPrecio', e.target.value)}
                  >
                    {LISTAS_PRECIO.map((lista) => (
                      <option key={lista}>{lista}</option>
                    ))}
                  </select>
                  <span className={styles.ayuda}>Lista de precios que se aplica a este cliente.</span>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="zona">Zona</label>
                  <select
                    id="zona"
                    className={styles.input}
                    value={receptor.zona}
                    onChange={(e) => actualizar('zona', e.target.value)}
                  >
                    {ZONAS.map((zona) => (
                      <option key={zona}>{zona}</option>
                    ))}
                  </select>
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="descuento">% Descuento Global</label>
                  <input
                    id="descuento"
                    type="number"
                    min="0"
                    max="100"
                    className={styles.input}
                    value={receptor.descuento}
                    onChange={(e) => actualizar('descuento', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="codigoInterno">Código Interno</label>
                  <input
                    id="codigoInterno"
                    className={styles.input}
                    placeholder="Identificador propio"
                    value={receptor.codigoInterno}
                    onChange={(e) => actualizar('codigoInterno', e.target.value)}
                  />
                </div>

                <div className={styles.formGroup}>
                  <label htmlFor="creditoMaximo">Crédito Máximo ($)</label>
                  <input
                    id="creditoMaximo"
                    type="number"
                    min="0"
                    step="0.01"
                    className={styles.input}
                    value={receptor.creditoMaximo}
                    onChange={(e) => actualizar('creditoMaximo', e.target.value)}
                  />
                  <span className={styles.ayuda}>0 significa sin límite de crédito asignado.</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
