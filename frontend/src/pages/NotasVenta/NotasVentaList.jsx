import { useMemo } from 'react';
import ListaDocumentosVenta from '../../components/documentos/ListaDocumentosVenta';
import { useRecurso } from '../../hooks/useRecurso';
import { documentoDesdeApi, TIPOS } from '../../api/documentos';
import { NOTAS_VENTA, ESTADOS_NOTA_VENTA } from '../../data/documentosVenta';

const CONSULTA = { tipo: TIPOS.NOTA_VENTA, tamano: 200 };

export default function NotasVentaList() {
  const recurso = useRecurso('/comprobantes', {
    parametros: CONSULTA,
    datosDemo: NOTAS_VENTA,
  });

  const registros = useMemo(
    () => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(documentoDesdeApi)),
    [recurso.datos, recurso.usandoDemo],
  );

  return (
    <ListaDocumentosVenta
      titulo="Notas de Venta"
      subtitulo="Régimen RIMPE — Negocio Popular. No desglosan IVA."
      datos={registros}
      estados={ESTADOS_NOTA_VENTA}
      rutaNuevo="/notas-venta/nueva"
      textoNuevo="Nueva Nota de Venta"
      cargando={recurso.cargando}
      error={recurso.error}
      usandoDemo={recurso.usandoDemo}
      onReintentar={recurso.recargar}
    />
  );
}
