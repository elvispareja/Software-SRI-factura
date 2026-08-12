import { useMemo, useState } from 'react';
import { SendHorizonal } from 'lucide-react';
import DocumentoVentaForm from '../../components/documentos/DocumentoVentaForm';
import { TIPOS } from '../../api/documentos';
import styles from '../../components/documentos/DocumentoVentaForm.module.css';

/**
 * La cotización (proforma) no es un comprobante electrónico: no viaja al SRI.
 * Por eso el banner es neutro y se añade la validez de la oferta, que es el
 * dato propio de este documento.
 */
export default function CotizacionForm() {
  const [diasValidez, setDiasValidez] = useState('15');

  const errores = useMemo(() => {
    const dias = Number(diasValidez);
    return Number.isFinite(dias) && dias > 0
      ? []
      : ['La validez de la oferta debe ser al menos 1 día.'];
  }, [diasValidez]);

  return (
    <DocumentoVentaForm
      tipo={TIPOS.COTIZACION}
      titulo="Nueva Cotización"
      subtitulo="Proforma — documento interno, no se envía al SRI"
      rutaVolver="/cotizaciones"
      banner={{
        tono: 'Neutro',
        texto:
          'Documento sin validez tributaria. Se convierte en factura cuando el cliente acepta.',
      }}
      accionPrincipal={{ texto: 'Enviar cotización', icono: SendHorizonal }}
      desglosaIva
      datosExtra={{ validezDias: diasValidez }}
      erroresExtra={errores}
      camposExtra={
        <div className={styles.grupo} style={{ marginTop: 16 }}>
          <label htmlFor="validez">Validez de la oferta (días)</label>
          <input
            id="validez"
            type="number"
            min="1"
            className={styles.input}
            value={diasValidez}
            onChange={(evento) => setDiasValidez(evento.target.value)}
          />
        </div>
      }
    />
  );
}
