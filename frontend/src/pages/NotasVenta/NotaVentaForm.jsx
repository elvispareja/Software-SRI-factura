import { Send } from 'lucide-react';
import DocumentoVentaForm from '../../components/documentos/DocumentoVentaForm';
import { TIPOS } from '../../api/documentos';

/**
 * Nota de Venta del régimen RIMPE - Negocio Popular.
 *
 * Este régimen no traslada IVA, así que se fuerza la tarifa 0% en todas las
 * líneas y se oculta la columna: dejar elegir una tarifa que el régimen no
 * admite solo produciría comprobantes rechazados.
 */
export default function NotaVentaForm() {
  return (
    <DocumentoVentaForm
      tipo={TIPOS.NOTA_VENTA}
      titulo="Nueva Nota de Venta"
      subtitulo="Régimen RIMPE — Negocio Popular"
      rutaVolver="/notas-venta"
      banner={{
        tono: 'Aviso',
        texto: 'Régimen RIMPE Negocio Popular: la nota de venta no desglosa IVA.',
      }}
      accionPrincipal={{ texto: 'Emitir nota de venta', icono: Send }}
      desglosaIva={false}
      tarifaForzada="0"
    />
  );
}
