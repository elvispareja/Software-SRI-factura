import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Building2,
  ShieldCheck,
  Landmark,
  Save,
  Plus,
  Trash2,
  Upload,
  AlertTriangle,
  CheckCircle2,
  Search,
  Loader2,
  User,
  Percent,
  FileText,
  Printer,
  Users,
  MapPin,
  UserCog,
  Image as ImageIcon,
  ScrollText,
  Plug2,
  Eye,
  RefreshCw,
  X,
} from 'lucide-react';
import {
  EMPRESA_INICIAL,
  ESTABLECIMIENTOS_INICIALES,
  CUENTAS_BANCARIAS_INICIALES,
  FIRMA_INICIAL,
  REGIMENES,
  AMBIENTES_SRI,
  diasParaExpirar,
} from '../../data/configuracionEmpresa';
import { NOMBRES_PROVINCIAS, cantonesDe } from '../../data/geografiaEcuador';
import { validarRuc } from '../../lib/sri/identificacion';
import { useRecurso } from '../../hooks/useRecurso';
import { useSesion } from '../../auth/useSesion';
import {
  actualizarEstablecimiento as actualizarEstablecimientoApi,
  actualizarPerfil,
  crearCuenta,
  cuentaDesdeApi,
  crearEstablecimiento,
  eliminarCuenta,
  eliminarEstablecimiento as eliminarEstablecimientoApi,
  empresaDesdeApi,
  establecimientoDesdeApi,
  firmaDesdeApi,
  guardarEmpresa,
  quitarFirma,
  subirFirma,
} from '../../api/configuracion';
import { AvisoDemo } from '../../components/ui/EstadoCarga';
import ListaConfiguracion from './ListaConfiguracion';
import { LISTAS } from './listas';
import styles from './Configuraciones.module.css';

const DIAS_AVISO_EXPIRACION = 60;

/**
 * Colores del PDF del comprobante.
 *
 * No son colores de la interfaz sino un valor de configuración del documento
 * que se imprime: el PDF sale igual en papel tenga el usuario el tema claro o
 * el oscuro, así que no pueden pasar por los tokens. La muestra de color y su
 * etiqueta leen de aquí para que nunca se contradigan.
 */
const COLOR_PDF_FONDO = '#000000';
const COLOR_PDF_TEXTO = '#FFFFFF';

let contadorId = 1000;
const nuevoId = () => ++contadorId;

const SECS = [
  { id: 'perfil', label: 'Perfil', Icon: User },
  { id: 'empresa', label: 'Empresa', Icon: Building2 },
  { id: 'bancos', label: 'Cuentas Bancarias', Icon: Landmark },
  { id: 'impuestos', label: 'Impuestos', Icon: Percent },
  { id: 'pdf', label: 'PDF/Impresiones', Icon: FileText },
  { id: 'impresoras', label: 'Impresoras', Icon: Printer },
  { id: 'permisos', label: 'Permisos', Icon: ShieldCheck },
  { id: 'usuarios', label: 'Usuarios', Icon: Users },
  { id: 'zonas', label: 'Zonas', Icon: MapPin },
  { id: 'vendedores', label: 'Vendedores/Administradores', Icon: UserCog },
  { id: 'banner', label: 'Banner Publicitario', Icon: ImageIcon },
  { id: 'leyendas', label: 'Leyendas Factura', Icon: ScrollText },
  { id: 'conexiones', label: 'Conexiones Tributarias', Icon: Plug2 },
];

const PLACEHOLDER_LISTS = {
  impuestos: {
    title: 'Impuestos',
    subtitle: 'Filtra y administra los impuestos disponibles.',
    cols: ['NOMBRE', 'CÓDIGO', 'PORCENTAJE', 'ESTADO', 'ACCIONES'],
    empty: 'No encontramos impuestos con los filtros actuales.',
    addLabel: 'Agregar',
  },
  permisos: {
    title: 'Permisos',
    subtitle: 'Busca, revisa y gestiona perfiles de acceso.',
    cols: ['NOMBRE PERMISO', 'ACCIONES'],
    empty: 'No encontramos perfiles de permisos con los filtros actuales.',
    addLabel: 'Permiso',
  },
  usuarios: {
    title: 'Usuarios',
    subtitle: 'Administra accesos y cuentas del equipo.',
    cols: ['USUARIO', 'CORREO', 'PERMISO', 'ACCIONES'],
    empty: 'No encontramos usuarios con los filtros actuales.',
    addLabel: 'Usuario',
  },
  zonas: {
    title: 'Filtros de búsqueda',
    subtitle: 'Ajusta los criterios para refinar el listado.',
    cols: ['NOMBRE', 'ACCIONES'],
    empty: 'No hay zonas configuradas. Crea la primera cuando necesites agrupar tus operaciones.',
    addLabel: 'Zona',
  },
  vendedores: {
    title: 'Filtros de búsqueda',
    subtitle: 'Ajusta los criterios para refinar el listado.',
    cols: ['NOMBRE', 'ESTADO', 'PUESTO', 'ACCIONES'],
    empty: 'No encontramos vendedores con los filtros actuales.',
    addLabel: 'Vendedor/Administrador',
  },
  leyendas: {
    title: 'Filtros de búsqueda',
    subtitle: 'Ajusta los criterios para refinar el listado.',
    cols: ['DESCRIPCIÓN', 'CLIENTE', 'ESTADO', 'ACCIONES'],
    empty: 'No hay leyendas configuradas para este filtro.',
    addLabel: 'Leyenda',
  },
};

