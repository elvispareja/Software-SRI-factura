import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Cloud, LogIn, UserPlus, AlertCircle, WifiOff, Loader2 } from 'lucide-react';
import { useSesion } from '../../auth/useSesion';
import { ErrorApi } from '../../api/cliente';
import SelectorTema from '../../tema/SelectorTema';
import styles from './Login.module.css';

const LONGITUD_MINIMA_CONTRASENA = 8;

export default function Login() {
  const { autenticado, iniciarSesion, registrar, entrarEnModoDemo } = useSesion();
  const ubicacion = useLocation();

  const [modo, setModo] = useState('entrar');
  const [correo, setCorreo] = useState('');
  const [nombre, setNombre] = useState('');
  const [contrasena, setContrasena] = useState('');
  const [error, setError] = useState(null);
  const [sinServidor, setSinServidor] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [aviso, setAviso] = useState(null);

  if (autenticado) {
    const destino = ubicacion.state?.desde ?? '/';
    return <Navigate to={destino} replace />;
  }

  const esRegistro = modo === 'registro';

  const enviar = async (evento) => {
    evento.preventDefault();
    setError(null);
    setAviso(null);
    setSinServidor(false);
    setEnviando(true);

    try {
      if (esRegistro) {
        await registrar(correo, nombre, contrasena);
        // Tras registrarse se entra directamente, sin pedir la clave otra vez.
        await iniciarSesion(correo, contrasena);
      } else {
        await iniciarSesion(correo, contrasena);
      }
    } catch (fallo) {
      if (fallo instanceof ErrorApi && fallo.esFalloDeRed) {
        setSinServidor(true);
      } else {
        setError(fallo.message);
      }
    } finally {
      setEnviando(false);
    }
  };

  const cambiarModo = () => {
    setModo(esRegistro ? 'entrar' : 'registro');
    setError(null);
    setSinServidor(false);
    setAviso(
      esRegistro
        ? null
        : 'La primera cuenta que se registre queda como administrador del sistema.',
    );
  };

  const contrasenaCorta = esRegistro && contrasena.length > 0 && contrasena.length < LONGITUD_MINIMA_CONTRASENA;
  const puedeEnviar =
    correo.trim() !== '' &&
    contrasena.length >= (esRegistro ? LONGITUD_MINIMA_CONTRASENA : 1) &&
    (!esRegistro || nombre.trim() !== '');

  return (
    <div className={styles.pantalla}>
      <div className={styles.esquina}>
        <SelectorTema />
      </div>

      <motion.div
        className={`${styles.tarjeta} glass-panel`}
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className={styles.marca}>
          <div className={styles.marcaIcono}>
            <Cloud size={26} strokeWidth={1.9} />
          </div>
          <div>
            <h1 className={styles.marcaNombre}>
              <small>CLOUD</small>
              Factur <span>AI</span>
            </h1>
            <p className={styles.marcaLema}>Facturación electrónica para Ecuador</p>
          </div>
        </div>

        <h2 className={styles.titulo}>{esRegistro ? 'Crear cuenta' : 'Iniciar sesión'}</h2>

        <form className={styles.formulario} onSubmit={enviar}>
          {esRegistro && (
            <div className={styles.grupo}>
              <label htmlFor="nombre">Nombre completo</label>
              <input
                id="nombre"
                className={styles.input}
                autoComplete="name"
                value={nombre}
                onChange={(evento) => setNombre(evento.target.value)}
              />
            </div>
          )}

          <div className={styles.grupo}>
            <label htmlFor="correo">Correo electrónico</label>
            <input
              id="correo"
              type="email"
              className={styles.input}
              autoComplete="username"
              value={correo}
              onChange={(evento) => setCorreo(evento.target.value)}
            />
          </div>

          <div className={styles.grupo}>
            <label htmlFor="contrasena">Contraseña</label>
            <input
              id="contrasena"
              type="password"
              className={`${styles.input} ${contrasenaCorta ? styles.inputError : ''}`}
              autoComplete={esRegistro ? 'new-password' : 'current-password'}
              value={contrasena}
              onChange={(evento) => setContrasena(evento.target.value)}
            />
            {esRegistro && (
              <span className={contrasenaCorta ? styles.ayudaError : styles.ayuda}>
                Mínimo {LONGITUD_MINIMA_CONTRASENA} caracteres.
              </span>
            )}
          </div>

          {aviso && <p className={styles.aviso}>{aviso}</p>}

          {error && (
            <p className={styles.error}>
              <AlertCircle size={16} /> {error}
            </p>
          )}

          {sinServidor && (
            <div className={styles.sinServidor}>
              <WifiOff size={18} />
              <div>
                <strong>No se pudo conectar con el servidor.</strong>
                <p>
                  Levanta el backend con <code>uvicorn app.main:aplicacion</code>, o entra en modo
                  demostración para recorrer la interfaz con datos de ejemplo.
                </p>
                <button type="button" className={styles.btnDemo} onClick={entrarEnModoDemo}>
                  Entrar en modo demostración
                </button>
              </div>
            </div>
          )}

          <button type="submit" className={styles.btnPrincipal} disabled={!puedeEnviar || enviando}>
            {enviando ? (
              <>
                <Loader2 size={18} className={styles.girando} /> Procesando…
              </>
            ) : esRegistro ? (
              <>
                <UserPlus size={18} /> Crear cuenta
              </>
            ) : (
              <>
                <LogIn size={18} /> Entrar
              </>
            )}
          </button>
        </form>

        <button type="button" className={styles.btnCambiarModo} onClick={cambiarModo}>
          {esRegistro ? '¿Ya tienes cuenta? Inicia sesión' : '¿No tienes cuenta? Regístrate'}
        </button>
      </motion.div>
    </div>
  );
}
