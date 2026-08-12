import { useState, useRef, useEffect } from 'react';
import { X, Send, Bot, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ia } from '../../api/ia';
import styles from './ChatSimulador.module.css';

export default function ChatSimulador() {
  const [abierto, setAbierto] = useState(false);
  const [mensajes, setMensajes] = useState([
    { id: '1', emisor: 'bot', texto: '¡Hola! Soy el simulador del Asistente de Facturación IA. ¿Qué deseas facturar hoy?' }
  ]);
  const [texto, setTexto] = useState('');
  const [cargando, setCargando] = useState(false);
  const finMensajesRef = useRef(null);

  // Usar un ID de teléfono consistente durante la sesión
  const telefonoSesion = useRef(`simulador-${Math.random().toString(36).substring(7)}`);

  const scrollAbajo = () => {
    finMensajesRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (abierto) {
      scrollAbajo();
    }
  }, [mensajes, abierto]);

  const enviar = async (e) => {
    e.preventDefault();
    const mensajeLimpio = texto.trim();
    if (!mensajeLimpio || cargando) return;

    const idMensaje = Date.now().toString();
    setMensajes((prev) => [...prev, { id: idMensaje, emisor: 'usuario', texto: mensajeLimpio }]);
    setTexto('');
    setCargando(true);

    try {
      const respuesta = await ia.simularMensaje(telefonoSesion.current, mensajeLimpio);
      setMensajes((prev) => [...prev, { id: Date.now().toString(), emisor: 'bot', texto: respuesta }]);
    } catch (error) {
      setMensajes((prev) => [
        ...prev,
        { id: Date.now().toString(), emisor: 'bot', texto: `⚠️ Error de conexión: ${error.message}` }
      ]);
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      <button 
        className={styles.fab} 
        onClick={() => setAbierto(true)}
        aria-label="Abrir Simulador IA"
        title="Simulador IA (Local)"
      >
        <Bot size={24} />
      </button>

      <AnimatePresence>
        {abierto && (
          <motion.div 
            className={styles.chatContenedor}
            initial={{ opacity: 0, y: 50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 50, scale: 0.9 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          >
            <div className={styles.chatHeader}>
              <div className={styles.headerInfo}>
                <div className={styles.avatarBot}><Bot size={20} /></div>
                <div>
                  <h3 className={styles.titulo}>Orquestador IA (Simulador)</h3>
                  <p className={styles.subtitulo}>Pruebas locales sin WhatsApp</p>
                </div>
              </div>
              <button className={styles.botonCerrar} onClick={() => setAbierto(false)}>
                <X size={20} />
              </button>
            </div>

            <div className={styles.chatArea}>
              {mensajes.map((msg) => (
                <div key={msg.id} className={`${styles.mensajeContenedor} ${msg.emisor === 'usuario' ? styles.mensajeUsuario : styles.mensajeBot}`}>
                  {msg.emisor === 'bot' && <div className={styles.iconoMini}><Bot size={14} /></div>}
                  <div className={`${styles.burbuja} ${msg.emisor === 'usuario' ? styles.burbujaUsuario : styles.burbujaBot}`}>
                    {msg.texto}
                  </div>
                </div>
              ))}
              {cargando && (
                <div className={`${styles.mensajeContenedor} ${styles.mensajeBot}`}>
                  <div className={styles.iconoMini}><Bot size={14} /></div>
                  <div className={`${styles.burbuja} ${styles.burbujaBot} ${styles.escribiendo}`}>
                    <Loader2 size={16} className={styles.spinner} /> <span>Procesando con Gemini...</span>
                  </div>
                </div>
              )}
              <div ref={finMensajesRef} />
            </div>

            <form onSubmit={enviar} className={styles.inputArea}>
              <input
                type="text"
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                placeholder="Ej. Factura 50 usd a Juan Pérez..."
                className={styles.input}
                disabled={cargando}
                autoFocus
              />
              <button 
                type="submit" 
                className={styles.botonEnviar} 
                disabled={!texto.trim() || cargando}
              >
                <Send size={18} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