export default function Configuraciones() {
  const { usuario, actualizarUsuario } = useSesion();
  const [sec, setSec] = useState('perfil');
  const [pdfTab, setPdfTab] = useState('pdf');
  const [query, setQuery] = useState('');
  const [facMail, setFacMail] = useState(false);
  const [modalBanco, setModalBanco] = useState(false);
  const [nuevaCuenta, setNuevaCuenta] = useState({ banco: '', numero: '', tipo: 'Corriente', titular: '' });
  const [bannerNombre, setBannerNombre] = useState('');
  const [bannerPreview, setBannerPreview] = useState(null);

  const [perfil, setPerfil] = useState({
    nombre: '',
    correo: '',
    contrasenaActual: '',
    contrasenaNueva: '',
    confirmar: '',
  });
  const [guardandoPerfil, setGuardandoPerfil] = useState(false);

  const [empresa, setEmpresa] = useState(EMPRESA_INICIAL);
  const [establecimientos, setEstablecimientos] = useState(ESTABLECIMIENTOS_INICIALES);
  const [cuentas, setCuentas] = useState(CUENTAS_BANCARIAS_INICIALES);
  const [firma, setFirma] = useState(FIRMA_INICIAL);
  const [guardando, setGuardando] = useState(false);
  const [aviso, setAviso] = useState(null);

  const recursoEmpresa = useRecurso('/configuracion/empresa', { datosDemo: null });
  const recursoEstablecimientos = useRecurso('/configuracion/establecimientos', {
    datosDemo: ESTABLECIMIENTOS_INICIALES,
  });
  const recursoCuentas = useRecurso('/configuracion/cuentas', {
    datosDemo: CUENTAS_BANCARIAS_INICIALES,
  });
  const recursoFirma = useRecurso('/configuracion/firma', { datosDemo: FIRMA_INICIAL });

  useEffect(() => {
    if (!recursoEmpresa.usandoDemo && recursoEmpresa.datos && !Array.isArray(recursoEmpresa.datos)) {
      setEmpresa(empresaDesdeApi(recursoEmpresa.datos));
    }
  }, [recursoEmpresa.datos, recursoEmpresa.usandoDemo]);

  useEffect(() => {
    if (!recursoEstablecimientos.usandoDemo && Array.isArray(recursoEstablecimientos.datos)) {
      setEstablecimientos(recursoEstablecimientos.datos.map(establecimientoDesdeApi));
    }
  }, [recursoEstablecimientos.datos, recursoEstablecimientos.usandoDemo]);

  useEffect(() => {
    if (!recursoCuentas.usandoDemo && Array.isArray(recursoCuentas.datos)) {
      setCuentas(recursoCuentas.datos.map(cuentaDesdeApi));
    }
  }, [recursoCuentas.datos, recursoCuentas.usandoDemo]);

  useEffect(() => {
    if (!recursoFirma.usandoDemo) {
      setFirma(Array.isArray(recursoFirma.datos) ? null : firmaDesdeApi(recursoFirma.datos));
    }
  }, [recursoFirma.datos, recursoFirma.usandoDemo]);

  const sinConexion = recursoEmpresa.usandoDemo;

  // Precarga los datos editables del usuario en sesión. Solo el nombre y el
  // correo: las contraseñas nunca vienen del servidor, se escriben aquí.
  useEffect(() => {
    setPerfil((actual) => ({
      ...actual,
      nombre: usuario?.nombre ?? '',
      correo: usuario?.correo ?? '',
    }));
  }, [usuario?.nombre, usuario?.correo]);

  const guardarPerfil = async () => {
    setAviso(null);
    if (!perfil.nombre.trim() || !perfil.correo.trim()) {
      setAviso({ tono: 'error', texto: 'El nombre y el correo no pueden quedar vacíos.' });
      return;
    }
    if (!perfil.contrasenaActual) {
      setAviso({ tono: 'error', texto: 'Escribe tu contraseña actual para confirmar los cambios.' });
      return;
    }
    if (perfil.contrasenaNueva) {
      if (perfil.contrasenaNueva.length < 8) {
        setAviso({ tono: 'error', texto: 'La nueva contraseña debe tener al menos 8 caracteres.' });
        return;
      }
      if (perfil.contrasenaNueva !== perfil.confirmar) {
        setAviso({ tono: 'error', texto: 'La nueva contraseña y su confirmación no coinciden.' });
        return;
      }
    }

    setGuardandoPerfil(true);
    try {
      const { datos } = await actualizarPerfil({
        nombre: perfil.nombre.trim(),
        correo: perfil.correo.trim(),
        contrasenaActual: perfil.contrasenaActual,
        contrasenaNueva: perfil.contrasenaNueva || null,
      });
      // Refresca la cabecera (nombre/correo) sin re-consultar al servidor.
      actualizarUsuario({ nombre: datos.nombre, correo: datos.correo });
      setPerfil((actual) => ({
        ...actual,
        nombre: datos.nombre,
        correo: datos.correo,
        contrasenaActual: '',
        contrasenaNueva: '',
        confirmar: '',
      }));
      setAviso({ tono: 'ok', texto: 'Perfil actualizado.' });
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    } finally {
      setGuardandoPerfil(false);
    }
  };

  const agregarCuenta = async () => {
    if (!nuevaCuenta.banco || !nuevaCuenta.numero) {
      setAviso({ tono: 'error', texto: 'Completa banco y número de cuenta.' });
      return;
    }
    try {
      const { datos } = await crearCuenta({
        banco: nuevaCuenta.banco,
        tipo: nuevaCuenta.tipo,
        numero: nuevaCuenta.numero,
        titular: nuevaCuenta.titular || empresa.razonSocial,
      });
      setCuentas((actuales) => [...actuales, cuentaDesdeApi(datos)]);
      setModalBanco(false);
      setNuevaCuenta({ banco: '', numero: '', tipo: 'Corriente', titular: '' });
      setAviso({ tono: 'ok', texto: 'Cuenta registrada.' });
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    }
  };

  const borrarCuenta = async (id) => {
    try {
      await eliminarCuenta(id);
      setCuentas((actuales) => actuales.filter((cuenta) => cuenta.id !== id));
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    }
  };

  const cargarCertificado = async (archivo, contrasenaCertificado) => {
    setAviso(null);
    try {
      setFirma(await subirFirma(archivo, contrasenaCertificado));
      setAviso({ tono: 'ok', texto: 'Certificado cargado y verificado.' });
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    }
  };

  const borrarCertificado = async () => {
    try {
      await quitarFirma();
      setFirma(null);
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    }
  };

  const enviarEmpresa = async () => {
    setGuardando(true);
    setAviso(null);
    try {
      await guardarEmpresa(empresa);
      for (const establecimiento of establecimientos) {
        if (establecimiento.id > 0 && establecimiento.id < 1000) {
          await actualizarEstablecimientoApi(establecimiento.id, establecimiento);
        } else {
          await crearEstablecimiento(establecimiento);
        }
      }
      recursoEstablecimientos.recargar();
      setAviso({ tono: 'ok', texto: 'Configuración guardada.' });
    } catch (error) {
      setAviso({ tono: 'error', texto: error.message });
    } finally {
      setGuardando(false);
    }
  };

  const validacionRuc = useMemo(() => validarRuc(empresa.ruc), [empresa.ruc]);
  const cantones = useMemo(() => cantonesDe(empresa.provincia), [empresa.provincia]);

  const actualizarEmpresa = (campo, valor) =>
    setEmpresa((actual) => {
      if (campo === 'provincia') return { ...actual, provincia: valor, canton: '' };
      return { ...actual, [campo]: valor };
    });

  const agregarEstablecimiento = () =>
    setEstablecimientos((actuales) => [
      ...actuales,
      {
        id: nuevoId(),
        codigo: String(actuales.length + 1).padStart(3, '0'),
        nombre: '',
        direccion: '',
        puntosEmision: [],
      },
    ]);

  const actualizarEstablecimiento = (id, campo, valor) =>
    setEstablecimientos((actuales) =>
      actuales.map((est) => (est.id === id ? { ...est, [campo]: valor } : est)),
    );

  const eliminarEstablecimiento = async (id) => {
    if (id < 1000) {
      try {
        await eliminarEstablecimientoApi(id);
      } catch (error) {
        setAviso({ tono: 'error', texto: error.message });
        return;
      }
    }
    setEstablecimientos((actuales) => actuales.filter((est) => est.id !== id));
  };

  const agregarPuntoEmision = (idEstablecimiento) =>
    setEstablecimientos((actuales) =>
      actuales.map((est) =>
        est.id === idEstablecimiento
          ? {
              ...est,
              puntosEmision: [
                ...est.puntosEmision,
                {
                  id: nuevoId(),
                  codigo: String(est.puntosEmision.length + 1).padStart(3, '0'),
                  nombre: '',
                  secuencialFactura: 1,
                },
              ],
            }
          : est,
      ),
    );

  const actualizarPuntoEmision = (idEstablecimiento, idPunto, campo, valor) =>
    setEstablecimientos((actuales) =>
      actuales.map((est) =>
        est.id === idEstablecimiento
          ? {
              ...est,
              puntosEmision: est.puntosEmision.map((punto) =>
                punto.id === idPunto ? { ...punto, [campo]: valor } : punto,
              ),
            }
          : est,
      ),
    );

  const eliminarPuntoEmision = (idEstablecimiento, idPunto) =>
    setEstablecimientos((actuales) =>
      actuales.map((est) =>
        est.id === idEstablecimiento
          ? { ...est, puntosEmision: est.puntosEmision.filter((p) => p.id !== idPunto) }
          : est,
      ),
    );

  const cuentasFiltradas = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return cuentas;
    return cuentas.filter((c) => `${c.banco} ${c.numero} ${c.titular}`.toLowerCase().includes(q));
  }, [cuentas, query]);

  // Cinco de las seis listas del prototipo ya tienen datos; `permisos`
  // sigue sin modelo porque el sistema aún no tiene roles granulares.
  const listaReal = LISTAS[sec];
  const esPlaceholder = Boolean(PLACEHOLDER_LISTS[sec]) && !listaReal;
  const isPerfil = sec === 'perfil';
  const isEmpresa = sec === 'empresa';
  const isBancos = sec === 'bancos';
  const isPdf = sec === 'pdf';
  const isImpresoras = sec === 'impresoras';
  const isBanner = sec === 'banner';
  const isConex = sec === 'conexiones';

  return (
    <div className={styles.container}>
      {recursoEmpresa.usandoDemo && <AvisoDemo />}

      {aviso && (
        <div className={aviso.tono === 'ok' ? styles.avisoOk : styles.avisoError}>{aviso.texto}</div>
      )}

      {empresa.ambiente === '1' && (
        <div className={styles.bannerPruebas}>
          <AlertTriangle size={18} />
          <span>
            Estás en <strong>ambiente de PRUEBAS</strong>. Los comprobantes emitidos no tienen validez tributaria.
          </span>
        </div>
      )}

      <div className={styles.cwoLayout}>
        <aside className={styles.cwoSidebar}>
          <div className={styles.cwoSidebarTitle}>CONFIGURACIÓN</div>
          <nav className={styles.cwoSidebarNav}>
            {SECS.map(({ id, label, Icon }) => {
              const activo = sec === id;
              return (
                <button
                  key={id}
                  className={`${styles.cwoSideItem} ${activo ? styles.cwoSideItemActive : ''}`}
                  onClick={() => {
                    setSec(id);
                    setQuery('');
                    setAviso(null);
                  }}
                >
                  <Icon size={17} />
                  <span>{label}</span>
                </button>
              );
            })}
          </nav>
        </aside>

        <div className={styles.cwoMain}>
          {/* PERFIL */}
          {isPerfil && (
            <div className={styles.perfilWrap}>
              <div className={styles.cwoSectionHead}>
                <span className={styles.cwoSectionIcon} />
                <div>
                  <div className={styles.cwoSectionTitle}>Perfil y notificaciones</div>
                  <div className={styles.cwoSectionSub}>Actualiza tu acceso y decide qué documentos recibes por correo.</div>
                </div>
              </div>

              <div className={styles.perfilGrid}>
                <div className={`${styles.cwoCard} ${styles.perfilCard}`}>
                  <div className={styles.cwoCardHead}>
                    <span className={styles.cwoCardIcon}>
                      <FileText size={17} />
                    </span>
                    <div>
                      <div className={styles.cwoCardTitle}>Datos de usuario</div>
                      <div className={styles.cwoCardSub}>Información de acceso a Factoa.</div>
                    </div>
                  </div>
                  <div className={styles.perfilFields}>
                    <div className={styles.fieldFloatWrap}>
                      <span className={styles.floatLabel}>Nombre</span>
                      <input
                        className={styles.input}
                        autoComplete="name"
                        value={perfil.nombre}
                        onChange={(e) => setPerfil((p) => ({ ...p, nombre: e.target.value }))}
                      />
                    </div>
                    <div className={styles.fieldFloatWrap}>
                      <span className={styles.floatLabel}>Contraseña actual</span>
                      <input
                        type="password"
                        className={styles.input}
                        autoComplete="current-password"
                        placeholder="Requerida para guardar"
                        value={perfil.contrasenaActual}
                        onChange={(e) => setPerfil((p) => ({ ...p, contrasenaActual: e.target.value }))}
                      />
                    </div>
                    <div className={styles.fieldFloatWrap}>
                      <span className={styles.floatLabel}>Correo electrónico</span>
                      <input
                        type="email"
                        className={styles.input}
                        autoComplete="email"
                        value={perfil.correo}
                        onChange={(e) => setPerfil((p) => ({ ...p, correo: e.target.value }))}
                      />
                    </div>
                    <div className={styles.fieldFloatWrap}>
                      <span className={styles.floatLabel}>Nueva contraseña (opcional)</span>
                      <input
                        type="password"
                        className={styles.input}
                        autoComplete="new-password"
                        placeholder="Mínimo 8 caracteres"
                        value={perfil.contrasenaNueva}
                        onChange={(e) => setPerfil((p) => ({ ...p, contrasenaNueva: e.target.value }))}
                      />
                    </div>
                    <PerfilField label="Miembro desde" value="—" disabled />
                    <div className={styles.fieldFloatWrap}>
                      <span className={styles.floatLabel}>Confirmar contraseña (opcional)</span>
                      <input
                        type="password"
                        className={styles.input}
                        autoComplete="new-password"
                        placeholder="Repite la nueva contraseña"
                        value={perfil.confirmar}
                        onChange={(e) => setPerfil((p) => ({ ...p, confirmar: e.target.value }))}
                      />
                    </div>
                  </div>
                  <div className={styles.cwoCardFoot}>
                    <button
                      className={styles.btnPrimary}
                      onClick={guardarPerfil}
                      disabled={guardandoPerfil}
                    >
                      {guardandoPerfil ? <Loader2 size={15} className={styles.girando} /> : <Save size={15} />}
                      {guardandoPerfil ? 'Guardando…' : 'Guardar Cambios'}
                    </button>
                  </div>
                </div>

                <div className={`${styles.cwoCard} ${styles.perfilCard}`}>
                  <div className={styles.cwoCardHeadSimple}>
                    <div className={styles.cwoCardTitle}>Copias automáticas</div>
                    <div className={styles.cwoCardSub}>Elige cuáles documentos llegan a tu correo.</div>
                  </div>
                  <div className={styles.copiasBody}>
                    <div className={styles.fieldFloat}>
                      <span className={styles.floatLabel}>Correo para recibir copias</span>
                      <div className={styles.inputConIcono}>
                        <Search size={15} style={{ color: 'var(--text-muted)', flex: '0 0 auto' }} />
                        <span className={styles.inputTexto}>{usuario?.correo ?? 'correo@empresademo.ec'}</span>
                      </div>
                    </div>
                    <label className={styles.toggleRow} onClick={() => setFacMail((v) => !v)}>
                      <span className={`${styles.toggleTrack} ${facMail ? styles.toggleOn : ''}`}>
                        <span className={styles.toggleKnob} />
                      </span>
                      <span className={styles.toggleLabel}>Facturas electrónicas</span>
                    </label>
                  </div>
                  <div className={styles.cwoCardFoot}>
                    <button
                      className={styles.btnPrimary}
                      disabled
                      title="Preferencias de correo — próximamente. Aún no se guardan en el servidor."
                    >
                      <Save size={15} /> Guardar Preferencias
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* EMPRESA (real) */}
          {isEmpresa && (
            <div className={styles.empresaWrap}>
              <div className={styles.cwoCard}>
                <div className={styles.cwoCardHeadRow}>
                  <span className={styles.cwoCardIconSm}>
                    <Building2 size={17} />
                  </span>
                  <div style={{ flex: 1 }}>
                    <div className={styles.cwoCardTitle}>Datos del emisor</div>
                    <div className={styles.cwoCardSub}>RUC, razón social y dirección matriz que viajan en el XML.</div>
                  </div>
                  <button
                    className={styles.btnPrimary}
                    onClick={enviarEmpresa}
                    disabled={guardando || !validacionRuc.esValida}
                    title={validacionRuc.esValida ? undefined : validacionRuc.error}
                  >
                    {guardando ? <Loader2 size={18} className={styles.girando} /> : <Save size={18} />}
                    {guardando ? 'Guardando…' : 'Guardar cambios'}
                  </button>
                </div>

                <div className={styles.formGrid}>
                  <div className={styles.grupo}>
                    <label htmlFor="ruc">RUC del emisor *</label>
                    <div className={styles.campoConAccion}>
                      <input
                        id="ruc"
                        className={`${styles.input} ${empresa.ruc && !validacionRuc.esValida ? styles.inputError : ''}`}
                        value={empresa.ruc}
                        maxLength={13}
                        inputMode="numeric"
                        onChange={(e) => actualizarEmpresa('ruc', e.target.value)}
                      />
                      <button className={styles.btnAccion} title="Consultar en el SRI">
                        <Search size={18} />
                      </button>
                    </div>
                    {empresa.ruc && (
                      <span className={validacionRuc.esValida ? styles.ayudaOk : styles.ayudaError}>
                        {validacionRuc.esValida ? `RUC válido · ${validacionRuc.tipo}` : validacionRuc.error}
                      </span>
                    )}
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="regimen">Régimen tributario *</label>
                    <select
                      id="regimen"
                      className={styles.input}
                      value={empresa.regimen}
                      onChange={(e) => actualizarEmpresa('regimen', e.target.value)}
                    >
                      {REGIMENES.map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.grupoAncho}>
                    <label htmlFor="razonSocial">Razón social *</label>
                    <input
                      id="razonSocial"
                      className={styles.input}
                      value={empresa.razonSocial}
                      onChange={(e) => actualizarEmpresa('razonSocial', e.target.value)}
                    />
                  </div>

                  <div className={styles.grupoAncho}>
                    <label htmlFor="nombreComercial">Nombre comercial</label>
                    <input
                      id="nombreComercial"
                      className={styles.input}
                      value={empresa.nombreComercial}
                      onChange={(e) => actualizarEmpresa('nombreComercial', e.target.value)}
                    />
                  </div>

                  <div className={styles.grupoAncho}>
                    <label htmlFor="direccionMatriz">Dirección matriz *</label>
                    <input
                      id="direccionMatriz"
                      className={styles.input}
                      value={empresa.direccionMatriz}
                      onChange={(e) => actualizarEmpresa('direccionMatriz', e.target.value)}
                    />
                    <span className={styles.ayuda}>Viaja en el XML como dirección del emisor.</span>
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="provincia">Provincia</label>
                    <select
                      id="provincia"
                      className={styles.input}
                      value={empresa.provincia}
                      onChange={(e) => actualizarEmpresa('provincia', e.target.value)}
                    >
                      <option value="">Seleccionar…</option>
                      {NOMBRES_PROVINCIAS.map((p) => (
                        <option key={p}>{p}</option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="canton">Cantón</label>
                    <select
                      id="canton"
                      className={styles.input}
                      value={empresa.canton}
                      disabled={cantones.length === 0}
                      onChange={(e) => actualizarEmpresa('canton', e.target.value)}
                    >
                      <option value="">{cantones.length === 0 ? 'Elige una provincia primero' : 'Seleccionar…'}</option>
                      {cantones.map((c) => (
                        <option key={c}>{c}</option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="telefono">Teléfono</label>
                    <input
                      id="telefono"
                      className={styles.input}
                      value={empresa.telefono}
                      onChange={(e) => actualizarEmpresa('telefono', e.target.value)}
                    />
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="correo">Correo de facturación</label>
                    <input
                      id="correo"
                      type="email"
                      className={styles.input}
                      value={empresa.correo}
                      onChange={(e) => actualizarEmpresa('correo', e.target.value)}
                    />
                  </div>

                  <div className={styles.grupo}>
                    <label htmlFor="ambiente">Ambiente SRI *</label>
                    <select
                      id="ambiente"
                      className={styles.input}
                      value={empresa.ambiente}
                      onChange={(e) => actualizarEmpresa('ambiente', e.target.value)}
                    >
                      {AMBIENTES_SRI.map((a) => (
                        <option key={a.codigo} value={a.codigo}>
                          {a.nombre}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className={styles.grupoAncho}>
                    <div className={styles.interruptores}>
                      <label className={styles.interruptor}>
                        <input
                          type="checkbox"
                          checked={empresa.obligadoContabilidad}
                          onChange={(e) => actualizarEmpresa('obligadoContabilidad', e.target.checked)}
                        />
                        <span className={styles.palanca}></span>
                        <span>Obligado a llevar contabilidad</span>
                      </label>
                      <label className={styles.interruptor}>
                        <input
                          type="checkbox"
                          checked={empresa.contribuyenteRimpe}
                          onChange={(e) => actualizarEmpresa('contribuyenteRimpe', e.target.checked)}
                        />
                        <span className={styles.palanca}></span>
                        <span>Mostrar leyenda RIMPE en el comprobante</span>
                      </label>
                    </div>
                  </div>
                </div>

                <div className={styles.establecimientosBloque}>
                  <div className={styles.puntosCabecera}>
                    <h4>Establecimientos y puntos de emisión</h4>
                    <button className={styles.btnMini} onClick={agregarEstablecimiento}>
                      <Plus size={14} /> Añadir establecimiento
                    </button>
                  </div>
                  <div className={styles.listaEstablecimientos}>
                    {establecimientos.map((est) => (
                      <div key={est.id} className={styles.tarjetaEstablecimiento}>
                        <div className={styles.filaEstablecimiento}>
                          <div className={styles.grupoCorto}>
                            <label>Código</label>
                            <input
                              className={styles.input}
                              value={est.codigo}
                              maxLength={3}
                              onChange={(e) => actualizarEstablecimiento(est.id, 'codigo', e.target.value)}
                            />
                          </div>
                          <div className={styles.grupo}>
                            <label>Nombre</label>
                            <input
                              className={styles.input}
                              value={est.nombre}
                              placeholder="Matriz, Sucursal Norte…"
                              onChange={(e) => actualizarEstablecimiento(est.id, 'nombre', e.target.value)}
                            />
                          </div>
                          <div className={styles.grupo}>
                            <label>Dirección</label>
                            <input
                              className={styles.input}
                              value={est.direccion}
                              onChange={(e) => actualizarEstablecimiento(est.id, 'direccion', e.target.value)}
                            />
                          </div>
                          <button className={styles.btnEliminar} onClick={() => eliminarEstablecimiento(est.id)}>
                            <Trash2 size={16} />
                          </button>
                        </div>
                        <div className={styles.puntos}>
                          <div className={styles.puntosCabecera}>
                            <h4>Puntos de emisión</h4>
                            <button className={styles.btnMini} onClick={() => agregarPuntoEmision(est.id)}>
                              <Plus size={14} /> Añadir punto
                            </button>
                          </div>
                          {est.puntosEmision.length === 0 ? (
                            <p className={styles.puntosVacio}>Sin puntos de emisión. Este establecimiento aún no puede facturar.</p>
                          ) : (
                            <table className={styles.tablaPuntos}>
                              <thead>
                                <tr>
                                  <th width="90">Código</th>
                                  <th>Nombre</th>
                                  <th width="140">Siguiente secuencial</th>
                                  <th width="180">Próximo número</th>
                                  <th width="48"></th>
                                </tr>
                              </thead>
                              <tbody>
                                {est.puntosEmision.map((p) => (
                                  <tr key={p.id}>
                                    <td>
                                      <input
                                        className={styles.inputMini}
                                        value={p.codigo}
                                        maxLength={3}
                                        onChange={(e) => actualizarPuntoEmision(est.id, p.id, 'codigo', e.target.value)}
                                      />
                                    </td>
                                    <td>
                                      <input
                                        className={styles.inputMini}
                                        value={p.nombre}
                                        placeholder="Caja principal…"
                                        onChange={(e) => actualizarPuntoEmision(est.id, p.id, 'nombre', e.target.value)}
                                      />
                                    </td>
                                    <td>
                                      <input
                                        type="number"
                                        min="1"
                                        className={styles.inputMini}
                                        value={p.secuencialFactura}
                                        onChange={(e) => actualizarPuntoEmision(est.id, p.id, 'secuencialFactura', e.target.value)}
                                      />
                                    </td>
                                    <td>
                                      <code className={styles.numeroPrevio}>
                                        {est.codigo}-{p.codigo}-{String(p.secuencialFactura || 0).padStart(9, '0')}
                                      </code>
                                    </td>
                                    <td>
                                      <button className={styles.btnEliminar} onClick={() => eliminarPuntoEmision(est.id, p.id)}>
                                        <Trash2 size={14} />
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* BANCOS (real) */}
          {isBancos && (
            <div className={styles.cwoCard}>
              <div className={styles.cwoListHead}>
                <span className={styles.cwoListIcon}>
                  <Landmark size={17} />
                </span>
                <div style={{ flex: 1 }}>
                  <div className={styles.cwoListTitle}>Filtros de búsqueda</div>
                  <div className={styles.cwoListSub}>Ajusta los criterios para refinar el listado.</div>
                </div>
                <button className={styles.btnPrimary} onClick={() => setModalBanco(true)}>
                  <Plus size={15} /> Cuenta
                </button>
              </div>

              <div className={styles.cwoToolbar}>
                <span className={styles.cwoSearch}>
                  <Search size={15} />
                  <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar por nombre" />
                </span>
                <button className={styles.cwoIconBtn} onClick={() => setQuery('')} title="Refrescar">
                  <RefreshCw size={16} />
                </button>
                <span className={styles.cwoCount}>10</span>
              </div>

              <div className={styles.cwoTableWrap}>
                <table className={styles.cwoTable}>
                  <thead>
                    <tr>
                      <th>BANCO</th>
                      <th># CUENTA</th>
                      <th># CUENTA IBAN</th>
                      <th>TIPO CUENTA</th>
                      <th>ACCIONES</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cuentasFiltradas.length === 0 ? (
                      <tr>
                        <td colSpan={5} className={styles.cwoEmpty}>
                          No hay cuentas bancarias configuradas. Crea la primera para registrar cobros y pagos.
                        </td>
                      </tr>
                    ) : (
                      cuentasFiltradas.map((c) => (
                        <tr key={c.id}>
                          <td>{c.banco}</td>
                          <td>
                            <code>{c.numero}</code>
                          </td>
                          <td>—</td>
                          <td>
                            <span className={styles.chip}>{c.tipo}</span>
                          </td>
                          <td>
                            <button className={styles.btnEliminar} onClick={() => borrarCuenta(c.id)} aria-label="Eliminar">
                              <Trash2 size={14} />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className={styles.cwoFoot}>
                <span>
                  Viendo {cuentasFiltradas.length ? 1 : 0} a {cuentasFiltradas.length} de {cuentasFiltradas.length} entradas
                </span>
              </div>
            </div>
          )}

          {/* PDF / IMPRESIONES */}
          {isPdf && (
            <div className={styles.pdfWrap}>
              <div className={styles.cwoTabs}>
                {[
                  ['pdf', 'Documento PDF'],
                  ['pos', 'Impresión POS'],
                ].map(([k, label]) => (
                  <button
                    key={k}
                    className={`${styles.cwoTab} ${pdfTab === k ? styles.cwoTabActive : ''}`}
                    onClick={() => setPdfTab(k)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {pdfTab === 'pdf' ? (
                <>
                  <div className={styles.cwoInfo}>
                    <span className={styles.cwoInfoIcon}>i</span>
                    <span>Los cambios se aplicarán a los próximos PDF que generes. Los documentos ya emitidos no cambian.</span>
                  </div>
                  <div className={styles.cwoCard} style={{ padding: 20 }}>
                    <div className={styles.cwoSectionHead} style={{ marginBottom: 22 }}>
                      <span className={styles.cwoSectionIconSm}>
                        <FileText size={18} />
                      </span>
                      <div>
                        <div className={styles.cwoSectionTitle}>Documento PDF</div>
                        <div className={styles.cwoSectionSub}>Personaliza el contenido y la apariencia de tus comprobantes impresos.</div>
                      </div>
                    </div>
                    <div className={styles.cwoFormTitle}>Contenido del documento</div>
                    <div className={styles.cwoFormSub}>Define los textos adicionales, los campos visibles y el orden de las líneas.</div>
                    <div className={styles.pdfGrid}>
                      <FieldFloat label="Leyenda del encabezado" value="Ej.: Gracias por tu compra" muted />
                      <FieldFloat label="Leyenda del pie" value="Ej.: Conserva este comprobante" muted />
                      <FieldFloat label="Campos opcionales" value="Nombre de la línea" chev />
                      <FieldFloat label="Decimales en los importes" value="2" chev />
                      <FieldFloat label="Orden de las líneas" value="Normal" chev />
                    </div>
                    <div className={styles.divider} />
                    <div className={styles.cwoFormTitle}>Colores del PDF</div>
                    <div className={styles.cwoFormSub}>Usa colores con buen contraste para que el documento sea fácil de leer.</div>
                    <div className={styles.pdfColors}>
                      <div className={styles.colorField}>
                        <span className={styles.floatLabelAccent}>Color de fondo</span>
                        <div className={styles.swatch} style={{ background: COLOR_PDF_FONDO }} />
                        <span className={styles.hex}>{COLOR_PDF_FONDO}</span>
                      </div>
                      <div className={styles.colorField}>
                        <span className={styles.floatLabelAccent}>Color del texto</span>
                        <div className={styles.swatch} style={{ background: COLOR_PDF_TEXTO, border: '1px solid var(--field-borde)' }} />
                        <span className={styles.hex}>{COLOR_PDF_TEXTO}</span>
                      </div>
                    </div>
                    <div className={styles.cwoCardFootRight}>
                      <button className={styles.btnPrimary} disabled title="Diseño del PDF — próximamente. Aún no se guarda en el servidor.">
                        <Save size={15} /> Guardar Configuración
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div className={styles.cwoCard} style={{ padding: 22 }}>
                  <div className={styles.cwoFormTitleSm}>Esta configuración se mostrara en todas las impresiones de tirilla POS.</div>
                  <div className={styles.pdfGrid} style={{ marginTop: 22 }}>
                    <FieldFloat label="Leyenda de Encabezado" value="Leyenda de Encabezado" muted />
                    <FieldFloat label="Leyenda de Pie" value="Leyenda de Pie" muted />
                    <FieldFloat label="Cantidad de Decimales" value="2" chev float />
                    <FieldFloat label="Mostrar Logo" value="No Mostrar" chev float />
                  </div>
                  <div className={styles.cwoCardFootRight}>
                    <button className={styles.btnPrimary} disabled title="Configuración POS — próximamente. Aún no se guarda en el servidor.">
                      Guardar
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* IMPRESORAS */}
          {isImpresoras && (
            <div className={styles.stackGap}>
              <div className={styles.cwoInfoGray}>
                <div className={styles.cwoInfoGrayHead}>
                  <span className={styles.cwoInfoGrayIcon}>
                    <Printer size={19} />
                  </span>
                  <div>
                    <div className={styles.cwoInfoGrayTitle}>Impresión directa con Factoa Print</div>
                    <div className={styles.cwoInfoGraySub}>Companion gratuito para imprimir sin diálogos del navegador</div>
                  </div>
                </div>
                <div className={styles.cwoInfoGrayBody}>
                  <p>
                    <strong>Factoa Print</strong> es un mini-programa (~3 MB) que se instala una vez en tu computadora y permite imprimir
                    tickets, facturas y comandas directo a la impresora térmica desde la web de Factoa.
                  </p>
                  <p>
                    <strong>Funciona en:</strong> macOS (Intel + Apple Silicon), Windows, Linux. Soporta impresoras USB, red local
                    (LAN/WiFi) y Bluetooth.
                  </p>
                  <p>
                    <strong>Después de instalar</strong> arranca automáticamente con tu equipo. Solo lo configuras una vez.
                  </p>
                </div>
                <div className={styles.cwoInfoGrayActions}>
                  <button className={styles.btnSuccess} disabled title="Factoa Print — próximamente.">
                    <Upload size={15} /> Descargar Factoa Print Para Windows
                  </button>
                  <button className={styles.linkMuted} disabled title="Asistente de instalación — próximamente.">
                    Abrir Asistente De Instalación
                  </button>
                </div>
              </div>

              <div className={styles.cwoCard} style={{ overflow: 'hidden', padding: 0 }}>
                <div className={styles.cwoCardHeadRow} style={{ background: 'var(--accent-light)', borderBottom: '1px solid var(--field-borde)', padding: '16px 20px' }}>
                  <span className={styles.cwoCardIconSm}>
                    <Printer size={18} />
                  </span>
                  <div style={{ flex: 1 }}>
                    <div className={styles.cwoEyebrow}>CONFIGURACIÓN · RESTAURANTE</div>
                    <div className={styles.cwoCardTitle}>Impresoras por terminal</div>
                  </div>
                  <div style={{ display: 'flex', gap: 9, flexWrap: 'wrap' }}>
                    <button className={styles.btnGhost} disabled title="Impresoras por terminal — próximamente.">
                      <RefreshCw size={14} /> Refrescar
                    </button>
                    <button className={styles.btnPrimary} disabled title="Impresoras por terminal — próximamente.">
                      <Plus size={14} /> Terminal
                    </button>
                    <button className={styles.btnSuccess} disabled title="Impresoras por terminal — próximamente.">
                      <RefreshCw size={14} /> Instalar Factoa Print
                    </button>
                  </div>
                </div>
                <div className={styles.emptyCenter}>
                  <Printer size={42} style={{ color: 'var(--text-muted)', marginBottom: 14, opacity: 0.5 }} />
                  <div className={styles.emptyTitle}>No hay terminales activas</div>
                  <div className={styles.emptySub}>Crea Cocina, Bar, Postres o cualquier estación desde el botón Terminal.</div>
                </div>
                <div className={styles.cwoFootMuted}>
                  <AlertTriangle size={14} style={{ flex: '0 0 auto', marginTop: 2 }} />
                  <span>
                    <strong>Sincronizada:</strong> la selección se comparte entre todos los equipos de la empresa. Si eliges &quot;Solo este
                    equipo&quot;, la preferencia se conserva únicamente en esta computadora.
                  </span>
                </div>
              </div>
              <ProximamenteBanner titulo="Impresoras — Próximamente" texto="La gestión de terminales y Factoa Print está en desarrollo." />
            </div>
          )}

          {/* BANNER */}
          {isBanner && (
            <div className={styles.cwoCard} style={{ padding: 20 }}>
              <div className={styles.cwoSectionHead}>
                <span className={styles.cwoSectionIconSm}>
                  <ImageIcon size={18} />
                </span>
                <div>
                  <div className={styles.cwoSectionTitle}>Banner publicitario</div>
                  <div className={styles.cwoSectionSub}>Se muestra en cada factura PDF que emitas</div>
                </div>
              </div>
              <div className={styles.cwoInfoGray} style={{ marginBottom: 20 }}>
                <span className={styles.cwoInfoIcon}>i</span>
                <div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    Promociona tus productos y servicios en cada factura emitida. Aplica solo a las facturas generadas después de
                    publicarlo — no a las anteriores.
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>
                    Tamaño máximo 800 × 100 px · la imagen se ajusta sin deformarse (opcional).
                  </div>
                </div>
              </div>
              <div className={styles.bannerGrid}>
                <div className={styles.bannerPreview}>
                  {bannerPreview ? (
                    <img src={bannerPreview} alt="Banner" style={{ maxWidth: '100%', maxHeight: 90, objectFit: 'contain' }} />
                  ) : (
                    <>
                      <ImageIcon size={34} style={{ color: 'var(--text-muted)', marginBottom: 12, opacity: 0.5 }} />
                      <div style={{ fontSize: 13.5, color: 'var(--text-muted)' }}>Vista previa del banner</div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-muted)', opacity: 0.7, marginTop: 4 }}>Sube una imagen para verla aquí</div>
                    </>
                  )}
                </div>
                <div className={styles.bannerForm}>
                  <input
                    className={styles.input}
                    placeholder="Nombre del banner"
                    value={bannerNombre}
                    onChange={(e) => setBannerNombre(e.target.value)}
                  />
                  <label className={styles.inputFile}>
                    <Upload size={15} />
                    <span>Imagen</span>
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (!f) return;
                        if (f.size > 2 * 1024 * 1024) {
                          setAviso({ tono: 'error', texto: 'La imagen no debe superar 2 MB.' });
                          return;
                        }
                        setBannerPreview(URL.createObjectURL(f));
                      }}
                    />
                  </label>
                  <span className={styles.ayuda}>800 × 100 px recomendado. Se guarda local hasta que exista endpoint.</span>
                </div>
              </div>
              <ProximamenteBanner titulo="Banner — sin endpoint aún" texto="La subida del banner se guarda solo en esta sesión. Se integrará con el backend cuando exista el endpoint." />
            </div>
          )}

          {/* CONEXIONES TRIBUTARIAS (firma real) */}
          {isConex && (
            <div className={styles.stackGap}>
              {/* Banner 3-B: aviso CLAVE_SECRETA → re-subir .p12 */}
              <div className={styles.bannerClaveSecreta}>
                <AlertTriangle size={18} style={{ flex: '0 0 auto' }} />
                <span>
                  <strong>Si cambias CLAVE_SECRETA, vuelve a subir el .p12.</strong> La contraseña del certificado se cifra con esa clave
                  (cifrado.py §11 — Fernet/PBKDF2 con sal fija). Al rotarla, el descifrado falla y hay que re-subir el certificado.
                </span>
              </div>

              {/* Banner crítico si valida_hasta <30 días */}
              {firma && firma.validaHasta && diasParaExpirar(firma.validaHasta) < 30 && (
                <div className={diasParaExpirar(firma.validaHasta) < 0 ? styles.bannerExpirado : styles.bannerPorExpirar}>
                  <AlertTriangle size={18} style={{ flex: '0 0 auto' }} />
                  <span>
                    {diasParaExpirar(firma.validaHasta) < 0
                      ? `Certificado expirado hace ${Math.abs(diasParaExpirar(firma.validaHasta))} días — no se puede firmar ni emitir. Renuévalo con tu entidad certificadora.`
                      : `Certificado por expirar: caduca en ${diasParaExpirar(firma.validaHasta)} días (${firma.validaHasta}). Renuévalo antes de que venza.`}
                  </span>
                </div>
              )}

              <div className={styles.cwoCard} style={{ padding: '22px 24px' }}>
                <div style={{ textAlign: 'center', fontSize: 17, color: 'var(--text-secondary)', marginBottom: 22 }}>
                  Configuración de Conexión SRI — Ecuador
                </div>
                <div className={styles.cwoInfoBox}>
                  <div className={styles.cwoInfoRow}>
                    <FileText size={17} style={{ flex: '0 0 auto', marginTop: 2, color: 'var(--text-secondary)' }} />
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                      Ecuador utiliza Facturación Electrónica directa con el SRI (Servicio de Rentas Internas). Los comprobantes se firman
                      digitalmente con un certificado .p12 o .pfx emitido por una entidad certificadora autorizada (BCE, Security Data,
                      Anfac, etc.).
                    </span>
                  </div>
                  <div className={styles.cwoInfoRow}>
                    <Upload size={17} style={{ flex: '0 0 auto', marginTop: 2, color: 'var(--text-secondary)' }} />
                    <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                      Sube tu certificado digital y su contraseña. El sistema firmará los comprobantes automáticamente antes de enviarlos
                      al SRI.
                    </span>
                  </div>
                </div>
              </div>

              <div className={styles.cwoCard} style={{ padding: '20px 24px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 11, marginBottom: 18 }}>
                  <Landmark size={19} style={{ color: 'var(--text-secondary)' }} />
                  <span style={{ fontSize: 16, color: 'var(--text-secondary)' }}>Certificado Digital (.p12 / .pfx)</span>
                </div>
                {firma ? (
                  <div className={styles.firmaBox}>
                    <span className={styles.badgeOk}>Vigente</span>
                    <div className={styles.firmaGrid}>
                      <div className={styles.fieldFloatMuted}>
                        <span className={styles.floatLabel}>Titular</span>
                        <div className={styles.inputMuted}>{firma.propietario || '—'}</div>
                      </div>
                      <div className={styles.fieldFloatMuted}>
                        <span className={styles.floatLabel}>Válido hasta</span>
                        <div className={styles.inputMuted} style={diasParaExpirar(firma.validaHasta) < 30 ? { color: 'var(--error)', fontWeight: 700 } : undefined}>
                          {firma.validaHasta || '—'}
                          {firma.validaHasta && diasParaExpirar(firma.validaHasta) < 30
                            ? ` · ${diasParaExpirar(firma.validaHasta) < 0 ? 'Expirado' : `Caduca en ${diasParaExpirar(firma.validaHasta)} días`}`
                            : ''}
                        </div>
                      </div>
                      <button className={styles.btnDanger} onClick={borrarCertificado}>
                        Eliminar
                      </button>
                    </div>
                    <EstadoFirmaDetalle firma={firma} />
                  </div>
                ) : (
                  <CargaCertificado onCargar={cargarCertificado} deshabilitado={sinConexion} />
                )}
              </div>

              <div className={styles.cwoInfo}>
                <span className={styles.cwoInfoIcon}>i</span>
                <span>
                  <strong>Importante:</strong> El certificado digital debe estar vigente. Si expira, los comprobantes no podrán ser firmados
                  ni enviados al SRI. Renuévalo antes de la fecha de vencimiento con tu entidad certificadora.
                </span>
              </div>
            </div>
          )}

          {listaReal && <ListaConfiguracion seccion={sec} />}

          {/* `permisos` sigue sin backend: el sistema no tiene roles
              granulares todavía, solo el campo `rol` del usuario. */}
          {esPlaceholder && (
            <div className={styles.cwoCard}>
              <ProximamenteBanner
                titulo={`${PLACEHOLDER_LISTS[sec].title} — Próximamente`}
                texto="Los permisos granulares aún no existen en el sistema: hoy cada usuario tiene un único rol. Se muestra la estructura para no romper la vista."
              />
              <div className={styles.cwoListHead}>
                <span className={styles.cwoListIcon}>
                  {(() => {
                    const found = SECS.find((s) => s.id === sec);
                    const Icon = found?.Icon ?? FileText;
                    return <Icon size={17} />;
                  })()}
                </span>
                <div style={{ flex: 1 }}>
                  <div className={styles.cwoListTitle}>{PLACEHOLDER_LISTS[sec].title}</div>
                  <div className={styles.cwoListSub}>{PLACEHOLDER_LISTS[sec].subtitle}</div>
                </div>
                <button className={styles.btnPrimary} onClick={() => setAviso({ tono: 'error', texto: 'Próximamente: creación de ' + PLACEHOLDER_LISTS[sec].addLabel })}>
                  <Plus size={15} /> {PLACEHOLDER_LISTS[sec].addLabel}
                </button>
              </div>
              <div className={styles.cwoToolbar}>
                <span className={styles.cwoSearch}>
                  <Search size={15} />
                  <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Buscar" />
                </span>
                <button className={styles.cwoIconBtn} onClick={() => setQuery('')}>
                  <RefreshCw size={16} />
                </button>
                <span className={styles.cwoCount}>10</span>
              </div>
              <div className={styles.cwoTableWrap}>
                <table className={styles.cwoTable}>
                  <thead>
                    <tr>
                      {PLACEHOLDER_LISTS[sec].cols.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td colSpan={PLACEHOLDER_LISTS[sec].cols.length} className={styles.cwoEmpty}>
                        {PLACEHOLDER_LISTS[sec].empty}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className={styles.cwoFoot}>
                <span>Viendo 0 a 0 de 0 entradas</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal nueva cuenta */}
      <AnimatePresence>
        {modalBanco && (
          <motion.div
            className={styles.modalOverlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setModalBanco(false)}
          >
            <motion.div
              className={styles.modal}
              initial={{ scale: 0.96, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.96, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <button className={styles.modalClose} onClick={() => setModalBanco(false)}>
                <X size={16} />
              </button>
              <div className={styles.modalTitle}>Nueva Cuenta Bancaria</div>
              <div className={styles.modalGrid}>
                <div className={styles.grupo}>
                  <label>Banco</label>
                  <input
                    className={styles.input}
                    placeholder="Banco Pichincha"
                    value={nuevaCuenta.banco}
                    onChange={(e) => setNuevaCuenta((a) => ({ ...a, banco: e.target.value }))}
                  />
                </div>
                <div className={styles.grupo}>
                  <label># Cuenta</label>
                  <input
                    className={styles.input}
                    placeholder="2100123456"
                    value={nuevaCuenta.numero}
                    onChange={(e) => setNuevaCuenta((a) => ({ ...a, numero: e.target.value }))}
                  />
                </div>
                <div className={styles.grupo}>
                  <label># Cuenta IBAN (opcional)</label>
                  <input className={styles.input} placeholder="—" disabled />
                </div>
                <div className={styles.grupo}>
                  <label>Tipo Cuenta</label>
                  <select
                    className={styles.input}
                    value={nuevaCuenta.tipo}
                    onChange={(e) => setNuevaCuenta((a) => ({ ...a, tipo: e.target.value }))}
                  >
                    <option>Corriente</option>
                    <option>Ahorros</option>
                  </select>
                </div>
              </div>
              <div className={styles.modalFoot}>
                <button className={styles.btnGhost} onClick={() => setModalBanco(false)}>
                  Cancelar
                </button>
                <button className={styles.btnPrimary} onClick={agregarCuenta}>
                  Guardar
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function PerfilField({ label, value, disabled, badge, eye, placeholder }) {
  return (
    <div className={styles.fieldFloatWrap}>
      <span className={`${styles.floatLabel} ${disabled ? styles.floatMuted : ''}`}>{label}</span>
      <div className={`${styles.inputConIcono} ${disabled ? styles.inputDisabled : ''}`}>
        <span className={styles.inputTexto} style={{ color: disabled ? 'var(--text-muted)' : 'var(--text-primary)' }}>
          {value || placeholder || '—'}
        </span>
        {badge && <span className={styles.badgeDots}>•••</span>}
        {eye && <Eye size={16} style={{ color: 'var(--text-muted)', flex: '0 0 auto' }} />}
      </div>
    </div>
  );
}

function FieldFloat({ label, value, chev, muted, float }) {
  return (
    <div className={styles.fieldFloatWrap}>
      <span className={`${styles.floatLabel} ${float ? '' : ''}`} style={{ color: float ? 'var(--text-secondary)' : undefined }}>
        {label}
      </span>
      <div className={styles.inputConIcono}>
        <span className={styles.inputTexto} style={{ color: muted ? 'var(--text-muted)' : 'var(--text-primary)' }}>
          {value}
        </span>
        {chev && <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>▼</span>}
      </div>
    </div>
  );
}

function ProximamenteBanner({ titulo, texto }) {
  return (
    <div className={styles.proximamente}>
      <AlertTriangle size={16} />
      <div>
        <strong>{titulo}</strong> — {texto}
      </div>
    </div>
  );
}

function CargaCertificado({ onCargar, deshabilitado }) {
  const [archivo, setArchivo] = useState(null);
  const [contrasena, setContrasena] = useState('');
  const [subiendo, setSubiendo] = useState(false);

  const enviar = async () => {
    if (!archivo || !contrasena) return;
    if (!archivo.name.toLowerCase().endsWith('.p12') && !archivo.name.toLowerCase().endsWith('.pfx')) {
      return;
    }
    setSubiendo(true);
    try {
      await onCargar(archivo, contrasena);
      setArchivo(null);
      setContrasena('');
    } finally {
      setSubiendo(false);
    }
  };

  return (
    <div className={styles.zonaCarga}>
      <Upload size={32} />
      <p>{archivo ? archivo.name : 'Selecciona tu certificado .p12 o .pfx'}</p>
      <span>La contraseña se guarda cifrada y nunca se devuelve por el API. Máx. 5 MB.</span>
      <input
        type="file"
        accept=".p12,.pfx"
        className={styles.inputArchivo}
        onChange={(e) => setArchivo(e.target.files?.[0] ?? null)}
        aria-label="Archivo del certificado"
      />
      <input
        type="password"
        className={styles.input}
        style={{ maxWidth: 280, marginTop: 12 }}
        placeholder="Contraseña del certificado"
        autoComplete="new-password"
        value={contrasena}
        onChange={(e) => setContrasena(e.target.value)}
      />
      <button className={styles.btnPrimario} onClick={enviar} disabled={!archivo || !contrasena || subiendo || deshabilitado}>
        {subiendo ? 'Verificando…' : 'Cargar certificado'}
      </button>
      {deshabilitado && <span className={styles.ayuda}>Sin conexión con el servidor — modo demostración.</span>}
    </div>
  );
}

function EstadoFirmaDetalle({ firma }) {
  const dias = diasParaExpirar(firma.validaHasta);
  const expirada = dias < 0;
  const porExpirar = !expirada && dias <= DIAS_AVISO_EXPIRACION;
  return (
    <div className={`${styles.tarjetaFirma} ${expirada ? styles.firmaExpirada : porExpirar ? styles.firmaPorExpirar : styles.firmaVigente}`}>
      <div className={styles.firmaIcono}>{expirada || porExpirar ? <AlertTriangle size={24} /> : <CheckCircle2 size={24} />}</div>
      <div className={styles.firmaDatos}>
        <h4>{firma.nombreArchivo}</h4>
        <dl className={styles.firmaLista}>
          <div>
            <dt>Propietario</dt>
            <dd>{firma.propietario}</dd>
          </div>
          <div>
            <dt>Emisor</dt>
            <dd>{firma.emisor}</dd>
          </div>
          <div>
            <dt>Vigencia</dt>
            <dd>
              {firma.validaDesde} — {firma.validaHasta}
            </dd>
          </div>
        </dl>
        <p className={styles.firmaEstado}>
          {expirada
            ? `Certificado expirado hace ${Math.abs(dias)} días. No se puede emitir.`
            : porExpirar
              ? `Caduca en ${dias} días. Renuévalo antes de que venza.`
              : `Vigente. Caduca en ${dias} días.`}
        </p>
      </div>
    </div>
  );
}
