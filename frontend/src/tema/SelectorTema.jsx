import { Moon, Sun, MonitorSmartphone } from 'lucide-react';
import { useTema } from './useTema';
import styles from './SelectorTema.module.css';

const ETIQUETAS = {
  sistema: { icono: MonitorSmartphone, texto: 'Tema del sistema' },
  claro: { icono: Sun, texto: 'Tema claro' },
  oscuro: { icono: Moon, texto: 'Tema oscuro' },
};

export default function SelectorTema() {
  const { preferencia, alternarTema } = useTema();
  const { icono: Icono, texto } = ETIQUETAS[preferencia];

  return (
    <button
      type="button"
      className={styles.boton}
      onClick={alternarTema}
      title={`${texto} (clic para cambiar)`}
      aria-label={`${texto}. Clic para cambiar de tema.`}
    >
      <Icono size={18} />
    </button>
  );
}
