import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Home,
  Users,
  UserPlus,
  Package,
  PackagePlus,
  FileText,
  FilePlus2,
  FileMinus2,
  FileSpreadsheet,
  ReceiptText,
  ClipboardList,
  Truck,
  Percent,
  BarChart3,
  Settings,
  LifeBuoy,
  Sun,
  Moon,
  MonitorSmartphone,
  Search,
  CornerDownLeft,
} from 'lucide-react';
import { useTema } from '../../tema/useTema';
import { contieneTexto } from '../../lib/texto';
import styles from './PaletaComandos.module.css';

/**
 * Paleta de comandos (Ctrl/Cmd + K).
 *
 * El plan pide navegación tipo Spotlight para evitar clics. Se monta una sola
 * vez en el Layout y escucha el atajo globalmente.
 */

const GRUPOS = [
  {
    nombre: 'Ir a',
    comandos: [
      { id: 'inicio', etiqueta: 'Inicio', icono: Home, ruta: '/' },
      { id: 'receptores', etiqueta: 'Receptores', icono: Users, ruta: '/receptores' },
      { id: 'articulos', etiqueta: 'Artículos y Servicios', icono: Package, ruta: '/articulos' },
      { id: 'comprobantes', etiqueta: 'Comprobantes', icono: FileText, ruta: '/comprobantes' },
      { id: 'cotizaciones', etiqueta: 'Cotizaciones', icono: FileSpreadsheet, ruta: '/cotizaciones' },
      { id: 'notas-venta', etiqueta: 'Notas de Venta', icono: ReceiptText, ruta: '/notas-venta' },
      { id: 'liquidaciones', etiqueta: 'Liquidaciones de Compra', icono: ClipboardList, ruta: '/liquidaciones' },
      { id: 'guias', etiqueta: 'Guías de Remisión', icono: Truck, ruta: '/guias' },
      { id: 'retenciones', etiqueta: 'Retenciones', icono: Percent, ruta: '/retenciones' },
      { id: 'reportes', etiqueta: 'Reportes', icono: BarChart3, ruta: '/reportes' },
      { id: 'configuraciones', etiqueta: 'Configuraciones', icono: Settings, ruta: '/configuraciones' },
      { id: 'soporte', etiqueta: 'Soporte Técnico', icono: LifeBuoy, ruta: '/soporte' },
    ],
  },
  {
    nombre: 'Crear',
    comandos: [
      { id: 'nueva-factura', etiqueta: 'Nueva Factura', icono: FilePlus2, ruta: '/comprobantes/nuevo' },
      { id: 'nuevo-receptor', etiqueta: 'Nuevo Receptor', icono: UserPlus, ruta: '/receptores/nuevo' },
      { id: 'nuevo-articulo', etiqueta: 'Nuevo Artículo', icono: PackagePlus, ruta: '/articulos/nuevo' },
      { id: 'nueva-cotizacion', etiqueta: 'Nueva Cotización', icono: FileSpreadsheet, ruta: '/cotizaciones/nueva' },
      { id: 'nueva-guia', etiqueta: 'Nueva Guía de Remisión', icono: Truck, ruta: '/guias/nueva' },
      { id: 'nueva-retencion', etiqueta: 'Nueva Retención', icono: Percent, ruta: '/retenciones/nueva' },
      { id: 'nueva-liquidacion', etiqueta: 'Nueva Liquidación de Compra', icono: ClipboardList, ruta: '/liquidaciones/nueva' },
      { id: 'nueva-nota-venta', etiqueta: 'Nueva Nota de Venta', icono: ReceiptText, ruta: '/notas-venta/nueva' },
      { id: 'nota-credito', etiqueta: 'Nueva Nota de Crédito', icono: FileMinus2, ruta: '/comprobantes/nota-credito' },
      { id: 'nota-debito', etiqueta: 'Nueva Nota de Débito', icono: FilePlus2, ruta: '/comprobantes/nota-debito' },
    ],
  },
];

