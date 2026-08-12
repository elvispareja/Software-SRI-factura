import { useEffect, useRef, useState } from 'react';
import { Outlet, Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { URL_API } from '../../api/cliente';
import {
  Home,
  Users,
  Package,
  FileText,
  FileSpreadsheet,
  ReceiptText,
  Settings,
  Menu,
  X,
  Cloud,
  BarChart3,
  TrendingDown,
  HandCoins,
  Repeat,
  Landmark,
  LogOut,
  LifeBuoy,
  Command,
  ChevronDown,
  Bell,
  MessageSquare,
  Mic,
  ShieldCheck,
  MessageCircle,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import SelectorTema from '../../tema/SelectorTema';
import { useSesion } from '../../auth/useSesion';
import PaletaComandos from '../ui/PaletaComandos';
import EstacionComprobante from './EstacionComprobante';
import { esRutaComprobante } from './estaciones';
import ChatSimulador from '../ChatSimulador/ChatSimulador';
import styles from './Layout.module.css';

const iniciales = (nombre) =>
  (nombre ?? '')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0].toUpperCase())
    .join('') || '?';

const CONSULTA_ESCRITORIO = '(min-width: 1024px)';

function saludoHora() {
  const h = new Date().getHours();
  if (h < 12) return 'Buenos días,';
  if (h < 19) return 'Buenas tardes,';
  return 'Buenas noches,';
}

