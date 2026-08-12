import { useMemo, useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LifeBuoy,
  MessageCircle,
  Mail,
  PlayCircle,
  ChevronDown,
  Send,
  Search,
  CircleDot,
  CheckCircle2,
  Clock,
  Plus,
  X,
  Video,
  Image as ImageIcon,
  AlertTriangle,
} from 'lucide-react';
import { contieneTexto } from '../../lib/texto';
import { useSesion } from '../../auth/useSesion';
import styles from './Soporte.module.css';

const PREGUNTAS = [
  {
    id: 'clave-acceso',
    pregunta: '¿Qué es la clave de acceso y por qué la rechaza el SRI?',
    respuesta:
      'Es el identificador de 49 dígitos que lleva todo comprobante electrónico. Se compone de fecha, tipo de documento, RUC, ambiente, serie, secuencial, código numérico, tipo de emisión y un dígito verificador módulo 11. Los rechazos casi siempre vienen de un secuencial repetido o de un ambiente equivocado (pruebas vs. producción).',
  },
  {
    id: 'firma',
    pregunta: 'Mi factura sale con “FIRMA INVÁLIDA”. ¿Qué reviso?',
    respuesta:
      'Primero, que el certificado no esté caducado (lo ves en Configuraciones → Firma Electrónica → Conexiones Tributarias). Segundo, que sea de una entidad acreditada: Banco Central, Security Data, ANF o Uanataca. Un certificado autofirmado nunca será aceptado por el SRI aunque la firma sea criptográficamente correcta.',
  },
  {
    id: 'direccion',
    pregunta: '¿Por qué me exige la dirección del cliente?',
    respuesta:
      'El XML del comprobante lleva el campo direccionComprador y el SRI lo valida. Sin dirección el comprobante se devuelve, por eso el sistema no deja guardar un receptor sin ella.',
  },
  {
    id: 'iva',
    pregunta: '¿Cómo manejo productos con distinto IVA en una misma factura?',
    respuesta:
      'Cada línea lleva su propia tarifa y el sistema agrupa los totales por tarifa automáticamente. Puedes mezclar 15%, 0%, exento y no objeto en un mismo comprobante: el resumen muestra un subtotal por cada tarifa usada.',
  },
  {
    id: 'ambiente',
    pregunta: '¿Cuándo paso de pruebas a producción?',
    respuesta:
      'Cuando hayas emitido correctamente al menos un comprobante de cada tipo en el ambiente de pruebas. El cambio se hace en Configuraciones → Empresa → Ambiente SRI. Ojo: los secuenciales de pruebas y producción son independientes.',
  },
  {
    id: 'whatsapp',
    pregunta: '¿Cómo funciona la facturación por WhatsApp?',
    respuesta:
      'Escribes al bot en lenguaje natural ("factura de 50 a Juan Pérez, RUC 179..."). El asistente extrae los datos, valida la identificación contra el algoritmo del SRI, calcula los totales y te muestra un resumen. La factura solo se emite después de que confirmes.',
  },
];

const VIDEOS = [
  { id: 1, titulo: 'Recorrido general de la plataforma', duracion: '8:42' },
  { id: 2, titulo: 'Cómo crear una factura electrónica', duracion: '6:15' },
  { id: 3, titulo: 'Cómo crear un cliente', duracion: '3:28' },
  { id: 4, titulo: 'Cómo crear bienes y servicios', duracion: '5:03' },
  { id: 5, titulo: 'Vinculación con el SRI y firma electrónica', duracion: '7:51' },
  { id: 6, titulo: 'Notas de crédito y débito', duracion: '4:37' },
];

const CATEGORIAS = ['Técnico', 'Facturación', 'Cuenta', 'Otro'];

const CASOS_SEMILLA = [
  { id: 'TK-000124', asunto: 'Error al cargar el certificado .p12', categoria: 'Técnico', estado: 'Abierto', fecha: '2026-08-07', descripcion: 'Al subir el .p12 el sistema dice contraseña incorrecta.' },
  { id: 'TK-000123', asunto: 'Duda sobre secuenciales por punto de emisión', categoria: 'Facturación', estado: 'Respondido', fecha: '2026-08-05', descripcion: '¿Cada punto de emisión lleva su propio secuencial?' },
  { id: 'TK-000121', asunto: 'Solicitud de ampliación de plan', categoria: 'Cuenta', estado: 'Cerrado', fecha: '2026-07-28', descripcion: 'Necesito pasar de 30 a 100 documentos.' },
];