export default function PaletaComandos() {
  const [abierta, setAbierta] = useState(false);
  const [consulta, setConsulta] = useState('');
  const [indiceActivo, setIndiceActivo] = useState(0);
  const navegar = useNavigate();
  const { setPreferencia } = useTema();
  const campoRef = useRef(null);

  const comandosTema = useMemo(
    () => [
      { id: 'tema-claro', etiqueta: 'Cambiar a tema claro', icono: Sun, accion: () => setPreferencia('claro') },
      { id: 'tema-oscuro', etiqueta: 'Cambiar a tema oscuro', icono: Moon, accion: () => setPreferencia('oscuro') },
      { id: 'tema-sistema', etiqueta: 'Usar el tema del sistema', icono: MonitorSmartphone, accion: () => setPreferencia('sistema') },
    ],
    [setPreferencia],
  );

  const grupos = useMemo(() => {
    const todos = [...GRUPOS, { nombre: 'Apariencia', comandos: comandosTema }];
    if (consulta.trim() === '') return todos;

    return todos
      .map((grupo) => ({
        ...grupo,
        comandos: grupo.comandos.filter((comando) => contieneTexto(comando.etiqueta, consulta)),
      }))
      .filter((grupo) => grupo.comandos.length > 0);
  }, [consulta, comandosTema]);

  // Lista plana para poder navegar con flechas a través de los grupos.
  const planos = useMemo(() => grupos.flatMap((grupo) => grupo.comandos), [grupos]);

  useEffect(() => {
    const alPresionar = (evento) => {
      const esAtajo = (evento.ctrlKey || evento.metaKey) && evento.key.toLowerCase() === 'k';
      if (esAtajo) {
        evento.preventDefault();
        setAbierta((valor) => !valor);
      }
    };

    window.addEventListener('keydown', alPresionar);
    return () => window.removeEventListener('keydown', alPresionar);
  }, []);

  useEffect(() => {
    if (abierta) {
      setConsulta('');
      setIndiceActivo(0);
      // El autofocus del input no basta: el elemento se monta con la animación.
      requestAnimationFrame(() => campoRef.current?.focus());
    }
  }, [abierta]);

  useEffect(() => {
    setIndiceActivo(0);
  }, [consulta]);

  const ejecutar = (comando) => {
    setAbierta(false);
    if (comando.ruta) navegar(comando.ruta);
    else comando.accion?.();
  };

  const alTeclear = (evento) => {
    if (evento.key === 'Escape') {
      setAbierta(false);
      return;
    }
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      setIndiceActivo((indice) => (indice + 1) % Math.max(planos.length, 1));
      return;
    }
    if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      setIndiceActivo((indice) => (indice - 1 + planos.length) % Math.max(planos.length, 1));
      return;
    }
    if (evento.key === 'Enter' && planos[indiceActivo]) {
      evento.preventDefault();
      ejecutar(planos[indiceActivo]);
    }
  };

  let contador = -1;

  return (
    <AnimatePresence>
      {abierta && (
        <motion.div
          className={styles.fondo}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setAbierta(false)}
        >
          <motion.div
            className={`${styles.paleta} glass-panel`}
            initial={{ opacity: 0, y: -16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            onClick={(evento) => evento.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Paleta de comandos"
          >
            <div className={styles.campoWrapper}>
              <Search size={18} className={styles.campoIcono} />
              <input
                ref={campoRef}
                className={styles.campo}
                placeholder="Buscar acción o sección…"
                value={consulta}
                onChange={(evento) => setConsulta(evento.target.value)}
                onKeyDown={alTeclear}
                aria-label="Buscar comando"
              />
              <kbd className={styles.tecla}>Esc</kbd>
            </div>

            <div className={styles.resultados}>
              {planos.length === 0 ? (
                <p className={styles.vacio}>Sin coincidencias para &ldquo;{consulta}&rdquo;</p>
              ) : (
                grupos.map((grupo) => (
                  <div key={grupo.nombre} className={styles.grupo}>
                    <span className={styles.grupoTitulo}>{grupo.nombre}</span>
                    {grupo.comandos.map((comando) => {
                      contador += 1;
                      const activo = contador === indiceActivo;
                      return (
                        <button
                          key={comando.id}
                          className={`${styles.comando} ${activo ? styles.comandoActivo : ''}`}
                          onMouseEnter={() => setIndiceActivo(planos.indexOf(comando))}
                          onClick={() => ejecutar(comando)}
                        >
                          <comando.icono size={18} />
                          <span>{comando.etiqueta}</span>
                          {activo && <CornerDownLeft size={14} className={styles.enter} />}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            <div className={styles.pie}>
              <span>
                <kbd className={styles.tecla}>↑</kbd>
                <kbd className={styles.tecla}>↓</kbd> navegar
              </span>
              <span>
                <kbd className={styles.tecla}>↵</kbd> abrir
              </span>
              <span>
                <kbd className={styles.tecla}>Ctrl</kbd>
                <kbd className={styles.tecla}>K</kbd> alternar
              </span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
