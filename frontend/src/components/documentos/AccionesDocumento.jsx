import { useEffect, useState } from 'react';
import {
  CalendarClock,
  FileDown,
  FileCode2,
  Loader2,
  Mail,
  RefreshCw,
  Send,
  X,
} from 'lucide-react';
import { generarCuotas } from '../../api/cuentas';
import {
  ACCIONES_COMPROBANTE,
  ESTADOS_CONSULTABLES,
  ESTADOS_EMITIBLES,
  estadoCorreo,
} from '../../api/documentos';
import styles from './AccionesDocumento.module.css';

/**
 * Acciones por fila de los listados de comprobantes, guías y retenciones.
 *
 * Qué se ofrece depende del estado ante el SRI: emitir solo tiene sentido
 * mientras no esté autorizado, y reconsultar solo si el SRI ya lo recibió.
 * Mostrar botones que van a fallar es peor que no mostrarlos.
 *
 * Los tres documentos tienen exactamente el mismo ciclo —RIDE, XML, emitir,
 * consultar— así que en vez de triplicar el componente se le pasa el juego de
 * rutas del recurso en `acciones`.
 */
export default function AccionesDocumento({
  comprobante,
  acciones = ACCIONES_COMPROBANTE,
  onActualizar,
}) {
  const [ocupado, setOcupado] = useState(null);
  const [mensajes, setMensajes] = useState(null);
  // Se consulta una vez si hay SMTP: sin él, el botón se ofrece igual pero
  // deshabilitado y explicando por qué, en vez de fallar al pulsarlo.
  const [correoListo, setCorreoListo] = useState(null);
  const [cuotasAbierto, setCuotasAbierto] = useState(false);

  useEffect(() => {
    let vigente = true;
    estadoCorreo()
      .then(({ datos }) => vigente && setCorreoListo(Boolean(datos?.configurado)))
      .catch(() => vigente && setCorreoListo(false));
    return () => {
      vigente = false;
    };
  }, []);

  const estado = comprobante.estadoSRI ?? comprobante.estado;
  const puedeEmitir = ESTADOS_EMITIBLES.has(estado);
  const puedeConsultar = ESTADOS_CONSULTABLES.has(estado) && Boolean(comprobante.claveAcceso);
  const autorizado = estado === 'Autorizado';
  const seEnviaPorCorreo = acciones.enviar !== undefined;
  // Solo tiene sentido repartir en cuotas lo que aún se debe.
  const sePuedeFraccionar =
    autorizado && seEnviaPorCorreo && comprobante.estadoPago !== 'Pagado';

  const ejecutar = async (accion, operacion) => {
    setOcupado(accion);
    setMensajes(null);

    try {
      const { datos } = await operacion(comprobante.id);
      // El SRI devuelve el motivo del rechazo aquí; es lo único que permite corregir.
      if (datos.mensajes?.length) setMensajes({ tono: 'aviso', lista: datos.mensajes });
      // El envío por correo responde con un solo mensaje, no con una lista.
      else if (datos.mensaje) setMensajes({ tono: 'aviso', lista: [{ mensaje: datos.mensaje }] });
      onActualizar?.();
    } catch (error) {
      setMensajes({ tono: 'error', lista: [{ mensaje: error.message }] });
    } finally {
      setOcupado(null);
    }
  };

  return (
    <div className={styles.contenedor}>
      <div className={styles.botones}>
        {/* El RIDE se puede ver siempre: en borrador sale con la marca de pruebas. */}
        <a
          className={styles.boton}
          href={acciones.urlRide(comprobante.id)}
          target="_blank"
          rel="noreferrer"
          title="Ver el RIDE en PDF"
        >
          <FileDown size={15} /> RIDE
        </a>

        <a
          className={styles.boton}
          href={acciones.urlXml(comprobante.id)}
          title="Descargar el XML"
        >
          <FileCode2 size={15} /> XML
        </a>

        {puedeEmitir && (
          <button
            className={styles.botonPrimario}
            onClick={() => ejecutar('emitir', acciones.emitir)}
            disabled={ocupado !== null}
            title="Firmar y enviar al SRI"
          >
            {ocupado === 'emitir' ? (
              <Loader2 size={15} className={styles.girando} />
            ) : (
              <Send size={15} />
            )}
            {estado === 'Borrador' ? 'Emitir' : 'Reintentar'}
          </button>
        )}

        {puedeConsultar && (
          <button
            className={styles.boton}
            onClick={() => ejecutar('consultar', acciones.consultar)}
            disabled={ocupado !== null}
            title="Volver a consultar la autorización al SRI"
          >
            {ocupado === 'consultar' ? (
              <Loader2 size={15} className={styles.girando} />
            ) : (
              <RefreshCw size={15} />
            )}
            Consultar
          </button>
        )}

        {autorizado && seEnviaPorCorreo && (
          <button
            className={styles.boton}
            onClick={() => ejecutar('enviar', acciones.enviar)}
            disabled={ocupado !== null || correoListo === false}
            title={
              correoListo === false
                ? 'El envío por correo no está configurado (SMTP_SERVIDOR).'
                : 'Enviar al receptor con el XML y el RIDE adjuntos'
            }
          >
            {ocupado === 'enviar' ? (
              <Loader2 size={15} className={styles.girando} />
            ) : (
              <Mail size={15} />
            )}
            Enviar
          </button>
        )}

        {sePuedeFraccionar && (
          <button
            className={styles.boton}
            onClick={() => setCuotasAbierto(true)}
            disabled={ocupado !== null}
            title="Repartir el importe en cuotas con vencimiento"
          >
            <CalendarClock size={15} /> Cuotas
          </button>
        )}

        {autorizado && comprobante.numeroAutorizacion && (
          <span className={styles.autorizacion} title="Número de autorización del SRI">
            {comprobante.numeroAutorizacion}
          </span>
        )}
      </div>

      {cuotasAbierto && (
        <DialogoCuotas
          comprobante={comprobante}
          onCerrar={() => setCuotasAbierto(false)}
          onGenerado={(cantidad) => {
            setCuotasAbierto(false);
            setMensajes({
              tono: 'aviso',
              lista: [{ mensaje: `Se generaron ${cantidad} cuotas. Se gestionan en Cuentas.` }],
            });
            onActualizar?.();
          }}
        />
      )}

      {mensajes && (
        <ul className={mensajes.tono === 'error' ? styles.mensajesError : styles.mensajes}>
          {mensajes.lista.map((item, indice) => (
            <li key={indice}>
              {item.identificador ? `[${item.identificador}] ` : ''}
              {item.mensaje}
              {item.informacion_adicional ? ` — ${item.informacion_adicional}` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}


/**
 * Reparte el importe de un comprobante en cuotas.
 *
 * El resto se acumula en la última cuota, y eso lo hace el servidor: dividir
 * 100 en 3 da 33,33 tres veces, que suma 99,99, y la cuota que falta un
 * centavo es un cobro que nunca cuadra.
 */
function DialogoCuotas({ comprobante, onCerrar, onGenerado }) {
  const [cuotas, setCuotas] = useState('3');
  const [dias, setDias] = useState('30');
  const [primera, setPrimera] = useState(() => new Date().toISOString().slice(0, 10));
  const [error, setError] = useState(null);
  const [ocupado, setOcupado] = useState(false);

  const cantidad = Number(cuotas) || 0;
  const valido = cantidad >= 1 && cantidad <= 60 && Number(dias) >= 1;

  const generar = async () => {
    setOcupado(true);
    setError(null);
    try {
      const { datos } = await generarCuotas(comprobante.id, {
        cuotas: cantidad,
        diasEntreCuotas: Number(dias),
        primeraFecha: primera,
      });
      onGenerado(datos.length);
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className={styles.fondoDialogo} onClick={onCerrar}>
      <div
        className={styles.dialogo}
        onClick={(evento) => evento.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Generar cuotas"
      >
        <div className={styles.dialogoCabecera}>
          <strong>Cuotas de {comprobante.numero}</strong>
          <button className={styles.boton} onClick={onCerrar} aria-label="Cerrar">
            <X size={15} />
          </button>
        </div>

        <div className={styles.dialogoCuerpo}>
          {error && <p className={styles.mensajesError}>{error}</p>}

          <label htmlFor="cuotas-cantidad">Número de cuotas</label>
          <input
            id="cuotas-cantidad"
            type="number"
            min="1"
            max="60"
            value={cuotas}
            onChange={(evento) => setCuotas(evento.target.value)}
          />

          <label htmlFor="cuotas-dias">Días entre cuotas</label>
          <input
            id="cuotas-dias"
            type="number"
            min="1"
            max="365"
            value={dias}
            onChange={(evento) => setDias(evento.target.value)}
          />

          <label htmlFor="cuotas-primera">Vencimiento de la primera</label>
          <input
            id="cuotas-primera"
            type="date"
            value={primera}
            onChange={(evento) => setPrimera(evento.target.value)}
          />

          <p className={styles.ayudaDialogo}>
            El comprobante pasará a método <strong>Crédito</strong>. Regenerar el plan
            borra las cuotas anteriores, y no se puede si ya hay cobros registrados.
          </p>
        </div>

        <div className={styles.dialogoPie}>
          <button className={styles.boton} onClick={onCerrar}>
            Cancelar
          </button>
          <button
            className={styles.botonPrimario}
            onClick={generar}
            disabled={!valido || ocupado}
          >
            {ocupado ? <Loader2 size={15} className={styles.girando} /> : null}
            Generar {cantidad} cuotas
          </button>
        </div>
      </div>
    </div>
  );
}