export default function Layout() {
  const { usuario, cerrarSesion } = useSesion();
  const location = useLocation();
  const navigate = useNavigate();
  const [esEscritorio, setEsEscritorio] = useState(
    () => window.matchMedia?.(CONSULTA_ESCRITORIO).matches ?? true,
  );
  const [sidebarAbierto, setSidebarAbierto] = useState(esEscritorio);
  const [assistant, setAssistant] = useState('');
  const [assistantEnviando, setAssistantEnviando] = useState(false);
  const [assistantToast, setAssistantToast] = useState(null);
  const assistantToastRef = useRef(null);

  // Submenús colapsables — mockup líneas 57-131
  const pathname = location.pathname;
  const esReceptores = pathname.startsWith('/receptores');
  // Solo las rutas que de verdad viven en el submenú de Comprobantes (líneas
  // ~280-327). Cotización, Notas de Venta y Recurrente son ítems propios,
  // fuera de ese submenú, y no deben encenderlo.
  const esComprobantes =
    pathname.startsWith('/comprobantes') ||
    pathname.startsWith('/liquidaciones') ||
    pathname.startsWith('/retenciones') ||
    pathname.startsWith('/guias');
  const esEgresos = pathname.startsWith('/gastos') || pathname.startsWith('/egresos');
  const esCuentas = pathname.startsWith('/cuentas');

  // Un solo desplegable abierto a la vez: abrir uno cierra el anterior, en
  // vez de cuatro banderas independientes que se acumulaban en pantalla.
  const seccionDeRuta = esComprobantes
    ? 'comprobantes'
    : esEgresos
      ? 'egresos'
      : esCuentas
        ? 'cuentas'
        : null;
  const [seccionAbierta, setSeccionAbierta] = useState(seccionDeRuta);
  const alternarSeccion = (seccion) =>
    setSeccionAbierta((actual) => (actual === seccion ? null : seccion));

  const compOpen = seccionAbierta === 'comprobantes';
  const egrOpen = seccionAbierta === 'egresos';
  const ctasOpen = seccionAbierta === 'cuentas';

  // Sincroniza con la ruta en cada navegación, incluido cerrar el submenú
  // cuando se entra a una página que no pertenece a ninguno (antes se
  // quedaba abierto el de la sección anterior).
  useEffect(() => {
    setSeccionAbierta(seccionDeRuta);
  }, [seccionDeRuta]);

  useEffect(() => {
    const consulta = window.matchMedia?.(CONSULTA_ESCRITORIO);
    if (!consulta) return undefined;
    const alCambiar = (evento) => {
      setEsEscritorio(evento.matches);
      setSidebarAbierto(evento.matches);
    };
    consulta.addEventListener('change', alCambiar);
    return () => consulta.removeEventListener('change', alCambiar);
  }, []);

  useEffect(() => {
    if (!esEscritorio) setSidebarAbierto(false);
  }, [location.pathname, esEscritorio]);

  useEffect(() => {
    if (esEscritorio || !sidebarAbierto) return undefined;
    const alPresionar = (evento) => {
      if (evento.key === 'Escape') setSidebarAbierto(false);
    };
    window.addEventListener('keydown', alPresionar);
    return () => window.removeEventListener('keydown', alPresionar);
  }, [esEscritorio, sidebarAbierto]);

  const mostrarEtiquetas = sidebarAbierto || !esEscritorio;
  const enEstacionComprobante = esRutaComprobante(pathname);

  const mostrarAssistantToast = (msg) => {
    setAssistantToast(msg);
    clearTimeout(assistantToastRef.current);
    assistantToastRef.current = setTimeout(() => setAssistantToast(null), 4200);
  };

  const onAssistantSend = async () => {
    const t = assistant.trim();
    if (!t || assistantEnviando) return;
    setAssistant('');
    // Si hay sesión real, intenta POST al backend WhatsApp (Graph API v21.0 vía orquestador).
    // El header no tiene número de WhatsApp: se informa al usuario cómo contactar al bot.
    if (!usuario || usuario.modoDemo) {
      mostrarAssistantToast('Escribe al bot de WhatsApp directamente. El asistente del header requiere sesión activa.');
      window.dispatchEvent(new CustomEvent('cwo:assistant', { detail: t }));
      return;
    }
    setAssistantEnviando(true);
    try {
      // El webhook real es POST /api/whatsapp (HMAC + BackgroundTasks → orquestador.atender_mensaje).
      // Desde el header no hay from/to de WhatsApp, así que se usa un endpoint de asistencia si existe,
      // o se deja el toast informativo y se emite evento para que una vista lo capture.
      const resp = await fetch(`${URL_API}/whatsapp/asistir`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texto: t }),
      });
      if (resp.ok) {
        const data = await resp.json().catch(() => null);
        mostrarAssistantToast(data?.respuesta || 'Asistente: mensaje enviado. Revisa WhatsApp para la respuesta.');
      } else if (resp.status === 404) {
        // Endpoint aún no existe — fallback documentado
        mostrarAssistantToast('Asistente WhatsApp: escribe al número del bot para facturar por chat. Ver docs/avance_fase2_config_soporte_whatsapp.md');
        window.dispatchEvent(new CustomEvent('cwo:assistant', { detail: t }));
      } else {
        const err = await resp.json().catch(() => null);
        mostrarAssistantToast(err?.detail || 'No se pudo contactar al asistente. Intenta desde WhatsApp.');
      }
    } catch {
      mostrarAssistantToast('Sin conexión con el asistente. Escribe al bot de WhatsApp directamente.');
      window.dispatchEvent(new CustomEvent('cwo:assistant', { detail: t }));
    } finally {
      setAssistantEnviando(false);
    }
  };

  return (
    <div className={styles.container}>
      <AnimatePresence>
        {!esEscritorio && sidebarAbierto && (
          <motion.div
            className={styles.overlay}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSidebarAbierto(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={`${styles.sidebar} ${
          esEscritorio && !sidebarAbierto ? styles.sidebarColapsado : ''
        } ${esEscritorio ? '' : styles.sidebarMovil} ${
          !esEscritorio && sidebarAbierto ? styles.sidebarMovilAbierto : ''
        }`}
      >
        <div className={styles.logoContainer}>
          <button
            className={styles.botonMenuLateral}
            onClick={() => setSidebarAbierto((abierto) => !abierto)}
            aria-label={sidebarAbierto ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={sidebarAbierto}
          >
            <Menu size={24} />
          </button>
          {mostrarEtiquetas && (
            <div className={styles.logoMarca}>
              <div className={styles.logoIcon}>
                <Cloud size={22} strokeWidth={1.9} />
              </div>
              <div className={styles.logoTexto}>
                <div className={styles.logoSuperior}>CLOUD</div>
                <div className={styles.logoNombre}>
                  Factur <em>AI</em>
                </div>
              </div>
            </div>
          )}
        </div>

        <nav className={styles.nav}>
          {/* Top: Inicio */}
          <NavLink
            to="/"
            end
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Inicio'}
          >
            <Home size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Inicio</span>}
          </NavLink>

          {/* Receptores: el filtro Cliente/Proveedor/Transportista ya vive en la propia página */}
          <NavLink
            to="/receptores"
            className={({ isActive }) => `${styles.navItem} ${isActive || esReceptores ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Receptores'}
          >
            <Users size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Receptores</span>}
          </NavLink>

          {/* INVENTARIO */}
          {mostrarEtiquetas && <div className={styles.navGrupo}>Inventario</div>}
          <NavLink
            to="/articulos"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Artículos / Servicios'}
          >
            <Package size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Artículos / Servicios</span>}
          </NavLink>

          {/* COMPROBANTES ELECTRÓNICOS */}
          {mostrarEtiquetas && <div className={styles.navGrupo}>Comprobantes electrónicos</div>}
          <button
            type="button"
            className={`${styles.navItem} ${styles.navToggle} ${esComprobantes ? styles.active : ''}`}
            onClick={() => alternarSeccion('comprobantes')}
            aria-expanded={compOpen}
            title={mostrarEtiquetas ? undefined : 'Comprobantes'}
          >
            <FileText size={19} className={styles.navIcon} />
            {mostrarEtiquetas && (
              <>
                <span className={styles.navLabel}>Comprobantes</span>
                <ChevronDown
                  size={16}
                  className={`${styles.chevron} ${compOpen ? styles.chevronAbierto : ''}`}
                />
              </>
            )}
          </button>
          {mostrarEtiquetas && compOpen && (
            <div className={styles.subNavComprobantes}>
              <NavLink
                to="/comprobantes"
                end
                className={({ isActive }) =>
                  `${styles.subItem} ${isActive ? styles.subActive : ''}`
                }
              >
                <span className={styles.subDot} aria-hidden="true" />
                <span className={styles.subLabel}>Facturas</span>
              </NavLink>
              <NavLink
                to="/liquidaciones"
                className={({ isActive }) =>
                  `${styles.subItem} ${isActive ? styles.subActive : ''}`
                }
              >
                <span className={styles.subDot} aria-hidden="true" />
                <span className={styles.subLabel}>Liquidación Compra</span>
              </NavLink>
              <NavLink
                to="/retenciones"
                className={({ isActive }) =>
                  `${styles.subItem} ${isActive ? styles.subActive : ''}`
                }
              >
                <span className={styles.subDot} aria-hidden="true" />
                <span className={styles.subLabel}>Retención</span>
              </NavLink>
              <NavLink
                to="/guias"
                className={({ isActive }) =>
                  `${styles.subItem} ${isActive ? styles.subActive : ''}`
                }
              >
                <span className={styles.subDot} aria-hidden="true" />
                <span className={styles.subLabel}>Guia Remisión</span>
              </NavLink>
              <NavLink
                to="/comprobantes/nota-credito"
                className={({ isActive }) =>
                  `${styles.subItem} ${isActive ? styles.subActive : ''}`
                }
              >
                <span className={styles.subDot} aria-hidden="true" />
                <span className={styles.subLabel}>Notas</span>
              </NavLink>
            </div>
          )}

          <NavLink
            to="/cotizaciones"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Cotización'}
          >
            <FileSpreadsheet size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Cotización</span>}
          </NavLink>
          <NavLink
            to="/notas-venta"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Notas de Venta'}
          >
            <ReceiptText size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Notas de Venta</span>}
          </NavLink>
          <NavLink
            to="/recurrentes"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Recurrente'}
          >
            <Repeat size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Recurrente</span>}
          </NavLink>

          <button
            type="button"
            className={`${styles.navItem} ${styles.navToggle} ${esEgresos ? styles.active : ''}`}
            onClick={() => alternarSeccion('egresos')}
            aria-expanded={egrOpen}
            title={mostrarEtiquetas ? undefined : 'Egresos'}
          >
            <TrendingDown size={19} className={styles.navIcon} />
            {mostrarEtiquetas && (
              <>
                <span className={styles.navLabel}>Egresos</span>
                <ChevronDown
                  size={15}
                  className={`${styles.chevron} ${egrOpen ? styles.chevronAbierto : ''}`}
                />
              </>
            )}
          </button>
          {mostrarEtiquetas && egrOpen && (
            <div className={styles.subNavEgresos}>
              <NavLink
                to="/gastos"
                className={({ isActive }) =>
                  `${styles.subItemSm} ${isActive ? styles.subActive : ''}`
                }
              >
                Gastos
              </NavLink>
            </div>
          )}

          <NavLink
            to="/anticipos"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Anticipos'}
          >
            <HandCoins size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Anticipos</span>}
          </NavLink>

          {/* CUENTAS PENDIENTES */}
          {mostrarEtiquetas && <div className={styles.navGrupo}>Cuentas pendientes</div>}
          <button
            type="button"
            className={`${styles.navItem} ${styles.navToggle} ${esCuentas ? styles.active : ''}`}
            onClick={() => alternarSeccion('cuentas')}
            aria-expanded={ctasOpen}
            title={mostrarEtiquetas ? undefined : 'Cuentas'}
          >
            <Landmark size={19} className={styles.navIcon} />
            {mostrarEtiquetas && (
              <>
                <span className={styles.navLabel}>Cuentas</span>
                <ChevronDown
                  size={15}
                  className={`${styles.chevron} ${ctasOpen ? styles.chevronAbierto : ''}`}
                />
              </>
            )}
          </button>
          {mostrarEtiquetas && ctasOpen && (
            <div className={styles.subNavEgresos}>
              <NavLink
                to="/cuentas?tipo=cobrar"
                className={({ isActive }) =>
                  `${styles.subItemSm} ${isActive ? styles.subActive : ''}`
                }
              >
                Cuentas por Cobrar
              </NavLink>
              <NavLink
                to="/cuentas?tipo=pagar"
                className={({ isActive }) =>
                  `${styles.subItemSm} ${isActive ? styles.subActive : ''}`
                }
              >
                Cuentas por Pagar
              </NavLink>
            </div>
          )}

          {/* OPCIONES */}
          {mostrarEtiquetas && <div className={styles.navGrupo}>Opciones</div>}
          <NavLink
            to="/reportes"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Reportes'}
          >
            <BarChart3 size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Reportes</span>}
          </NavLink>
          <NavLink
            to="/configuraciones"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Configuraciones'}
          >
            <Settings size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Configuraciones</span>}
          </NavLink>
          <NavLink
            to="/soporte"
            className={({ isActive }) => `${styles.navItem} ${isActive ? styles.active : ''}`}
            title={mostrarEtiquetas ? undefined : 'Soporte Técnico'}
          >
            <LifeBuoy size={19} className={styles.navIcon} />
            {mostrarEtiquetas && <span className={styles.navLabel}>Soporte Técnico</span>}
          </NavLink>
        </nav>

        {mostrarEtiquetas && (
          <Link to="/configuraciones" className={styles.sriCard}>
            <div className={styles.sriCardIcon}>
              <ShieldCheck size={22} strokeWidth={1.9} />
            </div>
            <div className={styles.sriCardTitle}>Cumple con el SRI</div>
            <div className={styles.sriCardDesc}>
              Facturación electrónica
              <br />
              100% legal y segura
            </div>
            <span className={styles.sriCardChat}>
              <MessageCircle size={15} strokeWidth={2} />
            </span>
          </Link>
        )}
      </aside>

      <main className={styles.main}>
        <header className={styles.header}>
          <div className={styles.headerGlass}>
            <button
              className={styles.burgerBtn}
              onClick={() => setSidebarAbierto((abierto) => !abierto)}
              aria-label={sidebarAbierto ? 'Cerrar menú' : 'Abrir menú'}
              aria-expanded={sidebarAbierto}
              style={{ display: esEscritorio ? 'none' : 'flex' }}
            >
              {sidebarAbierto ? <X size={20} /> : <Menu size={20} />}
            </button>

            <div className={styles.headerSaludo}>
              <div className={styles.avatarGrande}>{iniciales(usuario?.nombre)}</div>
              <div className={styles.saludoTexto}>
                <div className={styles.saludoHola}>{saludoHora()}</div>
                <div className={styles.saludoNombre}>{usuario?.nombre ?? 'Usuario'}</div>
              </div>
            </div>

            <div className={styles.headerCentro} />

            <div className={styles.headerCluster}>
              <span className={styles.clusterCloud} aria-hidden="true">
                <Cloud size={24} strokeWidth={1.8} />
              </span>
              <button
                type="button"
                className={styles.clusterBtn}
                title="Mensajes"
                aria-label="Mensajes"
                onClick={() => navigate('/soporte')}
              >
                <MessageSquare size={21} strokeWidth={1.8} />
              </button>
              <button
                type="button"
                className={styles.clusterBtnBell}
                title="Notificaciones"
                aria-label="Notificaciones"
              >
                <Bell size={21} strokeWidth={1.8} />
                <span className={styles.badge}>0</span>
              </button>
              <span className={styles.sriLogo} aria-hidden="true">
                <span className={styles.sriLogoAzul}>SR</span>
                <span className={styles.sriLogoRojo}>i</span>
              </span>
            </div>

            <div className={styles.whatsappBox}>
              <div className={styles.whatsappTitle}>WhatsApp AI Assistant</div>
              <div className={styles.whatsappRow}>
                <input
                  className={styles.whatsappInput}
                  value={assistant}
                  onChange={(e) => setAssistant(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && onAssistantSend()}
                  placeholder="ej., Crear Factura para Juan..."
                  aria-label="WhatsApp AI Assistant"
                  disabled={assistantEnviando}
                />
                <button
                  type="button"
                  className={styles.whatsappSend}
                  onClick={onAssistantSend}
                  title="Enviar"
                  aria-label="Enviar al asistente"
                  disabled={assistantEnviando}
                  style={{ opacity: assistantEnviando ? 0.6 : 1 }}
                >
                  <Mic size={19} strokeWidth={1.9} />
                </button>
              </div>
              {assistantToast && <div className={styles.whatsappToast}>{assistantToast}</div>}
            </div>

            <div className={styles.headerActions}>
              {usuario?.modoDemo && (
                <span className={styles.insigniaDemo} title="Sin conexión con el servidor">
                  Modo demostración
                </span>
              )}
              <button
                className={styles.atajoPaleta}
                onClick={() =>
                  window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', ctrlKey: true }))
                }
                title="Buscar (Ctrl+K)"
                type="button"
              >
                <Command size={14} />
                <span>Buscar</span>
                <kbd>Ctrl K</kbd>
              </button>
              <SelectorTema />
              <button
                className={styles.menuButton}
                onClick={cerrarSesion}
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
                type="button"
              >
                <LogOut size={18} />
              </button>
            </div>
          </div>
        </header>

        <div className={styles.content}>
          {enEstacionComprobante ? (
            <EstacionComprobante>
              <Outlet />
            </EstacionComprobante>
          ) : (
            <Outlet />
          )}
        </div>

        <PaletaComandos />
        <ChatSimulador />
      </main>
    </div>
  );
}
