import { Send, FileUp, ImageUp } from 'lucide-react';
import DocumentoVentaForm from '../../components/documentos/DocumentoVentaForm';
import { TIPOS } from '../../api/documentos';
import styles from '../../components/documentos/DocumentoVentaForm.module.css';

/**
 * Liquidación de Compra de Bienes y Prestación de Servicios.
 *
 * La emite el comprador cuando el proveedor no puede emitir factura (por
 * ejemplo, personas no obligadas a inscribirse en el RUC). Por eso el receptor
 * del documento es un PROVEEDOR y no un cliente, y el backend lo valida.
 */
export default function LiquidacionForm() {
  return (
    <DocumentoVentaForm
      tipo={TIPOS.LIQUIDACION}
      titulo="Nueva Liquidación de Compra"
      subtitulo="Comprobante que emite el comprador por cuenta del proveedor"
      rutaVolver="/liquidaciones"
      banner={{
        tono: 'Info',
        texto: 'Este comprobante electrónico se entregará a los servidores del SRI.',
      }}
      accionPrincipal={{ texto: 'Emitir al SRI', icono: Send }}
      desglosaIva
      rolReceptor="Proveedor"
      etiquetaReceptor="Proveedor"
      accionesSecundarias={
        <>
          <button className={styles.btnSecondary} title="Cargar el XML del proveedor">
            <FileUp size={18} /> Importar XML
          </button>
          <button className={styles.btnSecondary} title="Extraer datos de una foto o PDF">
            <ImageUp size={18} /> Importar PDF / Foto
          </button>
        </>
      }
    />
  );
}
