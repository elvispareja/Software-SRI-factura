import { useMemo } from 'react';
import ListaDocumentosVenta from '../../components/documentos/ListaDocumentosVenta';
import { useRecurso } from '../../hooks/useRecurso';
import { documentoDesdeApi, TIPOS } from '../../api/documentos';
import { COTIZACIONES, ESTADOS_COTIZACION } from '../../data/documentosVenta';

const CONSULTA = { tipo: TIPOS.COTIZACION, tamano: 200 };

export default function CotizacionesList() {
  const recurso = useRecurso('/comprobantes', {
    parametros: CONSULTA,
    datosDemo: COTIZACIONES,
  });

  const registros = useMemo(
    () => (recurso.usandoDemo ? recurso.datos : recurso.datos.map(documentoDesdeApi)),
    [recurso.datos, recurso.usandoDemo],
  );

  return (
    <ListaDocumentosVenta
      titulo="Cotizaciones"
      subtitulo="Proformas enviadas a clientes. No son comprobantes electrónicos."
      datos={registros}
      estados={ESTADOS_COTIZACION}
      rutaNuevo="/cotizaciones/nueva"
      textoNuevo="Nueva Cotización"
      columnaExtra={{
        titulo: 'Validez',
        valor: (item) => (item.validez ? `${item.validez} días` : '—'),
      }}
      cargando={recurso.cargando}
      error={recurso.error}
      usandoDemo={recurso.usandoDemo}
      onReintentar={recurso.recargar}
    />
  );
}