const ICONO_ESTADO = {
  Abierto: { icono: CircleDot, clase: 'estadoAbierto' },
  Respondido: { icono: Clock, clase: 'estadoRespondido' },
  Cerrado: { icono: CheckCircle2, clase: 'estadoCerrado' },
};

function useCasosLocales() {
  const [casos, setCasos] = useState(() => {
    try {
      const guardados = localStorage.getItem('soporte_casos');
      if (guardados) return JSON.parse(guardados);
    } catch { /* ignore */ }
    return CASOS_SEMILLA;
  });
  useEffect(() => {
    try { localStorage.setItem('soporte_casos', JSON.stringify(casos)); } catch { /* ignore */ }
  }, [casos]);
  return [casos, setCasos];
}

export default function Soporte() {
  const { usuario } = useSesion();
  const [casos, setCasos] = useCasosLocales();
  const [sopTab, setSopTab] = useState('casos'); // casos | base
  const [sopFilter, setSopFilter] = useState('Todos');
  const [busqueda, setBusqueda] = useState('');
  const [busquedaCasos, setBusquedaCasos] = useState('');
  const [abierta, setAbierta] = useState(null);
  const [toast, setToast] = useState(null);

  // Modal Nuevo Caso — fiel a isSopModal 1560-1608
  const [sopModal, setSopModal] = useState(false);
  const [asunto, setAsunto] = useState('');
  const [categoria, setCategoria] = useState('Técnico');
  const [catOpen, setCatOpen] = useState(false);
  const [detalle, setDetalle] = useState('');
  const [imagenes, setImagenes] = useState([]); // File[]
  const [video, setVideo] = useState(null);
  const [quiereMail, setQuiereMail] = useState(true);
  const fileImgRef = useRef(null);
  const fileVideoRef = useRef(null);

  const notify = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3200);
  };

  const preguntasFiltradas = useMemo(
    () => PREGUNTAS.filter((item) => contieneTexto(item.pregunta, busqueda) || contieneTexto(item.respuesta, busqueda)),
    [busqueda],
  );

  const casosFiltrados = useMemo(() => {
    let lista = [...casos];
    if (sopFilter === 'Abiertos') lista = lista.filter((c) => c.estado === 'Abierto');
    if (sopFilter === 'Esperando') lista = lista.filter((c) => c.estado === 'Respondido');
    if (sopFilter === 'Resueltos') lista = lista.filter((c) => c.estado === 'Cerrado');
    if (busquedaCasos.trim()) {
      const q = busquedaCasos.toLowerCase();
      lista = lista.filter((c) => `${c.asunto} ${c.id} ${c.categoria}`.toLowerCase().includes(q));
    }
    return lista;
  }, [casos, sopFilter, busquedaCasos]);

  const handleImagenes = (files) => {
    const arr = Array.from(files || []).slice(0, 3 - imagenes.length);
    const validas = [];
    for (const f of arr) {
      if (!f.type.startsWith('image/')) { notify('Solo se permiten imágenes.'); continue; }
      if (f.size > 5 * 1024 * 1024) { notify(`${f.name} supera 5 MB.`); continue; }
      validas.push(f);
    }
    if (imagenes.length + validas.length > 3) { notify('Máximo 3 imágenes.'); return; }
    setImagenes((prev) => [...prev, ...validas].slice(0, 3));
  };

  const handleVideo = (file) => {
    if (!file) return;
    const ok = ['video/mp4', 'video/webm', 'video/quicktime'];
    if (!ok.includes(file.type) && !file.name.match(/\.(mp4|webm|mov)$/i)) { notify('Formato no soportado: mp4, webm o mov.'); return; }
    if (file.size > 50 * 1024 * 1024) { notify('El video no debe superar 50 MB.'); return; }
    setVideo(file);
  };

  const puedeCrear = asunto.trim() !== '' && categoria && detalle.trim().length >= 10;

  const crearCaso = () => {
    if (!puedeCrear) { notify('Completa asunto, categoría y descripción (mín. 10 caracteres).'); return; }
    const nuevo = {
      id: `TK-${String(Date.now()).slice(-6)}`,
      asunto: asunto.trim(),
      categoria,
      descripcion: detalle.trim(),
      estado: 'Abierto',
      fecha: new Date().toISOString().slice(0, 10),
      imagenes: imagenes.map((f) => f.name),
      video: video?.name || null,
      quiereMail,
    };
    setCasos((prev) => [nuevo, ...prev]);
    setSopModal(false);
    setAsunto(''); setCategoria('Técnico'); setDetalle(''); setImagenes([]); setVideo(null); setQuiereMail(true);
    setSopFilter('Todos');
    notify('Caso creado. Te responderemos por este apartado' + (quiereMail ? ' y por correo.' : '.'));
  };

  return (
    <div className={styles.container}>
      {/* Banner Soporte — canal en desarrollo */}
      <div className={styles.bannerDesarrollo}>
        <AlertTriangle size={16} />
        <span><strong>Soporte — canal en desarrollo.</strong> Los casos se guardan solo en este navegador hasta que exista el endpoint del backend. Contrato futuro: <code>POST /api/soporte/casos</code>.</span>
      </div>

      {/* Sub-app header replicando mockup isSopApp líneas 1510-1524 */}
      <div className={styles.sopApp}>
        <div className={styles.sopTopBar}>
          <span className={styles.sopBrand}>
            <span className={styles.sopLogo}>FACTOA</span>
            <span className={styles.sopTitle}>Soporte Técnico</span>
          </span>
          <span className={styles.sopUserPill}>{usuario?.nombre ?? 'EMISOR DEMO EJEMPLO'}</span>
        </div>

        <div className={styles.sopTabsBar}>
          {[
            ['casos', 'Mis casos', 'M4 8a2 2 0 0 0 0 8v2h16v-2a2 2 0 0 1 0-8V6H4ZM10 8v8'],
            ['base', 'Base de conocimiento', 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM9.6 9.2A2.5 2.5 0 0 1 14 10.5c0 1.7-2 1.8-2 3.5M12 17h.01'],
          ].map(([k, label]) => {
            const on = sopTab === k;
            return (
              <button key={k} className={`${styles.sopTab} ${on ? styles.sopTabOn : ''}`} onClick={() => setSopTab(k)}>
                {label}
              </button>
            );
          })}
        </div>

        {sopTab === 'casos' ? (
          <div className={styles.sopBody}>
            <div className={styles.sopHero}>
              <span className={styles.sopHeroIcon}><LifeBuoy size={22} /></span>
              <div className={styles.sopHeroText}>
                <div className={styles.sopHeroTitle}>¿Tuviste algún problema?</div>
                <div className={styles.sopHeroDesc}>En este apartado puedes reportar cualquier inconveniente o duda que tengas con la plataforma. Creamos un caso y le damos seguimiento contigo hasta resolverlo: verás aquí mismo cada respuesta de nuestro equipo.</div>
              </div>
              <button className={styles.btnNuevoCaso} onClick={() => setSopModal(true)}><Plus size={15} /> Nuevo Caso</button>
            </div>

            <div className={`${styles.panel} glass-panel`}>
              <div className={styles.sopFilterBar}>
                <span className={styles.sopFilters}>
                  {['Todos', 'Abiertos', 'Esperando', 'Resueltos'].map((label) => {
                    const on = sopFilter === label;
                    return (
                      <button key={label} className={`${styles.sopFilter} ${on ? styles.sopFilterOn : ''}`} onClick={() => setSopFilter(label)}>
                        {label}
                      </button>
                    );
                  })}
                </span>
                <span className={styles.sopSearch}>
                  <Search size={14} />
                  <input placeholder="Buscar en mis casos..." value={busquedaCasos} onChange={(e) => setBusquedaCasos(e.target.value)} />
                </span>
              </div>

              {casosFiltrados.length === 0 ? (
                <div className={styles.sopEmpty}>
                  <p>No tienes casos en esta vista.</p>
                  <button className={styles.btnCrearPrimero} onClick={() => setSopModal(true)}><Plus size={15} /> Crear Mi Primer Caso</button>
                </div>
              ) : (
                <ul className={styles.tickets}>
                  {casosFiltrados.map((ticket) => {
                    const { icono: Icono, clase } = ICONO_ESTADO[ticket.estado] ?? ICONO_ESTADO.Abierto;
                    return (
                      <li className={styles.ticket} key={ticket.id}>
                        <Icono size={16} className={styles[clase]} />
                        <div>
                          <strong>{ticket.asunto}</strong>
                          <span>{ticket.id} · {ticket.categoria} · {ticket.fecha}</span>
                        </div>
                        <span className={`${styles.badge} ${styles[clase]}`}>{ticket.estado}</span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>

            <div className={styles.sopFooterMail}>¿Prefieres escribirnos por correo? Escríbenos a <a href="mailto:soporte@factoa.net">soporte@factoa.net</a> y con gusto te ayudamos.</div>

            {/* Videotutoriales — se mantienen como sección secundaria */}
            <section className={`${styles.panel} glass-panel`} style={{ padding: 24 }}>
              <h2 className={styles.panelTitulo}>Videotutoriales</h2>
              <div className={styles.videos}>
                {VIDEOS.map((v) => (
                  <button key={v.id} className={styles.video} onClick={() => notify('Reproducción — próximamente')}>
                    <PlayCircle size={22} />
                    <div><strong>{v.titulo}</strong><span>{v.duracion}</span></div>
                  </button>
                ))}
              </div>
            </section>
          </div>
        ) : (
          <div className={styles.sopBody}>
            <div className={styles.canales}>
              <a href="https://wa.me/593999999999" className={`${styles.canal} glass-panel`}>
                <MessageCircle size={22} /><div><strong>WhatsApp</strong><span>Respuesta en minutos, horario laboral</span></div>
              </a>
              <a href="mailto:soporte@factoa.ec" className={`${styles.canal} glass-panel`}>
                <Mail size={22} /><div><strong>Correo</strong><span>soporte@factoa.ec · respuesta en 24 h</span></div>
              </a>
              <div className={`${styles.canal} glass-panel`}>
                <LifeBuoy size={22} /><div><strong>Estado del servicio</strong><span className={styles.operativo}>Todos los sistemas operativos</span></div>
              </div>
            </div>

            <section className={`${styles.panel} glass-panel`} style={{ padding: 24 }}>
              <div className={styles.panelCabecera}>
                <h2 className={styles.panelTitulo} style={{ margin: 0 }}>Preguntas frecuentes</h2>
                <div className={styles.buscador}>
                  <Search size={16} />
                  <input placeholder="Buscar en la ayuda…" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} aria-label="Buscar en preguntas frecuentes" />
                </div>
              </div>
              {preguntasFiltradas.length === 0 ? (
                <p className={styles.vacio}>Nada coincide con “{busqueda}”. Escríbenos y lo resolvemos.</p>
              ) : (
                <div className={styles.acordeon}>
                  {preguntasFiltradas.map((item) => {
                    const open = abierta === item.id;
                    return (
                      <div className={styles.item} key={item.id}>
                        <button className={styles.itemCabecera} onClick={() => setAbierta(open ? null : item.id)} aria-expanded={open}>
                          <span>{item.pregunta}</span>
                          <ChevronDown size={18} className={`${styles.chevron} ${open ? styles.chevronAbierto : ''}`} />
                        </button>
                        <AnimatePresence initial={false}>
                          {open && (
                            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.2 }} className={styles.itemCuerpo}>
                              <p>{item.respuesta}</p>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>
          </div>
        )}
      </div>

      {/* Modal Nuevo Caso — fiel a isSopModal 1560-1608 */}
      <AnimatePresence>
        {sopModal && (
          <motion.div className={styles.modalOverlay} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setSopModal(false)}>
            <motion.div
              className={styles.modal}
              initial={{ y: 24, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 24, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className={styles.modalHead}>
                <span className={styles.modalIcon}><MessageCircle size={17} /></span>
                <div style={{ flex: 1 }}>
                  <div className={styles.modalTitle}>Nuevo caso de soporte</div>
                  <div className={styles.modalSub}>Cuéntanos con detalle qué necesitas. Te responderemos por este mismo apartado y, si lo activas, también por correo.</div>
                </div>
                <button className={styles.modalClose} onClick={() => setSopModal(false)}><X size={16} /></button>
              </div>

              <div className={styles.modalBody}>
                <div className={styles.modalGrid2}>
                  <div className={styles.grupo}>
                    <label>Asunto</label>
                    <input className={styles.input} placeholder="Ej. No me deja timbrar una factura" value={asunto} onChange={(e) => setAsunto(e.target.value)} />
                  </div>
                  <div className={styles.grupo}>
                    <label>Categoría</label>
                    <div className={styles.selectWrap}>
                      <button className={styles.selectBtn} onClick={() => setCatOpen((v) => !v)} type="button">
                        <span>{categoria}</span><ChevronDown size={16} style={{ transform: catOpen ? 'rotate(180deg)' : 'none', transition: '.2s' }} />
                      </button>
                      {catOpen && (
                        <div className={styles.selectMenu}>
                          {CATEGORIAS.map((c) => (
                            <button key={c} className={`${styles.selectOpt} ${c === categoria ? styles.selectOptOn : ''}`} onClick={() => { setCategoria(c); setCatOpen(false); }}>{c}</button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>

                <div className={styles.grupo}>
                  <label>Describe tu problema</label>
                  <textarea
                    className={styles.input}
                    placeholder="¿Qué estabas haciendo? ¿Qué esperabas que pasara y qué pasó? Incluye mensajes de error, número de documento, etc."
                    rows={4}
                    value={detalle}
                    onChange={(e) => setDetalle(e.target.value)}
                  />
                </div>

                <div className={styles.grupo}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ImageIcon size={16} /> Adjuntar capturas (opcional, hasta 3)</label>
                  <div className={styles.uploadRow}>
                    <input type="file" accept="image/*" multiple ref={fileImgRef} hidden onChange={(e) => handleImagenes(e.target.files)} />
                    <button className={styles.btnUpload} onClick={() => fileImgRef.current?.click()} type="button">Seleccionar imágenes</button>
                    <span className={styles.uploadHint}>{imagenes.length ? `${imagenes.length}/3 — ${imagenes.map((f) => f.name).join(', ')}` : 'Máximo 3 imágenes'}</span>
                  </div>
                  {imagenes.length > 0 && (
                    <div className={styles.fileChips}>
                      {imagenes.map((f, i) => (
                        <span key={i} className={styles.fileChip}>{f.name} <button onClick={() => setImagenes((prev) => prev.filter((_, j) => j !== i))}><X size={12} /></button></span>
                      ))}
                    </div>
                  )}
                </div>

                <div className={styles.grupo}>
                  <input type="file" accept="video/mp4,video/webm,video/quicktime,.mp4,.webm,.mov" ref={fileVideoRef} hidden onChange={(e) => handleVideo(e.target.files?.[0])} />
                  <button className={styles.btnVideo} onClick={() => fileVideoRef.current?.click()} type="button"><Video size={16} /> Adjuntar Un Video (Opcional)</button>
                  <span className={styles.ayuda}>Si el problema es difícil de explicar, graba la pantalla: máximo 50 MB (mp4, webm o mov). El video queda disponible 30 días.</span>
                  {video && <span className={styles.fileChip}>{video.name} · {(video.size / 1024 / 1024).toFixed(1)} MB <button onClick={() => setVideo(null)}><X size={12} /></button></span>}
                </div>

                <label className={styles.checkRow} onClick={() => setQuiereMail((v) => !v)}>
                  <span className={`${styles.checkBox} ${quiereMail ? styles.checkOn : ''}`}>{quiereMail && <CheckCircle2 size={11} />}</span>
                  <span>Quiero recibir las respuestas por correo</span>
                </label>
              </div>

              <div className={styles.modalFoot}>
                <button className={styles.btnGhost} onClick={() => setSopModal(false)}>Cancelar</button>
                <button className={styles.btnCrear} onClick={crearCaso} disabled={!puedeCrear}><Send size={16} /> Crear Caso</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {toast && (
        <motion.div className={styles.toast} initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }}>
          {toast}
        </motion.div>
      )}
    </div>
  );
}
