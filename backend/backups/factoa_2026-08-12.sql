--
-- PostgreSQL database dump
--

\restrict OuSnLr164PgCaFidb7UMGy5uolGwKlzhf6LQJywg8vVcBu6QwSwneY0Ej6SUaLu

-- Dumped from database version 17.10
-- Dumped by pg_dump version 17.10

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: anticipos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.anticipos (
    id integer NOT NULL,
    fecha date NOT NULL,
    tipo character varying(3) NOT NULL,
    receptor_id integer,
    receptor_razon_social character varying(300) NOT NULL,
    detalle character varying(300) NOT NULL,
    monto numeric(14,6) NOT NULL,
    facturado numeric(14,6) NOT NULL,
    forma_pago character varying(30) NOT NULL,
    estado character varying(20) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.anticipos OWNER TO factoa;

--
-- Name: anticipos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.anticipos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.anticipos_id_seq OWNER TO factoa;

--
-- Name: anticipos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.anticipos_id_seq OWNED BY public.anticipos.id;


--
-- Name: articulos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.articulos (
    id integer NOT NULL,
    codigo character varying(50) NOT NULL,
    codigo_auxiliar character varying(50),
    nombre character varying(300) NOT NULL,
    detalle text,
    tipo character varying(20) NOT NULL,
    categoria character varying(120),
    marca character varying(120),
    unidad character varying(50) NOT NULL,
    bodega character varying(120),
    ubicacion character varying(120),
    codigo_iva character varying(2) NOT NULL,
    codigo_ice character varying(10),
    costo numeric(14,6) NOT NULL,
    precio numeric(14,6) NOT NULL,
    stock numeric(14,6),
    stock_minimo numeric(14,6) NOT NULL,
    punto_reorden numeric(14,6) NOT NULL,
    stock_maximo numeric(14,6) NOT NULL,
    estado character varying(20) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.articulos OWNER TO factoa;

--
-- Name: articulos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.articulos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.articulos_id_seq OWNER TO factoa;

--
-- Name: articulos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.articulos_id_seq OWNED BY public.articulos.id;


--
-- Name: comprobantes; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.comprobantes (
    id integer NOT NULL,
    tipo character varying(30) NOT NULL,
    clave_acceso character varying(49),
    numero character varying(20) NOT NULL,
    establecimiento character varying(3) NOT NULL,
    punto_emision character varying(3) NOT NULL,
    secuencial integer NOT NULL,
    fecha_emision date NOT NULL,
    receptor_id integer,
    receptor_razon_social character varying(300) NOT NULL,
    receptor_identificacion character varying(20) NOT NULL,
    total_sin_impuestos numeric(14,6) NOT NULL,
    total_descuento numeric(14,6) NOT NULL,
    total_iva numeric(14,6) NOT NULL,
    importe_total numeric(14,6) NOT NULL,
    metodo character varying(20) NOT NULL,
    forma_pago character varying(2) NOT NULL,
    estado_sri character varying(30) NOT NULL,
    estado_pago character varying(30) NOT NULL,
    numero_autorizacion character varying(100),
    fecha_autorizacion character varying(50),
    mensajes_sri text,
    xml_firmado text,
    validez_dias integer,
    cod_doc_modificado character varying(2),
    num_doc_modificado character varying(20),
    fecha_doc_modificado date,
    motivo character varying(300),
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.comprobantes OWNER TO factoa;

--
-- Name: comprobantes_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.comprobantes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.comprobantes_id_seq OWNER TO factoa;

--
-- Name: comprobantes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.comprobantes_id_seq OWNED BY public.comprobantes.id;


--
-- Name: cuentas_bancarias; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.cuentas_bancarias (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    banco character varying(120) NOT NULL,
    tipo character varying(20) NOT NULL,
    numero character varying(50) NOT NULL,
    titular character varying(200) NOT NULL,
    activa boolean NOT NULL
);


ALTER TABLE public.cuentas_bancarias OWNER TO factoa;

--
-- Name: cuentas_bancarias_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.cuentas_bancarias_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cuentas_bancarias_id_seq OWNER TO factoa;

--
-- Name: cuentas_bancarias_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.cuentas_bancarias_id_seq OWNED BY public.cuentas_bancarias.id;


--
-- Name: cuotas; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.cuotas (
    id integer NOT NULL,
    comprobante_id integer NOT NULL,
    numero integer NOT NULL,
    vence date NOT NULL,
    monto numeric(14,6) NOT NULL,
    cobrado numeric(14,6) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.cuotas OWNER TO factoa;

--
-- Name: cuotas_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.cuotas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.cuotas_id_seq OWNER TO factoa;

--
-- Name: cuotas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.cuotas_id_seq OWNED BY public.cuotas.id;


--
-- Name: detalles_comprobante; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.detalles_comprobante (
    id integer NOT NULL,
    comprobante_id integer NOT NULL,
    codigo_principal character varying(50) NOT NULL,
    codigo_auxiliar character varying(50),
    descripcion character varying(300) NOT NULL,
    cantidad numeric(14,6) NOT NULL,
    precio_unitario numeric(14,6) NOT NULL,
    descuento_porcentaje numeric(14,6) NOT NULL,
    descuento numeric(14,6) NOT NULL,
    codigo_iva character varying(2) NOT NULL,
    base_imponible numeric(14,6) NOT NULL,
    valor_iva numeric(14,6) NOT NULL,
    total numeric(14,6) NOT NULL
);


ALTER TABLE public.detalles_comprobante OWNER TO factoa;

--
-- Name: detalles_comprobante_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.detalles_comprobante_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detalles_comprobante_id_seq OWNER TO factoa;

--
-- Name: detalles_comprobante_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.detalles_comprobante_id_seq OWNED BY public.detalles_comprobante.id;


--
-- Name: detalles_retencion; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.detalles_retencion (
    id integer NOT NULL,
    retencion_id integer NOT NULL,
    codigo_impuesto character varying(2) NOT NULL,
    codigo_retencion character varying(10) NOT NULL,
    base_imponible numeric(14,6) NOT NULL,
    porcentaje_retener numeric(14,6) NOT NULL,
    valor_retenido numeric(14,6) NOT NULL
);


ALTER TABLE public.detalles_retencion OWNER TO factoa;

--
-- Name: detalles_retencion_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.detalles_retencion_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.detalles_retencion_id_seq OWNER TO factoa;

--
-- Name: detalles_retencion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.detalles_retencion_id_seq OWNED BY public.detalles_retencion.id;


--
-- Name: egresos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.egresos (
    id integer NOT NULL,
    fecha date NOT NULL,
    concepto character varying(300) NOT NULL,
    beneficiario character varying(300) NOT NULL,
    monto numeric(14,6) NOT NULL,
    forma_pago character varying(30) NOT NULL,
    cuenta_id integer,
    referencia character varying(60),
    gasto_id integer,
    estado character varying(20) NOT NULL,
    observacion text,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.egresos OWNER TO factoa;

--
-- Name: egresos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.egresos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.egresos_id_seq OWNER TO factoa;

--
-- Name: egresos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.egresos_id_seq OWNED BY public.egresos.id;


--
-- Name: empresas; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.empresas (
    id integer NOT NULL,
    ruc character varying(13) NOT NULL,
    razon_social character varying(300) NOT NULL,
    nombre_comercial character varying(300),
    direccion_matriz character varying(300) NOT NULL,
    provincia character varying(100),
    canton character varying(100),
    telefono character varying(50),
    correo character varying(200),
    regimen character varying(100) NOT NULL,
    obligado_contabilidad boolean NOT NULL,
    contribuyente_especial character varying(20),
    agente_retencion character varying(20),
    contribuyente_rimpe character varying(100),
    ambiente character varying(1) NOT NULL
);


ALTER TABLE public.empresas OWNER TO factoa;

--
-- Name: empresas_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.empresas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.empresas_id_seq OWNER TO factoa;

--
-- Name: empresas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.empresas_id_seq OWNED BY public.empresas.id;


--
-- Name: establecimientos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.establecimientos (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    codigo character varying(3) NOT NULL,
    nombre character varying(200) NOT NULL,
    direccion character varying(300) NOT NULL
);


ALTER TABLE public.establecimientos OWNER TO factoa;

--
-- Name: establecimientos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.establecimientos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.establecimientos_id_seq OWNER TO factoa;

--
-- Name: establecimientos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.establecimientos_id_seq OWNED BY public.establecimientos.id;


--
-- Name: firmas_electronicas; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.firmas_electronicas (
    id integer NOT NULL,
    empresa_id integer NOT NULL,
    nombre_archivo character varying(200) NOT NULL,
    contenido bytea NOT NULL,
    contrasena_cifrada text NOT NULL,
    propietario character varying(300) NOT NULL,
    emisor character varying(300) NOT NULL,
    numero_serie character varying(80) NOT NULL,
    valida_desde date NOT NULL,
    valida_hasta date NOT NULL,
    activa boolean NOT NULL,
    subida_en timestamp with time zone NOT NULL
);


ALTER TABLE public.firmas_electronicas OWNER TO factoa;

--
-- Name: firmas_electronicas_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.firmas_electronicas_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.firmas_electronicas_id_seq OWNER TO factoa;

--
-- Name: firmas_electronicas_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.firmas_electronicas_id_seq OWNED BY public.firmas_electronicas.id;


--
-- Name: gastos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.gastos (
    id integer NOT NULL,
    fecha date NOT NULL,
    concepto character varying(300) NOT NULL,
    tipo_id integer,
    proveedor_id integer,
    proveedor_razon_social character varying(300) NOT NULL,
    proveedor_identificacion character varying(20) NOT NULL,
    documento character varying(30) NOT NULL,
    fecha_documento date,
    autorizacion_proveedor character varying(60),
    subtotal numeric(14,6) NOT NULL,
    iva numeric(14,6) NOT NULL,
    total numeric(14,6) NOT NULL,
    codigo_iva character varying(2) NOT NULL,
    estado_pago character varying(20) NOT NULL,
    observacion text,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.gastos OWNER TO factoa;

--
-- Name: gastos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.gastos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.gastos_id_seq OWNER TO factoa;

--
-- Name: gastos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.gastos_id_seq OWNED BY public.gastos.id;


--
-- Name: guias_remision; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.guias_remision (
    id integer NOT NULL,
    clave_acceso character varying(49),
    numero character varying(20) NOT NULL,
    establecimiento character varying(3) NOT NULL,
    punto_emision character varying(3) NOT NULL,
    secuencial integer NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date,
    motivo_traslado character varying(300) NOT NULL,
    ruta character varying(300),
    tipo_transporte character varying(20) NOT NULL,
    documento_aduanero character varying(50),
    transportista_id integer,
    transportista_razon_social character varying(300) NOT NULL,
    transportista_identificacion character varying(20) NOT NULL,
    placa character varying(20) NOT NULL,
    provincia_partida character varying(100),
    canton_partida character varying(100),
    direccion_partida character varying(300) NOT NULL,
    provincia_llegada character varying(100),
    canton_llegada character varying(100),
    direccion_llegada character varying(300) NOT NULL,
    estado_sri character varying(30) NOT NULL,
    numero_autorizacion character varying(100),
    fecha_autorizacion character varying(50),
    xml_firmado text,
    mensajes_sri text,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.guias_remision OWNER TO factoa;

--
-- Name: guias_remision_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.guias_remision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.guias_remision_id_seq OWNER TO factoa;

--
-- Name: guias_remision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.guias_remision_id_seq OWNED BY public.guias_remision.id;


--
-- Name: items_guia_remision; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.items_guia_remision (
    id integer NOT NULL,
    guia_id integer NOT NULL,
    codigo character varying(50) NOT NULL,
    descripcion character varying(300) NOT NULL,
    cantidad numeric(14,6) NOT NULL
);


ALTER TABLE public.items_guia_remision OWNER TO factoa;

--
-- Name: items_guia_remision_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.items_guia_remision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.items_guia_remision_id_seq OWNER TO factoa;

--
-- Name: items_guia_remision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.items_guia_remision_id_seq OWNED BY public.items_guia_remision.id;


--
-- Name: lineas_recurrentes; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.lineas_recurrentes (
    id integer NOT NULL,
    plantilla_id integer NOT NULL,
    codigo_principal character varying(50) NOT NULL,
    descripcion character varying(300) NOT NULL,
    cantidad numeric(14,6) NOT NULL,
    precio_unitario numeric(14,6) NOT NULL,
    descuento_porcentaje numeric(14,6) NOT NULL,
    codigo_iva character varying(2) NOT NULL
);


ALTER TABLE public.lineas_recurrentes OWNER TO factoa;

--
-- Name: lineas_recurrentes_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.lineas_recurrentes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.lineas_recurrentes_id_seq OWNER TO factoa;

--
-- Name: lineas_recurrentes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.lineas_recurrentes_id_seq OWNED BY public.lineas_recurrentes.id;


--
-- Name: listas_auxiliares; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.listas_auxiliares (
    id integer NOT NULL,
    tipo character varying(20) NOT NULL,
    nombre character varying(200) NOT NULL,
    detalle character varying(300),
    estado character varying(20) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.listas_auxiliares OWNER TO factoa;

--
-- Name: listas_auxiliares_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.listas_auxiliares_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.listas_auxiliares_id_seq OWNER TO factoa;

--
-- Name: listas_auxiliares_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.listas_auxiliares_id_seq OWNED BY public.listas_auxiliares.id;


--
-- Name: plantillas_recurrentes; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.plantillas_recurrentes (
    id integer NOT NULL,
    nombre character varying(200) NOT NULL,
    receptor_id integer,
    receptor_razon_social character varying(300) NOT NULL,
    periodicidad character varying(20) NOT NULL,
    proxima_emision date NOT NULL,
    ultima_emision date,
    hasta date,
    establecimiento character varying(3) NOT NULL,
    punto_emision character varying(3) NOT NULL,
    forma_pago character varying(2) NOT NULL,
    total numeric(14,6) NOT NULL,
    emitidas integer NOT NULL,
    activa boolean NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.plantillas_recurrentes OWNER TO factoa;

--
-- Name: plantillas_recurrentes_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.plantillas_recurrentes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.plantillas_recurrentes_id_seq OWNER TO factoa;

--
-- Name: plantillas_recurrentes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.plantillas_recurrentes_id_seq OWNED BY public.plantillas_recurrentes.id;


--
-- Name: puntos_emision; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.puntos_emision (
    id integer NOT NULL,
    establecimiento_id integer NOT NULL,
    codigo character varying(3) NOT NULL,
    nombre character varying(200) NOT NULL,
    secuencial_factura integer NOT NULL
);


ALTER TABLE public.puntos_emision OWNER TO factoa;

--
-- Name: puntos_emision_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.puntos_emision_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.puntos_emision_id_seq OWNER TO factoa;

--
-- Name: puntos_emision_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.puntos_emision_id_seq OWNED BY public.puntos_emision.id;


--
-- Name: receptores; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.receptores (
    id integer NOT NULL,
    tipo_identificacion character varying(50) NOT NULL,
    identificacion character varying(20) NOT NULL,
    razon_social character varying(300) NOT NULL,
    nombre_comercial character varying(300),
    tipo_persona character varying(20) NOT NULL,
    rol character varying(20) NOT NULL,
    correo character varying(200),
    correo2 character varying(200),
    telefono1 character varying(50),
    telefono2 character varying(50),
    direccion character varying(300) NOT NULL,
    provincia character varying(100),
    canton character varying(100),
    metodo_cancelacion character varying(20) NOT NULL,
    vendedor character varying(120),
    lista_precio character varying(20) NOT NULL,
    zona character varying(120),
    descuento numeric(14,6) NOT NULL,
    credito_maximo numeric(14,6) NOT NULL,
    estado character varying(20) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.receptores OWNER TO factoa;

--
-- Name: receptores_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.receptores_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.receptores_id_seq OWNER TO factoa;

--
-- Name: receptores_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.receptores_id_seq OWNED BY public.receptores.id;


--
-- Name: recibos; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.recibos (
    id integer NOT NULL,
    numero character varying(20) NOT NULL,
    fecha date NOT NULL,
    cuota_id integer,
    comprobante_id integer,
    receptor_razon_social character varying(300) NOT NULL,
    monto numeric(14,6) NOT NULL,
    forma_pago character varying(30) NOT NULL,
    cuenta_id integer,
    referencia character varying(60),
    estado character varying(20) NOT NULL,
    observacion text,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.recibos OWNER TO factoa;

--
-- Name: recibos_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.recibos_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.recibos_id_seq OWNER TO factoa;

--
-- Name: recibos_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.recibos_id_seq OWNED BY public.recibos.id;


--
-- Name: retenciones; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.retenciones (
    id integer NOT NULL,
    clave_acceso character varying(49),
    numero character varying(20) NOT NULL,
    establecimiento character varying(3) NOT NULL,
    punto_emision character varying(3) NOT NULL,
    secuencial integer NOT NULL,
    fecha_emision date NOT NULL,
    periodo_fiscal character varying(7) NOT NULL,
    sujeto_id integer,
    sujeto_razon_social character varying(300) NOT NULL,
    sujeto_identificacion character varying(20) NOT NULL,
    sujeto_tipo_identificacion character varying(30) NOT NULL,
    cod_doc_sustento character varying(2) NOT NULL,
    num_doc_sustento character varying(20) NOT NULL,
    fecha_doc_sustento date,
    total_retenido numeric(14,6) NOT NULL,
    estado_sri character varying(30) NOT NULL,
    numero_autorizacion character varying(100),
    fecha_autorizacion character varying(50),
    xml_firmado text,
    mensajes_sri text,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.retenciones OWNER TO factoa;

--
-- Name: retenciones_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.retenciones_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.retenciones_id_seq OWNER TO factoa;

--
-- Name: retenciones_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.retenciones_id_seq OWNED BY public.retenciones.id;


--
-- Name: secuenciales_documento; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.secuenciales_documento (
    id integer NOT NULL,
    punto_emision_id integer NOT NULL,
    tipo character varying(30) NOT NULL,
    siguiente integer NOT NULL
);


ALTER TABLE public.secuenciales_documento OWNER TO factoa;

--
-- Name: secuenciales_documento_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.secuenciales_documento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.secuenciales_documento_id_seq OWNER TO factoa;

--
-- Name: secuenciales_documento_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.secuenciales_documento_id_seq OWNED BY public.secuenciales_documento.id;


--
-- Name: tipos_gasto; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.tipos_gasto (
    id integer NOT NULL,
    nombre character varying(120) NOT NULL,
    descripcion character varying(300),
    deducible boolean NOT NULL,
    estado character varying(20) NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.tipos_gasto OWNER TO factoa;

--
-- Name: tipos_gasto_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.tipos_gasto_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.tipos_gasto_id_seq OWNER TO factoa;

--
-- Name: tipos_gasto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.tipos_gasto_id_seq OWNED BY public.tipos_gasto.id;


--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: factoa
--

CREATE TABLE public.usuarios (
    id integer NOT NULL,
    correo character varying(200) NOT NULL,
    nombre character varying(200) NOT NULL,
    contrasena_hash character varying(255) NOT NULL,
    rol character varying(30) NOT NULL,
    activo boolean NOT NULL,
    creado_en timestamp with time zone NOT NULL
);


ALTER TABLE public.usuarios OWNER TO factoa;

--
-- Name: usuarios_id_seq; Type: SEQUENCE; Schema: public; Owner: factoa
--

CREATE SEQUENCE public.usuarios_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuarios_id_seq OWNER TO factoa;

--
-- Name: usuarios_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: factoa
--

ALTER SEQUENCE public.usuarios_id_seq OWNED BY public.usuarios.id;


--
-- Name: anticipos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.anticipos ALTER COLUMN id SET DEFAULT nextval('public.anticipos_id_seq'::regclass);


--
-- Name: articulos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.articulos ALTER COLUMN id SET DEFAULT nextval('public.articulos_id_seq'::regclass);


--
-- Name: comprobantes id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.comprobantes ALTER COLUMN id SET DEFAULT nextval('public.comprobantes_id_seq'::regclass);


--
-- Name: cuentas_bancarias id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuentas_bancarias ALTER COLUMN id SET DEFAULT nextval('public.cuentas_bancarias_id_seq'::regclass);


--
-- Name: cuotas id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuotas ALTER COLUMN id SET DEFAULT nextval('public.cuotas_id_seq'::regclass);


--
-- Name: detalles_comprobante id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_comprobante ALTER COLUMN id SET DEFAULT nextval('public.detalles_comprobante_id_seq'::regclass);


--
-- Name: detalles_retencion id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_retencion ALTER COLUMN id SET DEFAULT nextval('public.detalles_retencion_id_seq'::regclass);


--
-- Name: egresos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.egresos ALTER COLUMN id SET DEFAULT nextval('public.egresos_id_seq'::regclass);


--
-- Name: empresas id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.empresas ALTER COLUMN id SET DEFAULT nextval('public.empresas_id_seq'::regclass);


--
-- Name: establecimientos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.establecimientos ALTER COLUMN id SET DEFAULT nextval('public.establecimientos_id_seq'::regclass);


--
-- Name: firmas_electronicas id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.firmas_electronicas ALTER COLUMN id SET DEFAULT nextval('public.firmas_electronicas_id_seq'::regclass);


--
-- Name: gastos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.gastos ALTER COLUMN id SET DEFAULT nextval('public.gastos_id_seq'::regclass);


--
-- Name: guias_remision id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.guias_remision ALTER COLUMN id SET DEFAULT nextval('public.guias_remision_id_seq'::regclass);


--
-- Name: items_guia_remision id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.items_guia_remision ALTER COLUMN id SET DEFAULT nextval('public.items_guia_remision_id_seq'::regclass);


--
-- Name: lineas_recurrentes id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.lineas_recurrentes ALTER COLUMN id SET DEFAULT nextval('public.lineas_recurrentes_id_seq'::regclass);


--
-- Name: listas_auxiliares id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.listas_auxiliares ALTER COLUMN id SET DEFAULT nextval('public.listas_auxiliares_id_seq'::regclass);


--
-- Name: plantillas_recurrentes id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.plantillas_recurrentes ALTER COLUMN id SET DEFAULT nextval('public.plantillas_recurrentes_id_seq'::regclass);


--
-- Name: puntos_emision id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.puntos_emision ALTER COLUMN id SET DEFAULT nextval('public.puntos_emision_id_seq'::regclass);


--
-- Name: receptores id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.receptores ALTER COLUMN id SET DEFAULT nextval('public.receptores_id_seq'::regclass);


--
-- Name: recibos id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.recibos ALTER COLUMN id SET DEFAULT nextval('public.recibos_id_seq'::regclass);


--
-- Name: retenciones id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.retenciones ALTER COLUMN id SET DEFAULT nextval('public.retenciones_id_seq'::regclass);


--
-- Name: secuenciales_documento id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.secuenciales_documento ALTER COLUMN id SET DEFAULT nextval('public.secuenciales_documento_id_seq'::regclass);


--
-- Name: tipos_gasto id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.tipos_gasto ALTER COLUMN id SET DEFAULT nextval('public.tipos_gasto_id_seq'::regclass);


--
-- Name: usuarios id; Type: DEFAULT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.usuarios ALTER COLUMN id SET DEFAULT nextval('public.usuarios_id_seq'::regclass);


--
-- Data for Name: anticipos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.anticipos (id, fecha, tipo, receptor_id, receptor_razon_social, detalle, monto, facturado, forma_pago, estado, creado_en) FROM stdin;
1	2026-08-01	ARD	8	CARLOS VILLACÍS	Anticipo proyecto fase 2	2500.000000	1200.000000	Transferencia	Parcial	2026-08-10 23:08:51.837012-04
2	2026-08-01	ARD	8	CARLOS VILLACÍS	Abono inicial contrato	900.000000	0.000000	Transferencia	Pendiente	2026-08-10 23:08:52.086178-04
\.


--
-- Data for Name: articulos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.articulos (id, codigo, codigo_auxiliar, nombre, detalle, tipo, categoria, marca, unidad, bodega, ubicacion, codigo_iva, codigo_ice, costo, precio, stock, stock_minimo, punto_reorden, stock_maximo, estado, creado_en) FROM stdin;
1	PROD-001	\N	Laptop Dell XPS 13	\N	Producto	Tecnología	\N	Unidad	\N	\N	4	\N	950.000000	1200.000000	15.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
2	SERV-001	\N	Mantenimiento Preventivo	\N	Servicio	Soporte	\N	Servicio	\N	\N	4	\N	20.000000	45.000000	\N	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
3	PROD-002	\N	Mouse Inalámbrico Logitech	\N	Producto	Tecnología	\N	Unidad	\N	\N	4	\N	16.000000	25.500000	40.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
4	PROD-003	\N	Pan común - funda 500g	\N	Producto	Alimentos	\N	Unidad	\N	\N	0	\N	1.200000	1.850000	120.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
5	SERV-002	\N	Consultoría contable mensual	\N	Servicio	Profesional	\N	Servicio	\N	\N	4	\N	90.000000	180.000000	\N	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
6	PROD-004	\N	Teclado mecánico retroiluminado	\N	Producto	Tecnología	\N	Unidad	\N	\N	4	\N	42.000000	62.900000	18.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
7	PROD-005	\N	Monitor LED 24"	\N	Producto	Tecnología	\N	Unidad	\N	\N	4	\N	140.000000	189.000000	7.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
8	PROD-006	\N	Resma de papel bond A4	\N	Producto	Oficina	\N	Unidad	\N	\N	4	\N	3.400000	4.750000	240.000000	5.000000	10.000000	200.000000	Activo	2026-08-09 22:51:47.65625-04
\.


--
-- Data for Name: comprobantes; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.comprobantes (id, tipo, clave_acceso, numero, establecimiento, punto_emision, secuencial, fecha_emision, receptor_id, receptor_razon_social, receptor_identificacion, total_sin_impuestos, total_descuento, total_iva, importe_total, metodo, forma_pago, estado_sri, estado_pago, numero_autorizacion, fecha_autorizacion, mensajes_sri, xml_firmado, validez_dias, cod_doc_modificado, num_doc_modificado, fecha_doc_modificado, motivo, creado_en) FROM stdin;
1	Factura	\N	001-001-000000135	001	001	135	2026-06-12	8	CARLOS VILLACÍS	0604567891	2401.850000	0.000000	360.000000	2761.850000	Contado	01	Autorizado	Pagado	DEMO0000000001	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:49.75442-04
2	Factura	\N	001-001-000000136	001	001	136	2026-06-25	3	CONSUMIDOR FINAL	9999999999999	76.500000	0.000000	11.480000	87.980000	Crédito	01	Autorizado	Pagado	DEMO0000000002	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:50.008915-04
3	Factura	\N	001-001-000000137	001	001	137	2026-07-08	8	CARLOS VILLACÍS	0604567891	818.000000	0.000000	122.700000	940.700000	Contado	01	Autorizado	Por Cobrar	DEMO0000000003	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:50.174418-04
4	Factura	\N	001-001-000000138	001	001	138	2026-07-19	1	CORPORACIÓN FAVORITA C.A.	1790016919001	1200.000000	0.000000	180.000000	1380.000000	Crédito	01	Autorizado	Pagado	DEMO0000000004	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:50.426442-04
5	Factura	\N	001-001-000000139	001	001	139	2026-07-28	3	CONSUMIDOR FINAL	9999999999999	189.500000	0.000000	28.430000	217.930000	Contado	01	Autorizado	Pagado	DEMO0000000005	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:50.603924-04
6	Factura	\N	001-001-000000140	001	001	140	2026-08-03	8	CARLOS VILLACÍS	0604567891	9.250000	0.000000	0.000000	9.250000	Crédito	01	Autorizado	Por Cobrar	DEMO0000000006	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:50.864924-04
7	Factura	\N	001-001-000000141	001	001	141	2026-08-07	1	CORPORACIÓN FAVORITA C.A.	1790016919001	1560.000000	0.000000	234.000000	1794.000000	Crédito	01	Autorizado	Pagado	DEMO0000000007	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:51.125599-04
8	Factura	\N	001-001-000000142	001	001	142	2026-08-09	3	CONSUMIDOR FINAL	9999999999999	189.000000	0.000000	28.350000	217.350000	Crédito	01	Autorizado	Parcial	DEMO0000000008	\N	\N	\N	\N	01	\N	\N	\N	2026-08-09 22:56:51.371881-04
9	Cotización	\N	001-001-000000001	001	001	1	2026-08-09	8	CARLOS VILLACÍS	0604567891	102.000000	0.000000	15.300000	117.300000	Contado	01	Pendiente	Por Cobrar	\N	\N	\N	\N	15	01	\N	\N	\N	2026-08-09 22:56:52.555457-04
10	Factura	\N	001-001-000000143	001	001	143	2026-09-01	8	CARLOS VILLACÍS	0604567891	800.000000	0.000000	120.000000	920.000000	Contado	01	Borrador	Por Cobrar	\N	\N	\N	\N	\N	\N	\N	\N	\N	2026-08-12 14:40:45.004715-04
\.


--
-- Data for Name: cuentas_bancarias; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.cuentas_bancarias (id, empresa_id, banco, tipo, numero, titular, activa) FROM stdin;
\.


--
-- Data for Name: cuotas; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.cuotas (id, comprobante_id, numero, vence, monto, cobrado, creado_en) FROM stdin;
1	8	1	2026-09-01	72.450000	72.450000	2026-08-11 01:47:19.207773-04
2	8	2	2026-10-01	72.450000	10.000000	2026-08-11 01:47:19.207773-04
3	8	3	2026-10-31	72.450000	0.000000	2026-08-11 01:47:19.207773-04
\.


--
-- Data for Name: detalles_comprobante; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.detalles_comprobante (id, comprobante_id, codigo_principal, codigo_auxiliar, descripcion, cantidad, precio_unitario, descuento_porcentaje, descuento, codigo_iva, base_imponible, valor_iva, total) FROM stdin;
1	1	PROD-001	\N	Laptop Dell XPS 13	2.000000	1200.000000	0.000000	0.000000	4	2400.000000	360.000000	2760.000000
2	1	PROD-003	\N	Pan común - funda 500g	1.000000	1.850000	0.000000	0.000000	0	1.850000	0.000000	1.850000
3	2	PROD-002	\N	Mouse Inalámbrico Logitech	3.000000	25.500000	0.000000	0.000000	4	76.500000	11.480000	87.980000
4	3	PROD-004	\N	Teclado mecánico retroiluminado	10.000000	62.900000	0.000000	0.000000	4	629.000000	94.350000	723.350000
5	3	PROD-005	\N	Monitor LED 24"	1.000000	189.000000	0.000000	0.000000	4	189.000000	28.350000	217.350000
6	4	PROD-001	\N	Laptop Dell XPS 13	1.000000	1200.000000	0.000000	0.000000	4	1200.000000	180.000000	1380.000000
7	5	PROD-006	\N	Resma de papel bond A4	2.000000	4.750000	0.000000	0.000000	4	9.500000	1.430000	10.930000
8	5	SERV-001	\N	Mantenimiento Preventivo	4.000000	45.000000	0.000000	0.000000	4	180.000000	27.000000	207.000000
9	6	PROD-003	\N	Pan común - funda 500g	5.000000	1.850000	0.000000	0.000000	0	9.250000	0.000000	9.250000
10	7	PROD-001	\N	Laptop Dell XPS 13	1.000000	1200.000000	0.000000	0.000000	4	1200.000000	180.000000	1380.000000
11	7	SERV-002	\N	Consultoría contable mensual	2.000000	180.000000	0.000000	0.000000	4	360.000000	54.000000	414.000000
12	8	PROD-005	\N	Monitor LED 24"	1.000000	189.000000	0.000000	0.000000	4	189.000000	28.350000	217.350000
13	9	PROD-002	\N	Mouse Inalámbrico Logitech	4.000000	25.500000	0.000000	0.000000	4	102.000000	15.300000	117.300000
14	10	ARR-001	\N	Arriendo mensual	1.000000	800.000000	0.000000	0.000000	4	800.000000	120.000000	920.000000
\.


--
-- Data for Name: detalles_retencion; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.detalles_retencion (id, retencion_id, codigo_impuesto, codigo_retencion, base_imponible, porcentaje_retener, valor_retenido) FROM stdin;
1	1	1	312	1200.000000	2.000000	24.000000
2	1	2	1	180.000000	30.000000	54.000000
\.


--
-- Data for Name: egresos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.egresos (id, fecha, concepto, beneficiario, monto, forma_pago, cuenta_id, referencia, gasto_id, estado, observacion, creado_en) FROM stdin;
1	2026-08-08	Pago planilla de luz	IMPORTADORA AUSTRAL S.A.	138.000000	Transferencia	\N	TRF-88213	1	Registrado	\N	2026-08-10 23:08:51.471785-04
2	2026-08-09	Abono arriendo	Inmobiliaria Quito	500.000000	Cheque	\N	CH-0091	2	Registrado	\N	2026-08-10 23:08:51.673184-04
\.


--
-- Data for Name: empresas; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.empresas (id, ruc, razon_social, nombre_comercial, direccion_matriz, provincia, canton, telefono, correo, regimen, obligado_contabilidad, contribuyente_especial, agente_retencion, contribuyente_rimpe, ambiente) FROM stdin;
1	1790016919001	MI EMPRESA DEMO S.A.	DEMO	Av. Amazonas N21-147 y Roca, Quito	Pichincha	Quito	022345678	facturacion@miempresa.ec	Régimen General	t	\N	1	\N	1
\.


--
-- Data for Name: establecimientos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.establecimientos (id, empresa_id, codigo, nombre, direccion) FROM stdin;
1	1	001	Matriz	Av. Amazonas N21-147 y Roca, Quito
2	1	002	Sucursal Norte	Av. Eloy Alfaro N45-120, Quito
\.


--
-- Data for Name: firmas_electronicas; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.firmas_electronicas (id, empresa_id, nombre_archivo, contenido, contrasena_cifrada, propietario, emisor, numero_serie, valida_desde, valida_hasta, activa, subida_en) FROM stdin;
1	1	pruebas.p12	\\x30820afe02010330820ab406092a864886f70d010701a0820aa504820aa130820a9d308204ea06092a864886f70d010706a08204db308204d7020100308204d006092a864886f70d010701305f06092a864886f70d01050d3052303106092a864886f70d01050c30240410ee00388c863f91eaf19a2a9e11968f1302024e20300c06082a864886f70d02090500301d060960864801650304012a0410ddb4e3165d930d374f018c2bca233161808204600564dda140ea409e9fdd8829e2eb458d1bf07479ec265414c83432ef350177a077acc7be246af950abb40a136b9691e2a61eae9bfa8bf2903c7b45abed5097b020af2ecd152c61f294a2acbee8292a0dc41fdf627aeafea9a88946451ffe83519bdab6d323954d2460c7b772cbd4637a4af7d4ae7ba55e566d5f780c640e96b8ad2a839b140d12ae5a3036018b1975dad957758e9a7fa129f12eab287e5ba3487e49d0b6d3052d58ff8b297fc295f15aba3cf5c972a3091d77a421e2578535aa709ccbd79f2be96008cfc5c1b40160105a68c6d6698bd5087ff4795162e78187f8742d0b76e92504e39058604e212e80cbfe45ef872ca775e80c84a739d5317d288724a19c5b9a6b012063ba9d88b140d4854e3ec7b53a6f99fb9ff1730672cdf033a9a1ec60155e9a9d9261a2c9f17264d3defdc5ba8b779882ae217dca1b8540dd7b9167800e984e83f61ccc4ef29cf0d2542386d0714a09f848c08c0f31427d7fd62dcf791a1a51ca96eef244b4e7cc8d04dacbea6fe73e5d289bf5cef5f87f22f79376aeca5fa3ef46403151e1e0870b0e5f785e558f1abe03ad67b59903a539d09e1402ee42a67a268d18bc4d0cf35d20d28ba45a8185618b5444bee00034442900f401214f2acef03b43424861dcff9066bf2175c18c976cab167ae039857699219d03918e45d08a7a02039d4a90b057e06efeec54281612a34566cf97a03730a5501aba3f425069adc581f2f70d7e5e289181b888d96240cbc164f2788597cd6d7da7d6c1611d91074fb583682057308a648a4e9468c4d86be5c788919d9ce6f8b22fd703b70f3552eb054055fb7d669ad89f44dfadf76db86a3e50666ec9763cb4e089fa29e49aa3f82efadb3cf916efd303d3f3d7b1f49db5aaad9ddf043bb1be7e7f261b952087150b0186c1e08e9c227d44c2e0d70656a33aebd23583a586cc8f1c71fa5eb7338c9e7245dacf804169006c2882d65228cbb1553086d63406384fc47c452a1b9d0df0476b0ee87aaa7a0186967d4898f863343c2692d5d3b8c2470f5ac4da7f597a20983afb9816645ed5236fe292798b24a2a4cd8fa6644a544e40e6a2542bc99c0e9a98e41209fcd9d04b9294a43a5c19e5869a0392546ccc8bf27d737131395a3599cb612b29d13fa52fe888eedf25d873ba7989b3074e516d53d1dad510c07b9bc3c4eb814adc6920f3c80178802d762d9c7d66ad5e7e3d1ceacb7bd982ba1b8e85d1892c86ae7f39e57c91e336073e8512692256b5c200b0adce433c5ed82357ea05ac9a02c1d86391ab802874cf12b3425455b3c56df2d30cd092f73ed841d6aa4a99eaa9a29df9742b3a655c8e209edf4a159982b268ec25105c93b33b020b6f8c4843565425844b7e0c6beb7c6abfdc32c73398e985b4f825ca4543cc311a779c985f0205c172ed88408d85a22e51747e4f5d6674b0c784faf860fe272ecb44cc26c364c1a63ff6f59309e652bcd2e4bcfa3c5e7f11ce89b2487370937cf1d1dd5a686891909d6897fc62b5fc60bb735d151b244fbb049c96fd1888b45916f448d9823b76ec920d5f2c6cfb48df94891a308205ab06092a864886f70d010701a082059c048205983082059430820590060b2a864886f70d010c0a0102a082053930820535305f06092a864886f70d01050d3052303106092a864886f70d01050c302404109c8587578b1d2f74d42dc38af58d2cf202024e20300c06082a864886f70d02090500301d060960864801650304012a0410f5ee587d1b47d2c7e48915ee2f5d55dc048204d071fd7110b0890b70e9e4af509cd9e9ab7a39c527563db3dc2e575448232c1f5365f107105e0d6c582c4dcc03f8a4462cc90656541978fefc753484667d7fabb4246cfd66917365baeb20e8842f7e464c70259359eda2b800c4929b41cc44c6e123177e8a2df1426151159e578e5f05e8094401e03db24403eff2e29c16309a35ac9d98b89bbf1c9f4766d58c193090e4b3e1931a635873723e09c320336fccddbf8fb0557e65b10b17e0d902c047d300af6a2f8bb3ff10b0781bf1fb113271543e4d5050f5cf41b7710d974e43938cfc2ee3bbc9cbc7cddf5eb4e39042a075e1e707c07db14f7417999efc13f43037637e0cb7e09b6027ae372a86e556d45b99fe2522edf1fd9659de2b106507673f497454d2d1e83ba11a0e6eb6584f83a0955cf5267b7855fd6a4db44367b219f0e279a59393787c7ec3d2c4da4fcfde1f720bdd4cab2b3333756dd36d19db1e279245d88200c049898ac2a6af0c50c1863f24647e92ad7868865928742a1b3290725dd9c6047cb1738befc37092797b155f3071db2a3e0fe729bf00e0fa8a371b512abdeca56868d242ce4b051fcc9b02e7b15b9bf16f8de198f857393b741bd4865bc846be51b1636a46b3a507b4d3d4012a293ad7970280e0ecb1d41bbbfe472ae257fb5347b4db49bb0dbc8fbddfd093e36871d6e77a627cdb3c8e6e6b2fe0ae2a41ff9575c9a8cd9362f5698e9bb087f3612e316736426e31e37f57d815d147d1cf6315f760d8c460a11bb4435e162d7b0b9f3499c069b940504e1b9e6ffaca81657dab29d9dde01b29ba0e0c3438ed9f589bb5af34346e55d1f3ff0c4e6d092185e4433119183c8f73b6a40913296defec9eba59721763bfb23d76acc91b2da4c254f26e2ded30e319377705c1e7dd98e30d789efe4409aa779bce58ad4a8ed1b98c9cbcb01ca4495976fc082310e17db163c00624f55738d6fe8f5797068d1db352e480d80c7f677430dcbed894d73040dce9b1795cef3752e191ac42d732fcbd91c0a87ee31e686b99b1a27892c9a365de726eda63b3f945ac70da9432933778704231be1187cc95e96ce79850125130ce81dc58cad701cadb19311f2869db5d9b747bb5116ff137b8999d37b24e1cb6cc1c1e0d1d7e2686e6c0048cf364f991cbacc652d142f33959445be3e1156d0e2f73bd1a4c3c3ba9ab5e35e267a1f74595f4702bd985bfcd7cbbc719de29b5b257d77b5466b2b9d70fc4bab69d185c29ff67567bb338fb9e28d8e59206031d43543d4c447e01846047b7499234ad099df579b9584713c78410eeb4c6cfc16b6d5f7dad902f2e77d6158ea1a5586fa70c263f0aea780c290cfe658a5be39921db124678110923615cc5afc2e5b2e59cfeeb48635b6a8a9927ca30b80b5d080833c6f28bad1f2ff37bd2f6de4059e267dff50114db015a2e764b297ca7bcd46b016364969ef521dd1b9e2270419d78fc35c819639f1fab3fdcbb5768f916c57df05380b5763764d814587a926a9e42274ab928a78822ada799d7bade4dfb517ad7b3b892c6e02e0ef197ce45595651c75aa121f998990a3936315eac0550ad2481a8d2bd6bbd47e181424157d22e04a3ddd3d4878fafad867f23a92d50243c4626bb5b3b074ac7675e8f6e6286f8a22f79e7503c1ccf4314ad26bd89dfd03a5245345e4698906007667d9a03112457f7c5f157c15ca915995114322e67ade476295e3277888d8f1ce3695a81b21b3d3144301d06092a864886f70d01091431101e0e0070007200750065006200610073302306092a864886f70d01091531160414ca2bce5dfde0de6652a68ad77fe12023126ac08830413031300d0609608648016503040201050004207377db45e8267364ca268056deda59d02df300fd835ce47d225f15303baaf067040823c3d41e17f6ddac02020800	gAAAAABqeQWxiv58in48uxLb5b_9Q_ZigyJvGetbKQ1O_4tJL9fGmkUiECpNlJiYrE87NilcguJbxa0gE9QlBbJNpqv9qCuxyw==	2.5.4.5=1790016919001,CN=MI EMPRESA DEMO S.A.,O=CERTIFICADO DE PRUEBAS - NO VALIDO,L=Quito,ST=Pichincha,C=EC	2.5.4.5=1790016919001,CN=MI EMPRESA DEMO S.A.,O=CERTIFICADO DE PRUEBAS - NO VALIDO,L=Quito,ST=Pichincha,C=EC	80267587989926569119963085620477830961403284899	2026-08-08	2028-08-08	t	2026-08-09 22:56:49.383499-04
\.


--
-- Data for Name: gastos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.gastos (id, fecha, concepto, tipo_id, proveedor_id, proveedor_razon_social, proveedor_identificacion, documento, fecha_documento, autorizacion_proveedor, subtotal, iva, total, codigo_iva, estado_pago, observacion, creado_en) FROM stdin;
1	2026-08-02	Planilla de luz agosto	1	7	IMPORTADORA AUSTRAL S.A.	0190001946001	001-001-000000500	2026-08-02	\N	120.000000	18.000000	138.000000	4	Pagado	\N	2026-08-10 23:08:50.795794-04
2	2026-08-03	Arriendo local comercial	2	7	IMPORTADORA AUSTRAL S.A.	0190001946001	001-001-000000501	2026-08-03	\N	800.000000	120.000000	920.000000	4	Parcial	\N	2026-08-10 23:08:50.9173-04
3	2026-08-06	Resmas de papel y tóner	3	7	IMPORTADORA AUSTRAL S.A.	0190001946001	001-001-000000502	2026-08-06	\N	95.500000	14.330000	109.830000	4	Por Pagar	\N	2026-08-10 23:08:51.027224-04
4	2026-07-02	Planilla de luz julio	1	7	IMPORTADORA AUSTRAL S.A.	0190001946001	001-001-000000503	2026-07-02	\N	110.000000	16.500000	126.500000	4	Por Pagar	\N	2026-08-10 23:08:51.213551-04
5	2026-07-03	Arriendo local comercial	2	7	IMPORTADORA AUSTRAL S.A.	0190001946001	001-001-000000504	2026-07-03	\N	800.000000	120.000000	920.000000	4	Por Pagar	\N	2026-08-10 23:08:51.328947-04
\.


--
-- Data for Name: guias_remision; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.guias_remision (id, clave_acceso, numero, establecimiento, punto_emision, secuencial, fecha_inicio, fecha_fin, motivo_traslado, ruta, tipo_transporte, documento_aduanero, transportista_id, transportista_razon_social, transportista_identificacion, placa, provincia_partida, canton_partida, direccion_partida, provincia_llegada, canton_llegada, direccion_llegada, estado_sri, numero_autorizacion, fecha_autorizacion, xml_firmado, mensajes_sri, creado_en) FROM stdin;
1	\N	001-001-000000001	001	001	1	2026-08-09	2026-08-10	Venta	\N	Privado	\N	5	TRANSPORTES ANDINOS CÍA. LTDA.	1791287541001	PBA1234	\N	\N	Bodega Norte, Quito	\N	\N	Km 14.5 vía Daule, Guayaquil	Autorizado	DEMO0000000001	\N	\N	\N	2026-08-09 22:56:51.727202-04
\.


--
-- Data for Name: items_guia_remision; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.items_guia_remision (id, guia_id, codigo, descripcion, cantidad) FROM stdin;
1	1	PROD-001	Laptop Dell XPS 13	2.000000
\.


--
-- Data for Name: lineas_recurrentes; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.lineas_recurrentes (id, plantilla_id, codigo_principal, descripcion, cantidad, precio_unitario, descuento_porcentaje, codigo_iva) FROM stdin;
1	1	ARR-001	Arriendo mensual	1.000000	800.000000	0.000000	4
\.


--
-- Data for Name: listas_auxiliares; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.listas_auxiliares (id, tipo, nombre, detalle, estado, creado_en) FROM stdin;
1	zona	Zona norte	\N	Activo	2026-08-11 03:55:12.379531-04
2	vendedor	Vendedor norte	\N	Activo	2026-08-11 03:55:12.662117-04
3	leyenda	Leyenda norte	\N	Activo	2026-08-11 03:55:12.852482-04
\.


--
-- Data for Name: plantillas_recurrentes; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.plantillas_recurrentes (id, nombre, receptor_id, receptor_razon_social, periodicidad, proxima_emision, ultima_emision, hasta, establecimiento, punto_emision, forma_pago, total, emitidas, activa, creado_en) FROM stdin;
1	Arriendo mensual local	8	CARLOS VILLACÍS	Mensual	2026-10-01	2026-09-01	\N	001	001	01	920.000000	1	t	2026-08-10 23:08:52.194254-04
\.


--
-- Data for Name: puntos_emision; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.puntos_emision (id, establecimiento_id, codigo, nombre, secuencial_factura) FROM stdin;
1	1	001	Caja principal	144
2	1	002	Ventas en línea	42
3	2	001	Caja sucursal	8
\.


--
-- Data for Name: receptores; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.receptores (id, tipo_identificacion, identificacion, razon_social, nombre_comercial, tipo_persona, rol, correo, correo2, telefono1, telefono2, direccion, provincia, canton, metodo_cancelacion, vendedor, lista_precio, zona, descuento, credito_maximo, estado, creado_en) FROM stdin;
1	RUC	1790016919001	CORPORACIÓN FAVORITA C.A.	SUPERMAXI	Jurídica	Cliente	1790016919001@ejemplo.ec	\N	\N	\N	Av. General Enríquez S/N, Sangolquí	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
2	Cédula	0912345675	JUAN PÉREZ	TIENDA JUANITO	Natural	Cliente	0912345675@ejemplo.ec	\N	\N	\N	Av. 9 de Octubre 1234, Guayaquil	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
3	Consumidor Final	9999999999999	CONSUMIDOR FINAL	\N	Natural	Cliente	9999999999999@ejemplo.ec	\N	\N	\N	S/N	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
4	RUC	0992339411001	PLÁSTICOS DEL LITORAL PLASTLIT S.A.	PLASTLIT	Jurídica	Proveedor	0992339411001@ejemplo.ec	\N	\N	\N	Km 14.5 vía Daule, Guayaquil	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
5	RUC	1791287541001	TRANSPORTES ANDINOS CÍA. LTDA.	TRANSANDINOS	Jurídica	Transportista	1791287541001@ejemplo.ec	\N	\N	\N	Av. Maldonado S12-45, Quito	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
6	Cédula	1712345675	MARÍA ANDRADE	\N	Natural	Cliente	1712345675@ejemplo.ec	\N	\N	\N	Av. Shyris N34-120, Quito	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
7	RUC	0190001946001	IMPORTADORA AUSTRAL S.A.	AUSTRAL	Jurídica	Proveedor	0190001946001@ejemplo.ec	\N	\N	\N	Av. España 4-52, Cuenca	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
8	Cédula	0604567891	CARLOS VILLACÍS	FERRETERÍA EL TORNILLO	Natural	Cliente	0604567891@ejemplo.ec	\N	\N	\N	Av. Daniel León Borja 22-10, Riobamba	\N	\N	Contado	\N	PVP 1	\N	0.000000	0.000000	Activo	2026-08-09 22:51:47.663755-04
\.


--
-- Data for Name: recibos; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.recibos (id, numero, fecha, cuota_id, comprobante_id, receptor_razon_social, monto, forma_pago, cuenta_id, referencia, estado, observacion, creado_en) FROM stdin;
1	REC-000001	2026-08-10	1	8	CONSUMIDOR FINAL	72.450000	Transferencia	\N	TRF-77120	Registrado	\N	2026-08-11 01:47:19.420972-04
2	REC-000002	2026-08-10	2	8	CONSUMIDOR FINAL	10.000000	Efectivo	\N	\N	Registrado	\N	2026-08-11 01:47:19.690569-04
\.


--
-- Data for Name: retenciones; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.retenciones (id, clave_acceso, numero, establecimiento, punto_emision, secuencial, fecha_emision, periodo_fiscal, sujeto_id, sujeto_razon_social, sujeto_identificacion, sujeto_tipo_identificacion, cod_doc_sustento, num_doc_sustento, fecha_doc_sustento, total_retenido, estado_sri, numero_autorizacion, fecha_autorizacion, xml_firmado, mensajes_sri, creado_en) FROM stdin;
1	\N	001-001-000000001	001	001	1	2026-08-08	08/2026	7	IMPORTADORA AUSTRAL S.A.	0190001946001	RUC	01	001-001-000000456	2026-08-05	78.000000	Autorizado	DEMO0000000001	\N	\N	\N	2026-08-09 22:56:52.384457-04
\.


--
-- Data for Name: secuenciales_documento; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.secuenciales_documento (id, punto_emision_id, tipo, siguiente) FROM stdin;
1	1	Factura	144
2	1	Guía de Remisión	2
3	1	Retención	2
4	1	Cotización	2
\.


--
-- Data for Name: tipos_gasto; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.tipos_gasto (id, nombre, descripcion, deducible, estado, creado_en) FROM stdin;
1	Servicios básicos	\N	t	Activo	2026-08-10 23:08:50.280482-04
2	Arriendo	\N	t	Activo	2026-08-10 23:08:50.377509-04
3	Suministros de oficina	\N	t	Activo	2026-08-10 23:08:50.480383-04
4	Multas e intereses	\N	f	Activo	2026-08-10 23:08:50.574994-04
\.


--
-- Data for Name: usuarios; Type: TABLE DATA; Schema: public; Owner: factoa
--

COPY public.usuarios (id, correo, nombre, contrasena_hash, rol, activo, creado_en) FROM stdin;
1	demo@empresa.ec	Ana Salazar	pbkdf2_sha256$260000$DEauc7DA3yqecjWDrqepJA==$MnHiBMf0g80JTN2UaNkqYUUAccHU8kpkcIaIFsCmthM=	administrador	t	2026-08-09 22:56:04.222083-04
\.


--
-- Name: anticipos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.anticipos_id_seq', 2, true);


--
-- Name: articulos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.articulos_id_seq', 8, true);


--
-- Name: comprobantes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.comprobantes_id_seq', 10, true);


--
-- Name: cuentas_bancarias_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.cuentas_bancarias_id_seq', 1, false);


--
-- Name: cuotas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.cuotas_id_seq', 3, true);


--
-- Name: detalles_comprobante_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.detalles_comprobante_id_seq', 14, true);


--
-- Name: detalles_retencion_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.detalles_retencion_id_seq', 2, true);


--
-- Name: egresos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.egresos_id_seq', 2, true);


--
-- Name: empresas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.empresas_id_seq', 1, true);


--
-- Name: establecimientos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.establecimientos_id_seq', 2, true);


--
-- Name: firmas_electronicas_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.firmas_electronicas_id_seq', 1, true);


--
-- Name: gastos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.gastos_id_seq', 5, true);


--
-- Name: guias_remision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.guias_remision_id_seq', 1, true);


--
-- Name: items_guia_remision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.items_guia_remision_id_seq', 1, true);


--
-- Name: lineas_recurrentes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.lineas_recurrentes_id_seq', 1, true);


--
-- Name: listas_auxiliares_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.listas_auxiliares_id_seq', 3, true);


--
-- Name: plantillas_recurrentes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.plantillas_recurrentes_id_seq', 1, true);


--
-- Name: puntos_emision_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.puntos_emision_id_seq', 3, true);


--
-- Name: receptores_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.receptores_id_seq', 8, true);


--
-- Name: recibos_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.recibos_id_seq', 2, true);


--
-- Name: retenciones_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.retenciones_id_seq', 1, true);


--
-- Name: secuenciales_documento_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.secuenciales_documento_id_seq', 4, true);


--
-- Name: tipos_gasto_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.tipos_gasto_id_seq', 4, true);


--
-- Name: usuarios_id_seq; Type: SEQUENCE SET; Schema: public; Owner: factoa
--

SELECT pg_catalog.setval('public.usuarios_id_seq', 2, true);


--
-- Name: anticipos anticipos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.anticipos
    ADD CONSTRAINT anticipos_pkey PRIMARY KEY (id);


--
-- Name: articulos articulos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.articulos
    ADD CONSTRAINT articulos_pkey PRIMARY KEY (id);


--
-- Name: comprobantes comprobantes_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.comprobantes
    ADD CONSTRAINT comprobantes_pkey PRIMARY KEY (id);


--
-- Name: cuentas_bancarias cuentas_bancarias_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuentas_bancarias
    ADD CONSTRAINT cuentas_bancarias_pkey PRIMARY KEY (id);


--
-- Name: cuotas cuotas_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuotas
    ADD CONSTRAINT cuotas_pkey PRIMARY KEY (id);


--
-- Name: detalles_comprobante detalles_comprobante_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_comprobante
    ADD CONSTRAINT detalles_comprobante_pkey PRIMARY KEY (id);


--
-- Name: detalles_retencion detalles_retencion_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_retencion
    ADD CONSTRAINT detalles_retencion_pkey PRIMARY KEY (id);


--
-- Name: egresos egresos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.egresos
    ADD CONSTRAINT egresos_pkey PRIMARY KEY (id);


--
-- Name: empresas empresas_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.empresas
    ADD CONSTRAINT empresas_pkey PRIMARY KEY (id);


--
-- Name: establecimientos establecimientos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.establecimientos
    ADD CONSTRAINT establecimientos_pkey PRIMARY KEY (id);


--
-- Name: firmas_electronicas firmas_electronicas_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.firmas_electronicas
    ADD CONSTRAINT firmas_electronicas_pkey PRIMARY KEY (id);


--
-- Name: gastos gastos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_pkey PRIMARY KEY (id);


--
-- Name: guias_remision guias_remision_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.guias_remision
    ADD CONSTRAINT guias_remision_pkey PRIMARY KEY (id);


--
-- Name: items_guia_remision items_guia_remision_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.items_guia_remision
    ADD CONSTRAINT items_guia_remision_pkey PRIMARY KEY (id);


--
-- Name: lineas_recurrentes lineas_recurrentes_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.lineas_recurrentes
    ADD CONSTRAINT lineas_recurrentes_pkey PRIMARY KEY (id);


--
-- Name: listas_auxiliares listas_auxiliares_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.listas_auxiliares
    ADD CONSTRAINT listas_auxiliares_pkey PRIMARY KEY (id);


--
-- Name: plantillas_recurrentes plantillas_recurrentes_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.plantillas_recurrentes
    ADD CONSTRAINT plantillas_recurrentes_pkey PRIMARY KEY (id);


--
-- Name: puntos_emision puntos_emision_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.puntos_emision
    ADD CONSTRAINT puntos_emision_pkey PRIMARY KEY (id);


--
-- Name: receptores receptores_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.receptores
    ADD CONSTRAINT receptores_pkey PRIMARY KEY (id);


--
-- Name: recibos recibos_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.recibos
    ADD CONSTRAINT recibos_pkey PRIMARY KEY (id);


--
-- Name: retenciones retenciones_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.retenciones
    ADD CONSTRAINT retenciones_pkey PRIMARY KEY (id);


--
-- Name: secuenciales_documento secuenciales_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.secuenciales_documento
    ADD CONSTRAINT secuenciales_documento_pkey PRIMARY KEY (id);


--
-- Name: tipos_gasto tipos_gasto_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.tipos_gasto
    ADD CONSTRAINT tipos_gasto_pkey PRIMARY KEY (id);


--
-- Name: establecimientos uq_establecimiento_codigo; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.establecimientos
    ADD CONSTRAINT uq_establecimiento_codigo UNIQUE (empresa_id, codigo);


--
-- Name: listas_auxiliares uq_lista_tipo_nombre; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.listas_auxiliares
    ADD CONSTRAINT uq_lista_tipo_nombre UNIQUE (tipo, nombre);


--
-- Name: puntos_emision uq_punto_codigo; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.puntos_emision
    ADD CONSTRAINT uq_punto_codigo UNIQUE (establecimiento_id, codigo);


--
-- Name: secuenciales_documento uq_secuencial_punto_tipo; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.secuenciales_documento
    ADD CONSTRAINT uq_secuencial_punto_tipo UNIQUE (punto_emision_id, tipo);


--
-- Name: usuarios usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id);


--
-- Name: ix_anticipos_fecha; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_anticipos_fecha ON public.anticipos USING btree (fecha);


--
-- Name: ix_articulos_codigo; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_articulos_codigo ON public.articulos USING btree (codigo);


--
-- Name: ix_comprobantes_clave_acceso; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_comprobantes_clave_acceso ON public.comprobantes USING btree (clave_acceso);


--
-- Name: ix_comprobantes_numero; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_comprobantes_numero ON public.comprobantes USING btree (numero);


--
-- Name: ix_cuotas_comprobante_id; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_cuotas_comprobante_id ON public.cuotas USING btree (comprobante_id);


--
-- Name: ix_cuotas_vence; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_cuotas_vence ON public.cuotas USING btree (vence);


--
-- Name: ix_egresos_fecha; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_egresos_fecha ON public.egresos USING btree (fecha);


--
-- Name: ix_empresas_ruc; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_empresas_ruc ON public.empresas USING btree (ruc);


--
-- Name: ix_gastos_fecha; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_gastos_fecha ON public.gastos USING btree (fecha);


--
-- Name: ix_guias_remision_clave_acceso; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_guias_remision_clave_acceso ON public.guias_remision USING btree (clave_acceso);


--
-- Name: ix_guias_remision_numero; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_guias_remision_numero ON public.guias_remision USING btree (numero);


--
-- Name: ix_listas_auxiliares_tipo; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_listas_auxiliares_tipo ON public.listas_auxiliares USING btree (tipo);


--
-- Name: ix_plantillas_recurrentes_proxima_emision; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_plantillas_recurrentes_proxima_emision ON public.plantillas_recurrentes USING btree (proxima_emision);


--
-- Name: ix_receptores_identificacion; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_receptores_identificacion ON public.receptores USING btree (identificacion);


--
-- Name: ix_recibos_fecha; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_recibos_fecha ON public.recibos USING btree (fecha);


--
-- Name: ix_recibos_numero; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_recibos_numero ON public.recibos USING btree (numero);


--
-- Name: ix_retenciones_clave_acceso; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_retenciones_clave_acceso ON public.retenciones USING btree (clave_acceso);


--
-- Name: ix_retenciones_numero; Type: INDEX; Schema: public; Owner: factoa
--

CREATE INDEX ix_retenciones_numero ON public.retenciones USING btree (numero);


--
-- Name: ix_tipos_gasto_nombre; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_tipos_gasto_nombre ON public.tipos_gasto USING btree (nombre);


--
-- Name: ix_usuarios_correo; Type: INDEX; Schema: public; Owner: factoa
--

CREATE UNIQUE INDEX ix_usuarios_correo ON public.usuarios USING btree (correo);


--
-- Name: anticipos anticipos_receptor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.anticipos
    ADD CONSTRAINT anticipos_receptor_id_fkey FOREIGN KEY (receptor_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: comprobantes comprobantes_receptor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.comprobantes
    ADD CONSTRAINT comprobantes_receptor_id_fkey FOREIGN KEY (receptor_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: cuentas_bancarias cuentas_bancarias_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuentas_bancarias
    ADD CONSTRAINT cuentas_bancarias_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id) ON DELETE CASCADE;


--
-- Name: cuotas cuotas_comprobante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.cuotas
    ADD CONSTRAINT cuotas_comprobante_id_fkey FOREIGN KEY (comprobante_id) REFERENCES public.comprobantes(id) ON DELETE CASCADE;


--
-- Name: detalles_comprobante detalles_comprobante_comprobante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_comprobante
    ADD CONSTRAINT detalles_comprobante_comprobante_id_fkey FOREIGN KEY (comprobante_id) REFERENCES public.comprobantes(id) ON DELETE CASCADE;


--
-- Name: detalles_retencion detalles_retencion_retencion_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.detalles_retencion
    ADD CONSTRAINT detalles_retencion_retencion_id_fkey FOREIGN KEY (retencion_id) REFERENCES public.retenciones(id) ON DELETE CASCADE;


--
-- Name: egresos egresos_cuenta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.egresos
    ADD CONSTRAINT egresos_cuenta_id_fkey FOREIGN KEY (cuenta_id) REFERENCES public.cuentas_bancarias(id) ON DELETE SET NULL;


--
-- Name: egresos egresos_gasto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.egresos
    ADD CONSTRAINT egresos_gasto_id_fkey FOREIGN KEY (gasto_id) REFERENCES public.gastos(id) ON DELETE SET NULL;


--
-- Name: establecimientos establecimientos_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.establecimientos
    ADD CONSTRAINT establecimientos_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id) ON DELETE CASCADE;


--
-- Name: firmas_electronicas firmas_electronicas_empresa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.firmas_electronicas
    ADD CONSTRAINT firmas_electronicas_empresa_id_fkey FOREIGN KEY (empresa_id) REFERENCES public.empresas(id) ON DELETE CASCADE;


--
-- Name: gastos gastos_proveedor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_proveedor_id_fkey FOREIGN KEY (proveedor_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: gastos gastos_tipo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.gastos
    ADD CONSTRAINT gastos_tipo_id_fkey FOREIGN KEY (tipo_id) REFERENCES public.tipos_gasto(id) ON DELETE SET NULL;


--
-- Name: guias_remision guias_remision_transportista_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.guias_remision
    ADD CONSTRAINT guias_remision_transportista_id_fkey FOREIGN KEY (transportista_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: items_guia_remision items_guia_remision_guia_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.items_guia_remision
    ADD CONSTRAINT items_guia_remision_guia_id_fkey FOREIGN KEY (guia_id) REFERENCES public.guias_remision(id) ON DELETE CASCADE;


--
-- Name: lineas_recurrentes lineas_recurrentes_plantilla_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.lineas_recurrentes
    ADD CONSTRAINT lineas_recurrentes_plantilla_id_fkey FOREIGN KEY (plantilla_id) REFERENCES public.plantillas_recurrentes(id) ON DELETE CASCADE;


--
-- Name: plantillas_recurrentes plantillas_recurrentes_receptor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.plantillas_recurrentes
    ADD CONSTRAINT plantillas_recurrentes_receptor_id_fkey FOREIGN KEY (receptor_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: puntos_emision puntos_emision_establecimiento_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.puntos_emision
    ADD CONSTRAINT puntos_emision_establecimiento_id_fkey FOREIGN KEY (establecimiento_id) REFERENCES public.establecimientos(id) ON DELETE CASCADE;


--
-- Name: recibos recibos_comprobante_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.recibos
    ADD CONSTRAINT recibos_comprobante_id_fkey FOREIGN KEY (comprobante_id) REFERENCES public.comprobantes(id) ON DELETE SET NULL;


--
-- Name: recibos recibos_cuenta_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.recibos
    ADD CONSTRAINT recibos_cuenta_id_fkey FOREIGN KEY (cuenta_id) REFERENCES public.cuentas_bancarias(id) ON DELETE SET NULL;


--
-- Name: recibos recibos_cuota_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.recibos
    ADD CONSTRAINT recibos_cuota_id_fkey FOREIGN KEY (cuota_id) REFERENCES public.cuotas(id) ON DELETE SET NULL;


--
-- Name: retenciones retenciones_sujeto_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.retenciones
    ADD CONSTRAINT retenciones_sujeto_id_fkey FOREIGN KEY (sujeto_id) REFERENCES public.receptores(id) ON DELETE SET NULL;


--
-- Name: secuenciales_documento secuenciales_documento_punto_emision_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: factoa
--

ALTER TABLE ONLY public.secuenciales_documento
    ADD CONSTRAINT secuenciales_documento_punto_emision_id_fkey FOREIGN KEY (punto_emision_id) REFERENCES public.puntos_emision(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict OuSnLr164PgCaFidb7UMGy5uolGwKlzhf6LQJywg8vVcBu6QwSwneY0Ej6SUaLu

