import { useMemo, useState } from 'react';
import { Send, FileMinus2, FilePlus2 } from 'lucide-react';
import DocumentoVentaForm from '../../components/documentos/DocumentoVentaForm';
import { TIPOS } from '../../api/documentos';
import styles from '../../components/documentos/DocumentoVentaForm.module.css';

/**
 * Nota de Crédito y Nota de Débito.
 *
 * Ambas modifican un comprobante ya emitido, así que el SRI exige la referencia
 * al documento original: tipo, número, fecha y motivo. Sin esos datos el
 * comprobante se rechaza, por eso el formulario los pide antes que nada y
 * bloquea la emisión mientras falten (el backend lo valida igualmente).
 *
 * La diferencia entre ambas es el signo económico: la de crédito devuelve o
 * anula valor (devoluciones, descuentos posteriores), la de débito lo aumenta
 * (intereses, gastos no facturados).
 */

const VARIANTES = {
  credito: {
    tipo: TIPOS.NOTA_CREDITO,
    titulo: 'Nueva Nota de Crédito',
    subtitulo: 'Devuelve o anula valor de un comprobante ya emitido',
    icono: FileMinus2,
    ayuda:
      'Úsala para devoluciones, descuentos posteriores o anulación total de una factura autorizada.',
    motivos: [
      'Devolución de mercadería',
      'Descuento posterior a la emisión',
      'Anulación de la operación',
      'Corrección de valores',
    ],
  },
  debito: {
    tipo: TIPOS.NOTA_DEBITO,
    titulo: 'Nueva Nota de Débito',
    subtitulo: 'Aumenta el valor de un comprobante ya emitido',
    icono: FilePlus2,
    ayuda: 'Úsala para intereses por mora, gastos o valores no incluidos en la factura original.',
    motivos: ['Intereses por mora', 'Gastos no facturados', 'Corrección de valores'],
  },
};

// Tabla 3 del SRI: tipo del documento que se modifica.
const DOCUMENTOS_MODIFICABLES = [
  { codigo: '01', nombre: 'Factura' },
  { codigo: '03', nombre: 'Liquidación de compra' },
  { codigo: '04', nombre: 'Nota de crédito' },
];

const PATRON_NUMERO = /^\d{3}-\d{3}-\d{9}$/;

export default function NotaCreditoForm({ variante = 'credito' }) {
  const configuracion = VARIANTES[variante];

  const [referencia, setReferencia] = useState({
    codigo: '01',
    numero: '',
    fecha: '',
    motivo: configuracion.motivos[0],
  });

  const errores = useMemo(() => {
    const lista = [];
    if (!PATRON_NUMERO.test(referencia.numero.trim())) {
      lista.push('Indica el número del documento original con el formato 001-001-000000135.');
    }
    if (!referencia.fecha) lista.push('Indica la fecha de emisión del documento original.');
    if (!referencia.motivo.trim()) lista.push('Indica el motivo de la nota.');
    return lista;
  }, [referencia]);

  const referenciaCompleta = errores.length === 0;

  const actualizar = (campo, valor) =>
    setReferencia((actual) => ({ ...actual, [campo]: valor }));

  return (
    <DocumentoVentaForm
      tipo={configuracion.tipo}
      titulo={configuracion.titulo}
      subtitulo={configuracion.subtitulo}
      rutaVolver="/comprobantes"
      banner={{
        tono: referenciaCompleta ? 'Info' : 'Aviso',
        texto: referenciaCompleta
          ? 'Este comprobante electrónico se entregará a los servidores del SRI.'
          : 'Indica el documento que se modifica: el SRI rechaza la nota sin esa referencia.',
      }}
      accionPrincipal={{ texto: 'Emitir al SRI', icono: Send }}
      desglosaIva
      etiquetaReceptor="Receptor del documento original"
      erroresExtra={errores}
      datosExtra={{
        documentoModificado: {
          codigo: referencia.codigo,
          numero: referencia.numero.trim(),
          fecha: referencia.fecha,
          motivo: referencia.motivo,
        },
      }}
      camposExtra={
        <div className={styles.grupo} style={{ marginTop: 20, gap: 16 }}>
          <div className={styles.grupo}>
            <label htmlFor="tipoOriginal">Tipo del documento original *</label>
            <select
              id="tipoOriginal"
              className={styles.input}
              value={referencia.codigo}
              onChange={(evento) => actualizar('codigo', evento.target.value)}
            >
              {DOCUMENTOS_MODIFICABLES.map((documento) => (
                <option key={documento.codigo} value={documento.codigo}>
                  {documento.nombre}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.grupo}>
            <label htmlFor="numeroOriginal">Número del documento original *</label>
            <input
              id="numeroOriginal"
              className={styles.input}
              placeholder="001-001-000000135"
              value={referencia.numero}
              onChange={(evento) => actualizar('numero', evento.target.value)}
            />
          </div>

          <div className={styles.grupo}>
            <label htmlFor="fechaOriginal">Fecha de emisión del original *</label>
            <input
              id="fechaOriginal"
              type="date"
              className={styles.input}
              value={referencia.fecha}
              onChange={(evento) => actualizar('fecha', evento.target.value)}
            />
          </div>

          <div className={styles.grupo}>
            <label htmlFor="motivo">Motivo *</label>
            <select
              id="motivo"
              className={styles.input}
              value={referencia.motivo}
              onChange={(evento) => actualizar('motivo', evento.target.value)}
            >
              {configuracion.motivos.map((motivo) => (
                <option key={motivo}>{motivo}</option>
              ))}
            </select>
          </div>

          <p className={styles.etiqueta} style={{ lineHeight: 1.5 }}>
            {configuracion.ayuda}
          </p>
        </div>
      }
    />
  );
}
