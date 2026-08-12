import { Send } from 'lucide-react';
import DocumentoVentaForm from '../../components/documentos/DocumentoVentaForm';
import { TIPOS } from '../../api/documentos';

export default function FacturaForm() {
  return (
    <DocumentoVentaForm
      tipo={TIPOS.FACTURA}
      titulo="Emitir Factura"
      subtitulo="Borrador — no enviada al SRI"
      rutaVolver="/comprobantes"
      banner={{
        tono: 'Info',
        texto: 'Este comprobante electrónico se entregará a los servidores del SRI.',
      }}
      accionPrincipal={{ texto: 'Emitir al SRI', icono: Send }}
      desglosaIva
    />
  );
}
